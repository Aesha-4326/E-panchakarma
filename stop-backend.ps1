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

Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object {
        ($_.Name -match '^python(\.exe)?$' -and $_.CommandLine -like '*app.py*' -and $_.CommandLine -like "*$projectRoot*") -or
        ($_.Name -match '^mysqld(\.exe)?$' -and $_.CommandLine -like "*$projectRoot*" -and $_.CommandLine -like '*mysql-data*')
    } |
    ForEach-Object {
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
        Write-Host "Stopped lingering process $($_.Name) (PID $($_.ProcessId))"
    }

Write-Host "Stop command finished."
