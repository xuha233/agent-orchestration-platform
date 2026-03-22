"""Service layer for the future desktop app bridge."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional

from aop import __version__
from aop.agent.driver import AgentDriver
from aop.agent.types import AgentDriverConfig
from aop.core.adapter import get_adapter_registry
from aop.core.compat import get_platform_detector
from aop.memory import MemoryBackend, MemoryConfig, MemoryMigrator, MemoryService, resolve_memory_config
from aop.primary import get_registry
from aop.primary.workspace import SettingsManager, WorkspaceManager
from aop.workflow import WorkflowRunDetail, WorkflowRunReader, WorkflowRunSummary

from .config_store import DesktopConfigStore
from .jobs import DesktopRunJobStore
from .models import (
    DesktopAppHealth,
    DesktopInstallResult,
    DesktopMemoryRecord,
    DesktopMemoryMigrationResult,
    DesktopMemorySettings,
    DesktopMemoryStatus,
    DesktopProjectSummary,
    DesktopProviderStatus,
    DesktopRunJob,
    DesktopRunLaunchResult,
    DesktopSetupCheck,
    DesktopSetupInstallResult,
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

WINDOWS_SETUP_COMMANDS: Dict[str, List[str]] = {
    "python": ["winget install Python.Python.3.11"],
    "node": ["winget install OpenJS.NodeJS.LTS"],
    "npm": ["winget install OpenJS.NodeJS.LTS"],
    "rustc": ["winget install Rustlang.Rustup"],
    "cargo": ["winget install Rustlang.Rustup"],
}

MACOS_SETUP_COMMANDS: Dict[str, List[str]] = {
    "python": ["brew install python@3.11"],
    "node": ["brew install node"],
    "npm": ["brew install node"],
    "rustc": ["brew install rustup-init", "rustup-init -y"],
    "cargo": ["brew install rustup-init", "rustup-init -y"],
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
                    attention_tags=list(latest_run.attention_tags) if latest_run else [],
                    priority_rank=latest_run.priority_rank if latest_run else 0,
                    triage_summary=latest_run.triage_summary if latest_run else "",
                    triage_evidence=list(latest_run.triage_evidence) if latest_run else [],
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

    def get_memory_status(self, project_id: str) -> DesktopMemoryStatus | None:
        """Return memory status for one desktop project."""
        workspace = self.workspace_manager.get_workspace(project_id)
        if workspace is None:
            return None

        project_path = Path(workspace.project_path)
        global_enabled = self.settings_manager.get_enable_mem0_memory()
        config_path = project_path / ".aop" / "memory_config.yaml"
        raw_config = MemoryConfig.from_yaml(config_path)
        project_enabled = raw_config.enabled if config_path.exists() else True
        config = self._load_memory_config(project_path)
        service = MemoryService(config, workspace_path=project_path)
        status = service.get_status()
        total_memories = len(service.list_all(limit=200))
        migrator = MemoryMigrator(service, workspace_path=project_path)
        migration = migrator.analyze()
        source_counts = {
            "hypotheses": int(migration.get("stats", {}).get("hypotheses", 0) or 0),
            "learnings": int(migration.get("stats", {}).get("learnings", 0) or 0),
            "project_memory": int(migration.get("stats", {}).get("memories", 0) or 0),
        }

        return DesktopMemoryStatus(
            project_id=project_id,
            project_path=workspace.project_path,
            enabled=bool(config.enabled),
            global_enabled=global_enabled,
            project_enabled=project_enabled,
            backend=str(config.backend.value),
            mem0_available=bool(status.get("mem0_available", False)),
            current_backend=str(status.get("backend", "file")),
            total_memories=total_memories,
            legacy_entry_count=int(migration.get("stats", {}).get("total_entries", 0) or 0),
            migration_ready=bool(migration.get("ready", False)),
            migration_issues=[str(issue) for issue in migration.get("issues", [])],
            memory_sources=source_counts,
            init_error=str(status.get("init_error", "") or ""),
        )

    def get_memory_settings(self, project_id: str) -> DesktopMemorySettings | None:
        """Return editable memory settings using the unified merge policy."""
        workspace = self.workspace_manager.get_workspace(project_id)
        if workspace is None:
            return None

        project_path = Path(workspace.project_path)
        config_path = project_path / ".aop" / "memory_config.yaml"
        raw_config = MemoryConfig.from_yaml(config_path)
        if raw_config.project_id == "default":
            raw_config.project_id = project_path.name or "default"
        global_enabled = self.settings_manager.get_enable_mem0_memory()
        project_enabled = raw_config.enabled if config_path.exists() else True
        effective = self._load_memory_config(project_path)

        return DesktopMemorySettings(
            project_id=project_id,
            global_enabled=global_enabled,
            project_enabled=project_enabled,
            effective_enabled=effective.enabled,
            backend=raw_config.backend.value,
            search_top_k=raw_config.search_top_k,
            search_threshold=raw_config.search_threshold,
            embedding_model=raw_config.embedding_model,
            embedding_dims=raw_config.embedding_dims,
        )

    def update_memory_settings(
        self,
        project_id: str,
        *,
        global_enabled: bool,
        project_enabled: bool,
        backend: str | None = None,
        search_top_k: int | None = None,
        search_threshold: float | None = None,
    ) -> DesktopMemorySettings:
        """Persist unified memory settings for one project and global toggle."""
        workspace = self.workspace_manager.get_workspace(project_id)
        if workspace is None:
            raise ValueError(f"workspace_not_found:{project_id}")

        project_path = Path(workspace.project_path)
        config_path = project_path / ".aop" / "memory_config.yaml"
        config = MemoryConfig.from_yaml(config_path)
        if config.project_id == "default":
            config.project_id = project_path.name or "default"

        if backend:
            try:
                config.backend = MemoryBackend(backend)
            except ValueError as error:
                raise ValueError(f"memory_backend_invalid:{backend}") from error
        if search_top_k is not None:
            config.search_top_k = int(search_top_k)
        if search_threshold is not None:
            config.search_threshold = float(search_threshold)
        config.enabled = bool(project_enabled)
        config.to_yaml(config_path)
        self.settings_manager.set_enable_mem0_memory(bool(global_enabled))
        settings = self.get_memory_settings(project_id)
        if settings is None:
            raise ValueError(f"workspace_not_found:{project_id}")
        return settings

    def list_memory_records(self, project_id: str, limit: int = 12) -> List[DesktopMemoryRecord]:
        """Return recent memory records for one desktop project."""
        workspace = self.workspace_manager.get_workspace(project_id)
        if workspace is None:
            return []

        project_path = Path(workspace.project_path)
        config = self._load_memory_config(project_path)
        service = MemoryService(config, workspace_path=project_path)
        memories = service.list_all(limit=max(limit, 1))

        def sort_key(memory: Dict[str, object]) -> str:
            metadata = memory.get("metadata", {})
            if isinstance(metadata, dict):
                return str(metadata.get("timestamp", ""))
            return ""

        records: List[DesktopMemoryRecord] = []
        for memory in sorted(memories, key=sort_key, reverse=True)[:limit]:
            metadata = memory.get("metadata", {})
            if not isinstance(metadata, dict):
                metadata = {}
            records.append(
                DesktopMemoryRecord(
                    memory_id=str(memory.get("id", "")),
                    content=str(memory.get("content", "")),
                    memory_type=str(metadata.get("type", "general")),
                    phase=str(metadata.get("phase", "")),
                    run_id=str(metadata.get("run_id", "")),
                    timestamp=str(metadata.get("timestamp", "")),
                )
            )
        return records

    def migrate_memory(self, project_id: str, dry_run: bool = False) -> DesktopMemoryMigrationResult:
        """Migrate legacy project memory sources into the active memory backend."""
        workspace = self.workspace_manager.get_workspace(project_id)
        if workspace is None:
            raise ValueError(f"workspace_not_found:{project_id}")

        project_path = Path(workspace.project_path)
        config = self._load_memory_config(project_path)
        service = MemoryService(config, workspace_path=project_path)
        migrator = MemoryMigrator(service, workspace_path=project_path)
        result = migrator.migrate_all(dry_run=dry_run)

        source_counts = {
            "hypotheses": int((result.get("hypotheses") or {}).get("count", 0)),
            "learnings": int((result.get("learnings") or {}).get("count", 0)),
            "project_memory": int((result.get("project_memory") or {}).get("count", 0)),
        }

        return DesktopMemoryMigrationResult(
            project_id=project_id,
            dry_run=bool(result.get("dry_run", False)),
            success=bool(result.get("success", False)),
            total_migrated=int(result.get("total", 0) or 0),
            source_counts=source_counts,
            errors=[str(error) for error in result.get("errors", [])],
        )

    def get_setup_status(self) -> List[DesktopSetupCheck]:
        """Return system dependency readiness for the desktop setup workspace."""
        checks = [
            self._tool_check(
                check_id="python",
                label="Python",
                command=[os.environ.get("AOP_DESKTOP_PYTHON", sys.executable or "python"), "--version"],
                required=True,
                install_hint="Install Python 3.11+ and keep it on PATH for the desktop sidecar.",
            ),
            self._tool_check(
                check_id="node",
                label="Node.js",
                command=["node", "--version"],
                required=True,
                install_hint="Install Node.js LTS so the desktop frontend and CLI dependencies can run.",
            ),
            self._tool_check(
                check_id="npm",
                label="npm",
                command=["npm", "--version"],
                required=True,
                install_hint="Install npm alongside Node.js so desktop packages and provider CLIs can be installed.",
            ),
            self._tool_check(
                check_id="rustc",
                label="Rust compiler",
                command=["rustc", "--version"],
                required=False,
                install_hint="Install Rust via rustup to enable native Tauri builds.",
            ),
            self._tool_check(
                check_id="cargo",
                label="Cargo",
                command=["cargo", "--version"],
                required=False,
                install_hint="Install Cargo via rustup to build native desktop packages.",
            ),
        ]
        return checks

    def install_setup_dependency(self, check_id: str) -> DesktopSetupInstallResult:
        """Run the primary install command for one system dependency."""
        check = next(
            (item for item in self.get_setup_status() if item.check_id == check_id),
            None,
        )
        if check is None:
            raise ValueError(f"setup_check_not_found:{check_id}")
        if not check.install_commands:
            raise ValueError(f"setup_install_command_missing:{check_id}")

        command = check.install_commands[0]
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
            f"{check.label} install command finished successfully."
            if success
            else f"{check.label} install command failed with exit code {completed.returncode}."
        )
        return DesktopSetupInstallResult(
            check_id=check_id,
            command=command,
            success=success,
            summary=summary,
            output=output,
            next_steps=check.install_commands[1:],
        )

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

    def _tool_check(
        self,
        check_id: str,
        label: str,
        command: List[str],
        required: bool,
        install_hint: str,
    ) -> DesktopSetupCheck:
        executable = command[0]
        install_commands = self._get_setup_install_commands(check_id)
        if not shutil.which(executable):
            return DesktopSetupCheck(
                check_id=check_id,
                label=label,
                detected=False,
                required=required,
                reason=f"{label} was not found on PATH.",
                install_hint=install_hint,
                install_commands=install_commands,
            )

        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
        except OSError as error:
            return DesktopSetupCheck(
                check_id=check_id,
                label=label,
                detected=False,
                required=required,
                reason=str(error),
                install_hint=install_hint,
                install_commands=install_commands,
            )

        version = (completed.stdout or completed.stderr).strip().splitlines()
        return DesktopSetupCheck(
            check_id=check_id,
            label=label,
            detected=completed.returncode == 0,
            required=required,
            version=version[0] if version else "",
            reason="" if completed.returncode == 0 else f"{label} check exited with code {completed.returncode}.",
            install_hint=install_hint,
            install_commands=install_commands,
        )

    def _get_setup_install_commands(self, check_id: str) -> List[str]:
        detector = get_platform_detector()
        if detector.is_windows():
            return list(WINDOWS_SETUP_COMMANDS.get(check_id, []))
        if detector.is_macos():
            return list(MACOS_SETUP_COMMANDS.get(check_id, []))
        return []

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

    def _load_memory_config(self, project_path: Path) -> MemoryConfig:
        return resolve_memory_config(
            project_path,
            global_enabled=self.settings_manager.get_enable_mem0_memory(),
        )
