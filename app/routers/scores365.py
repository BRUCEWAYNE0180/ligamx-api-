"""Endpoints en vivo basados en 365Scores (datos frescos de Liga MX)."""
from fastapi import APIRouter, Query
from app.scrapers.scores365_scraper import Scores365Scraper
from app.cache import cached

router = APIRouter(prefix="/365scores", tags=["365scores"])


@router.get("/matches")
@cached(60)
def matches(week: int = Query(None, description="Filtra por jornada (roundNum)"),
            status: str = Query(None, description="scheduled | live | finished")):
    data = Scores365Scraper().get_matches()
    if week is not None:
        data = [m for m in data if m.get("week") == week]
    if status:
        data = [m for m in data if m.get("status") == status]
    return sorted(data, key=lambda m: (m.get("match_date") is None, m.get("match_date")))


@router.get("/standings")
@cached(120)
def standings():
    return Scores365Scraper().get_standings()


@router.get("/teams")
@cached(3600)
def teams():
    return Scores365Scraper().get_teams()


@router.get("/matches/{game_id}/info")
@cached(60)
def info(game_id: int):
    """Ficha del partido: sede, arbitro/cuerpo arbitral, marcador y estado."""
    return Scores365Scraper().get_match_info(game_id)


@router.get("/matches/{game_id}/lineups")
@cached(60)
def lineups(game_id: int):
    return Scores365Scraper().get_match_lineups(game_id)


@router.get("/matches/{game_id}/events")
@cached(60)
def events(game_id: int):
    return Scores365Scraper().get_match_events(game_id)


@router.get("/matches/{game_id}/cards")
@cached(60)
def cards(game_id: int):
    return Scores365Scraper().get_match_cards(game_id)
