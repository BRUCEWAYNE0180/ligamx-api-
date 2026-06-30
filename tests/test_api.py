def test_root(client):
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["status"] == "running"


def test_health(client):
    assert client.get("/health").status_code == 200


def test_teams_incluye_logo_y_estadio(client, seeded):
    r = client.get("/teams")
    assert r.status_code == 200
    ame = [t for t in r.json() if t["id"] == 1][0]
    assert ame["logo_url"] == "http://x/a.png"
    assert ame["founded"] == 1916
    assert ame["stadium"]["capacity"] == 50000


def test_standings(client, seeded):
    r = client.get("/standings")
    assert r.status_code == 200
    assert r.json()[0]["team"]["name"] == "América"


def test_liguilla(client, seeded):
    r = client.get("/liguilla")
    assert r.status_code == 200
    body = r.json()
    assert "liguilla_directa" in body and "play_in" in body and "eliminados" in body


def test_team_form(client, seeded):
    r = client.get("/teams/1/form").json()
    assert r["form"] == "W"
    assert r["summary"]["W"] == 1
    assert r["played"] == 1


def test_h2h_summary(client, seeded):
    r = client.get("/h2h/1/2/summary").json()
    assert r["played"] == 1
    assert r["team1"]["wins"] == 1
    assert r["team2"]["wins"] == 0
    assert r["team1"]["goals"] == 2
    assert r["draws"] == 0


def test_player_search(client, seeded):
    r = client.get("/players/search", params={"q": "henry"}).json()
    assert len(r) == 1 and r[0]["name"] == "Henry Martín"
    # busqueda ignora acentos y filtra por nacionalidad
    r2 = client.get("/players/search", params={"q": "martin"}).json()
    assert len(r2) == 1
    r3 = client.get("/players/search", params={"nationality": "mexico"}).json()
    assert len(r3) == 1


def test_season_endpoint(client, seeded):
    r = client.get("/season").json()
    assert r["loaded_season"] == "Apertura 2026"
    assert r["tournament_type"] == "Apertura"
    assert r["finished_matches"] == 1
    assert r["total_matches"] == 1


def test_sync_requiere_api_key(client):
    # sin header -> 422 (falta X-API-Key)
    assert client.post("/sync", params={"source": "demo"}).status_code == 422
    # key incorrecta -> 403
    assert client.post("/sync", params={"source": "demo"},
                       headers={"X-API-Key": "wrong"}).status_code == 403


def test_sync_status_sin_datos(client):
    r = client.get("/sync/status").json()
    assert r["has_data"] is False
    assert r["last_sync"] is None
    assert r["last_successful_sync"] is None



def test_match_timeline(client, seeded):
    r = client.get("/matches/1/timeline")
    assert r.status_code == 200
    eventos = r.json()
    assert len(eventos) == 2
    # ordenados por minuto: gol (23') antes que tarjeta (55')
    assert eventos[0]["event_type"] == "goal" and eventos[0]["event_time"] == 23
    tipos = {e["event_type"] for e in eventos}
    assert "yellow_card" in tipos


def test_match_squad(client, seeded):
    r = client.get("/matches/1/squad").json()
    equipos = {t["team_id"]: t for t in r["teams"]}
    assert 1 in equipos
    assert equipos[1]["starters"][0]["player_name"] == "Henry Martín"
    assert equipos[1]["starters"][0]["jersey_number"] == 21


def test_match_full(client, seeded):
    r = client.get("/matches/1/full").json()
    assert r["id"] == 1
    assert r["score"] == {"home": 2, "away": 1}
    assert len(r["timeline"]) == 2
    assert len(r["lineups"]) >= 1
    assert len(r["stats"]) == 1
    assert r["stats"][0]["possession"] == 58.0


def test_match_full_404(client, seeded):
    assert client.get("/matches/999/full").status_code == 404



# ---------- Fase C: stats por jugador (365Scores) y arbitros ----------

def test_match_full_incluye_referee_y_venue(client, seeded, db):
    from app import models
    m = db.get(models.Match, 1)
    m.referee = "César Ramos"
    db.commit()
    r = client.get("/matches/1/full").json()
    assert r["referee"] == "César Ramos"
    assert "venue" in r  # presente aunque sea None


