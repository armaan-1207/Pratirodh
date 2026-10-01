$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if (-not (Test-Path -LiteralPath '.venv/Scripts/python.exe')) { python -m venv .venv }
& ./.venv/Scripts/python.exe -m pip install -r requirements-deploy.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed' }
& ./.venv/Scripts/python.exe -m pratirodh doctor
if ($LASTEXITCODE -ne 0) {
    & ./.venv/Scripts/python.exe -m pratirodh build-runner
    if ($LASTEXITCODE -ne 0) { throw 'Runner build failed. Start Docker Desktop first.' }
}
Write-Output 'For real offline repair, run setup-offline.ps1 once and restart Ollama with cloud disabled.'
& ./.venv/Scripts/python.exe -m pratirodh serve
