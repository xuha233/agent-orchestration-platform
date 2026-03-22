param(
    [string]$ReleaseVersion = ""
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$desktopDir = Split-Path -Parent $scriptDir
$rootDir = Split-Path -Parent $desktopDir
$tauriConfigPath = Join-Path $desktopDir "src-tauri\tauri.conf.json"

function Get-DesktopVersion {
    $config = Get-Content -Path $tauriConfigPath -Raw | ConvertFrom-Json
    return [string]$config.version
}

$effectiveVersion = if ($ReleaseVersion) { $ReleaseVersion } else { Get-DesktopVersion }
$releaseDir = Join-Path $rootDir "releases\windows\$effectiveVersion"
$manifestPath = Join-Path $releaseDir "release-manifest.json"
$notesPath = Join-Path $releaseDir "release-notes-template.md"

if (-not (Test-Path $releaseDir)) {
    throw "Release directory not found: $releaseDir"
}

if (-not (Test-Path $manifestPath)) {
    throw "Missing release manifest: $manifestPath"
}

if (-not (Test-Path $notesPath)) {
    throw "Missing release notes template: $notesPath"
}

$manifest = Get-Content -Path $manifestPath -Raw | ConvertFrom-Json
$missingArtifacts = @()
foreach ($artifact in $manifest.artifacts) {
    if (-not (Test-Path $artifact.staged_path)) {
        $missingArtifacts += $artifact.staged_path
    }
}

if ($missingArtifacts.Count -gt 0) {
    throw "Missing staged artifacts: $($missingArtifacts -join ', ')"
}

Write-Host "Release verification passed for version $effectiveVersion" -ForegroundColor Green
Write-Host "Release directory: $releaseDir" -ForegroundColor Green
foreach ($artifact in $manifest.artifacts) {
    Write-Host "Artifact: $($artifact.name) ($($artifact.size_bytes) bytes)" -ForegroundColor Green
}
