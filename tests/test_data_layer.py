"""
[Tester] Task 1 驗收測試
AC:
  - weather.py 回傳含 temperature, condition, humidity 的 dict
  - trends_cache.json 存在且包含至少 5 個關鍵字
  - festivals.py 在已知節慶日回傳正確名稱，非節慶日回傳 None
  - API 失敗時拋出帶訊息的自訂例外
"""
import json
import asyncio
import os
import pytest
from datetime import date
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock


# ---------------------------------------------------------------------------
# festivals.py tests (no network)
# ---------------------------------------------------------------------------

from src.data_layer.festivals import get_today_festival, FestivalsError


def test_festival_known_day():
    result = get_today_festival(date(2025, 2, 14))
    assert result == "情人節"


def test_festival_known_day_christmas():
    result = get_today_festival(date(2025, 12, 25))
    assert result == "聖誕節"


def test_festival_non_festival_day():
    result = get_today_festival(date(2025, 3, 15))
    assert result is None


def test_festival_one_time_event(tmp_path, monkeypatch):
    festivals_file = tmp_path / "festivals.json"
    festivals_file.write_text(
        json.dumps({"2025-06-01": "特別活動", "06-01": "兒童節"}), encoding="utf-8"
    )
    monkeypatch.setattr("src.data_layer.festivals.FESTIVALS_FILE", festivals_file)
    # Full date key takes priority
    assert get_today_festival(date(2025, 6, 1)) == "特別活動"


def test_festival_file_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "src.data_layer.festivals.FESTIVALS_FILE", tmp_path / "missing.json"
    )
    with pytest.raises(FestivalsError, match="not found"):
        get_today_festival()


# ---------------------------------------------------------------------------
# weather.py tests (mocked network)
# ---------------------------------------------------------------------------

from src.data_layer.weather import get_weather, WeatherError


@pytest.mark.asyncio
async def test_weather_returns_required_fields(tmp_path, monkeypatch):
    monkeypatch.setattr("src.data_layer.weather.CACHE_FILE", tmp_path / "weather.json")
    monkeypatch.setenv("OPENWEATHER_API_KEY", "test_key")
    monkeypatch.setenv("DEFAULT_CITY", "Taipei")

    mock_response = {
        "main": {"temp": 28.5, "feels_like": 31.0, "humidity": 75},
        "weather": [{"description": "多雲", "id": 803}],
        "name": "Taipei",
    }

    async def mock_fetch(city, api_key):
        from datetime import datetime
        return {
            "temperature": 28.5,
            "feels_like": 31.0,
            "condition": "多雲",
            "condition_code": 803,
            "humidity": 75,
            "city": "Taipei",
            "fetched_at": datetime.now().isoformat(),
        }

    monkeypatch.setattr("src.data_layer.weather._fetch_weather", mock_fetch)
    result = await get_weather()

    assert "temperature" in result
    assert "condition" in result
    assert "humidity" in result
    assert isinstance(result["temperature"], float)
    assert isinstance(result["humidity"], int)


@pytest.mark.asyncio
async def test_weather_raises_without_api_key(monkeypatch):
    monkeypatch.delenv("OPENWEATHER_API_KEY", raising=False)
    with pytest.raises(WeatherError, match="OPENWEATHER_API_KEY"):
        await get_weather()


@pytest.mark.asyncio
async def test_weather_uses_cache(tmp_path, monkeypatch):
    from datetime import datetime

    cache_file = tmp_path / "weather.json"
    cached_data = {
        "temperature": 20.0,
        "feels_like": 19.0,
        "condition": "晴",
        "condition_code": 800,
        "humidity": 60,
        "city": "taipei",
        "fetched_at": datetime.now().isoformat(),
    }
    cache_file.write_text(json.dumps(cached_data), encoding="utf-8")

    monkeypatch.setattr("src.data_layer.weather.CACHE_FILE", cache_file)
    monkeypatch.setenv("OPENWEATHER_API_KEY", "test_key")
    monkeypatch.setenv("DEFAULT_CITY", "Taipei")

    fetch_called = []

    async def mock_fetch(city, api_key):
        fetch_called.append(True)
        return cached_data

    monkeypatch.setattr("src.data_layer.weather._fetch_weather", mock_fetch)
    result = await get_weather("taipei")

    assert fetch_called == [], "Cache should have been returned without network call"
    assert result["temperature"] == 20.0


# ---------------------------------------------------------------------------
# trends.py tests (mocked network)
# ---------------------------------------------------------------------------

from src.data_layer.trends import get_trends, TrendsError, MOCK_TRENDS


@pytest.mark.asyncio
async def test_trends_fallback_to_mock(tmp_path, monkeypatch):
    monkeypatch.setattr("src.data_layer.trends.CACHE_FILE", tmp_path / "trends.json")

    async def mock_fetch_fail(url):
        raise TrendsError("simulated network failure")

    monkeypatch.setattr("src.data_layer.trends._fetch_feed_titles", mock_fetch_fail)
    result = await get_trends()

    assert len(result) >= 5
    assert result == MOCK_TRENDS


@pytest.mark.asyncio
async def test_trends_cache_written(tmp_path, monkeypatch):
    cache_file = tmp_path / "trends.json"
    monkeypatch.setattr("src.data_layer.trends.CACHE_FILE", cache_file)

    async def mock_fetch(url):
        return [f"trend-{i}" for i in range(10)]

    monkeypatch.setattr("src.data_layer.trends._fetch_feed_titles", mock_fetch)
    result = await get_trends()

    assert cache_file.exists()
    cached = json.loads(cache_file.read_text())
    assert len(cached["keywords"]) >= 5


@pytest.mark.asyncio
async def test_trends_cache_reused(tmp_path, monkeypatch):
    from datetime import datetime

    cache_file = tmp_path / "trends.json"
    cached_data = {
        "keywords": ["trend-a", "trend-b", "trend-c", "trend-d", "trend-e"],
        "updated_at": datetime.now().isoformat(),
        "source": "mock",
    }
    cache_file.write_text(json.dumps(cached_data), encoding="utf-8")
    monkeypatch.setattr("src.data_layer.trends.CACHE_FILE", cache_file)

    fetch_called = []

    async def mock_fetch(url):
        fetch_called.append(True)
        return []

    monkeypatch.setattr("src.data_layer.trends._fetch_feed_titles", mock_fetch)
    result = await get_trends()

    assert fetch_called == [], "Should use cache without network call"
    assert result == cached_data["keywords"]
