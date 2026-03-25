[CmdletBinding()]
param(
  [switch]$SkipDocker
)

$ErrorActionPreference = "Stop"

if (-not $SkipDocker) {
  Write-Host "[BeaconAI] Starting local infrastructure..."
  Push-Location "$PSScriptRoot\..\infra"
  docker compose up -d
  Pop-Location
} else {
  Write-Host "[BeaconAI] SkipDocker enabled. Using DATABASE_URL from backend/.env"
}

$backendPython = "$PSScriptRoot\..\.venv\Scripts\python.exe"
if (!(Test-Path $backendPython)) {
  Write-Host "[BeaconAI] Creating virtual environment..."
  Push-Location "$PSScriptRoot\.."
  python -m venv .venv
  Pop-Location
}

Write-Host "[BeaconAI] Installing backend dependencies..."
& $backendPython -m pip install -r "$PSScriptRoot\..\backend\requirements.txt"

Write-Host "[BeaconAI] Launching backend server (port 5000)..."
Start-Process -FilePath $backendPython -ArgumentList "run.py" -WorkingDirectory "$PSScriptRoot\..\backend"

Write-Host "[BeaconAI] Launching frontend static server (port 8080)..."
Start-Process -FilePath $backendPython -ArgumentList "-m", "http.server", "8080" -WorkingDirectory "$PSScriptRoot\..\frontend"

Write-Host "[BeaconAI] Startup complete."
Write-Host "Backend: http://localhost:5000"
Write-Host "Frontend: http://localhost:8080"
