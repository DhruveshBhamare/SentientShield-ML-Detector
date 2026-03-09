@echo off
echo ========================================================
echo      SentientShield GitHub Pusher
echo ========================================================
echo.
echo 1. Go to https://github.com/new
echo 2. Create a repository named 'SentientShield-ML-Detector'
echo 3. DO NOT check "Initialize with README", .gitignore, or License.
echo 4. Copy the HTTPS URL (e.g., https://github.com/yourname/repo.git)
echo.
set /p repo_url="Paste your GitHub Repository URL here: "

if "%repo_url%"=="" goto error

echo.
echo Adding remote origin...
git remote add origin %repo_url%

echo.
echo Renaming branch to main...
git branch -M main

echo.
echo Pushing code to GitHub...
git push -u origin main

echo.
echo ========================================================
echo      Done! Your code is now on GitHub.
echo ========================================================
pause
exit

:error
echo Error: No URL provided. Exiting.
pause
