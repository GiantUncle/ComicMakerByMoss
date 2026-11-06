@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
title ComicMaker

echo ============================================================
echo   ComicMaker  -  MOSS-Image prompt workbench
echo ============================================================
echo.

where python >nul 2>nul
if errorlevel 1 (
  echo [X] Python not found on PATH. Install Python 3.10+ and retry.
  echo.
  pause
  exit /b 1
)
where node >nul 2>nul
if errorlevel 1 (
  echo [X] Node.js not found on PATH. Install Node 18+ and retry.
  echo.
  pause
  exit /b 1
)

echo [1/5] backend dependencies...
python -c "import fastapi, uvicorn, httpx" >nul 2>nul
if errorlevel 1 (
  python -m pip install -r "app\backend\requirements.txt"
)

echo [2/5] frontend dependencies...
if not exist "app\frontend\node_modules" (
  echo       first run - installing, this takes a minute...
  pushd "app\frontend"
  call npm install --no-fund --no-audit
  popd
) else (
  echo       already installed
)

echo [3/5] freeing ports 8000 / 5173 (avoid duplicate servers)...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-NetTCPConnection -LocalPort 8000,5173 -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object { try { Stop-Process -Id $_ -Force -ErrorAction Stop; Write-Host ('      stopped pid ' + $_) } catch {} }"
timeout /t 1 /nobreak >nul

echo [4/5] starting servers in this window...
start "backend"  /b /D "%~dp0app\backend"  cmd /c "python -m uvicorn app.main:app --port 8000"
start "frontend" /b /D "%~dp0app\frontend" cmd /c "npm run dev"

echo [5/5] waiting for the UI to answer...
set /a tries=0
:wait
timeout /t 2 /nobreak >nul
curl -s -o nul http://localhost:5173 >nul 2>nul
if not errorlevel 1 goto ready
set /a tries+=1
if %tries% lss 60 goto wait
echo       the UI did not answer in time - opening anyway
:ready

start "" "http://localhost:5173"

echo.
echo   Frontend : http://localhost:5173
echo   Backend  : http://localhost:8000/docs
echo.
echo   Both servers run in THIS one window.
echo   Close this window to stop them, or double-click stop.bat.
echo.
pause >nul
