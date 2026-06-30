from datetime import datetime, timedelta
import logging
import os
from typing import List, Dict, Any
from app.scrapers.factory import get_scraper
from app.scrapers.news_scraper import fetch_news
from app.scrapers.sync_all_stats import sync_all_stats
from app.scrapers.sofascore_scraper import get_events as get_sofascore_events
from app.scrapers import extras_scraper
from app.season import current_tournament, tournament_from_matches
from app import models

logger = logging.getLogger(__name__)

def _validate_season(detected_tournament: str, detected_year: int):
    """Red de seguridad: verifica que los datos detectados correspondan al
    torneo/ano esperado ANTES de tocar la BD. Si no coinciden, se aborta el
    sync para no sobreescribir datos buenos con los de un torneo equivocado.

    El esperado se calcula de la fecha del sistema, pero puede forzarse con
    variables de entorno (utiles para pruebas o casos borde de calendario):
      - EXPECTED_SEASON_YEAR (p. ej. "2026")
      - EXPECTED_TOURNAMENT  (p. ej. "Apertura")
    """
    exp_tournament, exp_year = current_tournament()
    if os.getenv("EXPECTED_SEASON_YEAR"):
        try:
            exp_year = int(os.getenv("EXPECTED_SEASON_YEAR"))
        except ValueError:
            logger.warning("EXPECTED_SEASON_YEAR no es un entero valido; se ignora")
    if os.getenv("EXPECTED_TOURNAMENT"):
        exp_tournament = os.getenv("EXPECTED_TOURNAMENT")

    # El ano es la senal mas fuerte: si no coincide, abortamos.
    if detected_year != exp_year:
        raise ValueError(
            f"Sync abortado: ano detectado en los datos ({detected_tournament} "
            f"{detected_year}) != esperado ({exp_tournament} {exp_year}). "
            f"Se conservan los datos previos. Si es intencional, define "
            f"EXPECTED_SEASON_YEAR={detected_year}."
        )

    # Diferencia de torneo (mismo ano): solo advertencia (casos borde de calendario).
    if detected_tournament != exp_tournament:
        logger.warning(
            f"Torneo detectado ({detected_tournament}) distinto al esperado "
            f"({exp_tournament}) para {exp_year}; se continua pero revisa la fuente."
        )

def calculate_week_numbers(matches: List[Dict[str, Any]]):
    """Asigna numeros de jornada basandose en la fecha.
    La jornada de Liga MX va de viernes a jueves."""
    matches_with_date = [m for m in matches if m.get("match_date")]
    if not matches_with_date:
        return

    def week_start(date):
        days_since_friday = (date.weekday() - 4) % 7
        return (date - timedelta(days=days_since_friday)).date()

    matches_with_date.sort(key=lambda m: m["match_date"])

    groups = {}
    for m in matches_with_date:
        ws = week_start(m["match_date"])
        groups.setdefault(ws, []).append(m)

    sorted_weeks = sorted(groups.keys())
    week_number_by_start = {ws: i + 1 for i, ws in enumerate(sorted_weeks)}

    for m in matches_with_date:
        ws = week_start(m["match_date"])
        m["week"] = week_number_by_start[ws]

def _teams_match(name1: str, name2: str) -> bool:
    """Compara nombres de equipos de ESPN y SofaScore."""
    if not name1 or not name2:
        return False
    n1 = name1.lower().replace("fc", "").replace("cf", "").replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u").replace("ü", "u").strip()
    n2 = name2.lower().replace("fc", "").replace("cf", "").replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u").replace("ü", "u").strip()
    return n1 in n2 or n2 in n1 or n1.split()[0] in n2 or n2.split()[0] in n1

def _sync_sofascore_event_ids(db):
    """Busca y guarda sofascore_event_id para cada partido."""
    try:
        sofascore_events = get_sofascore_events()
        logger.info(f"SofaScore events found: {len(sofascore_events)}")
        
        matches = db.query(models.Match).all()
        updated = 0
        
        for match in matches:
            home_team = match.home_team.name if match.home_team else None
            away_team = match.away_team.name if match.away_team else None
            
            if not home_team or not away_team:
                continue
            
            for event in sofascore_events:
                event_home = event.get("homeTeam", {}).get("name", "")
                event_away = event.get("awayTeam", {}).get("name", "")
                
                if _teams_match(home_team, event_home) and _teams_match(away_team, event_away):
                    match.sofascore_event_id = event.get("id")
                    db.add(match)
                    updated += 1
                    break
        
        db.commit()
        logger.info(f"SofaScore event IDs updated: {updated}")
    except Exception as e:
        logger.warning(f"SofaScore event ID sync failed: {e}")

