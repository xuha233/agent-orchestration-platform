"""Tests for the desktop app runtime service."""

from __future__ import annotations

from pathlib import Path

from aop.app_runtime import DesktopAppBridge, DesktopAppService
from aop.agent.types import SprintState
from aop.workflow import CompletionDecision, VerificationReport, WorkflowArtifactManager, WorkflowPhase, WorkflowRun
from aop.primary.workspace import SettingsManager, WorkspaceManager


def _create_workspace(base_dir: Path, name: str, project_path: Path) -> str:
    manager = WorkspaceManager(base_dir)
    workspace = manager.create_workspace(name=name, project_path=str(project_path), primary_agent="codex")
    return workspace.id


def test_desktop_app_service_lists_projects_with_latest_run(tmp_path):
    project_path = tmp_path / "project-one"
    project_path.mkdir()

    artifact_manager = WorkflowArtifactManager(project_path)
    run = WorkflowRun(
        run_id="run-001",
        original_input="Build desktop shell",
        current_phase=WorkflowPhase.VERIFY,
        status="needs_follow_up",
    )
    artifact_manager.initialize_run(run)
    artifact_manager.write_verification(
        run.run_id,
        VerificationReport(summary="There are still unresolved UI gaps.", verdict="partial"),
    )
    artifact_manager.write_completion(
        run.run_id,
        CompletionDecision(
            passed=False,
            status="needs_follow_up",
            summary="Desktop shell still needs follow-up.",
            reasons=["Verification verdict is partial, not pass."],
        ),
    )

    workspace_id = _create_workspace(tmp_path / "aop-home", "Desktop Pilot", project_path)
    service = DesktopAppService(
        workspace_manager=WorkspaceManager(tmp_path / "aop-home"),
        settings_manager=SettingsManager(tmp_path / "aop-home"),
    )

    projects = service.list_projects()

    assert len(projects) == 1
    assert projects[0].project_id == workspace_id
    assert projects[0].latest_run_id == "run-001"
    assert projects[0].latest_run_phase == "verify"
    assert projects[0].needs_follow_up is True


def test_desktop_app_service_creates_project_workspace(tmp_path):
    workspace_home = tmp_path / "aop-home"
    project_path = tmp_path / "project-create"
    project_path.mkdir()

    service = DesktopAppService(
        workspace_manager=WorkspaceManager(workspace_home),
        settings_manager=SettingsManager(workspace_home),
    )

    project = service.create_project(
        name="Desktop Created Project",
        project_path=str(project_path),
        primary_agent="codex",
    )

    assert project.name == "Desktop Created Project"
    assert project.project_path == str(project_path)
    assert project.primary_agent == "codex"
    assert service.get_project(project.project_id) is not None


def test_desktop_app_bridge_returns_run_detail_payload(tmp_path):
    project_path = tmp_path / "project-two"
    project_path.mkdir()

    artifact_manager = WorkflowArtifactManager(project_path)
    run = WorkflowRun(
        run_id="run-002",
        original_input="Inspect workflow artifacts",
        current_phase=WorkflowPhase.COMPLETE,
        status="completed",
    )
    artifact_manager.initialize_run(run)
    artifact_manager.write_summary(run.run_id, "Workflow detail available.")

    workspace_home = tmp_path / "aop-home"
    workspace_id = _create_workspace(workspace_home, "Workflow Pilot", project_path)
    service = DesktopAppService(
        workspace_manager=WorkspaceManager(workspace_home),
        settings_manager=SettingsManager(workspace_home),
    )
    bridge = DesktopAppBridge(service)

    response = bridge.dispatch("run_detail", {"project_id": workspace_id, "run_id": run.run_id})

    assert response["ok"] is True
    assert response["data"]["summary"]["run_id"] == "run-002"
    assert any(artifact["title"] == "SUMMARY" for artifact in response["data"]["artifacts"])


def test_desktop_app_bridge_creates_project_payload(tmp_path):
    workspace_home = tmp_path / "aop-home"
    project_path = tmp_path / "project-bridge-create"
    project_path.mkdir()

    service = DesktopAppService(
        workspace_manager=WorkspaceManager(workspace_home),
        settings_manager=SettingsManager(workspace_home),
    )
    bridge = DesktopAppBridge(service)

    response = bridge.dispatch(
        "create_project",
        {
            "project_name": "Bridge Project",
            "project_path": str(project_path),
            "primary_agent": "codex",
        },
    )

    assert response["ok"] is True
    assert response["data"]["name"] == "Bridge Project"
    assert response["data"]["project_path"] == str(project_path)


