$ErrorActionPreference = "Stop"

$pythonExe = "$PSScriptRoot\..\.venv\Scripts\python.exe"
if (!(Test-Path $pythonExe)) {
  Write-Host "[BeaconAI] Virtual environment missing. Run scripts/dev-up.ps1 first."
  exit 1
}

Write-Host "[BeaconAI] Running backend unit tests..."
Push-Location "$PSScriptRoot\..\backend"
& $pythonExe -m pytest "tests" -q
Pop-Location