def test_365_player_leaders(client, monkeypatch):
    from app.scrapers import scores365_scraper
    fake = [{"category_id": 1, "category": "Goles",
             "leaders": [{"rank": 1, "name": "Paulinho", "value": "14", "team_id": 2078}]}]
    monkeypatch.setattr(scores365_scraper.Scores365Scraper,
                        "get_player_season_leaders",
                        lambda self, category_id=None: fake)
    r = client.get("/365scores/leaders")
    assert r.status_code == 200
    body = r.json()
    assert body[0]["category"] == "Goles"
    assert body[0]["leaders"][0]["name"] == "Paulinho"


def test_365_match_player_stats(client, monkeypatch):
    from app.scrapers import scores365_scraper
    fake = {"game_id": 123, "teams": [{
        "team_name": "Pumas", "formation": "4-3-3",
        "players": [{"name": "Carrasquilla", "rating": 6.8,
                     "stats": {"Minutes": "90'", "Total Remates": "3"}}],
    }]}
    monkeypatch.setattr(scores365_scraper.Scores365Scraper,
                        "get_match_player_stats",
                        lambda self, game_id: fake)
    r = client.get("/365scores/matches/123/player-stats")
    assert r.status_code == 200
    body = r.json()
    assert body["teams"][0]["players"][0]["rating"] == 6.8
    assert body["teams"][0]["players"][0]["stats"]["Minutes"] == "90'"



# ---------- Fase D: stats por jugador persistidas en BD ----------

def test_stat_parsers():
    from app.services.sync_service import _stat_int, _stat_float, _stat_fraction
    assert _stat_int("58'") == 58
    assert _stat_int("0") == 0
    assert _stat_int(None) is None
    assert _stat_float("0.05") == 0.05
    assert _stat_float("90'") == 90.0
    assert _stat_fraction("21/26 (81%)") == (21, 26)
    assert _stat_fraction("5") == (5, None)
    assert _stat_fraction(None) == (None, None)


def _seed_player_match_stats(db):
    from app import models
    db.add(models.PlayerMatchStat(
        match_id=1, player_id=999, player_name="Henry Martín", team_id=1, team_name="América",
        season="Apertura 2026", starter=1, minutes=90, goals=2, assists=1, shots=4, xg=1.2, xa=0.3,
        touches=60, interceptions=1, rating=8.5, stats={"Toques": "60"}))
    db.add(models.PlayerMatchStat(
        match_id=1, player_id=998, player_name="Rival X", team_id=2, team_name="Chivas",
        season="Apertura 2026", starter=1, minutes=90, goals=0, assists=0, rating=6.1))
    db.commit()


def test_match_player_stats_db(client, seeded, db):
    _seed_player_match_stats(db)
    r = client.get("/matches/1/player-stats").json()
    teams = {t["team_id"]: t for t in r["teams"]}
    assert 1 in teams and 2 in teams
    p = teams[1]["players"][0]
    assert p["player_name"] == "Henry Martín"
    assert p["goals"] == 2 and p["assists"] == 1 and p["rating"] == 8.5


def test_player_season_stats(client, seeded, db):
    _seed_player_match_stats(db)
    r = client.get("/players/10/season-stats").json()
    assert r["appearances"] == 1
    assert r["goals"] == 2 and r["assists"] == 1
    assert r["minutes"] == 90 and r["avg_rating"] == 8.5


def test_player_match_stats_history(client, seeded, db):
    _seed_player_match_stats(db)
    r = client.get("/players/10/match-stats").json()
    assert len(r) == 1 and r[0]["goals"] == 2 and r[0]["match_id"] == 1


def test_players_season_leaders(client, seeded, db):
    _seed_player_match_stats(db)
    r = client.get("/players/season-leaders", params={"stat": "goals"}).json()
    assert r[0]["player"] == "Henry Martín" and r[0]["value"] == 2
    # rating con filtro de apariciones
    r2 = client.get("/players/season-leaders", params={"stat": "rating"}).json()
    assert r2[0]["player"] == "Henry Martín" and r2[0]["value"] == 8.5



# ---------- Histórico multi-temporada ----------

