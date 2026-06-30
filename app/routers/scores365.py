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


@router.get("/matches/{game_id}/player-stats")
@cached(120)
def match_player_stats(game_id: int):
    """Estadisticas COMPLETAS por jugador del partido (minutos, goles, xG, xA,
    remates, pases, regates, duelos, intercepciones, rating...) para todos los
    jugadores de la alineacion. Joyita que ESPN no expone."""
    return Scores365Scraper().get_match_player_stats(game_id)


@router.get("/leaders")
@cached(600)
def player_leaders(category_id: int = Query(None, description="1=Goles, 3=Asistencias, 5=Goles+Asist, 12=Amarillas, 15=Salvadas...")):
    """Lideres de temporada por jugador en 16 categorias (goles, xG, asistencias,
    tarjetas, salvadas, valla invicta...). Filtra con category_id."""
    return Scores365Scraper().get_player_season_leaders(category_id)


@router.get("/team-leaders")
@cached(600)
def team_leaders(category_id: int = Query(None)):
    """Lideres de temporada por equipo."""
    return Scores365Scraper().get_team_season_leaders(category_id)


@router.get("/matches/{game_id}/shots")
@cached(120)
def match_shots(game_id: int):
    """Mapa de tiros con xG del partido: cada disparo con xG, xGoT, parte del
    cuerpo, resultado y coordenadas, mas los totales de xG por equipo."""
    return Scores365Scraper().get_match_shots(game_id)


@router.get("/matches/{game_id}/top-performers")
@cached(120)
def match_top_performers(game_id: int):
    """Mejores jugadores del partido por posicion (local y visitante)."""
    return Scores365Scraper().get_match_top_performers(game_id)
