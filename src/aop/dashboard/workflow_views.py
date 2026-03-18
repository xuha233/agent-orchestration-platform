"""Workflow run helpers for the Streamlit dashboard."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import streamlit as st

from aop.workflow import WorkflowRunReader


def get_latest_workflow_run(project_path: str = "."):
    """Return the latest workflow run summary for the project."""
    try:
        reader = WorkflowRunReader(Path(project_path))
        return reader.get_latest_run()
    except Exception:
        return None


def get_workflow_run_detail(project_path: str, run_id: str):
    """Return detailed workflow artifacts for a selected run."""
    try:
        reader = WorkflowRunReader(Path(project_path))
        return reader.load_run_detail(run_id)
    except Exception:
        return None


def summarize_workflow_runs(runs: List[Any]) -> Dict[str, int]:
    """Build a compact status summary for recent workflow runs."""
    summary = {
        "total": len(runs),
        "completed": 0,
        "active": 0,
        "follow_up": 0,
        "with_gaps": 0,
        "with_guardrails": 0,
    }
    for run in runs:
        if run.status == "completed":
            summary["completed"] += 1
        elif run.status in {"running", "partial"}:
            summary["active"] += 1
        else:
            summary["follow_up"] += 1
        if run.has_gaps:
            summary["with_gaps"] += 1
        if run.has_guardrails:
            summary["with_guardrails"] += 1
    return summary


def render_workflow_run_overview(recent_runs: List[Any]) -> None:
    """Render high-level run health and follow-up queue."""
    if not recent_runs:
        return

    counts = summarize_workflow_runs(recent_runs)
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Recent Runs", str(counts["total"]))
    col2.metric("Completed", str(counts["completed"]))
    col3.metric("Needs Follow-up", str(counts["follow_up"]))
    col4.metric("Gap Flags", str(counts["with_gaps"]))

    flagged_runs = [
        run for run in recent_runs
        if run.has_gaps or run.has_guardrails or run.status != "completed"
    ]
    if not flagged_runs:
        st.caption("最近的 workflow runs 状态稳定，无待跟进项。")
        return

    st.markdown("**Follow-up Queue**")
    for run in flagged_runs[:5]:
        badges = []
        if run.has_gaps:
            badges.append("gaps")
        if run.has_guardrails:
            badges.append("guardrails")
        if run.completion_status:
            badges.append(run.completion_status)
        badge_text = " | ".join(badges) if badges else run.status
        st.markdown(
            f"- `{run.run_id}` | phase `{run.current_phase}` | status `{run.status}` | {badge_text}"
        )


def render_artifact_metadata_summary(artifact: Any) -> None:
    """Render compact structured summaries for key workflow artifacts."""
    metadata = getattr(artifact, "metadata", {}) or {}
    if not metadata:
        return

    if artifact.title == "PLAN":
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Goals", str(metadata.get("goals", 0)))
        col2.metric("Tasks", str(metadata.get("tasks", 0)))
        col3.metric("Checks", str(metadata.get("verification_steps", 0)))
        col4.metric("Risks", str(metadata.get("risks", 0)))
    elif artifact.title == "PLAN CHECK":
        col1, col2 = st.columns(2)
        col1.metric("Passed", str(metadata.get("passed", "-")))
        col2.metric("Issues", str(metadata.get("issues", 0)))
        summary = metadata.get("summary")
        if summary:
            st.caption(summary)
    elif artifact.title == "EXECUTION":
        col1, col2, col3 = st.columns(3)
        col1.metric("Results", str(metadata.get("results", 0)))
        col2.metric("Failed", str(metadata.get("failed", 0)))
        col3.metric("Repair Waves", str(metadata.get("repair_waves", 0)))
    elif artifact.title == "VERIFICATION":
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Verdict", str(metadata.get("verdict", "-")))
        col2.metric("Truths", str(metadata.get("truths", 0)))
        col3.metric("Gaps", str(metadata.get("gaps", 0)))
        col4.metric("Checks", str(metadata.get("checks", 0)))
    elif artifact.title == "GAPS":
        col1, col2, col3 = st.columns(3)
        col1.metric("Gap Items", str(metadata.get("gaps", 0)))
        col2.metric("Repair Tasks", str(metadata.get("repair_tasks", 0)))
        col3.metric("Next Steps", str(metadata.get("next_steps", 0)))
    elif artifact.title == "GUARDRAILS":
        col1, col2 = st.columns(2)
        col1.metric("Should Stop", str(metadata.get("should_stop", "-")))
        col2.metric("Reasons", str(metadata.get("reasons", 0)))
    elif artifact.title == "LEARNINGS":
        st.metric("Learning Records", str(metadata.get("records", 0)))
    elif artifact.title == "COMPLETION":
        col1, col2, col3 = st.columns(3)
        col1.metric("Passed", str(metadata.get("passed", "-")))
        col2.metric("Status", str(metadata.get("status", "-")))
        col3.metric("Reasons", str(metadata.get("reasons", 0)))


def render_workflow_artifact_panel(project_path: str, workflow_run) -> None:
    """Render the workflow artifact workspace for a project."""
    if not workflow_run:
        st.info("暂无 workflow run artifact")
        return

    reader = WorkflowRunReader(Path(project_path))
    recent_runs = reader.list_runs(limit=12)
    run_options = [run.run_id for run in recent_runs] or [workflow_run.run_id]
    default_index = run_options.index(workflow_run.run_id) if workflow_run.run_id in run_options else 0

    selected_run_id = st.selectbox(
        "Workflow Run",
        options=run_options,
        index=default_index,
        key=f"workflow_run_select_{Path(project_path).resolve()}",
    )
    selected_detail = get_workflow_run_detail(project_path, selected_run_id)
    if not selected_detail:
        st.warning("无法读取所选 workflow run 详情")
        return

    selected_run = selected_detail.summary

    st.markdown(
        """<div class="glass-card"><div class="section-title"><span class="icon">🧭</span> Workflow Artifacts</div></div>""",
        unsafe_allow_html=True,
    )

    render_workflow_run_overview(recent_runs)
    st.markdown("---")

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Phase", selected_run.current_phase or "-")
    col2.metric("Status", selected_run.status or "-")
    col3.metric("Verify", selected_run.verification_verdict or "-")
    flags = []
    if selected_run.has_gaps:
        flags.append("gaps")
    if selected_run.has_guardrails:
        flags.append("guardrails")
    col4.metric("Completion", selected_run.completion_status or "-")
    col5.metric("Flags", ", ".join(flags) if flags else "-")

    if selected_run.original_input:
        st.markdown(f"**Goal**: {selected_run.original_input}")
    if selected_run.clarified_summary:
        st.caption(f"Clarified: {selected_run.clarified_summary}")
    if selected_run.success_criteria:
        st.caption("Success Criteria: " + " | ".join(selected_run.success_criteria[:4]))

    artifact_tabs = st.tabs([artifact.title for artifact in selected_detail.artifacts])
    for tab, artifact in zip(artifact_tabs, selected_detail.artifacts):
        with tab:
            st.caption(artifact.filename)
            if artifact.exists:
                render_artifact_metadata_summary(artifact)
                if artifact.metadata:
                    st.markdown("---")
                st.code(artifact.content, language="markdown")
            else:
                st.info(f"当前无 {artifact.filename}")
