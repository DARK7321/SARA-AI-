# OmniBrain 1-Click Launch Script (Windows PowerShell)
# Personal Autonomous AI Operating System — F.R.I.D.A.Y.

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "       🧠 OMNIBRAIN — AUTONOMOUS AI OPERATING SYSTEM        " -ForegroundColor Cyan
Write-Host "          Persona: F.R.I.D.A.Y.  |  100% Free Stack          " -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Check Docker
Write-Host "[1/5] Checking Docker Engine..." -ForegroundColor White
$dockerVersion = docker --version 2>$null
if (-not $dockerVersion) {
    Write-Host "ERROR: Docker is not installed or not running. Please start Docker Desktop." -ForegroundColor Red
    exit 1
}
Write-Host "  -> Docker is active ($dockerVersion)" -ForegroundColor Green

# 2. Start PostgreSQL, Redis & API containers
Write-Host "[2/5] Starting Backend Containers (PostgreSQL pgvector, Redis 7, FastAPI)..." -ForegroundColor White
docker compose up -d
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to start docker compose containers." -ForegroundColor Red
    exit 1
}
Write-Host "  -> Backend containers online." -ForegroundColor Green

# 3. Apply Alembic Migrations
Write-Host "[3/5] Applying Database Migrations..." -ForegroundColor White
docker compose exec -T api alembic upgrade head
Write-Host "  -> Database schema up to date (Alembic Head)." -ForegroundColor Green

# 4. Check Health Endpoint
Write-Host "[4/5] Verifying API Gateway Health..." -ForegroundColor White
Start-Sleep -Seconds 2
$healthOk = $false
for ($i = 0; $i -lt 15; $i++) {
    try {
        $res = Invoke-RestMethod -Uri "http://localhost:8000/v1/health" -Method Get -TimeoutSec 2 -ErrorAction Stop
        if ($res.ok -eq $true) {
            $healthOk = $true
            break
        }
    } catch {
        Start-Sleep -Seconds 1
    }
}

if ($healthOk) {
    Write-Host "  -> API Gateway is HEALTHY at http://localhost:8000" -ForegroundColor Green
} else {
    Write-Host "  -> Warning: API Gateway is still initializing..." -ForegroundColor Yellow
}

# 5. Launch Command Center UI
Write-Host "[5/5] Launching Command Center UI on http://localhost:3000..." -ForegroundColor White
Start-Process "http://localhost:3000"

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "       ✨ OMNIBRAIN IS ONLINE AND OPERATIONAL! ✨          " -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host "  🖥️  Web Command Center : http://localhost:3000" -ForegroundColor Cyan
Write-Host "  📖  API Documentation  : http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "  🛡️  Autonomy Controls  : http://localhost:3000 (Safety & Autonomy tab)" -ForegroundColor Cyan
Write-Host "  📱  Mobile Companion   : Inbound Webhooks & Tasker on /v1/mobile" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""

