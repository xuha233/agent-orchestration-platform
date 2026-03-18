"""Read persisted workflow run artifacts."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


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
