<#>
.SYNOPSIS
    WatchNext local development launcher.
    Creates a virtual environment, installs dependencies, and starts both backend and frontend.

.DESCRIPTION
    This script sets up a clean .venv in the repo root, installs requirements.txt,
    copies .env.example to .env if missing, then starts:
      - FastAPI backend on http://127.0.0.1:8000 (uvicorn)
      - Streamlit frontend on http://localhost:8501
    It waits for /health to return OK before printing the live URLs.

.USAGE
    .\run_local.ps1
#>

param(
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Definition
$VenvDir = Join-Path $RepoRoot ".venv"
$ReqFile = Join-Path $RepoRoot "requirements.txt"
$EnvExample = Join-Path $RepoRoot ".env.example"
$EnvFile = Join-Path $RepoRoot ".env"

Write-Host "=== WatchNext Local Launcher ===" -ForegroundColor Cyan
Write-Host "Repo: $RepoRoot" -ForegroundColor Gray

# 1. Create virtual environment if missing
if (-not (Test-Path $VenvDir)) {
    Write-Host "Creating virtual environment in .venv..." -ForegroundColor Yellow
    python -m venv $VenvDir
} else {
    Write-Host "Virtual environment already exists." -ForegroundColor Gray
}

# 2. Activate and install dependencies
$Py = Join-Path $VenvDir "Scripts" "python.exe"
$Pip = Join-Path $VenvDir "Scripts" "pip.exe"
Write-Host "Installing dependencies from requirements.txt..." -ForegroundColor Yellow
& $Pip install --quiet --upgrade pip
& $Pip install --quiet -r $ReqFile

# 3. Copy .env.example to .env if missing
if (-not (Test-Path $EnvFile)) {
    Write-Host "Creating .env from .env.example..." -ForegroundColor Yellow
    Copy-Item $EnvExample $EnvFile
} else {
    Write-Host ".env already exists." -ForegroundColor Gray
}

# 4. Start backend (uvicorn) as background job
Write-Host "Starting backend on http://127.0.0.1:8000..." -ForegroundColor Yellow
$backendJob = Start-Job -WorkingDirectory $RepoRoot -ScriptBlock {
    param($Py)
    & $Py -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
} -ArgumentList $Py

# Give backend a moment to start
Start-Sleep -Seconds 3

# 5. Wait for /health to return OK (max 60s)
Write-Host "Waiting for backend health check..." -ForegroundColor Yellow
$healthOk = $false
for ($i = 0; $i -lt 30; $i++) {
    try {
        $resp = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -Method Get -ErrorAction Stop
        if ($resp.model_ready -eq $true -or $resp.status -eq "ok") {
            $healthOk = $true
            break
        }
    } catch { }
    Start-Sleep -Seconds 2
}

if (-not $healthOk) {
    Write-Host "ERROR: Backend did not become healthy within 60 seconds." -ForegroundColor Red
    Write-Host "Check the backend job output with: Receive-Job -Id $($backendJob.Id)" -ForegroundColor Gray
    exit 1
}

Write-Host "Backend is healthy!" -ForegroundColor Green

# 6. Start Streamlit frontend
Write-Host "Starting frontend on http://localhost:8501..." -ForegroundColor Yellow
$frontendJob = Start-Job -WorkingDirectory $RepoRoot -ScriptBlock {
    param($Py)
    & $Py -m streamlit run frontend/app.py --server.port 8501 --server.headless true
} -ArgumentList $Py

# Give Streamlit a moment to start
Start-Sleep -Seconds 5

# 7. Print live URLs
Write-Host ""
Write-Host "=== WatchNext is running ===" -ForegroundColor Cyan
Write-Host "Frontend (open this):  http://localhost:8501" -ForegroundColor Green
Write-Host "Backend API docs:      http://127.0.0.1:8000/docs" -ForegroundColor Green
Write-Host "Backend health:        http://127.0.0.1:8000/health" -ForegroundColor Green
Write-Host ""
Write-Host "Backend job ID:  $($backendJob.Id)" -ForegroundColor Gray
Write-Host "Frontend job ID: $($frontendJob.Id)" -ForegroundColor Gray
Write-Host ""
Write-Host "To stop both servers:" -ForegroundColor Yellow
Write-Host "  Stop-Job -Id $($backendJob.Id), $($frontendJob.Id) | Remove-Job" -ForegroundColor Gray
Write-Host "Or close this PowerShell window." -ForegroundColor Gray
Write-Host ""

if (-not $NoBrowser) {
    Start-Process "http://localhost:8501"
}

# Keep script alive so background jobs stay running
Write-Host "Press Ctrl+C to stop both servers..." -ForegroundColor Yellow
try {
    while ($true) { Start-Sleep -Seconds 10 }
} finally {
    Write-Host "Stopping servers..." -ForegroundColor Yellow
    Stop-Job -Id $backendJob.Id, $frontendJob.Id -ErrorAction SilentlyContinue
    Remove-Job -Id $backendJob.Id, $frontendJob.Id -ErrorAction SilentlyContinue
}