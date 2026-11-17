@echo off
title Build Standalone APK
cd /d "%~dp0"
echo ========================================================
echo    Building Standalone Android APK (Capacitor)
echo ========================================================
echo.
echo Installing Capacitor dependencies...
call npm install
echo.
echo Syncing web assets...
call npx cap sync android
echo.
echo Opening Android Studio to compile APK...
call npx cap open android
echo.
echo APK will be created inside android/app/build/outputs/apk/
pause
