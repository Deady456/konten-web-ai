import re
import requests
from datetime import datetime
from xml.etree import ElementTree

def fetch_headlines(lang: str = "id", max_items: int = 15) -> list[dict]:
    headlines = []
    queries = ["anime", "manga", "anime news", "anime terbaru", "manga terbaru"]

    for q in queries:
        try:
            rss_url = f"https://news.google.com/rss/search?q={q}&hl={lang}&gl={'ID' if lang == 'id' else 'US'}"
            headers = {"User-Agent": "Mozilla/5.0"}
            r = requests.get(rss_url, headers=headers, timeout=10)
            r.raise_for_status()
            root = ElementTree.fromstring(r.content)
            for item in root.findall(".//item"):
                title = item.findtext("title", "")
                link = item.findtext("link", "")
                pub_date = item.findtext("pubDate", "")
                source = item.findtext("source", "")
                if link:
                    match = re.search(r'url=([^&]+)', link)
                    if match:
                        from urllib.parse import unquote
                        link = unquote(match.group(1))
                if title and link:
                    headlines.append({
                        "title": title,
                        "source": source or "Google News",
                        "date": pub_date,
                        "url": link,
                    })
        except Exception:
            pass

    seen = set()
    unique = []
    for h in headlines:
        key = h["title"].lower().strip()
        if key not in seen:
            seen.add(key)
            unique.append(h)

    return unique[:max_items]


def format_news(news: list[dict]) -> str:
    if not news:
        return "(tidak ada berita terkini yang ditemukan)"
    lines = [f"Berita anime/manga terkini ({datetime.now().strftime('%d %B %Y')}):"]
    for i, h in enumerate(news, 1):
        lines.append(f"  {i}. {h['title']}")
    return "\n".join(lines)
