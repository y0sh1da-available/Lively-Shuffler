@echo off
title Building Lively Wallpaper Shuffler
echo ========================================================
echo   Building Lively Wallpaper Shuffler Standalone EXE
echo ========================================================
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH!
    pause
    exit /b 1
)

python build.py
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Build failed! Check the output above.
    pause
    exit /b %errorlevel%
)

echo.
echo ========================================================
echo   Build Complete! Output located in dist/
echo ========================================================
pause
