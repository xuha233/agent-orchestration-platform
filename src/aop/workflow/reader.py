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
    attention_tags: List[str] = field(default_factory=list)
    priority_rank: int = 0
    triage_summary: str = ""
    triage_evidence: List[str] = field(default_factory=list)


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
        run_dirs.sort(key=lambda path: (self._sort_key(path), path.name), reverse=True)

        for run_dir in run_dirs[:limit]:
            summary = self.load_run(run_dir.name)
            if summary is not None:
                runs.append(summary)
        return self._annotate_runs(runs)

    def get_latest_run(self) -> Optional[WorkflowRunSummary]:
        """Return the latest workflow run if present."""
        runs = self.list_runs()
        return runs[0] if runs else None

    def load_run(self, run_id: str) -> Optional[WorkflowRunSummary]:
        """Load a single workflow run summary."""
        run_dir = self.runs_dir / run_id
        run_payload = self._read_json(run_dir / "run.json")
        if not run_payload:
            return None

        verification_payload = self._read_json(run_dir / "verification.json") or {}
        completion_payload = self._read_json(run_dir / "completion.json") or {}
        plan_check_payload = self._read_json(run_dir / "plan_check.json") or {}
        guardrail_payload = self._read_json(run_dir / "guardrails.json") or {}
        gap_payload = self._read_json(run_dir / "gap_closure.json") or {}

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
            triage_evidence=self._triage_evidence(
                verification_payload=verification_payload,
                completion_payload=completion_payload,
                plan_check_payload=plan_check_payload,
                guardrail_payload=guardrail_payload,
                gap_payload=gap_payload,
            ),
        )

    def load_run_detail(self, run_id: str) -> Optional[WorkflowRunDetail]:
        """Load a run summary together with its artifact documents."""
        summary = next((run for run in self.list_runs() if run.run_id == run_id), None)
        if summary is None:
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

    def _annotate_runs(self, runs: List[WorkflowRunSummary]) -> List[WorkflowRunSummary]:
        """Apply desktop triage labels to workflow summaries."""
        clean_streak = 0
        annotated: List[WorkflowRunSummary] = []
        prior_unresolved = False

        for run in reversed(runs):
            tags, triage_summary = self._classify_run(run, clean_streak, prior_unresolved)
            if "needs_follow_up" in tags or "flaky" in tags:
                clean_streak = 0
            elif "stable" in tags or "fresh" in tags:
                clean_streak += 1
            else:
                clean_streak = 0

            run.attention_tags = tags
            run.priority_rank = self._priority_for_tags(tags)
            run.triage_summary = triage_summary
            annotated.append(run)
            prior_unresolved = "needs_follow_up" in tags

        annotated.reverse()
        return annotated

    def _classify_run(
        self,
        run: WorkflowRunSummary,
        prior_clean_streak: int,
        prior_unresolved: bool,
    ) -> tuple[List[str], str]:
        """Classify one run into triage tags."""
        completion = (run.completion_status or "").lower()
        verdict = (run.verification_verdict or "").lower()
        status = (run.status or "").lower()

        unresolved = (
            run.has_gaps
            or run.has_guardrails
            or status not in {"completed", "success"}
            or completion in {"needs_follow_up", "partial", "failed"}
            or verdict in {"partial", "fail", "failed"}
        )
        clean = (
            status == "completed"
            and completion == "completed"
            and not run.has_gaps
            and not run.has_guardrails
            and verdict in {"", "pass", "passed"}
        )

        if unresolved:
            tags = ["needs_follow_up"]
            reasons: List[str] = []
            if run.has_guardrails:
                reasons.append("guardrails were triggered")
            if run.has_gaps:
                reasons.append("verification still has gaps")
            if verdict in {"partial", "fail", "failed"}:
                reasons.append("verification did not pass")
            if status not in {"completed", "success"}:
                reasons.append("run did not complete cleanly")
            if run.has_guardrails or verdict in {"partial", "fail", "failed"} or prior_clean_streak > 0 or prior_unresolved:
                tags.append("flaky")
            if "flaky" in tags and prior_unresolved:
                return tags, "Repeated unresolved runs suggest this workflow path is flaky."
            if reasons:
                return tags, f"Needs follow-up because {'; '.join(reasons[:2])}."
            return tags, "Needs follow-up because the run still has unresolved workflow pressure."

        if clean:
            if prior_clean_streak >= 2:
                return ["stable"], "Three clean runs in a row suggest this workflow is stable."
            return ["fresh"], "This run is clean, but it still needs more repetition before it becomes stable."

        return ["flaky"], "Run state changed in a non-clean way and should be watched for instability."

    def _priority_for_tags(self, tags: List[str]) -> int:
        if "needs_follow_up" in tags:
            return 100
        if "flaky" in tags:
            return 80
        if "fresh" in tags:
            return 50
        if "stable" in tags:
            return 20
        return 0

    def _triage_evidence(
        self,
        *,
        verification_payload: Dict[str, Any],
        completion_payload: Dict[str, Any],
        plan_check_payload: Dict[str, Any],
        guardrail_payload: Dict[str, Any],
        gap_payload: Dict[str, Any],
    ) -> List[str]:
        evidence: List[str] = []

        verdict = str(verification_payload.get("verdict", "") or "")
        if verdict:
            evidence.append(f"verification verdict: {verdict}")

        for gap in list(verification_payload.get("gaps", []) or [])[:2]:
            if gap:
                evidence.append(f"gap: {gap}")

        completion_status = str(completion_payload.get("status", "") or "")
        if completion_status:
            evidence.append(f"completion: {completion_status}")

        for reason in list(completion_payload.get("reasons", []) or [])[:2]:
            if reason:
                evidence.append(f"completion reason: {reason}")

        for reason in list(guardrail_payload.get("reasons", []) or [])[:2]:
            if reason:
                evidence.append(f"guardrail: {reason}")

        for category in list(guardrail_payload.get("categories", []) or [])[:2]:
            if category:
                evidence.append(f"guardrail category: {category}")

        issues = list(plan_check_payload.get("issues", []) or [])
        for issue in issues[:2]:
            message = issue.get("message", "") if isinstance(issue, dict) else ""
            severity = issue.get("severity", "") if isinstance(issue, dict) else ""
            if message:
                prefix = f"plan {severity}" if severity else "plan"
                evidence.append(f"{prefix}: {message}")

        for step in list(gap_payload.get("next_verification_steps", []) or [])[:2]:
            if step:
                evidence.append(f"next step: {step}")

        return evidence[:6]

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
