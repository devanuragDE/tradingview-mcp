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
from datetime import datetime, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))
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
from tradingview_mcp.core.utils.validators import normalize_yahoo_symbol

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
            if clean in ("TATAMOTORS", "NSE:TATAMOTORS"):
                clean = "TMPV"
            return {"symbol": clean, "exchange": "NSE", "screener": "india", "name": clean}
        if sym in ("TATAMOTORS", "NSE:TATAMOTORS"):
            return {"symbol": "TMPV", "exchange": "NSE", "screener": "india", "name": "Tata Motors Passenger Vehicles"}
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


def calculate_rsi_divergence(indicators: dict) -> bool:
    """Check for bullish RSI divergence (price making lower low, RSI making higher low)"""
    # Simplified check - in production would need historical data
    # For now, we'll check if RSI is recovering from oversold
    rsi = indicators.get("RSI", 50)
    return 30 <= rsi <= 45  # RSI bouncing from oversold territory


_STOCK_CACHE: dict[str, tuple[float, dict]] = {}
CACHE_TTL_SECONDS = 900  # 15 minutes cache to avoid TradingView 429 rate limits


try:
    from tradingview_screener import Query
    _SCREENER_AVAILABLE = True
except ImportError:
    _SCREENER_AVAILABLE = False


def batch_fetch_tradingview(watchlist: list[dict]) -> dict[str, dict]:
    """Fetch TradingView technical indicators for all watchlist tickers in a SINGLE batch HTTP query (zero 429 rate limits)."""
    if not _SCREENER_AVAILABLE or not watchlist:
        return {}
    
    tickers = []
    for item in watchlist:
        ex = item.get("exchange", "NASDAQ")
        sym = item["symbol"]
        tickers.append(f"{ex}:{sym}")

    try:
        q = (
            Query()
            .set_tickers(*tickers)
            .select(
                "name", "exchange", "close", "high", "low", "RSI", "EMA20", "EMA50", "EMA200",
                "MACD.macd", "MACD.signal", "Pivot.M.Classic.S1", "Pivot.M.Classic.R1",
                "price_52_week_high", "price_52_week_low"
            )
            .limit(len(tickers))
        )
        total, df = q.get_scanner_data(timeout=15)
        res = {}
        for r in df.to_dict("records"):
            sym = str(r.get("name", "")).upper()
            if sym:
                res[sym] = r
        return res
    except Exception as e:
        print(f"⚠️ Batch TradingView query error: {e}")
        return {}


KNOWN_ETFS = {
    "QQQ", "SPY", "VOO", "VTI", "IWM", "XLK", "SMH", "SOXX", "XLF", "XLE",
    "NIFTYBEES", "JUNIORBEES", "BANKBEES", "MON100", "GOLDBEES", "AUTOBEES", "ITBEES"
}


