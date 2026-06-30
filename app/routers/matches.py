from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_or_404
from app import models, schemas
from app.scrapers.espn_requests_scraper import ESPNRequestsScraper

router = APIRouter()

@router.get("/matches", response_model=list[schemas.MatchResponse])
def get_matches(db: Session = Depends(get_db), team_id: int = Query(None), week: int = Query(None), status: str = Query(None)):
    q = db.query(models.Match)
    if team_id:
        q = q.filter((models.Match.home_team_id == team_id) | (models.Match.away_team_id == team_id))
    if week:
        q = q.filter(models.Match.week_number == week)
    if status:
        q = q.filter(models.Match.status == status)
    return q.order_by(models.Match.match_date).all()

@router.get("/matches/team/{team_id}", response_model=list[schemas.MatchResponse])
def get_team_matches(team_id: int, db: Session = Depends(get_db)):
    get_or_404(db, models.Team, team_id)
    return db.query(models.Match).filter((models.Match.home_team_id == team_id) | (models.Match.away_team_id == team_id)).order_by(models.Match.match_date).all()

@router.get("/matches/week/{week_number}", response_model=list[schemas.MatchResponse])
def get_matches_by_week(week_number: int, db: Session = Depends(get_db)):
    return db.query(models.Match).filter(models.Match.week_number == week_number).order_by(models.Match.match_date).all()

@router.get("/h2h/{team1_id}/{team2_id}", response_model=list[schemas.MatchResponse])
def get_h2h(team1_id: int, team2_id: int, db: Session = Depends(get_db)):
    get_or_404(db, models.Team, team1_id)
    get_or_404(db, models.Team, team2_id)
    return db.query(models.Match).filter(
        ((models.Match.home_team_id == team1_id) & (models.Match.away_team_id == team2_id)) |
        ((models.Match.home_team_id == team2_id) & (models.Match.away_team_id == team1_id))
    ).order_by(models.Match.match_date).all()

@router.get("/matches/live")
def get_live_matches():
    scraper = ESPNRequestsScraper()
    return scraper.get_live_matches()

@router.get("/matches/today")
def get_matches_today(date: str = Query(None)):
    scraper = ESPNRequestsScraper()
    date_str = date.replace("-", "") if date else datetime.now().strftime("%Y%m%d")
    return scraper.get_matches_by_date(date_str)

@router.get("/matches/{event_id}/stats")
def get_match_stats(event_id: str):
    scraper = ESPNRequestsScraper()
    return scraper.get_match_stats(event_id)
