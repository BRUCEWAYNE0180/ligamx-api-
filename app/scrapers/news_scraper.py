from datetime import datetime
from typing import List, Dict
from playwright.sync_api import sync_playwright

def fetch_flashscore_news(limit: int = 20) -> List[Dict]:
    url = "https://www.flashscore.com.mx/futbol/mexico/liga-mx/noticias/"
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="networkidle")
        page.wait_for_timeout(3000)
        
        articles = page.query_selector_all("a[class*='wcl-article']")
        
        news = []
        for article in articles[:limit]:
            try:
                title_elem = article.query_selector("h3")
                if not title_elem:
                    continue
                title = title_elem.inner_text().strip()
                
                href = article.get_attribute("href")
                if href and href.startswith("/"):
                    href = f"https://www.flashscore.com.mx{href}"
                
                news.append({
                    "title": title,
                    "link": href,
                    "description": title,
                    "published_at": datetime.now(),
                    "source": "flashscore"
                })
            except Exception:
                continue
        
        browser.close()
        return news

def fetch_news(limit: int = 20) -> List[Dict]:
    return fetch_flashscore_news(limit)
