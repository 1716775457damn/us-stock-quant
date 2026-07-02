"""Test data layer."""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from data.cache import DataCache
from data.fetcher import DataFetcher


@pytest.fixture
def cache(tmp_path):
    return DataCache(str(tmp_path / "test.db"))


@pytest.fixture
def sample_df():
    """Generate sample OHLCV data."""
    dates = pd.date_range(end=datetime.now(), periods=60, freq="B")
    np.random.seed(42)
    prices = 100 + np.cumsum(np.random.randn(60) * 0.5)
    return pd.DataFrame({
        "Open": prices + np.random.randn(60) * 0.1,
        "High": prices + abs(np.random.randn(60) * 0.3),
        "Low": prices - abs(np.random.randn(60) * 0.3),
        "Close": prices,
        "Volume": np.random.randint(1_000_000, 10_000_000, 60),
    }, index=dates)


def test_cache_save_load(cache, sample_df):
    """Test saving and loading data from cache."""
    cache.save_daily("TEST", sample_df)
    loaded = cache.load_daily("TEST")
    assert not loaded.empty
    assert len(loaded) == 60
    assert "Close" in loaded.columns


def test_cache_symbol_list(cache, sample_df):
    cache.save_daily("TEST", sample_df)
    symbols = cache.list_symbols()
    assert "TEST" in symbols


def test_cache_watchlist(cache):
    cache.add_to_watchlist("AAPL", "test note")
    wl = cache.get_watchlist()
    assert len(wl) == 1
    assert wl[0]["symbol"] == "AAPL"
    cache.remove_from_watchlist("AAPL")
    assert len(cache.get_watchlist()) == 0


def test_cache_date_filter(cache, sample_df):
    cache.save_daily("TEST", sample_df)
    mid_date = sample_df.index[30].strftime("%Y-%m-%d")
    loaded = cache.load_daily("TEST", start=mid_date)
    assert len(loaded) == 30
