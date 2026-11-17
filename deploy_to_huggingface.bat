@echo off
title Deploy to Hugging Face Spaces (2D Explainer Studio)
cd /d "%~dp0"
echo ========================================================
echo       Deploy 2D Explainer Studio to Hugging Face
echo           (Free 16GB RAM + 24/7 Always Online)
echo ========================================================
echo.
echo Step 1: https://huggingface.co/new-space par jaakar Space banayein:
echo   - Space Name: (e.g. viral-2d-studio)
echo   - Space SDK: GRADIO  ^<-- IMPORTANT: Gradio choose karein (100%% FREE, Koi Card/Premium nahi maangega!)
echo   - Hardware: Free (CPU basic 2vCPU - 16GB RAM)
echo.
echo Step 2: Hugging Face Token (Write Permission):
echo   - https://huggingface.co/settings/tokens se 'WRITE' token banayein
echo.
echo ========================================================
echo.
set /p HF_USERNAME="1. Enter your Hugging Face Username: "
set /p HF_SPACENAME="2. Enter your Space Name (e.g. viral-2d-studio): "
set /p HF_TOKEN="3. Enter your Hugging Face Token (starts with hf_...): "

if "%HF_USERNAME%"=="" (
    echo Error: Username cannot be empty!
    pause
    exit /b
)
if "%HF_SPACENAME%"=="" (
    echo Error: Space name cannot be empty!
    pause
    exit /b
)

echo.
echo [1/3] Adding all updated 2D Explainer & Skia files to Git...
git init
git branch -M main
git add .
git commit -m "Deploy 2D Explainer Studio with Skia, Kokoro & Aesthetic Cards"

echo.
echo [2/3] Setting remote Hugging Face repository...
git remote remove space 2>nul

if "%HF_TOKEN%"=="" (
    git remote add space https://huggingface.co/spaces/%HF_USERNAME%/%HF_SPACENAME%
) else (
    git remote add space https://%HF_USERNAME%:%HF_TOKEN%@huggingface.co/spaces/%HF_USERNAME%/%HF_SPACENAME%
)

echo.
echo [3/3] Uploading code to Hugging Face Spaces...
git push -u space main --force

if %errorlevel% equ 0 (
    echo.
    echo ========================================================
    echo  SUCCESS! Files successfully uploaded to Hugging Face!
    echo ========================================================
    echo.
    echo Aapka Space build hona shuru ho gaya hai!
    echo 2-3 minute mein build complete hokar aapka server live hoga:
    echo.
    echo Dashboard URL: https://huggingface.co/spaces/%HF_USERNAME%/%HF_SPACENAME%
    echo Direct Web App: https://%HF_USERNAME%-%HF_SPACENAME%.hf.space
    echo.
    echo Laptop band bhi rahega tab bhi video 24/7 banegi!
    echo ========================================================
) else (
    echo.
    echo [ERROR] Push failed! Please check your username, space name or token.
)

pause
