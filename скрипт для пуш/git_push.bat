@echo off
chcp 65001 >nul
REM ── AI Analyzer — Git Push Script ──
REM Вставь свой токен GitHub вместо YOUR_TOKEN_HERE

set REPO_URL=https://YOUR_TOKEN_HERE@github.com/VVASILEVSS/AI-Analyzer-Plan.git
set BRANCH=main

cd /d "%~dp0"
cd D:\PROJECTS\AI_Analyzer

echo.
echo  === AI Analyzer — Git Push ===
echo.

REM Проверяем изменения
git status --short
echo.

set /p MSG="Коммит сообщение: "
if "%MSG%"=="" set MSG=update: auto-push

git add -A
git commit -m "%MSG%"
git push %REPO_URL% %BRANCH%

echo.
echo  Готово!
pause
