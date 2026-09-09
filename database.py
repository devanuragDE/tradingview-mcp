"""
SQLite Database Layer for Buy-on-Dip Trading Intelligence Platform (v2.0)
Manages watchlists, signal history, and user settings.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "trading_platform.db"


def get_db_connection() -> sqlite3.Connection:
    """Establish connection to SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Initialize database tables and seed default watchlists."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # 1. Watchlists Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS watchlists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT UNIQUE NOT NULL,
                exchange TEXT NOT NULL,
                screener TEXT NOT NULL,
                name TEXT NOT NULL,
                category TEXT DEFAULT 'Custom',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 2. Signal Logs Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS signal_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                exchange TEXT NOT NULL,
                price REAL NOT NULL,
                rsi REAL NOT NULL,
                dip_score INTEGER NOT NULL,
                decision_badge TEXT NOT NULL,
                decision_summary TEXT NOT NULL,
                action_plan TEXT NOT NULL,
                low_buy_zone REAL NOT NULL,
                high_buy_zone REAL NOT NULL,
                target_price REAL NOT NULL,
                stop_loss REAL NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 3. User Settings Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)

        conn.commit()
    seed_default_watchlist()


def seed_default_watchlist() -> None:
    """Seed initial watchlist if table is empty."""
    default_symbols = [
        # US ETFs & MegaCaps
        ("QQQ", "NASDAQ", "america", "Invesco QQQ Trust", "US ETFs"),
        ("SPY", "AMEX", "america", "SPDR S&P 500 ETF", "US ETFs"),
        ("NVDA", "NASDAQ", "america", "NVIDIA Corp.", "US MegaCap"),
        ("AAPL", "NASDAQ", "america", "Apple Inc.", "US MegaCap"),
        ("MSFT", "NASDAQ", "america", "Microsoft Corp.", "US MegaCap"),
        ("AMZN", "NASDAQ", "america", "Amazon.com Inc.", "US MegaCap"),
        ("GOOGL", "NASDAQ", "america", "Alphabet Inc.", "US MegaCap"),
        ("META", "NASDAQ", "america", "Meta Platforms", "US MegaCap"),
        ("TSLA", "NASDAQ", "america", "Tesla Inc.", "US MegaCap"),
        
        # Indian Stock Leaders
        ("HINDUNILVR", "NSE", "india", "Hindustan Unilever", "India Bluechip"),
        ("TRIDENT", "NSE", "india", "Trident Ltd", "India MidCap"),
        ("IRFC", "NSE", "india", "Indian Railway Finance", "India PSU"),
        ("MSUMI", "NSE", "india", "Motherson Sumi Wiring", "India Auto"),
        ("TITAN", "NSE", "india", "Titan Company", "India Consumer"),
        ("BSOFT", "NSE", "india", "Birlasoft Ltd", "India IT"),
        ("DMART", "NSE", "india", "Avenue Supermarts (D-Mart)", "India Retail"),
        ("TATAMOTORS", "NSE", "india", "Tata Motors Ltd", "India Auto"),
        ("BHARTIARTL", "NSE", "india", "Bharti Airtel", "India Telecom"),
        ("TATACHEM", "NSE", "india", "Tata Chemicals", "India Chemical"),
        ("VBL", "NSE", "india", "Varun Beverages", "India Consumer"),
        ("RITES", "NSE", "india", "RITES Ltd", "India PSU"),
        ("FEDERALBNK", "NSE", "india", "Federal Bank", "India Banking"),
        ("JIOFIN", "NSE", "india", "Jio Financial Services", "India NBFC"),
        ("MOTHERSON", "NSE", "india", "Samvardhana Motherson", "India Auto"),
        ("SBIN", "NSE", "india", "State Bank of India", "India Banking"),
        ("ICICIBANK", "NSE", "india", "ICICI Bank", "India Banking"),
        ("IGL", "NSE", "india", "Indraprastha Gas", "India Energy"),
        ("RELIANCE", "NSE", "india", "Reliance Industries", "India Conglomerate"),
        ("KAYNES", "NSE", "india", "Kaynes Technology", "India Electronics"),
        ("AVANTIFEED", "NSE", "india", "Avanti Feeds", "India Agro"),
        ("RADICO", "NSE", "india", "Radico Khaitan", "India Consumer"),
        ("TCS", "NSE", "india", "Tata Consultancy Services", "India IT"),
        ("INFY", "NSE", "india", "Infosys Ltd", "India IT"),
        ("HDFCBANK", "NSE", "india", "HDFC Bank", "India Banking"),
    ]

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM watchlists")
        count = cursor.fetchone()[0]
        if count == 0:
            cursor.executemany("""
                INSERT OR IGNORE INTO watchlists (symbol, exchange, screener, name, category)
                VALUES (?, ?, ?, ?, ?)
            """, default_symbols)
            conn.commit()


# ─── WATCHLIST CRUD ───────────────────────────────────────────────────────────
def get_all_watchlist_items() -> list[dict]:
    """Retrieve all watchlist stocks."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        rows = cursor.execute("SELECT * FROM watchlists ORDER BY category, symbol").fetchall()
        return [dict(row) for row in rows]


def add_watchlist_item(symbol: str, exchange: str = "NASDAQ", screener: str = "america", name: str = "", category: str = "Custom") -> dict:
    """Add a new stock ticker to the database watchlist."""
    symbol = symbol.strip().upper()
    if ".NS" in symbol or symbol.endswith("-IN"):
        symbol = symbol.replace(".NS", "").replace("-IN", "")
        exchange = "NSE"
        screener = "india"

    if not name:
        name = symbol

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO watchlists (symbol, exchange, screener, name, category)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(symbol) DO UPDATE SET exchange=excluded.exchange, screener=excluded.screener
        """, (symbol, exchange, screener, name, category))
        conn.commit()
    return {"status": "success", "symbol": symbol, "exchange": exchange}


def delete_watchlist_item(symbol: str) -> dict:
    """Remove a ticker from the database watchlist."""
    symbol = symbol.strip().upper().replace(".NS", "")
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM watchlists WHERE symbol = ?", (symbol,))
        conn.commit()
    return {"status": "deleted", "symbol": symbol}


# ─── SIGNAL LOGS CRUD ─────────────────────────────────────────────────────────
def log_signal(signal: dict) -> None:
    """Record a generated Buy-on-Dip signal to the database log."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO signal_logs (
                symbol, exchange, price, rsi, dip_score, decision_badge,
                decision_summary, action_plan, low_buy_zone, high_buy_zone,
                target_price, stop_loss
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            signal["symbol"], signal["exchange"], signal["price"], signal["rsi"],
            signal.get("dip_score", 50), signal["decision_badge"], signal["decision_summary"],
            signal["action_plan"], signal["low_buy_zone"], signal["high_buy_zone"],
            signal["resistance_r1"], signal["support_s1"]
        ))
        conn.commit()


def get_signal_history(limit: int = 50) -> list[dict]:
    """Retrieve historical signal logs."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        rows = cursor.execute("SELECT * FROM signal_logs ORDER BY timestamp DESC LIMIT ?", (limit,)).fetchall()
        return [dict(row) for row in rows]


if __name__ == "__main__":
    init_db()
    items = get_all_watchlist_items()
    print(f"✅ Database initialized cleanly. Total watchlists loaded: {len(items)}")
