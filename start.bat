@echo off
chcp 65001 >nul
echo [setup] 通过 WSL 启动...

wsl -e bash -c "cd /mnt/d/us-stock-quant && bash start.sh %*"

if %errorlevel% neq 0 (
    echo [ERROR] 启动失败，确认 WSL 已安装
    pause
)
