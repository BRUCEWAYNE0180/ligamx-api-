from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas

router = APIRouter()

@router.get("/standings", response_model=list[schemas.StandingResponse])
def get_standings(db: Session = Depends(get_db)):
    return db.query(models.Standing).order_by(models.Standing.position).all()

@router.get("/top-scorers", response_model=list[schemas.TopScorerResponse])
def get_top_scorers(db: Session = Depends(get_db), limit: int = Query(20, ge=1, le=100), season: str = Query("2026")):
    return db.query(models.TopScorer).filter(models.TopScorer.season == season).order_by(models.TopScorer.goals.desc()).limit(limit).all()
