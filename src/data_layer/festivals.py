import json
from datetime import date
from pathlib import Path

FESTIVALS_FILE = Path("cache/festivals.json")


class FestivalsError(Exception):
    pass


def get_today_festival(target_date: date | None = None) -> str | None:
    """Return festival name for the given date, or None if not a festival day.

    Checks YYYY-MM-DD first (one-time events), then MM-DD (annual recurring).
    """
    if not FESTIVALS_FILE.exists():
        raise FestivalsError(f"Festivals file not found: {FESTIVALS_FILE}")

    try:
        festivals: dict[str, str] = json.loads(
            FESTIVALS_FILE.read_text(encoding="utf-8")
        )
    except json.JSONDecodeError as e:
        raise FestivalsError(f"Invalid festivals.json: {e}") from e

    today = target_date or date.today()
    key_full = today.strftime("%Y-%m-%d")
    key_mmdd = today.strftime("%m-%d")

    return festivals.get(key_full) or festivals.get(key_mmdd)
