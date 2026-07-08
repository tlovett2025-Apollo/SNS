@echo off
title SNS Git Helper

echo.
echo ============================
echo      STOCK & STIR GIT
echo ============================
echo.

git status

echo.
set /p MSG=Commit message: 

echo.
git add .

git commit -m "%MSG%"

if errorlevel 1 (
    echo.
    echo Commit failed.
    pause
    exit /b
)

echo.
git push

echo.
echo ============================
echo Finished!
echo ============================
echo.

git status

pause