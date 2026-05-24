"""
Render Layer — AI Image Generator (Color Card + Outfit Photo)
==============================================================
使用 Gemini 圖像生成兩類圖片：

1. 色卡 (Color Card)：
   三橫條色塊，中性背景，無文字，極簡平面設計風格

2. 穿搭照 (Outfit Photo)：
   全白無臉人形模特，工作室背景，手插口袋，展示服裝配色

兩者均有 PIL 色塊漸層作為 fallback。
"""

import asyncio
import io
import os
from pathlib import Path

from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont

load_dotenv(override=True)

_IMG_MODEL  = "gemini-2.5-flash-image"
CARD_WIDTH  = 1080
CARD_HEIGHT = 1920

# 圖像生成模板已抽離為獨立外部檔案（內容 100% 等價），於模組載入時讀取。
_PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"
_COLOR_CARD_TEMPLATE = open(_PROMPTS_DIR / "服裝色卡模板.txt", "r", encoding="utf-8").read()
_OUTFIT_PHOTO_TEMPLATE = open(_PROMPTS_DIR / "穿搭照模板.txt", "r", encoding="utf-8").read()


# ── 顏色工具 ──────────────────────────────────────────────────────────────────

def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


# ── Prompt 建構（固定格式，顏色每日隨機）────────────────────────────────────

def build_color_card_prompt(group: dict) -> str:
    """
    色卡 Prompt：三橫條色塊，中性背景，無文字，平面設計風格。
    格式參考用戶規範，顏色由 outfit_generator 動態產生。
    """
    top    = group["top"]
    bottom = group["bottom"]
    shoes  = group["shoes"]
    return _COLOR_CARD_TEMPLATE.format(
        top_name=top["name"], top_hex=top["hex"],
        bottom_name=bottom["name"], bottom_hex=bottom["hex"],
        shoes_name=shoes["name"], shoes_hex=shoes["hex"],
    )


def build_outfit_photo_prompt(group: dict) -> str:
    """
    穿搭照 Prompt：全白人形模特，工作室環境，手插口袋，無臉。
    格式參考用戶規範，服裝顏色由 outfit_generator 動態產生。
    """
    top    = group["top"]
    bottom = group["bottom"]
    shoes  = group["shoes"]
    return _OUTFIT_PHOTO_TEMPLATE.format(
        top_name=top["name"], top_type=top["type"], top_hex=top["hex"],
        bottom_name=bottom["name"], bottom_type=bottom["type"], bottom_hex=bottom["hex"],
        shoes_name=shoes["name"], shoes_type=shoes["type"], shoes_hex=shoes["hex"],
    )


# ── PIL Fallback ──────────────────────────────────────────────────────────────

def _make_color_card_fallback(group: dict, output_path: Path) -> Path:
    """三色橫條佔位圖（Gemini 失敗時使用）。"""
    top_rgb    = _hex_to_rgb(group["top"]["hex"])
    bottom_rgb = _hex_to_rgb(group["bottom"]["hex"])
    shoes_rgb  = _hex_to_rgb(group["shoes"]["hex"])

    img  = Image.new("RGB", (CARD_WIDTH, CARD_HEIGHT), (247, 245, 242))
    draw = ImageDraw.Draw(img)

    # 留邊距，三橫條居中
    margin_x = 90
    margin_y = 240
    bar_w = CARD_WIDTH - margin_x * 2
    total_h = CARD_HEIGHT - margin_y * 2
    h1 = int(total_h * 0.30)
    h2 = int(total_h * 0.40)
    h3 = total_h - h1 - h2

    y0 = margin_y
    draw.rectangle([margin_x, y0,          margin_x + bar_w, y0 + h1],          fill=top_rgb)
    draw.rectangle([margin_x, y0 + h1,     margin_x + bar_w, y0 + h1 + h2],     fill=bottom_rgb)
    draw.rectangle([margin_x, y0 + h1+h2,  margin_x + bar_w, y0 + h1 + h2 + h3], fill=shoes_rgb)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(output_path), "PNG")
    return output_path


