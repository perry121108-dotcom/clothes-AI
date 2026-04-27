"""
music_report.py — 本週趨勢曲風參考報告生成器（Task 5.3）

使用方式：
    python music_report.py              # 使用快取或抓取最新資料
    python music_report.py --refresh    # 強制重新抓取

輸出：output/music_report_YYYY-MM-DD.md
"""

import argparse
import asyncio
import sys
from datetime import datetime
from pathlib import Path

from src.data_layer.music_trends import CACHE_FILE, get_music_trends

OUTPUT_DIR = Path(__file__).parent / "output"

# BPM 參考區間（每個曲風的建議 BPM 範圍）
BPM_REFERENCE: dict[str, str] = {
    "energetic": "120–140 BPM",
    "upbeat":    "100–120 BPM",
    "dramatic":  "90–115 BPM",
    "chill":     "70–95 BPM",
    "romantic":  "60–85 BPM",
}

# 曲風標籤建議說明
MOOD_GUIDANCE: dict[str, str] = {
    "energetic": "快節奏、律動強，適合運動、舞蹈類型穿搭短片",
    "upbeat":    "輕快活潑，適合日常通勤、街頭穿搭風格",
    "dramatic":  "情緒張力強，適合高對比色系、前衛造型視覺",
    "chill":     "放鬆慵懶，適合 OOTD、咖啡廳、慢節奏穿搭",
    "romantic":  "柔和抒情，適合浪漫約會、薄紗/蕾絲系穿搭",
}


def _suggest_mood(rank: int, artist: str, title: str) -> str:
    """依排名與關鍵字給出初步曲風建議（人工可覆寫）。"""
    lower_title = title.lower()
    lower_artist = artist.lower()

    # 關鍵字匹配
    if any(k in lower_title for k in ["love", "heart", "miss", "forever", "kiss", "sweet"]):
        return "romantic"
    if any(k in lower_title for k in ["party", "dance", "move", "go", "run", "fire", "wild"]):
        return "energetic"
    if any(k in lower_title for k in ["sad", "cry", "alone", "lose", "pain", "break"]):
        return "dramatic"
    if any(k in lower_title for k in ["chill", "vibe", "slow", "easy", "lazy", "dream"]):
        return "chill"

    # 排名位置作為兜底（前 5 名通常節奏快）
    if rank <= 5:
        return "energetic"
    if rank <= 10:
        return "upbeat"
    return "chill"


def _generate_markdown(tracks: list[dict], report_date: datetime) -> str:
    date_str = report_date.strftime("%Y-%m-%d")
    top10 = tracks[:10]

    lines: list[str] = [
        f"# 本週音樂趨勢曲風參考報告",
        f"",
        f"> 生成日期：{date_str}　｜　資料來源：Billboard Hot 100 / YouTube Trending",
        f"> ⚠️ 本報告僅供曲風參考，**不代表可直接使用版權音樂**。",
        f"> 請依報告曲風至 YouTube Audio Library / Epidemic Sound 搜尋無版權替代曲目。",
        f"",
        f"---",
        f"",
        f"## Top 10 本週趨勢曲目",
        f"",
        f"| 排名 | 曲目 | 歌手 | 來源 | 建議曲風 |",
        f"|:---:|------|------|------|:--------:|",
    ]

    for track in top10:
        rank = track.get("rank", "?")
        title = track.get("title", "Unknown")
        artist = track.get("artist", "Unknown")
        source = track.get("source", "—")
        mood = _suggest_mood(
            int(rank) if str(rank).isdigit() else 99,
            artist, title
        )
        lines.append(f"| {rank} | {title} | {artist} | {source} | `{mood}` |")

    lines += [
        f"",
        f"---",
        f"",
        f"## BPM 參考區間",
        f"",
        f"| 曲風標籤 | BPM 範圍 | 適用場景 |",
        f"|:--------:|---------|---------|",
    ]
    for mood, bpm in BPM_REFERENCE.items():
        guidance = MOOD_GUIDANCE[mood]
        lines.append(f"| `{mood}` | {bpm} | {guidance} |")

    lines += [
        f"",
        f"---",
        f"",
        f"## 本週穿搭曲風建議",
        f"",
        f"根據本週榜單分佈，建議本週影片優先使用以下曲風：",
        f"",
    ]

    # 統計各 mood 出現次數
    mood_counts: dict[str, int] = {}
    for track in top10:
        rank = int(track["rank"]) if str(track.get("rank", 0)).isdigit() else 99
        m = _suggest_mood(rank, track.get("artist", ""), track.get("title", ""))
        mood_counts[m] = mood_counts.get(m, 0) + 1

    for mood, count in sorted(mood_counts.items(), key=lambda x: -x[1]):
        pct = round(count / len(top10) * 100)
        lines.append(f"- **`{mood}`** — Top 10 中 {count} 首（{pct}%）")

    lines += [
        f"",
        f"---",
        f"",
        f"## 操作指引",
        f"",
        f"1. 對照上方曲風標籤，至以下平台搜尋對應 BPM 的無版權音樂：",
        f"   - [YouTube Audio Library](https://studio.youtube.com/channel/UC/music)",
        f"   - [Epidemic Sound](https://www.epidemicsound.com/)",
        f"   - [Pixabay Music](https://pixabay.com/music/)",
        f"2. 下載後放入 `assets/music/approved/` 資料夾",
        f"3. 在 `assets/music/music_metadata.json` 的 `tracks` 陣列中登記：",
        f"   ```json",
        f'   {{"filename": "your_track.mp3", "mood": "chill", "title": "Track Name", "source": "YouTube Audio Library", "license": "Creative Commons"}}',
        f"   ```",
        f"4. 執行 `python main.py` 即可自動匹配使用",
        f"",
        f"---",
        f"*由 music_report.py 自動生成於 {datetime.now().strftime('%Y-%m-%d %H:%M')}*",
    ]

    return "\n".join(lines)


async def main(force_refresh: bool = False) -> Path:
    """抓取趨勢資料並生成 Markdown 報告。"""
    print("[music_report] 載入音樂趨勢資料...")
    tracks = await get_music_trends(force_refresh=force_refresh)
    print(f"[music_report] 取得 {len(tracks)} 首曲目")

    report_date = datetime.now()
    markdown = _generate_markdown(tracks, report_date)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"music_report_{report_date.strftime('%Y-%m-%d')}.md"
    out_path.write_text(markdown, encoding="utf-8")

    print(f"[music_report] 報告已儲存至：{out_path}")
    return out_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="生成本週音樂趨勢曲風參考報告")
    parser.add_argument("--refresh", action="store_true", help="強制重新抓取，忽略快取")
    args = parser.parse_args()
    asyncio.run(main(force_refresh=args.refresh))
