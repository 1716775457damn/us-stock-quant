#!/usr/bin/env bash
# us-stock-quant 一键启动脚本
set -e

cd "$(dirname "$0")"

VENV_DIR="venv"
if [ -d "$VENV_DIR" ]; then
    PYTHON="$VENV_DIR/bin/python3"
    PIP="$VENV_DIR/bin/pip"
else
    PYTHON="python3"
    PIP="pip3"
fi

# 检查依赖
if ! $PYTHON -c "import yfinance, backtrader, streamlit" 2>/dev/null; then
    echo "[setup] 安装依赖..."
    $PIP install --break-system-packages -r requirements.txt -q 2>/dev/null || $PIP install -r requirements.txt -q
fi

# 清理旧数据缓存（可选，注释可跳过）
CACHE_FILE="data/cache/stock_data.db"
if [ "$1" = "--refresh" ]; then
    echo "[data] 清除缓存，重新抓取..."
    rm -f "$CACHE_FILE"
fi

# 抓取默认自选股数据
if [ ! -f "$CACHE_FILE" ]; then
    echo "[data] 首次启动，抓取默认自选股数据..."
    $PYTHON main.py fetch AAPL MSFT GOOGL AMZN NVDA TSLA META 2>&1
    echo "[data] 数据就绪"
fi

# 启动面板
echo "[dashboard] 启动 Streamlit 监控面板..."
echo "          浏览器打开 http://localhost:8501"
$PYTHON -m streamlit run dashboard/app.py --server.headless true --server.port 8501
