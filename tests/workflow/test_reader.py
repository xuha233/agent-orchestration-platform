"""Tests for workflow run reader."""

from aop.workflow import (
    CompletionDecision,
    GuardrailReport,
    PlanCheckReport,
    PlanCheckIssue,
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
    manager.write_plan_check(
        run.run_id,
        PlanCheckReport(
            passed=False,
            summary="Plan has budget pressure.",
            issues=[
                PlanCheckIssue("critical", "Top-level verification is incomplete."),
                PlanCheckIssue("important", "Plan exceeds the total effort budget guardrail."),
            ],
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
    assert artifact_titles["COMPLETION"].metadata["reason_details"] == []
    assert artifact_titles["PLAN CHECK"].metadata["critical_issues"] == 1
    assert artifact_titles["PLAN CHECK"].metadata["important_issues"] == 1


def test_workflow_run_reader_assigns_triage_labels(tmp_path):
    manager = WorkflowArtifactManager(tmp_path)

    for index in range(3):
        run = WorkflowRun(
            run_id=f"run-clean-{index}",
            original_input="Harden desktop flow",
            current_phase=WorkflowPhase.COMPLETE,
            status="completed",
        )
        manager.initialize_run(run)
        manager.write_verification(
            run.run_id,
            VerificationReport(summary="Looks good.", verdict="pass"),
        )
        manager.write_completion(
            run.run_id,
            CompletionDecision(
                passed=True,
                status="completed",
                summary="Completed cleanly.",
                reasons=[],
            ),
        )

    flaky = WorkflowRun(
        run_id="run-flaky",
        original_input="Retry flaky path",
        current_phase=WorkflowPhase.VERIFY,
        status="needs_follow_up",
    )
    manager.initialize_run(flaky)
    manager.write_verification(
        flaky.run_id,
        VerificationReport(summary="Guardrail and gaps found.", verdict="partial"),
    )
    manager.write_completion(
        flaky.run_id,
        CompletionDecision(
            passed=False,
            status="needs_follow_up",
            summary="Needs follow-up.",
            reasons=["Verification verdict is partial, not pass."],
        ),
    )
    manager.write_guardrails(
        flaky.run_id,
        GuardrailReport(
            should_stop=True,
            summary="Repeated verification failure.",
            categories=["repeated_failures"],
            reasons=["Repeated verification failure"],
        ),
    )

    reader = WorkflowRunReader(tmp_path)
    runs = reader.list_runs()

    assert runs[0].run_id == "run-flaky"
    assert runs[0].attention_tags == ["needs_follow_up", "flaky"]
    assert runs[0].priority_rank == 100
    assert "guardrails" in runs[0].triage_summary.lower()
    assert any("guardrail" in item for item in runs[0].triage_evidence)
    assert any("verification verdict" in item for item in runs[0].triage_evidence)

    stable_run = next(run for run in runs if run.run_id == "run-clean-2")
    assert stable_run.attention_tags == ["stable"]
    assert stable_run.priority_rank == 20
    assert "stable" in stable_run.triage_summary.lower()
