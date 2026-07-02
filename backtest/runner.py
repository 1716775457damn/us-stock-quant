"""Backtest runner — execute strategies on historical data."""
import backtrader as bt
import pandas as pd
from datetime import datetime
from .strategies import (
    MovingAverageCross,
    RSIStrategy,
    MACDStrategy,
    BollingerBandsStrategy,
)

STRATEGY_MAP = {
    "ma_cross": MovingAverageCross,
    "rsi": RSIStrategy,
    "macd": MACDStrategy,
    "bollinger": BollingerBandsStrategy,
}


class BacktestRunner:
    """Run backtrader backtests on historical data."""

    def __init__(self, cash: float = 100_000, commission: float = 0.001):
        self.cash = cash
        self.commission = commission

    def run(
        self,
        data: pd.DataFrame,
        strategy_name: str = "ma_cross",
        strategy_params: dict = None,
        cash: float = None,
    ) -> dict:
        """Run a single backtest.

        Args:
            data: OHLCV DataFrame with DatetimeIndex
            strategy_name: Key from STRATEGY_MAP
            strategy_params: Override strategy parameters
            cash: Starting cash (defaults to self.cash)

        Returns:
            Dict with metrics: total_return, sharpe, max_drawdown, trades, final_value
        """
        if strategy_name not in STRATEGY_MAP:
            raise ValueError(f"Unknown strategy: {strategy_name}. Available: {list(STRATEGY_MAP.keys())}")

        strategy_cls = STRATEGY_MAP[strategy_name]
        params = strategy_params or {}

        cerebro = bt.Cerebro()
        cerebro.broker.setcash(cash or self.cash)
        cerebro.broker.setcommission(commission=self.commission)

        # Convert DataFrame to backtrader data feed
        bt_data = bt.feeds.PandasData(dataname=data)
        cerebro.adddata(bt_data)
        cerebro.addstrategy(strategy_cls, **params)

        # Analyzers
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name="sharpe", timeframe=bt.TimeFrame.Days)
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trades")
        cerebro.addanalyzer(bt.analyzers.Returns, _name="returns")

        results = cerebro.run()
        strat = results[0]
        final_value = cerebro.broker.getvalue()

        # Extract metrics
        sharpe = strat.analyzers.sharpe.get_analysis()
        drawdown = strat.analyzers.drawdown.get_analysis()
        trades = strat.analyzers.trades.get_analysis()
        returns = strat.analyzers.returns.get_analysis()

        initial_cash = cash or self.cash
        total_return = ((final_value - initial_cash) / initial_cash) * 100

        # Safely extract nested values from backtrader analyzers
        dd_max = drawdown.get("max", {})
        max_dd_pct = round(dd_max.get("drawdown", 0) * 100, 2) if dd_max else 0.0
        max_dd_money = round(dd_max.get("moneydown", 0), 2) if dd_max else 0.0

        trades_total = trades.get("total", {})
        total_trades = trades_total.get("total", 0) if trades_total else 0
        won_trades = trades.get("won", {}).get("total", 0) if trades else 0
        lost_trades = trades.get("lost", {}).get("total", 0) if trades else 0

        return {
            "strategy": strategy_name,
            "params": params,
            "initial_cash": initial_cash,
            "final_value": round(final_value, 2),
            "total_return_pct": round(total_return, 2),
            "sharpe_ratio": round(sharpe.get("sharperatio", 0) or 0, 4),
            "max_drawdown_pct": max_dd_pct,
            "max_drawdown_money": max_dd_money,
            "total_trades": total_trades,
            "won_trades": won_trades,
            "lost_trades": lost_trades,
            "annual_return_pct": round(returns.get("rnorm100", 0) or 0, 2),
        }

    def run_multiple(
        self,
        data: pd.DataFrame,
        strategies: list[str] = None,
        cash: float = None,
    ) -> list[dict]:
        """Run multiple strategies on the same data for comparison."""
        strategies = strategies or list(STRATEGY_MAP.keys())
        results = []
        for s in strategies:
            try:
                r = self.run(data, strategy_name=s, cash=cash)
                results.append(r)
            except Exception as e:
                results.append({"strategy": s, "error": str(e)})
        return results

    def compare(self, results: list[dict]) -> pd.DataFrame:
        """Convert backtest results to a comparison DataFrame."""
        rows = []
        for r in results:
            if "error" in r:
                rows.append({"strategy": r["strategy"], "error": r["error"]})
            else:
                rows.append({
                    "strategy": r["strategy"],
                    "total_return_%": r["total_return_pct"],
                    "annual_return_%": r["annual_return_pct"],
                    "sharpe": r["sharpe_ratio"],
                    "max_drawdown_%": r["max_drawdown_pct"],
                    "trades": r["total_trades"],
                    "won": r["won_trades"],
                    "lost": r["lost_trades"],
                    "final_value": r["final_value"],
                })
        return pd.DataFrame(rows)
