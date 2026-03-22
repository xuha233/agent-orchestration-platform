param(
    [string]$ReleaseVersion = "",
    [switch]$SkipInstall,
    [switch]$WhatIf
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$desktopDir = Split-Path -Parent $scriptDir
$rootDir = Split-Path -Parent $desktopDir
$bundleDir = Join-Path $desktopDir "src-tauri\target\release\bundle\msi"
$tauriConfigPath = Join-Path $desktopDir "src-tauri\tauri.conf.json"
$releaseRoot = Join-Path $rootDir "releases\windows"

function Write-Step {
    param([string]$Message)
    Write-Host "`n==> $Message" -ForegroundColor Cyan
}

function Assert-Command {
    param(
        [string]$CommandName,
        [string]$InstallHint
    )

    if (Get-Command $CommandName -ErrorAction SilentlyContinue) {
        return
    }

    $fallbacks = @()
    if ($CommandName -in @("cargo", "rustc", "rustup")) {
        $fallbacks += Join-Path $env:USERPROFILE ".cargo\bin"
    }

    foreach ($fallback in $fallbacks) {
        $candidate = Join-Path $fallback "$CommandName.exe"
        if (Test-Path $candidate) {
            if (-not ($env:PATH -split ";" | Where-Object { $_ -eq $fallback })) {
                $env:PATH = "$fallback;$env:PATH"
            }
            return
        }
    }

    throw "$CommandName was not found. $InstallHint"
}

function Invoke-Step {
    param(
        [string]$Command,
        [string]$WorkingDirectory
    )

    if ($WhatIf) {
        Write-Host "[WhatIf] $Command" -ForegroundColor Yellow
        return
    }

    Push-Location $WorkingDirectory
    try {
        Invoke-Expression $Command
    }
    finally {
        Pop-Location
    }
}

function Get-DesktopVersion {
    if (-not (Test-Path $tauriConfigPath)) {
        throw "Could not find tauri.conf.json at $tauriConfigPath"
    }

    $config = Get-Content -Path $tauriConfigPath -Raw | ConvertFrom-Json
    return [string]$config.version
}

function Write-ReleaseManifest {
    param(
        [string]$Version,
        [string]$ReleaseDirectory,
        [array]$MsiFiles
    )

    $manifestPath = Join-Path $ReleaseDirectory "release-manifest.json"
    $notesPath = Join-Path $ReleaseDirectory "release-notes-template.md"
    $manifest = [ordered]@{
        version = $Version
        generated_at = (Get-Date).ToString("s")
        platform = "windows"
        artifacts = @(
            $MsiFiles | ForEach-Object {
                [ordered]@{
                    name = $_.Name
                    size_bytes = $_.Length
                    staged_path = (Join-Path $ReleaseDirectory $_.Name)
                }
            }
        )
        checklist = @(
            "Launch AOP Desktop on Windows",
            "Verify Setup, Providers, Projects, Run, Workflow, and Memory pages load",
            "Confirm first-run onboarding path is clear",
            "Capture known limitations before sharing"
        )
    } | ConvertTo-Json -Depth 6

    Set-Content -Path $manifestPath -Value $manifest -Encoding UTF8

    $notes = @"
# AOP Desktop Windows Release Notes

- Version: $Version
- Generated: $(Get-Date -Format s)
- MSI:
$($MsiFiles | ForEach-Object { "  - $($_.Name)" } | Out-String)

## Known limitations

- Windows is the primary supported packaging target right now.
- macOS packaging is intentionally deferred.
- Streamlit dashboard still exists as compatibility/debug UI.

## First-run notes

- Review Setup first if required blockers appear.
- Finish one Provider path before the first Run.
- Register a Project folder before launching a workflow.
"@
    Set-Content -Path $notesPath -Value $notes.Trim() -Encoding UTF8
}

Write-Step "Checking Windows desktop release prerequisites"
Assert-Command -CommandName "node" -InstallHint "Install Node.js LTS first."
Assert-Command -CommandName "npm" -InstallHint "Install npm with Node.js."
Assert-Command -CommandName "cargo" -InstallHint "Install Rust/Cargo with rustup."
Assert-Command -CommandName "python" -InstallHint "Install Python so the AOP sidecar can run."

$effectiveVersion = if ($ReleaseVersion) { $ReleaseVersion } else { Get-DesktopVersion }
$releaseDir = Join-Path $releaseRoot $effectiveVersion

Write-Step "Release version: $effectiveVersion"

if ($WhatIf) {
    Write-Host "[WhatIf] release output directory: $releaseDir" -ForegroundColor Yellow
}
else {
    New-Item -ItemType Directory -Path $releaseDir -Force | Out-Null
}

if (-not $SkipInstall) {
    Write-Step "Installing desktop npm dependencies"
    Invoke-Step -Command "npm install" -WorkingDirectory $desktopDir
}

Write-Step "Building desktop frontend"
Invoke-Step -Command "npm run build" -WorkingDirectory $desktopDir

Write-Step "Building Windows MSI via Tauri"
Invoke-Step -Command "npm run tauri -- build --bundles msi" -WorkingDirectory $desktopDir

Write-Step "Build completed"
Write-Host "Expected MSI output directory: $bundleDir" -ForegroundColor Green

if (Test-Path $bundleDir) {
    $msiFiles = Get-ChildItem -Path $bundleDir -Filter *.msi
    foreach ($msi in $msiFiles) {
        if ($WhatIf) {
            Write-Host "[WhatIf] stage MSI to $(Join-Path $releaseDir $msi.Name)" -ForegroundColor Yellow
        }
        else {
            Copy-Item -Path $msi.FullName -Destination (Join-Path $releaseDir $msi.Name) -Force
        }
        Write-Host "MSI: $($msi.FullName)" -ForegroundColor Green
    }
    if (-not $WhatIf -and $msiFiles.Count -gt 0) {
        Write-ReleaseManifest -Version $effectiveVersion -ReleaseDirectory $releaseDir -MsiFiles $msiFiles
        Write-Host "Release manifest: $(Join-Path $releaseDir 'release-manifest.json')" -ForegroundColor Green
        Write-Host "Release notes template: $(Join-Path $releaseDir 'release-notes-template.md')" -ForegroundColor Green
    }
}
else {
    Write-Host "MSI output directory was not found yet: $bundleDir" -ForegroundColor Yellow
}

if (-not $WhatIf) {
    Write-Host "Staged release directory: $releaseDir" -ForegroundColor Green
}
