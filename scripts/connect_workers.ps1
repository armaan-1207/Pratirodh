param(
    [string]$ExecutionHost = 'pratirodh-worker',
    [string]$AuditHost = 'pratirodh-audit'
)
$ErrorActionPreference = 'Stop'
foreach ($taskHost in @($ExecutionHost, $AuditHost)) {
    if ($taskHost -notmatch '^[A-Za-z0-9_.-]+$') { throw 'Use a configured SSH host alias.' }
}
function Get-WorkerIdentity([string]$taskHost) {
    $taskIdentity = & ssh -o BatchMode=yes -o ConnectTimeout=10 $taskHost docker info --format '{{.ID}}'
    if ($LASTEXITCODE -ne 0 -or -not $taskIdentity) {
        throw "SSH/Docker preflight failed for $taskHost. Check the setup guide."
    }
    return ($taskIdentity -join '').Trim()
}
$taskExecutionId = Get-WorkerIdentity $ExecutionHost
$taskAuditId = Get-WorkerIdentity $AuditHost
if ($taskExecutionId -eq $taskAuditId) { throw 'Both destinations refer to the same Docker daemon.' }
$taskLocalId = & docker --context desktop-linux info --format '{{.ID}}' 2>$null
if ($LASTEXITCODE -eq 0 -and ($taskLocalId -eq $taskExecutionId -or $taskLocalId -eq $taskAuditId)) {
    throw 'A destination refers to the shared Docker Desktop daemon.'
}
foreach ($taskWorker in @(@('pratirodh-worker', $ExecutionHost), @('pratirodh-audit', $AuditHost))) {
    & docker context inspect $taskWorker[0] *> $null
    if ($LASTEXITCODE -eq 0) { throw "Context $($taskWorker[0]) already exists; inspect it before changing it." }
}
foreach ($taskWorker in @(@('pratirodh-worker', $ExecutionHost), @('pratirodh-audit', $AuditHost))) {
    & docker context create $taskWorker[0] --docker "host=ssh://$($taskWorker[1])"
    if ($LASTEXITCODE -ne 0) { throw 'Context creation failed.' }
}
Write-Output 'Separate worker connections verified. The active Docker context was not changed.'
