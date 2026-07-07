@echo off
setlocal enabledelayedexpansion

REM ==========================================================
REM Stock & Stir Release Loader
REM Purpose:
REM   1. Back up current project files and data.
REM   2. Create a clean staging point for a new release.
REM   3. Prevent accidental loss of sns.db or project files.
REM
REM Usage:
REM   Put this file in your Stock & Stir project folder.
REM   Double-click it BEFORE copying in a new release.
REM ==========================================================

set "PROJECT_DIR=%~dp0"
cd /d "%PROJECT_DIR%"

for /f "tokens=1-4 delims=/ " %%a in ("%date%") do (
    set "MM=%%a"
    set "DD=%%b"
    set "YYYY=%%c"
)

for /f "tokens=1-3 delims=:." %%a in ("%time%") do (
    set "HH=%%a"
    set "MIN=%%b"
    set "SEC=%%c"
)

set "HH=%HH: =0%"
set "BACKUP_NAME=backup_%YYYY%-%MM%-%DD%_%HH%%MIN%%SEC%"
set "BACKUP_DIR=%PROJECT_DIR%backups\%BACKUP_NAME%"

echo.
echo ==========================================================
echo Stock ^& Stir Release Backup
echo ==========================================================
echo Project folder:
echo %PROJECT_DIR%
echo.
echo Backup folder:
echo %BACKUP_DIR%
echo.

mkdir "%BACKUP_DIR%"

REM Back up Python/config/database/documentation files.
echo Backing up project files...
for %%F in (*.py *.db *.sqlite *.sqlite3 *.md *.txt *.bat *.csv *.json) do (
    if exist "%%F" copy "%%F" "%BACKUP_DIR%\" >nul
)

REM Back up common data folders if they exist.
if exist "data" (
    echo Backing up data folder...
    xcopy "data" "%BACKUP_DIR%\data\" /E /I /Y >nul
)

if exist "docs" (
    echo Backing up docs folder...
    xcopy "docs" "%BACKUP_DIR%\docs\" /E /I /Y >nul
)

if exist "exports" (
    echo Backing up exports folder...
    xcopy "exports" "%BACKUP_DIR%\exports\" /E /I /Y >nul
)

REM Make a fresh incoming release folder.
if exist "incoming_release" (
    echo Removing old incoming_release folder...
    rmdir /S /Q "incoming_release"
)

mkdir "incoming_release"

echo.
echo Backup complete.
echo.
echo NEXT STEPS:
echo   1. Unzip the new release into:
echo      %PROJECT_DIR%incoming_release
echo.
echo   2. Review the files.
echo.
echo   3. Copy the new release files from incoming_release into this folder.
echo.
echo   4. Run:
echo      python -m streamlit run app.py
echo.
echo Your old files and database are saved in:
echo %BACKUP_DIR%
echo.
pause
