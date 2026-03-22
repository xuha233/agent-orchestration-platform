# Desktop Build Readiness And Installer Plan

## Current validation status

As of March 22, 2026, the desktop frontend build is working, but native Tauri packaging is blocked on this machine by missing Rust tooling.

Validated:

- `npm run build` in `desktop/` succeeds
- AOP Python app runtime tests continue to pass

Blocked locally:

- `cargo --version` is unavailable
- `rustc --version` is unavailable
- Native `tauri build` cannot run until Rust is installed

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
- Keep secondary steps like `auth login` and API key setup as guided follow-up

Medium-term UX:

- Add a dedicated setup/settings area with:
  - Rust/Tauri readiness
  - Node/npm readiness
  - Python readiness
  - provider readiness
- Show actionable install buttons where safe

## Safety and scope of the current one-click install

The current implementation only targets the first install command for a provider, typically the package install step.

Examples:

- `npm install -g @openai/codex`
- `npm install -g @anthropic-ai/claude-code`
- `pip install google-generativeai`

It does not auto-run:

- auth/login steps
- API key export commands
- OS-level Rust or Xcode installation

Those remain guided follow-up steps in the UI.

## Next recommended work

1. Add explicit build-readiness checks for Rust, Node, and Python into the desktop bridge.
2. Create a dedicated Setup page instead of overloading Home and Providers.
3. Add safer installation helpers for non-provider prerequisites where possible.
4. Re-validate native Tauri build once Rust is installed on the target machine.
