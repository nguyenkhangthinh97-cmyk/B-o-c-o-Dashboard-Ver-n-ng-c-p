@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo =============================================
echo   UPDATE WEATHER - DASHBOARD VUNG KEN V6.6
echo =============================================
echo.
where python >nul 2>nul
if %errorlevel%==0 (
  python update_weather.py
) else (
  py update_weather.py
)
echo.
echo Neu thanh cong, file data\weather_forecast.json da duoc cap nhat.
echo Sau do upload/commit file nay len GitHub de QLCH xem duoc weather moi.
pause
