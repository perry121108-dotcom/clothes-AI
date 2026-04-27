"""Daily AI Outfit Image Generator — 每日穿搭圖片生成

執行流程：
  1. 冪等性檢查（Lock 機制）
  2. Data Layer：天氣 / 趨勢 / 節慶
  3. Brain Layer：Gemini 生成 4 組配色 JSON
  4. Render Layer（×4）：色塊卡片 PNG（Playwright，含顏色文字標籤）
  5. Render Layer（×4）：AI 穿搭照 PNG（Gemini，白色人形模特）
  6. Delivery Layer：Telegram 傳送 8 張圖片
  7. 寫入 Lock 檔案

輸出：output/YYYY-MM-DD_card_1~4.png + output/YYYY-MM-DD_photo_1~4.png
"""

import asyncio
import io
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

load_dotenv(override=True)

OUTPUT_DIR = Path("output")


# ── 冪等性 Lock ───────────────────────────────────────────────────────────────

def _lock_path(date: datetime) -> Path:
    return OUTPUT_DIR / f"{date.strftime('%Y-%m-%d')}.lock"

def _check_lock(date: datetime) -> bool:
    return _lock_path(date).exists()

def _write_lock(date: datetime) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    _lock_path(date).write_text(
        f"generated_at={datetime.now().isoformat()}\n", encoding="utf-8"
    )


# ── 主流程 ────────────────────────────────────────────────────────────────────

async def _run() -> None:
    today    = datetime.now()
    date_str = today.strftime("%Y-%m-%d")

    # ── Step 1：冪等性檢查 ──
    if _check_lock(today):
        print(f"[main] 今日已生成（{date_str}），跳過。刪除 {_lock_path(today)} 可重新生成")
        return

    # ── Step 2：Data Layer ──
    print("[Data Layer] 抓取天氣、趨勢、節慶...")
    try:
        from src.data_layer.weather   import get_weather,        WeatherError
        from src.data_layer.trends    import get_trends,         TrendsError
        from src.data_layer.festivals import get_today_festival, FestivalsError

        weather, trends = await asyncio.gather(get_weather(), get_trends())
        festival = get_today_festival(today.date())

    except WeatherError  as e: print(f"[Data Layer / weather] 錯誤：{e}",   file=sys.stderr); sys.exit(1)
    except TrendsError   as e: print(f"[Data Layer / trends] 錯誤：{e}",    file=sys.stderr); sys.exit(1)
    except FestivalsError as e: print(f"[Data Layer / festivals] 錯誤：{e}", file=sys.stderr); sys.exit(1)

    print(f"  天氣：{weather.get('city')} {weather.get('temperature')}°C {weather.get('condition')}")
    print(f"  節慶：{festival or '無'}")

    # ── Step 3：Brain Layer ──
    print("[Brain Layer] 生成 4 組配色方案...")
    try:
        from src.brain_layer.outfit_generator import generate_outfit, OutfitGeneratorError
        outfit_data = await generate_outfit(weather, trends, festival)
    except OutfitGeneratorError as e:
        print(f"[Brain Layer] 錯誤：{e}", file=sys.stderr); sys.exit(1)

    groups  = outfit_data["groups"]
    caption = next((g.get("caption", "") for g in groups if g.get("caption")), "今日穿搭 #OOTD #男生穿搭")
    print(f"  生成 {len(groups)} 組：" + " / ".join(f"{g['style_tag']}" for g in groups))

    # ── Step 4：色塊卡片（Playwright HTML，含顏色名稱+衣物類別文字）──
    print("[Render Layer] 生成色塊卡片（含文字標籤）...")
    try:
        from src.render_layer.renderer import render_color_card, RenderError
        card_paths = list(await asyncio.gather(*[
            render_color_card(
                g, g["id"], len(groups),
                OUTPUT_DIR / f"{date_str}_card_{g['id']}.png",
            )
            for g in groups
        ]))
    except RenderError as e:
        print(f"[Render Layer] 色塊卡片錯誤：{e}", file=sys.stderr); sys.exit(1)

    print(f"  OK: {len(card_paths)} 張色塊卡片")

    # ── Step 5：AI 穿搭照（白色人形模特）──
    print("[Photo Gen] 生成 AI 穿搭照...")
    from src.render_layer.outfit_photo_generator import generate_outfit_photo
    photo_paths = list(await asyncio.gather(*[
        generate_outfit_photo(g, OUTPUT_DIR / f"{date_str}_photo_{g['id']}.png")
        for g in groups
    ]))
    print(f"  OK: {len(photo_paths)} 張穿搭照")

    # ── Step 6：Telegram 傳送 8 張圖片（色卡+穿搭照交替）──
    n = len(groups) * 2
    print(f"[Delivery Layer] 傳送 {n} 張圖片至 Telegram...")
    sequence = []
    for card, photo in zip(card_paths, photo_paths):
        sequence.append(card)
        sequence.append(photo)

    try:
        from src.delivery_layer.telegram_bot import send_photos, TelegramBotError
        await send_photos(sequence, caption=caption)
    except TelegramBotError as e:
        print(f"[Delivery Layer] 錯誤：{e}", file=sys.stderr); sys.exit(1)

    # ── Step 7：Lock ──
    _write_lock(today)
    print(f"[main] 完成！{n} 張圖片已儲存至 output/，Lock：{_lock_path(today)}")
    print(f"  色塊卡片：" + ", ".join(p.name for p in card_paths))
    print(f"  穿搭照片：" + ", ".join(p.name for p in photo_paths))


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
