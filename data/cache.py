"""SQLite cache for stock market data."""
import sqlite3
from pathlib import Path
from datetime import datetime
import pandas as pd


class DataCache:
    """Local SQLite cache for OHLCV data."""

    def __init__(self, db_path: str = "data/cache/stock_data.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS daily_prices (
                    symbol TEXT NOT NULL,
                    date TEXT NOT NULL,
                    open REAL,
                    high REAL,
                    low REAL,
                    close REAL,
                    volume INTEGER,
                    PRIMARY KEY (symbol, date)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS metadata (
                    symbol TEXT PRIMARY KEY,
                    last_updated TEXT,
                    company_name TEXT,
                    sector TEXT,
                    industry TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS watchlist (
                    symbol TEXT PRIMARY KEY,
                    added_at TEXT,
                    note TEXT
                )
            """)

    def save_daily(self, symbol: str, df: pd.DataFrame):
        """Save daily OHLCV data to cache."""
        with sqlite3.connect(self.db_path) as conn:
            for idx, row in df.iterrows():
                conn.execute(
                    """INSERT OR REPLACE INTO daily_prices
                       (symbol, date, open, high, low, close, volume)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (symbol, idx.strftime("%Y-%m-%d"),
                     float(row["Open"]), float(row["High"]),
                     float(row["Low"]), float(row["Close"]),
                     int(row["Volume"])),
                )
            conn.execute(
                """INSERT OR REPLACE INTO metadata (symbol, last_updated)
                   VALUES (?, ?)""",
                (symbol, datetime.now().isoformat()),
            )
            conn.commit()

    def load_daily(self, symbol: str, start: str = None, end: str = None) -> pd.DataFrame:
        """Load daily OHLCV from cache. Returns DataFrame with DatetimeIndex."""
        query = "SELECT date, open, high, low, close, volume FROM daily_prices WHERE symbol = ?"
        params = [symbol]
        if start:
            query += " AND date >= ?"
            params.append(start)
        if end:
            query += " AND date <= ?"
            params.append(end)
        query += " ORDER BY date"
        with sqlite3.connect(self.db_path) as conn:
            df = pd.read_sql_query(query, conn, params=params)
        if df.empty:
            return df
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date")
        df.columns = [c.capitalize() for c in df.columns]
        return df

    def get_last_date(self, symbol: str) -> str | None:
        """Get the last cached date for a symbol."""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT MAX(date) FROM daily_prices WHERE symbol = ?", (symbol,)
            ).fetchone()
        return row[0] if row and row[0] else None

    def list_symbols(self) -> list[str]:
        """List all cached symbols."""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("SELECT symbol FROM metadata ORDER BY symbol").fetchall()
        return [r[0] for r in rows]

    def add_to_watchlist(self, symbol: str, note: str = ""):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT OR REPLACE INTO watchlist (symbol, added_at, note)
                   VALUES (?, ?, ?)""",
                (symbol, datetime.now().isoformat(), note),
            )
            conn.commit()

    def get_watchlist(self) -> list[dict]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT symbol, added_at, note FROM watchlist ORDER BY symbol"
            ).fetchall()
        return [{"symbol": r[0], "added_at": r[1], "note": r[2]} for r in rows]

    def remove_from_watchlist(self, symbol: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM watchlist WHERE symbol = ?", (symbol,))
            conn.commit()
