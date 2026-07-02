"""Test signal generator."""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime
from signal_system.generator import SignalGenerator

@pytest.fixture
def sample_df():
    dates = pd.date_range(end=datetime.now(), periods=60, freq="B")
    np.random.seed(42)
    prices = 100 + np.cumsum(np.random.randn(60) * 0.5)
    return pd.DataFrame({
        "Open": prices,
        "High": prices + 1,
        "Low": prices - 1,
        "Close": prices,
        "Volume": np.random.randint(1_000_000, 10_000_000, 60),
    }, index=dates)


def test_ma_cross_signal(sample_df):
    sig = SignalGenerator.ma_cross_signal(sample_df)
    assert sig["signal"] == "ma_cross"
    assert sig["action"] in ("BUY", "SELL", "HOLD")
    assert "fast_ma" in sig
    assert "slow_ma" in sig


def test_rsi_signal(sample_df):
    sig = SignalGenerator.rsi_signal(sample_df)
    assert sig["signal"] == "rsi"
    assert sig["action"] in ("BUY", "SELL", "HOLD")
    assert 0 <= sig["rsi"] <= 100


def test_macd_signal(sample_df):
    sig = SignalGenerator.macd_signal(sample_df)
    assert sig["signal"] == "macd"
    assert sig["action"] in ("BUY", "SELL", "HOLD")


def test_bollinger_signal(sample_df):
    sig = SignalGenerator.bollinger_signal(sample_df)
    assert sig["signal"] == "bollinger"
    assert sig["action"] in ("BUY", "SELL", "HOLD")
    assert sig["upper_band"] > sig["lower_band"]


def test_volume_anomaly(sample_df):
    sig = SignalGenerator.volume_anomaly(sample_df)
    assert sig["signal"] == "volume_anomaly"
    assert sig["action"] in ("ALERT", "NORMAL")


def test_generate_all(sample_df):
    gen = SignalGenerator()
    signals = gen.generate_all(sample_df)
    assert len(signals) == 5


def test_generate_summary(sample_df):
    gen = SignalGenerator()
    summary = gen.generate_summary(sample_df, "TEST")
    assert summary["symbol"] == "TEST"
    assert summary["overall_signal"] in ("BUY", "SELL", "HOLD")
    assert summary["buy_signals"] + summary["sell_signals"] + summary["hold_signals"] <= 5
