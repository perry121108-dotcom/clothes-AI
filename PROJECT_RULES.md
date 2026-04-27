# PROJECT_RULES.md — Daily AI Outfit Shorts Generator (V1.0 - Semi-Auto)

## 1. 專案名稱
Daily AI Outfit Shorts Generator — 每日 AI 穿搭短影音自動生成系統

## 2. 專案目標
- **解決的問題**：每日手動製作穿搭內容費時費力，透過 AI 自動化生成 15 秒 Shorts 格式短影音。
- **目標使用者**：穿搭內容創作者（初期為開發者本人進行 QA）。
- **成功衡量標準**：腳本執行一次，可輸出一支符合 Shorts 規格的 MP4 並自動傳送至手機。

## 3. 開發範圍 (V1.0)

### ✅ In Scope
- 自動抓取指定地點當日天氣
- 每月更新一次時尚趨勢快取（Vogue RSS + Pinterest Trends）
- 識別當日節慶（靜態 JSON 清單）
- Claude API 生成穿搭建議 JSON（含風格、單品、配色、文案）
- Playwright (Python) 截圖 HTML/CSS 模板 → 1080x1920 PNG
- FFmpeg 合成 PNG + 音樂 + Edge TTS 語音 → 15 秒 MP4
- 每週自動抓取流行音樂 Top 10 清單（Billboard RSS + YouTube Charts）
- 音樂半自動審核：人工確認後放入 `assets/music/approved/` 供系統使用
- Telegram Bot 傳送 MP4 至開發者手機供人工 QA

### 🚫 Out of Scope (V1.0)
- 直接發布至 YouTube / Instagram / TikTok
- 複雜影片轉場與 3D 動畫
- 多使用者帳號管理
- 網頁後台介面

## 4. 技術棧

| 層級 | 技術 | 說明 |
|------|------|------|
| Runtime | Python 3.11+ | 與 ai_sop_toolkit 工具鏈一致 |
| LLM Engine | Anthropic API (Claude 3.5 Sonnet) | 穿搭建議生成 |
| 天氣資料 | OpenWeatherMap API | 免費方案足夠 |
| 趨勢資料 | Vogue RSS + Pinterest Trends | 月快取 |
| 音樂趨勢 | Billboard Hot 100 RSS + YouTube Charts | 週快取，僅參考 |
| 渲染引擎 | Playwright (Python) | HTML/CSS → PNG，替代 Puppeteer |
| 影音合成 | ffmpeg-python | 靜態圖 + 音樂 + TTS |
| TTS | Edge TTS (`edge-tts`) | 免費、中文支援佳、無需 API Key |
| 通知推送 | Telegram Bot API (`python-telegram-bot`) | 半自動派發 |
| 環境管理 | python-dotenv | 管理 API Keys |

## 5. 目錄結構
```
clothes-ai/
├── src/
│   ├── data_layer/          # 天氣、趨勢、節慶資料抓取
│   ├── brain_layer/         # Claude API Prompt 邏輯
│   ├── render_layer/        # HTML 模板 + Playwright 截圖
│   ├── media_layer/         # FFmpeg + Edge TTS 合成
│   └── delivery_layer/      # Telegram Bot 傳送
├── assets/
│   ├── templates/           # HTML/CSS 排版模板
│   └── music/
│       ├── approved/        # 人工審核通過的版權音樂
│       └── trends/          # 每週音樂趨勢快取 (music_trends.json)
├── cache/
│   ├── weather_cache.json
│   ├── trends_cache.json
│   └── festivals.json       # 節慶靜態清單
├── output/                  # 每日生成的 PNG 與 MP4
├── tests/
├── .env                     # API Keys (gitignore)
├── main.py                  # 主入口
└── requirements.txt
```

## 6. 冪等性設計
- 每日執行前檢查 `output/YYYY-MM-DD.lock`，若存在則跳過，防止重複生成。

## 7. 嚴格限制
- **絕對禁止** V1.0 開發任何社群平台自動發布 API。
- 所有 API Key 必須存放於 `.env`，禁止 Hard-code。
- 所有非同步操作必須包含 Timeout（預設 30 秒）與 Retry（最多 3 次）機制。
- `assets/music/approved/` 中的音樂必須確認為版權釋放或已取得授權。

## 8. 音樂版權策略
1. 系統每週自動抓取 Billboard Hot 100 + YouTube Shorts 趨勢榜單 → 存入 `music_trends.json`。
2. 系統產出「本週趨勢曲風參考報告」（不下載版權音樂）。
3. 開發者根據報告，從 YouTube Audio Library / Epidemic Sound 下載對應曲風的**版權釋放**音樂。
4. 將審核通過的 MP3 放入 `assets/music/approved/`，並在 `music_metadata.json` 中標記曲風標籤。
5. 系統根據當日穿搭風格自動從 `approved/` 中匹配最適合的曲目。
