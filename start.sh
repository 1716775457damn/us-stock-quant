#!/usr/bin/env bash
# us-stock-quant 一键启动脚本
cd "$(dirname "$0")"

VENV_DIR="venv"
if [ -d "$VENV_DIR" ]; then
    PYTHON="$VENV_DIR/bin/python3"
    PIP="$VENV_DIR/bin/pip3"
else
    PYTHON="python3"
    PIP="pip3"
fi

echo "[setup] 检测依赖..."
if ! $PYTHON -c "import yfinance, backtrader, streamlit" 2>/dev/null; then
    echo "[setup] 安装依赖..."
    $PIP install --break-system-packages -r requirements.txt -q 2>&1 ||
    $PIP install -r requirements.txt -q 2>&1
    if [ $? -ne 0 ]; then
        echo "[setup] 安装失败，请手动执行: pip install -r requirements.txt"
        exit 1
    fi
fi

CACHE_FILE="data/cache/stock_data.db"
if [ "$1" = "--refresh" ]; then
    echo "[data] 清除缓存，重新抓取..."
    rm -f "$CACHE_FILE"
fi

if [ ! -f "$CACHE_FILE" ]; then
    echo "[data] 首次启动，抓取默认自选股数据..."
    $PYTHON main.py fetch AAPL MSFT GOOGL AMZN NVDA TSLA META
    echo "[data] 数据就绪"
fi

echo ""
echo "[dashboard] 启动 Streamlit 监控面板..."
echo "          地址: http://localhost:8501"
echo "          按 Ctrl+C 停止"
echo ""
$PYTHON -m streamlit run dashboard/app.py --server.port 8501
