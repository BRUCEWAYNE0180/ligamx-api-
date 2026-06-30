from datetime import datetime, timedelta
from app.database import engine, Base, SessionLocal
from app.scrapers.factory import get_scraper

from app.scrapers.news_scraper import fetch_news
from app.scrapers.sync_all_stats import sync_all_stats

from app import models

Base.metadata.create_all(bind=engine)

def calculate_week_numbers(matches):
    """Asigna numeros de jornada basandose en la fecha.
    La jornada de Liga MX va de viernes a jueves."""
    matches_with_date = [m for m in matches if m.get("match_date")]
    if not matches_with_date:
        return

    def week_start(date):
        # Viernes=4; la jornada empieza viernes y termina jueves
        days_since_friday = (date.weekday() - 4) % 7
        return (date - timedelta(days=days_since_friday)).date()

    matches_with_date.sort(key=lambda m: m["match_date"])

    groups = {}
    for m in matches_with_date:
        ws = week_start(m["match_date"])
        groups.setdefault(ws, []).append(m)

    sorted_weeks = sorted(groups.keys())
    week_number_by_start = {ws: i + 1 for i, ws in enumerate(sorted_weeks)}

    for m in matches_with_date:
        ws = week_start(m["match_date"])
        m["week"] = week_number_by_start[ws]

db = SessionLocal()

try:
    scraper = get_scraper("espn")

    for m in [
        models.Standing,
        models.MatchStat,
        models.PlayerStat,
        models.Match,
        models.Player,
        models.Week,
        models.Team,
        models.Stadium,
        models.Season,
    ]:
        db.query(m).delete()
    db.commit()

    smap = {}
    for s in scraper.get_stadiums():
        st = models.Stadium(**s)
        db.add(st)
        db.flush()
        smap[s["name"]] = st.id

    tmap = {}
    team_count = 0
    for t in scraper.get_teams():
        tm = models.Team(
            id=t["id"],
            name=t["name"],
            short_name=t.get("short_name"),
            city=t.get("city"),
            colors=t.get("colors"),
            founded=t.get("founded"),
            stadium_id=smap.get(t.get("stadium_name")),
        )
        db.add(tm)
        db.flush()
        tmap[t["name"]] = tm.id
        tmap[t["id"]] = tm.id
        team_count += 1

    for p in scraper.get_players():
        db.add(
            models.Player(
                id=p["id"],
                name=p["name"],
                position=p.get("position"),
                number=p.get("number"),
                nationality=p.get("nationality"),
                birth_date=p.get("birth_date"),
                photo_url=p.get("photo_url"),
                team_id=tmap.get(p.get("team_name")),
            )
        )

    current_year = datetime.now().year
    sn = models.Season(name=str(current_year), year=current_year, tournament_type="Liga MX")
    db.add(sn)
    db.flush()

    matches = scraper.get_matches()
    calculate_week_numbers(matches)

    for m in matches:
        hid = tmap.get(m.get("home_team_id")) or tmap.get(m.get("home_team"))
        aid = tmap.get(m.get("away_team_id")) or tmap.get(m.get("away_team"))
        if hid and aid:
            db.add(
                models.Match(
                    season_id=sn.id,
                    home_team_id=hid,
                    away_team_id=aid,
                    match_date=m.get("match_date"),
                    home_score=m.get("home_score"),
                    away_score=m.get("away_score"),
                    status=m.get("status", "scheduled"),
                    week_number=m.get("week"),
                )
            )

    for s in scraper.get_standings():
        db.add(
            models.Standing(
                season_id=sn.id,
                team_id=tmap.get(s.get("team_name")),
                position=s["position"],
                played=s["played"],
                won=s["won"],
                drawn=s["drawn"],
                lost=s["lost"],
                goals_for=s["goals_for"],
                goals_against=s["goals_against"],
                goal_difference=s["goals_for"] - s["goals_against"],
                points=s["points"],
            )
        )

    db.commit()

    sync_all_stats(db, matches, scraper, tmap, str(current_year))

    print(
        "OK estadios",
        len(smap),
        "equipos",
        team_count,
        "jugadores",
        len(db.query(models.Player).all()),
        "partidos",
        len(db.query(models.Match).all()),
    )

    print("Sincronizando noticias...")
    db.query(models.News).delete()
    for n in fetch_news(limit=50):
        db.add(models.News(**n))
    db.commit()
    print("OK noticias", len(db.query(models.News).all()))

except Exception as e:
    db.rollback()
    print(f"Error durante la sincronizacion: {e}")
    raise
finally:
    db.close()
