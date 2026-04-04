$ErrorActionPreference = "Stop"
Set-Location "c:\Users\Ayesha\Desktop\PANCHKARMA\my project"

powershell -NoProfile -ExecutionPolicy Bypass -File ".\start-backend.ps1" | Out-Host

$stamp = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
$email = "smoke$stamp@example.com"

$regBody = @{ name = "Smoke User"; email = $email; password = "patient123"; age = 26 } | ConvertTo-Json
$reg = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:5000/api/auth/patient/register" -ContentType "application/json" -Body $regBody

$loginBody = @{ email = $email; password = "patient123" } | ConvertTo-Json
$login = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:5000/api/auth/patient/login" -ContentType "application/json" -Body $loginBody

Write-Host ("REGISTER_OK user_id=" + $reg.session.user_id)
Write-Host ("LOGIN_OK token_len=" + $login.session.token.Length)

powershell -NoProfile -ExecutionPolicy Bypass -File ".\stop-backend.ps1" | Out-Host
