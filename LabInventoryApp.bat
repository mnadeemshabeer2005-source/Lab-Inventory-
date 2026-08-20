@echo off
REM Move to the folder of this script
cd /d %~dp0

REM Activate virtual environment
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
)

REM Open browser automatically
start "" "http://10.99.149.3:5000"

REM Run the Flask app
python app.py

pause
