@echo off
title SNS Good Night Check


echo.
echo ===== SNS GOOD NIGHT =====
echo.

echo --- Git status ---
git status

echo.
echo --- Changed files ---
git diff --name-only

echo.
echo --- Reminder ---
echo If the build works, commit with:
echo git add .
echo git commit -m "YOUR MESSAGE HERE"
echo git push

echo.
echo Good night check complete.
pause