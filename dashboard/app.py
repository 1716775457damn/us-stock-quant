"""us-stock-quant Dashboard — Streamlit Web UI

Run: streamlit run dashboard/app.py
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

from data.fetcher import DataFetcher
from backtest.runner import BacktestRunner
from signal_system.generator import SignalGenerator
from broker.simulated import SimulatedBroker
from broker.base import OrderSide

# --- Page Config ---
st.set_page_config(
    page_title="美股量化交易系统",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Initialize session state ---
if "fetcher" not in st.session_state:
    st.session_state.fetcher = DataFetcher()
if "broker" not in st.session_state:
    st.session_state.broker = SimulatedBroker()
if "signal_gen" not in st.session_state:
    st.session_state.signal_gen = SignalGenerator()
if "runner" not in st.session_state:
    st.session_state.runner = BacktestRunner()

# --- Sidebar ---
st.sidebar.title("📈 美股量化交易系统")
st.sidebar.caption("us-stock-quant | 信号系统")

page = st.sidebar.radio("功能页面", [
    "📊 行情监控",
    "🔍 交易信号",
    "📈 策略回测",
    "💰 模拟持仓",
    "📋 自选股管理",
])

# --- Default watchlist ---
DEFAULT_SYMBOLS = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META", "SPY"]


def load_watchlist():
    fetcher = st.session_state.fetcher
    wl = fetcher.cache.get_watchlist()
    if not wl:
        for s in DEFAULT_SYMBOLS:
            fetcher.cache.add_to_watchlist(s, "default")
        wl = fetcher.cache.get_watchlist()
    return [item["symbol"] for item in wl]


# ==================== 行情监控 ====================
if page == "📊 行情监控":
    st.title("📊 行情监控")

    symbols = load_watchlist()
    col1, col2 = st.columns([3, 1])
    with col2:
        selected = st.multiselect("选择股票", symbols, default=symbols[:6])
        period = st.selectbox("时间范围", ["1mo", "3mo", "6mo", "1y", "2y", "5y"], index=3)
        if st.button("🔄 刷新数据", use_container_width=True):
            with st.spinner("下载中..."):
                for s in selected:
                    st.session_state.fetcher.fetch_history(s, period=period, force_refresh=True)
                st.success("数据已刷新")

    with col1:
        if not selected:
            st.warning("请选择至少一只股票")
        else:
            for symbol in selected:
                df = st.session_state.fetcher.fetch_history(symbol, period=period)
                if df.empty:
                    st.error(f"无法获取 {symbol} 数据")
                    continue

                st.subheader(f"{symbol}")

                # Price chart with volume
                fig = make_subplots(
                    rows=2, cols=1, shared_xaxes=True,
                    vertical_spacing=0.03, row_heights=[0.7, 0.3],
                    subplot_titles=("价格", "成交量"),
                )
                fig.add_trace(
                    go.Candlestick(
                        x=df.index, open=df["Open"], high=df["High"],
                        low=df["Low"], close=df["Close"], name="OHLC"
                    ),
                    row=1, col=1,
                )
                fig.add_trace(
                    go.Bar(x=df.index, y=df["Volume"], name="Volume", marker_color="rgba(0,212,170,0.5)"),
                    row=2, col=1,
                )
                fig.update_layout(height=400, xaxis_rangeslider_visible=False, showlegend=False)
                fig.update_yaxes(title_text="价格 ($)", row=1, col=1)
                fig.update_yaxes(title_text="成交量", row=2, col=1)
                st.plotly_chart(fig, use_container_width=True)

                # Stats
                c1, c2, c3, c4 = st.columns(4)
                latest = df.iloc[-1]
                c1.metric("最新价", f"${latest['Close']:.2f}")
                c2.metric("日涨跌", f"{((latest['Close'] - latest['Open']) / latest['Open'] * 100):.2f}%")
                c3.metric("成交量", f"{int(latest['Volume']):,}")
                c4.metric("区间最高", f"${df['High'].max():.2f}")
                st.divider()


# ==================== 交易信号 ====================
elif page == "🔍 交易信号":
    st.title("🔍 交易信号")

    symbols = load_watchlist()
    col1, col2 = st.columns([3, 1])
    with col2:
        selected = st.multiselect("选择股票", symbols, default=symbols[:1])
        if st.button("⚡ 生成信号", use_container_width=True):
            st.session_state.signals_generated = True

    with col1:
        if getattr(st.session_state, "signals_generated", False):
            gen = st.session_state.signal_gen
            summaries = []
            for symbol in selected:
                df = st.session_state.fetcher.fetch_history(symbol, period="6mo")
                if df.empty or len(df) < 30:
                    st.warning(f"{symbol} 数据不足")
                    continue
                summary = gen.generate_summary(df, symbol)
                summaries.append(summary)

            if not summaries:
                st.warning("无有效数据")
            else:
                # Summary table
                rows = []
                for s in summaries:
                    rows.append({
                        "股票": s["symbol"],
                        "综合信号": s["overall_signal"],
                        "买入": s["buy_signals"],
                        "卖出": s["sell_signals"],
                        "观望": s["hold_signals"],
                        "价格": f"${s['price']:.2f}" if s.get("price") else "N/A",
                    })
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

                # Per-symbol detail with charts
                for s in summaries:
                    details = s.get("details", [])
                    if not details:
                        continue

                    color = {"BUY": "🟢", "SELL": "🔴", "HOLD": "🟡"}.get(s["overall_signal"], "⚪")
                    with st.expander(f"{color} {s['symbol']} — {s['overall_signal']} (${s['price']})", expanded=True):
                        # Compute signal strengths for radar chart
                        radar_values = {}
                        for d in details:
                            if "error" in d:
                                continue
                            name = d.get("signal", "")
                            try:
                                if name == "rsi":
                                    rsi_val = float(d.get("rsi", 50))
                                    radar_values[name] = round((rsi_val - 50) / 10, 2)
                                elif name == "macd":
                                    hist = float(d.get("histogram", 0))
                                    radar_values[name] = round(hist * 100, 2)
                                elif name == "bollinger":
                                    price = float(d.get("price", 0))
                                    mid = float(d.get("middle_band", price))
                                    up = float(d.get("upper_band", price))
                                    if up != mid:
                                        radar_values[name] = round((price - mid) / (up - mid) * 2, 2)
                                    else:
                                        radar_values[name] = 0.0
                                elif name == "volume_anomaly":
                                    ratio = float(d.get("volume_ratio", 1))
                                    radar_values[name] = round((ratio - 1) * 3, 2)
                                elif name == "ma_cross":
                                    fast = float(d.get("fast_ma", 0))
                                    slow = float(d.get("slow_ma", 1))
                                    radar_values[name] = round((fast - slow) / slow * 100, 2)
                            except (ValueError, TypeError, KeyError):
                                radar_values[name] = 0.0

                        # Layout: charts row + table row
                        chart_cols = st.columns([3, 2])

                        with chart_cols[0]:
                            if radar_values:
                                # Radar chart
                                cats = list(radar_values.keys())
                                vals = list(radar_values.values())
                                cats.append(cats[0])
                                vals.append(vals[0])

                                fig_radar = go.Figure()
                                fig_radar.add_trace(go.Scatterpolar(
                                    r=vals, theta=cats, fill="toself",
                                    name=s["symbol"],
                                    line=dict(color="#00d4aa", width=2),
                                    fillcolor="rgba(0, 212, 170, 0.2)",
                                ))
                                fig_radar.update_layout(
                                    polar=dict(
                                        radialaxis=dict(visible=True, range=[
                                            min(min(vals)-1, -5),
                                            max(max(vals)+1, 5),
                                        ]),
                                        angularaxis=dict(direction="clockwise"),
                                    ),
                                    showlegend=False,
                                    margin=dict(l=60, r=60, t=30, b=30),
                                    height=380,
                                )
                                st.plotly_chart(fig_radar, use_container_width=True)

                        with chart_cols[1]:
                            # Pie chart: BUY/SELL/HOLD distribution
                            action_counts = {}
                            for d in details:
                                if "error" in d:
                                    continue
                                act = d.get("action", "UNKNOWN")
                                action_counts[act] = action_counts.get(act, 0) + 1

                            if action_counts:
                                pie_labels = list(action_counts.keys())
                                pie_values = list(action_counts.values())
                                pie_colors = {
                                    "BUY": "#22c55e", "SELL": "#ef4444",
                                    "HOLD": "#f59e0b", "ALERT": "#3b82f6",
                                    "NORMAL": "#6b7280",
                                }
                                colors = [pie_colors.get(l, "#6b7280") for l in pie_labels]

                                fig_pie = go.Figure(go.Pie(
                                    labels=pie_labels, values=pie_values,
                                    marker=dict(colors=colors),
                                    hole=0.4, textinfo="label+value",
                                    textfont=dict(color="white"),
                                ))
                                fig_pie.update_layout(
                                    showlegend=False,
                                    margin=dict(l=10, r=10, t=30, b=10),
                                    height=300,
                                )
                                fig_pie.add_annotation(
                                    text=s["overall_signal"], x=0.5, y=0.5,
                                    font=dict(size=22, color="white"), showarrow=False,
                                )
                                st.plotly_chart(fig_pie, use_container_width=True)

                        # Detail table
                        detail_rows = []
                        for d in details:
                            d = dict(d)  # copy to avoid mutating original
                            if "error" in d:
                                detail_rows.append({"指标": d["signal"], "结果": "ERROR", "详情": d["error"]})
                            else:
                                action = d.pop("action", "?")
                                name = d.pop("signal", "?")
                                d.pop("date", None)
                                detail_str = " | ".join(f"{k}={v}" for k, v in d.items())
                                detail_rows.append({"指标": name, "结果": action, "详情": detail_str})
                        st.dataframe(pd.DataFrame(detail_rows), use_container_width=True, hide_index=True)
        else:
            st.info("点击右侧「生成信号」按钮开始分析")


# ==================== 策略回测 ====================
elif page == "📈 策略回测":
    st.title("📈 策略回测")

    symbols = load_watchlist()
    col1, col2 = st.columns([3, 1])
    with col2:
        symbol = st.selectbox("选择股票", symbols)
        period = st.selectbox("回测时间", ["6mo", "1y", "2y", "5y"], index=1)
        strategies = st.multiselect(
            "选择策略",
            ["ma_cross", "rsi", "macd", "bollinger"],
            default=["ma_cross", "rsi", "macd"],
        )
        initial_cash = st.number_input("初始资金", value=100000, step=10000)
        if st.button("▶️ 运行回测", use_container_width=True):
            st.session_state.backtest_run = True

    with col1:
        if not getattr(st.session_state, "backtest_run", False):
            st.info("选择股票和策略后点击「运行回测」")
        else:
            df = st.session_state.fetcher.fetch_history(symbol, period=period)
            if df.empty:
                st.error("无法获取数据")
            elif not strategies:
                st.warning("请选择策略")
            else:
                with st.spinner("回测中..."):
                    runner = st.session_state.runner
                    results = []
                    for strat in strategies:
                        r = runner.run(df, strategy_name=strat, cash=initial_cash)
                        results.append(r)

                    # Comparison table
                    comp_df = runner.compare(results)
                    st.subheader("策略对比")
                    st.dataframe(comp_df, use_container_width=True, hide_index=True)

                    # Detailed results
                    for r in results:
                        if "error" in r:
                            continue
                        st.subheader(f"{r['strategy']} 策略")
                        c1, c2, c3, c4, c5 = st.columns(5)
                        c1.metric("总收益", f"{r['total_return_pct']}%")
                        c2.metric("年化收益", f"{r['annual_return_pct']}%")
                        c3.metric("夏普比率", f"{r['sharpe_ratio']}")
                        c4.metric("最大回撤", f"{r['max_drawdown_pct']}%")
                        c5.metric("交易次数", f"{r['total_trades']}")


# ==================== 模拟持仓 ====================
elif page == "💰 模拟持仓":
    st.title("💰 模拟持仓 (Paper Trading)")

    broker = st.session_state.broker

    # Portfolio summary
    summary = broker.get_summary()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("总资产", f"${summary['total_value']:,.2f}")
    c2.metric("可用现金", f"${summary['cash']:,.2f}")
    c3.metric("持仓市值", f"${summary['positions_value']:,.2f}")
    c4.metric("总盈亏", f"${summary['total_pnl']:,.2f}", delta=f"{(summary['total_pnl']/summary['initial_cash']*100):.2f}%")

    st.divider()

    # Place order
    st.subheader("下单")
    symbols = load_watchlist()
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        order_symbol = st.selectbox("股票", symbols, key="order_sym")
    with col2:
        order_side = st.selectbox("方向", ["买入", "卖出"])
    with col3:
        order_qty = st.number_input("数量", min_value=1, value=10)
    with col4:
        order_price = st.number_input("价格 ($)", min_value=0.01, value=100.0, step=1.0)
    with col5:
        st.write("")  # spacing
        if st.button("提交订单", use_container_width=True):
            side = OrderSide.BUY if order_side == "买入" else OrderSide.SELL
            order = broker.place_order(order_symbol, side, order_qty, order_price)
            if order.status.value == "filled":
                st.success(f"成交: {order_side} {order_qty} 股 {order_symbol} @ ${order_price}")
            elif order.status.value == "rejected":
                st.error("订单被拒绝（资金不足或持仓不够）")
            else:
                st.warning(f"订单状态: {order.status.value}")

    # Current positions
    st.subheader("当前持仓")
    positions = broker.get_positions()
    if positions:
        pos_rows = []
        for p in positions:
            pnl_pct = ((p.current_price - p.avg_price) / p.avg_price * 100) if p.avg_price else 0
            pos_rows.append({
                "股票": p.symbol,
                "数量": p.qty,
                "均价": f"${p.avg_price:.2f}",
                "现价": f"${p.current_price:.2f}",
                "市值": f"${p.market_value:,.2f}",
                "盈亏": f"${p.unrealized_pnl:,.2f}",
                "盈亏%": f"{pnl_pct:.2f}%",
            })
        st.dataframe(pd.DataFrame(pos_rows), use_container_width=True, hide_index=True)
    else:
        st.info("暂无持仓")

    # Order history
    st.subheader("历史订单")
    if broker.orders:
        order_rows = []
        for o in broker.orders:
            order_rows.append({
                "ID": o.order_id,
                "时间": o.timestamp.strftime("%Y-%m-%d %H:%M"),
                "股票": o.symbol,
                "方向": o.side.value,
                "数量": o.qty,
                "价格": f"${o.filled_price:.2f}" if o.filled_price else "-",
                "状态": o.status.value,
            })
        st.dataframe(pd.DataFrame(order_rows), use_container_width=True, hide_index=True)
    else:
        st.info("暂无订单")


# ==================== 自选股管理 ====================
elif page == "📋 自选股管理":
    st.title("📋 自选股管理")

    fetcher = st.session_state.fetcher

    # Add symbol
    col1, col2 = st.columns([3, 1])
    with col1:
        new_sym = st.text_input("添加股票代码", placeholder="如 AAPL, MSFT, NVDA...")
    with col2:
        st.write("")
        if st.button("➕ 添加", use_container_width=True):
            if new_sym.strip():
                sym = new_sym.strip().upper()
                fetcher.cache.add_to_watchlist(sym)
                st.success(f"已添加 {sym}")
                st.rerun()

    # Current watchlist
    wl = fetcher.cache.get_watchlist()
    if wl:
        rows = []
        for item in wl:
            rows.append({
                "股票": item["symbol"],
                "添加时间": item["added_at"][:10] if item["added_at"] else "",
                "备注": item["note"] or "",
            })
        df_wl = pd.DataFrame(rows)
        st.dataframe(df_wl, use_container_width=True, hide_index=True)

        # Remove
        st.divider()
        remove_sym = st.selectbox("选择要删除的股票", [item["symbol"] for item in wl])
        if st.button("🗑️ 删除", use_container_width=True):
            fetcher.cache.remove_from_watchlist(remove_sym)
            st.success(f"已删除 {remove_sym}")
            st.rerun()
    else:
        st.info("自选股为空，添加股票代码开始监控")
