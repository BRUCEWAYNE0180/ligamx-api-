import re
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper
from typing import List, Dict

class ESPNPlaywrightScraper(BaseScraper):
    def __init__(self):
        self._cached_soup = None
    
    @property
    def source_name(self):
        return "espn_playwright"
    
    def _get_soup(self) -> BeautifulSoup:
        if self._cached_soup is None:
            url = "https://www.espn.com.mx/futbol/liga/_/nombre/mex.1/"
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(url, wait_until="domcontentloaded")
                page.wait_for_timeout(5000)
                content = page.content()
                browser.close()
            self._cached_soup = BeautifulSoup(content, "html.parser")
        return self._cached_soup
    
    def _extract_team_id(self, href: str) -> int:
        match = re.search(r'/id/(\d+)/', href)
        if match:
            return int(match.group(1))
        return 0
    
    def get_teams(self) -> List[Dict]:
        soup = self._get_soup()
        teams = []
        rows = soup.select("article.sub-module.standings table.mod-data tbody tr")
        
        for i, row in enumerate(rows):
            team_link = row.select_one("td a")
            if not team_link:
                continue
            
            name = team_link.text.strip()
            href = team_link.get("href", "")
            team_id = self._extract_team_id(href)
            
            if team_id == 0:
                team_id = i + 1000
            
            teams.append({
                "id": team_id,
                "name": name,
                "short_name": "",
                "city": "",
                "colors": ""
            })
        
        return teams
    
    def get_standings(self) -> List[Dict]:
        soup = self._get_soup()
        standings = []
        rows = soup.select("article.sub-module.standings table.mod-data tbody tr")
        
        for i, row in enumerate(rows):
            team_link = row.select_one("td a")
            if not team_link:
                continue
            
            team_name = team_link.text.strip()
            stats = row.select("td.right")
            
            if len(stats) < 6:
                continue
            
            standings.append({
                "position": i + 1,
                "team_name": team_name,
                "played": int(stats[0].text.strip() or 0),
                "won": int(stats[1].text.strip() or 0),
                "drawn": int(stats[2].text.strip() or 0),
                "lost": int(stats[3].text.strip() or 0),
                "goals_for": 0,
                "goals_against": 0,
                "goal_difference": int(stats[4].text.strip() or 0),
                "points": int(stats[5].text.strip() or 0)
            })
        
        return standings
    
    def get_stadiums(self) -> List[Dict]:
        return []
    
    def get_matches(self, season_id: int = None) -> List[Dict]:
        return []
    
    def get_players(self) -> List[Dict]:
        return []
