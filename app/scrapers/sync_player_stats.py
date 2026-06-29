import unicodedata
from app import models

def norm(s):
    return unicodedata.normalize('NFKD', s or '').encode('ASCII', 'ignore').decode('ASCII').lower().strip()

def sync_player_stats(db, season="2025"):
    from app.scrapers.player_stats_scraper import fetch_player_stats
    print("Sincronizando stats por jugador...")
    player_ids = {p.id for p in db.query(models.Player).all()}
    team_map = {norm(t.name): t.id for t in db.query(models.Team).all()}
    db.query(models.PlayerStat).filter(models.PlayerStat.season == season).delete()
    for p in fetch_player_stats(limit=500, season=season):
        pid = p.get("player_id")
        int_pid = int(pid) if pid else None
        if int_pid and int_pid not in player_ids:
            db.add(models.Player(id=int_pid, name=p["player_name"], team_id=team_map.get(norm(p["team_name"]))))
            player_ids.add(int_pid)
        p["player_id"] = int_pid if int_pid in player_ids else None
        p["team_id"] = team_map.get(norm(p["team_name"]))
        db.add(models.PlayerStat(**p))
    db.commit()
    print("OK stats por jugador", len(db.query(models.PlayerStat).all()))
