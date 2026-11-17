@echo off
title Faceless AI Video Studio - Worldwide Online Tunnel
cd /d "%~dp0"
echo ====================================================================
echo      Faceless AI Video Studio - Worldwide Online Live (Cloudflare)
echo ====================================================================
echo.
echo Starting Local Engine Server...
set OMNI_HOME=%~dp0.omni-shorts
set PYTHONPATH=%~dp0studio;%PYTHONPATH%
start "Studio Engine" /min ".omni-shorts\venv\Scripts\python.exe" -m uvicorn server:app --app-dir studio --host 0.0.0.0 --port 8000

timeout /t 2 /nobreak >nul

echo.
echo ====================================================================
echo Generating Free Global HTTPS URL (Worldwide Access)...
echo Niche diye gaye link ko copy karke kisi bhi phone ya browser par kholein:
echo ====================================================================
echo.

cloudflared.exe tunnel --url http://localhost:8000

pause
