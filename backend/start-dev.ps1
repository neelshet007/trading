param(
  [switch]$Reload = $true
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $PSScriptRoot "venv\Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
  throw "Backend virtual environment not found at backend\venv. Create it first with: python -m venv backend\venv"
}

Set-Location $root

if ($Reload) {
  & $venvPython -m uvicorn app:app --reload
} else {
  & $venvPython -m uvicorn app:app
}
