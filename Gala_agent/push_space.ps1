# Push hf_space updates to jklkdkfl/Final_Assignment_Template
# Requires HUGGINGFACEHUB_API_TOKEN with WRITE access in .env
# Create one at: https://huggingface.co/settings/tokens (role: Write)

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$repo = Join-Path $root "hf_space_repo"

if (-not (Test-Path $repo)) {
    Write-Host "Cloning Space repo..." -ForegroundColor Cyan
    git clone https://huggingface.co/spaces/jklkdkfl/Final_Assignment_Template $repo
}

Copy-Item -Force (Join-Path $root "hf_space\app.py") (Join-Path $repo "app.py")
Copy-Item -Force (Join-Path $root "hf_space\requirements.txt") (Join-Path $repo "requirements.txt")

$readme = @"
---
title: GAIA Agent — Gala Agent
emoji: 🎩
colorFrom: indigo
colorTo: blue
sdk: gradio
sdk_version: 5.25.2
app_file: app.py
pinned: false
hf_oauth: true
hf_oauth_expiration_minutes: 480
---

# GAIA Agent — submission UI (full agent runs locally)
"@

Set-Content -Path (Join-Path $repo "README.md") -Value $readme -Encoding UTF8

$tokenLine = Get-Content (Join-Path $root ".env") | Where-Object { $_ -match '^HUGGINGFACEHUB_API_TOKEN=' }
$token = $tokenLine -replace '^HUGGINGFACEHUB_API_TOKEN=',''

if (-not $token) {
    Write-Host "Set HUGGINGFACEHUB_API_TOKEN in .env (Write token required)" -ForegroundColor Red
    exit 1
}

$env:HF_TOKEN = $token
Push-Location $repo
git add app.py requirements.txt README.md
git diff --cached --quiet
if ($LASTEXITCODE -ne 0) {
    git commit -m "Deploy lightweight GAIA submission UI for local agent workflow"
}
git push "https://jklkdkfl:${token}@huggingface.co/spaces/jklkdkfl/Final_Assignment_Template" main
$code = $LASTEXITCODE
Pop-Location

if ($code -eq 0) {
    Write-Host "Pushed! Space: https://huggingface.co/spaces/jklkdkfl/Final_Assignment_Template" -ForegroundColor Green
} else {
    Write-Host "Push failed. Use a Write token: https://huggingface.co/settings/tokens" -ForegroundColor Red
    exit $code
}
