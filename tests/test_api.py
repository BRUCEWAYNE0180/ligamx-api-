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
