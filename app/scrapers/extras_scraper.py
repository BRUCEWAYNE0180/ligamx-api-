"""Fuentes complementarias ("joyitas") para enriquecer la API de Liga MX.

- Scorebat: highlights en video de los partidos (gratis, sin key).
- TheSportsDB: escudos, jerseys, estadios, apodos y descripciones en espanol.
  Trae el campo idESPN, que coincide con los IDs de equipo de ESPN usados en
  el resto del proyecto, lo que permite unir ambas fuentes sin friccion.
"""
import logging
from typing import Dict, List
import requests

logger = logging.getLogger(__name__)

SCOREBAT_URL = "https://www.scorebat.com/video-api/v3/"
THESPORTSDB_KEY = "3"  # key publica gratuita
THESPORTSDB_TEAMS = f"https://www.thesportsdb.com/api/v1/json/{THESPORTSDB_KEY}/search_all_teams.php"

_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"}


def _get_json(url: str, params: Dict = None) -> Dict:
    r = requests.get(url, headers=_HEADERS, params=params, timeout=20)
    r.raise_for_status()
    return r.json()


def get_highlights() -> List[Dict]:
    """Highlights en video de Liga MX desde Scorebat."""
    try:
        data = _get_json(SCOREBAT_URL)
    except Exception as e:
        logger.warning(f"Scorebat fallo: {e}")
        return []
    out = []
    for item in data.get("response", []):
        comp = (item.get("competition") or "").lower()
        if "mexico" not in comp and "liga mx" not in comp:
            continue
        out.append({
            "title": item.get("title"),
            "competition": item.get("competition"),
            "home_team": item.get("homeTeam", {}).get("name") if isinstance(item.get("homeTeam"), dict) else item.get("homeTeam"),
            "away_team": item.get("awayTeam", {}).get("name") if isinstance(item.get("awayTeam"), dict) else item.get("awayTeam"),
            "date": item.get("date"),
            "thumbnail": item.get("thumbnail"),
            "match_url": item.get("matchviewUrl"),
            "videos": [{"title": v.get("title"), "embed": v.get("embed")} for v in item.get("videos", [])],
        })
    return out


def get_team_assets() -> List[Dict]:
    """Escudos, jerseys, estadios, apodos y descripciones (ES) por equipo,
    indexados por idESPN para unir con los equipos de ESPN."""
    try:
        data = _get_json(THESPORTSDB_TEAMS, {"l": "Mexican Primera League"})
    except Exception as e:
        logger.warning(f"TheSportsDB fallo: {e}")
        return []
    out = []
    for t in data.get("teams", []) or []:
        espn_id = t.get("idESPN")
        out.append({
            "espn_team_id": int(espn_id) if espn_id and str(espn_id).isdigit() else None,
            "name": t.get("strTeam"),
            "nickname": t.get("strKeywords"),
            "founded": int(t["intFormedYear"]) if t.get("intFormedYear") and str(t["intFormedYear"]).isdigit() else None,
            "stadium": t.get("strStadium"),
            "stadium_capacity": int(t["intStadiumCapacity"]) if t.get("intStadiumCapacity") and str(t["intStadiumCapacity"]).isdigit() else None,
            "badge": t.get("strBadge"),
            "jersey": t.get("strEquipment"),
            "stadium_image": t.get("strStadiumThumb"),
            "description_es": t.get("strDescriptionES"),
            "website": t.get("strWebsite"),
        })
    return out


def get_team_assets_by_espn(espn_team_id: int) -> Dict:
    for team in get_team_assets():
        if team.get("espn_team_id") == espn_team_id:
            return team
    return {}
