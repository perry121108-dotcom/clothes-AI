"""Tests for Delivery Layer (Telegram Bot, Lock, main.py)"""

import asyncio
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ─────────────────────────────────────────────────────────────────────────────
# send_photos 測試
# ─────────────────────────────────────────────────────────────────────────────

class TestSendPhotos:

    def test_file_not_found_raises(self, tmp_path):
        from src.delivery_layer.telegram_bot import TelegramBotError, send_photos

        missing = tmp_path / "missing.png"
        with pytest.raises(TelegramBotError, match="圖片不存在"):
            asyncio.run(send_photos([missing], token="fake", chat_id="123"))

    def test_missing_token_raises(self, tmp_path):
        from src.delivery_layer.telegram_bot import TelegramBotError, send_photos

        img = tmp_path / "test.png"
        img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 8)

        with patch.dict("os.environ", {}, clear=True):
            with patch("src.delivery_layer.telegram_bot.load_dotenv"):
                with pytest.raises(TelegramBotError, match="TELEGRAM_BOT_TOKEN"):
                    asyncio.run(send_photos([img]))

    def test_missing_chat_id_raises(self, tmp_path):
        from src.delivery_layer.telegram_bot import TelegramBotError, send_photos

        img = tmp_path / "test.png"
        img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 8)

        with patch.dict("os.environ", {"TELEGRAM_BOT_TOKEN": "fake"}, clear=True):
            with patch("src.delivery_layer.telegram_bot.load_dotenv"):
                with pytest.raises(TelegramBotError, match="TELEGRAM_CHAT_ID"):
                    asyncio.run(send_photos([img]))

    def test_send_success(self, tmp_path):
        from src.delivery_layer.telegram_bot import send_photos

        imgs = []
        for i in range(4):
            p = tmp_path / f"img{i}.png"
            p.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 8)
            imgs.append(p)

        mock_bot = AsyncMock()
        mock_bot.send_media_group = AsyncMock(return_value=None)

        with patch("src.delivery_layer.telegram_bot.Bot", MagicMock(return_value=mock_bot)):
            asyncio.run(send_photos(imgs, caption="test", token="tok", chat_id="999"))

        mock_bot.send_media_group.assert_called_once()

    def test_retries_on_telegram_error(self, tmp_path):
        from telegram.error import TelegramError
        from src.delivery_layer.telegram_bot import TelegramBotError, send_photos

        img = tmp_path / "img.png"
        img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 8)

        mock_bot = AsyncMock()
        mock_bot.send_media_group = AsyncMock(side_effect=TelegramError("fail"))

        with patch("src.delivery_layer.telegram_bot.Bot", MagicMock(return_value=mock_bot)):
            with patch("asyncio.sleep", new_callable=AsyncMock):
                with pytest.raises(TelegramBotError):
                    asyncio.run(send_photos([img], token="tok", chat_id="999"))

        assert mock_bot.send_media_group.call_count == 3

    def test_caption_truncated_to_1024(self, tmp_path):
        from src.delivery_layer.telegram_bot import send_photos
        from telegram import InputMediaPhoto

        img = tmp_path / "img.png"
        img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 8)

        captured_media = []

        async def capture_call(chat_id, media):
            captured_media.extend(media)

        mock_bot = AsyncMock()
        mock_bot.send_media_group = capture_call

        with patch("src.delivery_layer.telegram_bot.Bot", MagicMock(return_value=mock_bot)):
            asyncio.run(send_photos([img], caption="x" * 2000, token="t", chat_id="1"))

        assert len(captured_media[0].caption) == 1024


# ─────────────────────────────────────────────────────────────────────────────
# 冪等性 Lock 機制
# ─────────────────────────────────────────────────────────────────────────────

class TestLockMechanism:

    def test_check_lock_no_lock(self, tmp_path, monkeypatch):
        import main as m
        monkeypatch.setattr(m, "OUTPUT_DIR", tmp_path)
        assert m._check_lock(datetime(2026, 4, 27)) is False

    def test_check_lock_existing(self, tmp_path, monkeypatch):
        import main as m
        monkeypatch.setattr(m, "OUTPUT_DIR", tmp_path)
        (tmp_path / "2026-04-27.lock").write_text("generated_at=2026-04-27T00:00:00\n")
        assert m._check_lock(datetime(2026, 4, 27)) is True

    def test_write_lock_creates_file(self, tmp_path, monkeypatch):
        import main as m
        monkeypatch.setattr(m, "OUTPUT_DIR", tmp_path)
        m._write_lock(datetime(2026, 4, 27))
        lock = tmp_path / "2026-04-27.lock"
        assert lock.exists()
        assert "generated_at=" in lock.read_text()

    def test_write_lock_creates_output_dir(self, tmp_path, monkeypatch):
        import main as m
        nested = tmp_path / "nested" / "output"
        monkeypatch.setattr(m, "OUTPUT_DIR", nested)
        m._write_lock(datetime(2026, 4, 27))
        assert (nested / "2026-04-27.lock").exists()

    def test_lock_path_format(self, tmp_path, monkeypatch):
        import main as m
        monkeypatch.setattr(m, "OUTPUT_DIR", tmp_path)
        assert m._lock_path(datetime(2026, 12, 31)) == tmp_path / "2026-12-31.lock"


