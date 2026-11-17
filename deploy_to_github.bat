@echo off
title Push Code to GitHub (For Render.com Deploy)
cd /d "%~dp0"
echo ========================================================
echo       Push 2D Studio to GitHub (For Render.com)
echo ========================================================
echo.
echo Step 1: github.com/new par jaakar ek new empty repo banayein:
echo   - Repository name: (e.g. viral-2d-studio)
echo   - Visibility: Public ya Private
echo.
set /p REPO_URL="Enter your GitHub Repo URL (e.g. https://github.com/USERNAME/REPO): "

if "%REPO_URL%"=="" (
    echo Error: URL cannot be empty!
    pause
    exit /b
)

echo.
echo [1/2] Preparing files...
git init
git branch -M main
git add .
git commit -m "Deploy 2D Explainer Studio"

echo.
echo [2/2] Pushing to GitHub...
git remote remove origin 2>nul
git remote add origin %REPO_URL%
git push -u origin main --force

if %errorlevel% equ 0 (
    echo.
    echo ========================================================
    echo  SUCCESS! Code pushed to GitHub!
    echo ========================================================
    echo.
    echo Ab Render.com par deploy karne ke liye:
    echo 1. https://dashboard.render.com kholein
    echo 2. "New +" -^> "Web Service" click karein
    echo 3. Apna yeh GitHub repo select karein
    echo 4. Render automatically Dockerfile detect karke deploy kar dega!
    echo ========================================================
) else (
    echo.
    echo [ERROR] Push failed! Check your repo URL or GitHub login.
)

pause
