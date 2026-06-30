"""Scraper de 365Scores para Liga MX (Apertura 2026).

365Scores expone una API JSON accesible desde servidores (sin el bloqueo de
Cloudflare que tiene SofaScore) y entrega datos muy frescos y en espanol:
fixtures, resultados, tabla, alineaciones con posiciones en cancha, eventos
(goles, tarjetas, cambios) y arbitros.

Competencia Liga MX = 141.
"""
import time
import logging
from datetime import datetime, timezone
from typing import Dict, List
import requests

from app.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

BASE = "https://webws.365scores.com/web"
COMPETITION_ID = 141  # Liga MX
COMMON_PARAMS = {"appTypeId": 5, "langId": 29, "timezoneName": "America/Mexico_City"}

# Catalogo de tipos de evento de 365Scores
EVENT_GOAL = 1
EVENT_YELLOW = 2
EVENT_RED = 3
EVENT_GOAL_DISALLOWED = 11
EVENT_SUBSTITUTION = 1000


def _status_from_group(game: Dict) -> str:
    sg = game.get("statusGroup")
    if sg == 4:
        return "finished"
    if sg == 3:
        return "live"
    return "scheduled"


def _parse_date(value):
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return None
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


class Scores365Scraper(BaseScraper):
    def __init__(self):
        self._headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "*/*",
            "Referer": "https://www.365scores.com/",
        }

    @property
    def source_name(self) -> str:
        return "365scores"

    def _get_json(self, path: str, params: Dict = None, retries: int = 3) -> Dict:
        url = f"{BASE}/{path.lstrip('/')}"
        merged = dict(COMMON_PARAMS)
        if params:
            merged.update(params)
        for attempt in range(retries):
            try:
                r = requests.get(url, headers=self._headers, params=merged, timeout=20)
                r.raise_for_status()
                return r.json()
            except Exception as e:
                logger.warning(f"365scores request fallo ({attempt+1}/{retries}): {url} - {e}")
                if attempt == retries - 1:
                    raise
                time.sleep(2 ** attempt)
        return {}

    # ---------- Catalogo base ----------
    def _standings_raw(self) -> Dict:
        return self._get_json("standings/", {"competitions": COMPETITION_ID})

    def get_teams(self) -> List[Dict]:
        data = self._standings_raw()
        teams = []
        seen = set()
        for block in data.get("standings", []):
            for row in block.get("rows", []):
                c = row.get("competitor", {})
                cid = c.get("id")
                if not cid or cid in seen:
                    continue
                seen.add(cid)
                teams.append({
                    "id": int(cid),
                    "name": c.get("name", ""),
                    "short_name": c.get("symbolicName") or c.get("name", "")[:3].upper(),
                    "city": None,
                    "colors": c.get("color"),
                    "stadium_name": None,
                })
        return teams

    def get_standings(self) -> List[Dict]:
        data = self._standings_raw()
        standings = []
        for block in data.get("standings", []):
            for i, row in enumerate(block.get("rows", [])):
                c = row.get("competitor", {})
                gf = int(row.get("for", 0) or 0)
                ga = int(row.get("against", 0) or 0)
                standings.append({
                    "position": int(row.get("position", i + 1)),
                    "team_name": c.get("name", ""),
                    "played": int(row.get("gamePlayed", 0) or 0),
                    "won": int(row.get("gamesWon", 0) or 0),
                    "drawn": int(row.get("gamesEven", 0) or 0),
                    "lost": int(row.get("gamesLost", 0) or 0),
                    "goals_for": gf,
                    "goals_against": ga,
                    "goal_difference": gf - ga,
                    "points": int(row.get("points", 0) or 0),
                })
            break  # solo la tabla general
        return standings

    def get_stadiums(self) -> List[Dict]:
        # 365Scores no siempre expone estadios antes del partido; mejor esfuerzo
        # a partir de los resultados ya jugados.
        stadiums = {}
        try:
            data = self._get_json("games/results/", {"competitions": COMPETITION_ID})
            for g in data.get("games", []):
                v = g.get("venue") or {}
                name = v.get("name")
                if name and name not in stadiums:
                    stadiums[name] = {"name": name, "city": v.get("shortName") or None}
        except Exception as e:
            logger.warning(f"365scores stadiums fallo: {e}")
        return list(stadiums.values())

    def get_players(self, competitor_ids: List[int] = None) -> List[Dict]:
        # 365Scores no expone un endpoint de plantilla estable (404/500),
        # por lo que los rosters se obtienen de ESPN. Se devuelve vacio para
        # no bloquear el sync. (Los jugadores que SI aporta 365Scores salen
        # del detalle de cada partido via get_match_lineups.)
        logger.info("365scores get_players: rosters no disponibles via API; usar ESPN")
        return []

    def get_matches(self, season_id: int = None) -> List[Dict]:
        # Detecta la temporada vigente (seasonNum mas frecuente en fixtures)
        # para NO mezclar torneos (ej. Clausura vs Apertura).
        current_season = season_id
        try:
            fixtures = self._get_json("games/fixtures/", {"competitions": COMPETITION_ID})
            if current_season is None:
                from collections import Counter
                counts = Counter(g.get("seasonNum") for g in fixtures.get("games", []) if g.get("seasonNum") is not None)
                current_season = counts.most_common(1)[0][0] if counts else None
        except Exception as e:
            logger.warning(f"365scores fixtures fallo: {e}")
            fixtures = {"games": []}

        matches = {}
        sources = [fixtures]
        try:
            sources.append(self._get_json("games/results/", {"competitions": COMPETITION_ID}))
        except Exception as e:
            logger.warning(f"365scores results fallo: {e}")

        for data in sources:
            for g in data.get("games", []):
                gid = g.get("id")
                if not gid or gid in matches:
                    continue
                # Filtra a la temporada vigente (Apertura 2026)
                if current_season is not None and g.get("seasonNum") != current_season:
                    continue
                home = g.get("homeCompetitor", {})
                away = g.get("awayCompetitor", {})
                hs = home.get("score")
                as_ = away.get("score")
                matches[gid] = {
                    "event_id": gid,
                    "home_team_id": int(home.get("id")) if home.get("id") else None,
                    "away_team_id": int(away.get("id")) if away.get("id") else None,
                    "home_team": home.get("name"),
                    "away_team": away.get("name"),
                    "home_score": int(hs) if isinstance(hs, (int, float)) and hs >= 0 else None,
                    "away_score": int(as_) if isinstance(as_, (int, float)) and as_ >= 0 else None,
                    "match_date": _parse_date(g.get("startTime")),
                    "status": _status_from_group(g),
                    "week": g.get("roundNum"),
                    "season_num": g.get("seasonNum"),
                }
        return list(matches.values())

    # ---------- Detalle por partido ----------
    def _game_raw(self, game_id) -> Dict:
        return self._get_json("game/", {"gameId": game_id}).get("game", {})

    def get_game(self, game_id) -> Dict:
        """Detalle crudo del partido (un request). Util para extraer en una sola
        llamada el arbitro, las alineaciones, eventos y las stats por jugador."""
        return self._game_raw(game_id)

    def get_match_info(self, game_id, game: Dict = None) -> Dict:
        """Ficha del partido: sede (estadio), arbitro y cuerpo arbitral,
        marcador, estado, jornada y temporada. El arbitro (officials) es un
        dato que ESPN no expone y suele interesar mucho a los aficionados.

        Acepta un `game` ya descargado para evitar pedir el detalle dos veces."""
        game = game if game is not None else self._game_raw(game_id)
        home = game.get("homeCompetitor", {}) or {}
        away = game.get("awayCompetitor", {}) or {}
        venue = game.get("venue") or {}
        officials = [
            {"name": o.get("name"), "id": o.get("id")}
            for o in (game.get("officials") or [])
            if o.get("name")
        ]
        referee = officials[0]["name"] if officials else None
        return {
            "game_id": game_id,
            "home_team": home.get("name"),
            "away_team": away.get("name"),
            "home_score": home.get("score") if isinstance(home.get("score"), (int, float)) and home.get("score") >= 0 else None,
            "away_score": away.get("score") if isinstance(away.get("score"), (int, float)) and away.get("score") >= 0 else None,
            "status": _status_from_group(game),
            "start_time": game.get("startTime"),
            "round": game.get("roundNum"),
            "season_num": game.get("seasonNum"),
            "venue": venue.get("name"),
            "referee": referee,
            "officials": officials,
        }

    def get_match_lineups(self, game_id) -> Dict:
        """Alineaciones con formacion, posiciones en cancha (x/y) y ratings."""
        game = self._game_raw(game_id)
        members = {m["id"]: m for m in game.get("members", [])}
        teams = []
        for side in ("homeCompetitor", "awayCompetitor"):
            c = game.get(side, {})
            lu = c.get("lineups") or {}
            players = []
            for m in lu.get("members", []):
                info = members.get(m.get("id"), {})
                pos = m.get("position", {}) or {}
                yard = m.get("yardFormation", {}) or {}
                players.append({
                    "player_id": int(m["id"]) if m.get("id") else None,
                    "name": info.get("name") or info.get("shortName"),
                    "jersey": info.get("jerseyNumber"),
                    "position": pos.get("name"),
                    "starter": m.get("status") == 1 or m.get("statusText") == "Starting",
                    "rating": m.get("ranking"),
                    "field_line": yard.get("line"),
                    "field_side": yard.get("fieldSide"),
                })
            teams.append({
                "team_name": c.get("name"),
                "home_away": "home" if side == "homeCompetitor" else "away",
                "formation": lu.get("formation"),
                "status": lu.get("status"),
                "players": players,
            })
        return {"game_id": game_id, "teams": teams}

    def get_match_events(self, game_id) -> List[Dict]:
        """Eventos: goles, tarjetas (amarilla/roja), cambios y goles anulados."""
        game = self._game_raw(game_id)
        members = {m["id"]: m["name"] for m in game.get("members", [])}
        home = game.get("homeCompetitor", {})
        away = game.get("awayCompetitor", {})
        team_by_id = {home.get("id"): home.get("name"), away.get("id"): away.get("name")}
        cat_map = {
            EVENT_GOAL: "goal",
            EVENT_YELLOW: "yellow_card",
            EVENT_RED: "red_card",
            EVENT_GOAL_DISALLOWED: "goal_disallowed",
            EVENT_SUBSTITUTION: "substitution",
        }
        events = []
        for e in game.get("events", []):
            et = e.get("eventType", {}) or {}
            events.append({
                "category": cat_map.get(et.get("id"), "other"),
                "type": et.get("name"),
                "subtype": et.get("subTypeName"),
                "minute": e.get("gameTimeDisplay") or (f"{int(e['gameTime'])}'" if e.get("gameTime") else None),
                "team_name": team_by_id.get(e.get("competitorId")),
                "player": members.get(e.get("playerId")),
                "is_major": e.get("isMajor", False),
            })
        return events

    def get_match_cards(self, game_id) -> List[Dict]:
        return [e for e in self.get_match_events(game_id)
                if e["category"] in ("yellow_card", "red_card")]

    # ---------- Joyitas: estadisticas por jugador ----------
    def get_match_player_stats(self, game_id, game: Dict = None) -> Dict:
        """Estadisticas COMPLETAS por jugador en un partido: minutos, goles,
        asistencias, xG, xA, remates, pases completados, regates, duelos,
        intercepciones, toques, rating (ranking)... para TODOS los jugadores
        de la alineacion (no solo los que anotan). ESPN no expone este detalle.

        Acepta un `game` ya descargado para evitar pedir el detalle dos veces.
        Cada jugador trae `stats` (nombre->valor, en espanol) y `stats_by_type`
        (id_de_metrica->valor), util para parsear sin depender del idioma."""
        game = game if game is not None else self._game_raw(game_id)
        members = {m["id"]: m for m in game.get("members", [])}
        teams = []
        for side in ("homeCompetitor", "awayCompetitor"):
            c = game.get(side, {}) or {}
            lu = c.get("lineups") or {}
            players = []
            for m in lu.get("members", []):
                info = members.get(m.get("id"), {})
                pos = m.get("position", {}) or {}
                raw_stats = m.get("stats") or []
                # Las stats vienen como lista de {type, name, value}; las volvemos
                # dos dicts: por nombre (consumo humano) y por type (parseo robusto).
                stats = {s.get("name"): s.get("value") for s in raw_stats if s.get("name")}
                stats_by_type = {s.get("type"): s.get("value") for s in raw_stats if s.get("type") is not None}
                players.append({
                    "player_id": int(m["id"]) if m.get("id") else None,
                    "name": info.get("name") or info.get("shortName"),
                    "jersey": info.get("jerseyNumber"),
                    "position": pos.get("name"),
                    "starter": m.get("status") == 1 or m.get("statusText") == "Starting",
                    "rating": m.get("ranking"),
                    "stats": stats,
                    "stats_by_type": stats_by_type,
                })
            teams.append({
                "team_id": int(c["id"]) if c.get("id") else None,
                "team_name": c.get("name"),
                "home_away": "home" if side == "homeCompetitor" else "away",
                "formation": lu.get("formation"),
                "players": players,
            })
        return {"game_id": game_id, "teams": teams}

    def _season_leaders(self, key: str) -> List[Dict]:
        data = self._get_json("stats/", {"competitions": COMPETITION_ID}).get("stats", {})
        out = []
        for c in data.get(key, []) or []:
            rows = []
            for row in c.get("rows", []):
                e = row.get("entity", {}) or {}
                value = (row.get("stats") or [{}])[0].get("value")
                rows.append({
                    "rank": (row.get("position", 0) or 0) + 1,
                    "id": int(e["id"]) if e.get("id") else None,
                    "name": e.get("name"),
                    "team_id": int(e["competitorId"]) if e.get("competitorId") else None,
                    "position": e.get("positionName"),
                    "value": value,
                    "note": row.get("secondaryStatName"),
                })
            out.append({"category_id": c.get("id"), "category": c.get("name"), "leaders": rows})
        return out

    def get_player_season_leaders(self, category_id: int = None) -> List[Dict]:
        """Lideres de temporada por jugador en 16 categorias: goles, goles
        esperados (xG), asistencias, xA, goles+asistencias, penales, barridas,
        intercepciones, tarjetas rojas/amarillas, valla invicta, goles recibidos,
        salvadas y penales atajados. Un solo request (no raspa partido por partido)."""
        leaders = self._season_leaders("athletesStats")
        if category_id is not None:
            leaders = [c for c in leaders if c.get("category_id") == category_id]
        return leaders

    def get_team_season_leaders(self, category_id: int = None) -> List[Dict]:
        """Lideres de temporada por equipo (goles, posesion, etc.)."""
        leaders = self._season_leaders("competitorsStats")
        if category_id is not None:
            leaders = [c for c in leaders if c.get("category_id") == category_id]
        return leaders
