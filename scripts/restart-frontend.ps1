param(
    [int]$Port = 3000
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$frontendDir = Join-Path $repoRoot "frontend"
$nextDir = Join-Path $frontendDir ".next"

Write-Host "Stopping frontend processes on port $Port..."
$connections = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
$processIds = $connections | Select-Object -ExpandProperty OwningProcess -Unique
foreach ($processId in $processIds) {
    if ($processId -and $processId -ne 0) {
        Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
        Write-Host "Stopped process $processId"
    }
}

if (Test-Path -LiteralPath $nextDir) {
    $resolvedNext = Resolve-Path -LiteralPath $nextDir
    $resolvedRepo = Resolve-Path -LiteralPath $repoRoot
    if (-not $resolvedNext.Path.StartsWith($resolvedRepo.Path)) {
        throw "Refusing to delete outside repo: $($resolvedNext.Path)"
    }
    Remove-Item -LiteralPath $resolvedNext.Path -Recurse -Force
    Write-Host "Cleared frontend\.next"
}

Write-Host "Starting frontend on port $Port..."
Start-Process -FilePath "cmd.exe" `
    -ArgumentList @("/k", "cd /d `"$frontendDir`" && npm.cmd run dev -- --port $Port") `
    -WindowStyle Minimized

Write-Host "Frontend starting at http://localhost:$Port"
