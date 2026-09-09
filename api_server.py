"""
FastAPI REST API Server for Buy-on-Dip Trading Intelligence Platform (v2.0)
Serves Web Dashboard endpoints, Watchlist management, and Live Signal Engine.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

import database
from buy_on_dip_notifier import analyze_stock, format_whatsapp_message, send_telegram, send_whatsapp_meta


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for startup and shutdown database initialization."""
    database.init_db()
    yield


app = FastAPI(
    title="Buy-on-Dip Trading Intelligence API",
    description="REST API for multi-market stock screening, dynamic watchlists, and live alerts",
    version="2.0.0",
    lifespan=lifespan,
)

# Enable CORS for Next.js / React Frontend Development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Web Dashboard UI
app.mount("/dashboard", StaticFiles(directory="static", html=True), name="dashboard")


# ─── PYDANTIC SCHEMAS ────────────────────────────────────────────────────────
class WatchlistAddRequest(BaseModel):
    symbol: str
    exchange: Optional[str] = "NASDAQ"
    screener: Optional[str] = "america"
    name: Optional[str] = None
    category: Optional[str] = "Custom"


class ScanResponse(BaseModel):
    status: str
    scanned_count: int
    signals_found: int


# ─── API ENDPOINTS ────────────────────────────────────────────────────────────

@app.get("/")
def read_root():
    """Redirect root path to Web Dashboard UI."""
    return RedirectResponse(url="/dashboard")


@app.get("/api/watchlist")
def get_watchlist():
    """Retrieve all tracked stocks and ETFs from the database."""
    items = database.get_all_watchlist_items()
    return {"status": "success", "count": len(items), "data": items}


@app.post("/api/watchlist")
def add_watchlist(request: WatchlistAddRequest):
    """Add a new stock or ETF ticker to the dynamic watchlist."""
    try:
        res = database.add_watchlist_item(
            symbol=request.symbol,
            exchange=request.exchange or "NASDAQ",
            screener=request.screener or "america",
            name=request.name or request.symbol,
            category=request.category or "Custom",
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/api/watchlist/{symbol}")
def delete_watchlist(symbol: str):
    """Remove a ticker from the dynamic watchlist."""
    try:
        res = database.delete_watchlist_item(symbol)
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/signals")
def get_live_signals(all_stocks: bool = Query(False, description="Return analysis for all stocks, even non-dips")):
    """Run real-time technical analysis and return Buy-on-Dip signals."""
    watchlist = database.get_all_watchlist_items()
    signals = []

    for item in watchlist:
        res = analyze_stock(dict(item))
        if "error" in res:
            continue
        
        # Calculate 0-100 Dip Score
        score = 40
        if res.get("is_uptrend") or res.get("is_macro_uptrend"):
            score += 25
        rsi = res.get("rsi", 50)
        if rsi <= 45:
            score += 25
        elif rsi <= 52:
            score += 15
        
        res["dip_score"] = min(100, max(0, score))

        is_buy = bool(res.get("is_buy_on_dip", res.get("is_buy_signal", False)))
        res["is_buy_on_dip"] = is_buy
        res["is_buy_signal"] = is_buy

        if "low_buy_zone" not in res:
            res["low_buy_zone"] = res.get("stop_loss", res.get("support_s1", res.get("price", 0.0) * 0.95))
        if "high_buy_zone" not in res:
            res["high_buy_zone"] = res.get("support_s1", res.get("price", 0.0))

        if is_buy or all_stocks:
            signals.append(res)
            # Log to DB
            try:
                database.log_signal(res)
            except Exception:
                pass

    return {
        "status": "success",
        "total_scanned": len(watchlist),
        "signals_count": len(signals),
        "signals": signals,
    }


@app.get("/api/signals/history")
def get_signal_history(limit: int = 50):
    """Retrieve historical signal logs for performance tracking."""
    history = database.get_signal_history(limit=limit)
    return {"status": "success", "count": len(history), "history": history}


def _run_scan_and_notify_task():
    """Background worker task to run scan and dispatch notifications."""
    watchlist = database.get_all_watchlist_items()
    for item in watchlist:
        res = analyze_stock(dict(item))
        if "error" in res:
            continue
        if res.get("is_buy_on_dip") or res.get("is_buy_signal"):
            msg = format_whatsapp_message(res)
            send_telegram(msg)
            send_whatsapp_meta(msg)


@app.post("/api/scan", response_model=ScanResponse)
def trigger_scan(background_tasks: BackgroundTasks):
    """Trigger an instant market scan & notify via Telegram/WhatsApp in background."""
    watchlist = database.get_all_watchlist_items()
    background_tasks.add_task(_run_scan_and_notify_task)
    return ScanResponse(
        status="scan_triggered",
        scanned_count=len(watchlist),
        signals_found=0,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api_server:app", host="0.0.0.0", port=8000, reload=True)
