# Windows Release Checklist

Last updated: 2026-03-22

## Goal

Produce a repeatable Windows desktop release for AOP with:

- a verified frontend build
- a Tauri-generated MSI
- a staged release directory under `releases/windows/<version>/`

## Release command

From the repository root:

```powershell
cd desktop
npm run build:windows
```

Optional dry run:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build-windows-release.ps1 -WhatIf
```

Optional explicit version:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build-windows-release.ps1 -ReleaseVersion 0.1.0
```

Verify the staged release after build:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\verify-windows-release.ps1 -ReleaseVersion 0.1.0
```

## Prerequisites

- Node.js
- npm
- Python
- Rust/Cargo
- Windows-native Tauri build toolchain

Notes:

- the build helper auto-detects `~/.cargo/bin` if `cargo` is not already on `PATH`
- provider auth and API key setup are still handled in-app after install

## Output paths

Primary Tauri bundle output:

```text
desktop/src-tauri/target/release/bundle/msi/
```

Staged release directory:

```text
releases/windows/<version>/
```

Expected staged metadata:

```text
releases/windows/<version>/release-manifest.json
releases/windows/<version>/release-notes-template.md
```

## Manual checks before sharing

1. Open AOP Desktop on Windows.
2. Confirm `Setup` loads and shows local dependency status.
3. Confirm `Providers` loads and a preferred provider can be selected.
4. Confirm `Projects` can open an existing workspace.
5. Confirm `Run` opens without layout issues.
6. Confirm `Workflow` shows runs and artifact detail.
7. Confirm `Memory` shows settings, records, and migration controls.
8. Confirm `Follow-up workbench` appears on Home when follow-up projects exist.

## Release notes checklist

- Version number used
- MSI filename produced
- Release directory staged
- Release manifest present
- Release notes template present
- Known limitations
- Any required first-run setup notes

## Current known limitations

- Windows is the primary supported packaging target right now
- macOS packaging is intentionally deferred
- Streamlit dashboard still exists as compatibility/debug UI
