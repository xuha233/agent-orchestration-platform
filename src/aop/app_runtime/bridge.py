"""Simple JSON bridge for desktop app experiments."""

from __future__ import annotations

from typing import Any, Dict

from .service import DesktopAppService


class DesktopAppBridge:
    """Dispatch simple desktop bridge actions."""

    def __init__(self, service: DesktopAppService | None = None) -> None:
        self.service = service or DesktopAppService()

    def dispatch(self, action: str, payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
        """Execute one bridge action and return JSON-serializable data."""
        data = payload or {}
        if action == "health":
            return {"ok": True, "data": self.service.get_app_health().to_dict()}
        if action == "projects":
            return {
                "ok": True,
                "data": [project.to_dict() for project in self.service.list_projects()],
            }
        if action == "providers":
            return {
                "ok": True,
                "data": [provider.to_dict() for provider in self.service.get_provider_status()],
            }
        if action == "settings":
            return {"ok": True, "data": self.service.get_settings()}
        if action == "runs":
            project_id = str(data.get("project_id", "")).strip()
            runs = self.service.list_runs(project_id=project_id, limit=int(data.get("limit", 12)))
            return {
                "ok": True,
                "data": [run.__dict__ for run in runs],
            }
        if action == "run_detail":
            project_id = str(data.get("project_id", "")).strip()
            run_id = str(data.get("run_id", "")).strip()
            detail = self.service.get_run_detail(project_id=project_id, run_id=run_id)
            if detail is None:
                return {"ok": False, "error": "run_not_found"}
            return {
                "ok": True,
                "data": {
                    "summary": detail.summary.__dict__,
                    "artifacts": [artifact.__dict__ for artifact in detail.artifacts],
                },
            }
        if action == "update_provider":
            provider_id = str(data.get("provider_id", "")).strip()
            if not provider_id:
                return {"ok": False, "error": "provider_id_required"}
            env_values = data.get("env_values", {})
            if not isinstance(env_values, dict):
                return {"ok": False, "error": "env_values_must_be_object"}
            preferred = bool(data.get("preferred", False))
            status = self.service.update_provider_config(
                provider_id=provider_id,
                env_values={str(key): str(value) for key, value in env_values.items()},
                preferred=preferred,
            )
            if status is None:
                return {"ok": False, "error": "provider_not_found"}
            return {"ok": True, "data": status.to_dict()}
        if action == "start_run":
            project_id = str(data.get("project_id", "")).strip()
            prompt = str(data.get("prompt", ""))
            try:
                result = self.service.start_run(project_id=project_id, prompt=prompt)
            except ValueError as error:
                return {"ok": False, "error": str(error)}
            return {"ok": True, "data": result.to_dict()}
        return {"ok": False, "error": f"unknown_action:{action}"}
