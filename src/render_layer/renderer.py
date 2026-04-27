"""
Render Layer — Color Card Renderer
=====================================
使用 Playwright async headless 將 Jinja2 HTML 模板渲染為 1080×1920 PNG。
"""

import asyncio
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from playwright.async_api import async_playwright

# ── 路徑常數 ──────────────────────────────────────────────────────────────────
TEMPLATES_DIR = Path(__file__).parent.parent.parent / "assets" / "templates"
OUTPUT_DIR = Path(__file__).parent.parent.parent / "output"

CARD_WIDTH = 1080
CARD_HEIGHT = 1920


# ── 自訂例外 ──────────────────────────────────────────────────────────────────

class RenderError(Exception):
    """Render Layer 執行錯誤"""


# ── 色彩工具 ──────────────────────────────────────────────────────────────────

def _expand_hex(hex_color: str) -> str:
    """將 #RGB 展開為 #RRGGBB。"""
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return f"#{h.upper()}"


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = _expand_hex(hex_color).lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _text_color(hex_color: str) -> str:
    """依背景亮度決定文字顏色（白或深灰）。"""
    r, g, b = _hex_to_rgb(hex_color)
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    return "#FFFFFF" if luminance < 0.55 else "#2C2C2C"


def _darken(hex_color: str, factor: float = 0.35) -> str:
    """將顏色加深，用於背景漸層。"""
    r, g, b = _hex_to_rgb(hex_color)
    return "#{:02X}{:02X}{:02X}".format(
        int(r * factor), int(g * factor), int(b * factor)
    )


# ── Jinja2 環境 ───────────────────────────────────────────────────────────────

def _get_jinja_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html"]),
    )


# ── 色塊卡片渲染（Douyin 風格）────────────────────────────────────────────────

def _render_color_card_html(group: dict, group_id: int, total_groups: int) -> str:
    env = _get_jinja_env()
    template = env.get_template("color_card.html")

    top    = group["top"]
    bottom = group["bottom"]
    shoes  = group["shoes"]

    context = {
        # 背景漸層（各色加深版本）
        "top_bg": _darken(top["hex"],    0.4),
        "mid_bg": _darken(bottom["hex"], 0.4),
        "bot_bg": _darken(shoes["hex"],  0.4),
        # 色條實際顏色
        "top_hex": top["hex"],
        "mid_hex": bottom["hex"],
        "bot_hex": shoes["hex"],
        # 文字顏色（自動對比）
        "top_text": _text_color(top["hex"]),
        "mid_text": _text_color(bottom["hex"]),
        "bot_text": _text_color(shoes["hex"]),
        # 標籤文字
        "top_name": top["name"],
        "top_type": top["type"],
        "mid_name": bottom["name"],
        "mid_type": bottom["type"],
        "bot_name": shoes["name"],
        "bot_type": shoes["type"],
        # 組號
        "group_id":     group_id,
        "total_groups": total_groups,
        "style_tag":    group.get("style_tag", ""),
    }
    return template.render(**context)


async def render_color_card(
    group: dict,
    group_id: int,
    total_groups: int,
    output_path: Path,
) -> Path:
    """
    將單組配色渲染為 1080×1920 色塊卡片 PNG。

    Args:
        group:        outfit_generator 回傳的單組 dict
        group_id:     第幾組（從 1 開始）
        total_groups: 總組數（通常為 2）
        output_path:  輸出 PNG 路徑

    Returns:
        成功儲存的 PNG Path
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    html = _render_color_card_html(group, group_id, total_groups)

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-gpu"],
            )
            page = await browser.new_page(
                viewport={"width": CARD_WIDTH, "height": CARD_HEIGHT},
            )
            await page.set_content(html, wait_until="networkidle")
            await page.screenshot(
                path=str(output_path),
                clip={"x": 0, "y": 0, "width": CARD_WIDTH, "height": CARD_HEIGHT},
                type="png",
            )
            await browser.close()
    except Exception as e:
        raise RenderError(f"色塊卡片渲染失敗：{e}") from e

    return output_path
