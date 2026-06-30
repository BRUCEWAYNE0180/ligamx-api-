from fastapi import APIRouter, Query

router = APIRouter()

@router.get("/sofascore/player-stats")
def get_sofascore_player_stats(limit: int = Query(20, ge=1, le=500)):
    from app.scrapers.sofascore_scraper import get_player_stats
    return get_player_stats(limit)

@router.get("/sofascore/matches")
def get_sofascore_matches():
    from app.scrapers.sofascore_scraper import get_events
    return get_events()
