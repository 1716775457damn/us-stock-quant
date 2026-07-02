# us-stock-quant

美股量化交易信号系统 — 数据抓取 + 策略回测 + AI选股 + 实时监控面板

## 架构

```
data/        数据层 — yfinance 抓取 + SQLite 缓存
backtest/    回测层 — backtrader 技术指标 + qlib AI模型
signal/      信号系统 — 每日生成买卖信号，推送通知
dashboard/   监控面板 — Streamlit Web UI
broker/      交易接口 — 抽象层，预留实盘接入
```

## 快速开始

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 启动监控面板
streamlit run dashboard/app.py
```

## 数据源

- yfinance (免费) — 历史行情 + 实时数据
- 后续可接入富途/老虎/IBKR 实盘接口

## 功能

1. 多股票行情抓取与本地缓存
2. 技术指标策略回测（均线交叉、RSI、MACD、布林带）
3. AI选股模型（LightGBM 因子模型 via qlib）
4. 每日交易信号生成 + 微信/飞书推送
5. Streamlit 实时监控面板

## License

MIT
