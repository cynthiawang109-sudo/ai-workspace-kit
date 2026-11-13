# Human-run promotion: doc-search stays credential-free and is not involved.
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$Draft,
    [string]$Project = $env:AI_WORKSPACE_PROJECT
)
$ErrorActionPreference = 'Stop'
if ($Project -and $Project -notmatch '^[0-9]+$') { throw 'Project must be a project number.' }
if (-not (Get-Command gh -ErrorAction SilentlyContinue)) { throw 'gh is missing; install the GitHub CLI first.' }
gh auth status *> $null
if ($LASTEXITCODE -ne 0) { throw 'gh is not logged in; run gh auth login first.' }
if (-not (Test-Path -LiteralPath $Draft -PathType Leaf)) { throw "Draft file does not exist: $Draft" }
$root = Split-Path $PSScriptRoot -Parent
$allowed = [IO.Path]::GetFullPath((Join-Path $root 'tickets/drafts'))
$path = (Resolve-Path -LiteralPath $Draft).ProviderPath
if (-not $path.StartsWith($allowed + [IO.Path]::DirectorySeparatorChar, [StringComparison]::Ordinal)) {
    throw 'Draft must be under tickets/drafts/.'
}
# Reject links/junctions so an apparent draft cannot resolve outside the directory.
$item = Get-Item -LiteralPath $path -Force
while ($item -and $item.FullName -ne $root) {
    if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Draft path must not contain symbolic links or junctions.' }
    $item = Get-Item -LiteralPath (Split-Path $item.FullName -Parent) -Force
}
$path = (Resolve-Path -LiteralPath $Draft).ProviderPath
$content = [IO.File]::ReadAllText($path)
$parts = $content -split '---', 3
if (-not $content.StartsWith('---') -or $parts.Count -ne 3) { throw 'Draft must have --- delimited front matter.' }
$meta = New-Object 'System.Collections.Generic.Dictionary[string,string]' ([StringComparer]::Ordinal)
foreach ($line in ($parts[1] -split '\r?\n')) {
    if ($line.Contains(':')) {
        $pair = $line -split ':', 2
        $meta[$pair[0].Trim()] = $pair[1].Trim()
    }
}
if ($meta['status'] -cne 'draft') { throw 'Draft status must be draft.' }
if (-not $meta['title']) { throw 'Draft title is required.' }
$relative = $path.Substring($root.Length + 1).Replace('\', '/')
$body = $parts[2] + "`n`nPromoted from $relative (draft-first: filed by a human via scripts/promote-draft)`n"
$temp = [IO.Path]::GetTempFileName()
try {
    [IO.File]::WriteAllText($temp, $body, (New-Object Text.UTF8Encoding $false))
    $url = gh issue create --repo cynthiawang109-sudo/ai-workspace-kit --title $meta['title'] --body-file $temp
    if ($LASTEXITCODE -ne 0) { throw 'Issue creation failed.' }
    $url = "$url".Trim()
    Write-Output $url
    if ($Project) {
        gh project item-add $Project --owner cynthiawang109-sudo --url $url
        if ($LASTEXITCODE -ne 0) { throw "Issue created at $url, but adding it to Project $Project failed." }
        Write-Output "Added to Project $Project."
    } else {
        Write-Output 'No Project configured; issue was not added to a board.'
    }
} finally {
    Remove-Item -LiteralPath $temp -Force
}
