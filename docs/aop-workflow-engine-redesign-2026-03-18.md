# AOP Workflow Engine Redesign

Date: 2026-03-18

## Why this document exists

AOP already has strong building blocks:

- `src/aop/agent/driver.py` implements an end-to-end sprint flow
- `src/aop/agent/orchestrator.py` implements richer execution orchestration
- `src/aop/review/two_stage.py` implements spec-first and quality review
- `src/aop/state/manager.py` persists cross-session state into `.aop/STATE.md`
- `src/aop/dashboard/app.py` exposes the platform through a usable UI

The problem is not lack of features. The problem is that workflow ownership is split across multiple layers, which makes behavior inconsistent, hard to reason about, and difficult to evolve.

This redesign proposes a single internal workflow engine that turns AOP's current capabilities into a stricter and more inspectable execution loop.

## Additional external input

This redesign also aligns with two external references reviewed during planning:

- LangChain's harness engineering guidance
- Anthropic's multi-agent research system article

The Anthropic article is especially useful for one practical point: the orchestrator should not merely split work, it should delegate with a strong task contract. In AOP terms, that means planned work items should carry explicit:

- objective
- output format
- tool guidance
- boundaries
- effort budget

These fields help AOP decide when parallelism is worth it, improve subagent quality, and reduce wasteful execution loops.

## Current implementation map

### 1. AgentDriver is the user-facing workflow spine

`src/aop/agent/driver.py` currently drives this flow:

1. Clarify requirement
2. Generate hypotheses
3. Decompose tasks
4. Execute tasks
5. Validate hypotheses
6. Extract learnings
7. Persist state and summarize

Strengths:

- Clear high-level lifecycle
- Already integrates clarifier, hypothesis generation, validation, and learning
- Already writes useful sprint artifacts

Limitations:

- The "plan" phase is mostly implicit
- Task decomposition is not treated as a first-class persisted artifact
- Execution, verification, and repair loops are tightly coupled
- Completion can happen without a strong goal-backward verification gate

### 2. AgentOrchestrator is a richer but parallel workflow center

`src/aop/agent/orchestrator.py` includes:

- preflight validation
- codebase analysis
- task scheduling
- dynamic timeouts
- error recovery
- LLM-as-judge evaluation
- knowledge base integration
- checkpointing

Strengths:

- Better harness engineering than `AgentDriver`
- More production-grade execution support
- Better hooks for resilience and introspection

Limitations:

- It is not the canonical workflow engine for the whole product
- Workflow semantics are mixed with execution semantics
- Planning, execution, and recovery are orchestrated procedurally rather than through explicit phase contracts

### 3. State, memory, and review are useful but loosely coupled

`src/aop/state/manager.py` gives AOP a good cross-session digest. `src/aop/review/two_stage.py` already models a high-value review pattern. Legacy workflow modules under `src/aop/workflow/` still provide hypothesis, learning, and team abstractions.

Limitations:

- These modules do not currently enforce workflow gates
- Artifacts are scattered across state files, sprint persistence, and ad hoc execution outputs
- The dashboard can display workflow state, but it is not rendering one unified run model

## Key limitations in the current architecture

### 1. No single source of truth for workflow state

There are at least three overlapping workflow narratives:

- sprint lifecycle in `AgentDriver`
- execution lifecycle in `AgentOrchestrator`
- project memory and `.aop/STATE.md` digests

This leads to drift between what the system did, what the UI shows, and what the memory files claim.

### 2. Planning is under-modeled

AOP talks about hypotheses and decomposition, but it does not persist a robust execution plan with:

- scope
- intended file touch set
- dependencies
- verification strategy
- out-of-scope declarations
- risk checks

This makes it harder to audit execution quality and reason about regressions.

### 3. Verification is too close to execution details

The platform validates hypotheses, but it does not consistently answer the more important question:

"Did we actually solve the user's goal in a way that can be trusted?"

This is where goal-backward verification and explicit gap closure are still thin.

### 4. Repair loops are ad hoc

The codebase has retries, recovery, and validation, but not a first-class:

- gap capture
- repair planning
- targeted re-execution
- re-verification

loop.

### 5. Dashboard and CLI have to understand too many layers

Because the workflow contract is not centralized, the CLI and dashboard need to compensate by coordinating multiple subsystems directly.

### 6. Historical layering is becoming product debt

Older modules in `src/aop/workflow/` still carry useful ideas, but they no longer define the actual runtime shape of the system. This increases cognitive load for contributors and future agents.

## Design goals

The redesign should:

1. Keep AOP's product framing: `idea -> hypothesis -> prototype -> validation`
2. Introduce a stricter internal runtime: `clarify -> plan -> execute -> verify -> gap-close -> learn`
3. Reuse existing modules instead of replacing them wholesale
4. Persist workflow artifacts as first-class files under `.aop/`
5. Make completion conditional on explicit verification
6. Give the dashboard and CLI one canonical run model to display

## Proposed architecture

### Canonical runtime: Workflow Engine

Add a new workflow engine layer that owns the lifecycle of a run. This engine should not replace executors or providers. It should sit above them and define the contract between phases.

Suggested package:

- `src/aop/workflow/engine.py`
- `src/aop/workflow/types.py`
- `src/aop/workflow/artifacts.py`
- `src/aop/workflow/checks.py`

### New internal phases

Each run should move through these phases:

1. `clarify`
2. `plan`
3. `execute`
4. `verify`
5. `gap_close`
6. `learn`
7. `complete`

This phase model should be reflected in code, persisted artifacts, and state summaries.

