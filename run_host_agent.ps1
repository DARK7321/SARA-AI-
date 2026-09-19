# Start the local Windows desktop-control service.
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

$python = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $python) {
    Write-Host "ERROR: Python is not installed or not on PATH." -ForegroundColor Red
    exit 1
}

& $python -m uvicorn packages.connectors.host_agent.server:app --host 0.0.0.0 --port 7788
