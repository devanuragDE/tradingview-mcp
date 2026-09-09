# 📈 100% Free Automated Buy-On-Dip Trading Platform & Web Cockpit v2.0

An intelligent, automated stock scanner, web dashboard cockpit, and push-notification system powered by `tradingview-mcp` technical analysis and **GitHub Actions Cloud Runner**. It monitors watchlist stocks across **US and Indian markets**, filters for high-probability accumulation dips, and delivers **plain-English decision alerts** directly to your **Telegram** app and **Web Dashboard**.

---

## 🖥️ How to Start & Access the Web Dashboard (Beginner Guide)

Follow these simple commands to launch and open the interactive Web Cockpit in your browser:

### Step 1: Open Terminal and Navigate to Project
```bash
cd /Users/anuragraut/.gemini/antigravity/scratch/tradingview-mcp
```

### Step 2: Start the Server
Run the following command:
```bash
uv run python api_server.py
```
*You will see the output:*
```text
INFO: Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO: Application startup complete.
```

### Step 3: Open in Browser
Click or open this URL in your web browser:
👉 **[http://localhost:8000/dashboard/](http://localhost:8000/dashboard/)**  
*(Or root URL: [http://localhost:8000/](http://localhost:8000/))*

---

## 🌟 Key Dashboard Features

- 🎯 **Active Buy-on-Dip Cards:** View real-time price, RSI (14), recommended buy zone range, 52-week targets, and action plans.
- ➕ **Add Stock / ETF Ticker:** Click `➕ Add Stock` in the top bar to track any US stock (`NVDA`, `AAPL`, `QQQ`) or Indian stock (`TCS.NS`, `INFY.NS`, `RELIANCE.NS`).
- ⚡ **Instant Cloud Scan & Telegram Alert:** Click `⚡ Trigger Cloud Scan` to evaluate all tickers live and dispatch notifications directly to your Telegram chat.
- 📊 **Dual Market Coverage:** Pre-seeded with 34 top US MegaCaps/ETFs and Indian Bluechip leaders.
- 🛡️ **15-Minute Intelligent Caching & Fallback:** Prevents API rate limits by caching data and seamlessly falling back to Yahoo Finance data when needed.

---

## 📱 Sample Telegram Alert Format

```text
📢 STOCK ALERT: TCS (Tata Consultancy Services)
─────────────────────────────

🟡 DECISION: ⚡ MODERATE DIP

💡 Summary: Trading at support level.

💵 Current Price: ₹2,208.00
🛑 Stop Loss: ₹2,053.40
🎯 Target 1: ₹2,350.00 (+6.4%)
🎯 Target 2: ₹2,400.00
⚖️ Risk/Reward: 1:1.5
📊 Signal Strength: 5/7

🛒 What To Do: Buy 10% to 20% on dip.

🔍 Details:
   Trend: ✅ Strong
   Support: ✅ At Support
   RSI: 42.0 (✅ Buy Zone)
   Momentum: ❌ Weak

⏰ Generated: 09 Sep 2026 22:59 IST
```

---

## 🚀 Quick Setup & Installation

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

### 3. Environment Credentials Setup (`.env`)
Ensure `.env` contains your Telegram credentials:
```ini
TELEGRAM_BOT_TOKEN="8867216133:AAG3S-n-mScYyyOA2qntAJCBrFkd9xBVtwc"
TELEGRAM_CHAT_ID="707881814"
```

---

## 📲 How to Setup Telegram Bot Credentials (100% Free)

1. **Create Bot:** Open Telegram, search for `@BotFather`, send `/newbot`, and copy `TELEGRAM_BOT_TOKEN`.
2. **Get Chat ID:** Search for `@userinfobot` on Telegram, tap **Start**, and copy `TELEGRAM_CHAT_ID`.
3. **Initialize Bot:** Search for your bot's username on Telegram and click **Start**.

---

## 🧪 Terminal CLI Commands

| Action | Command |
| :--- | :--- |
| **Start Web Dashboard Server** | `uv run python api_server.py` |
| **Run Dry-Run Scan (Terminal Preview)** | `uv run python buy_on_dip_notifier.py --dry-run` |
| **Run Live Market Scan & Alert** | `uv run python buy_on_dip_notifier.py` |
| **Force Scan for ALL Watchlist Stocks** | `uv run python buy_on_dip_notifier.py --all-stocks` |

---

## 🔧 Troubleshooting Common Dashboard Issues

- **Port 8000 Already in Use (`Errno 48`)**:
  If port 8000 is occupied by a previous process, free it with:
  ```bash
  kill -9 $(lsof -t -i:8000)
  ```
  Then restart the server:
  ```bash
  uv run python api_server.py
  ```

- **Stop Server**: Press `CTRL + C` in the terminal running `api_server.py`.

---

## 📄 License

MIT License. Free for personal and commercial use.
