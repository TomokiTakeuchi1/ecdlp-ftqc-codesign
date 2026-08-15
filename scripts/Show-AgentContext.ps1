$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot

$Files = @(
    "AGENTS.md",
    "context/PROJECT_CHARTER.md",
    "context/STATUS.md",
    "context/TASKS.md",
    "context/AI_HANDOFF.md",
    "coordination/PROTOCOL.md",
    "coordination/WORK_LOCKS.md",
    "coordination/REVIEW_QUEUE.md"
)

foreach ($RelativePath in $Files) {
    $Path = Join-Path $RepoRoot $RelativePath
    Write-Host "`n===== $RelativePath =====" -ForegroundColor Cyan
    Get-Content -LiteralPath $Path
}