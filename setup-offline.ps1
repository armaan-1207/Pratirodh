$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$ollamaPath = Join-Path $env:LOCALAPPDATA 'Programs/Ollama/ollama.exe'
if (-not (Test-Path -LiteralPath $ollamaPath)) {
    winget install --id Ollama.Ollama --exact --silent --accept-package-agreements --accept-source-agreements --disable-interactivity
    if ($LASTEXITCODE -ne 0) { throw 'Ollama installation failed' }
}
$env:OLLAMA_HOST = '127.0.0.1:11434'
$env:OLLAMA_NO_CLOUD = '1'
$env:OLLAMA_NUM_PARALLEL = '1'
$env:OLLAMA_CONTEXT_LENGTH = '8192'
$ollamaConfigDirectory = Join-Path $env:USERPROFILE '.ollama'
New-Item -ItemType Directory -Path $ollamaConfigDirectory -Force | Out-Null
$ollamaConfigPath = Join-Path $ollamaConfigDirectory 'server.json'
$ollamaConfig = if (Test-Path -LiteralPath $ollamaConfigPath) { Get-Content -LiteralPath $ollamaConfigPath -Raw | ConvertFrom-Json -AsHashtable } else { @{} }
$ollamaConfig['disable_ollama_cloud'] = $true
$ollamaConfig | ConvertTo-Json | Set-Content -LiteralPath $ollamaConfigPath -Encoding utf8
if (-not (Test-NetConnection -ComputerName 127.0.0.1 -Port 11434 -InformationLevel Quiet -WarningAction SilentlyContinue)) {
    Start-Process -FilePath $ollamaPath -ArgumentList 'serve' -WindowStyle Hidden
}
$installedModels = @()
for ($attempt = 0; $attempt -lt 20; $attempt++) {
    try { $installedModels = (Invoke-RestMethod -Uri 'http://127.0.0.1:11434/api/tags' -TimeoutSec 2).models.name; break }
    catch { Start-Sleep -Milliseconds 500 }
}
if ($installedModels -notcontains 'qwen2.5-coder:3b') {
    & $ollamaPath pull qwen2.5-coder:3b
    if ($LASTEXITCODE -ne 0) { throw 'Local model download failed. Temporarily remove offline rules during setup downloads.' }
}
Write-Output 'Offline model setup complete. Downloads are not part of runtime.'
