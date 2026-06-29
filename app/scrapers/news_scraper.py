import re
import feedparser
from datetime import datetime
from typing import List, Dict

NEWS_FEEDS = [
    "https://news.google.com/rss/search?q=Liga+MX&hl=es-419&gl=MX&ceid=MX:es-419",
    "https://www.espn.com.mx/espn/rss?images=off",
]

def _strip_html(text):
    return re.sub(r"<[^>]+>", "", text or "")

def _parse_date(entry):
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        return datetime(*entry.published_parsed[:6])
    if hasattr(entry, "updated_parsed") and entry.updated_parsed:
        return datetime(*entry.updated_parsed[:6])
    return None

def fetch_news(limit=20) -> List[Dict]:
    items = []
    for url in NEWS_FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:limit]:
                items.append({
                    "title": entry.get("title", ""),
                    "link": entry.get("link", ""),
                    "description": _strip_html(entry.get("summary", ""))[:500],
                    "published_at": _parse_date(entry),
                    "source": feed.feed.get("title", url),
                })
        except Exception as e:
            print(f"⚠️ news feed {url}: {e}")
    items.sort(key=lambda x: x["published_at"] or datetime.min, reverse=True)
    return items[:limit]
