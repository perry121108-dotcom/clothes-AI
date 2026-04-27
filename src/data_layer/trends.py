import json
import asyncio
import aiohttp
import feedparser
from datetime import datetime, timedelta
from pathlib import Path

CACHE_FILE = Path("cache/trends_cache.json")
CACHE_TTL_DAYS = 30

FASHION_RSS_FEEDS = [
    "https://www.vogue.com/feed/rss",
    "https://www.harpersbazaar.com/rss/all.xml",
]

MOCK_TRENDS = [
    "oversized blazer",
    "quiet luxury",
    "ballet flats",
    "chocolate brown",
    "wide-leg trousers",
    "minimalist accessories",
    "sheer layers",
    "earth tones",
    "cargo pockets",
    "monochrome styling",
]


class TrendsError(Exception):
    pass


async def _fetch_feed_titles(url: str) -> list[str]:
    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=timeout) as resp:
            if resp.status != 200:
                raise TrendsError(f"RSS fetch error {resp.status} from {url}")
            text = await resp.text()

    feed = feedparser.parse(text)
    return [entry.title.strip() for entry in feed.entries if entry.get("title")][:20]


async def get_trends(force_refresh: bool = False) -> list[str]:
    """Return list of fashion trend keywords.

    Uses monthly cache. Falls back to MOCK_TRENDS if all live fetches fail.
    """
    if not force_refresh and CACHE_FILE.exists():
        try:
            cached = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
            updated_at = datetime.fromisoformat(cached["updated_at"])
            if datetime.now() - updated_at < timedelta(days=CACHE_TTL_DAYS):
                return cached["keywords"]
        except (json.JSONDecodeError, KeyError, ValueError):
            pass

    keywords: list[str] = []
    for url in FASHION_RSS_FEEDS:
        last_err: Exception | None = None
        for attempt in range(1, 4):
            try:
                titles = await _fetch_feed_titles(url)
                keywords.extend(titles)
                break
            except Exception as e:
                last_err = e
                if attempt < 3:
                    await asyncio.sleep(2**attempt)

    source = "live"
    if len(keywords) < 5:
        keywords = MOCK_TRENDS.copy()
        source = "mock"

    # Deduplicate preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for kw in keywords:
        if kw not in seen:
            seen.add(kw)
            unique.append(kw)

    result = {
        "keywords": unique,
        "updated_at": datetime.now().isoformat(),
        "source": source,
    }

    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return result["keywords"]
