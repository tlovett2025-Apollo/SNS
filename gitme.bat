@echo off
title GitMe - SNS

echo.
echo ============================
echo      STOCK ^& STIR GIT
echo ============================
echo.

git status

echo.
echo This will stage ALL changed files.
echo Press Ctrl+C now if you do not want that.
echo.
pause

echo.
set /p MSG=Enter COMMIT MESSAGE, not a git command: 

if "%MSG%"=="" (
    echo.
    echo Commit message cannot be blank.
    pause
    exit /b
)

echo.
git add .

git commit -m "%MSG%"

if errorlevel 1 (
    echo.
    echo Commit failed. Nothing was pushed.
    pause
    exit /b
)

echo.
git push

if errorlevel 1 (
    echo.
    echo Push failed.
    pause
    exit /b
)

echo.
echo ============================
echo You are officially gitted.
echo ============================
echo.

git status

pause