def _season_payload():
    from datetime import datetime
    return dict(
        stadiums=[{"name": "Azteca", "city": "CDMX"}],
        teams=[{"id": 1, "name": "América"}, {"id": 2, "name": "Chivas"}],
        players=[{"id": 10, "name": "Henry Martín", "team_name": "América"}],
        matches=[{"home_team": "América", "away_team": "Chivas", "home_team_id": 1,
                  "away_team_id": 2, "status": "finished", "home_score": 1, "away_score": 0,
                  "match_date": datetime(2025, 8, 1), "event_id": "E1"}],
        standings=[{"team_name": "América", "position": 1, "played": 1, "won": 1, "drawn": 0,
                    "lost": 0, "goals_for": 1, "goals_against": 0, "points": 3}],
    )


def test_write_season_data_no_destructivo(db):
    from app import models
    from app.services.sync_service import _write_season_data
    # Dos torneos del MISMO año deben coexistir (clave = etiqueta, no solo año)
    _write_season_data(db, tournament="Clausura", year=2026, **_season_payload())
    db.commit()
    _write_season_data(db, tournament="Apertura", year=2026, **_season_payload())
    db.commit()
    assert db.query(models.Season).count() == 2
    assert db.query(models.Match).count() == 2
    assert db.query(models.Team).count() == 2
    assert db.query(models.Player).count() == 1  # upsert por id, no duplica
    # Re-sincronizar un torneo NO duplica ni borra el otro
    _write_season_data(db, tournament="Clausura", year=2026, **_season_payload())
    db.commit()
    assert db.query(models.Season).count() == 2
    assert db.query(models.Match).count() == 2
    assert db.query(models.Team).count() == 2


def test_seasons_y_standings_por_temporada(client, seeded, db):
    from app import models
    db.add(models.Season(id=2, name="Clausura 2026", year=2026, tournament_type="Clausura"))
    db.flush()
    db.add(models.Standing(season_id=2, team_id=1, position=1, played=1, won=0, drawn=1,
                           lost=0, goals_for=0, goals_against=0, goal_difference=0, points=1))
    db.commit()
    names = {s["name"] for s in client.get("/seasons").json()}
    assert {"Apertura 2026", "Clausura 2026"} <= names
    # Por defecto: temporada vigente (Apertura 2026) -> 2 filas sembradas
    assert len(client.get("/standings").json()) == 2
    # Filtrada a Clausura 2026 -> 1 fila
    assert len(client.get("/standings", params={"season": "Clausura 2026"}).json()) == 1



# ---------- Backfill de temporadas pasadas ----------

def test_compute_standings_from_matches():
    from app.services.sync_service import compute_standings_from_matches
    ms = [
        {"status": "finished", "home_team": "A", "away_team": "B", "home_score": 2, "away_score": 0},
        {"status": "finished", "home_team": "B", "away_team": "A", "home_score": 1, "away_score": 1},
        {"status": "scheduled", "home_team": "A", "away_team": "B", "home_score": None, "away_score": None},
    ]
    table = {r["team_name"]: r for r in compute_standings_from_matches(ms)}
    assert table["A"]["points"] == 4 and table["A"]["played"] == 2 and table["A"]["position"] == 1
    assert table["A"]["goal_difference"] == 2
    assert table["B"]["points"] == 1 and table["B"]["position"] == 2


def test_run_backfill_crea_temporada_pasada(db, monkeypatch):
    from datetime import datetime
    from app import models
    from app.services import sync_service

    class _Fake:
        def get_stadiums(self):
            return [{"name": "Azteca", "city": "CDMX"}]
        def get_teams(self):
            return [{"id": 1, "name": "América"}, {"id": 2, "name": "Chivas"}]
        def get_players(self):
            return [{"id": 10, "name": "Henry Martín", "team_name": "América"}]
        def get_matches(self, season_id=None, tournament=None):
            return [
                {"event_id": "E1", "home_team": "América", "away_team": "Chivas", "home_team_id": 1,
                 "away_team_id": 2, "home_score": 3, "away_score": 1, "status": "finished",
                 "match_date": datetime(2025, 8, 1)},
                {"event_id": "E2", "home_team": "Chivas", "away_team": "América", "home_team_id": 2,
                 "away_team_id": 1, "home_score": 0, "away_score": 0, "status": "finished",
                 "match_date": datetime(2025, 8, 8)},
            ]

    monkeypatch.setattr(sync_service, "get_scraper", lambda source: _Fake())
    res = sync_service.run_backfill(db, 2025, "Apertura", "espn")
    assert res["season"] == "Apertura 2025"
    assert res["finished_matches"] == 2
    assert db.query(models.Season).filter_by(name="Apertura 2025").count() == 1
    st = (db.query(models.Standing).join(models.Season)
          .filter(models.Season.name == "Apertura 2025")
          .order_by(models.Standing.position).all())
    assert st[0].team.name == "América" and st[0].points == 4  # victoria + empate
    assert st[1].team.name == "Chivas" and st[1].points == 1


