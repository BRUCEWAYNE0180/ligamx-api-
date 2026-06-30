from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app import models
from app.season import current_tournament, current_season_name

router = APIRouter()

@router.get("/")
def read_root():
    return {"message": "API Liga MX", "version": "1.0", "status": "running",
            "dashboard": "/app", "docs": "/docs"}

@router.get("/health")
def health_check():
    return {"status": "ok", "timestamp": datetime.now()}

@router.get("/season")
def season_info(db: Session = Depends(get_db)):
    """Informacion del torneo vigente y de los datos cargados, para saber con
    claridad QUE torneo esta sirviendo la API (Apertura vs Clausura)."""
    tournament, year = current_tournament()
    season = db.query(models.Season).order_by(models.Season.id.desc()).first()
    total_matches = db.query(models.Match).count()
    finished = db.query(models.Match).filter(models.Match.status == "finished").count()
    first = (
        db.query(models.Match)
        .filter(models.Match.match_date != None)
        .order_by(models.Match.match_date)
        .first()
    )
    now = datetime.utcnow()
    first_date = first.match_date if first else None
    started = bool(first_date and first_date <= now)
    return {
        "tournament_now": current_season_name(),
        "tournament_type": tournament,
        "year": year,
        "loaded_season": season.name if season else None,
        "loaded_season_type": season.tournament_type if season else None,
        "has_started": started,
        "first_match_date": first_date,
        "total_matches": total_matches,
        "finished_matches": finished,
    }
