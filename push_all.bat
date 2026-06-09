@echo off
echo Resetting local commits to match remote (origin/main) to clean history...
git reset origin/main

echo Cleaning up duplicate files and folders from the root directory...
del /q app.py >nul 2>&1
del /q TEST.PY >nul 2>&1
del /q file_router.py >nul 2>&1
del /q gaia_client.py >nul 2>&1
del /q gaia_progress.json >nul 2>&1
del /q gaia_run_log.txt >nul 2>&1
del /q gaia_runner.py >nul 2>&1
del /q gemma_server.py >nul 2>&1
del /q push_space.ps1 >nul 2>&1
del /q quick_test.py >nul 2>&1
del /q requirements.txt >nul 2>&1
del /q retriever.py >nul 2>&1
del /q run_ollama.ps1 >nul 2>&1
del /q skills-lock.json >nul 2>&1
del /q supabase_client.py >nul 2>&1
del /q supabase_gaia.py >nul 2>&1
del /q test_gaia.py >nul 2>&1
del /q tools.py >nul 2>&1
del /q train-00000-of-00001.parquet >nul 2>&1
del /q prompts.yaml >nul 2>&1
del /q LANGFUSE_SETUP.md >nul 2>&1

rd /s /q downloads >nul 2>&1
rd /s /q test_data >nul 2>&1
rd /s /q scripts >nul 2>&1
rd /s /q hf_space >nul 2>&1
rd /s /q hf_space_repo >nul 2>&1
rd /s /q temp_langfuse_skills >nul 2>&1

echo Unstaging all files to ensure .gitignore is fully respected...
git rm -r --cached . >nul 2>&1

echo Re-adding all files (excluding .venv, secrets, and temp folders)...
git add .

echo Committing clean files with the new layout...
git commit -m "Clean up repository layout and add all projects"

echo Pushing to GitHub...
git push origin main

echo Done! Folder is now clean and pushed.
pause
