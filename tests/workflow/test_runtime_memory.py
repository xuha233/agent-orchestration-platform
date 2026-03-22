"""Tests for workflow runtime memory integration."""

from __future__ import annotations

from types import SimpleNamespace

from aop.workflow import (
    GuardrailReport,
    VerificationReport,
    WorkflowRuntime,
)


class FakeMemoryRecorder:
    def __init__(self):
        self.calls: list[tuple[str, object]] = []

    def record_plan(self, run, plan, plan_check):
        self.calls.append(("plan", run.run_id))

    def record_verification(self, run, report, gap_closure=None):
        self.calls.append(("verification", run.run_id))

    def record_learnings(self, run, learnings):
        self.calls.append(("learnings", run.run_id))

    def record_completion(self, run, decision, guardrails=None):
        self.calls.append(("completion", run.run_id))

    def recall_follow_up_context(self, run, report, limit=3):
        return ["workflow_learning: Similar gap was fixed by tightening verification."]

    def recall_verification_context(self, run, report, limit=2):
        return ["workflow_verification: Previous verification found the same auth gap."]

    def recall_planning_context(self, run, plan, limit=2):
        return ["workflow_learning: Similar desktop shell work previously failed due to missing verification."]


def _context():
    return SimpleNamespace(
        sprint_id="run-201",
        original_input="Ship desktop shell",
        clarified_requirement=SimpleNamespace(
            summary="Ship desktop shell",
            core_features=["Desktop shell"],
            success_criteria=["Build succeeds"],
            risks=[],
        ),
        hypotheses=[],
        learnings=[SimpleNamespace(phase="learn", insights=["keep artifacts concise"])],
        execution_results=[],
        validation_results=[],
    )


def test_workflow_runtime_records_memory_for_key_artifacts(tmp_path):
    recorder = FakeMemoryRecorder()
    runtime = WorkflowRuntime(storage_path=tmp_path, memory_recorder=recorder)
    context = _context()

    runtime.initialize(context)
    runtime.sync_metadata(context)
    runtime.write_plan(context)
    runtime.write_verification(context)
    runtime.write_learnings(context)
    runtime.latest_verification_report = VerificationReport(summary="Pass", verdict="pass")
    runtime.latest_guardrail_report = GuardrailReport(
        should_stop=False,
        summary="No stop.",
        categories=[],
        reasons=[],
    )
    runtime.finalize(context, status="completed", summary="Done.")

    assert ("plan", "run-201") in recorder.calls
    assert ("verification", "run-201") in recorder.calls
    assert ("learnings", "run-201") in recorder.calls
    assert ("completion", "run-201") in recorder.calls


def test_workflow_runtime_uses_memory_hints_in_plan(tmp_path):
    recorder = FakeMemoryRecorder()
    runtime = WorkflowRuntime(storage_path=tmp_path, memory_recorder=recorder)
    context = _context()

    runtime.initialize(context)
    runtime.sync_metadata(context)
    plan = runtime.build_workflow_plan(context)

    assert "Recalled 1 related workflow memory hint" in plan.summary
    assert any(item.startswith("Historical context: workflow_learning") for item in plan.risks)
    assert any("Check prior memory while planning" in item for item in plan.verification_steps)


def test_workflow_runtime_uses_memory_hints_in_gap_closure_plan(tmp_path):
    recorder = FakeMemoryRecorder()
    runtime = WorkflowRuntime(storage_path=tmp_path, memory_recorder=recorder)
    context = _context()

    runtime.initialize(context)
    runtime.sync_metadata(context)
    report = VerificationReport(
        summary="Verification found a repeated auth gap.",
        verdict="partial",
        gaps=["Authentication gap remained after repair"],
    )

    plan = runtime.build_gap_closure_plan(report)

    assert "Recalled 1 related workflow memory hint" in plan.summary
    assert any("Consider previous memory" in step for step in plan.next_verification_steps)


def test_workflow_runtime_uses_memory_hints_in_verification_report(tmp_path):
    recorder = FakeMemoryRecorder()
    runtime = WorkflowRuntime(storage_path=tmp_path, memory_recorder=recorder)
    context = _context()
    context.execution_results = [
        {
            "task_id": "task-auth",
            "hypothesis_id": "h-auth",
            "state": "failed",
            "success": False,
        }
    ]

    runtime.initialize(context)
    runtime.sync_metadata(context)
    report = runtime.build_verification_report(context)

    assert "Recalled 1 related workflow memory hint" in report.summary
    assert any(item.startswith("memory_hint: workflow_verification") for item in report.evidence)
    assert any(check.name == "memory:related_context" for check in report.checks)
