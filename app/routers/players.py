from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_or_404
from app import models, schemas

router = APIRouter()

@router.get("/players/top", response_model=list[schemas.PlayerStatResponse])
def get_top_players(limit: int = Query(10, ge=1, le=100), season: str = Query("2026"), db: Session = Depends(get_db)):
    return db.query(models.PlayerStat).filter(models.PlayerStat.season == season).order_by(models.PlayerStat.goals.desc()).limit(limit).all()

@router.get("/players", response_model=list[schemas.PlayerResponse])
def get_players(limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0), db: Session = Depends(get_db)):
    return db.query(models.Player).offset(offset).limit(limit).all()

@router.get("/players/{player_id}", response_model=schemas.PlayerResponse)
def get_player(player_id: int, db: Session = Depends(get_db)):
    return get_or_404(db, models.Player, player_id)

@router.get("/players/{player_id}/stats", response_model=schemas.PlayerStatResponse)
def get_player_stat(player_id: int, db: Session = Depends(get_db), season: str = Query("2026")):
    stat = db.query(models.PlayerStat).filter(models.PlayerStat.player_id == player_id, models.PlayerStat.season == season).first()
    if not stat:
        raise HTTPException(status_code=404, detail="Estadisticas no encontradas")
    return stat
