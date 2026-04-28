param(
    [string]$Version = "",
    [string]$NotesPath = "docs\release-notes.md",
    [switch]$Draft,
    [switch]$Prerelease,
    [switch]$NoBuild
)

$ErrorActionPreference = "Stop"

function Get-VersionFromPyProject {
    $match = Select-String -Path "pyproject.toml" -Pattern '^version\s*=\s*"([^"]+)"' | Select-Object -First 1
    if (-not $match) {
        throw "Could not find version in pyproject.toml."
    }
    return $match.Matches[0].Groups[1].Value
}

if (-not $Version) {
    $Version = Get-VersionFromPyProject
}

if (-not (Test-Path $NotesPath)) {
    throw "Release notes file not found: $NotesPath"
}

$notes = Get-Content $NotesPath -Raw
if ($notes -notmatch "(?m)^# Release notes for\s+$([regex]::Escape($Version))\s*$") {
    Write-Warning "The release notes header does not match version $Version."
}

if (-not $NoBuild) {
    python -m build
}

$tag = "v$Version"
$releaseArgs = @(
    "release",
    "create",
    $tag,
    "--repo",
    "rolling-codes/EasyCord",
    "--title",
    "EasyCord v$Version",
    "--notes-file",
    $NotesPath,
    "--target",
    "HEAD"
)

if ($Draft) {
    $releaseArgs += "--draft"
}

if ($Prerelease) {
    $releaseArgs += "--prerelease"
}

$assets = @()
if (-not $NoBuild -and (Test-Path "dist")) {
    $assets = Get-ChildItem -File "dist" | ForEach-Object { $_.FullName }
    if ($assets.Count -gt 0) {
        $releaseArgs += $assets
    }
}

& gh @releaseArgs
