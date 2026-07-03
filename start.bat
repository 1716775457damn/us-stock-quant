@echo off
echo === us-stock-quant 启动 ===
wsl -e bash -c "cd /mnt/d/us-stock-quant && bash start.sh %*"
if errorlevel 1 goto :error
goto :end

:error
echo 启动失败，请确认 WSL 已安装
echo 在 PowerShell 运行: wsl --install
pause

:end