def test_backfill_valida_torneo(client):
    r = client.post("/sync/backfill", params={"year": 2025, "tournament": "Liguilla"},
                    headers={"X-API-Key": "test-key"})
    assert r.status_code == 422



# ---------- Liguilla: bracket oficial ----------

def test_liguilla_bracket(client, db):
    from app import models
    db.add(models.Season(id=1, name="Apertura 2026", year=2026, tournament_type="Apertura"))
    db.flush()
    for pos in range(1, 11):
        db.add(models.Team(id=pos, name=f"Equipo {pos}"))
        db.add(models.Standing(season_id=1, team_id=pos, position=pos, played=17, won=10, drawn=0,
                               lost=7, goals_for=20, goals_against=10, goal_difference=10,
                               points=40 - pos))
    db.commit()

    b = client.get("/liguilla/bracket").json()
    assert b["season"] == "Apertura 2026"
    assert len(b["qualified_direct"]) == 6
    assert len(b["play_in_teams"]) == 4
    # Play-In: 7º vs 8º y 9º vs 10º
    assert b["play_in"]["game_1"]["home"]["position"] == 7
    assert b["play_in"]["game_1"]["away"]["position"] == 8
    assert b["play_in"]["game_2"]["home"]["position"] == 9
    # Cuartos sembrados correctamente
    qf = {q["series"]: q for q in b["quarterfinals"]}
    assert qf["C1"]["high_seed"]["position"] == 1
    assert qf["C3"]["high_seed"]["position"] == 3 and qf["C3"]["low_seed"]["position"] == 6
    assert qf["C4"]["high_seed"]["position"] == 4 and qf["C4"]["low_seed"]["position"] == 5



# ---------- Búsqueda global ----------

def test_search_global(client, seeded):
    # jugador por nombre (ignora acentos)
    r = client.get("/search", params={"q": "henry"}).json()
    assert r["counts"]["players"] == 1
    assert r["players"][0]["name"] == "Henry Martín"
    assert r["players"][0]["team_name"] == "América"
    # equipo (acentos: 'América' coincide con 'amer')
    r2 = client.get("/search", params={"q": "amer"}).json()
    assert any(t["name"] == "América" for t in r2["teams"])
    # estadio sembrado
    r3 = client.get("/search", params={"q": "test"}).json()
    assert any(s["name"] == "Estadio Test" for s in r3["stadiums"])


def test_search_prefijo_primero(client, seeded, db):
    from app import models
    # 'Martín' contiene pero no empieza; 'Mart' como prefijo debe ir antes
    db.add(models.Player(id=11, team_id=1, name="Martina López"))
    db.commit()
    r = client.get("/search", params={"q": "mart"}).json()
    # ambos coinciden; el que EMPIEZA por 'mart' (Martina) va primero
    assert r["players"][0]["name"] == "Martina López"


def test_search_requiere_q(client):
    assert client.get("/search").status_code == 422



# ---------- Seguridad: cabeceras, API key y rate limiting ----------

def test_security_headers(client):
    r = client.get("/health")
    assert r.headers.get("X-Content-Type-Options") == "nosniff"
    assert r.headers.get("X-Frame-Options") == "DENY"
    assert r.headers.get("Referrer-Policy") == "no-referrer"


def test_sync_503_si_no_hay_api_key_configurada(client, monkeypatch):
    monkeypatch.delenv("SYNC_API_KEY", raising=False)
    r = client.post("/sync", params={"source": "demo"}, headers={"X-API-Key": "loquesea"})
    assert r.status_code == 503


def test_rate_limit_devuelve_429():
    # App minima con limite bajo para verificar la integracion de slowapi
    from fastapi import FastAPI, Request
    from fastapi.testclient import TestClient
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded
    from slowapi.middleware import SlowAPIMiddleware

    lim = Limiter(key_func=get_remote_address, default_limits=["2/minute"])
    app = FastAPI()
    app.state.limiter = lim
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

    @app.get("/ping")
    def ping(request: Request):
        return {"ok": True}

    c = TestClient(app)
    assert c.get("/ping").status_code == 200
    assert c.get("/ping").status_code == 200
    assert c.get("/ping").status_code == 429  # tercer request supera 2/minute



