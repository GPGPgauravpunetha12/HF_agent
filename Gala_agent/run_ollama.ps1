# Run GAIA agent with local Ollama (no cloud API credits needed)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$env:PYTHONPATH = $PSScriptRoot
$env:PYTHONIOENCODING = "utf-8"
$env:LLM_PROVIDER = "ollama"
$env:OLLAMA_MODEL_NAME = if ($env:OLLAMA_MODEL_NAME) { $env:OLLAMA_MODEL_NAME } else { "llama3.1:latest" }
$env:OLLAMA_BASE_URL = if ($env:OLLAMA_BASE_URL) { $env:OLLAMA_BASE_URL } else { "http://127.0.0.1:11434" }

Write-Host "Checking Ollama..." -ForegroundColor Cyan
ollama list | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Ollama is not running. Start the Ollama app, then retry." -ForegroundColor Red
    exit 1
}

Write-Host "Model: $env:OLLAMA_MODEL_NAME" -ForegroundColor Green
python gaia_runner.py @args
