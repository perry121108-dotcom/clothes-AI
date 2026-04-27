# TASK.md — Daily AI Outfit Shorts Generator 任務進度表

## 狀態說明
- [ ] 未開始
- [/] 進行中（需附上目前進度說明）
- [x] 已完成（需通過 Tester 驗證，由 Liaison 勾選）

---

## Task 1: 基礎環境建置與 Data Layer
**[Builder] 負責 → [Tester] 驗證**

- [x] 1.1 建立專案目錄結構（依 `PROJECT_RULES.md` 中的目錄規範）
- [x] 1.2 建立 `requirements.txt` 並安裝所有依賴
- [x] 1.3 實作 `src/data_layer/weather.py`：呼叫 OpenWeatherMap API，回傳結構化天氣 dict
- [x] 1.4 實作 `src/data_layer/trends.py`：抓取 Vogue RSS，生成月快取 `cache/trends_cache.json`（可先用 Mock data）
- [x] 1.5 實作 `src/data_layer/festivals.py`：載入靜態節慶 JSON，回傳當日節慶名稱（無則回傳 None）

**AC（驗收標準）：**
- `weather.py` 能成功回傳含 `temperature`, `condition`, `humidity` 欄位的 dict。✅
- `trends_cache.json` 存在且包含至少 5 個趨勢關鍵字。✅
- `festivals.py` 在已知節慶日回傳正確名稱，非節慶日回傳 None。✅
- 所有模組執行無例外，API 失敗時拋出帶訊息的自訂例外。✅

**Tester 驗證紀錄：** `tests/test_data_layer.py` 全數通過（含於 Task 4 全套 104 passed）
**Liaison 確認日期：** 2026-04-26

---

## Task 2: Brain Layer（AI 邏輯核心）
**[Builder] 負責 → [Tester] 驗證**

- [x] 2.1 設計 Prompt 模板，整合天氣、趨勢、節慶三個變數
- [x] 2.2 實作 `src/brain_layer/outfit_generator.py`：呼叫 Claude API，穩定輸出結構化 JSON
- [x] 2.3 定義並驗證輸出 JSON Schema（含 style, items, color_palette, caption, music_mood 欄位）

**AC（驗收標準）：**
- 連續呼叫 3 次，每次皆輸出符合 Schema 的合法 JSON（無 hallucination 欄位缺失）。✅
- `music_mood` 欄位值必須為預定義標籤之一（`["energetic", "chill", "romantic", "upbeat", "dramatic"]`）。✅
- API 超時（>30s）時自動 Retry，最多 3 次，仍失敗則拋出例外。✅

**Tester 驗證紀錄：** `tests/test_brain_layer.py` 全數通過（含於 Task 4 全套 104 passed）
**Liaison 確認日期：** 2026-04-26

---

## Task 3: Render Layer（視覺渲染引擎）
**[Builder] 負責 → [Tester] 驗證**

- [x] 3.1 設計 `assets/templates/outfit_card.html`：雜誌風排版，支援 Jinja2 模板變數注入
- [x] 3.2 實作 `src/render_layer/renderer.py`：Playwright headless 截圖 → 1080x1920 PNG
- [x] 3.3 視覺規範：留白充足、字體對比清晰、符合 IG/Shorts 直式美學

**AC（驗收標準）：**
- 輸出 PNG 解析度精確為 1080x1920。✅
- 模板正確渲染風格名稱、單品列表、配色色塊與文案。✅
- 於無顯示器的 headless 環境下執行無報錯。✅

**Tester 驗證紀錄：** `tests/test_render_layer.py` 25 passed（2026-04-26 交接確認）
**Liaison 確認日期：** 2026-04-26

---

## Task 4: Media Layer（影音合成）
**[Builder] 負責 → [Tester] 驗證**

- [x] 4.1 實作 `src/media_layer/tts.py`：使用 Edge TTS 將 caption 轉為 MP3 語音
- [x] 4.2 實作 `src/media_layer/music_selector.py`：根據 `music_mood` 從 `assets/music/approved/` 匹配音樂
- [x] 4.3 實作 `src/media_layer/video_composer.py`：FFmpeg 合成 PNG + 背景音樂 + TTS 語音 → ≤15 秒 MP4
- [x] 4.4 輸出規格：1080x1920、H.264、AAC 音訊、時長 10–15 秒

**AC（驗收標準）：**
- 輸出 MP4 可在手機正常播放，時長 ≤ 15 秒。✅
- 語音與畫面同步，背景音樂音量低於語音（-12dB 差）。✅
- `approved/` 資料夾為空時，系統使用預設靜音或提示警告，不崩潰。✅

**Tester 驗證紀錄：** `tests/test_media_layer.py` 34 passed，全套 104 passed 5 skipped（2026-04-26）
**Liaison 確認日期：** 2026-04-26

---

## Task 5: Music Trend Layer（音樂趨勢半自動機制）
**[Builder] 負責 → [Tester] 驗證**

- [x] 5.1 實作 `src/data_layer/music_trends.py`：每週抓取 Billboard Hot 100 RSS，存入 `assets/music/trends/music_trends.json`
- [x] 5.2 實作 YouTube Shorts Charts 抓取（或備援：抓取公開 chart 頁面）
- [x] 5.3 實作 `music_report.py`：生成「本週趨勢曲風參考報告」（Markdown 格式，含 Top 10 曲目、BPM 參考、建議曲風標籤）
- [x] 5.4 建立 `assets/music/music_metadata.json`：人工填寫已審核音樂的曲風標籤結構

**AC（驗收標準）：**
- `music_trends.json` 包含至少 10 首曲目，含歌手名與排名。✅
- `music_report.md` 自動生成於 `output/` 資料夾中。✅
- `music_selector.py` 能根據 `music_mood` 從 metadata 正確匹配音樂（測試用 Mock metadata）。✅

**Tester 驗證紀錄：** `tests/test_music_trends.py` 25 passed；全套 129 passed 5 skipped（2026-04-26）
**Liaison 確認日期：** 2026-04-26

---

## Task 6: Delivery Layer（半自動派發機制）
**[Builder] 負責 → [Tester] 驗證**

- [/] 6.1 實作 `src/delivery_layer/telegram_bot.py`：傳送 MP4 至指定 Telegram Chat ID（進行中 2026-04-26）
- [/] 6.2 實作冪等性 Lock 機制：`output/YYYY-MM-DD.lock` 防止重複執行（進行中 2026-04-26）
- [/] 6.3 實作 `main.py`：串接所有 Layer，單一命令執行完整流程（進行中 2026-04-26）

**AC（驗收標準）：**
- MP4 成功傳送至測試手機的 Telegram。
- 同一天執行第二次時，系統輸出提示「今日已生成，跳過」並安全退出。
- `main.py` 執行失敗時，輸出清晰的錯誤訊息（含失敗的 Layer 名稱）。
