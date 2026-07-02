#!/usr/bin/env python3
"""CLI entry point for us-stock-quant.

Usage:
  python main.py fetch AAPL MSFT NVDA          # Download data
  python main.py signal AAPL                    # Generate signals
  python main.py backtest AAPL                  # Run backtests
  python main.py dashboard                      # Launch Streamlit
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def cmd_fetch(args):
    from data.fetcher import DataFetcher
    fetcher = DataFetcher()
    for symbol in args:
        df = fetcher.fetch_history(symbol, period="1y", force_refresh=True)
        if df.empty:
            print(f"  {symbol}: FAILED")
        else:
            print(f"  {symbol}: {len(df)} rows, latest={df.index[-1].strftime('%Y-%m-%d')} close=${df['Close'].iloc[-1]:.2f}")


def cmd_signal(args):
    from data.fetcher import DataFetcher
    from signal_system.generator import SignalGenerator
    from signal_system.notifier import SignalNotifier
    fetcher = DataFetcher()
    gen = SignalGenerator()
    notifier = SignalNotifier()

    for symbol in args:
        df = fetcher.fetch_history(symbol, period="6mo")
        if df.empty or len(df) < 30:
            print(f"  {symbol}: 数据不足")
            continue
        summary = gen.generate_summary(df, symbol)
        notifier.notify(summary)


def cmd_backtest(args):
    from data.fetcher import DataFetcher
    from backtest.runner import BacktestRunner
    fetcher = DataFetcher()
    runner = BacktestRunner()

    for symbol in args:
        df = fetcher.fetch_history(symbol, period="1y")
        if df.empty:
            print(f"  {symbol}: 无法获取数据")
            continue
        print(f"\n=== {symbol} 回测结果 ===")
        results = runner.run_multiple(df)
        comp = runner.compare(results)
        print(comp.to_string(index=False))


def cmd_dashboard(args):
    import subprocess
    app_path = os.path.join(os.path.dirname(__file__), "dashboard", "app.py")
    subprocess.run([sys.executable, "-m", "streamlit", "run", app_path])


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]
    args = sys.argv[2:]

    commands = {
        "fetch": cmd_fetch,
        "signal": cmd_signal,
        "backtest": cmd_backtest,
        "dashboard": cmd_dashboard,
    }

    if cmd not in commands:
        print(f"Unknown command: {cmd}")
        print(__doc__)
        sys.exit(1)

    commands[cmd](args)


if __name__ == "__main__":
    main()
