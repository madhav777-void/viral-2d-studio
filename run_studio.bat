@echo off
title Faceless AI Video Studio
cd /d "%~dp0"
echo ======================================================
echo    Starting Faceless AI Video Studio
echo ======================================================
echo.
echo Opening in your browser...
start http://localhost:8000
echo.
set OMNI_HOME=%~dp0.omni-shorts
set PYTHONPATH=%~dp0studio;%PYTHONPATH%
".omni-shorts\venv\Scripts\python.exe" -m uvicorn server:app --app-dir studio --host 0.0.0.0 --port 8000
pause
