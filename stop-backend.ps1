$ErrorActionPreference = "SilentlyContinue"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$runDir = Join-Path $projectRoot ".run"

function Stop-FromPidFile([string]$name, [string]$fileName) {
    $pidFile = Join-Path $runDir $fileName
    if (-not (Test-Path $pidFile)) { return }

    $pidText = Get-Content $pidFile -ErrorAction SilentlyContinue
    $pidValue = 0
    [void][int]::TryParse($pidText, [ref]$pidValue)
    if ($pidValue -gt 0) {
        Stop-Process -Id $pidValue -Force -ErrorAction SilentlyContinue
        Write-Host "Stopped $name (PID $pidValue)"
    }
    Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
}

Stop-FromPidFile "Flask" "flask.pid"
Stop-FromPidFile "MySQL" "mysql.pid"

Write-Host "Stop command finished."