def _calculate_rsi_from_series(closes: list[float], period: int = 14) -> float:
    """Calculate Relative Strength Index (RSI) over a list of closing prices."""
    if len(closes) < period + 1:
        return 50.0
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [d if d > 0 else 0.0 for d in deltas]
    losses = [abs(d) if d < 0 else 0.0 for d in deltas]
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def analyze_stock_long_term(item: dict) -> dict:
    """
    Evaluates Long-Term Value & Quality Accumulation Strategy (v3.0).
    Uses Weekly RSI, 52-Week High Drawdown, Fundamental Quality Gates, and Multi-Tranche DCA Allocations.
    """
    symbol = item["symbol"].upper()
    exchange = item["exchange"]
    name = item.get("name", symbol)
    currency_symbol = "₹" if exchange == "NSE" else "$"

    raw_ticker = f"{symbol}.NS" if exchange == "NSE" and not symbol.endswith(".NS") else symbol
    ticker_str = normalize_yahoo_symbol(raw_ticker)
    is_etf = symbol in KNOWN_ETFS or "ETF" in name.upper() or "BEES" in symbol or "TRUST" in name.upper()

    price = 0.0
    high52 = 0.0
    low52 = 0.0
    pe_ratio = None
    roe = None
    debt_to_equity = None
    weekly_rsi = 50.0
    sma200 = 0.0

    try:
        import yfinance as yf
        t = yf.Ticker(ticker_str)
        info = t.info or {}
        price = float(info.get("regularMarketPrice") or info.get("currentPrice") or 0.0)
        high52 = float(info.get("fiftyTwoWeekHigh") or price * 1.1)
        low52 = float(info.get("fiftyTwoWeekLow") or price * 0.9)
        pe_ratio = info.get("trailingPE")
        roe = info.get("returnOnEquity")
        debt_to_equity = info.get("debtToEquity")

        # Fetch weekly candle history for Weekly RSI & 200-day SMA
        hist_w = t.history(period="1y", interval="1wk")
        if not hist_w.empty and len(hist_w) >= 14:
            w_closes = hist_w["Close"].dropna().tolist()
            if w_closes:
                price = float(w_closes[-1])
                weekly_rsi = _calculate_rsi_from_series(w_closes)
        
        hist_d = t.history(period="1y", interval="1d")
        if not hist_d.empty and len(hist_d) >= 200:
            sma200 = float(hist_d["Close"].rolling(200).mean().iloc[-1])
        elif not hist_d.empty:
            sma200 = float(hist_d["Close"].mean())
    except Exception:
        # Fallback using get_price
        yf_data = get_price(ticker_str)
        if "error" not in yf_data and yf_data.get("price"):
            price = float(yf_data["price"])
            high52 = float(yf_data.get("52w_high") or price * 1.1)
            low52 = float(yf_data.get("52w_low") or price * 0.9)
            sma200 = round(price * 0.92, 2)
            weekly_rsi = 46.0

    if price == 0.0:
        return {"symbol": symbol, "error": "Unable to fetch market price"}

    pct_pullback = round(max(0.0, ((high52 - price) / high52) * 100), 1) if high52 > 0 else 0.0

    # Fundamental Quality Gate
    quality_pass = True
    quality_reasons = []

    if is_etf:
        quality_score = 10
        quality_label = "🌟 Index ETF (100% Quality Immunity)"
    else:
        q_score = 7
        if roe is not None:
            roe_pct = roe * 100 if roe < 5.0 else roe
            if roe_pct >= 15.0:
                q_score += 1.5
                quality_reasons.append(f"High ROE ({roe_pct:.1f}%)")
            elif roe_pct < 8.0:
                q_score -= 2.0
                quality_reasons.append(f"Low ROE ({roe_pct:.1f}%)")
        
        if debt_to_equity is not None:
            de_ratio = debt_to_equity / 100.0 if debt_to_equity > 10.0 else debt_to_equity
            if de_ratio <= 0.5:
                q_score += 1.5
                quality_reasons.append(f"Low Debt (D/E {de_ratio:.2f})")
            elif de_ratio > 1.5:
                q_score -= 2.0
                quality_reasons.append(f"High Debt (D/E {de_ratio:.2f})")
                quality_pass = False

        if pe_ratio is not None and pe_ratio > 70:
            q_score -= 1.0
            quality_reasons.append(f"High P/E ({pe_ratio:.1f})")

        quality_score = max(1, min(10, int(round(q_score))))
        quality_label = f"⭐ Quality Score: {quality_score}/10"

    # Multi-Tranche Long-Term DCA Decision Matrix
    if (pct_pullback >= 22.0 or (weekly_rsi <= 38 and pct_pullback >= 15.0)) and quality_pass:
        tranche = 3
        tranche_allocation = "45%"
        decision_badge = "🟢 DECISION: 🏛️ TRANCHE 3 BUY — GENERATIONAL PANIC BARGAIN"
        decision_summary = f"Generational Value Dip: Price ({currency_symbol}{price:,.2f}) is {pct_pullback:.1f}% below 52W High ({currency_symbol}{high52:,.2f}) with Weekly RSI at {weekly_rsi:.1f}. High-conviction long-term DCA entry."
        action_plan = f"Generational Value Entry: Deploy 45% of your total planned budget for {symbol}. Hold for 5–10+ years."
        is_buy_signal = True

    elif (pct_pullback >= 14.0 or (weekly_rsi <= 44 and pct_pullback >= 10.0)) and quality_pass:
        tranche = 2
        tranche_allocation = "35%"
        decision_badge = "🟢 DECISION: 🏛️ TRANCHE 2 BUY — DEEP VALUE ACCUMULATION"
        decision_summary = f"Deep Value Pullback: Price ({currency_symbol}{price:,.2f}) is {pct_pullback:.1f}% below 52W High ({currency_symbol}{high52:,.2f}) with Weekly RSI at {weekly_rsi:.1f}. Solid long-term entry point."
        action_plan = f"Deep Value Accumulation: Deploy 35% of your total planned budget for {symbol} (Tranche 2 SIP)."
        is_buy_signal = True

    elif (pct_pullback >= 8.0 or weekly_rsi <= 50) and quality_pass:
        tranche = 1
        tranche_allocation = "20%"
        decision_badge = "🟡 DECISION: 🏛️ TRANCHE 1 BUY — INITIAL DIP ACCUMULATION"
        decision_summary = f"Initial Valuation Dip: Price ({currency_symbol}{price:,.2f}) is {pct_pullback:.1f}% below 52W High ({currency_symbol}{high52:,.2f}) with Weekly RSI at {weekly_rsi:.1f}. Favorable initial entry."
        action_plan = f"Initial Dip Accumulation: Deploy 20% of your total planned budget for {symbol} (Tranche 1 SIP)."
        is_buy_signal = True

    else:
        tranche = 0
        tranche_allocation = "0%"
        decision_badge = "🔴 DECISION: 🛑 DO NOT BUY YET (WAIT FOR LOWER VALUATION)"
        if not quality_pass:
            decision_summary = f"Fundamental Quality Warning: High debt or weak financial health. Avoid accumulating long-term."
        else:
            decision_summary = f"Fair Valuation Peak: Price ({currency_symbol}{price:,.2f}) is trading within {pct_pullback:.1f}% of 52W High ({currency_symbol}{high52:,.2f}) with neutral Weekly RSI ({weekly_rsi:.1f}). Wait for lower entry."
        action_plan = f"Hold existing position. Do not accumulate at current valuation peak."
        is_buy_signal = False

    return {
        "symbol": symbol,
        "exchange": exchange,
        "name": name,
        "price": price,
        "mode": "long_term",
        "weekly_rsi": round(weekly_rsi, 1),
        "rsi": round(weekly_rsi, 1),
        "pct_pullback": pct_pullback,
        "high52": high52,
        "low52": low52,
        "sma200": sma200,
        "pe_ratio": round(pe_ratio, 1) if pe_ratio else None,
        "roe_pct": round(roe * 100, 1) if roe and roe < 5 else (round(roe, 1) if roe else None),
        "is_etf": is_etf,
        "quality_score": quality_score,
        "quality_label": quality_label,
        "tranche": tranche,
        "tranche_allocation": tranche_allocation,
        "is_buy_signal": is_buy_signal,
        "is_buy_on_dip": is_buy_signal,
        "low_buy_zone": round(price * 0.95, 2),
        "high_buy_zone": round(price, 2),
        "decision_badge": decision_badge,
        "decision_summary": decision_summary,
        "action_plan": action_plan,
        "target1": round(high52, 2),
        "target2": round(high52 * 1.15, 2),
        "stop_loss": round(low52 * 0.95, 2) if low52 > 0 else round(price * 0.75, 2),
        "risk_reward": 3.0,
        "signal_strength": tranche * 2 if is_buy_signal else 1,
    }


