from fastapi import FastAPI, Depends, Query
from sqlalchemy.orm import Session
from apscheduler.schedulers.background import BackgroundScheduler
import subprocess
from app.database import engine, Base, get_db
from app.scrapers.factory import get_scraper
from app import models, schemas

Base.metadata.create_all(bind=engine)

scheduler = BackgroundScheduler()

def auto_sync():
    subprocess.run(["/Users/mac/Desktop/ligamx-api/venv/bin/python", "sync.py"], cwd="/Users/mac/Desktop/ligamx-api")

scheduler.add_job(auto_sync, "interval", hours=6)
scheduler.start()

app = FastAPI(title="Liga MX API", version="1.0")

@app.get("/")
def read_root():
    return {"message": "API Liga MX", "version": "1.0", "status": "running"}

@app.post("/sync")
def sync_data(source: str = "demo", db: Session = Depends(get_db)):
    scraper = get_scraper(source)

    for model in [models.Standing, models.Match, models.Player, models.Week, models.Team, models.Stadium, models.Season]:
        db.query(model).delete()
    db.commit()

    stadiums_map = {}
    for s in scraper.get_stadiums():
        st = models.Stadium(**s)
        db.add(st)
        db.flush()
        stadiums_map[s["name"]] = st.id

    teams_map = {}
    for t in scraper.get_teams():
        team = models.Team(
            id=t["id"],
            name=t["name"],
            short_name=t.get("short_name"),
            city=t.get("city"),
            colors=t.get("colors"),
            founded=t.get("founded"),
            stadium_id=stadiums_map.get(t.get("stadium_name"))
        )
        db.add(team)
        db.flush()
        teams_map[t["name"]] = team.id
        teams_map[t["id"]] = team.id

    for p in scraper.get_players():
        db.add(models.Player(
            id=p["id"],
            name=p["name"],
            position=p.get("position"),
            number=p.get("number"),
            nationality=p.get("nationality"),
            birth_date=p.get("birth_date"),
            photo_url=p.get("photo_url"),
            team_id=teams_map.get(p.get("team_name"))
        ))

    season = models.Season(name="2025", year=2025, tournament_type="Liga MX")
    db.add(season)
    db.flush()

    for m in scraper.get_matches():
        home_id = teams_map.get(m.get("home_team_id")) or teams_map.get(m.get("home_team"))
        away_id = teams_map.get(m.get("away_team_id")) or teams_map.get(m.get("away_team"))
        if not home_id or not away_id:
            continue
        db.add(models.Match(
            season_id=season.id,
            home_team_id=home_id,
            away_team_id=away_id,
            match_date=m.get("match_date"),
            home_score=m.get("home_score"),
            away_score=m.get("away_score"),
            status=m.get("status", "scheduled")
        ))

    for s in scraper.get_standings():
        db.add(models.Standing(
            season_id=season.id,
            team_id=teams_map.get(s.get("team_name")),
            position=s["position"],
            played=s["played"],
            won=s["won"],
            drawn=s["drawn"],
            lost=s["lost"],
            goals_for=s["goals_for"],
            goals_against=s["goals_against"],
            goal_difference=s["goals_for"] - s["goals_against"],
            points=s["points"]
        ))

    db.commit()
    return {"message": "Datos sincronizados", "source": source, "scraper": scraper.source_name}

@app.get("/teams", response_model=list[schemas.TeamResponse])
def get_teams(db: Session = Depends(get_db)): return db.query(models.Team).all()

@app.get("/teams/{team_id}", response_model=schemas.TeamResponse)
def get_team(team_id: int, db: Session = Depends(get_db)): return db.query(models.Team).filter(models.Team.id == team_id).first()

@app.get("/teams/{team_id}/players", response_model=list[schemas.PlayerResponse])
def get_team_players(team_id: int, db: Session = Depends(get_db)): return db.query(models.Player).filter(models.Player.team_id == team_id).all()

@app.get("/matches/team/{team_id}", response_model=list[schemas.MatchResponse])
def get_team_matches(team_id: int, db: Session = Depends(get_db)):
    return db.query(models.Match).filter((models.Match.home_team_id == team_id) | (models.Match.away_team_id == team_id)).order_by(models.Match.match_date).all()

@app.get("/matches/week/{week_number}", response_model=list[schemas.MatchResponse])
def get_matches_by_week(week_number: int, db: Session = Depends(get_db)):
    return db.query(models.Match).filter(models.Match.week_number == week_number).order_by(models.Match.match_date).all()

