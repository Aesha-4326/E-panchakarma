param(
    [string]$MySqlHost = "127.0.0.1",
    [string]$MySqlUser = "root",
    [string]$MySqlPassword = "",
    [string]$MySqlDatabase = "e_panchakarma",
    [string]$MySqlPort = "3306",
    [string]$GoogleClientId = ""
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$runDir = Join-Path $projectRoot ".run"
$mysqlDataDir = Join-Path $projectRoot "mysql-data"
$mysqlExe = "C:\Program Files\MySQL\MySQL Server 8.4\bin\mysqld.exe"
$mysqlCli = "C:\Program Files\MySQL\MySQL Server 8.4\bin\mysql.exe"

if (-not (Test-Path $mysqlExe)) {
    Write-Host "MySQL executable not found at: $mysqlExe" -ForegroundColor Red
    Write-Host "Please install MySQL Server 8.4 or update path in start-backend.ps1" -ForegroundColor Red
    exit 1
}

New-Item -ItemType Directory -Force -Path $runDir | Out-Null
New-Item -ItemType Directory -Force -Path $mysqlDataDir | Out-Null

function Get-LogPath {
    param([string]$basePath)
    if (-not (Test-Path $basePath)) { return $basePath }
    try {
        Remove-Item $basePath -Force -ErrorAction Stop
        return $basePath
    } catch {
        $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
        $dir = Split-Path -Parent $basePath
        $name = [System.IO.Path]::GetFileNameWithoutExtension($basePath)
        $ext = [System.IO.Path]::GetExtension($basePath)
        return (Join-Path $dir ("{0}-{1}{2}" -f $name, $stamp, $ext))
    }
}

function Test-MySqlReady {
    try {
        & $mysqlCli -h 127.0.0.1 -P $MySqlPort -u $MySqlUser -e "SELECT 1" | Out-Null
        return ($LASTEXITCODE -eq 0)
    } catch {
        return $false
    }
}

# Initialize MySQL data directory once.
if (-not (Test-Path (Join-Path $mysqlDataDir "auto.cnf"))) {
    Write-Host "Initializing MySQL data directory..." -ForegroundColor Yellow
    & $mysqlExe --initialize-insecure --datadir="$mysqlDataDir"
}

$mysqlReady = Test-MySqlReady
if (-not $mysqlReady) {
    $mysqlOut = Get-LogPath (Join-Path $runDir "mysqld.out.log")
    $mysqlErr = Get-LogPath (Join-Path $runDir "mysqld.err.log")

    $mysqlArgs = "--datadir=""$mysqlDataDir"" --port=$MySqlPort --bind-address=127.0.0.1 --console"
    $mysqlProc = Start-Process -FilePath $mysqlExe -ArgumentList $mysqlArgs -WorkingDirectory $projectRoot -RedirectStandardOutput $mysqlOut -RedirectStandardError $mysqlErr -PassThru
    Set-Content -Path (Join-Path $runDir "mysql.pid") -Value $mysqlProc.Id

    $started = $false
    for ($i = 0; $i -lt 30; $i++) {
        Start-Sleep -Milliseconds 500
        if (Test-MySqlReady) { $started = $true; break }
    }

    if (-not $started) {
        Write-Host "MySQL did not start on port $MySqlPort. Check: $mysqlErr" -ForegroundColor Red
        exit 1
    }
}

$flaskOut = Get-LogPath (Join-Path $runDir "flask.out.log")
$flaskErr = Get-LogPath (Join-Path $runDir "flask.err.log")

$flaskCommand = @"
`$env:MYSQL_HOST='$MySqlHost'
`$env:MYSQL_USER='$MySqlUser'
`$env:MYSQL_PASSWORD='$MySqlPassword'
`$env:MYSQL_DATABASE='$MySqlDatabase'
`$env:MYSQL_PORT='$MySqlPort'
if('$GoogleClientId' -ne ''){
    `$env:GOOGLE_CLIENT_ID='$GoogleClientId'
}
Set-Location '$projectRoot'
python app.py
"@

$flaskProc = Start-Process -FilePath "powershell" -ArgumentList "-NoProfile", "-Command", $flaskCommand -WorkingDirectory $projectRoot -RedirectStandardOutput $flaskOut -RedirectStandardError $flaskErr -PassThru
Set-Content -Path (Join-Path $runDir "flask.pid") -Value $flaskProc.Id

$apiReady = $false
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Milliseconds 500
    try {
        $health = Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:5000/health" -ErrorAction Stop
        if ($health.status -eq "ok") { $apiReady = $true; break }
    } catch {
    }
}

if (-not $apiReady) {
    Write-Host "Flask API did not come up. Check: $flaskErr" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Backend started successfully." -ForegroundColor Green
Write-Host "API URL: http://127.0.0.1:5000"
Write-Host "Health:  http://127.0.0.1:5000/health"
Write-Host ""
Write-Host "Log files:"
Write-Host " - $flaskErr"
Write-Host " - $mysqlDataDir"
Write-Host ""
Write-Host "To stop everything: .\stop-backend.ps1" -ForegroundColor Yellow
