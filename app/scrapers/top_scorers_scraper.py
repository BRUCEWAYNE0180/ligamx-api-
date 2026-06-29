from app.scrapers.espn_requests_scraper import ESPNRequestsScraper

def fetch_top_scorers(limit=20, season="2025"):
    try:
        scraper = ESPNRequestsScraper()
        scorers = scraper.get_top_scorers(season_name=season)
        return scorers[:limit]
    except Exception as e:
        print(f"ESPN top scorers falló: {e}")
        return []
