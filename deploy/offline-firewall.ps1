# Run in an elevated PowerShell before a dedicated offline rehearsal.
# Rules target only Ollama and the chosen Python executable. Loopback is excluded.
param([Parameter(Mandatory=$true)][string]$PythonPath, [switch]$Remove)
$ErrorActionPreference = 'Stop'
$ollamaExecutable = Join-Path $env:LOCALAPPDATA 'Programs/Ollama/ollama.exe'
$programs = @{'PRATIRODH-Ollama-Offline'=$ollamaExecutable; 'PRATIRODH-Python-Offline'=$PythonPath}
foreach ($ruleName in $programs.Keys) {
    if ($Remove) {
        Get-NetFirewallRule -Name $ruleName -ErrorAction SilentlyContinue | Remove-NetFirewallRule
    } else {
        $resolvedProgram = (Resolve-Path -LiteralPath $programs[$ruleName]).Path
        if (-not (Get-NetFirewallRule -Name $ruleName -ErrorAction SilentlyContinue)) {
            New-NetFirewallRule -Name $ruleName -DisplayName $ruleName -Direction Outbound -Action Block -Program $resolvedProgram -RemoteAddress @('0.0.0.0-126.255.255.255','128.0.0.0-255.255.255.255','::2-ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff') | Out-Null
        } else {
            Get-NetFirewallRule -Name $ruleName | Get-NetFirewallApplicationFilter | Set-NetFirewallApplicationFilter -Program $resolvedProgram | Out-Null
        }
    }
}
