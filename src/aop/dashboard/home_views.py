"""Home page dashboard view helpers."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Dict, List

import streamlit as st

from aop.dashboard.workflow_views import get_latest_workflow_run, render_workflow_artifact_panel


def get_project_progress_data(project_path: str) -> dict:
    """Collect project progress, test, and git summary data."""
    result = {
        "hypotheses": {"total": 0, "validated": 0, "testing": 0, "pending": 0},
        "learnings": {"total": 0, "latest": ""},
        "git": {"branch": "unknown", "changes": 0},
        "tests": {"passed": 0, "total": 0},
    }

    aop_dir = Path(project_path) / ".aop"

    hypotheses_file = aop_dir / "hypotheses.json"
    if hypotheses_file.exists():
        try:
            data = json.loads(hypotheses_file.read_text(encoding="utf-8"))
            hypotheses = list(data.get("data", {}).values())
            result["hypotheses"]["total"] = len(hypotheses)
            for hypothesis in hypotheses:
                status = hypothesis.get("state", "pending")
                if status == "validated":
                    result["hypotheses"]["validated"] += 1
                elif status == "testing":
                    result["hypotheses"]["testing"] += 1
                else:
                    result["hypotheses"]["pending"] += 1
        except Exception:
            pass

    learning_file = aop_dir / "learning.json"
    if learning_file.exists():
        try:
            data = json.loads(learning_file.read_text(encoding="utf-8"))
            learnings = data.get("data", {}).get("records", [])
            result["learnings"]["total"] = len(learnings)
            if learnings:
                insights = learnings[-1].get("insights", [])
                if insights:
                    result["learnings"]["latest"] = insights[-1][:50]
        except Exception:
            pass

    try:
        branch_result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=project_path,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
        )
        result["git"]["branch"] = branch_result.stdout.strip() or "unknown"

        status_result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=project_path,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
        )
        changes = [line for line in status_result.stdout.strip().split("\n") if line]
        result["git"]["changes"] = len(changes)
    except Exception:
        pass

    try:
        test_result = subprocess.run(
            ["pytest", "--collect-only", "-q"],
            cwd=project_path,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
        output = test_result.stdout + test_result.stderr
        import re as regex

        match = regex.search(r"(\d+)\s+(?:tests?|items?)\s+(?:collected|selected)", output, regex.IGNORECASE)
        if match:
            result["tests"]["total"] = int(match.group(1))

        run_result = subprocess.run(
            ["pytest", "-q", "--tb=no", "-x"],
            cwd=project_path,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
        )
        run_output = run_result.stdout + run_result.stderr
        passed_match = regex.search(r"(\d+)\s+passed", run_output)
        if passed_match:
            result["tests"]["passed"] = int(passed_match.group(1))
        elif result["tests"]["total"] > 0 and run_result.returncode == 0:
            result["tests"]["passed"] = result["tests"]["total"]
    except Exception:
        pass

    return result


def render_home_header(project_name: str, agents: List[Any], stats: Dict[str, Any]) -> None:
    """Render the dashboard home header."""
    st.markdown(
        f"""
        <div class="header-gradient">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <h1 style="margin: 0; font-size: 1.35rem; color: white; font-weight: 600;">{project_name}</h1>
                    <p style="margin: 0.2rem 0 0 0; color: rgba(255,255,255,0.75); font-size: 0.75rem;">Agent 编排平台</p>
                </div>
                <div style="display: flex; gap: 0.4rem; align-items: center;">
                    <span class="status-badge {'status-online' if agents else 'status-offline'}">{'● ' + str(len(agents)) + ' 个 Agent' if agents else '○ 无 Agent'}</span>
                    <span class="status-badge status-info">📊 {stats['file_count']} 个文件</span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_home_metrics(
    progress_data: Dict[str, Any],
    stats: Dict[str, Any],
    h_validated: int,
    h_total: int,
    progress_pct: int,
) -> None:
    """Render top-line metrics for the home page."""
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="label">假设验证</div>
                <div class="value">{h_validated}/{h_total}</div>
                <div class="progress-bar"><div class="fill" style="width: {progress_pct}%;"></div></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col2:
        tests = progress_data["tests"]
        test_status = f"{tests['passed']}/{tests['total']}" if tests["total"] > 0 else "无"
        test_class = "success" if tests["passed"] == tests["total"] and tests["total"] > 0 else "warning"
        st.markdown(
            f"""
            <div class="metric-card {test_class}">
                <div class="label">测试通过</div>
                <div class="value">{test_status}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col3:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="label">代码行数</div>
                <div class="value">{stats['line_count']:,}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col4:
        git = progress_data["git"]
        git_status = "✓" if git["changes"] == 0 else f"±{git['changes']}"
        st.markdown(
            f"""
            <div class="metric-card {'success' if git['changes'] == 0 else 'warning'}">
                <div class="label">Git: {git['branch']}</div>
                <div class="value">{git_status}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


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


def render_agent_status(
    primary_agent_id: str | None,
    agents: List[Any],
    hypotheses: List[Dict[str, Any]],
) -> None:
    """Render primary and supporting agent status cards."""
    st.markdown(
        """<div class="glass-card"><div class="section-title"><span class="icon">🤖</span> Agent 状态</div></div>""",
        unsafe_allow_html=True,
    )

    if primary_agent_id:
        agent_names = {
            "claude_code": "Claude Code",
            "opencode": "OpenCode",
            "codex": "Codex",
            "openclaw": "OpenClaw",
        }
        agent_name = agent_names.get(primary_agent_id, primary_agent_id)
        is_available = any(agent.id == primary_agent_id for agent in agents)
        badge = "status-online" if is_available else "status-offline"
        status_icon = "●" if is_available else "○"
        status_text = "可用" if is_available else "离线"
        st.markdown(
            f"""
            <div class="agent-row">
                <div><div class="name">{agent_name}</div><div class="role">主 Agent · {status_text}</div></div>
                <span class="status-badge {badge}">{status_icon}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    sub_agents = [
        {"name": "开发者", "role": "实现"},
        {"name": "审查者", "role": "代码审查"},
        {"name": "测试者", "role": "验证"},
    ]
    active_hypotheses = [hypothesis for hypothesis in hypotheses if hypothesis.get("state") == "testing"]

    for agent in sub_agents:
        status = "忙碌" if active_hypotheses else "空闲"
        badge = "status-busy" if active_hypotheses else "status-info"
        icon = "●" if active_hypotheses else "○"
        st.markdown(
            f"""
            <div class="agent-row">
                <div><div class="name">{agent['name']}</div><div class="role">{agent['role']}</div></div>
                <span class="status-badge {badge}">{icon} {status}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_issue_queue(
    hypotheses_pending: int,
    hypotheses_testing: int,
    agents: List[Any],
) -> None:
    """Render outstanding issues for the home sidebar."""
    st.markdown(
        """<div class="glass-card"><div class="section-title"><span class="icon">⚠️</span> 待处理</div></div>""",
        unsafe_allow_html=True,
    )

    issues = []
    if hypotheses_pending > 0:
        issues.append({"text": f"📋 {hypotheses_pending} 个假设待验证", "type": ""})
    if hypotheses_testing > 0:
        issues.append({"text": f"🔬 {hypotheses_testing} 个假设测试中", "type": "info"})
    if not agents:
        issues.append({"text": "🔴 无可用 Agent", "type": "error"})

    if issues:
        for issue in issues:
            st.markdown(
                f"""<div class="issue-badge {issue['type']}">{issue['text']}</div>""",
                unsafe_allow_html=True,
            )
    else:
        st.success("✅ 状态良好")
