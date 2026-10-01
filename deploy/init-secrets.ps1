$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)
if (Test-Path -LiteralPath '.env') { throw '.env already exists; preserve its existing credentials' }
function New-Secret {
    $bytes = New-Object byte[] 48
    $generator = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try { $generator.GetBytes($bytes) } finally { $generator.Dispose() }
    return [Convert]::ToBase64String($bytes)
}
$deploymentPassword = New-Secret
$deploymentSession = New-Secret
@"
PRATIRODH_ENV=production
PRATIRODH_READ_ONLY=1
PRATIRODH_ALLOWED_HOSTS=localhost,127.0.0.1
PRATIRODH_USERNAME=reviewer
PRATIRODH_PASSWORD=$deploymentPassword
PRATIRODH_SESSION_SECRET=$deploymentSession
"@ | Set-Content -LiteralPath '.env' -Encoding utf8
Write-Output 'Created .env. Store its credentials in your password manager and restrict file access.'