@app.get("/h2h/{team1_id}/{team2_id}", response_model=list[schemas.MatchResponse])
def get_h2h(team1_id: int, team2_id: int, db: Session = Depends(get_db)):
    return db.query(models.Match).filter(
        ((models.Match.home_team_id == team1_id) & (models.Match.away_team_id == team2_id)) |
        ((models.Match.home_team_id == team2_id) & (models.Match.away_team_id == team1_id))
    ).order_by(models.Match.match_date).all()

@app.get("/matches", response_model=list[schemas.MatchResponse])
def get_matches(db: Session = Depends(get_db)): return db.query(models.Match).all()

@app.get("/standings", response_model=list[schemas.StandingResponse])
def get_standings(db: Session = Depends(get_db)): return db.query(models.Standing).order_by(models.Standing.position).all()

@app.get("/stadiums", response_model=list[schemas.StadiumResponse])
def get_stadiums(db: Session = Depends(get_db)): return db.query(models.Stadium).all()

@app.get("/players", response_model=list[schemas.PlayerResponse])
def get_players(db: Session = Depends(get_db)): return db.query(models.Player).all()

@app.get("/top-scorers", response_model=list[schemas.TopScorerResponse])
def get_top_scorers(db: Session = Depends(get_db), limit: int = Query(20, ge=1, le=100), season: str = Query("2025")):
    return db.query(models.TopScorer).filter(models.TopScorer.season == season).order_by(models.TopScorer.goals.desc()).limit(limit).all()

@app.get("/news", response_model=list[schemas.NewsResponse])
def get_news(db: Session = Depends(get_db), limit: int = Query(20, ge=1, le=100)):
    return db.query(models.News).order_by(models.News.published_at.desc()).limit(limit).all()

@app.get("/matches/live")
def get_live_matches():
    from app.scrapers.espn_requests_scraper import ESPNRequestsScraper
    scraper = ESPNRequestsScraper()
    return scraper.get_live_matches()

@app.get("/matches/today")
def get_matches_today(date: str = Query(None)):
    from datetime import datetime
    from app.scrapers.espn_requests_scraper import ESPNRequestsScraper
    scraper = ESPNRequestsScraper()
    date_str = date.replace("-", "") if date else datetime.now().strftime("%Y%m%d")
    return scraper.get_matches_by_date(date_str)

@app.get("/matches/{event_id}/stats")
def get_match_stats(event_id: str):
    from app.scrapers.espn_requests_scraper import ESPNRequestsScraper
    scraper = ESPNRequestsScraper()
    return scraper.get_match_stats(event_id)

@app.get("/teams/{team_id}/stats")
def get_team_stats(team_id: int, season: str = Query("2025"), db: Session = Depends(get_db)):
    stats = db.query(models.MatchStat).filter(models.MatchStat.team_id == team_id, models.MatchStat.season == season).all()
    if not stats:
        return {"team_id": team_id, "season": season, "matches": 0, "message": "No stats found"}
    totals = {"shots": 0, "shots_on_target": 0, "corners": 0, "fouls": 0, "yellow_cards": 0, "red_cards": 0}
    possession_sum = 0
    count = 0
    for s in stats:
        for k in totals:
            if getattr(s, k):
                totals[k] += getattr(s, k)
        if s.possession:
            possession_sum += s.possession
            count += 1
    return {"team_id": team_id, "season": season, "matches": len(stats), "possession_avg": round(possession_sum / count, 1) if count else None, "totals": totals}

@app.get("/player-stats", response_model=list[schemas.PlayerStatResponse])
def get_player_stats(db: Session = Depends(get_db), limit: int = Query(20, ge=1, le=500), season: str = Query("2025")):
    return db.query(models.PlayerStat).filter(models.PlayerStat.season == season).order_by(models.PlayerStat.goals.desc()).limit(limit).all()

@app.get("/players/{player_id}/stats", response_model=schemas.PlayerStatResponse)
def get_player_stat(player_id: int, db: Session = Depends(get_db), season: str = Query("2025")):
    return db.query(models.PlayerStat).filter(models.PlayerStat.player_id == player_id, models.PlayerStat.season == season).first()

@app.get("/sofascore/player-stats")
def get_sofascore_player_stats(limit: int = Query(20, ge=1, le=500)):
    from app.scrapers.sofascore_scraper import get_player_stats
    return get_player_stats(limit)

@app.get("/sofascore/matches")
def get_sofascore_matches():
    from app.scrapers.sofascore_scraper import get_events
    return get_events()
