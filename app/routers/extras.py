"""Endpoints complementarios: highlights en video y assets de equipos."""
from fastapi import APIRouter
from app.scrapers import extras_scraper

router = APIRouter(prefix="/extras", tags=["extras"])


@router.get("/highlights")
def highlights():
    """Highlights en video + miniaturas de los ultimos partidos (TheSportsDB,
    con Scorebat como respaldo)."""
    return extras_scraper.get_highlights()


@router.get("/calendar")
def calendar():
    """Calendario de los proximos partidos de Liga MX con miniatura, sede y
    horario (TheSportsDB)."""
    return extras_scraper.get_upcoming_events()


@router.get("/teams/assets")
def team_assets():
    """Escudos, jerseys, estadios y descripciones (ES) por equipo (TheSportsDB),
    indexados por idESPN para unir con los equipos de ESPN."""
    return extras_scraper.get_team_assets()


@router.get("/teams/{espn_team_id}/assets")
def team_assets_by_espn(espn_team_id: int):
    return extras_scraper.get_team_assets_by_espn(espn_team_id)