# ─────────────────────────────────────────────────────────────────────────────
# main.py 整合流程
# ─────────────────────────────────────────────────────────────────────────────

SAMPLE_WEATHER = {
    "city": "Taipei",
    "temperature": 28.0,
    "condition": "晴朗",
    "humidity": 65,
}
SAMPLE_TRENDS = ["quiet luxury", "oversized tee"]
SAMPLE_FESTIVAL = None

SAMPLE_GROUP_1 = {
    "id": 1, "style_tag": "街頭休閒",
    "top":    {"hex": "#FFFFFF", "name": "純白", "type": "短袖T恤"},
    "bottom": {"hex": "#2C3E50", "name": "深藍", "type": "牛仔褲"},
    "shoes":  {"hex": "#E8D5B0", "name": "奶茶", "type": "運動鞋"},
    "photo_prompt": "", "caption": "今日穿搭 #OOTD #男生穿搭", "music_mood": "chill",
}
SAMPLE_GROUP_2 = {
    "id": 2, "style_tag": "都市簡約",
    "top":    {"hex": "#F5E6D0", "name": "米白", "type": "polo衫"},
    "bottom": {"hex": "#8B7355", "name": "棕褐", "type": "卡其褲"},
    "shoes":  {"hex": "#333333", "name": "炭黑", "type": "帆布鞋"},
    "photo_prompt": "", "caption": "", "music_mood": "",
}
SAMPLE_OUTFIT_DATA = {"groups": [SAMPLE_GROUP_1, SAMPLE_GROUP_2]}


