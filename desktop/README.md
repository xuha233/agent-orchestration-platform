# AOP Desktop

This directory contains the Windows-first desktop shell for AOP.

Current stack:

- shell: Tauri
- frontend: React + TypeScript
- backend bridge: `aop.app_runtime`

Current MVP surfaces:

- `Setup`
- `Providers`
- `Projects`
- `Run`
- `Workflow`
- `Memory`

The desktop app is no longer just a scaffold. It now supports:

- registering projects
- configuring providers
- launching desktop-driven runs
- inspecting workflow artifacts
- triaging follow-up work
- inspecting and migrating workflow memory

## Windows build

Use the packaged Windows build helper:

```powershell
npm run build:windows
```

Verify a staged Windows release:

```powershell
npm run verify:windows
```

Dry-run the release flow without invoking the heavy steps:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build-windows-release.ps1 -WhatIf
```

Expected prerequisites:

- Node.js + npm
- Rust/Cargo
- Python
- Windows build tooling needed by Tauri/Rust

Expected MSI output:

```text
desktop/src-tauri/target/release/bundle/msi/
```

Staged release output:

```text
releases/windows/<version>/
```

Each staged release now includes:

- the MSI copied from the Tauri bundle output
- `release-manifest.json`
- `release-notes-template.md`

See the release checklist here:

```text
docs/windows-release-checklist-2026-03-22.md
```

The Streamlit dashboard remains the compatibility/debug UI during migration.
