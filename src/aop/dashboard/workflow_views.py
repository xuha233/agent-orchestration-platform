"""Workflow run helpers for the Streamlit dashboard."""

from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any, Dict, List

import streamlit as st

from aop.workflow import WorkflowRunReader


PHASE_ORDER = [
    ("clarify", "Clarify"),
    ("plan", "Plan"),
    ("execute", "Execute"),
    ("verify", "Verify"),
    ("gap_close", "Gap Close"),
    ("learn", "Learn"),
    ("complete", "Complete"),
]

STATUS_TONE_MAP = {
    "completed": "status-online",
    "running": "status-busy",
    "partial": "status-info",
    "needs_follow_up": "status-busy",
    "failed": "status-offline",
}

ISSUE_TONE_MAP = {
    "critical": "error",
    "warning": "",
    "info": "info",
}


def _status_badge(label: str, tone: str | None = None) -> str:
    """Render a compact status badge."""
    badge_class = tone or STATUS_TONE_MAP.get(label.lower(), "status-info")
    return f"<span class='status-badge {badge_class}'>{escape(label)}</span>"


def _issue_badge(label: str, tone: str = "warning") -> str:
    """Render a compact issue badge."""
    tone_class = ISSUE_TONE_MAP.get(tone, "")
    suffix = f" {tone_class}" if tone_class else ""
    return f"<div class='issue-badge{suffix}'>{escape(label)}</div>"


def _format_phase_label(phase: str) -> str:
    """Convert internal phase keys to a readable label."""
    for phase_key, label in PHASE_ORDER:
        if phase_key == phase:
            return label
    return phase.replace("_", " ").title() if phase else "-"


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


