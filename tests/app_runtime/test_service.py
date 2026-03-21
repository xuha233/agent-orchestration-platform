"""Tests for the desktop app runtime service."""

from __future__ import annotations

from pathlib import Path

from aop.app_runtime import DesktopAppBridge, DesktopAppService
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
