"""Delivery Layer — Telegram Bot

傳送圖片（send_photos）至指定 Telegram Chat ID。
所有 Token / Chat ID 從 .env 載入，timeout=30，retry×3。
"""

import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv
from telegram import Bot, InputMediaPhoto
from telegram.error import TelegramError

load_dotenv(override=True)

_TIMEOUT     = 60
_MAX_RETRIES = 3


class TelegramBotError(Exception):
    """Telegram 傳送失敗"""


def _get_credentials() -> tuple[str, str]:
    token   = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    if not token:
        raise TelegramBotError("TELEGRAM_BOT_TOKEN 未設定，請在 .env 中填入")
    if not chat_id:
        raise TelegramBotError("TELEGRAM_CHAT_ID 未設定，請在 .env 中填入")
    return token, chat_id


async def send_photos(
    image_paths: list[Path],
    caption: str = "",
    *,
    token: str | None = None,
    chat_id: str | None = None,
) -> None:
    """
    以媒體相簿形式傳送多張圖片至 Telegram。
    Telegram 每次最多 10 張，超過自動分批。

    Args:
        image_paths: PNG/JPG 圖片路徑列表
        caption:     第一批的說明文字
        token:       覆蓋預設 Token（供測試使用）
        chat_id:     覆蓋預設 Chat ID（供測試使用）

    Raises:
        TelegramBotError: 憑證缺失、檔案不存在、或重試耗盡後仍失敗
    """
    for p in image_paths:
        if not p.exists():
            raise TelegramBotError(f"圖片不存在：{p}")

    if token is None or chat_id is None:
        token, chat_id = _get_credentials()

    bot = Bot(token=token)

    # 分批（每批最多 10 張）
    batch_size = 10
    batches = [image_paths[i:i + batch_size] for i in range(0, len(image_paths), batch_size)]

    for batch_idx, batch in enumerate(batches):
        last_err: Exception | None = None
        batch_caption = caption[:1024] if (batch_idx == 0 and caption) else ""

        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                async with asyncio.timeout(_TIMEOUT):
                    media = []
                    handles = []
                    for i, p in enumerate(batch):
                        f = open(p, "rb")
                        handles.append(f)
                        media.append(InputMediaPhoto(
                            media=f,
                            caption=batch_caption if i == 0 else "",
                        ))

                    await bot.send_media_group(chat_id=chat_id, media=media)

                    for f in handles:
                        f.close()

                print(f"[telegram_bot] 第 {batch_idx+1}/{len(batches)} 批已傳送（{len(batch)} 張）")
                break

            except TimeoutError:
                last_err = TelegramBotError(f"第 {attempt} 次傳送逾時（>{_TIMEOUT}s）")
                for f in handles:
                    try: f.close()
                    except Exception: pass
                if attempt < _MAX_RETRIES:
                    await asyncio.sleep(2 ** attempt)

            except TelegramError as e:
                last_err = TelegramBotError(f"Telegram API 錯誤：{e}")
                for f in handles:
                    try: f.close()
                    except Exception: pass
                if attempt < _MAX_RETRIES:
                    await asyncio.sleep(2 ** attempt)
        else:
            raise last_err or TelegramBotError("所有重試均失敗")