# ---------- Streaming en vivo (SSE) ----------

def test_live_stream_sse(client, monkeypatch):
    from app.routers import live
    monkeypatch.setattr(live, "_live_snapshot", lambda: [
        {"event_id": "1", "home_team": "América", "away_team": "Chivas",
         "home_score": 1, "away_score": 0, "status": "live", "clock": "55'"},
    ])
    with client.stream("GET", "/live/stream", params={"interval": 1, "max_seconds": 1}) as r:
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/event-stream")
        got_data = False
        lines = []
        for line in r.iter_lines():
            lines.append(line)
            if "América" in line:
                got_data = True
                break
    blob = "\n".join(lines)
    assert got_data
    assert "event: live" in blob



# ---------- Versionado /v1 ----------

def test_version_endpoint(client):
    r = client.get("/version").json()
    assert r["current"] == "v1"
    assert "v1" in r["available_versions"]


def test_v1_mirrors_root(client, seeded):
    # health y standings disponibles bajo /v1 igual que en la raiz
    assert client.get("/v1/health").status_code == 200
    root = client.get("/standings").json()
    v1 = client.get("/v1/standings").json()
    assert v1 == root
    assert len(v1) == 2
    # un endpoint mas para asegurar el espejo
    assert client.get("/v1/seasons").status_code == 200



# ---------- Observabilidad: métricas ----------

def test_metrics_endpoint(client, seeded):
    # generamos algo de trafico
    client.get("/health")
    client.get("/standings")
    client.get("/matches/1/full")
    m = client.get("/metrics").json()
    assert m["requests"]["total"] >= 3
    assert "2xx" in m["requests"]["by_class"]
    assert "uptime_seconds" in m
    assert "avg" in m["latency_ms"]
    assert "cache" in m
    # las rutas se normalizan a su plantilla, no IDs concretos
    paths = {p["path"] for p in m["top_paths"]}
    assert any("{match_id}" in p for p in paths) or "/standings" in paths


def test_metrics_cuenta_errores(client):
    from app.metrics import metrics
    before = metrics.snapshot()["requests"]["total"]
    client.get("/matches/999999")  # 404
    after = metrics.snapshot()
    assert after["requests"]["total"] > before
    assert after["requests"]["by_class"].get("4xx", 0) >= 1



# ---------- Joyita: estadísticas de equipo por temporada (ESPN) ----------

def test_team_season_stats(client, seeded, monkeypatch):
    from app.scrapers import espn_requests_scraper as espn
    fake = {"team_id": 1, "season_year": 2025, "categories": {
        "defensive": {"interceptions": 154.0, "effectiveTackles": 176.0},
        "goalKeeping": {"cleanSheet": 6.0, "goalsConceded": 23.0},
    }}
    monkeypatch.setattr(espn.ESPNRequestsScraper, "get_team_season_stats",
                        lambda self, team_id, year=None: {**fake, "team_id": team_id, "season_year": year})
    r = client.get("/teams/1/season-stats", params={"season": "Apertura 2025"}).json()
    assert r["season_year"] == 2025  # ano extraido de la etiqueta
    assert r["categories"]["goalKeeping"]["cleanSheet"] == 6.0


def test_team_stats_usa_etiqueta_de_temporada(client, seeded):
    # /teams/{id}/stats ahora resuelve la etiqueta vigente (no el viejo "2026")
    r = client.get("/teams/1/stats").json()
    # la MatchStat sembrada tiene season="Apertura 2026" y team_id=1
    assert r["season"] == "Apertura 2026"
    assert r["matches"] == 1
    assert r["totals"]["shots"] == 12



# ---------- Joyita: shotmap/xG y top performers (365Scores) ----------

