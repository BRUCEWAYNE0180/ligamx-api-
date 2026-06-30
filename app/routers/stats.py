from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas

router = APIRouter()

@router.get("/player-stats", response_model=list[schemas.PlayerStatResponse])
def get_player_stats(db: Session = Depends(get_db), limit: int = Query(20, ge=1, le=500), season: str = Query("2026")):
    return db.query(models.PlayerStat).filter(models.PlayerStat.season == season).order_by(models.PlayerStat.goals.desc()).limit(limit).all()
