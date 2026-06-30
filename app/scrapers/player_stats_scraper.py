import time
from app.scrapers.espn_requests_scraper import ESPNRequestsScraper

def fetch_player_stats(limit=100, season=None):
    from app.season import current_season_year
    season = season or current_season_year()
    scraper = ESPNRequestsScraper()
    matches = scraper.get_matches()
    stats = {}
    seen = {}

    def add(athlete, team, field, eid):
        name = athlete.get("displayName")
        pid = athlete.get("id")
        key = (name, pid)
        seen.setdefault(key, set()).add(eid)
        s = stats.setdefault(key, {
            "player_name": name, "player_id": pid, "team_name": team, "season": season,
            "goals": 0, "assists": 0, "yellow_cards": 0, "red_cards": 0
        })
        s[field] += 1

    for m in matches:
        if m.get("status") != "finished": continue
        eid = m.get("event_id")
        if not eid: continue
        try:
            data = scraper._get_json(f"https://site.api.espn.com/apis/site/v2/sports/soccer/mex.1/summary?event={eid}")
        except Exception as e:
            print(f"⚠️ {eid}: {e}")
            continue
        for ev in data.get("keyEvents", []):
            parts = ev.get("participants", [])
            team = ev.get("team", {}).get("displayName")
            if ev.get("scoringPlay"):
                if parts: add(parts[0].get("athlete", {}), team, "goals", eid)
                if len(parts) > 1: add(parts[1].get("athlete", {}), team, "assists", eid)
            elif "Yellow Card" in (ev.get("type", {}).get("text") or "") and parts:
                add(parts[0].get("athlete", {}), team, "yellow_cards", eid)
            elif "Red Card" in (ev.get("type", {}).get("text") or "") and parts:
                add(parts[0].get("athlete", {}), team, "red_cards", eid)
        time.sleep(0.15)

    for key in stats: stats[key]["matches_played"] = len(seen[key])
    return sorted(stats.values(), key=lambda x: x["goals"], reverse=True)[:limit]
