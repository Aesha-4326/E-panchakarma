[string]$MySqlPassword = "7#2A7Eea"

param(
    [string]$MySqlHost = "127.0.0.1",
    [string]$MySqlUser = "root",
    [string]$MySqlPassword = "",
    [string]$MySqlDatabase = "e_panchakarma",
    [string]$MySqlPort = "3307",
    [string]$GoogleClientId = "",
    [string]$SmtpHost = "",
    [string]$SmtpPort = "",
    [string]$SmtpUsername = "",
    [string]$SmtpPassword = "",
    [string]$SmtpFromEmail = "",
    [string]$SmtpFromName = "",
    [string]$SmtpUseTls = "",
    [string]$SmtpUseSsl = ""
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$runDir = Join-Path $projectRoot ".run"
$mysqlDataDir = Join-Path $projectRoot "mysql-data"
$mysqlExe = "C:\Program Files\MySQL\MySQL Server 8.4\bin\mysqld.exe"
$mysqlCli = "C:\Program Files\MySQL\MySQL Server 8.4\bin\mysql.exe"
$envFile = Join-Path $projectRoot ".env.local"

function Get-LocalEnvValue {
    param(
        [string]$Key
    )

    if (-not (Test-Path $envFile)) {
        return $null
    }

    $match = Get-Content $envFile | Where-Object {
        $_ -match "^\s*$Key\s*="
    } | Select-Object -First 1

    if (-not $match) {
        return $null
    }

    $value = ($match -split "=", 2)[1].Trim()
    if (($value.StartsWith('"') -and $value.EndsWith('"')) -or ($value.StartsWith("'") -and $value.EndsWith("'"))) {
        $value = $value.Substring(1, $value.Length - 2)
    }
    return $value
}

function Resolve-Setting {
    param(
        [string]$ParamName,
        [string]$CurrentValue,
        [string]$EnvKey,
        [string]$DefaultValue = ""
    )

    if ($PSBoundParameters.ContainsKey($ParamName)) {
        return $CurrentValue
    }

    $localValue = Get-LocalEnvValue $EnvKey
    if ($null -ne $localValue) {
        return $localValue
    }

    $envValue = [Environment]::GetEnvironmentVariable($EnvKey)
    if (-not [string]::IsNullOrWhiteSpace($envValue)) {
        return $envValue
    }

    return $DefaultValue
}

$MySqlHost = Resolve-Setting "MySqlHost" $MySqlHost "MYSQL_HOST" "127.0.0.1"
$MySqlUser = Resolve-Setting "MySqlUser" $MySqlUser "MYSQL_USER" "root"
$MySqlPassword = Resolve-Setting "MySqlPassword" $MySqlPassword "MYSQL_PASSWORD" ""
$MySqlDatabase = Resolve-Setting "MySqlDatabase" $MySqlDatabase "MYSQL_DATABASE" "e_panchakarma"
$MySqlPort = Resolve-Setting "MySqlPort" $MySqlPort "MYSQL_PORT" "3307"
$GoogleClientId = Resolve-Setting "GoogleClientId" $GoogleClientId "GOOGLE_CLIENT_ID" ""
$SmtpHost = Resolve-Setting "SmtpHost" $SmtpHost "SMTP_HOST" ""
$SmtpPort = Resolve-Setting "SmtpPort" $SmtpPort "SMTP_PORT" ""
$SmtpUsername = Resolve-Setting "SmtpUsername" $SmtpUsername "SMTP_USERNAME" ""
$SmtpPassword = Resolve-Setting "SmtpPassword" $SmtpPassword "SMTP_PASSWORD" ""
$SmtpFromEmail = Resolve-Setting "SmtpFromEmail" $SmtpFromEmail "SMTP_FROM_EMAIL" ""
$SmtpFromName = Resolve-Setting "SmtpFromName" $SmtpFromName "SMTP_FROM_NAME" ""
$SmtpUseTls = Resolve-Setting "SmtpUseTls" $SmtpUseTls "SMTP_USE_TLS" ""
$SmtpUseSsl = Resolve-Setting "SmtpUseSsl" $SmtpUseSsl "SMTP_USE_SSL" ""

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
        $mysqlArgs = @("-h", "127.0.0.1", "-P", $MySqlPort, "-u", $MySqlUser)
        if (-not [string]::IsNullOrEmpty($MySqlPassword)) {
            $mysqlArgs += "-p$MySqlPassword"
        }
        $mysqlArgs += @("-e", "SELECT 1")
        & $mysqlCli @mysqlArgs | Out-Null
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
`$env:APP_DEBUG='false'
if('$GoogleClientId' -ne ''){
    `$env:GOOGLE_CLIENT_ID='$GoogleClientId'
}
if('$SmtpHost' -ne ''){
    `$env:SMTP_HOST='$SmtpHost'
}
if('$SmtpPort' -ne ''){
    `$env:SMTP_PORT='$SmtpPort'
}
if('$SmtpUsername' -ne ''){
    `$env:SMTP_USERNAME='$SmtpUsername'
}
if('$SmtpPassword' -ne ''){
    `$env:SMTP_PASSWORD='$SmtpPassword'
}
if('$SmtpFromEmail' -ne ''){
    `$env:SMTP_FROM_EMAIL='$SmtpFromEmail'
}
if('$SmtpFromName' -ne ''){
    `$env:SMTP_FROM_NAME='$SmtpFromName'
}
if('$SmtpUseTls' -ne ''){
    `$env:SMTP_USE_TLS='$SmtpUseTls'
}
if('$SmtpUseSsl' -ne ''){
    `$env:SMTP_USE_SSL='$SmtpUseSsl'
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
Write-Host "App URL: http://127.0.0.1:5000"
Write-Host "API URL: http://127.0.0.1:5000/api"
Write-Host "Health:  http://127.0.0.1:5000/health"
Write-Host "Other devices on the same Wi-Fi can open: http://YOUR_COMPUTER_IP:5000"
Write-Host ""
Write-Host "Log files:"
Write-Host " - $flaskErr"
Write-Host " - $mysqlDataDir"
Write-Host ""
Write-Host "To stop everything: .\stop-backend.ps1" -ForegroundColor Yellow
