# AOP Desktop App Migration Plan

Date: 2026-03-19

Status: Proposed and approved for implementation

## Why this document exists

AOP has reached the point where the current Streamlit dashboard is no longer the right primary product surface.

The core runtime is getting stronger:

- workflow artifacts are now first-class
- the driver/runtime/coordinator split is clearer
- the CLI and dashboard already read from a more unified workflow model

But the product shell is still optimized for a demo:

- the main UI still depends on a large Streamlit app
- startup and process management are fragile across platforms
- installation assumes Python and pip literacy
- the old dashboard contains too much historical UI debt to remain the main product surface

This document defines the next major update: migrate AOP toward an installable desktop application while preserving the Python workflow engine as the product core.

## Product direction

The next version of AOP should feel like a real local app:

- downloadable installer
- double-click to open
- guided interface
- workflow-first experience
- less exposure to Python, pip, Streamlit, and terminal setup

This is not a rewrite of the AOP engine. It is a shell, install, and UX migration around the existing runtime.

## Confirmed scope

### Desktop MVP must support

- run `aop run`
- view projects
- view workflow/artifacts
- configure providers

### Desktop MVP can defer

- complex settings pages
- lower-value legacy dashboard pages
- feature parity with every existing Streamlit view

### Platform priority

- Windows
- macOS

### Distribution priority

- primary: downloadable desktop installer
- secondary: keep developer-friendly CLI install paths

### Runtime choice

- accepted: local embedded Python runtime / sidecar

## Technology decision

### Recommended default: Tauri + Python sidecar

Tauri is the preferred shell for the next AOP phase.

Why:

- smaller install footprint than Electron
- better fit for a lightweight local productivity app
- strong cross-platform desktop story
- good long-term direction for a real product surface

### Fallback: Electron only if Tauri sidecar packaging becomes a blocker

Electron remains a valid backup if one of these becomes prohibitively expensive during the spike:

- packaging Python sidecars consistently on Windows and macOS
- smooth local process lifecycle management
- installer reliability

Current decision:

- default path: Tauri
- fallback path: Electron
- do not implement both in parallel

## Target architecture

The system should be split into three layers.

### 1. Desktop Shell

Proposed location:

- `desktop/`

Responsibilities:

- window shell
- navigation
- project picker
- run submission
- artifact browsing
- provider configuration
- onboarding and empty states

This layer should not directly understand legacy dashboard internals.

### 2. Local App Runtime

Proposed location:

- `src/aop/app_runtime/`

Responsibilities:

- spawn and supervise the local AOP runtime
- expose stable local APIs to the desktop shell
- manage project discovery
- invoke workflow runs
- surface workflow run summaries and details
- manage provider state/config status
- coordinate local logs and health checks

This layer becomes the canonical bridge between the desktop app and the Python engine.

### 3. AOP Core

Existing code reused here:

- workflow runtime
- workflow coordinator
- workflow artifacts and reader
- provider/orchestrator integration
- CLI-compatible execution paths

Responsibilities:

- business logic
- workflow semantics
- artifact generation
- verification and repair loops

This layer should continue to be usable without the desktop shell.

## Why the old Streamlit dashboard should stop being the primary shell

The current dashboard is still useful as a transition/debug tool, but it is not a good long-term app shell because:

- `src/aop/dashboard/app.py` is too large
- UI logic and app logic are too entangled
- cross-platform launch flows are brittle
- installation and startup remain too developer-oriented
- visual/product constraints of Streamlit are starting to fight the product direction

The Streamlit dashboard should transition to:

- compatibility/debug surface
- internal fallback UI
- migration reference during the desktop build

Not:

- the primary user-facing app

## Desktop MVP information architecture

The first desktop release should stay narrow and deliberate.

### Primary sections

1. Home
2. Projects
3. Run
4. Workflow
5. Providers

### Home

Should answer:

- what projects exist
- what needs follow-up
- what the latest workflow run is doing
- what the user should do next

### Projects

Should support:

- recent projects
- open/create project
- project state summary
- latest run summary

### Run

Should support:

- input box for new idea/task
- launch `aop run`
- show current run lifecycle
- show status, logs, and artifact progression

### Workflow

Should support:

- workflow run list
- artifact explorer
- risk summary
- follow-up queue
- run comparison

This view should reuse the artifact-first UX concepts already being built.

### Providers

Should support:

- provider availability
- install/setup guidance
- key presence/config status
- preferred provider selection

This should be simpler than the current settings mindset.

## Runtime bridge design

The desktop app should not shell out to arbitrary CLI commands from the frontend.

Instead, add a local runtime bridge with explicit operations.

Suggested capabilities:

- `get_app_health()`
- `list_projects()`
- `get_project(project_id)`
- `start_run(project_id, prompt, options)`
- `list_runs(project_id)`
- `get_run_detail(project_id, run_id)`
- `get_provider_status()`
- `update_provider_config(provider_id, payload)`

