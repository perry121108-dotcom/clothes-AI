import os
import json
import asyncio
import aiohttp
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(override=True)

CACHE_FILE = Path("cache/weather_cache.json")
CACHE_TTL_HOURS = 3


class WeatherError(Exception):
    pass


async def _fetch_weather(city: str, api_key: str) -> dict:
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": city,
        "appid": api_key,
        "units": "metric",
        "lang": "zh_tw",
    }
    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params, timeout=timeout) as resp:
            if resp.status != 200:
                body = await resp.text()
                raise WeatherError(f"OpenWeatherMap API {resp.status}: {body}")
            data = await resp.json()

    return {
        "temperature": round(data["main"]["temp"], 1),
        "feels_like": round(data["main"]["feels_like"], 1),
        "condition": data["weather"][0]["description"],
        "condition_code": data["weather"][0]["id"],
        "humidity": data["main"]["humidity"],
        "city": data["name"],
        "fetched_at": datetime.now().isoformat(),
    }


async def get_weather(city: str | None = None) -> dict:
    """Return structured weather dict for the given city.

    Caches result for CACHE_TTL_HOURS. Retries up to 3 times on transient errors.
    Raises WeatherError on permanent failure.
    """
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key:
        raise WeatherError("OPENWEATHER_API_KEY not set in .env")

    target_city = city or os.getenv("DEFAULT_CITY", "Taipei")

    # Return cached result if still fresh
    if CACHE_FILE.exists():
        try:
            cached = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
            if cached.get("city", "").lower() == target_city.lower():
                fetched_at = datetime.fromisoformat(cached["fetched_at"])
                if datetime.now() - fetched_at < timedelta(hours=CACHE_TTL_HOURS):
                    return cached
        except (json.JSONDecodeError, KeyError, ValueError):
            pass  # corrupt cache — fall through to live fetch

    last_err: Exception = WeatherError("unknown")
    for attempt in range(1, 4):
        try:
            result = await _fetch_weather(target_city, api_key)
            CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            CACHE_FILE.write_text(
                json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            return result
        except WeatherError:
            raise  # permanent error — do not retry
        except Exception as e:
            last_err = e
            if attempt < 3:
                await asyncio.sleep(2**attempt)

    raise WeatherError(f"get_weather failed after 3 attempts: {last_err}")
