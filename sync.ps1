# Materialize versions.txt pins in projects/. Dirty checkouts are warned and skipped.
# Main-tip pins stay on main; historical pins use detached HEAD.
# Usage: .\sync.ps1 [-Only substring] [-UpdatePins]
# -UpdatePins fetches origin/main and rewrites pins without moving checkouts.
param([string]$Only = "", [switch]$UpdatePins)
$root = $PSScriptRoot
$versions = Join-Path $root 'versions.txt'
if (-not (Test-Path $versions)) { Write-Error 'versions.txt missing'; exit 1 }
$content = [IO.File]::ReadAllText($versions)
$failed = @()
$changed = 0
foreach ($line in Get-Content (Join-Path $root 'repos.txt')) {
    $line = $line.Trim()
    if (-not $line -or $line.StartsWith('#')) { continue }
    $name, $url = $line -split '\s+', 2
    if (-not $name.Contains($Only)) { continue }
    $pattern = '(?m)^' + [regex]::Escape($name) + '[ \t]+([0-9a-fA-F]{40})\r?$'
    $match = [regex]::Match($content, $pattern)
    if (-not $match.Success) {
        Write-Warning "$name : missing or invalid pin in versions.txt"
        $failed += $name; continue
    }
    $pin = $match.Groups[1].Value
    $dest = Join-Path $root "projects/$name"
    $temporary = $null
    if ((Test-Path $dest) -and -not (Test-Path (Join-Path $dest '.git'))) {
        Write-Warning "$name : $dest exists but is not a git checkout"
        $failed += $name; continue
    }
    if (-not $UpdatePins -and (Test-Path (Join-Path $dest '.git'))) {
        $dirty = @(git -C $dest status --porcelain)
        if ($LASTEXITCODE -ne 0) { $failed += $name; continue }
        if ($dirty.Count -gt 0) {
            Write-Warning "$name : uncommitted changes - skipped, nothing touched"
            continue
        }
    }
    try {
        if (-not (Test-Path (Join-Path $dest '.git'))) {
            if ($UpdatePins) {
                $temporary = Join-Path ([IO.Path]::GetTempPath()) ("tf-110-" + [guid]::NewGuid())
                $dest = $temporary
                git init --bare -q $dest
                if ($LASTEXITCODE -ne 0) { $failed += $name; continue }
                git -C $dest remote add origin $url
                if ($LASTEXITCODE -ne 0) { $failed += $name; continue }
            } else {
                New-Item -ItemType Directory -Force (Join-Path $root 'projects') | Out-Null
                Write-Host "== $name : clone"
                git clone $url $dest
                if ($LASTEXITCODE -ne 0) { $failed += $name; continue }
            }
        }
        git -C $dest fetch origin +refs/heads/main:refs/remotes/origin/main
        if ($LASTEXITCODE -ne 0) { $failed += $name; continue }
        $tip = git -C $dest rev-parse refs/remotes/origin/main
        if ($UpdatePins) {
            if ($pin -ne $tip) {
                $sha = $match.Groups[1]
                $content = $content.Remove($sha.Index, $sha.Length).Insert($sha.Index, $tip)
                [IO.File]::WriteAllText($versions, $content, (New-Object Text.UTF8Encoding $false))
                Write-Host "== $name : pin $pin -> $tip"
                $changed++
            }
            continue
        }
        $head = git -C $dest rev-parse HEAD
        $branch = git -C $dest rev-parse --abbrev-ref HEAD
        if ($head -eq $pin -and ($pin -ne $tip -or $branch -ne 'HEAD')) {
            Write-Host "== $name : already at pin $pin"
        } elseif ($pin -eq $tip) {
            git -C $dest checkout main
            if ($LASTEXITCODE -ne 0) { $failed += $name; continue }
            git -C $dest merge --ff-only $tip
            if ($LASTEXITCODE -ne 0) { $failed += $name; continue }
            if ((git -C $dest rev-parse HEAD) -ne $pin) {
                Write-Warning "$name : main has local commits beyond pin $pin"
                $failed += $name
            }
        } else {
            git -C $dest checkout --detach $pin
            if ($LASTEXITCODE -ne 0) {
                Write-Warning "$name : cannot check out pin $pin"
                $failed += $name
            }
        }
    } finally {
        if ($temporary -and (Test-Path -LiteralPath $temporary)) {
            $resolved = [IO.Path]::GetFullPath($temporary)
            $tempRoot = [IO.Path]::GetFullPath([IO.Path]::GetTempPath())
            if (-not $resolved.StartsWith($tempRoot) -or (Split-Path $resolved -Leaf) -notlike 'tf-110-*') {
                throw 'Unexpected temporary directory'
            }
            Remove-Item -LiteralPath $resolved -Recurse -Force
        }
    }
}
if ($failed.Count -gt 0) {
    Write-Warning ("Sync finished with problems: " + ($failed -join ', ')); exit 1
}
if ($UpdatePins) { Write-Host "Pin update complete: $changed changed pin(s)." }
else { Write-Host 'Sync complete.' }