### Run artifact model

For each workflow run, persist artifacts under:

`.aop/runs/<run_id>/`

Recommended files:

- `RUN.md`
- `PLAN.md`
- `EXECUTION.md`
- `VERIFICATION.md`
- `GAPS.md`
- `LEARNINGS.md`
- `SUMMARY.md`

This gives AOP a stable handoff surface for:

- cross-session continuation
- dashboard rendering
- debugging
- human review
- future subagent collaboration

### Phase contracts

#### Clarify

Inputs:

- raw user intent
- project state
- existing memory and state digest

Outputs:

- clarified requirement
- success criteria
- constraints
- unresolved assumptions

#### Plan

Inputs:

- clarified requirement
- hypothesis set
- codebase analysis

Outputs:

- ordered work items
- file touch candidates
- dependencies
- verification plan
- explicit out-of-scope notes
- risk notes

#### Execute

Inputs:

- approved plan
- selected executor and provider

Outputs:

- execution traces
- changed files
- test and command results
- checkpoint summaries

#### Verify

Inputs:

- plan
- execution traces
- repository state
- review outputs

Outputs:

- truths
- evidence
- unmet requirements
- user-visible risks
- verdict: pass, partial, fail

#### Gap Close

Inputs:

- verification gaps

Outputs:

- targeted repair plan
- limited re-execution
- updated verification

#### Learn

Inputs:

- traces
- verification report
- repairs

Outputs:

- reusable learnings
- failure patterns
- harness improvements

## Component reuse plan

The redesign should reuse current modules as follows:

- `AgentDriver`
  - becomes a thin entrypoint and compatibility facade
- `AgentOrchestrator`
  - remains the execution harness behind the `execute` phase
- `TwoStageReviewer`
  - becomes a standard verifier inside the `verify` phase
- `StateManager`
  - remains the cross-session digest writer fed from run artifacts
- `CodebaseAnalyzer`, `TaskScheduler`, `KnowledgeBase`, `LLMEvaluator`
  - become tools used by specific phases rather than alternate workflow centers

## New foundational types

Add workflow-native types:

- `WorkflowPhase`
- `WorkflowRun`
- `WorkflowPlan`
- `WorkflowTask`
- `VerificationReport`
- `GapItem`
- `LearningReport`

Planned task contracts should also make delegation explicit:

- objective
- output format
- tool guidance
- boundaries
- effort budget

Important property:

These types should be plain dataclasses first. The goal is to create a stable contract before doing deeper refactors.

## New workflow gates

### Plan Checker

Before execution starts, require a lightweight plan check:

- are success criteria covered
- are file targets plausible
- are dependencies ordered
- is verification defined
- is out-of-scope documented
- does each delegated task have a clear objective and output contract
- are boundaries and effort budgets explicit enough to avoid agent sprawl

### Completion Gate

Before marking a run complete, require:

- verification report exists
- required checks were run or explicitly skipped
- unresolved gaps are documented
- next-step guidance is present if not fully complete

### Loop Detection

Track repeated failure patterns such as:

- same file changed too many times in one run
- same failing command repeated
- same unresolved requirement repeated across repair cycles

When triggered, the engine should reconsider plan quality instead of blindly continuing.

## Dashboard implications

The dashboard should evolve from "showing tool outputs" to "showing workflow artifacts".

That means future views can be organized around:

- current phase
- plan checklist
- verification verdict
- unresolved gaps
- learnings

This also creates a cleaner path to multi-agent or team-style collaboration, because every participant can anchor on the same run folder.

## Implementation strategy

### Phase 1: Foundation

Add workflow types and artifact persistence without changing the whole engine.

Deliverables:

- workflow dataclasses
- run directory creation
- markdown artifact writing
- compatibility helper for current `AgentDriver`

### Phase 2: Plan and verification become explicit

Make `AgentDriver` generate a first-class plan artifact before execution, and write a verification artifact after execution.

Deliverables:

- `PLAN.md`
- `VERIFICATION.md`
- completion gate based on verification presence

### Phase 3: Gap closure loop

Add repair planning and targeted re-execution driven by verification gaps.

Deliverables:

- `GAPS.md`
- bounded repair cycles
- re-verification step

### Phase 4: Unify orchestrator ownership

Move execution semantics under the new workflow engine and shrink direct workflow logic in `AgentDriver`.

### Phase 5: Dashboard and CLI convergence

Refactor CLI and dashboard to read the same workflow run model.

## Recommended first implementation slice

The first slice should be intentionally modest:

1. add workflow types
2. add artifact manager for `.aop/runs/<run_id>/`
3. teach `AgentDriver` to persist a real `PLAN.md`
4. teach `AgentDriver` to persist a real `VERIFICATION.md`
5. add tests for artifact creation and phase summaries

This creates immediate value while keeping risk low.

## Risks

1. Over-refactoring too early

If we try to merge `AgentDriver`, `AgentOrchestrator`, dashboard, and CLI in one pass, we will destabilize the product.

2. Documentation without enforcement

If we only write more markdown files without phase gates, the system will accumulate more artifacts but not more reliability.

3. Backward compatibility drift

Existing commands and tests may rely on current result shapes, so the first slices should extend current structures rather than replace them.

## Success criteria for this redesign

We should consider the redesign successful when:

1. every run has a stable run directory with inspectable artifacts
2. planning is explicit and reviewable before execution
3. verification can explain whether the user's goal was actually met
4. gap closure is bounded and intentional
5. dashboard and CLI read from the same workflow record
6. future agents can resume work from artifacts instead of reverse-engineering runtime state