def render_workspace_header(selected_run: Any, selected_detail: Any) -> None:
    """Render a more product-like header for the selected run."""
    flags: List[str] = []
    if selected_run.has_gaps:
        flags.append("Gaps")
    if selected_run.has_guardrails:
        flags.append("Guardrails")
    if selected_run.completion_status and selected_run.completion_status != "completed":
        flags.append(selected_run.completion_status.replace("_", " ").title())

    summary_line = selected_run.clarified_summary or selected_run.original_input or "No goal recorded."
    success_line = " | ".join(selected_run.success_criteria[:3]) if selected_run.success_criteria else "No explicit success criteria."

    artifact_map = {artifact.title: artifact for artifact in selected_detail.artifacts}
    verification = artifact_map.get("VERIFICATION")
    gaps = verification.metadata.get("gaps", 0) if verification else 0
    plan_check = artifact_map.get("PLAN CHECK")
    critical = plan_check.metadata.get("critical_issues", 0) if plan_check else 0
    important = plan_check.metadata.get("important_issues", 0) if plan_check else 0

    badge_row = " ".join(
        [
            _status_badge(selected_run.status or "-"),
            _status_badge(f"Phase {_format_phase_label(selected_run.current_phase or '')}", "status-info"),
            _status_badge(f"Verify {selected_run.verification_verdict or '-'}", "status-info"),
            _status_badge(f"Completion {selected_run.completion_status or '-'}", "status-busy"),
        ]
    )
    if flags:
        badge_row += " " + " ".join(_status_badge(flag, "status-busy") for flag in flags[:3])

    highlights: List[str] = []
    if critical:
        highlights.append(_issue_badge(f"{critical} critical plan issues", "critical"))
    if important:
        highlights.append(_issue_badge(f"{important} important plan issues", "warning"))
    if gaps:
        highlights.append(_issue_badge(f"{gaps} unresolved verification gaps", "info"))
    if not highlights:
        highlights.append(_issue_badge("Run looks stable. No prominent workflow blockers.", "info"))

    st.markdown(
        f"""
        <div class="header-gradient">
            <div style="display:flex;justify-content:space-between;gap:1rem;align-items:flex-start;flex-wrap:wrap;">
                <div style="flex:2;min-width:320px;">
                    <div style="font-size:0.72rem;letter-spacing:0.08em;text-transform:uppercase;opacity:0.85;">Workflow Workspace</div>
                    <div style="font-size:1.6rem;font-weight:700;line-height:1.2;margin-top:0.3rem;">Run {escape(selected_run.run_id)}</div>
                    <div style="margin-top:0.6rem;display:flex;gap:0.4rem;flex-wrap:wrap;">{badge_row}</div>
                    <div style="margin-top:0.9rem;font-size:0.95rem;line-height:1.5;opacity:0.96;">{escape(summary_line)}</div>
                    <div style="margin-top:0.45rem;font-size:0.78rem;opacity:0.8;">Success cues: {escape(success_line)}</div>
                </div>
                <div style="flex:1;min-width:260px;">
                    <div class="glass-card" style="background:rgba(12,12,12,0.16);border-color:rgba(255,255,255,0.1);">
                        <div class="section-title" style="border-bottom:none;margin-bottom:0.4rem;padding-bottom:0;">
                            <span class="icon">⚡</span> Run Signals
                        </div>
                        {''.join(highlights)}
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_workspace_controls(
    run_options: List[str],
    selected_run_key: str,
    filter_key: str,
    selected_detail: Any,
) -> Any:
    """Render the main interaction controls for the workspace."""
    st.markdown(
        """<div class="glass-card"><div class="section-title"><span class="icon">🎛️</span> Workspace Controls</div></div>""",
        unsafe_allow_html=True,
    )
    controls_col, focus_col = st.columns([1.25, 1.0])
    with controls_col:
        st.checkbox("仅显示待跟进 runs", key=filter_key)
        st.selectbox("Workflow Run", options=run_options, key=selected_run_key)
    with focus_col:
        focused_artifact = render_artifact_focus_selector(selected_detail)
        st.caption(f"Focused artifact: {focused_artifact.title}")
    return focused_artifact


def render_follow_up_queue_controls(
    recent_runs: List[Any],
    selected_run_key: str,
) -> None:
    """Render clickable follow-up queue shortcuts."""
    flagged_runs = [
        run for run in recent_runs
        if run.has_gaps or run.has_guardrails or run.status != "completed"
    ]
    if not flagged_runs:
        return

    st.markdown("**Jump To Follow-up Run**")
    queue_cols = st.columns(min(3, len(flagged_runs[:3])) or 1)
    for index, run in enumerate(flagged_runs[:3]):
        with queue_cols[index % len(queue_cols)]:
            label = f"{run.run_id} ({run.current_phase})"
            if st.button(label, key=f"workflow_jump_{run.run_id}", use_container_width=True):
                st.session_state[selected_run_key] = run.run_id
                st.rerun()


def render_follow_up_details(selected_detail: Any) -> None:
    """Render structured follow-up details for the selected run."""
    artifact_map = {artifact.title: artifact for artifact in selected_detail.artifacts}
    verification = artifact_map.get("VERIFICATION")
    gaps = artifact_map.get("GAPS")
    guardrails = artifact_map.get("GUARDRAILS")
    completion = artifact_map.get("COMPLETION")

    detail_lines: List[str] = []
    if completion and completion.metadata.get("summary"):
        detail_lines.append(f"Completion: {completion.metadata['summary']}")
    for reason in (completion.metadata.get("reason_details", []) if completion else []):
        detail_lines.append(f"Completion reason: {reason}")
    if gaps and gaps.metadata.get("summary"):
        detail_lines.append(f"Gaps: {gaps.metadata['summary']}")
    for gap in (verification.metadata.get("gap_details", []) if verification else []):
        detail_lines.append(f"Gap: {gap}")
    for reason in (guardrails.metadata.get("reason_details", []) if guardrails else []):
        detail_lines.append(f"Guardrail: {reason}")

    if not detail_lines:
        st.caption("当前 run 没有额外的 follow-up 细节。")
        return

    st.markdown("**Follow-up Detail**")
    for line in detail_lines[:8]:
        st.markdown(f"- {line}")


def render_phase_journey(current_phase: str) -> None:
    """Render a simple workflow journey indicator."""
    chips = []
    phase_seen = True
    for phase_key, label in PHASE_ORDER:
        is_current = phase_key == current_phase
        if is_current:
            phase_seen = False
        tone = "#f59e0b" if is_current else "#22c55e" if phase_seen else "#71717a"
        chips.append(
            f"<span style='padding:0.2rem 0.55rem;border:1px solid rgba(255,255,255,0.08);"
            f"border-radius:999px;margin-right:0.35rem;color:{tone};font-size:0.72rem;'>{label}</span>"
        )
    st.markdown(
        f"""
        <div class="glass-card">
            <div class="section-title"><span class="icon">🛣️</span> Phase Journey</div>
            <div style="display:flex;gap:0.35rem;flex-wrap:wrap;">{''.join(chips)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_run_risk_profile(selected_detail: Any) -> None:
    """Render a top-level risk profile for the selected run."""
    artifact_map = {artifact.title: artifact for artifact in selected_detail.artifacts}
    plan_check = artifact_map.get("PLAN CHECK")
    verification = artifact_map.get("VERIFICATION")
    guardrails = artifact_map.get("GUARDRAILS")
    completion = artifact_map.get("COMPLETION")

    st.markdown(
        """<div class="glass-card"><div class="section-title"><span class="icon">🧪</span> Risk Profile</div></div>""",
        unsafe_allow_html=True,
    )
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Plan Critical", str((plan_check.metadata.get("critical_issues", 0) if plan_check else 0)))
    col2.metric("Plan Important", str((plan_check.metadata.get("important_issues", 0) if plan_check else 0)))
    col3.metric("Verify Gaps", str((verification.metadata.get("gaps", 0) if verification else 0)))
    col4.metric("Guardrail Categories", str(len(guardrails.metadata.get("categories", [])) if guardrails else 0))

    highlights: List[str] = []
    if plan_check and plan_check.metadata.get("critical_issues", 0) > 0:
        highlights.append("Plan has critical quality issues.")
    if plan_check and plan_check.metadata.get("important_issues", 0) > 0:
        highlights.append("Plan is under budget/scope pressure.")
    if verification and verification.metadata.get("gaps", 0) > 0:
        highlights.append("Verification still reports unresolved gaps.")
    if guardrails and guardrails.metadata.get("categories", []):
        highlights.append("Guardrails are actively constraining the run.")
    if completion and completion.metadata.get("status"):
        highlights.append(f"Completion status: {completion.metadata['status']}.")

    if highlights:
        for item in highlights[:4]:
            tone = "critical" if "critical" in item.lower() else "info" if "guardrails" in item.lower() else "warning"
            st.markdown(_issue_badge(item, tone), unsafe_allow_html=True)
    else:
        st.markdown(_issue_badge("当前 run 风险较低，未发现明显的计划或执行阻塞。", "info"), unsafe_allow_html=True)


def render_next_action(selected_detail: Any, artifact_focus_key: str) -> None:
    """Render a concise next-step recommendation for the selected run."""
    artifact_map = {artifact.title: artifact for artifact in selected_detail.artifacts}
    plan_check = artifact_map.get("PLAN CHECK")
    verification = artifact_map.get("VERIFICATION")
    guardrails = artifact_map.get("GUARDRAILS")
    completion = artifact_map.get("COMPLETION")

    headline = "当前 run 可以继续观察。"
    targets = ["SUMMARY"]

    if plan_check and plan_check.metadata.get("critical_issues", 0) > 0:
        headline = "先修计划质量问题，再继续执行。"
        targets = ["PLAN CHECK", "PLAN"]
    elif guardrails and guardrails.metadata.get("categories", []):
        headline = "当前 run 已被 guardrails 卡住，建议重新规划。"
        targets = ["GUARDRAILS", "PLAN CHECK", "GAPS"]
    elif verification and verification.metadata.get("gaps", 0) > 0:
        headline = "先处理验证缺口，再决定是否继续修复。"
        targets = ["VERIFICATION", "GAPS", "COMPLETION"]
    elif completion and completion.metadata.get("status") not in {"", "completed"}:
        headline = "当前 run 尚未满足完成条件，先查看 completion 原因。"
        targets = ["COMPLETION", "VERIFICATION"]

    st.markdown(
        """<div class="glass-card"><div class="section-title"><span class="icon">🎯</span> Recommended Next Action</div></div>""",
        unsafe_allow_html=True,
    )
    st.markdown(_issue_badge(headline, "info"), unsafe_allow_html=True)
    st.caption("Suggested focus: " + " -> ".join(targets))

    action_cols = st.columns(len(targets))
    for index, target in enumerate(targets):
        with action_cols[index]:
            if st.button(
                f"Open {target}",
                key=f"next_action_{selected_detail.summary.run_id}_{target}",
                use_container_width=True,
            ):
                st.session_state[artifact_focus_key] = target
                st.rerun()


def recommend_focus_targets(selected_detail: Any) -> List[str]:
    """Return the best next artifacts to focus based on current risk state."""
    artifact_map = {artifact.title: artifact for artifact in selected_detail.artifacts}
    plan_check = artifact_map.get("PLAN CHECK")
    verification = artifact_map.get("VERIFICATION")
    guardrails = artifact_map.get("GUARDRAILS")
    completion = artifact_map.get("COMPLETION")

    if plan_check and plan_check.metadata.get("critical_issues", 0) > 0:
        return ["PLAN CHECK", "PLAN"]
    if guardrails and guardrails.metadata.get("categories", []):
        return ["GUARDRAILS", "PLAN CHECK", "GAPS"]
    if verification and verification.metadata.get("gaps", 0) > 0:
        return ["VERIFICATION", "GAPS", "COMPLETION"]
    if completion and completion.metadata.get("status") not in {"", "completed"}:
        return ["COMPLETION", "VERIFICATION"]
    return ["SUMMARY"]


def render_run_comparison(selected_run: Any, recent_runs: List[Any]) -> None:
    """Render a compact comparison against the previous run."""
    previous_run = next((run for run in recent_runs if run.run_id != selected_run.run_id), None)
    if previous_run is None:
        st.caption("暂无可对比的上一条 workflow run。")
        return

    st.markdown("**Compare With Previous Run**")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Previous Run", previous_run.run_id)
    col2.metric("Prev Phase", previous_run.current_phase or "-")
    col3.metric("Prev Verify", previous_run.verification_verdict or "-")
    col4.metric("Prev Completion", previous_run.completion_status or "-")

    delta_bits = []
    if selected_run.status != previous_run.status:
        delta_bits.append(f"status {previous_run.status} -> {selected_run.status}")
    if selected_run.current_phase != previous_run.current_phase:
        delta_bits.append(f"phase {previous_run.current_phase} -> {selected_run.current_phase}")
    if selected_run.verification_verdict != previous_run.verification_verdict:
        delta_bits.append(
            f"verify {previous_run.verification_verdict or '-'} -> {selected_run.verification_verdict or '-'}"
        )
    if selected_run.completion_status != previous_run.completion_status:
        delta_bits.append(
            f"completion {previous_run.completion_status or '-'} -> {selected_run.completion_status or '-'}"
        )

    if delta_bits:
        st.caption(" | ".join(delta_bits))
    else:
        st.caption("与上一条 run 的核心状态一致。")


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
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Passed", str(metadata.get("passed", "-")))
        col2.metric("Issues", str(metadata.get("issues", 0)))
        col3.metric("Critical", str(metadata.get("critical_issues", 0)))
        col4.metric("Important", str(metadata.get("important_issues", 0)))
        summary = metadata.get("summary")
        if summary:
            st.caption(summary)
        issue_details = metadata.get("issue_details", [])
        for issue in issue_details[:3]:
            st.markdown(f"- {issue}")
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
        col1, col2, col3 = st.columns(3)
        col1.metric("Should Stop", str(metadata.get("should_stop", "-")))
        col2.metric("Reasons", str(metadata.get("reasons", 0)))
        categories = metadata.get("categories", [])
        col3.metric("Categories", str(len(categories)))
        if categories:
            st.caption(" | ".join(categories))
    elif artifact.title == "LEARNINGS":
        st.metric("Learning Records", str(metadata.get("records", 0)))
    elif artifact.title == "COMPLETION":
        col1, col2, col3 = st.columns(3)
        col1.metric("Passed", str(metadata.get("passed", "-")))
        col2.metric("Status", str(metadata.get("status", "-")))
        col3.metric("Reasons", str(metadata.get("reasons", 0)))


def render_artifact_focus_selector(selected_detail: Any) -> Any:
    """Choose a single artifact to focus on instead of scanning all tabs."""
    artifact_titles = [artifact.title for artifact in selected_detail.artifacts]
    focus_key = f"artifact_focus_{selected_detail.summary.run_id}"
    recommended_targets = recommend_focus_targets(selected_detail)
    recommended_focus = next(
        (target for target in recommended_targets if target in artifact_titles),
        "SUMMARY" if "SUMMARY" in artifact_titles else artifact_titles[0],
    )
    if focus_key not in st.session_state or st.session_state[focus_key] not in artifact_titles:
        st.session_state[focus_key] = recommended_focus

    current_focus = st.session_state.get(focus_key)
    if current_focus == "SUMMARY" and recommended_focus != "SUMMARY":
        st.session_state[focus_key] = recommended_focus

    selected_title = st.selectbox("Focus Artifact", options=artifact_titles, key=focus_key)
    return next(
        artifact for artifact in selected_detail.artifacts if artifact.title == selected_title
    )


def render_workflow_artifact_panel(project_path: str, workflow_run) -> None:
    """Render the workflow artifact workspace for a project."""
    if not workflow_run:
        st.info("暂无 workflow run artifact")
        return

    reader = WorkflowRunReader(Path(project_path))
    recent_runs = reader.list_runs(limit=12)
    state_key = f"workflow_run_select_{Path(project_path).resolve()}"
    filter_key = f"workflow_follow_up_only_{Path(project_path).resolve()}"

    st.markdown(
        """<div class="glass-card"><div class="section-title"><span class="icon">🧭</span> Workflow Artifacts</div></div>""",
        unsafe_allow_html=True,
    )

    render_workflow_run_overview(recent_runs)
    render_follow_up_queue_controls(recent_runs, state_key)
    st.markdown("---")

    filtered_runs = (
        [
            run for run in recent_runs
            if run.has_gaps or run.has_guardrails or run.status != "completed"
        ]
        if st.session_state.get(filter_key, False)
        else recent_runs
    )
    run_options = [run.run_id for run in filtered_runs] or [workflow_run.run_id]

    if state_key not in st.session_state or st.session_state[state_key] not in run_options:
        st.session_state[state_key] = workflow_run.run_id if workflow_run.run_id in run_options else run_options[0]

    selected_run_id = st.session_state[state_key]
    selected_detail = get_workflow_run_detail(project_path, selected_run_id)
    if not selected_detail:
        st.warning("无法读取所选 workflow run 详情")
        return

    selected_run = selected_detail.summary

    render_workspace_header(selected_run, selected_detail)
    focused_artifact = render_workspace_controls(run_options, state_key, filter_key, selected_detail)
    if st.session_state[state_key] != selected_run.run_id:
        selected_detail = get_workflow_run_detail(project_path, st.session_state[state_key])
        if not selected_detail:
            st.warning("无法读取切换后的 workflow run 详情")
            return
        selected_run = selected_detail.summary
        focused_artifact = render_artifact_focus_selector(selected_detail)

    stats_col1, stats_col2, stats_col3, stats_col4 = st.columns(4)
    stats_col1.metric("Phase", _format_phase_label(selected_run.current_phase or ""))
    stats_col2.metric("Status", selected_run.status or "-")
    stats_col3.metric("Verify", selected_run.verification_verdict or "-")
    stats_col4.metric("Completion", selected_run.completion_status or "-")

    render_phase_journey(selected_run.current_phase or "")

    render_run_risk_profile(selected_detail)
    st.markdown("---")

    compare_col, followup_col = st.columns(2)
    with compare_col:
        render_run_comparison(selected_run, recent_runs)
    with followup_col:
        render_follow_up_details(selected_detail)

    st.markdown("---")
    render_next_action(
        selected_detail,
        artifact_focus_key=f"artifact_focus_{selected_detail.summary.run_id}",
    )
    st.markdown("---")

    st.markdown(
        """<div class="glass-card"><div class="section-title"><span class="icon">📄</span> Focused Artifact</div></div>""",
        unsafe_allow_html=True,
    )
    st.caption(focused_artifact.filename)
    if focused_artifact.exists:
        render_artifact_metadata_summary(focused_artifact)
        if focused_artifact.metadata:
            st.markdown("---")
        st.code(focused_artifact.content, language="markdown")
    else:
        st.info(f"当前无 {focused_artifact.filename}")
