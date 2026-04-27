# 每日 AI 穿搭圖片生成器 / Daily AI Outfit Image Generator

> 每天自動生成 2 組男生配色穿搭，產出色塊卡片與 AI 人形模特穿搭照，並透過 Telegram 傳送。  
> Automatically generates 2 men's outfit color combinations daily — producing color cards and AI mannequin photos — then delivers them via Telegram.

---

## 目錄 / Table of Contents

- [功能說明 / Features](#功能說明--features)
- [輸出範例 / Output](#輸出範例--output)
- [系統架構 / Architecture](#系統架構--architecture)
- [安裝與設定 / Setup](#安裝與設定--setup)
- [執行方式 / Usage](#執行方式--usage)
- [環境變數 / Environment Variables](#環境變數--environment-variables)
- [專案結構 / Project Structure](#專案結構--project-structure)

---

## 功能說明 / Features

**中文**

- 即時抓取台北天氣（OpenWeatherMap API）
- 擷取當前流行趨勢與節慶資訊
- 呼叫 Gemini AI 生成 2 組協調配色穿搭方案（上衣 / 下裝 / 鞋子）
- 使用 Playwright 渲染 Douyin 風格色塊卡片（含顏色名稱與衣物類別文字標籤）
- 使用 Gemini Image 生成全白無臉人形模特穿搭照
- 自動以媒體相簿形式傳送 4 張圖片至 Telegram
- 冪等性設計：同一天重複執行會自動跳過，不重複發送

**English**

- Fetches real-time weather data for Taipei via OpenWeatherMap API
- Retrieves current fashion trends and festival information
- Calls Gemini AI to generate 2 coordinated outfit color combinations (top / bottom / shoes)
- Renders Douyin-style color strip cards via Playwright (with color name and clothing type labels)
- Generates full-body AI mannequin outfit photos via Gemini Image (featureless white form, studio background)
- Automatically sends 4 images as a Telegram media album
- Idempotent by design: re-running on the same day is safely skipped

---

## 輸出範例 / Output

每次執行產出 **4 張圖片**，傳送至 Telegram：

| 圖片 | 說明 |
|------|------|
| `card_1.png` | 第 1 組色塊卡片（顏色名稱 + 衣物類別） |
| `photo_1.png` | 第 1 組 AI 人形模特穿搭照 |
| `card_2.png` | 第 2 組色塊卡片 |
| `photo_2.png` | 第 2 組 AI 人形模特穿搭照 |

---

## 系統架構 / Architecture

```
main.py
├── Data Layer      — 天氣 / 趨勢 / 節慶資料抓取
├── Brain Layer     — Gemini AI 生成 2 組配色 JSON
├── Render Layer
│   ├── renderer.py              — Playwright 色塊卡片 PNG
│   └── outfit_photo_generator.py — Gemini Image 穿搭照 PNG
└── Delivery Layer  — Telegram send_media_group（4 張）
```

---

## 安裝與設定 / Setup

**需求 / Requirements**

- Python 3.12+
- [Playwright](https://playwright.dev/python/) Chromium（`playwright install chromium`）
- 有效的 API Key：Gemini、OpenWeatherMap、Telegram Bot

**步驟 / Steps**

```bash
# 1. Clone 專案
git clone https://github.com/your-username/clothes-ai.git
cd clothes-ai

# 2. 安裝依賴
pip install -r requirements.txt

# 3. 安裝 Playwright 瀏覽器
playwright install chromium

# 4. 建立 .env
cp .env.example .env
# 編輯 .env，填入真實 API Key
```

---

## 執行方式 / Usage

```bash
python main.py
```

執行後 Telegram 會收到 4 張圖片（2 色卡 + 2 穿搭照）。  
After running, Telegram receives 4 images (2 color cards + 2 outfit photos).

**重新生成（刪除今日 Lock）/ Force re-run**

```bash
# 刪除今日 lock 檔案即可重新生成
del output\YYYY-MM-DD.lock
python main.py
```

**測試 / Run Tests**

```bash
python -m pytest --tb=short -q
```

---

## 環境變數 / Environment Variables

複製 `.env.example` 為 `.env` 並填入以下值：

| 變數 | 說明 | 取得方式 |
|------|------|---------|
| `GEMINI_API_KEY` | Google Gemini API Key | [Google AI Studio](https://aistudio.google.com/) |
| `OPENWEATHER_API_KEY` | 天氣 API Key | [OpenWeatherMap](https://openweathermap.org/api) |
| `DEFAULT_CITY` | 預設城市（預設 `Taipei`） | 直接填入 |
| `TELEGRAM_BOT_TOKEN` | Telegram Bot Token | [@BotFather](https://t.me/BotFather) |
| `TELEGRAM_CHAT_ID` | 接收訊息的 Chat ID | [@userinfobot](https://t.me/userinfobot) |

---

## 專案結構 / Project Structure

```
clothes-ai/
├── main.py                          # 主程式入口
├── requirements.txt                 # Python 依賴
├── .env.example                     # 環境變數範本
├── assets/
│   └── templates/
│       └── color_card.html          # Douyin 色塊卡片 HTML 模板
├── src/
│   ├── data_layer/
│   │   ├── weather.py               # 天氣資料（OpenWeatherMap）
│   │   ├── trends.py                # 流行趨勢
│   │   └── festivals.py             # 節慶資訊
│   ├── brain_layer/
│   │   └── outfit_generator.py      # Gemini AI 配色生成
│   ├── render_layer/
│   │   ├── renderer.py              # Playwright 色塊卡片渲染
│   │   └── outfit_photo_generator.py # Gemini Image 穿搭照生成
│   └── delivery_layer/
│       └── telegram_bot.py          # Telegram 傳送
└── tests/                           # 單元測試（65 個，全數通過）
```

---

## 授權 / License

MIT License
