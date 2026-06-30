from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from app.database import get_db
from app.dependencies import resolve_season_id, resolve_season_label, latest_season, _apertura_first
from app import models, schemas

router = APIRouter()


@router.get("/seasons")
def list_seasons(db: Session = Depends(get_db)):
    """Temporadas (torneos) disponibles en la BD, con su numero de partidos.
    Util para el historico multi-temporada: cada torneo es 'Apertura/Clausura AAAA'."""
    seasons = db.query(models.Season).order_by(models.Season.year.desc(), _apertura_first().desc()).all()
    current = latest_season(db)
    out = []
    for s in seasons:
        matches = db.query(func.count(models.Match.id)).filter(models.Match.season_id == s.id).scalar()
        out.append({
            "id": s.id, "name": s.name, "year": s.year,
            "tournament": s.tournament_type, "matches": matches,
            "is_current": bool(current and current.id == s.id),
        })
    return out


@router.get("/standings", response_model=list[schemas.StandingResponse])
def get_standings(season: str = Query(None, description="Etiqueta ('Apertura 2026') o ano; por defecto la vigente"), db: Session = Depends(get_db)):
    season_id = resolve_season_id(db, season)
    q = db.query(models.Standing).options(joinedload(models.Standing.team))
    if season_id is not None:
        q = q.filter(models.Standing.season_id == season_id)
    return q.order_by(models.Standing.position).all()

@router.get("/top-scorers", response_model=list[schemas.TopScorerResponse])
def get_top_scorers(db: Session = Depends(get_db), limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0), season: str = Query(None)):
    label = resolve_season_label(db, season)
    return db.query(models.TopScorer).filter(models.TopScorer.season == label).order_by(models.TopScorer.goals.desc()).offset(offset).limit(limit).all()


@router.get("/liguilla")
def get_liguilla(season: str = Query(None), db: Session = Depends(get_db)):
    """Foto de la clasificacion segun el formato de Liga MX:
      - Liguilla directa: posiciones 1-6
      - Play-In: posiciones 7-10
      - Eliminados: 11 en adelante
    """
    season_id = resolve_season_id(db, season)
    q = (
        db.query(models.Standing)
        .options(joinedload(models.Standing.team))
    )
    if season_id is not None:
        q = q.filter(models.Standing.season_id == season_id)
    rows = q.order_by(models.Standing.position).all()
    if not rows:
        raise HTTPException(status_code=404, detail="No hay tabla de posiciones todavia")

    def entry(s):
        return {
            "position": s.position,
            "team_id": s.team_id,
            "team": s.team.name if s.team else None,
            "logo_url": s.team.logo_url if s.team else None,
            "played": s.played,
            "points": s.points,
            "goal_difference": s.goal_difference,
        }

    direct, play_in, eliminated = [], [], []
    for s in rows:
        if s.position <= 6:
            direct.append(entry(s))
        elif s.position <= 10:
            play_in.append(entry(s))
        else:
            eliminated.append(entry(s))

    return {
        "format": "Liga MX: 1-6 Liguilla directa, 7-10 Play-In, 11+ eliminados",
        "liguilla_directa": direct,
        "play_in": play_in,
        "eliminados": eliminated,
    }