class TestMainFlow:

    def _make_png(self, path: Path) -> Path:
        path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
        return path

    def test_full_flow_success(self, tmp_path, monkeypatch):
        import main as m
        monkeypatch.setattr(m, "OUTPUT_DIR", tmp_path)

        date_str = datetime.now().strftime("%Y-%m-%d")
        card1 = self._make_png(tmp_path / f"{date_str}_card_1.png")
        card2 = self._make_png(tmp_path / f"{date_str}_card_2.png")
        photo1 = self._make_png(tmp_path / f"{date_str}_photo_1.png")
        photo2 = self._make_png(tmp_path / f"{date_str}_photo_2.png")

        with (
            patch("src.data_layer.weather.get_weather", AsyncMock(return_value=SAMPLE_WEATHER)),
            patch("src.data_layer.trends.get_trends", AsyncMock(return_value=SAMPLE_TRENDS)),
            patch("src.data_layer.festivals.get_today_festival", MagicMock(return_value=None)),
            patch("src.brain_layer.outfit_generator.generate_outfit",
                  AsyncMock(return_value=SAMPLE_OUTFIT_DATA)),
            patch("src.render_layer.renderer.render_color_card",
                  AsyncMock(side_effect=[card1, card2])),
            patch("src.render_layer.outfit_photo_generator.generate_outfit_photo",
                  AsyncMock(side_effect=[photo1, photo2])),
            patch("src.delivery_layer.telegram_bot.send_photos", AsyncMock(return_value=None)),
        ):
            asyncio.run(m._run())

        lock = tmp_path / f"{date_str}.lock"
        assert lock.exists(), "Lock 檔案應在成功後寫入"

    def test_skip_when_locked(self, tmp_path, monkeypatch, capsys):
        import main as m
        monkeypatch.setattr(m, "OUTPUT_DIR", tmp_path)

        today = datetime.now()
        (tmp_path / f"{today.strftime('%Y-%m-%d')}.lock").write_text("generated_at=mock\n")

        mock_weather = AsyncMock()
        with patch("src.data_layer.weather.get_weather", mock_weather):
            asyncio.run(m._run())

        mock_weather.assert_not_called()
        assert "跳過" in capsys.readouterr().out

    def test_weather_error_exits(self, tmp_path, monkeypatch):
        import main as m
        from src.data_layer.weather import WeatherError
        monkeypatch.setattr(m, "OUTPUT_DIR", tmp_path)

        with (
            patch("src.data_layer.weather.get_weather", AsyncMock(side_effect=WeatherError("fail"))),
            patch("src.data_layer.trends.get_trends", AsyncMock(return_value=SAMPLE_TRENDS)),
            patch("src.data_layer.festivals.get_today_festival", MagicMock(return_value=None)),
            pytest.raises(SystemExit) as exc,
        ):
            asyncio.run(m._run())
        assert exc.value.code == 1

    def test_brain_layer_error_exits(self, tmp_path, monkeypatch):
        import main as m
        from src.brain_layer.outfit_generator import OutfitGeneratorError
        monkeypatch.setattr(m, "OUTPUT_DIR", tmp_path)

        with (
            patch("src.data_layer.weather.get_weather", AsyncMock(return_value=SAMPLE_WEATHER)),
            patch("src.data_layer.trends.get_trends", AsyncMock(return_value=SAMPLE_TRENDS)),
            patch("src.data_layer.festivals.get_today_festival", MagicMock(return_value=None)),
            patch("src.brain_layer.outfit_generator.generate_outfit",
                  AsyncMock(side_effect=OutfitGeneratorError("fail"))),
            pytest.raises(SystemExit) as exc,
        ):
            asyncio.run(m._run())
        assert exc.value.code == 1

    def test_render_error_exits(self, tmp_path, monkeypatch):
        import main as m
        from src.render_layer.renderer import RenderError
        monkeypatch.setattr(m, "OUTPUT_DIR", tmp_path)

        with (
            patch("src.data_layer.weather.get_weather", AsyncMock(return_value=SAMPLE_WEATHER)),
            patch("src.data_layer.trends.get_trends", AsyncMock(return_value=SAMPLE_TRENDS)),
            patch("src.data_layer.festivals.get_today_festival", MagicMock(return_value=None)),
            patch("src.brain_layer.outfit_generator.generate_outfit",
                  AsyncMock(return_value=SAMPLE_OUTFIT_DATA)),
            patch("src.render_layer.renderer.render_color_card",
                  AsyncMock(side_effect=RenderError("fail"))),
            pytest.raises(SystemExit) as exc,
        ):
            asyncio.run(m._run())
        assert exc.value.code == 1

    def test_telegram_error_exits_no_lock(self, tmp_path, monkeypatch):
        import main as m
        from src.delivery_layer.telegram_bot import TelegramBotError
        monkeypatch.setattr(m, "OUTPUT_DIR", tmp_path)

        date_str = datetime.now().strftime("%Y-%m-%d")
        card1 = self._make_png(tmp_path / f"{date_str}_card_1.png")
        card2 = self._make_png(tmp_path / f"{date_str}_card_2.png")
        photo1 = self._make_png(tmp_path / f"{date_str}_photo_1.png")
        photo2 = self._make_png(tmp_path / f"{date_str}_photo_2.png")

        with (
            patch("src.data_layer.weather.get_weather", AsyncMock(return_value=SAMPLE_WEATHER)),
            patch("src.data_layer.trends.get_trends", AsyncMock(return_value=SAMPLE_TRENDS)),
            patch("src.data_layer.festivals.get_today_festival", MagicMock(return_value=None)),
            patch("src.brain_layer.outfit_generator.generate_outfit",
                  AsyncMock(return_value=SAMPLE_OUTFIT_DATA)),
            patch("src.render_layer.renderer.render_color_card",
                  AsyncMock(side_effect=[card1, card2])),
            patch("src.render_layer.outfit_photo_generator.generate_outfit_photo",
                  AsyncMock(side_effect=[photo1, photo2])),
            patch("src.delivery_layer.telegram_bot.send_photos",
                  AsyncMock(side_effect=TelegramBotError("fail"))),
            pytest.raises(SystemExit) as exc,
        ):
            asyncio.run(m._run())

        assert exc.value.code == 1
        assert not (tmp_path / f"{date_str}.lock").exists()

    def test_lock_not_written_on_weather_error(self, tmp_path, monkeypatch):
        import main as m
        from src.data_layer.weather import WeatherError
        monkeypatch.setattr(m, "OUTPUT_DIR", tmp_path)

        with (
            patch("src.data_layer.weather.get_weather", AsyncMock(side_effect=WeatherError("fail"))),
            patch("src.data_layer.trends.get_trends", AsyncMock(return_value=SAMPLE_TRENDS)),
            patch("src.data_layer.festivals.get_today_festival", MagicMock(return_value=None)),
            pytest.raises(SystemExit),
        ):
            asyncio.run(m._run())

        date_str = datetime.now().strftime("%Y-%m-%d")
        assert not (tmp_path / f"{date_str}.lock").exists()
