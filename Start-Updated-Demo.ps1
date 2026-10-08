param([int]$Port = 8770, [string]$Store, [switch]$ReadOnly, [switch]$Requests,
      [string]$Model, [switch]$Fresh, [switch]$Check)
$ErrorActionPreference = 'Stop'
$demoWorkspace = $PSScriptRoot
$demoPython = Join-Path $demoWorkspace '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $demoPython)) {
    Write-Output 'Preparing the local Python environment...'
    $pythonLauncher = Get-Command py -ErrorAction SilentlyContinue
    if (-not $pythonLauncher) { throw 'Install Python 3.11 with its Windows py launcher, then run this command again.' }
    & $pythonLauncher.Source -3.11 -m venv (Join-Path $demoWorkspace '.venv')
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.11 environment creation failed. Install Python 3.11 and retry.' }
}
$dependencyLock = Join-Path $demoWorkspace 'requirements-deploy.txt'
$dependencyStamp = Join-Path $demoWorkspace '.venv\pratirodh-dependencies.sha256'
$dependencyHash = (Get-FileHash -LiteralPath $dependencyLock -Algorithm SHA256).Hash
$recordedHash = if (Test-Path -LiteralPath $dependencyStamp) { (Get-Content -LiteralPath $dependencyStamp -Raw).Trim() } else { '' }
& $demoPython -c 'import importlib.util, sys; sys.exit(0 if all(importlib.util.find_spec(x) for x in ("flask", "cryptography", "bandit", "waitress")) else 1)'
$dependenciesAvailable = $LASTEXITCODE -eq 0
if ($recordedHash -ne $dependencyHash -or -not $dependenciesAvailable) {
    Write-Output 'Installing verified dependencies (network access is needed during first setup)...'
    & $demoPython -m pip install --only-binary=:all: --require-hashes -r $dependencyLock
    if ($LASTEXITCODE -ne 0) { throw 'Dependency setup failed. Check internet access and retry; saved evidence is preserved.' }
    & $demoPython -m pip check
    if ($LASTEXITCODE -ne 0) { throw 'Dependency conflicts found. Resolve the reported environment conflicts before starting.' }
    Set-Content -LiteralPath $dependencyStamp -Value $dependencyHash -Encoding ascii
}
$demoArgs = @((Join-Path $demoWorkspace 'scripts\start_demo.py'), '--port', "$Port")
if ($Store) { $demoArgs += @('--store', $Store) }
if ($Requests) { $demoArgs += '--requests' }
if ($Model) { $demoArgs += @('--model', $Model) }
if ($Fresh) { $demoArgs += '--fresh' }
if ($Check) { $demoArgs += '--check' }
$previousReadOnly = [Environment]::GetEnvironmentVariable('PRATIRODH_READ_ONLY', 'Process')
try {
    if ($ReadOnly) { $env:PRATIRODH_READ_ONLY = '1' }
    else { Remove-Item Env:PRATIRODH_READ_ONLY -ErrorAction SilentlyContinue }
    Push-Location -LiteralPath $demoWorkspace
    try { & $demoPython @demoArgs; $demoExit = $LASTEXITCODE }
    finally { Pop-Location }
} finally { [Environment]::SetEnvironmentVariable('PRATIRODH_READ_ONLY', $previousReadOnly, 'Process') }
exit $demoExit
