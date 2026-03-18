"""Tests for workflow run reader."""

from aop.workflow import (
    CompletionDecision,
    VerificationReport,
    WorkflowArtifactManager,
    WorkflowPhase,
    WorkflowRun,
    WorkflowRunReader,
)


def test_workflow_run_reader_loads_latest_run(tmp_path):
    manager = WorkflowArtifactManager(tmp_path)
    run = WorkflowRun(
        run_id="run-123",
        original_input="Build login MVP",
        current_phase=WorkflowPhase.VERIFY,
        status="needs_follow_up",
        clarified_summary="Implement login",
        success_criteria=["Users can sign in"],
        hypothesis_ids=["H-001"],
    )
    manager.initialize_run(run)
    manager.write_verification(
        run.run_id,
        VerificationReport(summary="Still failing.", verdict="partial"),
    )
    manager.write_completion(
        run.run_id,
        CompletionDecision(
            passed=False,
            status="needs_follow_up",
            summary="Needs follow-up.",
            reasons=["Verification verdict is partial, not pass."],
        ),
    )

    reader = WorkflowRunReader(tmp_path)
    latest = reader.get_latest_run()

    assert latest is not None
    assert latest.run_id == "run-123"
    assert latest.current_phase == "verify"
    assert latest.verification_verdict == "partial"
    assert latest.completion_status == "needs_follow_up"
