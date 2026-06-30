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