def _enrich_team_assets(db):
    """Enriquece equipos y estadios con datos de TheSportsDB (cruzando por
    idESPN): ano de fundacion, escudo (si falta) y capacidad del estadio.
    Fuente complementaria, no critica."""
    try:
        assets = extras_scraper.get_team_assets()
        if not assets:
            return
        by_espn = {a["espn_team_id"]: a for a in assets if a.get("espn_team_id")}
        updated_teams = 0
        updated_stadiums = 0
        for team in db.query(models.Team).all():
            a = by_espn.get(team.id)
            if not a:
                continue
            if a.get("founded") and not team.founded:
                team.founded = a["founded"]
            if a.get("badge") and not team.logo_url:
                team.logo_url = a["badge"]
            db.add(team)
            updated_teams += 1
            if team.stadium and a.get("stadium_capacity") and not team.stadium.capacity:
                team.stadium.capacity = a["stadium_capacity"]
                db.add(team.stadium)
                updated_stadiums += 1
        db.commit()
        logger.info(f"TheSportsDB enrich: {updated_teams} equipos, {updated_stadiums} estadios")
    except Exception as e:
        db.rollback()
        logger.warning(f"Enriquecimiento TheSportsDB fallo (no critico): {e}")


def run_sync(db, source: str = "espn"):
    """Ejecuta la sincronizacion completa de datos.

    Estrategia segura:
      1. FETCH: se descargan TODOS los datos externos a memoria primero.
         Si alguna fuente critica falla, se aborta sin tocar la BD,
         conservando los datos previos intactos.
      2. WRITE: borrado + insercion dentro de UNA sola transaccion.
         Si la escritura falla, se hace rollback y los datos viejos quedan.
      3. ENRICH: stats avanzados, SofaScore y noticias se ejecutan de forma
         aislada; un fallo en estas etapas NO invalida el sync principal.
    """
    logger.info(f"Iniciando sincronizacion desde {source}")
    scraper = get_scraper(source)

    # -------- FASE 1: FETCH (sin tocar la BD) --------
    # Si algo critico falla aqui, abortamos antes de borrar nada.
    try:
        raw_stadiums = scraper.get_stadiums()
        raw_teams = scraper.get_teams()
        raw_players = scraper.get_players()
        raw_matches = scraper.get_matches()
        raw_standings = scraper.get_standings()
    except Exception as e:
        logger.error(f"Sync abortado: fallo al obtener datos de {source}: {e}. "
                     f"Los datos previos se conservan intactos.")
        raise

    if not raw_teams or not raw_matches:
        logger.error("Sync abortado: el scraper no devolvio equipos/partidos. "
                     "Los datos previos se conservan intactos.")
        raise ValueError("Datos insuficientes del scraper; se aborta para no vaciar la BD")

    calculate_week_numbers(raw_matches)
    # El torneo/ano se deduce de las fechas REALES de los partidos cargados
    # (p. ej. partidos jul-dic 2026 => "Apertura 2026"), no del mes actual.
    tournament, current_year = tournament_from_matches(raw_matches)
    logger.info(f"Temporada detectada de los datos: {tournament} {current_year}")

    # Red de seguridad: aborta (sin tocar la BD) si no es el torneo/ano esperado.
    _validate_season(tournament, current_year)

    # -------- FASE 2: WRITE (una sola transaccion) --------
    try:
        # Limpiar tablas core.
        # IMPORTANTE: se borran primero las tablas HIJAS (con FK) y luego las
        # PADRES, para no violar claves foraneas en Postgres. El bulk delete
        # de SQLAlchemy NO dispara el cascade del ORM, asi que el orden importa.
        for m in [
            models.MatchEvent,
            models.MatchLineup,
            models.MatchStat,
            models.PlayerStat,
            models.Standing,
            models.Match,
            models.Player,
            models.Week,
            models.Team,
            models.Stadium,
            models.Season,
        ]:
            db.query(m).delete()

        # Estadios
        smap = {}
        for s in raw_stadiums:
            st = models.Stadium(**s)
            db.add(st)
            db.flush()
            smap[s["name"]] = st.id

        # Equipos
        tmap = {}
        team_count = 0
        for t in raw_teams:
            tm = models.Team(
                id=t["id"],
                name=t["name"],
                short_name=t.get("short_name"),
                city=t.get("city"),
                colors=t.get("colors"),
                founded=t.get("founded"),
                logo_url=t.get("logo_url"),
                stadium_id=smap.get(t.get("stadium_name")),
            )
            db.add(tm)
            db.flush()
            tmap[t["name"]] = tm.id
            tmap[t["id"]] = tm.id
            team_count += 1

        # Jugadores
        for p in raw_players:
            db.add(
                models.Player(
                    id=p["id"],
                    name=p["name"],
                    position=p.get("position"),
                    number=p.get("number"),
                    nationality=p.get("nationality"),
                    birth_date=p.get("birth_date"),
                    photo_url=p.get("photo_url"),
                    team_id=tmap.get(p.get("team_name")),
                )
            )

        # Temporada (etiquetada por torneo: p. ej. "Apertura 2026")
        sn = models.Season(name=f"{tournament} {current_year}", year=current_year, tournament_type=tournament)
        db.add(sn)
        db.flush()

        # Partidos
        for m in raw_matches:
            hid = tmap.get(m.get("home_team_id")) or tmap.get(m.get("home_team"))
            aid = tmap.get(m.get("away_team_id")) or tmap.get(m.get("away_team"))
            if hid and aid:
                db.add(
                    models.Match(
                        season_id=sn.id,
                        home_team_id=hid,
                        away_team_id=aid,
                        match_date=m.get("match_date"),
                        home_score=m.get("home_score"),
                        away_score=m.get("away_score"),
                        status=m.get("status", "scheduled"),
                        week_number=m.get("week"),
                    )
                )

        # Standings
        for s in raw_standings:
            db.add(
                models.Standing(
                    season_id=sn.id,
                    team_id=tmap.get(s.get("team_name")),
                    position=s["position"],
                    played=s["played"],
                    won=s["won"],
                    drawn=s["drawn"],
                    lost=s["lost"],
                    goals_for=s["goals_for"],
                    goals_against=s["goals_against"],
                    goal_difference=s["goals_for"] - s["goals_against"],
                    points=s["points"],
                )
            )

        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Sync fallo durante la escritura, rollback aplicado. "
                     f"Los datos previos se conservan: {e}")
        raise

    # -------- FASE 3: ENRICH (aislado, no critico) --------
    # Escudos, fundacion y capacidad via TheSportsDB (cruce por idESPN)
    _enrich_team_assets(db)

    # Stats avanzados
    try:
        sync_all_stats(db, raw_matches, scraper, tmap, str(current_year))
    except Exception as e:
        db.rollback()
        logger.warning(f"sync_all_stats fallo (no critico): {e}")

    # SofaScore event IDs (puede fallar por bloqueo de Cloudflare/403)
    _sync_sofascore_event_ids(db)

    # News sync (aislado para no invalidar el resto)
    try:
        news_items = fetch_news(limit=50)
        db.query(models.News).delete()
        for n in news_items:
            db.add(models.News(**n))
        db.commit()
    except Exception as e:
        db.rollback()
        logger.warning(f"Sync de noticias fallo (no critico): {e}")

    logger.info("Sincronizacion completada")

    return {
        "stadiums": len(smap),
        "teams": team_count,
        "players": len(db.query(models.Player).all()),
        "matches": len(db.query(models.Match).all()),
        "season": f"{tournament} {current_year}",
    }


def run_sync_with_log(db, source: str = "espn"):
    """Ejecuta run_sync y registra el resultado (exito o error) en sync_logs.
    Devuelve el resultado del sync; relanza la excepcion si falla."""
    started = datetime.utcnow()
    try:
        result = run_sync(db, source)
    except Exception as e:
        try:
            db.rollback()
            db.add(models.SyncLog(
                source=source, status="error", detail=str(e)[:500],
                started_at=started,
                duration_seconds=(datetime.utcnow() - started).total_seconds(),
            ))
            db.commit()
        except Exception:
            db.rollback()
        raise
    try:
        db.add(models.SyncLog(
            source=source, status="success", detail="ok",
            season=result.get("season"),
            teams=result.get("teams"), players=result.get("players"),
            matches=result.get("matches"),
            started_at=started,
            duration_seconds=(datetime.utcnow() - started).total_seconds(),
        ))
        db.commit()
    except Exception:
        db.rollback()
    return result
