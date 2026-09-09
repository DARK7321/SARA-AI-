# OmniBrain Clean Shutdown Script (Windows PowerShell)

Write-Host "Stopping OmniBrain services gracefully..." -ForegroundColor Yellow
docker compose down
Write-Host "OmniBrain backend stopped safely." -ForegroundColor Green

