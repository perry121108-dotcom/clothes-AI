"""
Tests for Brain Layer — outfit_generator.py
=============================================
覆蓋 AC：
  AC1: 輸出符合 Schema 的合法 JSON（2 組，含 Mock 測試）
  AC2: 驗證 hex 格式自動修正（#RGB → #RRGGBB）
  AC3: API 逾時自動 Retry，最多 3 次，仍失敗則拋出例外
"""

import asyncio
import json
import os
import pytest
from unittest.mock import MagicMock, patch

from src.brain_layer.outfit_generator import (
    MUSIC_MOODS,
    OutfitGeneratorError,
    SchemaValidationError,
    _build_prompt,
    _validate,
    generate_outfit,
)

# ── 測試用共用資料 ────────────────────────────────────────────────────────────

SAMPLE_WEATHER = {
    "temperature": 28.0,
    "condition": "晴天",
    "humidity": 65,
    "city": "Taipei",
}
SAMPLE_TRENDS = ["oversized tee", "cargo pants", "earth tones"]
SAMPLE_FESTIVAL = "端午節"

VALID_GROUP_1 = {
    "id": 1,
    "style_tag": "街頭休閒",
    "top":    {"hex": "#FFFFFF", "name": "純白", "type": "短袖T恤"},
    "bottom": {"hex": "#2C3E50", "name": "深藍", "type": "直筒牛仔褲"},
    "shoes":  {"hex": "#E8D5B0", "name": "奶茶", "type": "運動鞋"},
    "photo_prompt": "back view of young male...",
    "caption": "今日穿搭 #OOTD #男生穿搭",
    "music_mood": "chill",
}
VALID_GROUP_2 = {
    "id": 2,
    "style_tag": "都市簡約",
    "top":    {"hex": "#F5E6D0", "name": "米白", "type": "polo衫"},
    "bottom": {"hex": "#8B7355", "name": "棕褐", "type": "卡其褲"},
    "shoes":  {"hex": "#333333", "name": "炭黑", "type": "帆布鞋"},
    "photo_prompt": "front view of young male...",
    "caption": "",
    "music_mood": "",
}
VALID_OUTFIT_DATA = {"groups": [VALID_GROUP_1, VALID_GROUP_2]}


# ══════════════════════════════════════════════════════════════════════════════
# _build_prompt 測試
# ══════════════════════════════════════════════════════════════════════════════

class TestBuildPrompt:
    def test_includes_weather_fields(self):
        prompt = _build_prompt(SAMPLE_WEATHER, SAMPLE_TRENDS, None)
        assert "28.0" in prompt
        assert "Taipei" in prompt
        assert "晴天" in prompt

    def test_includes_festival_when_present(self):
        prompt = _build_prompt(SAMPLE_WEATHER, SAMPLE_TRENDS, "端午節")
        assert "端午節" in prompt

    def test_festival_fallback_when_none(self):
        prompt = _build_prompt(SAMPLE_WEATHER, SAMPLE_TRENDS, None)
        assert "無" in prompt

    def test_includes_trends(self):
        prompt = _build_prompt(SAMPLE_WEATHER, SAMPLE_TRENDS, None)
        assert "oversized tee" in prompt

    def test_empty_trends_fallback(self):
        prompt = _build_prompt(SAMPLE_WEATHER, [], None)
        assert "無" in prompt

    def test_prompt_mentions_2_groups(self):
        prompt = _build_prompt(SAMPLE_WEATHER, SAMPLE_TRENDS, None)
        assert "2" in prompt


# ══════════════════════════════════════════════════════════════════════════════
# _validate 測試
# ══════════════════════════════════════════════════════════════════════════════