def test_365_match_shots(client, monkeypatch):
    from app.scrapers import scores365_scraper
    fake = {
        "game_id": 123, "teams": {"home": "Pumas", "away": "Cruz Azul"},
        "totals": {"home": {"shots": 8, "xg": 0.53, "xgot": 0.3, "goals": 0},
                   "away": {"shots": 12, "xg": 0.95, "xgot": 0.7, "goals": 1}},
        "shots": [{"minute": "6'", "team": "Cruz Azul", "side": "away", "player": "Rotondi",
                   "xg": 0.03, "xgot": 0.11, "body_part": "Pie izquierdo",
                   "outcome": "Atajado", "is_goal": False, "x": 47.9, "y": 75.4}],
    }
    monkeypatch.setattr(scores365_scraper.Scores365Scraper, "get_match_shots",
                        lambda self, game_id: fake)
    r = client.get("/365scores/matches/123/shots").json()
    assert r["totals"]["away"]["xg"] == 0.95
    assert r["shots"][0]["player"] == "Rotondi"
    assert r["shots"][0]["is_goal"] is False


def test_365_top_performers(client, monkeypatch):
    from app.scrapers import scores365_scraper
    fake = {"game_id": 123, "categories": [
        {"category": "Delantero",
         "home": {"player_id": 1, "name": "Morales", "position": "Centro Delantero",
                  "stats": {"Total Remates": "2"}},
         "away": {"player_id": 2, "name": "Otro", "position": "Delantero", "stats": {}}},
    ]}
    monkeypatch.setattr(scores365_scraper.Scores365Scraper, "get_match_top_performers",
                        lambda self, game_id: fake)
    r = client.get("/365scores/matches/123/top-performers").json()
    assert r["categories"][0]["category"] == "Delantero"
    assert r["categories"][0]["home"]["name"] == "Morales"



# ---------- Estadios oficiales 2026 ----------

def test_estadios_oficiales_2026():
    from app.scrapers.espn_requests_scraper import STADIUMS
    # Renombres oficiales del Apertura 2026
    assert STADIUMS[227]["name"] == "Estadio Banorte"          # ex Azteca (América)
    assert STADIUMS[15720]["name"] == "Estadio Libertad Financiera"  # ex Alfonso Lastras (San Luis)
    # No quedaron nombres viejos
    names = {s["name"] for s in STADIUMS.values()}
    assert "Estadio Azteca" not in names
    assert "Estadio Alfonso Lastras" not in names



# ---------- Calendario, noticias 365 y xG de temporada ----------

def test_calendar(client, seeded):
    r = client.get("/calendar").json()
    assert r["total_matches"] == 1
    j1 = r["jornadas"][0]
    assert j1["jornada"] == 1
    m = j1["matches"][0]
    assert m["home_team"]["name"] == "América"
    assert m["away_team"]["name"] == "Chivas"
    assert m["score"] == {"home": 2, "away": 1}
    assert "venue" in m


def test_365_news(client, monkeypatch):
    from app.scrapers import scores365_scraper
    monkeypatch.setattr(scores365_scraper.Scores365Scraper, "get_news",
                        lambda self, limit=30: [{"id": 1, "title": "Fichaje bomba",
                                                 "url": "http://x", "image": "http://i",
                                                 "published_at": "2026-06-30", "is_magazine": False}])
    r = client.get("/365scores/news").json()
    assert r[0]["title"] == "Fichaje bomba"


def test_xg_performance(client, seeded, db):
    _seed_player_match_stats(db)
    r = client.get("/players/xg-performance").json()
    top = r[0]
    assert top["player"] == "Henry Martín"
    assert top["goals"] == 2 and top["xg"] == 1.2
    assert top["diff"] == 0.8  # 2 goles - 1.2 xG (sobre-rendimiento)



# ---------- Noticias con imagen (RSS + 365Scores unificados) ----------

def test_news_incluye_imagen(client, db):
    from datetime import datetime
    from app import models
    db.add(models.News(title="Gol de último minuto", link="http://x/n1",
                       description="...", source="365Scores",
                       image_url="http://img/portada.webp",
                       published_at=datetime(2026, 7, 1)))
    db.commit()
    r = client.get("/news").json()
    assert r[0]["title"] == "Gol de último minuto"
    assert r[0]["image_url"] == "http://img/portada.webp"
    assert r[0]["source"] == "365Scores"



# ---------- xG por equipo, porteros y heatmaps ----------

