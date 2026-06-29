import requests
from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper
from typing import List, Dict

class ExampleScraper(BaseScraper):
    """Plantilla de scraper usando BeautifulSoup.
    Debes adaptar los selectores CSS a la fuente que elijas."""
    
    @property
    def source_name(self):
        return "example"
    
    def _get_soup(self, url: str) -> BeautifulSoup:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return BeautifulSoup(response.text, "html.parser")
    
    def get_teams(self) -> List[Dict]:
        # Ejemplo básico
        # soup = self._get_soup("https://ejemplo.com/equipos")
        # teams = []
        # for item in soup.select(".team-row"):
        #     teams.append({
        #         "name": item.select_one(".team-name").text.strip(),
        #         "city": item.select_one(".team-city").text.strip(),
        #     })
        # return teams
        return []
    
    def get_stadiums(self) -> List[Dict]:
        return []
    
    def get_matches(self, season_id: int = None) -> List[Dict]:
        return []
    
    def get_players(self) -> List[Dict]:
        return []
    
    def get_standings(self) -> List[Dict]:
        return []