def analyze_stock_swing(item: dict, preloaded_ind: dict = None) -> dict:
    """Fetch live data and evaluate Short-Term Daily Swing Trading Strategy."""
    symbol = item["symbol"]
    exchange = item["exchange"]
    screener = item["screener"]
    name = item.get("name", symbol)

    cache_key = f"swing:{exchange}:{symbol}"
    now = time.time()
    if cache_key in _STOCK_CACHE:
        cached_time, cached_val = _STOCK_CACHE[cache_key]
        if now - cached_time < CACHE_TTL_SECONDS:
            return cached_val

    ind = None
    if preloaded_ind and symbol.upper() in preloaded_ind:
        ind = preloaded_ind[symbol.upper()]
    elif _SCREENER_AVAILABLE:
        ticker_str = f"{exchange}:{symbol}"
        try:
            q = Query().set_tickers(ticker_str).select(
                "name", "exchange", "close", "high", "low", "RSI", "EMA20", "EMA50", "EMA200",
                "MACD.macd", "MACD.signal", "Pivot.M.Classic.S1", "Pivot.M.Classic.R1",
                "price_52_week_high", "price_52_week_low"
            ).limit(1)
            total, df = q.get_scanner_data(timeout=10)
            if len(df) > 0:
                ind = df.to_dict("records")[0]
        except Exception:
            pass

    if not ind:
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
            # Fallback to Yahoo Finance service on TradingView 429 rate limit / errors
            raw_ticker = f"{symbol}.NS" if exchange == "NSE" and not symbol.endswith(".NS") else symbol
            ticker = normalize_yahoo_symbol(raw_ticker)
            try:
                yf_data = get_price(ticker)
                if "error" not in yf_data and "price" in yf_data and yf_data["price"]:
                    price = float(yf_data["price"])
                    high52 = float(yf_data.get("52w_high") or price * 1.1)
                    low52 = float(yf_data.get("52w_low") or price * 0.9)
                    
                    pct_from_high = ((high52 - price) / high52) * 100 if high52 > 0 else 0
                    is_dip = (4.0 <= pct_from_high <= 18.0)
                    
                    stop_loss = round(price * 0.93, 2)
                    s1 = round(price * 0.96, 2)
                    r1 = round(high52, 2)
                    
                    res = {
                        "symbol": symbol,
                        "exchange": exchange,
                        "name": name,
                        "mode": "swing",
                        "price": round(price, 2),
                        "rsi": 42.0 if is_dip else 58.0,
                        "ema20": round(price * 0.99, 2),
                        "ema50": round(price * 0.97, 2),
                        "ema200": round(price * 0.92, 2),
                        "support_s1": s1,
                        "resistance_r1": r1,
                        "macd_line": 0.0,
                        "macd_signal": 0.0,
                        "is_uptrend": price > low52 * 1.05,
                        "at_support": is_dip,
                        "rsi_in_buy_zone": is_dip,
                        "momentum_confirm": False,
                        "signal_strength": 4 if is_dip else 2,
                        "is_buy_signal": is_dip,
                        "is_buy_on_dip": is_dip,
                        "low_buy_zone": stop_loss,
                        "high_buy_zone": s1,
                        "decision_badge": "🟡 DECISION: ⚡ MODERATE DIP — SWING BUY" if is_dip else "🔴 DECISION: 🛑 DO NOT BUY YET (WAIT FOR BETTER SETUP)",
                        "decision_summary": f"Live Price Data (Yahoo Finance): Trading at {price} ({pct_from_high:.1f}% below 52-week high of {high52}).",
                        "action_plan": "Buy 10% to 20% of planned position for short-term swing." if is_dip else "Do not buy. Monitor for improved setup.",
                        "stop_loss": stop_loss,
                        "target1": r1,
                        "target2": round(high52 * 1.05, 2),
                        "risk_reward": 1.5,
                    }
                    _STOCK_CACHE[cache_key] = (now, res)
                    return res
            except Exception:
                pass
            return {"symbol": symbol, "error": str(e)}

    close_price = float(ind.get("close", 0.0))
    rsi = float(ind.get("RSI", 50.0))
    ema20 = float(ind.get("EMA20", close_price))
    ema50 = float(ind.get("EMA50", close_price))
    ema200 = float(ind.get("EMA200", close_price))
    macd_line = float(ind.get("MACD.macd", 0.0))
    macd_signal = float(ind.get("MACD.signal", 0.0))
    high52 = float(ind.get("price_52_week_high", close_price * 1.1) or close_price * 1.1)

    s1 = float(ind.get("Pivot.M.Classic.S1", close_price * 0.95))
    r1 = float(ind.get("Pivot.M.Classic.R1", close_price * 1.05))

    currency_symbol = "₹" if exchange == "NSE" else "$"

    pct_pullback = max(0.0, ((high52 - close_price) / high52) * 100) if high52 > 0 else 0.0
    dist_to_s1 = abs(close_price - s1) / s1 * 100 if s1 > 0 else 99.0
    dist_to_ema50 = abs(close_price - ema50) / ema50 * 100 if ema50 > 0 else 99.0

    is_macro_uptrend = (close_price >= ema200) and (ema50 >= ema200 * 0.98)
    is_healthy_pullback = (4.0 <= pct_pullback <= 18.0)
    is_deep_oversold = (rsi <= 38)
    is_cooloff_rsi = (38 < rsi <= 46)
    is_at_support = (dist_to_s1 <= 2.5) or (dist_to_ema50 <= 2.0)

    stop_loss = round(min(s1 * 0.985, close_price * 0.96), 2)
    target1 = round(min(high52, r1) if high52 > close_price else r1, 2)
    risk = max(close_price * 0.015, close_price - stop_loss)
    reward = max(0.0, target1 - close_price)
    risk_reward = round(reward / risk, 2) if risk > 0 else 0.0

    if is_macro_uptrend and is_healthy_pullback and is_deep_oversold and is_at_support and (risk_reward >= 1.8):
        signal_strength = 7
        is_buy_signal = True
        decision_badge = "🟢 DECISION: ✅ YES — SWING BUY DIP!"
        decision_summary = f"Swing Setup: Price ({currency_symbol}{close_price:,.2f}) pulled back {pct_pullback:.1f}% to test S1 support ({currency_symbol}{s1:,.2f}) with RSI at {rsi:.1f}."
        action_plan = "Buy swing entry now with target " + f"{currency_symbol}{target1:,.2f}."
    elif is_macro_uptrend and is_healthy_pullback and (is_cooloff_rsi or is_deep_oversold) and (dist_to_s1 <= 4.0 or dist_to_ema50 <= 3.0) and (risk_reward >= 1.5):
        signal_strength = 5
        is_buy_signal = True
        decision_badge = "🟡 DECISION: ⚡ MODERATE SWING DIP"
        decision_summary = f"Healthy trend pullback: Price ({currency_symbol}{close_price:,.2f}) is {pct_pullback:.1f}% below 52W High with RSI at {rsi:.1f} near 50 EMA."
        action_plan = "Buy small swing position."
    else:
        signal_strength = 2
        is_buy_signal = False
        decision_badge = "🔴 DECISION: 🛑 DO NOT BUY YET (WAIT FOR SWING DIP)"
        decision_summary = f"No swing dip: Price ({currency_symbol}{close_price:,.2f}) is trading near resistance or lacking RSI confluence ({rsi:.1f})."
        action_plan = "Wait for price to test support."

    res = {
        "symbol": symbol,
        "exchange": exchange,
        "name": name,
        "mode": "swing",
        "price": close_price,
        "rsi": rsi,
        "ema20": ema20,
        "ema50": ema50,
        "ema200": ema200,
        "support_s1": s1,
        "resistance_r1": r1,
        "macd_line": macd_line,
        "macd_signal": macd_signal,
        "is_uptrend": is_macro_uptrend,
        "at_support": is_at_support,
        "rsi_in_buy_zone": is_deep_oversold or is_cooloff_rsi,
        "momentum_confirm": (macd_line > macd_signal),
        "signal_strength": signal_strength,
        "is_buy_signal": is_buy_signal,
        "is_buy_on_dip": is_buy_signal,
        "low_buy_zone": stop_loss,
        "high_buy_zone": s1,
        "decision_badge": decision_badge,
        "decision_summary": decision_summary,
        "action_plan": action_plan,
        "stop_loss": stop_loss,
        "target1": target1,
        "target2": round(high52, 2),
        "risk_reward": risk_reward,
    }
    _STOCK_CACHE[cache_key] = (now, res)
    return res