def test_teams_xg_performance(client, seeded, db):
    _seed_player_match_stats(db)  # Henry (equipo 1): goals=2, xg=1.2
    r = client.get("/teams/xg-performance").json()
    top = r[0]
    assert top["team_id"] == 1
    assert top["goals"] == 2 and top["xg"] == 1.2 and top["diff"] == 0.8
    # no debe colisionar con /teams/{team_id}
    assert client.get("/teams/xg-performance").status_code == 200


def test_365_goalkeepers(client, monkeypatch):
    from app.scrapers import scores365_scraper
    fake = [{"player_id": 1, "name": "Nahuel Guzmán", "team_id": 10,
             "clean_sheets": "7", "goals_conceded": "8", "saves": "3.1", "penalties_saved": "1/2"}]
    monkeypatch.setattr(scores365_scraper.Scores365Scraper, "get_goalkeepers", lambda self: fake)
    r = client.get("/365scores/goalkeepers").json()
    assert r[0]["name"] == "Nahuel Guzmán" and r[0]["clean_sheets"] == "7"


def test_365_heatmaps(client, monkeypatch):
    from app.scrapers import scores365_scraper
    fake = {"game_id": 123, "teams": [{"team_name": "Pumas", "players": [
        {"player_id": 1, "name": "Carrasquilla", "position": "Mediocampista",
         "heatmap_url": "https://heatmap.365scores.com/?x=1"}]}]}
    monkeypatch.setattr(scores365_scraper.Scores365Scraper, "get_match_heatmaps",
                        lambda self, game_id: fake)
    r = client.get("/365scores/matches/123/heatmaps").json()
    assert r["teams"][0]["players"][0]["heatmap_url"].startswith("https://heatmap")



# ---------- Analítica: comparador y predictor ----------

def test_compare_players(client, seeded, db):
    from app import models
    _seed_player_match_stats(db)
    db.add(models.Player(id=11, team_id=2, name="Rival X"))
    db.commit()
    r = client.get("/compare/players", params={"a": 10, "b": 11}).json()
    assert r["a"]["name"] == "Henry Martín" and r["a"]["goals"] == 2
    assert r["a"]["xg"] == 1.2
    assert r["b"]["name"] == "Rival X" and r["b"]["goals"] == 0


def test_compare_teams(client, seeded, db):
    _seed_player_match_stats(db)
    r = client.get("/compare/teams", params={"a": 1, "b": 2}).json()
    assert r["a"]["team_id"] == 1 and r["a"]["standing"]["position"] == 1
    assert r["a"]["xg"] == 1.2
    assert r["b"]["team_id"] == 2


def test_predict_match(client, seeded):
    r = client.get("/predict", params={"home": 1, "away": 2}).json()
    p = r["probabilities"]
    assert abs(p["home_win"] + p["draw"] + p["away_win"] - 1.0) < 0.05
    assert "expected_goals" in r and "most_likely_score" in r
    # equipo 1 (mejor ataque/defensa) y de local debe ser favorito
    assert p["home_win"] > p["away_win"]


def test_predict_sin_datos(client, db):
    from app import models
    db.add(models.Season(id=1, name="Apertura 2026", year=2026, tournament_type="Apertura"))
    db.add(models.Team(id=1, name="A"))
    db.add(models.Team(id=2, name="B"))
    db.commit()
    # sin standings con partidos jugados -> 400
    assert client.get("/predict", params={"home": 1, "away": 2}).status_code == 400



# ---------- Dashboard y readiness ----------

def test_dashboard(client, seeded):
    r = client.get("/dashboard").json()
    assert r["season"] == "Apertura 2026"
    # líder de la tabla = América (posición 1 sembrada)
    assert r["standings_leader"]["team"]["name"] == "América"
    assert r["standings_leader"]["position"] == 1
    # claves presentes (listas, aunque vacías)
    for k in ("top_scorer", "upcoming_matches", "recent_results", "latest_news"):
        assert k in r
    # hay 1 partido finalizado sembrado -> aparece en recent_results
    assert len(r["recent_results"]) == 1


def test_health_ready(client):
    r = client.get("/health/ready")
    assert r.status_code == 200
    body = r.json()
    assert body["ready"] is True
    assert body["checks"]["database"] == "ok"
    assert body["checks"]["redis"] in ("disabled", "ok")



# ---------- Power ranking y perfiles ----------

