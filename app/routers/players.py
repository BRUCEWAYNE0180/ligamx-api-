from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_or_404
from app import models, schemas

router = APIRouter()

@router.get("/players", response_model=list[schemas.PlayerResponse])
def get_players(db: Session = Depends(get_db)):
    return db.query(models.Player).all()

@router.get("/players/{player_id}/stats", response_model=schemas.PlayerStatResponse)
def get_player_stat(player_id: int, db: Session = Depends(get_db), season: str = Query("2026")):
    stat = db.query(models.PlayerStat).filter(models.PlayerStat.player_id == player_id, models.PlayerStat.season == season).first()
    if not stat:
        raise HTTPException(status_code=404, detail="Estadisticas no encontradas")
    return stat
