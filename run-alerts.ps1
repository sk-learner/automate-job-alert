$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

$BundledPython = "C:\Users\sarat\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
$Python = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $Python -and (Test-Path $BundledPython)) {
    $Python = $BundledPython
}
if (-not $Python) {
    throw "Python was not found. Install Python 3.10+ or update run-alerts.ps1 with the Python path."
}

& $Python .\job_alerts.py
