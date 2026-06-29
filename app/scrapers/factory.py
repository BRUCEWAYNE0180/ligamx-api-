from app.scrapers.demo_scraper import DemoScraper
from app.scrapers.espn_requests_scraper import ESPNRequestsScraper
SCRAPERS = {"demo": DemoScraper, "espn": ESPNRequestsScraper}
def get_scraper(source: str = "demo"):
    if source not in SCRAPERS:
        raise ValueError(f"Fuente no soportada: {source}. Disponibles: {list(SCRAPERS.keys())}")
    return SCRAPERS[source]()