def test_desktop_app_service_returns_minimal_settings(tmp_path):
    settings = SettingsManager(tmp_path / "aop-home")
    settings.set_primary_agent("codex")
    settings.set_enable_mem0_memory(True)

    service = DesktopAppService(
        workspace_manager=WorkspaceManager(tmp_path / "aop-home"),
        settings_manager=settings,
    )

    payload = service.get_settings()

    assert payload["primary_agent"] == "codex"
    assert payload["enable_mem0_memory"] is True


def test_desktop_app_service_reports_setup_status(tmp_path, monkeypatch):
    workspace_home = tmp_path / "aop-home"

    monkeypatch.setattr(
        "aop.app_runtime.service.shutil.which",
        lambda name: "C:/bin/tool.exe"
        if Path(str(name)).name.lower().startswith(("python", "node", "npm"))
        else None,
    )

    class Completed:
        def __init__(self, output: str):
            self.returncode = 0
            self.stdout = output
            self.stderr = ""

    monkeypatch.setattr(
        "aop.app_runtime.service.subprocess.run",
        lambda command, **kwargs: Completed(f"{command[0]} 1.0.0"),
    )

    service = DesktopAppService(
        workspace_manager=WorkspaceManager(workspace_home),
        settings_manager=SettingsManager(workspace_home),
    )

    checks = service.get_setup_status()

    assert any(check.check_id == "python" and check.detected for check in checks)
    assert any(check.check_id == "node" and check.install_commands for check in checks)
    assert any(check.check_id == "cargo" and not check.detected for check in checks)


def test_desktop_app_bridge_returns_setup_status_payload(tmp_path, monkeypatch):
    workspace_home = tmp_path / "aop-home"

    monkeypatch.setattr("aop.app_runtime.service.shutil.which", lambda name: None)
    service = DesktopAppService(
        workspace_manager=WorkspaceManager(workspace_home),
        settings_manager=SettingsManager(workspace_home),
    )
    bridge = DesktopAppBridge(service)

    response = bridge.dispatch("setup_status", {})

    assert response["ok"] is True
    assert any(check["check_id"] == "python" for check in response["data"])


