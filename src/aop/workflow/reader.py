"""Read persisted workflow run artifacts."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


DEFAULT_WORKFLOW_ARTIFACTS = (
    ("RUN.md", "RUN"),
    ("PLAN.md", "PLAN"),
    ("PLAN_CHECK.md", "PLAN CHECK"),
    ("EXECUTION.md", "EXECUTION"),
    ("VERIFICATION.md", "VERIFICATION"),
    ("GAPS.md", "GAPS"),
    ("GUARDRAILS.md", "GUARDRAILS"),
    ("LEARNINGS.md", "LEARNINGS"),
    ("COMPLETION.md", "COMPLETION"),
    ("SUMMARY.md", "SUMMARY"),
)


@dataclass
class WorkflowRunSummary:
    """Compact view of a persisted workflow run."""

    run_id: str
    status: str
    current_phase: str
    original_input: str = ""
    clarified_summary: str = ""
    success_criteria: List[str] = field(default_factory=list)
    hypothesis_ids: List[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    verification_verdict: str = ""
    completion_status: str = ""
    has_gaps: bool = False
    has_guardrails: bool = False


@dataclass
class WorkflowArtifactDocument:
    """Single artifact document for a workflow run."""

    filename: str
    title: str
    content: str = ""
    exists: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowRunDetail:
    """Expanded workflow run data including artifact contents."""

    summary: WorkflowRunSummary
    artifacts: List[WorkflowArtifactDocument] = field(default_factory=list)


class WorkflowRunReader:
    """Read workflow run state from `.aop/runs`."""

    def __init__(self, project_path: Path | str):
        base = Path(project_path)
        self.aop_dir = base if base.name == ".aop" else base / ".aop"
        self.runs_dir = self.aop_dir / "runs"

    def list_runs(self, limit: int | None = None) -> List[WorkflowRunSummary]:
        """List workflow runs ordered by updated timestamp descending."""
        if not self.runs_dir.exists():
            return []

        runs: List[WorkflowRunSummary] = []
        run_dirs = [path for path in self.runs_dir.iterdir() if path.is_dir()]
        run_dirs.sort(key=self._sort_key, reverse=True)

        for run_dir in run_dirs[:limit]:
            summary = self.load_run(run_dir.name)
            if summary is not None:
                runs.append(summary)
        return runs

    def get_latest_run(self) -> Optional[WorkflowRunSummary]:
        """Return the latest workflow run if present."""
        runs = self.list_runs(limit=1)
        return runs[0] if runs else None

    def load_run(self, run_id: str) -> Optional[WorkflowRunSummary]:
        """Load a single workflow run summary."""
        run_dir = self.runs_dir / run_id
        run_payload = self._read_json(run_dir / "run.json")
        if not run_payload:
            return None

        verification_payload = self._read_json(run_dir / "verification.json") or {}
        completion_payload = self._read_json(run_dir / "completion.json") or {}

        return WorkflowRunSummary(
            run_id=run_payload.get("run_id", run_id),
            status=run_payload.get("status", "unknown"),
            current_phase=run_payload.get("current_phase", "unknown"),
            original_input=run_payload.get("original_input", ""),
            clarified_summary=run_payload.get("clarified_summary", ""),
            success_criteria=list(run_payload.get("success_criteria", []) or []),
            hypothesis_ids=list(run_payload.get("hypothesis_ids", []) or []),
            created_at=run_payload.get("created_at", ""),
            updated_at=run_payload.get("updated_at", ""),
            verification_verdict=verification_payload.get("verdict", ""),
            completion_status=completion_payload.get("status", ""),
            has_gaps=(run_dir / "GAPS.md").exists(),
            has_guardrails=(run_dir / "GUARDRAILS.md").exists(),
        )

    def load_run_detail(self, run_id: str) -> Optional[WorkflowRunDetail]:
        """Load a run summary together with its artifact documents."""
        summary = self.load_run(run_id)
        if summary is None:
            return None
        return WorkflowRunDetail(
            summary=summary,
            artifacts=self.list_artifacts(run_id),
        )

    def list_artifacts(self, run_id: str) -> List[WorkflowArtifactDocument]:
        """Return ordered artifact documents for a workflow run."""
        run_dir = self.runs_dir / run_id
        if not run_dir.exists():
            return []

        metadata_by_filename = self._artifact_metadata(run_dir)
        artifacts: List[WorkflowArtifactDocument] = []
        for filename, title in DEFAULT_WORKFLOW_ARTIFACTS:
            path = run_dir / filename
            content = self._read_text(path)
            artifacts.append(
                WorkflowArtifactDocument(
                    filename=filename,
                    title=title,
                    content=content or "",
                    exists=path.exists() and bool(content),
                    metadata=metadata_by_filename.get(filename, {}),
                )
            )
        return artifacts

    def _artifact_metadata(self, run_dir: Path) -> Dict[str, Dict[str, Any]]:
        """Build structured summaries for artifact rendering."""
        plan_payload = self._read_json(run_dir / "plan.json") or {}
        plan_check_payload = self._read_json(run_dir / "plan_check.json") or {}
        execution_payload = self._read_json(run_dir / "execution.json") or {}
        verification_payload = self._read_json(run_dir / "verification.json") or {}
        gap_payload = self._read_json(run_dir / "gap_closure.json") or {}
        guardrail_payload = self._read_json(run_dir / "guardrails.json") or {}
        learnings_payload = self._read_json(run_dir / "learnings.json") or {}
        completion_payload = self._read_json(run_dir / "completion.json") or {}

        execution_results = list(execution_payload.get("results", []) or [])
        failed_results = [result for result in execution_results if not result.get("success")]

        return {
            "PLAN.md": {
                "goals": len(plan_payload.get("goals", []) or []),
                "tasks": len(plan_payload.get("tasks", []) or []),
                "verification_steps": len(plan_payload.get("verification_steps", []) or []),
                "risks": len(plan_payload.get("risks", []) or []),
            },
            "PLAN_CHECK.md": {
                "passed": plan_check_payload.get("passed"),
                "issues": len(plan_check_payload.get("issues", []) or []),
                "summary": plan_check_payload.get("summary", ""),
                "critical_issues": sum(
                    1 for issue in plan_check_payload.get("issues", []) or []
                    if issue.get("severity") == "critical"
                ),
                "important_issues": sum(
                    1 for issue in plan_check_payload.get("issues", []) or []
                    if issue.get("severity") == "important"
                ),
                "issue_details": [
                    issue.get("message", "")
                    for issue in (plan_check_payload.get("issues", []) or [])[:5]
                    if issue.get("message")
                ],
            },
            "EXECUTION.md": {
                "results": len(execution_results),
                "failed": len(failed_results),
                "repair_waves": sum(1 for result in execution_results if result.get("repair_wave")),
            },
            "VERIFICATION.md": {
                "verdict": verification_payload.get("verdict", ""),
                "truths": len(verification_payload.get("truths", []) or []),
                "gaps": len(verification_payload.get("gaps", []) or []),
                "checks": len(verification_payload.get("checks", []) or []),
                "gap_details": list(verification_payload.get("gaps", []) or [])[:5],
            },
            "GAPS.md": {
                "gaps": len(gap_payload.get("gaps", []) or []),
                "repair_tasks": len(gap_payload.get("repair_tasks", []) or []),
                "next_steps": len(gap_payload.get("next_verification_steps", []) or []),
                "summary": gap_payload.get("summary", ""),
            },
            "GUARDRAILS.md": {
                "should_stop": guardrail_payload.get("should_stop"),
                "categories": list(guardrail_payload.get("categories", []) or []),
                "reasons": len(guardrail_payload.get("reasons", []) or []),
                "reason_details": list(guardrail_payload.get("reasons", []) or [])[:5],
            },
            "LEARNINGS.md": {
                "records": len(learnings_payload.get("records", []) or []),
            },
            "COMPLETION.md": {
                "passed": completion_payload.get("passed"),
                "status": completion_payload.get("status", ""),
                "reasons": len(completion_payload.get("reasons", []) or []),
                "reason_details": list(completion_payload.get("reasons", []) or [])[:5],
                "summary": completion_payload.get("summary", ""),
            },
        }

    def _sort_key(self, run_dir: Path) -> datetime:
        payload = self._read_json(run_dir / "run.json") or {}
        updated_at = payload.get("updated_at") or payload.get("created_at")
        if isinstance(updated_at, str):
            try:
                return datetime.fromisoformat(updated_at)
            except ValueError:
                pass
        return datetime.min

    def _read_json(self, path: Path) -> Dict[str, Any] | None:
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            return None

    def _read_text(self, path: Path) -> str | None:
        if not path.exists():
            return None
        try:
            return path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return None
