"""Service layer for the future desktop app bridge."""

from __future__ import annotations

import os
import subprocess
import sys
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
from .jobs import DesktopRunJobStore
from .models import (
    DesktopAppHealth,
    DesktopInstallResult,
    DesktopProjectSummary,
    DesktopProviderStatus,
    DesktopRunJob,
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
        job_store: DesktopRunJobStore | None = None,
    ) -> None:
        self.workspace_manager = workspace_manager or WorkspaceManager()
        self.settings_manager = settings_manager or SettingsManager()
        self.config_store = config_store or DesktopConfigStore(self.workspace_manager.base_dir)
        self.job_store = job_store or DesktopRunJobStore(self.workspace_manager.base_dir)

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

    def create_project(
        self,
        name: str,
        project_path: str,
        primary_agent: str = "codex",
    ) -> DesktopProjectSummary:
        """Register an existing project path as a desktop workspace."""
        clean_path = Path(project_path).expanduser()
        if not clean_path.exists():
            raise ValueError(f"project_path_missing:{clean_path}")
        if not clean_path.is_dir():
            raise ValueError(f"project_path_not_directory:{clean_path}")

        clean_name = name.strip() or clean_path.name or "AOP Project"
        workspace = self.workspace_manager.create_workspace(
            name=clean_name,
            project_path=str(clean_path),
            primary_agent=primary_agent,
        )
        return self.get_project(workspace.id) or DesktopProjectSummary(
            project_id=workspace.id,
            name=workspace.name,
            project_path=workspace.project_path,
            primary_agent=workspace.primary_agent,
            last_active=workspace.last_active,
            session_id=workspace.session_id,
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

    def install_provider_dependency(self, provider_id: str) -> DesktopInstallResult:
        """Run the primary install command for one provider."""
        provider = next(
            (status for status in self.get_provider_status() if status.provider_id == provider_id),
            None,
        )
        if provider is None:
            raise ValueError(f"provider_not_found:{provider_id}")
        if not provider.install_commands:
            raise ValueError(f"provider_install_command_missing:{provider_id}")

        command = provider.install_commands[0]
        completed = subprocess.run(
            self._build_shell_command(command),
            capture_output=True,
            text=True,
            timeout=900,
            check=False,
            cwd=str(Path.cwd()),
        )
        output = "\n".join(
            chunk for chunk in [completed.stdout.strip(), completed.stderr.strip()] if chunk
        ).strip()
        success = completed.returncode == 0
        summary = (
            f"{provider.label} install command finished successfully."
            if success
            else f"{provider.label} install command failed with exit code {completed.returncode}."
        )
        return DesktopInstallResult(
            provider_id=provider_id,
            command=command,
            success=success,
            summary=summary,
            output=output,
            next_steps=provider.install_commands[1:],
        )

    def start_run(self, project_id: str, prompt: str) -> DesktopRunLaunchResult:
        """Run one AOP workflow from the desktop shell."""
        clean_prompt, project_path, preferred_provider = self._validate_run_request(project_id, prompt)
        result = self._execute_run(project_path, clean_prompt, preferred_provider)
        return DesktopRunLaunchResult(
            project_id=project_id,
            sprint_id=result.sprint_id,
            success=result.success,
            state=result.state.value if hasattr(result.state, "value") else str(result.state),
            summary=result.summary,
            next_steps=list(result.next_steps),
        )

    def start_run_async(self, project_id: str, prompt: str) -> DesktopRunJob:
        """Queue one desktop run as a background job."""
        clean_prompt, _, _ = self._validate_run_request(project_id, prompt)
        job = self.job_store.create_job(project_id=project_id, prompt=clean_prompt)
        self._spawn_run_worker(job.job_id)
        return job

    def get_run_job(self, job_id: str) -> Optional[DesktopRunJob]:
        """Return one async desktop run job if present."""
        return self.job_store.get_job(job_id)

    def execute_run_job(self, job_id: str) -> DesktopRunJob:
        """Execute one queued desktop run job and persist status transitions."""
        job = self.job_store.get_job(job_id)
        if job is None:
            raise ValueError(f"job_not_found:{job_id}")

        job = self.job_store.save_job(DesktopRunJob(**{**job.to_dict(), "status": "running", "error": ""}))
        try:
            clean_prompt, project_path, preferred_provider = self._validate_run_request(
                job.project_id,
                job.prompt,
            )
            result = self._execute_run(project_path, clean_prompt, preferred_provider)
        except Exception as error:
            return self.job_store.save_job(
                DesktopRunJob(
                    job_id=job.job_id,
                    project_id=job.project_id,
                    prompt=job.prompt,
                    status="failed",
                    created_at=job.created_at,
                    updated_at=job.updated_at,
                    error=str(error),
                )
            )

        return self.job_store.save_job(
            DesktopRunJob(
                job_id=job.job_id,
                project_id=job.project_id,
                prompt=job.prompt,
                status="completed" if result.success else "failed",
                created_at=job.created_at,
                updated_at=job.updated_at,
                sprint_id=result.sprint_id,
                summary=result.summary,
                state=result.state.value if hasattr(result.state, "value") else str(result.state),
                next_steps=list(result.next_steps),
            )
        )

    def _load_latest_run(self, project_path: str) -> WorkflowRunSummary | None:
        path = Path(project_path)
        if not path.exists():
            return None
        return WorkflowRunReader(path).get_latest_run()

    def _validate_run_request(self, project_id: str, prompt: str) -> tuple[str, Path, str]:
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
        if preferred_provider:
            preferred_status = next(
                (status for status in self.get_provider_status() if status.provider_id == preferred_provider),
                None,
            )
            if preferred_status is None:
                raise ValueError(f"preferred_provider_unknown:{preferred_provider}")
            if preferred_status.required_env_vars and preferred_status.missing_env_vars:
                raise ValueError(
                    f"preferred_provider_missing_env:{preferred_provider}:{','.join(preferred_status.missing_env_vars)}"
                )
            if not preferred_status.detected:
                raise ValueError(f"preferred_provider_unavailable:{preferred_provider}")

        return clean_prompt, project_path, preferred_provider

    def _execute_run(self, project_path: Path, prompt: str, preferred_provider: str):
        providers = self._build_provider_priority(preferred_provider)
        orchestrator_type = self._resolve_orchestrator_type(preferred_provider)

        driver = AgentDriver(
            config=AgentDriverConfig(
                orchestrator_type=orchestrator_type,
                providers=providers,
                storage_path=project_path / ".aop",
            )
        )
        return driver.run_from_vague_description(prompt)

    def _spawn_run_worker(self, job_id: str) -> None:
        python = os.environ.get("AOP_DESKTOP_PYTHON", sys.executable or "python")
        command = [
            python,
            "-m",
            "aop.app_runtime",
            "worker-run",
            "--job-id",
            job_id,
        ]
        kwargs = {
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
            "stdin": subprocess.DEVNULL,
            "cwd": str(Path.cwd()),
            "close_fds": True,
        }
        if os.name == "nt":
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW  # type: ignore[index]
        subprocess.Popen(command, **kwargs)

    def _build_shell_command(self, command: str) -> List[str]:
        detector = get_platform_detector()
        if detector.is_windows():
            return ["powershell", "-NoProfile", "-Command", command]
        return ["bash", "-lc", command]

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
