# Workflow UI Tech Debt

Date: 2026-03-18

## Scope

This note captures pre-existing issues discovered while wiring workflow-run artifacts into the CLI and dashboard. These are not all addressed in the current phase because they would expand the work far beyond the artifact-first UI goal.

## CLI

- `src/aop/cli/main.py` has multiple existing unused imports and dead local variables.
- Several existing `f""` strings do not interpolate values and should be normalized.
- The file is large and mixes unrelated command groups, which increases the cost of safe edits.

## Dashboard

- `src/aop/dashboard/app.py` is too large and owns too many unrelated concerns.
- The module has pre-existing lint issues, including unused imports, bare `except`, ambiguous variable names, and undefined names in lower sections.
- Importing the dashboard in bare mode triggers Streamlit runtime warnings, which are expected but make low-noise validation harder.
- Existing project-state sections still blend legacy sprint state, hypothesis files, and workspace data instead of using one canonical workflow-run model.

## Follow-up order

1. Keep extending artifact-first views without broad refactors.
2. Extract workflow reading/rendering helpers out of `dashboard/app.py`.
3. Split CLI workflow inspection into a dedicated module.
4. Clean historical lint issues in `cli/main.py` and `dashboard/app.py` once the workflow UX stabilizes.
