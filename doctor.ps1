# doctor.ps1 - one-command health check for this workspace.
#
# Verifies the pieces the kit needs to be fully operational on this
# machine: workspace layout, sub-repo git state, the doc-search virtual
# environment, Codex MCP registration, and the presence (never the
# value) of the GitHub token. Exits non-zero if any hard check fails.
#
# Usage:  .\doctor.ps1        (from the workspace root)

$ErrorActionPreference = 'Continue'
$root = $PSScriptRoot
$fail = 0
$warn = 0

function Report([string]$Status, [string]$Name, [string]$Detail) {
    if ($Status -eq 'fail') { $script:fail++ }
    if ($Status -eq 'warn') { $script:warn++ }
    "{0,-6} {1} - {2}" -f "[$Status]", $Name, $Detail
}

Write-Output "ai-workspace-kit doctor - $root"
Write-Output ""

# 1. Workspace layout: every repos.txt entry checked out under projects/.
$repos = Get-Content (Join-Path $root 'repos.txt') |
    Where-Object { $_ -and -not $_.StartsWith('#') } |
    ForEach-Object { ($_ -split '\s+')[0] }
foreach ($name in $repos) {
    $path = Join-Path $root "projects\$name"
    if (Test-Path $path) {
        Report 'ok' "layout/$name" 'present'
    } else {
        Report 'fail' "layout/$name" 'missing - run .\sync.ps1'
    }
}

# 2. Git state of each checkout: default branch, clean tree.
foreach ($name in $repos) {
    $path = Join-Path $root "projects\$name"
    if (-not (Test-Path $path)) { continue }
    $branch = git -C $path rev-parse --abbrev-ref HEAD 2>$null
    $dirty = @(git -C $path status --porcelain 2>$null).Count
    if ($branch -ne 'main') {
        Report 'warn' "git/$name" "on branch '$branch', expected 'main'"
    } elseif ($dirty -gt 0) {
        Report 'warn' "git/$name" "$dirty uncommitted change(s)"
    } else {
        Report 'ok' "git/$name" 'main, clean'
    }
}

# 3. Python + doc-search virtual environment.
$venvPy = Join-Path $root 'mcp\doc-search\.venv\Scripts\python.exe'
if (-not (Test-Path $venvPy)) {
    Report 'fail' 'doc-search venv' 'missing - see mcp\doc-search\README.md setup'
} else {
    $ver = & $venvPy -c "import fastmcp, sys; print(sys.version.split()[0] + ' / fastmcp ' + fastmcp.__version__)" 2>$null
    if ($LASTEXITCODE -eq 0) {
        Report 'ok' 'doc-search venv' $ver
    } else {
        Report 'fail' 'doc-search venv' 'present but fastmcp is not importable'
    }
}

# 4. Codex CLI + MCP registration.
$codex = Get-Command codex -ErrorAction SilentlyContinue
if (-not $codex) {
    $defaultCodex = Join-Path $env:LOCALAPPDATA 'Programs\OpenAI\Codex\bin\codex.exe'
    if (Test-Path $defaultCodex) { $codex = Get-Item $defaultCodex }
}
if (-not $codex) {
    Report 'warn' 'codex' 'CLI not found - MCP registration unchecked'
} else {
    $mcpList = & $codex.Source mcp list 2>$null | Out-String
    if ($mcpList -match 'doc-search') {
        Report 'ok' 'codex mcp/doc-search' 'registered'
    } else {
        Report 'fail' 'codex mcp/doc-search' 'not registered - see mcp\README.md'
    }
    if ($mcpList -match 'github') {
        Report 'ok' 'codex mcp/github' 'registered'
    } else {
        Report 'warn' 'codex mcp/github' 'not registered - see mcp\README.md'
    }
}

# 5. GITHUB_PAT present (value never printed).
$pat = [Environment]::GetEnvironmentVariable('GITHUB_PAT', 'User')
if (-not $pat) { $pat = [Environment]::GetEnvironmentVariable('GITHUB_PAT', 'Process') }
if ($pat) {
    Report 'ok' 'GITHUB_PAT' "set (length $($pat.Length))"
} else {
    Report 'warn' 'GITHUB_PAT' 'not set - the github MCP server cannot authenticate'
}

# 6. gh CLI login (needed to push workflow files and manage PRs).
$gh = Get-Command gh -ErrorAction SilentlyContinue
if (-not $gh) {
    $defaultGh = 'C:\Program Files\GitHub CLI\gh.exe'
    if (Test-Path $defaultGh) { $gh = Get-Item $defaultGh }
}
if (-not $gh) {
    Report 'warn' 'gh' 'CLI not found'
} else {
    $status = & $gh.Source auth status 2>&1 | Out-String
    if ($status -match 'Logged in to github.com') {
        if ($status -match 'workflow') {
            Report 'ok' 'gh' 'logged in, workflow scope present'
        } else {
            Report 'warn' 'gh' 'logged in but workflow scope missing - cannot push Actions files'
        }
    } else {
        Report 'fail' 'gh' 'not logged in (or token invalid)'
    }
}

Write-Output ""
if ($fail -gt 0) {
    Write-Output "Result: $fail failing check(s), $warn warning(s)."
    exit 1
}
Write-Output "Result: all hard checks passed ($warn warning(s))."
exit 0
