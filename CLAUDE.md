# CLAUDE.md — Daily AI Outfit Shorts Generator 全域行為準則

## 核心準則

1. **Document-Driven**：任何架構變更必須先更新 `PROJECT_RULES.md`，再動程式碼。
2. **Single Task Focus**：每次開發僅讀取 `TASK.md` 中第一個 `[ ]` 狀態的任務。絕不跳躍開發。
3. **Role Awareness**：每次回應開頭必須標示當前角色，例如 `[Builder] Task 1.3 開始`。
4. **No Self-Completion**：Builder 不得自行將任務勾選為 `[x]`，只有 Liaison 可以。

## 設計標準

- **Render Layer** 必須以現代 IG/Shorts 視覺美學為標準：留白、極簡、高對比，字體不超過 2 種。
- 色彩方案必須從 Claude API 輸出的 `color_palette` 動態注入，不得硬編碼顏色。

## 技術守則

- 所有 API Key 存放於 `.env`，透過 `python-dotenv` 載入，嚴禁 Hard-code。
- 所有外部 API 呼叫必須設定 `timeout=30` 與最多 `retry=3`。
- FFmpeg 指令必須依賴 `ffmpeg-python` 官方 API，不得拼接 shell 字串（防止 Command Injection）。
- Playwright 使用 `async` 模式執行截圖，避免阻塞主流程。

## 音樂版權守則（重要）

- **絕對禁止**直接下載或使用版權音樂（Billboard Top 10 等）作為影片音軌。
- `assets/music/trends/` 目錄僅存放「參考清單 JSON」，不存放音樂檔案。
- `assets/music/approved/` 只存放人工確認版權釋放的音樂，每首需在 `music_metadata.json` 登記。

## ❌ 禁止事項

- 不可在 V1.0 實作任何社群平台（YouTube / IG / TikTok）自動發布 API。
- 不可跳過 Tester 驗證直接進入下一個 Task。
- 不可在未釐清需求前變更 `PROJECT_RULES.md` 的技術棧。
- 不可使用 `subprocess` 或 shell string 執行 FFmpeg（使用 `ffmpeg-python`）。
- 嚴禁在程式碼中寫入任何 API Key、Token 或密碼。
