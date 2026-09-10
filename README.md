# 📈 100% Free Automated Buy-On-Dip Trading Platform & Web Cockpit v2.0

An intelligent, automated stock scanner, web dashboard cockpit, and push-notification system powered by `tradingview-mcp` technical analysis and **GitHub Actions Cloud Runner**. It monitors watchlist stocks across **US and Indian markets**, filters for high-probability accumulation dips, handles corporate ticker demergers/re-labeling seamlessly, and delivers **plain-English decision alerts** directly to your **WhatsApp**, **Telegram**, and **Web Dashboard**.

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

## 🌟 Key Dashboard & Engine Features

- 🎯 **Active Buy-on-Dip Cards:** View real-time price, RSI, recommended buy zone range, 52-week drawdown, and multi-tranche action plans.
- 🏛️ **Dual Strategy Engine:** 
  - **Long-Term DCA Mode (`long_term`):** Evaluates 52-week high drawdown, Weekly RSI, Fundamental Quality Gates (ROE, Debt/Equity, P/E), and 3-Tranche SIP capital allocations (Tranche 1: 20%, Tranche 2: 35%, Tranche 3: 45%).
  - **Short-Term Swing Mode (`swing`):** Evaluates daily trend confluence, EMA 20/50/200, MACD momentum, and S1/R1 pivot levels.
- 🔄 **Corporate Demerger & Symbol Normalization:** Automatically resolves renamed or de-listed corporate tickers (e.g. `TATAMOTORS` / `TATAMOTORS.NS` seamlessly maps to post-demerger tickers `TMPV` (Passenger Vehicles) and `TMCV` (Commercial Vehicles) without 404 errors).
- 💾 **SQLite DB Auto-Migration:** Database initialization (`init_db()`) auto-detects and migrates legacy Watchlist records in SQLite (`trading_platform.db`).
- 📲 **Multi-Channel Push Alerts:** Sends formatted, plain-English push notification cards to **Meta WhatsApp Cloud API** and **Telegram Bot API**.
- ➕ **Dynamic Watchlist Management:** Click `➕ Add Stock` in the top bar or update `watchlist.txt` to track US (`NVDA`, `AAPL`, `QQQ`, `SPY`) and Indian stocks (`TCS.NS`, `TMPV.NS`, `TMCV.NS`, `RELIANCE.NS`).
- 🛡️ **15-Minute Intelligent Caching & Fallback:** Prevents API rate limits by caching data and falling back to Yahoo Finance quotes gracefully.

---

## 📱 Sample Alert Format

### Long-Term Value Accumulation Alert
```text
📢 LONG-TERM ACCUMULATION ALERT: TMPV (Tata Motors Passenger Vehicles)
─────────────────────────────

🟢 DECISION: 🏛️ TRANCHE 3 BUY — GENERATIONAL PANIC BARGAIN

💡 Summary: Generational Value Dip: Price (₹301.10) is 59.3% below 52W High (₹739.70) with Weekly RSI at 31.8. High-conviction long-term DCA entry.

💵 Current Price: ₹301.10
📉 52-Week High Drawdown: -59.3%
📊 Weekly RSI: 31.8
🏛️ Recommended Tranche: 45% Capital Allocation
⭐ Quality Score: 7/10

🛒 Action Plan: Generational Value Entry: Deploy 45% of your total planned budget for TMPV. Hold for 5–10+ years.

⏰ Generated: 10 Sep 2026 15:27 IST
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
Create or edit `.env` for push notifications:
```ini
# Telegram Push Notifications
TELEGRAM_BOT_TOKEN="your_bot_token"
TELEGRAM_CHAT_ID="your_chat_id"

# Meta WhatsApp Cloud API (Optional)
WHATSAPP_TOKEN="your_meta_system_user_token"
WHATSAPP_PHONE_ID="your_whatsapp_phone_number_id"
WHATSAPP_RECIPIENT="your_phone_number_with_country_code"
```

---

## 🧪 Terminal CLI & API Commands

| Action | Command |
| :--- | :--- |
| **Start Web Dashboard Server** | `uv run python api_server.py` |
| **Run Long-Term DCA Scan (Terminal Preview)** | `uv run python buy_on_dip_notifier.py --dry-run --mode long_term` |
| **Run Short-Term Swing Scan (Terminal Preview)** | `uv run python buy_on_dip_notifier.py --dry-run --mode swing` |
| **Run Live Market Scan & Push Alerts** | `uv run python buy_on_dip_notifier.py` |
| **Scan Custom Symbol List** | `uv run python buy_on_dip_notifier.py --symbols TMPV.NS,TMCV.NS,AAPL,NVDA` |
| **Run PyTest Suite** | `uv run pytest` |

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

- **Legacy Symbol Errors (e.g. TATAMOTORS)**:
  Run `uv run python database.py` to trigger the automatic database migration to replace delisted symbols with `TMPV` and `TMCV`.

- **Stop Server**: Press `CTRL + C` in the terminal running `api_server.py`.

---

## 📄 License

MIT License. Free for personal and commercial use.
