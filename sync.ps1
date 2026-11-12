# sync.ps1 - clone or fast-forward-update every repo listed in repos.txt
# into projects/. Idempotent. Usage:
#   .\sync.ps1              sync everything
#   .\sync.ps1 -Only docs   sync only repos whose name matches *docs*
param(
    [string]$Only = ""
)

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$manifest = Join-Path $root "repos.txt"
$projectsDir = Join-Path $root "projects"

if (-not (Test-Path $projectsDir)) {
    New-Item -ItemType Directory -Path $projectsDir | Out-Null
}

$failed = @()

foreach ($line in Get-Content $manifest) {
    $line = $line.Trim()
    if ($line -eq "" -or $line.StartsWith("#")) { continue }
    $parts = $line -split '\s+', 2
    $name = $parts[0]
    $url = $parts[1]
    if ($Only -ne "" -and $name -notlike "*$Only*") { continue }

    $dest = Join-Path $projectsDir $name
    if (Test-Path (Join-Path $dest ".git")) {
        Write-Host "== $name : pull --ff-only"
        git -C $dest pull --ff-only
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "$name : pull failed (local commits or conflicts?) - skipped, nothing overwritten"
            $failed += $name
        }
    } elseif (Test-Path $dest) {
        Write-Warning "$name : $dest exists but is not a git checkout - skipped"
        $failed += $name
    } else {
        Write-Host "== $name : clone"
        git clone $url $dest
        if ($LASTEXITCODE -ne 0) { $failed += $name }
    }
}

if ($failed.Count -gt 0) {
    Write-Warning ("Sync finished with problems: " + ($failed -join ", "))
    exit 1
}
Write-Host "Sync complete."
