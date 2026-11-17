@echo off
title 2D Viral Video Studio - Local Engine
cd /d "%~dp0"

echo ======================================================
echo       2D Viral Video Studio (Full Local Power)
echo       Uses your laptop's GPU, CPU ^& RAM directly!
echo ======================================================
echo.

:: 1. Check Python installation
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH!
    echo Please install Python 3.10, 3.11, or 3.12 from https://www.python.org/downloads/
    echo Make sure to CHECK the box: "Add python.exe to PATH"
    pause
    exit /b 1
)

:: 2. Find or Create Virtual Environment
set VENV_PYTHON=
if exist "%~dp0.omni-shorts\venv\Scripts\python.exe" (
    set VENV_PYTHON="%~dp0.omni-shorts\venv\Scripts\python.exe"
) else if exist "%~dp0venv\Scripts\python.exe" (
    set VENV_PYTHON="%~dp0venv\Scripts\python.exe"
) else (
    echo [Setup] Creating fresh Python virtual environment (venv)...
    python -m venv venv
    set VENV_PYTHON="%~dp0venv\Scripts\python.exe"
    echo [Setup] Installing dependencies (FastAPI, Skia 2D, ONNX, Kokoro)...
    %VENV_PYTHON% -m pip install --upgrade pip
    %VENV_PYTHON% -m pip install -r requirements.txt
    echo [Setup] Virtual environment ready!
)

:: 3. Check Kokoro TTS Voice models
set OMNI_HOME=%~dp0.omni-shorts
if not exist "%OMNI_HOME%\kokoro\kokoro-v1.0.onnx" (
    echo [Setup] Downloading Kokoro AI voice models (one-time setup)...
    %VENV_PYTHON% -c "import urllib.request, os; os.makedirs(r'%OMNI_HOME%\kokoro', exist_ok=True); urllib.request.urlretrieve('https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx', r'%OMNI_HOME%\kokoro\kokoro-v1.0.onnx'); urllib.request.urlretrieve('https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin', r'%OMNI_HOME%\kokoro\voices-v1.0.bin'); print('Kokoro models downloaded successfully!')"
)

:: 4. Set Environment Variables
set PYTHONPATH=%~dp0studio;%~dp0cinematic-skill\skills\cinematic-film\scripts;%PYTHONPATH%

echo.
echo ======================================================
echo    Studio is starting on: http://localhost:8000
echo ======================================================
echo.

:: 5. Open browser automatically
start http://localhost:8000

:: 6. Launch Uvicorn Server
%VENV_PYTHON% -m uvicorn server:app --app-dir studio --host 0.0.0.0 --port 8000

pause
