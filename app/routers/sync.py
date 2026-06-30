from datetime import datetime
from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import verify_api_key
from app.scrapers.factory import get_scraper
from app.scrapers.news_scraper import fetch_news
from app import models

router = APIRouter()

@router.post("/sync")
def sync_data(source: str = "demo", db: Session = Depends(get_db), api_key: str = Depends(verify_api_key)):
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

    current_year = datetime.now().year
    season = models.Season(name=str(current_year), year=current_year, tournament_type="Liga MX")
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
            status=m.get("status", "scheduled"),
            week_number=m.get("week")
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

    # News sync
    db.query(models.News).delete()
    for n in fetch_news(limit=50):
        db.add(models.News(**n))
    db.commit()

    return {"message": "Datos sincronizados", "source": source, "scraper": scraper.source_name}
