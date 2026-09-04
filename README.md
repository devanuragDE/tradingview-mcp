# 📈 100% Free Automated Buy-On-Dip Stock Alert System

An intelligent, automated stock scanner and push-notification system powered by `tradingview-mcp` technical analysis and **GitHub Actions Cloud Runner**. It monitors watchlist stocks across **US and Indian markets**, filters for high-probability accumulation dips, and delivers **plain-English decision alerts** directly to your **Telegram** or **WhatsApp** app.

---

## 🌟 Key Features

- 🤖 **Smart Dip Filtering:** Monitors trends using Golden Cross (50/200 EMA), RSI cool-off zones (30–52), and EMA support touchpoints. It alerts you **only when a stock is in a genuine buy zone**, filtering out overbought peaks.
- 💬 **Beginner-Friendly Decision Alerts:** Zero technical jargon. Notifications give you plain-English badges:
  - 🟢 `DECISION: ✅ YES — EXCELLENT DIP TO BUY!`
  - 🟡 `DECISION: ⚡ MODERATE DIP — SMALL BUY / DCA`
  - 🔴 `DECISION: 🛑 DO NOT BUY YET (WAIT FOR DIP)`
- 🛒 **Actionable Execution Plan:** Specifies exact **Recommended Buy Range**, **Target Price (+% upside)**, **Stop Loss**, and **Allocation Suggestion** (e.g. *Buy 15–20% of budget now*).
- 🌍 **Multi-Market Support:** Pre-configured for US equities (`QQQ`, `AAPL`, `NVDA`) and Indian equities (`TCS.NS`, `RELIANCE.NS`). Easily customizable for any ticker.
- ☁️ **100% Free Cloud Automation:** Runs automatically every Monday–Friday at 09:30 AM IST (04:00 UTC) on GitHub's free cloud runners. No local computer required to stay powered on!

---

## 📱 Sample Telegram Alert

```text
📢 STOCK ALERT: QQQ (Invesco QQQ Trust)
─────────────────────────────

🟡 DECISION: ⚡ MODERATE DIP — SMALL BUY / DCA

💡 Summary: Stock is pulling back slightly. Good area to start a small position.

💵 Current Price: $720.44
🎯 Recommended Buy Zone: $690.19 – $724.04
🛒 What To Do: Buy 15% to 20% of your planned investment amount now.

📈 Upside Target: $738.95 (+2.6% potential)
🛡️ Safety Stop Level: $690.19

⏰ Generated: 04 Sep 2026 13:52 UTC
```

---

## 🚀 Quick Start & Local Setup

### 1. Prerequisites
- **Python 3.10 – 3.13** installed.
- **`uv` (Fast Python package manager)**:
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```

### 2. Clone & Install Dependencies
```bash
git clone https://github.com/devanuragDE/tradingview-mcp.git
cd tradingview-mcp

# Create virtualenv & sync dependencies
uv venv && uv sync
```

### 3. Environment Credentials Setup
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

Open `.env` and fill in your Telegram Bot credentials:
```bash
TELEGRAM_BOT_TOKEN="8867216133:AAG3S-n-mScYyyOA2qntAJCBrFkd9xBVtwc"
TELEGRAM_CHAT_ID="707881814"
```

---

## 📲 How to Setup Your Telegram Bot (100% Free)

1. **Create Bot:** Open Telegram, search for `@BotFather`, send `/newbot`, and follow prompts to get your `TELEGRAM_BOT_TOKEN`.
2. **Get Chat ID:** Search for `@userinfobot` on Telegram, tap **Start**, and copy your numerical `TELEGRAM_CHAT_ID`.
3. **Initialize Bot:** Search for your new bot's `@username` on Telegram and tap **Start** (required once so Telegram allows your bot to text you).

---

## 🧪 Running Scans

### Run Dry-Run (Console Preview Only)
```bash
uv run python buy_on_dip_notifier.py --dry-run
```

### Run Live Scan & Send Telegram Alert
```bash
uv run python buy_on_dip_notifier.py
```

### Run Report for ALL Watchlist Stocks (Ignore Dip Filter)
```bash
uv run python buy_on_dip_notifier.py --all-stocks
```

---

## ☁️ 100% Free Cloud Automation (GitHub Actions)

This repository includes a pre-configured GitHub Actions workflow (`.github/workflows/daily_scan.yml`).

### Setup GitHub Secrets (1 Minute):
1. Go to your repository on GitHub: `https://github.com/devanuragDE/tradingview-mcp`
2. Click **Settings** → **Secrets and variables** → **Actions**.
3. Click **New repository secret** and add:
   - `TELEGRAM_BOT_TOKEN`: Your BotFather Token
   - `TELEGRAM_CHAT_ID`: Your Chat ID

### Manual Trigger via GitHub Web UI:
1. Go to your repository on GitHub → Click **Actions** tab.
2. Select **Daily Buy-on-Dip Stock Scanner** on the left menu.
3. Click **Run workflow** → Click the green **Run workflow** button.

---

## 📝 Customizing Your Watchlist

Open `buy_on_dip_notifier.py` and edit the `DEFAULT_WATCHLIST` array:

```python
DEFAULT_WATCHLIST = [
    {"symbol": "QQQ", "exchange": "NASDAQ", "screener": "america", "name": "Invesco QQQ Trust"},
    {"symbol": "AAPL", "exchange": "NASDAQ", "screener": "america", "name": "Apple Inc."},
    {"symbol": "NVDA", "exchange": "NASDAQ", "screener": "america", "name": "NVIDIA Corp."},
    {"symbol": "TCS", "exchange": "NSE", "screener": "india", "name": "Tata Consultancy Services"},
    {"symbol": "RELIANCE", "exchange": "NSE", "screener": "india", "name": "Reliance Industries"},
]
```

---

## 📄 License

MIT License. Free for personal and commercial use.
