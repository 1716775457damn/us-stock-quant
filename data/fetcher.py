"""Stock data fetcher using yfinance with SQLite caching."""
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from .cache import DataCache


class DataFetcher:
    """Fetch US stock data via yfinance, with local SQLite caching."""

    def __init__(self, db_path: str = "data/cache/stock_data.db"):
        self.cache = DataCache(db_path)

    def fetch_history(
        self,
        symbol: str,
        period: str = "1y",
        start: str = None,
        end: str = None,
        use_cache: bool = True,
        force_refresh: bool = False,
    ) -> pd.DataFrame:
        """Fetch OHLCV history for a symbol.

        Args:
            symbol: Ticker symbol, e.g. "AAPL"
            period: yfinance period string ("1d","5d","1mo","3mo","6mo","1y","2y","5y","max")
            start: Start date "YYYY-MM-DD" (overrides period)
            end: End date "YYYY-MM-DD"
            use_cache: Read from cache if available
            force_refresh: Force re-download even if cache exists

        Returns:
            DataFrame with DatetimeIndex, columns [Open, High, Low, Close, Volume]
        """
        if use_cache and not force_refresh:
            cached = self.cache.load_daily(symbol, start, end)
            if not cached.empty:
                last_date = self.cache.get_last_date(symbol)
                today = datetime.now().strftime("%Y-%m-%d")
                if last_date and last_date >= today:
                    return cached
                # Cache is stale — fetch incremental
                incremental_start = (
                    (datetime.strptime(last_date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
                    if last_date
                    else None
                )
                if incremental_start:
                    new_data = self._download(symbol, start=incremental_start)
                    if not new_data.empty:
                        self.cache.save_daily(symbol, new_data)
                    return self.cache.load_daily(symbol, start, end)

        # Full download
        df = self._download(symbol, period=period, start=start, end=end)
        if not df.empty:
            self.cache.save_daily(symbol, df)
        return df

    def _download(self, symbol: str, period: str = None, start: str = None, end: str = None) -> pd.DataFrame:
        """Raw yfinance download."""
        kwargs = {}
        if start and end:
            kwargs["start"] = start
            kwargs["end"] = end
        elif start:
            kwargs["start"] = start
        else:
            kwargs["period"] = period or "1y"
        try:
            df = yf.download(symbol, **kwargs, progress=False, auto_adjust=True)
            if df.empty:
                return df
            # Flatten multi-level columns if present
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            # Standardize column names
            df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
            # Drop rows with NaN
            df = df.dropna()
            return df
        except Exception as e:
            print(f"[ERROR] Failed to download {symbol}: {e}")
            return pd.DataFrame()

    def fetch_realtime(self, symbol: str) -> dict:
        """Fetch real-time quote info."""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.fast_info
            return {
                "symbol": symbol,
                "price": getattr(info, "last_price", None),
                "previous_close": getattr(info, "previous_close", None),
                "open": getattr(info, "open", None),
                "day_high": getattr(info, "day_high", None),
                "day_low": getattr(info, "day_low", None),
                "market_cap": getattr(info, "market_cap", None),
            }
        except Exception as e:
            print(f"[ERROR] Realtime fetch failed for {symbol}: {e}")
            return {"symbol": symbol, "error": str(e)}

    def fetch_info(self, symbol: str) -> dict:
        """Fetch company info."""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.get_info()
            return {
                "symbol": symbol,
                "name": info.get("longName", info.get("shortName", "")),
                "sector": info.get("sector", ""),
                "industry": info.get("industry", ""),
                "market_cap": info.get("marketCap", None),
                "pe_ratio": info.get("trailingPE", None),
                "dividend_yield": info.get("dividendYield", None),
                "52wk_high": info.get("fiftyTwoWeekHigh", None),
                "52wk_low": info.get("fiftyTwoWeekLow", None),
            }
        except Exception as e:
            print(f"[ERROR] Info fetch failed for {symbol}: {e}")
            return {"symbol": symbol, "error": str(e)}

    def fetch_batch(
        self, symbols: list[str], period: str = "1y", force_refresh: bool = False
    ) -> dict[str, pd.DataFrame]:
        """Fetch multiple symbols at once."""
        results = {}
        for s in symbols:
            df = self.fetch_history(s, period=period, force_refresh=force_refresh)
            results[s] = df
        return results

    def update_watchlist_data(self):
        """Refresh data for all watchlist symbols."""
        wl = self.cache.get_watchlist()
        symbols = [item["symbol"] for item in wl]
        return self.fetch_batch(symbols, force_refresh=True)