def test_desktop_app_service_installs_setup_dependency(tmp_path, monkeypatch):
    workspace_home = tmp_path / "aop-home"
    captured: dict[str, object] = {}

    class Completed:
        returncode = 0
        stdout = "installed"
        stderr = ""

    service = DesktopAppService(
        workspace_manager=WorkspaceManager(workspace_home),
        settings_manager=SettingsManager(workspace_home),
    )

    monkeypatch.setattr(
        "aop.app_runtime.service.shutil.which",
        lambda name: None if str(name) == "cargo" else "C:/bin/tool.exe",
    )

    def fake_run(command, **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs
        return Completed()

    monkeypatch.setattr("aop.app_runtime.service.subprocess.run", fake_run)

    result = service.install_setup_dependency("cargo")

    assert result.check_id == "cargo"
    assert result.success is True
    assert "winget install" in result.command
    assert captured["command"][:3] == ["powershell", "-NoProfile", "-Command"]


def test_desktop_app_bridge_installs_setup_dependency_payload(tmp_path, monkeypatch):
    workspace_home = tmp_path / "aop-home"

    class Completed:
        returncode = 1
        stdout = ""
        stderr = "install failed"

    service = DesktopAppService(
        workspace_manager=WorkspaceManager(workspace_home),
        settings_manager=SettingsManager(workspace_home),
    )

    monkeypatch.setattr(
        "aop.app_runtime.service.shutil.which",
        lambda name: None if str(name) == "cargo" else "C:/bin/tool.exe",
    )
    monkeypatch.setattr("aop.app_runtime.service.subprocess.run", lambda *args, **kwargs: Completed())
    bridge = DesktopAppBridge(service)

    response = bridge.dispatch("install_setup_dependency", {"check_id": "cargo"})

    assert response["ok"] is True
    assert response["data"]["check_id"] == "cargo"
    assert response["data"]["success"] is False
    assert "failed" in response["data"]["summary"]


def test_desktop_app_service_updates_provider_config(tmp_path, monkeypatch):
    workspace_home = tmp_path / "aop-home"
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    service = DesktopAppService(
        workspace_manager=WorkspaceManager(workspace_home),
        settings_manager=SettingsManager(workspace_home),
    )

    status = service.update_provider_config(
        "codex",
        env_values={"OPENAI_API_KEY": "desktop-token"},
        preferred=True,
    )

    assert status is not None
    assert status.provider_id == "codex"
    assert status.preferred is True
    assert status.stored_env_vars["OPENAI_API_KEY"] == "desktop-token"
    assert "OPENAI_API_KEY" in status.configured_env_vars


def test_desktop_app_bridge_updates_provider_payload(tmp_path):
    workspace_home = tmp_path / "aop-home"
    service = DesktopAppService(
        workspace_manager=WorkspaceManager(workspace_home),
        settings_manager=SettingsManager(workspace_home),
    )
    bridge = DesktopAppBridge(service)

    response = bridge.dispatch(
        "update_provider",
        {
            "provider_id": "codex",
            "env_values": {"OPENAI_API_KEY": "bridge-token"},
            "preferred": True,
        },
    )

    assert response["ok"] is True
    assert response["data"]["provider_id"] == "codex"
    assert response["data"]["preferred"] is True
    assert response["data"]["stored_env_vars"]["OPENAI_API_KEY"] == "bridge-token"


def test_desktop_app_service_installs_provider_dependency(tmp_path, monkeypatch):
    workspace_home = tmp_path / "aop-home"
    captured: dict[str, object] = {}

    class Completed:
        returncode = 0
        stdout = "installed"
        stderr = ""

    def fake_run(command, **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs
        return Completed()

    service = DesktopAppService(
        workspace_manager=WorkspaceManager(workspace_home),
        settings_manager=SettingsManager(workspace_home),
    )
    monkeypatch.setattr("aop.app_runtime.service.subprocess.run", fake_run)

    result = service.install_provider_dependency("codex")

    assert result.provider_id == "codex"
    assert result.success is True
    assert result.command.startswith("npm install -g")
    assert captured["command"][:3] == ["powershell", "-NoProfile", "-Command"]


def test_desktop_app_bridge_installs_provider_payload(tmp_path, monkeypatch):
    workspace_home = tmp_path / "aop-home"

    class Completed:
        returncode = 1
        stdout = ""
        stderr = "install failed"

    service = DesktopAppService(
        workspace_manager=WorkspaceManager(workspace_home),
        settings_manager=SettingsManager(workspace_home),
    )
    monkeypatch.setattr("aop.app_runtime.service.subprocess.run", lambda *args, **kwargs: Completed())
    bridge = DesktopAppBridge(service)

    response = bridge.dispatch("install_provider", {"provider_id": "codex"})

    assert response["ok"] is True
    assert response["data"]["provider_id"] == "codex"
    assert response["data"]["success"] is False
    assert "failed" in response["data"]["summary"]


def test_desktop_app_service_starts_run_with_driver(tmp_path, monkeypatch):
    workspace_home = tmp_path / "aop-home"
    project_path = tmp_path / "project-run"
    project_path.mkdir()
    workspace_id = _create_workspace(workspace_home, "Run Pilot", project_path)

    captured: dict[str, object] = {}

    class FakeDriver:
        def __init__(self, config):
            captured["config"] = config

        def run_from_vague_description(self, prompt):
            captured["prompt"] = prompt
            class Result:
                sprint_id = "sprint-desktop-001"
                success = True
                state = SprintState.COMPLETED
                summary = "Run completed from desktop."
                next_steps = ["Inspect artifacts"]

            return Result()

    monkeypatch.setattr("aop.app_runtime.service.AgentDriver", FakeDriver)

    service = DesktopAppService(
        workspace_manager=WorkspaceManager(workspace_home),
        settings_manager=SettingsManager(workspace_home),
    )
    service.update_provider_config("codex", {"OPENAI_API_KEY": "desktop-token"}, preferred=True)

    result = service.start_run(workspace_id, "Build a desktop launch flow")

    assert result.project_id == workspace_id
    assert result.sprint_id == "sprint-desktop-001"
    assert result.success is True
    assert result.state == "completed"
    assert captured["prompt"] == "Build a desktop launch flow"
    assert captured["config"].storage_path == project_path / ".aop"


def test_desktop_app_bridge_start_run_returns_payload(tmp_path, monkeypatch):
    workspace_home = tmp_path / "aop-home"
    project_path = tmp_path / "project-run-bridge"
    project_path.mkdir()
    workspace_id = _create_workspace(workspace_home, "Run Bridge Pilot", project_path)

    class FakeDriver:
        def __init__(self, config):
            pass

        def run_from_vague_description(self, prompt):
            class Result:
                sprint_id = "sprint-desktop-bridge"
                success = False
                state = SprintState.FAILED
                summary = "Run failed from desktop."
                next_steps = ["Check provider config"]

            return Result()

    monkeypatch.setattr("aop.app_runtime.service.AgentDriver", FakeDriver)

    service = DesktopAppService(
        workspace_manager=WorkspaceManager(workspace_home),
        settings_manager=SettingsManager(workspace_home),
    )
    bridge = DesktopAppBridge(service)

    response = bridge.dispatch(
        "start_run",
        {"project_id": workspace_id, "prompt": "Launch test flow"},
    )

    assert response["ok"] is True
    assert response["data"]["sprint_id"] == "sprint-desktop-bridge"
    assert response["data"]["state"] == "failed"


def test_desktop_app_service_starts_async_run_job(tmp_path, monkeypatch):
    workspace_home = tmp_path / "aop-home"
    project_path = tmp_path / "project-run-async"
    project_path.mkdir()
    workspace_id = _create_workspace(workspace_home, "Run Async Pilot", project_path)

    captured: dict[str, object] = {}

    class FakePopen:
        def __init__(self, command, **kwargs):
            captured["command"] = command
            captured["kwargs"] = kwargs

    service = DesktopAppService(
        workspace_manager=WorkspaceManager(workspace_home),
        settings_manager=SettingsManager(workspace_home),
    )
    service.update_provider_config("codex", {"OPENAI_API_KEY": "desktop-token"}, preferred=True)
    monkeypatch.setattr(service, "_spawn_run_worker", lambda job_id: FakePopen(["python", "--job-id", job_id]))

    job = service.start_run_async(workspace_id, "Build async desktop launch flow")

    assert job.project_id == workspace_id
    assert job.status == "queued"
    assert job.prompt == "Build async desktop launch flow"
    assert captured["command"][-2:] == ["--job-id", job.job_id]
    assert service.get_run_job(job.job_id) is not None


def test_desktop_app_service_executes_run_job(tmp_path, monkeypatch):
    workspace_home = tmp_path / "aop-home"
    project_path = tmp_path / "project-run-job"
    project_path.mkdir()
    workspace_id = _create_workspace(workspace_home, "Run Job Pilot", project_path)

    class FakeDriver:
        def __init__(self, config):
            self.config = config

        def run_from_vague_description(self, prompt):
            class Result:
                sprint_id = "sprint-job-001"
                success = True
                state = SprintState.COMPLETED
                summary = "Async desktop run completed."
                next_steps = ["Inspect workflow artifacts"]

            return Result()

    monkeypatch.setattr("aop.app_runtime.service.AgentDriver", FakeDriver)

    service = DesktopAppService(
        workspace_manager=WorkspaceManager(workspace_home),
        settings_manager=SettingsManager(workspace_home),
    )
    service.update_provider_config("codex", {"OPENAI_API_KEY": "desktop-token"}, preferred=True)
    monkeypatch.setattr(service, "_spawn_run_worker", lambda job_id: None)

    job = service.start_run_async(workspace_id, "Build async desktop validation flow")
    completed = service.execute_run_job(job.job_id)

    assert completed.job_id == job.job_id
    assert completed.status == "completed"
    assert completed.sprint_id == "sprint-job-001"
    assert completed.state == "completed"
    assert completed.next_steps == ["Inspect workflow artifacts"]


def test_desktop_app_service_rejects_run_when_preferred_provider_missing_env(tmp_path, monkeypatch):
    workspace_home = tmp_path / "aop-home"
    project_path = tmp_path / "project-run-env"
    project_path.mkdir()
    workspace_id = _create_workspace(workspace_home, "Run Env Pilot", project_path)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    service = DesktopAppService(
        workspace_manager=WorkspaceManager(workspace_home),
        settings_manager=SettingsManager(workspace_home),
    )
    service.update_provider_config("codex", {}, preferred=True)

    try:
        service.start_run(workspace_id, "Build desktop validation flow")
    except ValueError as error:
        assert str(error).startswith("preferred_provider_missing_env:codex")
    else:
        raise AssertionError("Expected start_run to reject missing preferred provider env values")
