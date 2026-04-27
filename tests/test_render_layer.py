"""
Tests for Render Layer — renderer.py
======================================
覆蓋 AC：
  AC1: 輸出 PNG 解析度精確為 1080×1920
  AC2: HTML 模板包含顏色名稱、衣物類型文字
  AC3: 於 headless 環境下執行無報錯
"""

import asyncio
from pathlib import Path

import pytest

from src.render_layer.renderer import (
    CARD_HEIGHT,
    CARD_WIDTH,
    RenderError,
    _darken,
    _expand_hex,
    _render_color_card_html,
    _text_color,
    render_color_card,
)

# ── 測試用共用資料 ────────────────────────────────────────────────────────────

SAMPLE_GROUP = {
    "id": 1,
    "style_tag": "街頭休閒",
    "top":    {"hex": "#FFFFFF", "name": "純白", "type": "短袖T恤"},
    "bottom": {"hex": "#2C3E50", "name": "深藍", "type": "直筒牛仔褲"},
    "shoes":  {"hex": "#E8D5B0", "name": "奶茶", "type": "運動鞋"},
    "photo_prompt": "",
    "caption": "今日穿搭 #OOTD",
    "music_mood": "chill",
}


# ══════════════════════════════════════════════════════════════════════════════
# 色彩工具函式測試
# ══════════════════════════════════════════════════════════════════════════════

class TestColorUtils:
    def test_expand_hex_3digit(self):
        assert _expand_hex("#FFF") == "#FFFFFF"
        assert _expand_hex("#000") == "#000000"
        assert _expand_hex("#ABC") == "#AABBCC"

    def test_expand_hex_6digit_unchanged(self):
        assert _expand_hex("#2C3E50") == "#2C3E50"
        assert _expand_hex("#ffffff") == "#FFFFFF"

    def test_text_color_dark_bg_returns_white(self):
        assert _text_color("#000000") == "#FFFFFF"
        assert _text_color("#1A1A2E") == "#FFFFFF"

    def test_text_color_light_bg_returns_dark(self):
        assert _text_color("#FFFFFF") == "#2C2C2C"
        assert _text_color("#F5F5F5") == "#2C2C2C"

    def test_darken_reduces_brightness(self):
        darkened = _darken("#FFFFFF", 0.4)
        r = int(darkened[1:3], 16)
        assert r == 102  # 255 * 0.4 = 102

    def test_darken_black_stays_black(self):
        assert _darken("#000000", 0.4) == "#000000"


# ══════════════════════════════════════════════════════════════════════════════
# HTML 模板內容測試
# ══════════════════════════════════════════════════════════════════════════════

class TestRenderColorCardHtml:
    def test_html_contains_color_names(self):
        html = _render_color_card_html(SAMPLE_GROUP, 1, 2)
        assert "純白" in html
        assert "深藍" in html
        assert "奶茶" in html

    def test_html_contains_clothing_types(self):
        html = _render_color_card_html(SAMPLE_GROUP, 1, 2)
        assert "短袖T恤" in html
        assert "直筒牛仔褲" in html
        assert "運動鞋" in html

    def test_html_contains_hex_colors(self):
        html = _render_color_card_html(SAMPLE_GROUP, 1, 2)
        assert "#FFFFFF" in html
        assert "#2C3E50" in html
        assert "#E8D5B0" in html

    def test_html_contains_style_tag(self):
        html = _render_color_card_html(SAMPLE_GROUP, 1, 2)
        assert "街頭休閒" in html

    def test_html_contains_group_id(self):
        html = _render_color_card_html(SAMPLE_GROUP, 1, 2)
        assert "1" in html

    def test_html_no_jinja_placeholders(self):
        html = _render_color_card_html(SAMPLE_GROUP, 1, 2)
        assert "{{" not in html
        assert "}}" not in html


# ══════════════════════════════════════════════════════════════════════════════
# Playwright 截圖測試
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
class TestRenderColorCard:

    async def test_renders_png_correct_size(self, tmp_path):
        from PIL import Image

        out = tmp_path / "test_card.png"
        result = await render_color_card(SAMPLE_GROUP, 1, 2, out)

        assert result.exists()
        assert result.suffix == ".png"
        img = Image.open(result)
        assert img.size == (CARD_WIDTH, CARD_HEIGHT)

    async def test_creates_parent_dir(self, tmp_path):
        out = tmp_path / "subdir" / "card.png"
        result = await render_color_card(SAMPLE_GROUP, 1, 2, out)
        assert result.exists()

    async def test_group2_renders(self, tmp_path):
        group2 = {
            **SAMPLE_GROUP,
            "id": 2,
            "style_tag": "都市簡約",
            "top":    {"hex": "#F5E6D0", "name": "米白", "type": "polo衫"},
            "bottom": {"hex": "#8B7355", "name": "棕褐", "type": "卡其褲"},
            "shoes":  {"hex": "#333333", "name": "炭黑", "type": "帆布鞋"},
        }
        out = tmp_path / "card2.png"
        result = await render_color_card(group2, 2, 2, out)
        assert result.exists()
