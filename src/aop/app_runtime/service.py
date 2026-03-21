"""Service layer for the future desktop app bridge."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Optional

from aop import __version__
from aop.agent.driver import AgentDriver
from aop.agent.types import AgentDriverConfig
from aop.core.adapter import get_adapter_registry
from aop.core.compat import get_platform_detector
from aop.primary import get_registry
from aop.primary.workspace import SettingsManager, WorkspaceManager
from aop.workflow import WorkflowRunDetail, WorkflowRunReader, WorkflowRunSummary

from .config_store import DesktopConfigStore
from .models import (
    DesktopAppHealth,
    DesktopProjectSummary,
    DesktopProviderStatus,
    DesktopRunLaunchResult,
)


PROVIDER_ENV_VARS: Dict[str, List[str]] = {
    "claude": [],
    "codex": ["OPENAI_API_KEY"],
    "gemini": ["GOOGLE_API_KEY"],
    "opencode": [],
    "qwen": ["DASHSCOPE_API_KEY"],
}

PROVIDER_LABELS: Dict[str, str] = {
    "claude": "Claude Code",
    "codex": "Codex",
    "gemini": "Gemini",
    "opencode": "OpenCode",
    "qwen": "Qwen",
}


class DesktopAppService:
    """High-level read model for desktop app surfaces."""

    def __init__(
        self,
        workspace_manager: WorkspaceManager | None = None,
        settings_manager: SettingsManager | None = None,
        config_store: DesktopConfigStore | None = None,
    ) -> None:
        self.workspace_manager = workspace_manager or WorkspaceManager()
        self.settings_manager = settings_manager or SettingsManager()
        self.config_store = config_store or DesktopConfigStore()

    def get_app_health(self) -> DesktopAppHealth:
        """Return a lightweight runtime summary for the desktop shell."""
        platform_info = get_platform_detector().get_platform_info()
        agents = get_registry().list_available()
        providers = [status for status in self.get_provider_status() if status.detected]
        workspaces = self.workspace_manager.list_workspaces()
        return DesktopAppHealth(
            version=__version__,
            platform=platform_info["platform"],
            workspace_count=len(workspaces),
            available_agents=len(agents),
            available_providers=len(providers),
        )

    def list_projects(self) -> List[DesktopProjectSummary]:
        """Return desktop-friendly project summaries."""
        projects: List[DesktopProjectSummary] = []
        for workspace in self.workspace_manager.list_workspaces():
            latest_run = self._load_latest_run(workspace.project_path)
            projects.append(
                DesktopProjectSummary(
                    project_id=workspace.id,
                    name=workspace.name,
                    project_path=workspace.project_path,
                    primary_agent=workspace.primary_agent,
                    last_active=workspace.last_active,
                    session_id=workspace.session_id,
                    latest_run_id=latest_run.run_id if latest_run else "",
                    latest_run_status=latest_run.status if latest_run else "",
                    latest_run_phase=latest_run.current_phase if latest_run else "",
                    latest_run_completion=latest_run.completion_status if latest_run else "",
                    needs_follow_up=(
                        bool(latest_run)
                        and (
                            latest_run.status != "completed"
                            or latest_run.has_gaps
                            or latest_run.has_guardrails
                        )
                    ),
                )
            )
        return projects

    def get_project(self, project_id: str) -> Optional[DesktopProjectSummary]:
        """Return one project summary if present."""
        return next(
            (project for project in self.list_projects() if project.project_id == project_id),
            None,
        )

    def list_runs(self, project_id: str, limit: int = 12) -> List[WorkflowRunSummary]:
        """Return recent runs for a project."""
        workspace = self.workspace_manager.get_workspace(project_id)
        if workspace is None:
            return []
        return WorkflowRunReader(Path(workspace.project_path)).list_runs(limit=limit)

    def get_run_detail(self, project_id: str, run_id: str) -> Optional[WorkflowRunDetail]:
        """Return artifact detail for a specific workflow run."""
        workspace = self.workspace_manager.get_workspace(project_id)
        if workspace is None:
            return None
        return WorkflowRunReader(Path(workspace.project_path)).load_run_detail(run_id)

    def get_provider_status(self) -> List[DesktopProviderStatus]:
        """Return provider availability and config state."""
        detector = get_platform_detector()
        install_commands = detector.get_provider_install_commands()
        runtime_config = self.config_store.load()
        preferred_provider = str(runtime_config.get("preferred_provider", "") or "")
        stored_provider_envs = runtime_config.get("provider_envs", {})
        statuses: List[DesktopProviderStatus] = []

        for provider_id, adapter in get_adapter_registry().items():
            presence = adapter.detect()
            required_env_vars = list(PROVIDER_ENV_VARS.get(provider_id, []))
            stored_env_vars = stored_provider_envs.get(provider_id, {})
            if not isinstance(stored_env_vars, dict):
                stored_env_vars = {}
            configured_env_vars = [
                var_name
                for var_name in required_env_vars
                if os.environ.get(var_name) or stored_env_vars.get(var_name)
            ]
            missing_env_vars = [
                var_name for var_name in required_env_vars if var_name not in configured_env_vars
            ]
            statuses.append(
                DesktopProviderStatus(
                    provider_id=provider_id,
                    label=PROVIDER_LABELS.get(provider_id, provider_id.title()),
                    detected=presence.detected,
                    auth_ok=presence.auth_ok,
                    binary_path=presence.binary_path,
                    version=presence.version,
                    reason=presence.reason,
                    install_commands=list(install_commands.get(provider_id, [])),
                    required_env_vars=required_env_vars,
                    configured_env_vars=configured_env_vars,
                    missing_env_vars=missing_env_vars,
                    stored_env_vars={key: str(value) for key, value in stored_env_vars.items()},
                    preferred=provider_id == preferred_provider,
                )
            )
        return statuses

    def get_settings(self) -> Dict[str, object]:
        """Return the minimal settings needed by the desktop MVP."""
        settings = self.settings_manager.load()
        runtime_config = self.config_store.load()
        return {
            "primary_agent": settings.get("primary_agent"),
            "enable_mem0_memory": settings.get("enable_mem0_memory", False),
            "show_dev_console": settings.get("show_dev_console", False),
            "preferred_provider": runtime_config.get("preferred_provider", ""),
        }

    def update_provider_config(
        self,
        provider_id: str,
        env_values: Dict[str, str] | None = None,
        preferred: bool = False,
    ) -> DesktopProviderStatus | None:
        """Persist desktop-side provider config and return refreshed status."""
        if env_values:
            self.config_store.update_provider(provider_id, env_values)
        if preferred:
            self.config_store.set_preferred_provider(provider_id)
        return next(
            (status for status in self.get_provider_status() if status.provider_id == provider_id),
            None,
        )

    def start_run(self, project_id: str, prompt: str) -> DesktopRunLaunchResult:
        """Run one AOP workflow from the desktop shell."""
        workspace = self.workspace_manager.get_workspace(project_id)
        if workspace is None:
            raise ValueError(f"workspace_not_found:{project_id}")

        clean_prompt = prompt.strip()
        if not clean_prompt:
            raise ValueError("prompt_required")

        project_path = Path(workspace.project_path)
        if not project_path.exists():
            raise ValueError(f"project_path_missing:{project_path}")

        runtime_config = self.config_store.load()
        preferred_provider = str(runtime_config.get("preferred_provider", "") or "").strip()
        providers = self._build_provider_priority(preferred_provider)
        orchestrator_type = self._resolve_orchestrator_type(preferred_provider)

        driver = AgentDriver(
            config=AgentDriverConfig(
                orchestrator_type=orchestrator_type,
                providers=providers,
                storage_path=project_path / ".aop",
            )
        )
        result = driver.run_from_vague_description(clean_prompt)
        return DesktopRunLaunchResult(
            project_id=project_id,
            sprint_id=result.sprint_id,
            success=result.success,
            state=result.state.value if hasattr(result.state, "value") else str(result.state),
            summary=result.summary,
            next_steps=list(result.next_steps),
        )

    def _load_latest_run(self, project_path: str) -> WorkflowRunSummary | None:
        path = Path(project_path)
        if not path.exists():
            return None
        return WorkflowRunReader(path).get_latest_run()

    def _build_provider_priority(self, preferred_provider: str) -> List[str]:
        ordered: List[str] = []
        for provider_id in [preferred_provider, "claude", "codex", "opencode", "gemini", "qwen"]:
            if provider_id and provider_id not in ordered:
                ordered.append(provider_id)
        return ordered or ["claude", "codex"]

    def _resolve_orchestrator_type(self, preferred_provider: str) -> str:
        mapping = {
            "claude": "claude-code",
            "opencode": "opencode",
            "codex": "auto",
            "gemini": "api",
            "qwen": "api",
        }
        return mapping.get(preferred_provider, "auto")
