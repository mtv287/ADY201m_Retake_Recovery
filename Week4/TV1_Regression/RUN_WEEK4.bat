@echo off
cd /d "%~dp0"
py -m pip install -r "..\requirements.txt"
if errorlevel 1 goto :error
py TV1_Regression_Master.py
if errorlevel 1 goto :error
echo.
echo Week 4 completed successfully.
pause
exit /b 0
:error
echo.
echo Week 4 failed. Read the error above. Make sure VS Code uses the same Python interpreter.
pause
exit /b 1
