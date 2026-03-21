"""Filesystem-backed desktop run job persistence."""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from .models import DesktopRunJob


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class DesktopRunJobStore:
    """Persist async desktop run jobs under the local AOP home."""

    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir
        self.jobs_dir = base_dir / "desktop-jobs"
        self.jobs_dir.mkdir(parents=True, exist_ok=True)

    def create_job(self, project_id: str, prompt: str) -> DesktopRunJob:
        """Create a queued job entry and persist it."""
        now = _utc_now()
        job = DesktopRunJob(
            job_id=f"job-{uuid4().hex[:12]}",
            project_id=project_id,
            prompt=prompt,
            status="queued",
            created_at=now,
            updated_at=now,
        )
        self.save_job(job)
        return job

    def get_job(self, job_id: str) -> DesktopRunJob | None:
        """Load one persisted job if present."""
        path = self.jobs_dir / f"{job_id}.json"
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            return None
        if not isinstance(payload, dict):
            return None
        return DesktopRunJob(
            job_id=str(payload.get("job_id", "")),
            project_id=str(payload.get("project_id", "")),
            prompt=str(payload.get("prompt", "")),
            status=str(payload.get("status", "unknown")),
            created_at=str(payload.get("created_at", "")),
            updated_at=str(payload.get("updated_at", "")),
            sprint_id=str(payload.get("sprint_id", "")),
            summary=str(payload.get("summary", "")),
            state=str(payload.get("state", "")),
            next_steps=[str(item) for item in payload.get("next_steps", []) if str(item)],
            error=str(payload.get("error", "")),
        )

    def save_job(self, job: DesktopRunJob) -> DesktopRunJob:
        """Persist one job and return the saved model."""
        updated = replace(job, updated_at=_utc_now())
        path = self.jobs_dir / f"{updated.job_id}.json"
        path.write_text(
            json.dumps(updated.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return updated
