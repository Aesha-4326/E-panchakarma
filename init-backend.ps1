param(
    [switch]$StopAfterInit
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$startScript = Join-Path $projectRoot "start-backend.ps1"
$stopScript = Join-Path $projectRoot "stop-backend.ps1"

if (-not (Test-Path $startScript)) {
    Write-Host "Missing script: $startScript" -ForegroundColor Red
    exit 1
}

Write-Host "Starting backend..." -ForegroundColor Yellow
& $startScript

Write-Host "Running POST /init-db ..." -ForegroundColor Yellow
$initResponse = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:5000/init-db"
$json = $initResponse | ConvertTo-Json -Depth 5 -Compress
Write-Host "init-db response: $json" -ForegroundColor Green

if ($StopAfterInit) {
    if (Test-Path $stopScript) {
        Write-Host "Stopping backend (--StopAfterInit used)..." -ForegroundColor Yellow
        & $stopScript
    }
}

Write-Host "Done." -ForegroundColor Green
