"""Data Layer — Music Trends (Billboard Hot 100 + YouTube Charts)

抓取策略（Task 5.1 + 5.2）：
  1. 嘗試 Billboard Hot 100 RSS → feedparser 解析
  2. 嘗試 YouTube Trending RSS → feedparser 解析（附加來源）
  3. 以上皆失敗 → 使用 MOCK_TRACKS，標記 source="mock"
  4. 結果快取 7 天（週快取）至 assets/music/trends/music_trends.json

版權守則：僅儲存曲目名稱 / 歌手 / 排名等公開資訊，不下載任何音樂檔案。
"""

import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path

import aiohttp
import feedparser

TRENDS_DIR = Path(__file__).parent.parent.parent / "assets" / "music" / "trends"
CACHE_FILE = TRENDS_DIR / "music_trends.json"
CACHE_TTL_DAYS = 7

BILLBOARD_RSS_URLS = [
    "https://www.billboard.com/charts/hot-100/feed/",
    "https://www.billboard.com/feed/",
]
YOUTUBE_TRENDING_RSS = (
    "https://www.youtube.com/feeds/videos.xml?chart=0&gl=US&hl=en"
)

# MOCK_TRACKS：提供離線 / RSS 封鎖時的參考資料
MOCK_TRACKS: list[dict] = [
    {"rank": 1,  "title": "Die With A Smile",            "artist": "Lady Gaga & Bruno Mars",  "source": "Billboard Hot 100", "weeks_on_chart": 30},
    {"rank": 2,  "title": "A Bar Song (Tipsy)",           "artist": "Shaboozey",               "source": "Billboard Hot 100", "weeks_on_chart": 28},
    {"rank": 3,  "title": "Good Luck, Babe!",             "artist": "Chappell Roan",           "source": "Billboard Hot 100", "weeks_on_chart": 22},
    {"rank": 4,  "title": "Espresso",                     "artist": "Sabrina Carpenter",       "source": "Billboard Hot 100", "weeks_on_chart": 24},
    {"rank": 5,  "title": "Please Please Please",         "artist": "Sabrina Carpenter",       "source": "Billboard Hot 100", "weeks_on_chart": 18},
    {"rank": 6,  "title": "Too Sweet",                    "artist": "Hozier",                  "source": "Billboard Hot 100", "weeks_on_chart": 16},
    {"rank": 7,  "title": "I Had Some Help",              "artist": "Post Malone ft. Morgan Wallen", "source": "Billboard Hot 100", "weeks_on_chart": 14},
    {"rank": 8,  "title": "Beautiful Things",             "artist": "Benson Boone",            "source": "Billboard Hot 100", "weeks_on_chart": 20},
    {"rank": 9,  "title": "Lunch",                        "artist": "Billie Eilish",           "source": "Billboard Hot 100", "weeks_on_chart": 12},
    {"rank": 10, "title": "We Can't Be Friends",          "artist": "Ariana Grande",           "source": "Billboard Hot 100", "weeks_on_chart": 10},
    {"rank": 11, "title": "Lose Control",                 "artist": "Teddy Swims",             "source": "Billboard Hot 100", "weeks_on_chart": 8},
    {"rank": 12, "title": "Birds of a Feather",           "artist": "Billie Eilish",           "source": "Billboard Hot 100", "weeks_on_chart": 15},
    {"rank": 13, "title": "Fortnight",                    "artist": "Taylor Swift ft. Post Malone", "source": "Billboard Hot 100", "weeks_on_chart": 11},
    {"rank": 14, "title": "Million Dollar Baby",          "artist": "Tommy Richman",           "source": "Billboard Hot 100", "weeks_on_chart": 9},
    {"rank": 15, "title": "Stargazing",                   "artist": "Myles Smith",             "source": "YouTube Trending",  "weeks_on_chart": 6},
]


class MusicTrendsError(Exception):
    """Music Trends 抓取失敗"""


# ── 內部抓取函式 ──────────────────────────────────────────────────────────────

