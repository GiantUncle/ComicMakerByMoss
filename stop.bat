@echo off
chcp 65001 >nul
setlocal
title ComicMaker stop
echo Stopping ComicMaker servers (ports 8000 / 5173)...

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ports=8000,5173; $pids=Get-NetTCPConnection -LocalPort $ports -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique; if(-not $pids){ Write-Host '  already free'; exit }; foreach($p in $pids){ try { Stop-Process -Id $p -Force -ErrorAction Stop; Write-Host ('  stopped pid ' + $p) } catch { Write-Host ('  failed pid ' + $p) } }"

echo Done.
timeout /t 2 /nobreak >nul