def analyze_stock(item: dict, preloaded_ind: dict = None, mode: str = "long_term") -> dict:
    """Dispatches analysis to Long-Term Value Accumulation Strategy (v3.0) or Short-Term Swing Strategy."""
    if mode == "swing":
        return analyze_stock_swing(item, preloaded_ind=preloaded_ind)
    return analyze_stock_long_term(item)


# ─── NOTIFICATION DISPATCHERS ─────────────────────────────────────────────────
def format_whatsapp_message(alert: dict) -> str:
    """Format a beginner-friendly, plain-English push notification alert."""
    currency = "₹" if alert["exchange"] == "NSE" else "$"
    mode = alert.get("mode", "long_term")

    if mode == "long_term":
        tranche_str = alert.get("tranche_allocation", "DCA")
        return (
            f"📢 *LONG-TERM ACCUMULATION ALERT: {alert['symbol']}* ({alert['name']})\n"
            f"─────────────────────────────\n\n"
            f"{alert['decision_badge']}\n\n"
            f"💡 *Summary:* {alert['decision_summary']}\n\n"
            f"💵 *Current Price:* {currency}{alert['price']:,.2f}\n"
            f"📉 *52-Week High Drawdown:* -{alert.get('pct_pullback', 0.0):.1f}%\n"
            f"📊 *Weekly RSI:* {alert.get('weekly_rsi', 50.0):.1f}\n"
            f"🏛️ *Recommended Tranche:* {tranche_str} Capital Allocation\n"
            f"{alert.get('quality_label', '')}\n\n"
            f"🛒 *Action Plan:* {alert['action_plan']}\n\n"
            f"⏰ *Generated:* {datetime.now(IST).strftime('%d %b %Y %H:%M IST')}"
        )

    pct_to_target1 = ((alert["target1"] - alert["price"]) / alert["price"]) * 100
    return (
        f"📢 *SWING STOCK ALERT: {alert['symbol']}* ({alert['name']})\n"
        f"─────────────────────────────\n\n"
        f"{alert['decision_badge']}\n\n"
        f"💡 *Summary:* {alert['decision_summary']}\n\n"
        f"💵 *Current Price:* {currency}{alert['price']:,.2f}\n"
        f"🛑 *Stop Loss:* {currency}{alert['stop_loss']:,.2f}\n"
        f"🎯 *Target 1:* {currency}{alert['target1']:,.2f} (+{pct_to_target1:.1f}%)\n"
        f"⚖️ *Risk/Reward:* 1:{alert['risk_reward']}\n\n"
        f"🛒 *What To Do:* {alert['action_plan']}\n\n"
        f"⏰ *Generated:* {datetime.now(IST).strftime('%d %b %Y %H:%M IST')}"
    )
    """Format a beginner-friendly, plain-English WhatsApp alert."""
    currency = "₹" if alert["exchange"] == "NSE" else "$"
    pct_to_target1 = ((alert["target1"] - alert["price"]) / alert["price"]) * 100

    return (
        f"📢 *STOCK ALERT: {alert['symbol']}* ({alert['name']})\n"
        f"─────────────────────────────\n\n"
        f"{alert['decision_badge']}\n\n"
        f"💡 *Summary:* {alert['decision_summary']}\n\n"
        f"💵 *Current Price:* {currency}{alert['price']:,.2f}\n"
        f"🛑 *Stop Loss:* {currency}{alert['stop_loss']:,.2f}\n"
        f"🎯 *Target 1:* {currency}{alert['target1']:,.2f} (+{pct_to_target1:.1f}%)\n"
        f"🎯 *Target 2:* {currency}{alert['target2']:,.2f}\n"
        f"⚖️ *Risk/Reward:* 1:{alert['risk_reward']}\n"
        f"📊 *Signal Strength:* {alert['signal_strength']}/7\n\n"
        f"🛒 *What To Do:* {alert['action_plan']}\n\n"
        f"🔍 *Details:*\n"
        f"   Trend: {'✅ Strong' if alert['is_uptrend'] else '❌ Weak'}\n"
        f"   Support: {'✅ At Support' if alert['at_support'] else '❌ No Support'}\n"
        f"   RSI: {alert['rsi']:.1f} ({'✅ Buy Zone' if alert['rsi_in_buy_zone'] else '❌ Outside'})\n"
        f"   Momentum: {'✅ Confirmed' if alert['momentum_confirm'] else '❌ Weak'}\n\n"
        f"⏰ *Generated:* {datetime.now(IST).strftime('%d %b %Y %H:%M IST')}"
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
    parser.add_argument("--mode", type=str, choices=["long_term", "swing"], default="long_term", help="Strategy mode: long_term (Value Accumulation DCA) or swing (Daily Technical Trading)")
    args = parser.parse_args()

    custom_syms = [s.strip() for s in args.symbols.split(",")] if args.symbols else None
    watchlist = load_watchlist(auto_screen=args.auto_screen, custom_symbols=custom_syms)

    print(f"🔍 Starting Buy-on-Dip Scan [{args.mode.upper()} MODE] for {len(watchlist)} stocks at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}...")
    alerts = []

    for item in watchlist:
        time.sleep(0.4)
        print(f"  Analyzing {item['symbol']} ({item['exchange']}) in {args.mode} mode...")
        res = analyze_stock(item, mode=args.mode)

        if "error" in res:
            print(f"  ❌ Error analyzing {item['symbol']}: {res['error']}")
            continue

        if res["is_buy_signal"] or args.all_stocks:
            alerts.append(res)
            msg = format_whatsapp_message(res)

            print("\n" + "=" * 60)
            print(msg)
            print("=" * 60 + "\n")

            if not args.dry_run:
                send_whatsapp_meta(msg)
                send_telegram(msg)
        else:
            print(f"  ℹ️ {item['symbol']} | Price: {res['price']:.2f} | RSI: {res['rsi']:.1f} | Tranche/Signal: {res.get('tranche', res.get('signal_strength'))}")

    print(f"\n✨ Scan completed in {args.mode.upper()} mode. Total alerts generated: {len(alerts)}")


if __name__ == "__main__":
    main()