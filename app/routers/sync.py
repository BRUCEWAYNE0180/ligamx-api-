from datetime import datetime
from fastapi import APIRouter, Depends, Query, HTTPException, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import verify_api_key
from app.rate_limit import limiter, SYNC_LIMIT
from app.season import to_naive_utc
from app.services.sync_service import run_sync_with_log, run_backfill_with_log
from app import models

router = APIRouter()

@router.post("/sync")
@limiter.limit(SYNC_LIMIT)
def sync_data(request: Request, source: str = "espn", db: Session = Depends(get_db), api_key: str = Depends(verify_api_key)):
    result = run_sync_with_log(db, source)
    return {"message": "Datos sincronizados", "source": source, "result": result}


@router.post("/sync/backfill")
@limiter.limit(SYNC_LIMIT)
def backfill_season(
    request: Request,
    year: int = Query(..., ge=2000, le=2100, description="Ano del torneo, p. ej. 2025"),
    tournament: str = Query(..., description="'Apertura' o 'Clausura'"),
    source: str = Query("espn"),
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key),
):
    """Carga una temporada PASADA al historico sin borrar las demas. La tabla se
    reconstruye desde los resultados. Ej: POST /sync/backfill?year=2025&tournament=Apertura"""
    if tournament not in ("Apertura", "Clausura"):
        raise HTTPException(status_code=422, detail="tournament debe ser 'Apertura' o 'Clausura'")
    try:
        result = run_backfill_with_log(db, year, tournament, source)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return {"message": "Temporada cargada al historico", "result": result}


@router.post("/sync/player-identity")
@limiter.limit(SYNC_LIMIT)
def sync_player_identity(
    request: Request,
    season: str = Query(None, description="Etiqueta de temporada; por defecto todas"),
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key),
):
    """Reconstruye el mapa de identidad ESPN<->365Scores (rellena
    players.external_365_id) emparejando por nombre+equipo. Idempotente."""
    from app.services.player_identity import build_player_identity_map
    result = build_player_identity_map(db, season)
    return {"message": "Mapa de identidad reconstruido", "result": result}


@router.get("/sync/status")
def sync_status(db: Session = Depends(get_db)):
    """Estado y frescura de los datos: ultimo sync, si fue exitoso y hace
    cuanto corrio. Util para monitoreo y para confiar en la API."""
    last = db.query(models.SyncLog).order_by(models.SyncLog.finished_at.desc()).first()
    last_success = (
        db.query(models.SyncLog)
        .filter(models.SyncLog.status == "success")
        .order_by(models.SyncLog.finished_at.desc())
        .first()
    )

    def serialize(log):
        if not log:
            return None
        return {
            "status": log.status,
            "source": log.source,
            "season": log.season,
            "teams": log.teams,
            "players": log.players,
            "matches": log.matches,
            "detail": log.detail,
            "duration_seconds": round(log.duration_seconds, 1) if log.duration_seconds else None,
            "finished_at": log.finished_at,
        }

    age_seconds = None
    if last_success and last_success.finished_at:
        age_seconds = (datetime.utcnow() - to_naive_utc(last_success.finished_at)).total_seconds()

    return {
        "last_sync": serialize(last),
        "last_successful_sync": serialize(last_success),
        "data_age_seconds": int(age_seconds) if age_seconds is not None else None,
        "data_age_hours": round(age_seconds / 3600, 1) if age_seconds is not None else None,
        "has_data": db.query(models.Team).count() > 0,
    }
