# clothes AI

[![CI](https://github.com/perry121108-dotcom/clothes-AI/actions/workflows/ci.yml/badge.svg)](https://github.com/perry121108-dotcom/clothes-AI/actions/workflows/ci.yml)
[![Tests](https://img.shields.io/badge/tests-65%20passing-brightgreen)](#test)
[![Python](https://img.shields.io/badge/python-3.12-blue)](https://www.python.org/)

**AI 每日穿搭內容生成自動化工作流。** 根據天氣、趨勢與季節條件，自動生成穿搭組合、渲染色卡與模特圖，並透過 Telegram 推送每日報告。

An end-to-end AI automation workflow: reads live conditions → generates outfits → renders visual assets → delivers via Telegram. Runs on a daily schedule.

---

## 工作流架構 / Workflow

```
天氣 / 趨勢資料  →  AI 穿搭生成  →  色卡渲染 + 模特圖  →  Telegram 推送
 data_layer          brain_layer       render_layer          delivery_layer
```

1. **資料層**：讀取即時天氣（OpenWeatherMap）、穿搭趨勢（RSS）、節慶日曆
2. **生成層**：呼叫 Gemini API 生成穿搭組合與文字描述
3. **渲染層**：Playwright + Jinja2 渲染穿搭色卡；Gemini 生成 AI 模特圖
4. **交付層**：透過 Telegram Bot API 推送至頻道，含防重複同日鎖定機制

---

## 展示成果 / Showcase

### 穿搭色卡 Outfit Cards

<table>
  <tr>
    <td align="center">
      <img src="assets/github/generated/outfit-card-1.png" width="360"><br>
      <sub>色卡 1 — 春夏配色方案</sub>
    </td>
    <td align="center">
      <img src="assets/github/generated/outfit-card-2.png" width="360"><br>
      <sub>色卡 2 — 秋冬配色方案</sub>
    </td>
  </tr>
</table>

### AI 模特穿搭圖 AI Outfit Images

<table>
  <tr>
    <td align="center">
      <img src="assets/github/generated/outfit-photo-1.png" width="360"><br>
      <sub>AI 生成模特圖 1</sub>
    </td>
    <td align="center">
      <img src="assets/github/generated/outfit-photo-2.png" width="360"><br>
      <sub>AI 生成模特圖 2</sub>
    </td>
  </tr>
</table>

### Telegram 推送截圖 Delivery Screenshots

<table>
  <tr>
    <td align="center">
      <img src="assets/github/telegram/telegram-delivery-1.png" width="360"><br>
      <sub>每日推送 — 穿搭色卡</sub>
    </td>
    <td align="center">
      <img src="assets/github/telegram/telegram-delivery-2.png" width="360"><br>
      <sub>每日推送 — AI 模特圖</sub>
    </td>
  </tr>
  <tr>
    <td align="center">
      <img src="assets/github/telegram/telegram-delivery-3.png" width="360"><br>
      <sub>每日推送 — 完整報告</sub>
    </td>
    <td></td>
  </tr>
</table>

---

## 技術棧 / Tech Stack

| 類別 | 工具 |
|------|------|
| 語言 | Python 3.12 |
| AI 生成 | Google Gemini API |
| 渲染引擎 | Playwright · Jinja2 |
| 天氣資料 | OpenWeatherMap API |
| 推送通道 | Telegram Bot API |
| 圖片處理 | Pillow |
| 測試 | pytest · pytest-asyncio |
| CI | GitHub Actions |

---

## 專案結構 / Project Structure

```
clothes-AI/
├── main.py                  ← 工作流入口
├── requirements.txt
├── pytest.ini
├── .env.example
├── cache/
│   └── festivals.json       ← 節慶日曆靜態資料
├── src/
│   ├── data_layer/          ← 天氣、趨勢、節慶資料取得
│   ├── brain_layer/         ← Gemini 穿搭內容生成
│   ├── render_layer/        ← 色卡渲染 + AI 模特圖生成
│   └── delivery_layer/      ← Telegram 推送 + 防重複鎖定
├── assets/
│   ├── templates/           ← Jinja2 HTML 模板
│   └── github/              ← 作品集展示圖片
└── tests/                   ← 65 個 pytest 測試
```

---

## 🧩 提示詞外部化治理架構 / Prompt Externalization

本專案已將**所有核心 LLM 提示詞**從 Python 程式碼解耦，集中存放於 `prompts/` 目錄下的獨立 `.txt` 檔，與正式業務程式碼完全分離。

| 提示詞檔 | 角色 | 由何處動態載入 |
|---------|------|---------------|
| `prompts/男裝造型師_系統.txt` | 男裝造型師 System Prompt | `src/brain_layer/outfit_generator.py` |
| `prompts/男裝造型師_用戶模板.txt` | 配色生成 User Prompt 模板 | `src/brain_layer/outfit_generator.py` |
| `prompts/服裝色卡模板.txt` | 色卡圖像生成模板 | `src/render_layer/outfit_photo_generator.py` |
| `prompts/穿搭照模板.txt` | AI 模特穿搭照生成模板 | `src/render_layer/outfit_photo_generator.py` |

各檔於模組載入時以 `open(..., 'r', encoding='utf-8').read()` 動態讀入，並以 `{變數}` 佔位符配合 `str.format()` 回填動態內容。

**核心價值 —— AI 大腦與程式碼解耦：**

- 開發者或 AI 代理可**直接修改 `.txt` 文本**來迭代造型師的配色邏輯、圖像生成風格與文案語氣，**無須更動任何 `.py` 業務程式碼**。
- 提示詞文字與程式邏輯分離後，可獨立版本控制、審查與回歸測試，避免長字串散落在函式中形成技術債。

---

## 快速開始 / Setup

```bash
git clone https://github.com/perry121108-dotcom/clothes-AI
cd clothes-AI
pip install -r requirements.txt
playwright install chromium
```

複製並填入環境變數 / Copy and fill in env vars:

```bash
cp .env.example .env
```

```text
GEMINI_API_KEY=       # Google AI Studio
OPENWEATHER_API_KEY=  # openweathermap.org
DEFAULT_CITY=         # 預設城市，例：Taipei
TELEGRAM_BOT_TOKEN=   # BotFather 取得
TELEGRAM_CHAT_ID=     # 目標頻道或聊天室 ID
```

---

## 執行 / Run

```bash
python main.py
```

---

## 測試 / Test

```bash
python -m pytest --tb=short -q
```

預期輸出：

```
65 passed
```

測試涵蓋所有四層（資料層、生成層、渲染層、交付層），所有外部 API 呼叫均以 mock 取代，無需真實金鑰即可執行。

---

## 排程自動化 / Automation Schedule

本 repo 記錄排程配置但未啟用，避免持續消耗 API 配額。實際部署可透過以下任一方式執行每日自動化：

- 本機 cron job
- 雲端 VM cron
- GitHub Actions schedule（範例如下）

```yaml
on:
  schedule:
    - cron: "0 0 * * *"   # 每日 UTC 00:00
  workflow_dispatch:        # 支援手動觸發

jobs:
  daily-outfit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -r requirements.txt
      - run: playwright install chromium
      - run: playwright install-deps chromium
      - run: python main.py
        env:
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
          OPENWEATHER_API_KEY: ${{ secrets.OPENWEATHER_API_KEY }}
          TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
```

---

## 產品決策說明 / Product Note

本專案早期探索了短影音生成（成果保留於 `assets/`）。由於影音 API 成本較高且難以穩定重現，主要展示方向調整為「圖片生成 + Telegram 推送」的可持續自動化迴圈。

這體現了一個實際的工程決策：保留實驗性成果作為功能演進證據，同時聚焦在成本可控、可重複執行的核心路徑上。

---

## License

MIT
