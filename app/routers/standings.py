from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import func, case
from sqlalchemy.orm import Session, joinedload
from app.database import get_db
from app import models, schemas

router = APIRouter()

@router.get("/standings", response_model=list[schemas.StandingResponse])
def get_standings(db: Session = Depends(get_db)):
    return db.query(models.Standing).options(joinedload(models.Standing.team)).order_by(models.Standing.position).all()

@router.get("/top-scorers", response_model=list[schemas.TopScorerResponse])
def get_top_scorers(db: Session = Depends(get_db), limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0), season: str = Query("2026")):
    return db.query(models.TopScorer).filter(models.TopScorer.season == season).order_by(models.TopScorer.goals.desc()).offset(offset).limit(limit).all()


@router.get("/liguilla")
def get_liguilla(db: Session = Depends(get_db)):
    """Foto de la clasificacion segun el formato de Liga MX:
      - Liguilla directa: posiciones 1-6
      - Play-In: posiciones 7-10
      - Eliminados: 11 en adelante
    """
    rows = (
        db.query(models.Standing)
        .options(joinedload(models.Standing.team))
        .order_by(models.Standing.position)
        .all()
    )
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



@router.get("/discipline")
def discipline(db: Session = Depends(get_db), limit: int = Query(20, ge=1, le=100)):
    """Tabla de disciplina (fair play) a partir de las tarjetas guardadas en los
    partidos: jugadores con mas tarjetas y totales por equipo."""
    yellow = func.sum(case((models.MatchEvent.event_type == "yellow_card", 1), else_=0))
    red = func.sum(case((models.MatchEvent.event_type == "red_card", 1), else_=0))

    player_rows = (
        db.query(
            models.MatchEvent.player_name,
            models.MatchEvent.team_name,
            yellow.label("yellow"),
            red.label("red"),
        )
        .filter(
            models.MatchEvent.event_type.in_(["yellow_card", "red_card"]),
            models.MatchEvent.player_name.isnot(None),
        )
        .group_by(models.MatchEvent.player_name, models.MatchEvent.team_name)
        .all()
    )
    players = sorted(
        [
            {
                "player": r.player_name,
                "team": r.team_name,
                "yellow_cards": int(r.yellow or 0),
                "red_cards": int(r.red or 0),
                "points": int(r.yellow or 0) + int(r.red or 0) * 2,  # roja pesa doble
            }
            for r in player_rows
        ],
        key=lambda x: (x["red_cards"], x["yellow_cards"]),
        reverse=True,
    )[:limit]

    team_rows = (
        db.query(
            models.MatchEvent.team_name,
            yellow.label("yellow"),
            red.label("red"),
        )
        .filter(
            models.MatchEvent.event_type.in_(["yellow_card", "red_card"]),
            models.MatchEvent.team_name.isnot(None),
        )
        .group_by(models.MatchEvent.team_name)
        .all()
    )
    teams = sorted(
        [
            {
                "team": r.team_name,
                "yellow_cards": int(r.yellow or 0),
                "red_cards": int(r.red or 0),
                "points": int(r.yellow or 0) + int(r.red or 0) * 2,
            }
            for r in team_rows
        ],
        key=lambda x: x["points"],
        reverse=True,
    )

    return {"players": players, "teams": teams}
