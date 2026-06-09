@echo off
echo Resetting local commits to match remote (origin/main) to clean history...
git reset origin/main

echo Unstaging all files to ensure .gitignore is fully respected...
git rm -r --cached . >nul 2>&1

echo Re-adding all files (excluding .venv, secrets, and temp folders)...
git add .

echo Committing clean files...
git commit -m "Add Gatekeeper, Vision React agents, and root project files"

echo Pushing to GitHub...
git push origin main

echo Done!
pause
