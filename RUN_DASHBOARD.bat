@echo off
title Dashboard Vung Ken V6.6
cd /d "%~dp0"
start "" http://localhost:8000/index.html?v=66
python -m http.server 8000
pause
