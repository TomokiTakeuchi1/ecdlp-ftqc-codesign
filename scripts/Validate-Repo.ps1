$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

$Required = @(
    "AGENTS.md",
    "CLAUDE.md",
    "context/PROJECT_CHARTER.md",
    "context/STATUS.md",
    "context/TASKS.md",
    "coordination/PROTOCOL.md",
    "coordination/WORK_LOCKS.md",
    "coordination/REVIEW_QUEUE.md",
    "pyproject.toml"
)

$Missing = @()
foreach ($RelativePath in $Required) {
    if (-not (Test-Path -LiteralPath (Join-Path $RepoRoot $RelativePath))) {
        $Missing += $RelativePath
    }
}

if ($Missing.Count -gt 0) {
    Write-Error ("Missing required files: " + ($Missing -join ", "))
}

Write-Host "Repository structure check passed." -ForegroundColor Green

if (Get-Command python -ErrorAction SilentlyContinue) {
    $env:PYTHONPATH = Join-Path $RepoRoot "src"
    python -m pytest
}
else {
    Write-Warning "Python was not found; pytest was not run."
}