Possible transport options:

- local HTTP on loopback
- local IPC contract
- Tauri commands that call Python bridge processes

Recommendation for the spike:

- start with a minimal local HTTP bridge or explicit command bridge
- optimize later only if needed

## Installation and distribution strategy

The current install story is not friendly enough for the target audience.

Today, users effectively need to understand:

- Python
- pip
- editable installs
- optional dependencies
- CLI provider installs

That is too much.

### New primary path

Desktop installers:

- Windows installer
- macOS app bundle / installer

The default user path should be:

1. download
2. install
3. launch
4. configure provider
5. run first workflow

### Secondary paths that remain

1. Python package install for developers
2. npm bootstrap/install path if useful for agent-heavy users

### Recommended distribution tiers

#### Tier 1: End users

- native installer
- bundled runtime
- minimal setup

#### Tier 2: Builders and contributors

- `pip install ...`
- repo clone + dev setup

#### Tier 3: Agent-native users

- optional npm-based bootstrap or launcher

This avoids forcing one distribution model on every audience.

## Historical issues that must be included in the migration

This migration is also the right time to address specific product debt.

### Dashboard debt

- the main dashboard module is oversized
- legacy pages and workflow pages are mixed together
- state sources are still partially fragmented

### Startup/process debt

- dashboard launch uses fragile shell flows
- platform-specific startup commands are too string-heavy
- process lifecycle needs a cleaner ownership model

### Install debt

- current installation assumes technical users
- provider setup is not yet shaped like first-run onboarding
- optional dependencies need a clearer product story

### UX debt

- current experience is still too artifact/debug driven in some places
- onboarding and empty states need product-quality guidance
- many existing controls are still inherited from Streamlit-era constraints

## Migration phases

### Phase 1: Architecture and spike

Deliverables:

- this design document
- `desktop/` skeleton
- Tauri feasibility spike
- Python sidecar proof of concept
- runtime bridge shape

Exit criteria:

- desktop shell launches
- Python runtime can be started and queried locally
- one workflow read path works end-to-end

### Phase 2: Data bridge and project surfaces

Deliverables:

- project list
- project detail summary
- workflow run list
- artifact detail loading

Exit criteria:

- users can browse projects and workflow runs without Streamlit

### Phase 3: Run flow

Deliverables:

- run submission UI
- run lifecycle status
- streaming/progress model
- completion/follow-up UX

Exit criteria:

- users can start and observe a run from desktop UI

### Phase 4: Provider onboarding

Deliverables:

- provider detection
- configuration UI
- setup instructions
- first-run guidance

Exit criteria:

- first-time users can configure a provider without reading deep docs

### Phase 5: Packaging and installers

Deliverables:

- Windows packaging pipeline
- macOS packaging pipeline
- desktop install docs

Exit criteria:

- installable builds exist for both priority platforms

### Phase 6: Legacy dashboard downgrade

Deliverables:

- Streamlit dashboard repositioned as fallback/debug surface
- docs updated
- old entrypoints clarified

Exit criteria:

- desktop app is the primary recommended interface

## Immediate implementation plan

The next coding phase should start with these concrete steps:

1. create `desktop/` scaffold
2. decide frontend stack inside Tauri
3. create `src/aop/app_runtime/` bridge skeleton
4. expose minimal project/run/artifact APIs
5. wire one end-to-end desktop view for projects and workflow runs
6. keep the old dashboard untouched except for compatibility fixes

## Docs cleanup policy for this migration

The following kinds of docs are now obsolete and should be removed when replaced by desktop-era guidance:

- Streamlit-dashboard-only implementation plans
- old dashboard test reports tied to v0.4 behavior
- startup workaround notes tied to web-page-triggered agent startup

Reference reports that still help migration should remain, especially:

- workflow engine redesign
- UI tech debt notes
- cross-platform compatibility analysis

## Risks

### Risk 1: Tauri sidecar packaging complexity

Mitigation:

- do a spike first
- define Electron as explicit fallback

### Risk 2: Legacy dashboard logic still owns too much behavior

Mitigation:

- introduce `app_runtime` as a clean bridge
- do not wire desktop directly to Streamlit internals

### Risk 3: Packaging becomes the schedule bottleneck

Mitigation:

- separate shell/runtime MVP from installer hardening
- validate desktop app functionality before full packaging work

### Risk 4: Desktop MVP scope grows too wide

Mitigation:

- keep only run/projects/workflow/providers in phase 1 MVP
- defer complex settings and old utility pages

## Success criteria

This migration is successful when:

- AOP can be installed as a desktop app on Windows and macOS
- users can launch it without knowing Python or Streamlit
- users can configure a provider from the app
- users can start a run and inspect workflow artifacts from the app
- Streamlit is no longer the primary recommended product surface