class TestValidate:
    def test_valid_2_groups_passes(self):
        _validate(VALID_OUTFIT_DATA)

    def test_wrong_group_count_raises(self):
        data = {"groups": [VALID_GROUP_1]}
        with pytest.raises(SchemaValidationError, match="2 組"):
            _validate(data)

    def test_four_groups_raises(self):
        data = {"groups": [VALID_GROUP_1, VALID_GROUP_2, VALID_GROUP_1, VALID_GROUP_2]}
        with pytest.raises(SchemaValidationError, match="2 組"):
            _validate(data)

    def test_empty_groups_raises(self):
        with pytest.raises(SchemaValidationError):
            _validate({"groups": []})

    def test_missing_field_raises(self):
        bad = {**VALID_GROUP_1}
        del bad["style_tag"]
        with pytest.raises(SchemaValidationError, match="style_tag"):
            _validate({"groups": [bad, VALID_GROUP_2]})

    def test_missing_garment_sub_field_raises(self):
        bad = {**VALID_GROUP_1, "top": {"hex": "#FFF", "name": "白"}}  # missing type
        with pytest.raises(SchemaValidationError, match="type"):
            _validate({"groups": [bad, VALID_GROUP_2]})

    def test_hex_auto_fix_3_to_6_digit(self):
        data = {
            "groups": [
                {**VALID_GROUP_1, "top": {"hex": "#FFF", "name": "白", "type": "T恤"}},
                VALID_GROUP_2,
            ]
        }
        _validate(data)
        assert data["groups"][0]["top"]["hex"] == "#FFFFFF"

    def test_invalid_hex_raises(self):
        bad = {**VALID_GROUP_1, "top": {"hex": "white", "name": "白", "type": "T恤"}}
        with pytest.raises(SchemaValidationError, match="hex"):
            _validate({"groups": [bad, VALID_GROUP_2]})


# ══════════════════════════════════════════════════════════════════════════════
# generate_outfit 邏輯測試（Mock Gemini）
# ══════════════════════════════════════════════════════════════════════════════

def _make_gemini_response(data: dict) -> MagicMock:
    resp = MagicMock()
    resp.text = json.dumps(data, ensure_ascii=False)
    return resp


@pytest.mark.asyncio
class TestGenerateOutfit:

    @patch("src.brain_layer.outfit_generator.genai.Client")
    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"})
    async def test_returns_valid_data_on_success(self, mock_cls):
        mock_client = mock_cls.return_value
        mock_client.models.generate_content.return_value = _make_gemini_response(VALID_OUTFIT_DATA)

        result = await generate_outfit(SAMPLE_WEATHER, SAMPLE_TRENDS, SAMPLE_FESTIVAL)

        assert len(result["groups"]) == 2
        assert result["groups"][0]["style_tag"] == "街頭休閒"

    @patch("src.brain_layer.outfit_generator.genai.Client")
    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"})
    async def test_three_consecutive_calls_all_valid(self, mock_cls):
        mock_client = mock_cls.return_value
        mock_client.models.generate_content.return_value = _make_gemini_response(VALID_OUTFIT_DATA)

        for _ in range(3):
            result = await generate_outfit(SAMPLE_WEATHER, SAMPLE_TRENDS, None)
            assert len(result["groups"]) == 2
            _validate(result)

    @patch.dict(os.environ, {}, clear=True)
    async def test_raises_without_api_key(self):
        with pytest.raises(OutfitGeneratorError, match="GEMINI_API_KEY"):
            await generate_outfit(SAMPLE_WEATHER, SAMPLE_TRENDS, None)

    @patch("src.brain_layer.outfit_generator.genai.Client")
    @patch("src.brain_layer.outfit_generator.asyncio.sleep")
    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"})
    async def test_retries_on_timeout_then_succeeds(self, mock_sleep, mock_cls):
        mock_client = mock_cls.return_value
        good_resp = _make_gemini_response(VALID_OUTFIT_DATA)
        call_count = [0]

        def side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise asyncio.TimeoutError()
            return good_resp

        mock_client.models.generate_content.side_effect = side_effect

        result = await generate_outfit(SAMPLE_WEATHER, SAMPLE_TRENDS, None)
        assert len(result["groups"]) == 2

    @patch("src.brain_layer.outfit_generator.genai.Client")
    @patch("src.brain_layer.outfit_generator.asyncio.sleep")
    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"})
    async def test_raises_after_max_retries(self, mock_sleep, mock_cls):
        mock_client = mock_cls.return_value
        mock_client.models.generate_content.side_effect = asyncio.TimeoutError()

        with pytest.raises(OutfitGeneratorError):
            await generate_outfit(SAMPLE_WEATHER, SAMPLE_TRENDS, None, max_retries=3)
