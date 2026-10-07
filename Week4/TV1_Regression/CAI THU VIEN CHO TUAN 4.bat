@echo off
cd /d "%~dp0"
echo ==============================================
echo Installing Week 4 Python requirements...
echo ==============================================
py -m pip install --upgrade pip
py -m pip install -r "..\requirements.txt"
echo.
echo Done. In VS Code, select the same Python interpreter/kernel, then Restart Kernel and Run All.
pause
