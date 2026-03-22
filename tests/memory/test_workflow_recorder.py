# -*- coding: utf-8 -*-
"""Tests for workflow memory recorder."""

from __future__ import annotations

from aop.memory import MemoryConfig
from aop.memory.workflow_recorder import WorkflowMemoryRecorder
from aop.primary.workspace import SettingsManager
from aop.workflow import CompletionDecision, GuardrailReport, PlanCheckReport, VerificationReport, WorkflowPhase, WorkflowPlan, WorkflowRun


def test_workflow_memory_recorder_respects_global_toggle(tmp_path):
    workspace = tmp_path / "project"
    workspace.mkdir()
    (workspace / ".aop").mkdir()

    config = MemoryConfig(enabled=True)
    config.to_yaml(workspace / ".aop" / "memory_config.yaml")

    settings = SettingsManager(tmp_path / "aop-home")
    settings.set_enable_mem0_memory(False)

    recorder = WorkflowMemoryRecorder(workspace, settings_manager=settings)
    run = WorkflowRun(run_id="run-001", original_input="Ship desktop shell", current_phase=WorkflowPhase.PLAN)
    plan = WorkflowPlan(summary="Plan desktop shell")
    plan_check = PlanCheckReport(passed=True, summary="Looks good.", issues=[])

    recorder.record_plan(run, plan, plan_check)

    memories_file = workspace / ".aop" / "memory" / "memories.json"
    assert not memories_file.exists()


def test_workflow_memory_recorder_writes_plan_and_completion_to_file_fallback(tmp_path):
    workspace = tmp_path / "project"
    workspace.mkdir()
    (workspace / ".aop").mkdir()

    config = MemoryConfig(enabled=True)
    config.to_yaml(workspace / ".aop" / "memory_config.yaml")

    settings = SettingsManager(tmp_path / "aop-home")
    settings.set_enable_mem0_memory(True)

    recorder = WorkflowMemoryRecorder(workspace, settings_manager=settings)
    run = WorkflowRun(run_id="run-101", original_input="Ship desktop shell", current_phase=WorkflowPhase.COMPLETE)

    recorder.record_plan(
        run,
        WorkflowPlan(summary="Plan desktop shell", goals=["Ship shell"], verification_steps=["Build app"]),
        PlanCheckReport(passed=False, summary="Budget pressure.", issues=[]),
    )
    recorder.record_verification(
        run,
        VerificationReport(summary="Partial verification.", verdict="partial", gaps=["UI gap"]),
    )
    recorder.record_completion(
        run,
        CompletionDecision(
            passed=False,
            status="needs_follow_up",
            summary="Needs another pass.",
            reasons=["Verification verdict is partial, not pass."],
        ),
        GuardrailReport(
            should_stop=True,
            summary="Stop after repair budget.",
            categories=["repair_budget"],
            reasons=["Repair budget exhausted"],
        ),
    )

    memories_file = workspace / ".aop" / "memory" / "memories.json"
    assert memories_file.exists()
    content = memories_file.read_text(encoding="utf-8")
    assert "workflow_plan" in content
    assert "workflow_verification" in content
    assert "workflow_completion" in content
    assert "workflow_guardrail" in content


def test_workflow_memory_recorder_recalls_previous_follow_up_context(tmp_path):
    workspace = tmp_path / "project"
    workspace.mkdir()
    (workspace / ".aop").mkdir()

    config = MemoryConfig(enabled=True)
    config.to_yaml(workspace / ".aop" / "memory_config.yaml")

    settings = SettingsManager(tmp_path / "aop-home")
    settings.set_enable_mem0_memory(True)

    recorder = WorkflowMemoryRecorder(workspace, settings_manager=settings)
    previous_run = WorkflowRun(run_id="run-prev", original_input="Old issue", current_phase=WorkflowPhase.COMPLETE)
    recorder.record_verification(
        previous_run,
        VerificationReport(
            summary="Authentication gap remained.",
            verdict="partial",
            gaps=["Authentication gap remained after repair"],
        ),
    )

    current_run = WorkflowRun(run_id="run-now", original_input="Current issue", current_phase=WorkflowPhase.GAP_CLOSE)
    hints = recorder.recall_follow_up_context(
        current_run,
        VerificationReport(
            summary="Authentication gap still failing.",
            verdict="partial",
            gaps=["Authentication gap remained after repair"],
        ),
    )

    assert hints
    assert any("workflow_verification" in hint for hint in hints)


def test_workflow_memory_recorder_recalls_previous_verification_context(tmp_path):
    workspace = tmp_path / "project"
    workspace.mkdir()
    (workspace / ".aop").mkdir()

    config = MemoryConfig(enabled=True)
    config.to_yaml(workspace / ".aop" / "memory_config.yaml")

    settings = SettingsManager(tmp_path / "aop-home")
    settings.set_enable_mem0_memory(True)

    recorder = WorkflowMemoryRecorder(workspace, settings_manager=settings)
    previous_run = WorkflowRun(
        run_id="run-prev",
        original_input="Old verification issue",
        current_phase=WorkflowPhase.VERIFY,
    )
    recorder.record_verification(
        previous_run,
        VerificationReport(
            summary="Authentication gap remained.",
            verdict="partial",
            gaps=["Authentication gap remained after repair"],
        ),
    )

    current_run = WorkflowRun(
        run_id="run-now",
        original_input="Current verification issue",
        current_phase=WorkflowPhase.VERIFY,
    )
    hints = recorder.recall_verification_context(
        current_run,
        VerificationReport(
            summary="Authentication gap still failing.",
            verdict="partial",
            gaps=["Authentication gap remained after repair"],
        ),
    )

    assert hints
    assert any("workflow_verification" in hint for hint in hints)


def test_workflow_memory_recorder_recalls_previous_planning_context(tmp_path):
    workspace = tmp_path / "project"
    workspace.mkdir()
    (workspace / ".aop").mkdir()

    config = MemoryConfig(enabled=True)
    config.to_yaml(workspace / ".aop" / "memory_config.yaml")

    settings = SettingsManager(tmp_path / "aop-home")
    settings.set_enable_mem0_memory(True)

    recorder = WorkflowMemoryRecorder(workspace, settings_manager=settings)
    previous_run = WorkflowRun(
        run_id="run-prev",
        original_input="Desktop shell planning",
        current_phase=WorkflowPhase.PLAN,
    )
    recorder.record_plan(
        previous_run,
        WorkflowPlan(
            summary="Plan desktop shell",
            goals=["Desktop shell"],
            verification_steps=["Build succeeds"],
        ),
        PlanCheckReport(passed=True, summary="Looks good.", issues=[]),
    )

    current_run = WorkflowRun(
        run_id="run-now",
        original_input="Desktop shell planning again",
        current_phase=WorkflowPhase.PLAN,
    )
    hints = recorder.recall_planning_context(
        current_run,
        WorkflowPlan(summary="Plan desktop shell", goals=["Desktop shell"]),
    )

    assert hints
    assert any("workflow_plan" in hint for hint in hints)
