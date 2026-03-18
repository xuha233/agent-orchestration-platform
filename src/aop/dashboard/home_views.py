"""Home page dashboard view helpers."""

from __future__ import annotations

from typing import Any, Dict, List

import streamlit as st

from aop.dashboard.workflow_views import get_latest_workflow_run, render_workflow_artifact_panel


def render_project_progress(
    project_path: str,
    sprint: Dict[str, Any] | None,
    hypotheses: List[Dict[str, Any]],
) -> None:
    """Render project progress and workflow workspace."""
    st.markdown(
        """<div class="glass-card"><div class="section-title"><span class="icon">📈</span> 项目进度</div></div>""",
        unsafe_allow_html=True,
    )

    workflow_run = get_latest_workflow_run(".")

    if sprint:
        st.markdown(f"**当前冲刺**: {sprint.get('original_input', '无')[:60]}")
        st.caption(f"ID: {sprint.get('sprint_id', '-')}")
    else:
        st.info("暂无活跃冲刺")

    if workflow_run:
        flags = []
        if workflow_run.has_gaps:
            flags.append("gaps")
        if workflow_run.has_guardrails:
            flags.append("guardrails")
        flag_text = f" | Flags: {', '.join(flags)}" if flags else ""
        st.markdown(
            f"**Workflow Run**: `{workflow_run.run_id}` | "
            f"Status: `{workflow_run.status}` | "
            f"Phase: `{workflow_run.current_phase}` | "
            f"Verify: `{workflow_run.verification_verdict or '-'}`"
            f"{flag_text}"
        )

    pending = [hypothesis for hypothesis in hypotheses if hypothesis.get("state") == "pending"]
    if pending:
        st.markdown(f"**下一个假设**: {pending[0].get('statement', '-')[:50]}...")

    st.markdown("---")
    render_workflow_artifact_panel(project_path, workflow_run)


def render_recent_activity(hypotheses: List[Dict[str, Any]]) -> None:
    """Render recent hypothesis activity feed."""
    st.markdown(
        """<div class="glass-card"><div class="section-title"><span class="icon">📋</span> 最近活动</div></div>""",
        unsafe_allow_html=True,
    )

    activities = []
    for hypothesis in hypotheses[:6]:
        state = hypothesis.get("state", "pending")
        statement = hypothesis.get("statement", "")[:30]
        icon = "✅" if state == "validated" else "🔬" if state == "testing" else "📝"
        state_text = "已验证" if state == "validated" else "测试中" if state == "testing" else "待处理"
        activities.append({"icon": icon, "text": statement + "...", "state": state_text})

    if activities:
        for activity in activities:
            st.markdown(
                f"""<div class="activity-item"><span class="icon">{activity['icon']}</span><span class="text">{activity['text']}</span><span style="color: var(--text-muted); font-size: 0.65rem;">{activity['state']}</span></div>""",
                unsafe_allow_html=True,
            )
    else:
        st.info("暂无最近活动")


def render_current_iteration(memory_content: str, parse_md_section) -> None:
    """Render current iteration summary from project memory."""
    st.markdown(
        """<div class="glass-card"><div class="section-title"><span class="icon">🎯</span> 当前迭代</div></div>""",
        unsafe_allow_html=True,
    )

    if memory_content:
        in_progress = parse_md_section(memory_content, "进行中")
        if in_progress:
            st.markdown(in_progress[:350])
        else:
            st.info("暂无进行中的迭代目标")
    else:
        st.info("未找到项目记忆文件")
