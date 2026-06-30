from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
import unicodedata
from app.database import get_db
from app.dependencies import get_or_404
from app import models, schemas

router = APIRouter()


def _norm(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s or "") if unicodedata.category(c) != "Mn").lower()


@router.get("/players/top", response_model=list[schemas.PlayerStatResponse])
def get_top_players(limit: int = Query(10, ge=1, le=100), season: str = Query("2026"), db: Session = Depends(get_db)):
    return db.query(models.PlayerStat).filter(models.PlayerStat.season == season).order_by(models.PlayerStat.goals.desc()).limit(limit).all()


@router.get("/players/search", response_model=list[schemas.PlayerResponse])
def search_players(
    q: str = Query(None, description="Texto a buscar en el nombre (ignora acentos)"),
    position: str = Query(None),
    nationality: str = Query(None),
    team_id: int = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Busqueda y filtrado de jugadores por nombre, posicion, nacionalidad y equipo."""
    query = db.query(models.Player)
    if team_id:
        query = query.filter(models.Player.team_id == team_id)
    if position:
        query = query.filter(models.Player.position == position)
    candidates = query.all()
    nq = _norm(q) if q else None
    nnat = _norm(nationality) if nationality else None
    out = []
    for p in candidates:
        if nq and nq not in _norm(p.name):
            continue
        if nnat and nnat not in _norm(p.nationality or ""):
            continue
        out.append(p)
        if len(out) >= limit:
            break
    return out


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
