from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session, joinedload
from app.database import get_db
from app.dependencies import get_or_404
from app import models, schemas
from app.scrapers.espn_requests_scraper import ESPNRequestsScraper
from app.scrapers.sofascore_scraper import get_match_details

router = APIRouter()

@router.get("/matches", response_model=list[schemas.MatchResponse])
def get_matches(limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0), team_id: int = Query(None), week: int = Query(None), status: str = Query(None), db: Session = Depends(get_db)):
    q = db.query(models.Match).options(joinedload(models.Match.home_team), joinedload(models.Match.away_team))
    if team_id:
        q = q.filter((models.Match.home_team_id == team_id) | (models.Match.away_team_id == team_id))
    if week:
        q = q.filter(models.Match.week_number == week)
    if status:
        q = q.filter(models.Match.status == status)
    return q.order_by(models.Match.match_date).offset(offset).limit(limit).all()

@router.get("/matches/upcoming", response_model=list[schemas.MatchResponse])
def get_upcoming_matches(limit: int = Query(10, ge=1, le=50), db: Session = Depends(get_db)):
    return db.query(models.Match).options(joinedload(models.Match.home_team), joinedload(models.Match.away_team)).filter(models.Match.match_date >= datetime.now()).order_by(models.Match.match_date).limit(limit).all()

@router.get("/matches/team/{team_id}", response_model=list[schemas.MatchResponse])
def get_team_matches(team_id: int, limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0), db: Session = Depends(get_db)):
    get_or_404(db, models.Team, team_id)
    return db.query(models.Match).options(joinedload(models.Match.home_team), joinedload(models.Match.away_team)).filter((models.Match.home_team_id == team_id) | (models.Match.away_team_id == team_id)).order_by(models.Match.match_date).offset(offset).limit(limit).all()

@router.get("/matches/week/{week_number}", response_model=list[schemas.MatchResponse])
def get_matches_by_week(week_number: int, limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0), db: Session = Depends(get_db)):
    return db.query(models.Match).options(joinedload(models.Match.home_team), joinedload(models.Match.away_team)).filter(models.Match.week_number == week_number).order_by(models.Match.match_date).offset(offset).limit(limit).all()

@router.get("/h2h/{team1_id}/{team2_id}", response_model=list[schemas.MatchResponse])
def get_h2h(team1_id: int, team2_id: int, db: Session = Depends(get_db)):
    get_or_404(db, models.Team, team1_id)
    get_or_404(db, models.Team, team2_id)
    return db.query(models.Match).filter(
        ((models.Match.home_team_id == team1_id) & (models.Match.away_team_id == team2_id)) |
        ((models.Match.home_team_id == team2_id) & (models.Match.away_team_id == team1_id))
    ).order_by(models.Match.match_date).all()

@router.get("/matches/{match_id}", response_model=schemas.MatchResponse)
def get_match(match_id: int, db: Session = Depends(get_db)):
    return get_or_404(db, models.Match, match_id)

@router.get("/matches/{match_id}/sofascore")
def get_match_sofascore(match_id: int, db: Session = Depends(get_db)):
    match = get_or_404(db, models.Match, match_id)
    if not match.sofascore_event_id:
        raise HTTPException(status_code=404, detail="No hay datos de SofaScore para este partido")
    return get_match_details(match.sofascore_event_id)

@router.get("/matches/{event_id}/stats")
def get_match_stats(event_id: str):
    scraper = ESPNRequestsScraper()
    return scraper.get_match_stats(event_id)

@router.get("/matches/live")
def get_live_matches():
    scraper = ESPNRequestsScraper()
    return scraper.get_live_matches()

@router.get("/matches/today")
def get_matches_today(date: str = Query(None)):
    scraper = ESPNRequestsScraper()
    date_str = date.replace("-", "") if date else datetime.now().strftime("%Y%m%d")
    return scraper.get_matches_by_date(date_str)

@router.get("/weeks")
def get_weeks(db: Session = Depends(get_db)):
    weeks = db.query(models.Match.week_number).filter(models.Match.week_number != None).distinct().order_by(models.Match.week_number).all()
    return [w[0] for w in weeks]

@router.get("/weeks/current")
def get_current_week(db: Session = Depends(get_db)):
    today = datetime.now().date()
    matches = db.query(models.Match).filter(models.Match.match_date != None).order_by(models.Match.match_date).all()
    if not matches:
        raise HTTPException(status_code=404, detail="No hay partidos")
    def week_start(date):
        days_since_friday = (date.weekday() - 4) % 7
        return date - timedelta(days=days_since_friday)
    today_week_start = week_start(today)
    for m in matches:
        mdate = m.match_date.date() if hasattr(m.match_date, "date") else m.match_date
        if week_start(mdate) == today_week_start:
            return {"week_number": m.week_number, "start_date": str(today_week_start)}
    first_match = matches[0]
    first_date = first_match.match_date.date() if hasattr(first_match.match_date, "date") else first_match.match_date
    if today < first_date:
        return {"week_number": first_match.week_number, "start_date": str(week_start(first_date)), "note": "Temporada aun no inicia"}
    last_match = matches[-1]
    return {"week_number": last_match.week_number, "note": "Temporada finalizada"}
