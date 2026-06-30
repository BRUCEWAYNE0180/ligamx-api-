from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
import unicodedata
from app.database import get_db
from app.dependencies import get_or_404, resolve_season_label
from app import models, schemas

router = APIRouter()


def _norm(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s or "") if unicodedata.category(c) != "Mn").lower()


# Metricas agregables para la tabla de lideres de temporada (desde player_match_stats)
_LEADER_AGG = {
    "goals": (func.sum(models.PlayerMatchStat.goals), "desc"),
    "assists": (func.sum(models.PlayerMatchStat.assists), "desc"),
    "minutes": (func.sum(models.PlayerMatchStat.minutes), "desc"),
    "shots": (func.sum(models.PlayerMatchStat.shots), "desc"),
    "xg": (func.sum(models.PlayerMatchStat.xg), "desc"),
    "xa": (func.sum(models.PlayerMatchStat.xa), "desc"),
    "key_passes": (func.sum(models.PlayerMatchStat.key_passes), "desc"),
    "interceptions": (func.sum(models.PlayerMatchStat.interceptions), "desc"),
    "touches": (func.sum(models.PlayerMatchStat.touches), "desc"),
    "rating": (func.avg(models.PlayerMatchStat.rating), "desc"),
}


@router.get("/players/top", response_model=list[schemas.PlayerStatResponse])
def get_top_players(limit: int = Query(10, ge=1, le=100), season: str = Query(None), db: Session = Depends(get_db)):
    label = resolve_season_label(db, season)
    return db.query(models.PlayerStat).filter(models.PlayerStat.season == label).order_by(models.PlayerStat.goals.desc()).limit(limit).all()


@router.get("/players/season-leaders")
def season_leaders(
    stat: str = Query("goals", description="goals|assists|minutes|shots|xg|xa|key_passes|interceptions|touches|rating"),
    season: str = Query(None),
    limit: int = Query(20, ge=1, le=100),
    min_appearances: int = Query(1, ge=0, description="filtra jugadores con pocas apariciones (util para 'rating')"),
    db: Session = Depends(get_db),
):
    """Tabla de lideres de temporada calculada desde las stats por partido
    persistidas (player_match_stats): goleadores, asistentes, minutos, xG, xA,
    rating promedio, etc. A diferencia de /365scores/leaders, sale de la BD."""
    label = resolve_season_label(db, season)
    expr, _ = _LEADER_AGG.get(stat, _LEADER_AGG["goals"])
    M = models.PlayerMatchStat
    rows = (
        db.query(M.player_name, M.team_name, func.count(M.id).label("apps"), expr.label("value"))
        .filter(M.season == label)
        .group_by(M.player_name, M.team_name)
        .having(func.count(M.id) >= min_appearances)
        .order_by(expr.desc())
        .limit(limit)
        .all()
    )
    out = []
    for i, (name, team, apps, value) in enumerate(rows):
        if value is None:
            continue
        out.append({
            "rank": i + 1, "player": name, "team": team, "appearances": apps,
            "stat": stat, "value": round(float(value), 2) if stat in ("xg", "xa", "rating") else int(value),
        })
    return out


@router.get("/players/xg-performance")
def xg_performance(
    season: str = Query(None),
    order: str = Query("over", description="'over' = más goles que su xG primero; 'under' = al revés"),
    limit: int = Query(20, ge=1, le=100),
    min_appearances: int = Query(1, ge=0),
    db: Session = Depends(get_db),
):
    """Rendimiento goles vs xG de la temporada (desde player_match_stats): quién
    finaliza por encima de lo esperado (clínicos) y quién por debajo. diff = goles − xG."""
    label = resolve_season_label(db, season)
    M = models.PlayerMatchStat
    rows = (
        db.query(M.player_name, M.team_name, func.count(M.id).label("apps"),
                 func.sum(M.goals).label("goals"), func.sum(M.xg).label("xg"))
        .filter(M.season == label)
        .group_by(M.player_name, M.team_name)
        .having(func.count(M.id) >= min_appearances)
        .all()
    )
    out = []
    for name, team, apps, goals, xg in rows:
        g = int(goals or 0)
        x = round(float(xg or 0), 2)
        out.append({
            "player": name, "team": team, "appearances": apps,
            "goals": g, "xg": x, "diff": round(g - x, 2),
        })
    out.sort(key=lambda r: r["diff"], reverse=(order != "under"))
    for i, r in enumerate(out):
        r["rank"] = i + 1
    return out[:limit]


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
def get_player_stat(player_id: int, db: Session = Depends(get_db), season: str = Query(None)):
    label = resolve_season_label(db, season)
    stat = db.query(models.PlayerStat).filter(models.PlayerStat.player_id == player_id, models.PlayerStat.season == label).first()
    if not stat:
        raise HTTPException(status_code=404, detail="Estadisticas no encontradas")
    return stat


def _player_match_rows(db, player_name: str, season: str = None):
    """Filas de player_match_stats del jugador, emparejadas por nombre normalizado
    (las stats vienen de 365Scores, cuyos ids de jugador no coinciden con ESPN)."""
    nq = _norm(player_name)
    q = db.query(models.PlayerMatchStat)
    if season:
        q = q.filter(models.PlayerMatchStat.season == season)
    return [r for r in q.all() if _norm(r.player_name or "") == nq]


@router.get("/players/{player_id}/match-stats", response_model=list[schemas.PlayerMatchStatResponse])
def get_player_match_stats(player_id: int, season: str = Query(None), db: Session = Depends(get_db)):
    """Historial partido a partido del jugador con sus estadisticas completas."""
    player = get_or_404(db, models.Player, player_id)
    rows = _player_match_rows(db, player.name, season)
    return sorted(rows, key=lambda r: (r.match_id is None, r.match_id))


@router.get("/players/{player_id}/season-stats")
def get_player_season_stats(player_id: int, season: str = Query(None), db: Session = Depends(get_db)):
    """Resumen agregado de la temporada del jugador (suma de partidos jugados):
    minutos, goles, asistencias, remates, xG, xA y rating promedio."""
    player = get_or_404(db, models.Player, player_id)
    label = resolve_season_label(db, season)
    rows = _player_match_rows(db, player.name, label)
    if not rows:
        raise HTTPException(status_code=404, detail="Sin estadisticas por partido para esta temporada")

    def _sum(attr):
        return sum(getattr(r, attr) or 0 for r in rows)

    ratings = [r.rating for r in rows if r.rating is not None]
    return {
        "player_id": player_id,
        "player_name": player.name,
        "team_id": player.team_id,
        "season": label,
        "appearances": len(rows),
        "starts": sum(1 for r in rows if r.starter),
        "minutes": _sum("minutes"),
        "goals": _sum("goals"),
        "assists": _sum("assists"),
        "shots": _sum("shots"),
        "key_passes": _sum("key_passes"),
        "interceptions": _sum("interceptions"),
        "touches": _sum("touches"),
        "xg": round(_sum("xg"), 2),
        "xa": round(_sum("xa"), 2),
        "avg_rating": round(sum(ratings) / len(ratings), 2) if ratings else None,
    }
