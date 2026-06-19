@echo off
:: GVN Master AI - One-Click Git Push Script

set msg=%~1
if "%msg%"=="" (
    set /p msg="Enter Commit Message: "
)
if "%msg%"=="" (
    set msg="GVN Master Update"
)

echo.
echo [1/3] Adding all changes...
git add .

echo.
echo [2/3] Committing changes...
git commit -m "%msg%"

echo.
echo [3/3] Pushing to GitHub (main branch)...
git push origin main

echo.
echo ==========================================
echo ✅ Successfully Pushed to GitHub!
echo ==========================================
pause
