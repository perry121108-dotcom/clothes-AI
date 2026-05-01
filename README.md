# clothes AI

一個以 AI 自動化生成穿搭內容為核心的工作流專案。  
目前主展示方向為「每日穿搭圖片生成 + Telegram 自動交付」，並保留早期短影音生成成果作為功能演進證據。

## 專案定位

`clothes AI` 是作品集中的 AI 自動化展示專案，重點不是單一模型本身，而是整個工作流：

1. 讀取天氣、流行資訊與節慶條件
2. 由 AI 生成穿搭組合
3. 產出穿搭色卡與 AI 模特圖
4. 自動傳送到 Telegram

## 專案方向演進

這個專案一開始的目標其實是「短影音自動化生成」。

後來因為影片 API 成本較高，為了讓流程能更穩定、可持續、可控制成本，主展示方向改為：

- 以圖片生成為主
- 保留影片輸出作為曾經做過的功能證據

這代表專案不是縮水，而是做過實驗後，基於成本與實用性作出的產品調整。

## 展示畫面

### AI 穿搭色卡

![AI 穿搭色卡 1](assets/github/generated/outfit-card-1.png)

![AI 穿搭色卡 2](assets/github/generated/outfit-card-2.png)

### AI 穿搭人物圖

![AI 穿搭人物圖 1](assets/github/generated/outfit-photo-1.png)

![AI 穿搭人物圖 2](assets/github/generated/outfit-photo-2.png)

### Telegram 交付畫面

![Telegram 交付畫面 1](assets/github/telegram/telegram-delivery-1.png)

![Telegram 交付畫面 2](assets/github/telegram/telegram-delivery-2.png)

![Telegram 交付畫面 3](assets/github/telegram/telegram-delivery-3.png)

## 目前展示證據

### 圖片輸出

以下素材已整理到 repo：

- `assets/github/generated/outfit-card-1.png`
- `assets/github/generated/outfit-card-2.png`
- `assets/github/generated/outfit-photo-1.png`
- `assets/github/generated/outfit-photo-2.png`
- `assets/github/telegram/telegram-delivery-1.png`
- `assets/github/telegram/telegram-delivery-2.png`
- `assets/github/telegram/telegram-delivery-3.png`

### 影片證據

早期短影音成果保留於：

- `assets/github/video/sample-short-video.mp4`

### 原始輸出

原始每日輸出仍保留於：

- `output/`

## 技術組成

- Python
- Playwright
- Google Gemini API
- OpenWeatherMap API
- Telegram Bot API
- Jinja2
- pytest

## 核心功能

- 根據天氣與條件生成穿搭內容
- 產生色卡圖片
- 產生 AI 穿搭人物圖片
- 將結果自動傳送到 Telegram
- 支援重跑保護，避免同日重複輸出

## 專案結構

```text
clothes AI/
├─ main.py
├─ requirements.txt
├─ .env.example
├─ output/
├─ assets/
│  ├─ templates/
│  └─ github/
│     ├─ generated/
│     ├─ telegram/
│     └─ video/
├─ src/
│  ├─ data_layer/
│  ├─ brain_layer/
│  ├─ render_layer/
│  └─ delivery_layer/
└─ tests/
```

## 安裝方式

```bash
pip install -r requirements.txt
playwright install chromium
```

## 執行方式

```bash
python main.py
```

## 測試方式

```bash
python -m pytest --tb=short -q
```

## 環境變數

請參考 `.env.example`，主要包含：

- `GEMINI_API_KEY`
- `OPENWEATHER_API_KEY`
- `DEFAULT_CITY`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

## GitHub 展示重點

這個專案在 GitHub 上應該傳達三件事：

1. 你做的是「AI 自動化工作流」，不是只有單次圖片生成
2. 專案曾經做到影片生成，後來因成本控制改為圖片主展示
3. 這個流程有實際輸出、有證據、有交付場景

## 待補強項目

- Telegram 接收畫面截圖整理到 `assets/github/telegram/`
- README 中加入展示圖片區塊
- 補上 CI / 執行驗證資訊

## License

MIT