def _make_outfit_photo_fallback(group: dict, output_path: Path) -> Path:
    """三色漸層穿搭佔位圖（Gemini 失敗時使用）。"""
    top_rgb    = _hex_to_rgb(group["top"]["hex"])
    bottom_rgb = _hex_to_rgb(group["bottom"]["hex"])
    shoes_rgb  = _hex_to_rgb(group["shoes"]["hex"])

    img  = Image.new("RGB", (CARD_WIDTH, CARD_HEIGHT), (220, 220, 215))
    draw = ImageDraw.Draw(img)

    # 模擬穿著比例：上衣40%、下裝40%、鞋子20%
    h1 = int(CARD_HEIGHT * 0.40)
    h2 = int(CARD_HEIGHT * 0.40)
    h3 = CARD_HEIGHT - h1 - h2

    draw.rectangle([0, 0,       CARD_WIDTH, h1],           fill=top_rgb)
    draw.rectangle([0, h1,      CARD_WIDTH, h1 + h2],      fill=bottom_rgb)
    draw.rectangle([0, h1 + h2, CARD_WIDTH, CARD_HEIGHT],  fill=shoes_rgb)

    # 半透明深色遮罩
    overlay = Image.new("RGBA", (CARD_WIDTH, CARD_HEIGHT), (0, 0, 0, 70))
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(img)

    # 中心提示文字
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 56)
    except Exception:
        font = ImageFont.load_default()
    draw.text(
        (CARD_WIDTH // 2, CARD_HEIGHT // 2),
        group.get("style_tag", "穿搭示範"),
        fill=(255, 255, 255, 200), font=font, anchor="mm",
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(output_path), "PNG")
    return output_path


# ── Gemini 圖像生成核心 ───────────────────────────────────────────────────────

async def _generate_image(
    prompt: str,
    output_path: Path,
    fallback_fn,
    group: dict,
    label: str,
    max_retries: int = 2,
) -> Path:
    """通用 Gemini 圖像生成，失敗時呼叫 fallback_fn。"""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print(f"[photo_gen] GEMINI_API_KEY 未設定，{label} 使用佔位圖")
        return fallback_fn(group, output_path)

    try:
        from google import genai
        from google.genai import types as gtypes
    except ImportError:
        print(f"[photo_gen] google-genai 未安裝，{label} 使用佔位圖")
        return fallback_fn(group, output_path)

    client    = genai.Client(api_key=api_key)
    last_err  = None

    for attempt in range(1, max_retries + 1):
        try:
            loop = asyncio.get_event_loop()
            response = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: client.models.generate_content(
                        model=_IMG_MODEL,
                        contents=prompt,
                        config=gtypes.GenerateContentConfig(
                            response_modalities=["IMAGE"],
                        ),
                    ),
                ),
                timeout=45.0,
            )

            image_bytes = None
            for part in response.candidates[0].content.parts:
                if hasattr(part, "inline_data") and part.inline_data:
                    image_bytes = part.inline_data.data
                    break

            if not image_bytes:
                raise RuntimeError("Gemini 未回傳圖像 bytes")

            img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            # 保持原比例縮放至能覆蓋目標尺寸，再置中裁切為 1080×1920
            from PIL import ImageOps
            img = ImageOps.fit(img, (CARD_WIDTH, CARD_HEIGHT), Image.LANCZOS)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            img.save(str(output_path), "PNG")
            print(f"[photo_gen] {label} 生成成功")
            return output_path

        except asyncio.TimeoutError:
            last_err = f"第 {attempt} 次逾時"
            print(f"[photo_gen] {label} {last_err}")
        except Exception as e:
            last_err = str(e)
            print(f"[photo_gen] {label} 第 {attempt} 次失敗：{e}")

        if attempt < max_retries:
            await asyncio.sleep(3)

    print(f"[photo_gen] {label} 所有重試失敗，使用佔位圖")
    return fallback_fn(group, output_path)


# ── 公開介面 ──────────────────────────────────────────────────────────────────

async def generate_color_card(group: dict, output_path: Path) -> Path:
    """
    AI 生成色卡圖片（三橫條色塊，無文字，中性背景）。

    Args:
        group:       outfit_generator 回傳的單組 dict
        output_path: 輸出 PNG 路徑

    Returns:
        PNG Path（AI 生成或佔位圖）
    """
    prompt = build_color_card_prompt(group)
    return await _generate_image(
        prompt, output_path,
        _make_color_card_fallback, group,
        f"色卡 第{group['id']}組",
    )


async def generate_outfit_photo(group: dict, output_path: Path) -> Path:
    """
    AI 生成穿搭照（白色人形模特，工作室背景，無臉）。

    Args:
        group:       outfit_generator 回傳的單組 dict
        output_path: 輸出 PNG 路徑

    Returns:
        PNG Path（AI 生成或佔位圖）
    """
    prompt = build_outfit_photo_prompt(group)
    return await _generate_image(
        prompt, output_path,
        _make_outfit_photo_fallback, group,
        f"穿搭照 第{group['id']}組",
    )
