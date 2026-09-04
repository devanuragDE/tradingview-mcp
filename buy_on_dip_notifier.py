#!/usr/bin/env python3
"""
Automated Buy-on-Dip Stock Alert System (WhatsApp & Telegram)
Uses tradingview-mcp engine to scan watchlist stocks daily and send
100% free push alerts via Meta WhatsApp Cloud API and Telegram Bot.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import requests
from datetime import datetime, timezone
import time
from pathlib import Path

# Add project root to sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR / "src"))

# Load environment variables if .env exists
env_path = SCRIPT_DIR / ".env"
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

# Import tradingview-mcp services
from tradingview_ta import TA_Handler, Interval
from tradingview_mcp.core.services.yahoo_finance_service import get_price

# ─── DEFAULT WATCHLIST ────────────────────────────────────────────────────────
DEFAULT_WATCHLIST = [
    {"symbol": "QQQ", "exchange": "NASDAQ", "screener": "america", "name": "Invesco QQQ Trust"},
    {"symbol": "AAPL", "exchange": "NASDAQ", "screener": "america", "name": "Apple Inc."},
    {"symbol": "NVDA", "exchange": "NASDAQ", "screener": "america", "name": "NVIDIA Corp."},
    {"symbol": "TCS", "exchange": "NSE", "screener": "india", "name": "Tata Consultancy Services"},
    {"symbol": "RELIANCE", "exchange": "NSE", "screener": "india", "name": "Reliance Industries"},
]


ETF_EXCHANGES = {
    "SPY": "AMEX",
    "IWM": "AMEX",
    "VOO": "AMEX",
    "VTI": "AMEX",
    "QQQ": "NASDAQ",
    "XLK": "AMEX",
    "SMH": "AMEX",
    "SOXX": "NASDAQ",
    "XLF": "AMEX",
    "XLE": "AMEX",
}


def load_watchlist(auto_screen: bool = False, custom_symbols: list[str] = None) -> list[dict]:
    """Dynamically load watchlist from CLI flags, env var, watchlist.txt, auto-screener, or defaults."""
    items = []

    def _resolve_symbol(raw_sym: str) -> dict:
        sym = raw_sym.strip().upper()
        if ".NS" in sym or sym.endswith("-IN"):
            clean = sym.replace(".NS", "").replace("-IN", "")
            return {"symbol": clean, "exchange": "NSE", "screener": "india", "name": clean}
        ex = ETF_EXCHANGES.get(sym, "NASDAQ")
        return {"symbol": sym, "exchange": ex, "screener": "america", "name": sym}

    # 1. Custom Symbols passed via CLI --symbols
    if custom_symbols:
        for sym in custom_symbols:
            if sym.strip():
                items.append(_resolve_symbol(sym))
        if items:
            return items

    # 2. Environment Variable WATCHLIST="QQQ,SPY,AAPL,TCS.NS"
    env_watchlist = os.environ.get("WATCHLIST")
    if env_watchlist:
        for sym in env_watchlist.split(","):
            if sym.strip():
                items.append(_resolve_symbol(sym))
        if items:
            return items

    # 3. Text file watchlist.txt
    watchlist_file = SCRIPT_DIR / "watchlist.txt"
    if watchlist_file.exists():
        with open(watchlist_file) as f:
            for line in f:
                sym = line.strip().upper()
                if not sym or sym.startswith("#"):
                    continue
                items.append(_resolve_symbol(sym))
        if items:
            return items

    # 4. Auto-Screener Discovery Mode
    if auto_screen:
        try:
            from tradingview_mcp.core.services.stock_screener_service import screen_stocks
            seen = set()
            # Top US Megacaps
            us_res = screen_stocks(country="america", limit=10)
            for row in us_res.get("rows", []):
                sym = row["symbol"]
                if sym not in seen:
                    seen.add(sym)
                    items.append({"symbol": sym, "exchange": row.get("exchange", "NASDAQ"), "screener": "america", "name": row.get("description", sym)})
            
            # Top India Megacaps (NSE)
            in_res = screen_stocks(country="india", limit=10)
            for row in in_res.get("rows", []):
                sym = row["symbol"]
                ex = row.get("exchange", "NSE")
                if ex == "NSE" and sym not in seen:
                    seen.add(sym)
                    items.append({"symbol": sym, "exchange": "NSE", "screener": "india", "name": row.get("description", sym)})
            
            if items:
                return items
        except Exception as e:
            print(f"⚠️ Auto-screener discovery fallback: {e}")

    # 5. Default Watchlist
    return DEFAULT_WATCHLIST


# ─── ANALYSIS & STRATEGY ENGINE ────────────────────────────────────────────────
def analyze_stock(item: dict) -> dict:
    """Fetch live data and evaluate Buy-On-Dip strategy criteria."""
    symbol = item["symbol"]
    exchange = item["exchange"]
    screener = item["screener"]
    name = item.get("name", symbol)

    try:
        handler = TA_Handler(
            symbol=symbol,
            exchange=exchange,
            screener=screener,
            interval=Interval.INTERVAL_1_DAY
        )
        analysis = handler.get_analysis()
        ind = analysis.indicators
    except Exception as e:
        return {"symbol": symbol, "error": str(e)}

    close_price = ind.get("close", 0.0)
    rsi = ind.get("RSI", 50.0)
    ema20 = ind.get("EMA20", close_price)
    ema50 = ind.get("EMA50", close_price)
    ema200 = ind.get("EMA200", close_price)
    macd_line = ind.get("MACD.macd", 0.0)
    macd_signal = ind.get("MACD.signal", 0.0)
    
    # Calculate support / resistance
    s1 = ind.get("Pivot.M.Classic.S1", close_price * 0.95)
    r1 = ind.get("Pivot.M.Classic.R1", close_price * 1.05)
    pivot_mid = ind.get("Pivot.M.Classic.Middle", close_price)

    # 1. Macro Trend Check
    is_macro_uptrend = (close_price >= ema200 * 0.97) or (ema50 > ema200)

    # 2. Dip Conditions
    rsi_dip = rsi <= 52.0  # Cool-off zone
    ema_support_dip = (abs(close_price - ema20) / ema20 <= 0.018) or (abs(close_price - ema50) / ema50 <= 0.02)
    near_s1 = abs(close_price - s1) / s1 <= 0.025

    is_buy_on_dip = is_macro_uptrend and (rsi_dip or ema_support_dip or near_s1)

    # 3. Decision Logic & Human-Readable Action Plan
    if is_macro_uptrend and (rsi <= 48 or near_s1):
        decision_badge = "🟢 DECISION: ✅ YES — EXCELLENT DIP TO BUY!"
        decision_summary = "Stock is in a healthy long-term uptrend and has cooled down to major support."
        action_plan = "Buy 30% to 40% of your planned investment amount now."
    elif is_buy_on_dip:
        decision_badge = "🟡 DECISION: ⚡ MODERATE DIP — SMALL BUY / DCA"
        decision_summary = "Stock is pulling back slightly. Good area to start a small position."
        action_plan = "Buy 15% to 20% of your planned investment amount now."
    else:
        decision_badge = "🔴 DECISION: 🛑 DO NOT BUY YET (WAIT FOR DIP)"
        decision_summary = "Stock is near short-term highs or lacks a clear dip setup."
        action_plan = "Do not buy now. Keep on watchlist and wait for a deeper pullback."

    # Buy Zone Range
    low_buy_zone = min(ema50, s1, close_price * 0.985)
    high_buy_zone = max(ema20, close_price * 1.005)

    return {
        "symbol": symbol,
        "exchange": exchange,
        "name": name,
        "price": close_price,
        "rsi": rsi,
        "ema50": ema50,
        "support_s1": s1,
        "resistance_r1": r1,
        "is_macro_uptrend": is_macro_uptrend,
        "is_buy_on_dip": is_buy_on_dip,
        "decision_badge": decision_badge,
        "decision_summary": decision_summary,
        "action_plan": action_plan,
        "low_buy_zone": low_buy_zone,
        "high_buy_zone": high_buy_zone,
    }


# ─── NOTIFICATION DISPATCHERS ─────────────────────────────────────────────────
def format_whatsapp_message(alert: dict) -> str:
    """Format a beginner-friendly, plain-English WhatsApp alert."""
    currency = "₹" if alert["exchange"] == "NSE" else "$"
    pct_to_target = ((alert["resistance_r1"] - alert["price"]) / alert["price"]) * 100
    
    return (
        f"📢 *STOCK ALERT: {alert['symbol']}* ({alert['name']})\n"
        f"─────────────────────────────\n\n"
        f"{alert['decision_badge']}\n\n"
        f"💡 *Summary:* {alert['decision_summary']}\n\n"
        f"💵 *Current Price:* {currency}{alert['price']:,.2f}\n"
        f"🎯 *Recommended Buy Zone:* {currency}{alert['low_buy_zone']:,.2f} – {currency}{alert['high_buy_zone']:,.2f}\n"
        f"🛒 *What To Do:* {alert['action_plan']}\n\n"
        f"📈 *Upside Target:* {currency}{alert['resistance_r1']:,.2f} (+{pct_to_target:.1f}% potential)\n"
        f"🛡️ *Safety Stop Level:* {currency}{alert['support_s1']:,.2f}\n\n"
        f"⏰ *Generated:* {datetime.now(timezone.utc).strftime('%d %b %Y %H:%M UTC')}"
    )


def send_whatsapp_meta(text: str) -> bool:
    """Send WhatsApp message using Meta WhatsApp Cloud API (100% Free tier)."""
    token = os.environ.get("WHATSAPP_TOKEN")
    phone_number_id = os.environ.get("WHATSAPP_PHONE_ID")
    recipient = os.environ.get("WHATSAPP_RECIPIENT")

    if not (token and phone_number_id and recipient):
        print("⚠️ Meta WhatsApp credentials not fully configured in .env (WHATSAPP_TOKEN, WHATSAPP_PHONE_ID, WHATSAPP_RECIPIENT)")
        return False

    url = f"https://graph.facebook.com/v21.0/{phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": recipient,
        "type": "text",
        "text": {"body": text}
    }

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        if resp.status_code == 200:
            print(f"✅ WhatsApp alert successfully sent to {recipient}")
            return True
        else:
            print(f"❌ Failed to send WhatsApp message: HTTP {resp.status_code} - {resp.text}")
            return False
    except Exception as e:
        print(f"❌ WhatsApp API Exception: {e}")
        return False


def send_telegram(text: str) -> bool:
    """Send alert via Telegram Bot API (100% Free)."""
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not (bot_token and chat_id):
        print("⚠️ Telegram credentials not configured in .env (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)")
        return False

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }

    try:
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code == 200:
            print(f"✅ Telegram alert successfully sent to chat {chat_id}")
            return True
        else:
            print(f"❌ Failed to send Telegram message: HTTP {resp.status_code} - {resp.text}")
            return False
    except Exception as e:
        print(f"❌ Telegram API Exception: {e}")
        return False


# ─── MAIN EXECUTION ───────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Automated Buy-on-Dip Stock Alert Notifier")
    parser.add_argument("--dry-run", action="store_true", help="Print alerts to console without sending network messages")
    parser.add_argument("--all-stocks", action="store_true", help="Force report for all stocks, even if not strictly in dip zone")
    parser.add_argument("--auto-screen", action="store_true", help="Auto-discover top MegaCap market leaders dynamically using TradingView Screener API")
    parser.add_argument("--symbols", type=str, help="Comma-separated custom stock/ETF symbols (e.g. QQQ,SPY,NVDA,TCS.NS)")
    args = parser.parse_args()

    custom_syms = [s.strip() for s in args.symbols.split(",")] if args.symbols else None
    watchlist = load_watchlist(auto_screen=args.auto_screen, custom_symbols=custom_syms)

    print(f"🔍 Starting Buy-on-Dip Scan for {len(watchlist)} stocks at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}...")
    alerts = []

    for item in watchlist:
        time.sleep(0.4)
        print(f"  Fetching technical analysis for {item['symbol']} ({item['exchange']})...")
        res = analyze_stock(item)
        
        if "error" in res:
            print(f"  ❌ Error analyzing {item['symbol']}: {res['error']}")
            continue

        if res["is_buy_on_dip"] or args.all_stocks:
            alerts.append(res)
            msg = format_whatsapp_message(res)

            print("\n" + "=" * 50)
            print(msg)
            print("=" * 50 + "\n")

            if not args.dry_run:
                # Attempt WhatsApp send
                send_whatsapp_meta(msg)
                # Attempt Telegram send if configured
                send_telegram(msg)
        else:
            print(f"  ℹ️ {item['symbol']} Price: {res['price']:.2f} | RSI: {res['rsi']:.1f} (Not in dip buy zone)")

    print(f"\n✨ Scan completed. Total Buy-on-Dip alerts generated: {len(alerts)}")


if __name__ == "__main__":
    main()
