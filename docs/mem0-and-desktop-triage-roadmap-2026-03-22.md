# AOP mem0 And Desktop Triage Roadmap

Last updated: 2026-03-22

## Why This Exists

AOP now has three strong but still loosely-coupled foundations:

- a workflow runtime with persisted run artifacts
- a desktop shell that can guide users through setup, projects, runs, and workflow review
- an experimental `mem0` integration for semantic memory

The next stage is to turn these into two product-level capabilities:

1. `mem0` becomes a first-class AOP memory layer instead of an optional prompt-only enhancement
2. Desktop becomes a real triage workbench with explicit project/run stability labels

This document is the working checklist for that stage.

## Priority Order

1. mem0 integration closure
2. Desktop triage labels and prioritization
3. Desktop memory UX
4. Windows release process cleanup
5. macOS build validation
6. legacy Streamlit dashboard downgrade

## Track A: mem0 Integration Closure

### Goals

- Make `mem0` a formal AOP memory subsystem
- Connect memory to workflow decisions, not just prompt hydration
- Keep file-memory fallback and backward compatibility

### Current State

- `MemoryService` already wraps file storage and `mem0`
- `MemoryMigrator` already supports file-to-mem0 migration
- `build_agent_system_prompt()` already loads `mem0` memories when enabled
- Dashboard and settings already expose an experimental `enable_mem0_memory` toggle
- Desktop runtime currently only exposes the boolean setting; it does not yet provide a memory workbench

### Problems To Solve

- memory is still mostly prompt-time context, not runtime decision input
- write points are not standardized across plan / verify / gap-close / learn
- CLI, settings, loader, and dashboard toggles are loosely coupled
- there is no clear desktop UX for memory readiness, inspection, or migration

### Implementation Plan

#### Phase A1: Policy and lifecycle definition

- Define canonical write triggers:
  - plan accepted
  - verification completed
  - gap closure created
  - guardrail stop reason emitted
  - learnings recorded
- Define canonical memory record classes:
  - project fact
  - workflow lesson
  - decision rationale
  - recurring failure pattern
  - follow-up directive

#### Phase A2: Runtime integration

- Inject memory retrieval into workflow runtime and coordinator at controlled checkpoints
- Add memory-backed context for:
  - planning
  - verification
  - follow-up prioritization
- Avoid loading large, unbounded memory blobs into every run

#### Phase A3: Desktop UX

- Add desktop memory readiness and configuration
- Add memory migration entry point
- Add memory status and recent-memory inspection

#### Phase A4: Cleanup

- Remove drift between:
  - `.aop/memory_config.yaml`
  - global settings toggle
  - dashboard toggle
  - desktop settings payload

## Track B: Desktop Triage Labels

### Goal

Adopt the most useful workflow lessons from `Do-It-Till-It-Works-Agent` without copying its heavy process ceremony.

### Labels

- `needs_follow_up`
- `flaky`
- `fresh`
- `stable`

### Initial Semantics

- `needs_follow_up`
  - latest run is unresolved
  - gaps exist, guardrails exist, or completion is not done
- `flaky`
  - recent run history shows instability or repeated follow-up pressure
  - guardrail-triggered runs should be treated as flaky by default
- `fresh`
  - run is currently clean but has not yet proven stability
- `stable`
  - clean run with enough recent clean history to be considered reliable

### Desktop Surfaces To Update

- project priority strip
- project cards
- workflow run list
- workflow compare view
- follow-up queue

### Next Step After Labels

- add evidence index so users can see why a project/run was labeled flaky or follow-up
- add configurable stabilization threshold, for example 2-3 clean runs before `stable`

## Immediate Implementation Slice

The first implementation slice should stay intentionally narrow:

1. add read-model labels and priority rank to workflow runs
2. surface those labels in desktop project and workflow views
3. use those labels for sorting and follow-up emphasis
4. do not yet add new persisted files or new workflow write paths

This keeps the first slice low-risk while establishing the language the rest of the product can build on.

## Follow-up Work After This Slice

- promote label logic from read-model heuristics to workflow runtime truth
- connect `mem0` and evidence index into triage decisions
- add desktop memory and triage drill-down views
- finalize Windows release workflow
- prepare macOS validation
