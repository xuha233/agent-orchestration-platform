"""Tests for workflow run reader."""

from aop.workflow import (
    CompletionDecision,
    VerificationReport,
    WorkflowArtifactManager,
    WorkflowArtifactDocument,
    WorkflowPhase,
    WorkflowPlan,
    WorkflowRun,
    WorkflowRunDetail,
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


def test_workflow_run_reader_loads_run_detail_with_artifacts(tmp_path):
    manager = WorkflowArtifactManager(tmp_path)
    run = WorkflowRun(
        run_id="run-detail",
        original_input="Build dashboard",
        current_phase=WorkflowPhase.COMPLETE,
        status="completed",
    )
    manager.initialize_run(run)
    manager.write_plan(
        run.run_id,
        WorkflowPlan(
            summary="Ship workflow dashboard",
            goals=["Show workflow artifacts"],
            verification_steps=["Render plan and verification"],
        ),
    )
    manager.write_verification(
        run.run_id,
        VerificationReport(
            summary="All artifacts available.",
            verdict="pass",
            truths=["Dashboard can read workflow files."],
        ),
    )
    manager.write_summary(run.run_id, "Workflow run completed.")

    reader = WorkflowRunReader(tmp_path)
    detail = reader.load_run_detail(run.run_id)

    assert isinstance(detail, WorkflowRunDetail)
    assert detail.summary.run_id == "run-detail"
    assert len(detail.artifacts) == 10
    assert all(isinstance(artifact, WorkflowArtifactDocument) for artifact in detail.artifacts)

    artifact_titles = {artifact.title: artifact for artifact in detail.artifacts}
    assert artifact_titles["RUN"].exists is True
    assert artifact_titles["PLAN"].exists is True
    assert artifact_titles["VERIFICATION"].exists is True
    assert artifact_titles["SUMMARY"].exists is True
    assert artifact_titles["EXECUTION"].exists is False
    assert "Ship workflow dashboard" in artifact_titles["PLAN"].content
    assert artifact_titles["PLAN"].metadata["goals"] == 1
    assert artifact_titles["VERIFICATION"].metadata["verdict"] == "pass"
