# 🖥️ Starter Guide: How to Launch & Use the Web Dashboard

This guide provides step-by-step instructions on how to start the Web Dashboard server, access it in your browser, and manage your stock watchlists and alerts.

---

## 📌 Quick Commands Cheatsheet

| Task | Command / Action |
| :--- | :--- |
| **1. Navigate to Project** | `cd /Users/anuragraut/.gemini/antigravity/scratch/tradingview-mcp` |
| **2. Start Server** | `uv run python api_server.py` |
| **3. Access Dashboard Link** | 👉 **[http://localhost:8000/dashboard/](http://localhost:8000/dashboard/)** |
| **4. Stop Server** | Press `CTRL + C` in your terminal |
| **5. Fix Port Conflict** | `kill -9 $(lsof -t -i:8000)` |

---

## 🚀 Step-by-Step Instructions for Beginners

### Step 1: Open Your Terminal
Open **Terminal** (macOS) or command prompt.

### Step 2: Navigate to Project Directory
Run:
```bash
cd /Users/anuragraut/.gemini/antigravity/scratch/tradingview-mcp
```

### Step 3: Run the Server Command
Start the FastAPI server:
```bash
uv run python api_server.py
```

You will see output in the terminal like this:
```text
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

> **Note:** Keep this terminal window open while you use the dashboard!

---

### Step 4: Access the Dashboard in Browser
Open Chrome, Safari, Firefox, or Edge and go to:

👉 **[http://localhost:8000/dashboard/](http://localhost:8000/dashboard/)**

*(You can also use [http://localhost:8000](http://localhost:8000), which automatically redirects to `/dashboard/`).*

---

## 🎨 How to Use Dashboard Features

### 1. View Stock Cards & Technical Data
- **🎯 Active Dips Tab:** Displays stocks currently sitting in prime buy-on-dip support zones.
- **📊 All Watchlist Tab:** View real-time technical analysis, RSI (14), stop loss, target price, and action plan for all 34+ tracked stocks.

### 2. Add New Ticker / Stock
1. Click the **`➕ Add Stock`** button in the header bar.
2. Enter the ticker symbol:
   - For **US Stocks & ETFs**: `QQQ`, `SPY`, `NVDA`, `AAPL`, `TSLA`, `MSFT`
   - For **Indian Stocks (NSE)**: Add `.NS` at the end (e.g. `TCS.NS`, `RELIANCE.NS`, `HDFCBANK.NS`, `INFY.NS`)
3. Select Category and click **Add Ticker**.

### 3. Send Instant Alerts to Telegram
Click the **`⚡ Trigger Cloud Scan`** button in the top right.
The server evaluates all stocks in real-time and sends structured alert cards to your Telegram app.

---

## 🛠️ Troubleshooting & FAQ

#### Q: I get `ERROR: [Errno 48] Address already in use` when starting `api_server.py`.
**Solution:** Another process is occupying port 8000. Run this command to free port 8000:
```bash
kill -9 $(lsof -t -i:8000)
```
Then run `uv run python api_server.py` again.

#### Q: How do I stop the server?
**Solution:** In the terminal window running `api_server.py`, press `CTRL + C`.
