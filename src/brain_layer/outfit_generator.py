"""
Brain Layer — Outfit Generator (2-Group Color Style)
=====================================================
呼叫 Gemini API，生成 2 組男生夏季配色方案。
每組包含上衣/下裝/鞋子的顏色名稱、HEX、單品類型，
以及給 AI 圖像生成使用的 photo_prompt。
"""

import asyncio
import json
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv(override=True)

MUSIC_MOODS = ["energetic", "chill", "romantic", "upbeat", "dramatic"]
_MODEL = "gemini-2.5-flash-lite"

# 提示詞已抽離為獨立外部檔案（內容 100% 等價），於模組載入時讀取。
_PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"
SYSTEM_PROMPT = open(_PROMPTS_DIR / "男裝造型師_系統.txt", "r", encoding="utf-8").read()
USER_PROMPT_TEMPLATE = open(_PROMPTS_DIR / "男裝造型師_用戶模板.txt", "r", encoding="utf-8").read()

# ── Gemini JSON Schema ────────────────────────────────────────────────────────

_GARMENT = types.Schema(
    type=types.Type.OBJECT,
    properties={
        "hex":  types.Schema(type=types.Type.STRING),
        "name": types.Schema(type=types.Type.STRING),
        "type": types.Schema(type=types.Type.STRING),
    },
    required=["hex", "name", "type"],
)

_GROUP = types.Schema(
    type=types.Type.OBJECT,
    properties={
        "id":           types.Schema(type=types.Type.INTEGER),
        "style_tag":    types.Schema(type=types.Type.STRING),
        "top":          _GARMENT,
        "bottom":       _GARMENT,
        "shoes":        _GARMENT,
        "photo_prompt": types.Schema(type=types.Type.STRING),
        "caption":      types.Schema(type=types.Type.STRING),
        "music_mood":   types.Schema(type=types.Type.STRING),
    },
    required=["id", "style_tag", "top", "bottom", "shoes", "photo_prompt", "caption", "music_mood"],
)

_RESPONSE_SCHEMA = types.Schema(
    type=types.Type.OBJECT,
    properties={
        "groups": types.Schema(type=types.Type.ARRAY, items=_GROUP),
    },
    required=["groups"],
)

_HEX_RE = re.compile(r"^#([0-9A-Fa-f]{6})$")


# ── 例外 ──────────────────────────────────────────────────────────────────────

class OutfitGeneratorError(Exception):
    pass

class SchemaValidationError(OutfitGeneratorError):
    pass


# ── 驗證 ──────────────────────────────────────────────────────────────────────

def _validate(data: dict) -> None:
    groups = data.get("groups", [])
    if not isinstance(groups, list) or len(groups) != 2:
        raise SchemaValidationError(f"groups 必須恰好 2 組，目前：{len(groups) if isinstance(groups, list) else '非列表'}")
    for i, g in enumerate(groups):
        for key in ["id", "style_tag", "top", "bottom", "shoes", "photo_prompt"]:
            if key not in g:
                raise SchemaValidationError(f"第 {i+1} 組缺少欄位：{key}")
        for slot in ["top", "bottom", "shoes"]:
            garment = g[slot]
            for sub in ["hex", "name", "type"]:
                if sub not in garment:
                    raise SchemaValidationError(f"第 {i+1} 組 {slot} 缺少：{sub}")
            # 自動修正 6 位 hex（有時 Gemini 回傳 #RGB）
            h = garment["hex"].strip()
            if len(h) == 4:  # #RGB → #RRGGBB
                h = "#" + "".join(c*2 for c in h[1:])
                garment["hex"] = h
            if not _HEX_RE.match(h):
                raise SchemaValidationError(f"第 {i+1} 組 {slot}.hex 格式錯誤：{h!r}")


# ── Prompt 組裝 ───────────────────────────────────────────────────────────────

def _build_prompt(weather: dict, trends: list[str], festival: str | None) -> str:
    return USER_PROMPT_TEMPLATE.format(
        city=weather.get("city", "未知"),
        temperature=weather.get("temperature", "N/A"),
        condition=weather.get("condition", "晴"),
        festival=festival or "無",
        trends="、".join(trends[:5]) if trends else "無",
    )


# ── 主函式 ────────────────────────────────────────────────────────────────────

async def generate_outfit(
    weather: dict,
    trends: list[str],
    festival: str | None,
    *,
    max_retries: int = 3,
) -> dict:
    """
    回傳含 2 組配色的 dict：{"groups": [...]}
    每組：{id, style_tag, top, bottom, shoes, photo_prompt, caption, music_mood}
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise OutfitGeneratorError("GEMINI_API_KEY 未設定")

    client = genai.Client(api_key=api_key)
    prompt = f"{SYSTEM_PROMPT}\n\n{_build_prompt(weather, trends, festival)}"
    last_error: Exception | None = None

    for attempt in range(1, max_retries + 1):
        try:
            loop = asyncio.get_event_loop()
            response = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: client.models.generate_content(
                        model=_MODEL,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            response_schema=_RESPONSE_SCHEMA,
                        ),
                    ),
                ),
                timeout=30.0,
            )

            raw = response.text
            if not raw:
                raise SchemaValidationError("Gemini 回應為空")

            data = json.loads(raw)
            _validate(data)
            return data

        except asyncio.TimeoutError:
            last_error = OutfitGeneratorError(f"第 {attempt} 次逾時")
            print(f"[outfit_generator] 第 {attempt}/{max_retries} 次逾時")
        except SchemaValidationError:
            raise
        except Exception as e:
            err = str(e)
            if "API_KEY_INVALID" in err or "PERMISSION_DENIED" in err:
                raise OutfitGeneratorError(f"Gemini 認證失敗：{e}") from e
            last_error = OutfitGeneratorError(f"第 {attempt} 次錯誤（{type(e).__name__}）：{e}")
            print(f"[outfit_generator] 第 {attempt}/{max_retries} 次失敗：{e}")

        if attempt < max_retries:
            await asyncio.sleep(2 ** attempt)

    raise last_error or OutfitGeneratorError("所有重試均失敗")
