@echo off
cd /d "%~dp0"
py -3.12 -m venv .venv
if errorlevel 1 goto :failed
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto :failed
.venv\Scripts\python.exe setup_model.py
if errorlevel 1 goto :failed
echo Setup complete. No training is required.
pause
exit /b 0
:failed
echo Setup failed. Install Python 3.12 64-bit, or check the message above.
pause
exit /b 1
