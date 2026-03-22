# Desktop Build Readiness And Installer Plan

## Current validation status

Updated on March 22, 2026:

Validated on Windows:

- `npm run build` in `desktop/` succeeds
- AOP Python app runtime tests continue to pass
- native `tauri build` has already succeeded on Windows
- Windows MSI output has been verified locally

Current packaging focus:

- standardize the Windows release flow
- make repeatable MSI generation easier for future iterations
- improve first-run installer and post-install guidance

## Required local prerequisites for native Tauri builds

Windows:

- Rust toolchain (`rustup`, `cargo`, `rustc`)
- Visual Studio C++ build tools when required by the Rust ecosystem
- Node/npm
- Python runtime for the AOP sidecar

macOS:

- Rust toolchain (`rustup`, `cargo`, `rustc`)
- Xcode command line tools
- Node/npm
- Python runtime for the AOP sidecar

## Product direction for installer UX

The desktop app should not assume users know how to install all dependencies manually.

Short-term desktop UX:

- Surface provider install commands directly in the app
- Allow one-click execution of the primary dependency install command
- Surface system dependency readiness in a dedicated Setup page
- Allow one-click execution of the primary install command for supported system tools
- Keep secondary steps like `auth login` and API key setup as guided follow-up

Medium-term UX:

- Expand Setup into a fuller settings workspace with:
  - Rust/Tauri readiness
  - Node/npm readiness
  - Python readiness
  - provider readiness
- Group blockers into required and optional sections
- Show actionable install buttons where safe

## Safety and scope of the current one-click install

The current implementation only targets the first install command for a provider, typically the package install step.

Examples:

- `npm install -g @openai/codex`
- `npm install -g @anthropic-ai/claude-code`
- `pip install google-generativeai`

It now supports safe first-step installs for some system dependencies as well, such as:

- `winget install Python.Python.3.11`
- `winget install OpenJS.NodeJS.LTS`
- `winget install Rustlang.Rustup`

It still does not auto-run:

- auth/login steps
- API key export commands
- OS-level Rust or Xcode installation

Those remain guided follow-up steps in the UI.

## Windows release workflow

Current helper:

- `desktop/scripts/build-windows-release.ps1`
- `npm run build:windows`

The helper currently standardizes:

- prerequisite checks
- optional npm install
- frontend build
- MSI bundle build
- final MSI output path reporting

## Next recommended work

1. Add version stamping and release notes guidance to the Windows release helper.
2. Improve the first-run Windows installer experience and post-install routing.
3. Prepare a lightweight Windows release checklist for repeatable local packaging.
4. Keep macOS validation deferred until the Windows release flow is fully comfortable.
