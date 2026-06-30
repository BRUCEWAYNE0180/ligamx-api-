from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload
import unicodedata
from app.database import get_db
from app.dependencies import get_or_404
from app import models, schemas

router = APIRouter()

@router.get("/teams", response_model=list[schemas.TeamResponse])
def get_teams(limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0), db: Session = Depends(get_db)):
    return db.query(models.Team).options(joinedload(models.Team.stadium)).offset(offset).limit(limit).all()

@router.get("/teams/search", response_model=list[schemas.TeamResponse])
def search_teams(q: str, db: Session = Depends(get_db)):
    def norm(s):
        return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn").lower()
    query = norm(q)
    return [t for t in db.query(models.Team).all() if query in norm(t.name)]

@router.get("/teams/{team_id}", response_model=schemas.TeamResponse)
def get_team(team_id: int, db: Session = Depends(get_db)):
    return get_or_404(db, models.Team, team_id)

@router.get("/teams/{team_id}/players", response_model=list[schemas.PlayerResponse])
def get_team_players(team_id: int, db: Session = Depends(get_db)):
    get_or_404(db, models.Team, team_id)
    return db.query(models.Player).filter(models.Player.team_id == team_id).all()

@router.get("/teams/{team_id}/last-matches", response_model=list[schemas.MatchResponse])
def get_team_last_matches(team_id: int, limit: int = Query(5, ge=1, le=20), db: Session = Depends(get_db)):
    get_or_404(db, models.Team, team_id)
    return db.query(models.Match).options(joinedload(models.Match.home_team), joinedload(models.Match.away_team)).filter((models.Match.home_team_id == team_id) | (models.Match.away_team_id == team_id)).order_by(models.Match.match_date.desc()).limit(limit).all()

@router.get("/teams/{team_id}/stats")
def get_team_stats(team_id: int, season: str = Query("2026"), db: Session = Depends(get_db)):
    get_or_404(db, models.Team, team_id)
    stats = db.query(models.MatchStat).filter(models.MatchStat.team_id == team_id, models.MatchStat.season == season).all()
    if not stats:
        return {"team_id": team_id, "season": season, "matches": 0, "message": "No stats found"}
    totals = {"shots": 0, "shots_on_target": 0, "corners": 0, "fouls": 0, "yellow_cards": 0, "red_cards": 0}
    possession_sum = 0
    count = 0
    for s in stats:
        for k in totals:
            if getattr(s, k):
                totals[k] += getattr(s, k)
        if s.possession:
            possession_sum += s.possession
            count += 1
    return {"team_id": team_id, "season": season, "matches": len(stats), "possession_avg": round(possession_sum / count, 1) if count else None, "totals": totals}



@router.get("/teams/{team_id}/form")
def get_team_form(team_id: int, limit: int = Query(5, ge=1, le=20), db: Session = Depends(get_db)):
    """Forma reciente del equipo: ultimos N partidos jugados con resultado
    (W/D/L) desde la perspectiva del equipo, mas el racha en texto."""
    get_or_404(db, models.Team, team_id)
    matches = (
        db.query(models.Match)
        .options(joinedload(models.Match.home_team), joinedload(models.Match.away_team))
        .filter((models.Match.home_team_id == team_id) | (models.Match.away_team_id == team_id))
        .filter(models.Match.status == "finished")
        .filter(models.Match.home_score != None, models.Match.away_score != None)
        .order_by(models.Match.match_date.desc())
        .limit(limit)
        .all()
    )

    results = []
    summary = {"W": 0, "D": 0, "L": 0}
    for m in matches:
        is_home = m.home_team_id == team_id
        gf = m.home_score if is_home else m.away_score
        ga = m.away_score if is_home else m.home_score
        if gf > ga:
            outcome = "W"
        elif gf < ga:
            outcome = "L"
        else:
            outcome = "D"
        summary[outcome] += 1
        opponent = m.away_team if is_home else m.home_team
        results.append({
            "match_id": m.id,
            "date": m.match_date,
            "home": is_home,
            "opponent": opponent.name if opponent else None,
            "score": f"{gf}-{ga}",
            "result": outcome,
        })

    return {
        "team_id": team_id,
        "played": len(results),
        "summary": summary,
        "form": "".join(r["result"] for r in results),
        "matches": results,
    }
