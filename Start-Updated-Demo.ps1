param([int]$Port = 8770, [string]$Store, [switch]$ReadOnly, [switch]$Requests)
$ErrorActionPreference = 'Stop'
$demoWorkspace = $PSScriptRoot
$demoPython = Join-Path $demoWorkspace '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $demoPython)) { throw 'Create .venv and install project dependencies first.' }
$demoArgs = @((Join-Path $demoWorkspace 'scripts\start_demo.py'), '--port', "$Port")
if ($Store) { $demoArgs += @('--store', $Store) }
if ($Requests) { $demoArgs += '--requests' }
$previousReadOnly = [Environment]::GetEnvironmentVariable('PRATIRODH_READ_ONLY', 'Process')
try {
    if ($ReadOnly) { $env:PRATIRODH_READ_ONLY = '1' }
    else { Remove-Item Env:PRATIRODH_READ_ONLY -ErrorAction SilentlyContinue }
    Push-Location -LiteralPath $demoWorkspace
    try { & $demoPython @demoArgs; $demoExit = $LASTEXITCODE }
    finally { Pop-Location }
} finally { [Environment]::SetEnvironmentVariable('PRATIRODH_READ_ONLY', $previousReadOnly, 'Process') }
exit $demoExit
