"""Backtrader trading strategies."""
import backtrader as bt


class MovingAverageCross(bt.Strategy):
    """Moving average crossover strategy.

    Buy when fast MA crosses above slow MA, sell when it crosses below.
    """

    params = (("fast_period", 10), ("slow_period", 30))

    def __init__(self):
        self.fast_ma = bt.indicators.SMA(self.data.close, period=self.p.fast_period)
        self.slow_ma = bt.indicators.SMA(self.data.close, period=self.p.slow_period)
        self.crossover = bt.indicators.CrossOver(self.fast_ma, self.slow_ma)

    def next(self):
        if not self.position:
            if self.crossover > 0:
                self.buy()
        elif self.crossover < 0:
            self.sell()


class RSIStrategy(bt.Strategy):
    """RSI mean-reversion strategy.

    Buy when RSI < oversold, sell when RSI > overbought.
    """

    params = (("rsi_period", 14), ("oversold", 30), ("overbought", 70))

    def __init__(self):
        self.rsi = bt.indicators.RSI(self.data.close, period=self.p.rsi_period)

    def next(self):
        if not self.position:
            if self.rsi < self.p.oversold:
                self.buy()
        elif self.rsi > self.p.overbought:
            self.sell()


class MACDStrategy(bt.Strategy):
    """MACD crossover strategy."""

    params = (("fast_period", 12), ("slow_period", 26), ("signal_period", 9))

    def __init__(self):
        self.macd = bt.indicators.MACD(
            self.data.close,
            period_me1=self.p.fast_period,
            period_me2=self.p.slow_period,
            period_signal=self.p.signal_period,
        )
        self.crossover = bt.indicators.CrossOver(self.macd.macd, self.macd.signal)

    def next(self):
        if not self.position:
            if self.crossover > 0:
                self.buy()
        elif self.crossover < 0:
            self.sell()


class BollingerBandsStrategy(bt.Strategy):
    """Bollinger Bands mean-reversion strategy.

    Buy when price touches lower band, sell when price touches upper band.
    """

    params = (("bb_period", 20), ("bb_dev", 2.0))

    def __init__(self):
        self.bands = bt.indicators.BollingerBands(
            self.data.close, period=self.p.bb_period, devfactor=self.p.bb_dev
        )

    def next(self):
        if not self.position:
            if self.data.close < self.bands.lines.bot:
                self.buy()
        elif self.data.close > self.bands.lines.top:
            self.sell()
