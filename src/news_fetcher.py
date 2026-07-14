import re
import requests
from datetime import datetime, timedelta
from xml.etree import ElementTree
from urllib.parse import unquote, quote_plus


def _parse_date(date_str: str) -> datetime | None:
    """Parse RSS pubDate format."""
    try:
        # Format: "Mon, 14 Jul 2026 08:00:00 GMT"
        return datetime.strptime(date_str.strip(), "%a, %d %b %Y %H:%M:%S %Z")
    except Exception:
        try:
            return datetime.strptime(date_str.strip()[:25], "%a, %d %b %Y %H:%M:%S")
        except Exception:
            return None


def _is_fresh(date_str: str, max_days: int = 7) -> bool:
    """Check if news item is within max_days old."""
    dt = _parse_date(date_str)
    if not dt:
        return True  # can't parse = assume fresh
    return (datetime.now() - dt) < timedelta(days=max_days)


def _fuzzy_overlap(a: str, b: str) -> float:
    """Simple word overlap ratio between two strings."""
    words_a = set(a.lower().split())
    words_b = set(b.lower().split())
    if not words_a or not words_b:
        return 0.0
    common = len(words_a & words_b)
    return common / min(len(words_a), len(words_b))


def fetch_headlines(lang: str = "id", max_items: int = 30) -> list[dict]:
    headlines = []
    queries = [
        "anime",
        "manga",
        "anime news",
        "anime terbaru",
        "manga terbaru",
        "anime review",
        "voice actor anime",
        "studio anime",
        "rekomendasi anime",
        "anime film 2026",
    ]

    seen_titles = set()

    for q in queries:
        try:
            rss_url = f"https://news.google.com/rss/search?q={quote_plus(q)}&hl={lang}&gl={'ID' if lang == 'id' else 'US'}"
            headers = {"User-Agent": "Mozilla/5.0"}
            r = requests.get(rss_url, headers=headers, timeout=10)
            r.raise_for_status()
            root = ElementTree.fromstring(r.content)
            for item in root.findall(".//item"):
                title = item.findtext("title", "")
                link = item.findtext("link", "")
                pub_date = item.findtext("pubDate", "")
                source = item.findtext("source", "")

                if not title or not link:
                    continue

                # Filter old news (>7 days)
                if not _is_fresh(pub_date, max_days=7):
                    continue

                # Extract real URL from Google News redirect
                match = re.search(r'url=([^&]+)', link)
                if match:
                    link = unquote(match.group(1))

                # Dedup by fuzzy title match
                title_lower = title.lower().strip()
                is_dup = False
                for seen in seen_titles:
                    if _fuzzy_overlap(title_lower, seen) > 0.7:
                        is_dup = True
                        break
                if is_dup:
                    continue

                seen_titles.add(title_lower)
                headlines.append({
                    "title": title,
                    "source": source or "Google News",
                    "date": pub_date,
                    "url": link,
                })
        except Exception:
            pass

    return headlines[:max_items]


def format_news(news: list[dict]) -> str:
    if not news:
        return "(tidak ada berita terkini yang ditemukan)"
    lines = [f"Berita anime/manga terkini ({datetime.now().strftime('%d %B %Y')}):"]
    for i, h in enumerate(news, 1):
        lines.append(f"  {i}. {h['title']}")
    return "\n".join(lines)