def test_power_ranking(client, seeded):
    r = client.get("/power-ranking").json()
    assert r["season"] == "Apertura 2026"
    assert len(r["ranking"]) == 2
    for row in r["ranking"]:
        assert 0 <= row["rating"] <= 100
        assert "team" in row and "ppg" in row and "rank" in row


def test_player_profile(client, seeded, db):
    _seed_player_match_stats(db)
    r = client.get("/players/10/profile").json()
    assert r["player"]["name"] == "Henry Martín"
    assert r["player"]["team"]["name"] == "América"
    assert r["season_stats"]["goals"] == 2
    assert r["season_stats"]["xg"] == 1.2
    assert len(r["recent_matches"]) >= 1


def test_team_profile(client, seeded, db):
    _seed_player_match_stats(db)
    r = client.get("/teams/1/profile").json()
    assert r["team"]["name"] == "América"
    assert r["standing"]["position"] == 1
    assert r["xg"] == 1.2
    assert r["squad_size"] >= 1
    assert "form" in r and "last_result" in r



# ---------- Jugadores a seguir ----------

def test_players_to_watch(client, seeded, db):
    _seed_player_match_stats(db)
    r = client.get("/matches/1/players-to-watch").json()
    assert r["season"] == "Apertura 2026"
    assert r["home_team"]["id"] == 1 and r["away_team"]["id"] == 2
    hp = r["home_team"]["players"]
    assert hp and hp[0]["player"] == "Henry Martín"
    assert hp[0]["goals"] == 2 and "reason" in hp[0] and hp[0]["watch_score"] > 0
    ap = r["away_team"]["players"]
    assert ap and ap[0]["player"] == "Rival X"


def test_players_to_watch_sin_datos(client, seeded):
    # match sembrado pero sin player_match_stats -> note y listas vacías
    r = client.get("/matches/1/players-to-watch").json()
    assert r["home_team"]["players"] == [] and r["away_team"]["players"] == []
    assert "note" in r



# ---------- Disciplina: tarjetas acumuladas y suspensiones ----------

def _seed_cards(db):
    """Agrega tarjetas al jugador 'Tarjetero' (equipo 1): 4 amarillas (en riesgo)."""
    from app import models
    for minute in (10, 20, 30, 40):
        db.add(models.MatchEvent(match_id=1, event_type="yellow_card", event_time=minute,
                                 player_name="Tarjetero", team_id=1, team_name="América",
                                 description="Yellow Card", is_home=1))
    db.commit()


def test_players_discipline(client, seeded, db):
    _seed_cards(db)
    r = client.get("/players/discipline").json()
    assert r["season"] == "Apertura 2026"
    players = {p["player"]: p for p in r["players"]}
    # Rival X tiene 1 amarilla sembrada en el fixture; Tarjetero 4
    assert players["Tarjetero"]["yellow_cards"] == 4
    assert players["Tarjetero"]["suspension_risk"] is True
    assert players["Tarjetero"]["yellows_to_suspension"] == 1
    assert players["Rival X"]["yellow_cards"] == 1
    assert players["Rival X"]["suspension_risk"] is False
    # ordenado por discipline_points desc -> Tarjetero primero
    assert r["players"][0]["player"] == "Tarjetero"


def test_players_discipline_at_risk(client, seeded, db):
    _seed_cards(db)
    r = client.get("/players/discipline", params={"at_risk": True}).json()
    nombres = {p["player"] for p in r["players"]}
    assert "Tarjetero" in nombres and "Rival X" not in nombres


def test_player_discipline_individual(client, seeded, db):
    from app import models
    db.add(models.Player(id=20, team_id=1, name="Tarjetero"))
    _seed_cards(db)
    r = client.get("/players/20/discipline").json()
    assert r["player"] == "Tarjetero"
    assert r["yellow_cards"] == 4 and r["red_cards"] == 0
    assert r["suspension_risk"] is True


def test_team_discipline(client, seeded, db):
    _seed_cards(db)
    r = client.get("/teams/1/discipline").json()
    assert r["team_id"] == 1
    assert r["totals"]["yellow_cards"] == 4  # Tarjetero (equipo 1)
    assert any(p["player"] == "Tarjetero" for p in r["players"])
    assert len(r["at_risk"]) == 1
    # equipo 2 (Chivas) tiene la amarilla de Rival X
    r2 = client.get("/teams/2/discipline").json()
    assert r2["totals"]["yellow_cards"] == 1