async def _fetch_billboard(session: aiohttp.ClientSession) -> list[dict]:
    """嘗試從 Billboard RSS 解析曲目清單。"""
    timeout = aiohttp.ClientTimeout(total=30)
    for url in BILLBOARD_RSS_URLS:
        try:
            async with session.get(url, timeout=timeout, allow_redirects=True) as resp:
                if resp.status != 200:
                    continue
                text = await resp.text()
            feed = feedparser.parse(text)
            tracks = []
            for i, entry in enumerate(feed.entries[:20], start=1):
                title = (entry.get("title") or "").strip()
                if not title:
                    continue
                # Billboard RSS entries 格式：「Artist - Title」或純標題
                if " - " in title:
                    artist_part, title_part = title.split(" - ", 1)
                else:
                    artist_part, title_part = "Unknown", title
                tracks.append({
                    "rank": i,
                    "title": title_part.strip(),
                    "artist": artist_part.strip(),
                    "source": "Billboard Hot 100",
                    "weeks_on_chart": None,
                })
            if len(tracks) >= 5:
                return tracks
        except Exception:
            continue
    return []


async def _fetch_youtube_trending(session: aiohttp.ClientSession) -> list[dict]:
    """嘗試從 YouTube Trending RSS 解析影片（作為次要參考）。"""
    timeout = aiohttp.ClientTimeout(total=30)
    try:
        async with session.get(YOUTUBE_TRENDING_RSS, timeout=timeout) as resp:
            if resp.status != 200:
                return []
            text = await resp.text()
        feed = feedparser.parse(text)
        tracks = []
        for i, entry in enumerate(feed.entries[:10], start=1):
            title = (entry.get("title") or "").strip()
            author = (entry.get("author") or entry.get("yt_channeltitle") or "Unknown").strip()
            if title:
                tracks.append({
                    "rank": i,
                    "title": title,
                    "artist": author,
                    "source": "YouTube Trending",
                    "weeks_on_chart": None,
                })
        return tracks
    except Exception:
        return []


# ── 主要公開函式 ──────────────────────────────────────────────────────────────

async def get_music_trends(force_refresh: bool = False) -> list[dict]:
    """
    回傳本週音樂趨勢清單（週快取）。

    Args:
        force_refresh: 強制忽略快取，重新抓取。

    Returns:
        list[dict]，每筆含 rank / title / artist / source / weeks_on_chart

    Notes:
        - 優先 Billboard Hot 100 RSS，補充 YouTube Trending
        - 所有來源失敗時，回傳 MOCK_TRACKS 並標記 source="mock"
        - 快取 7 天至 assets/music/trends/music_trends.json
    """
    if not force_refresh and CACHE_FILE.exists():
        try:
            cached = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
            updated_at = datetime.fromisoformat(cached["updated_at"])
            if datetime.now() - updated_at < timedelta(days=CACHE_TTL_DAYS):
                return cached["tracks"]
        except (json.JSONDecodeError, KeyError, ValueError):
            pass

    tracks: list[dict] = []
    source_tag = "live"

    timeout = aiohttp.ClientTimeout(total=30)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            billboard = await _fetch_billboard(session)
            tracks.extend(billboard)

            youtube = await _fetch_youtube_trending(session)
            # 合併 YouTube 資料，去重（以 title 為鍵）
            existing_titles = {t["title"].lower() for t in tracks}
            yt_rank = len(tracks) + 1
            for yt in youtube:
                if yt["title"].lower() not in existing_titles:
                    yt["rank"] = yt_rank
                    tracks.append(yt)
                    yt_rank += 1
    except Exception:
        pass

    if len(tracks) < 10:
        tracks = MOCK_TRACKS.copy()
        source_tag = "mock"

    payload = {
        "tracks": tracks,
        "updated_at": datetime.now().isoformat(),
        "source": source_tag,
        "total": len(tracks),
    }
    TRENDS_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return tracks


def get_music_trends_sync(force_refresh: bool = False) -> list[dict]:
    """同步包裝器。"""
    return asyncio.run(get_music_trends(force_refresh))
