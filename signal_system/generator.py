"""Signal generator — compute technical indicators and generate buy/sell signals."""
import pandas as pd
import numpy as np
from datetime import datetime


class SignalGenerator:
    """Generate trading signals from technical indicators."""

    @staticmethod
    def ma_cross_signal(df: pd.DataFrame, fast: int = 10, slow: int = 30) -> dict:
        """Moving average crossover signal."""
        close = df["Close"]
        fast_ma = close.rolling(window=fast).mean()
        slow_ma = close.rolling(window=slow).mean()

        prev_fast = fast_ma.iloc[-2]
        prev_slow = slow_ma.iloc[-2]
        curr_fast = fast_ma.iloc[-1]
        curr_slow = slow_ma.iloc[-1]

        crossed_up = (prev_fast <= prev_slow) and (curr_fast > curr_slow)
        crossed_down = (prev_fast >= prev_slow) and (curr_fast < curr_slow)

        if crossed_up:
            action = "BUY"
        elif crossed_down:
            action = "SELL"
        else:
            action = "HOLD"

        return {
            "signal": "ma_cross",
            "action": action,
            "fast_ma": round(curr_fast, 2),
            "slow_ma": round(curr_slow, 2),
            "price": round(close.iloc[-1], 2),
            "date": df.index[-1].strftime("%Y-%m-%d"),
        }

    @staticmethod
    def rsi_signal(df: pd.DataFrame, period: int = 14, oversold: int = 30, overbought: int = 70) -> dict:
        """RSI signal."""
        close = df["Close"]
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        curr_rsi = rsi.iloc[-1]

        if curr_rsi < oversold:
            action = "BUY"
        elif curr_rsi > overbought:
            action = "SELL"
        else:
            action = "HOLD"

        return {
            "signal": "rsi",
            "action": action,
            "rsi": round(curr_rsi, 2),
            "oversold": oversold,
            "overbought": overbought,
            "price": round(close.iloc[-1], 2),
            "date": df.index[-1].strftime("%Y-%m-%d"),
        }

    @staticmethod
    def macd_signal(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> dict:
        """MACD signal."""
        close = df["Close"]
        ema_fast = close.ewm(span=fast, adjust=False).mean()
        ema_slow = close.ewm(span=slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()

        prev_diff = (macd_line - signal_line).iloc[-2]
        curr_diff = (macd_line - signal_line).iloc[-1]

        crossed_up = (prev_diff <= 0) and (curr_diff > 0)
        crossed_down = (prev_diff >= 0) and (curr_diff < 0)

        if crossed_up:
            action = "BUY"
        elif crossed_down:
            action = "SELL"
        else:
            action = "HOLD"

        return {
            "signal": "macd",
            "action": action,
            "macd": round(macd_line.iloc[-1], 4),
            "signal_line": round(signal_line.iloc[-1], 4),
            "histogram": round(curr_diff, 4),
            "price": round(close.iloc[-1], 2),
            "date": df.index[-1].strftime("%Y-%m-%d"),
        }

    @staticmethod
    def bollinger_signal(df: pd.DataFrame, period: int = 20, dev: float = 2.0) -> dict:
        """Bollinger Bands signal."""
        close = df["Close"]
        ma = close.rolling(window=period).mean()
        std = close.rolling(window=period).std()
        upper = ma + dev * std
        lower = ma - dev * std
        curr_price = close.iloc[-1]

        if curr_price < lower.iloc[-1]:
            action = "BUY"
        elif curr_price > upper.iloc[-1]:
            action = "SELL"
        else:
            action = "HOLD"

        return {
            "signal": "bollinger",
            "action": action,
            "upper_band": round(upper.iloc[-1], 2),
            "middle_band": round(ma.iloc[-1], 2),
            "lower_band": round(lower.iloc[-1], 2),
            "price": round(curr_price, 2),
            "date": df.index[-1].strftime("%Y-%m-%d"),
        }

    @staticmethod
    def volume_anomaly(df: pd.DataFrame, window: int = 20, threshold: float = 2.0) -> dict:
        """Volume anomaly detection."""
        vol = df["Volume"]
        avg_vol = vol.rolling(window=window).mean().iloc[-1]
        curr_vol = vol.iloc[-1]
        ratio = curr_vol / avg_vol if avg_vol > 0 else 0

        action = "ALERT" if ratio > threshold else "NORMAL"

        return {
            "signal": "volume_anomaly",
            "action": action,
            "current_volume": int(curr_vol),
            "avg_volume": int(avg_vol),
            "volume_ratio": round(ratio, 2),
            "price": round(df["Close"].iloc[-1], 2),
            "date": df.index[-1].strftime("%Y-%m-%d"),
        }

    def generate_all(self, df: pd.DataFrame) -> list[dict]:
        """Generate all signals for a dataframe."""
        if df.empty or len(df) < 30:
            return []
        signals = []
        for method in [self.ma_cross_signal, self.rsi_signal, self.macd_signal, self.bollinger_signal, self.volume_anomaly]:
            try:
                sig = method(df)
                signals.append(sig)
            except Exception as e:
                signals.append({"signal": method.__name__, "error": str(e)})
        return signals

    def generate_summary(self, df: pd.DataFrame, symbol: str) -> dict:
        """Generate a summary signal for a symbol."""
        signals = self.generate_all(df)
        buy_count = sum(1 for s in signals if s.get("action") == "BUY")
        sell_count = sum(1 for s in signals if s.get("action") == "SELL")

        if buy_count > sell_count and buy_count >= 2:
            overall = "BUY"
        elif sell_count > buy_count and sell_count >= 2:
            overall = "SELL"
        else:
            overall = "HOLD"

        return {
            "symbol": symbol,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "overall_signal": overall,
            "buy_signals": buy_count,
            "sell_signals": sell_count,
            "hold_signals": sum(1 for s in signals if s.get("action") == "HOLD"),
            "details": signals,
            "price": round(df["Close"].iloc[-1], 2) if not df.empty else None,
        }
