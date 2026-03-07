"""
AOP Dashboard - 对话式界面

Run with: streamlit run app.py
Or: aop dashboard
"""

import time
import asyncio
import threading
import re
import sys
import streamlit as st
import json
import subprocess
from pathlib import Path
from typing import Optional, Dict, List, Any
from datetime import datetime

from aop.primary import get_registry
from aop.primary.base import PrimaryAgent
from aop.primary.workspace import WorkspaceManager, Workspace, SettingsManager
from aop.primary.listener import start_listener, submit_command
from aop.dashboard.logger import get_dashboard_logger, setup_dashboard_logging

import logging
_logger = logging.getLogger(__name__)

# Page config
from aop.memory import build_agent_system_prompt
st.set_page_config(
    page_title="AOP Dashboard",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown("""
<style>
    .welcome-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 2rem;
        border-radius: 1rem;
        margin: 1rem 0;
    }
    .quick-card {
        background: #f8f9fa;
        border: 1px solid #e9ecef;
        border-radius: 0.5rem;
        padding: 1rem;
        cursor: pointer;
        transition: all 0.2s;
    }
    .quick-card:hover {
        border-color: #667eea;
        box-shadow: 0 2px 8px rgba(102, 126, 234, 0.2);
    }
    .status-badge {
        display: inline-block;
        padding: 0.25rem 0.5rem;
        border-radius: 0.25rem;
        font-size: 0.875rem;
    }
    .status-ok { background: #d4edda; color: #155724; }
    .status-error { background: #f8d7da; color: #721c24; }
</style>
""", unsafe_allow_html=True)


# ============ 初始化 ============

# 启动命令监听器（模块加载时立即启动）
_listener_started = False

def check_openclaw_status() -> tuple:
    """检查 OpenClaw Gateway 是否运行
    返回: (is_running: bool, status_text: str)
    """
    import socket
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex(("127.0.0.1", 18792))
        sock.close()
        if result == 0:
            return True, "运行中"
        else:
            return False, "未运行"
    except Exception as e:
        return False, f"检测失败: {e}"


def ensure_listener():
    """确保监听器已启动"""
    global _listener_started
    if not _listener_started:
        try:
            start_listener()
            _listener_started = True
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Failed to start listener: {e}")

# 模块加载时启动
ensure_listener()

# 设置 Dashboard 日志
setup_dashboard_logging()


def init_session_state():
    """初始化 session state"""
    if "workspace_manager" not in st.session_state:
        st.session_state.workspace_manager = WorkspaceManager()
    if "settings_manager" not in st.session_state:
        st.session_state.settings_manager = SettingsManager()
    if "current_workspace" not in st.session_state:
        st.session_state.current_workspace = None
    if "current_agent" not in st.session_state:
        st.session_state.current_agent = None
    # 执行状态
    if "execution_running" not in st.session_state:
        st.session_state.execution_running = False
    if "execution_thread" not in st.session_state:
        st.session_state.execution_thread = None
    if "execution_result" not in st.session_state:
        st.session_state.execution_result = None
    if "execution_error" not in st.session_state:
        st.session_state.execution_error = None
    if "execution_start_time" not in st.session_state:
        st.session_state.execution_start_time = None
    # 用于立即取消的 Event（线程安全）
    if "cancel_event" not in st.session_state:
        st.session_state.cancel_event = threading.Event()
    # 后台执行结果存储（避免在线程中直接修改 session_state）
    if "execution_result_buffer" not in st.session_state:
        st.session_state.execution_result_buffer = None
    if "execution_error_buffer" not in st.session_state:
        st.session_state.execution_error_buffer = None
    # 按项目隔离的对话历史存储
    if "workspace_messages" not in st.session_state:
        st.session_state.workspace_messages = {}  # {workspace_id: [messages]}
    if "workspace_sessions" not in st.session_state:
        st.session_state.workspace_sessions = {}  # {workspace_id: session_id}
    # 流式输出支持
    if "token_queue" not in st.session_state:
        st.session_state.token_queue = None
    if "streaming_content" not in st.session_state:
        st.session_state.streaming_content = ""


def get_current_workspace_id() -> Optional[str]:
    """获取当前工作区的唯一标识"""
    if st.session_state.current_workspace:
        return st.session_state.current_workspace.id
    return None


def get_messages_for_workspace(workspace_id: Optional[str]) -> list:
    """获取指定工作区的对话历史"""
    if not workspace_id:
        return []
    if 'workspace_messages' not in st.session_state:
        st.session_state.workspace_messages = {}
    return st.session_state.workspace_messages.get(workspace_id, [])


def save_messages_for_workspace(workspace_id: Optional[str], messages: list) -> None:
    """保存指定工作区的对话历史"""
    if not workspace_id:
        return
    st.session_state.workspace_messages[workspace_id] = messages


def get_session_id_for_workspace(workspace_id: Optional[str]) -> Optional[str]:
    """获取指定工作区的 session_id"""
    if not workspace_id:
        return None
    if 'workspace_sessions' not in st.session_state:
        st.session_state.workspace_sessions = {}
    return st.session_state.workspace_sessions.get(workspace_id)


def save_session_id_for_workspace(workspace_id: Optional[str], session_id: Optional[str]) -> None:
    """保存指定工作区的 session_id"""
    if not workspace_id:
        return
    if session_id:
        st.session_state.workspace_sessions[workspace_id] = session_id


def get_available_agents() -> list:
    """获取可用的 Agent 列表"""
    registry = get_registry()
    return registry.list_available()


def get_agent_by_id(agent_id: str) -> Optional[PrimaryAgent]:
    """根据 ID 获取 Agent"""
    registry = get_registry()
    return registry.get(agent_id)


# ============ 数据读取辅助函数 ============

def get_aop_dir() -> Path:
    """获取 .aop 目录路径"""
    # 优先使用当前工作区的 .aop 目录
    if st.session_state.current_workspace:
        ws_path = Path(st.session_state.current_workspace.project_path)
        aop_dir = ws_path / ".aop"
        if aop_dir.exists():
            return aop_dir
    # 回退到当前工作目录
    return Path.cwd() / ".aop"


def read_aop_file(filename: str) -> Optional[str]:
    """读取 .aop 目录下的文件内容"""
    aop_dir = get_aop_dir()
    file_path = aop_dir / filename
    if file_path.exists():
        return file_path.read_text(encoding="utf-8")
    return None


def read_aop_json(filename: str) -> Optional[Dict]:
    """读取 .aop 目录下的 JSON 文件"""
    content = read_aop_file(filename)
    if content:
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass
    return None


def get_project_stats() -> Dict[str, Any]:
    """获取项目统计数据"""
    stats = {
        "file_count": 0,
        "line_count": 0,
        "py_files": 0,
        "js_files": 0,
        "md_files": 0,
    }

    if st.session_state.current_workspace:
        project_path = Path(st.session_state.current_workspace.project_path)
    else:
        project_path = Path.cwd()

    if not project_path.exists():
        return stats

    try:
        # 统计文件数量
        for ext, key in [(".py", "py_files"), (".js", "js_files"), (".md", "md_files")]:
            files = list(project_path.rglob(f"*{ext}"))
            # 排除 node_modules, .git, venv 等目录
            files = [f for f in files if not any(p in f.parts for p in ["node_modules", ".git", "venv", "__pycache__", ".venv", "build", "dist"])]
            stats[key] = len(files)

        # 总文件数
        all_files = list(project_path.rglob("*"))
        all_files = [f for f in all_files if f.is_file() and not any(p in f.parts for p in ["node_modules", ".git", "venv", "__pycache__", ".venv", "build", "dist"])]
        stats["file_count"] = len(all_files)

        # 代码行数（Python 文件）
        py_files = list(project_path.rglob("*.py"))
        py_files = [f for f in py_files if not any(p in f.parts for p in ["node_modules", ".git", "venv", "__pycache__", ".venv", "build", "dist"])]
        total_lines = 0
        for f in py_files[:100]:  # 限制读取数量
            try:
                total_lines += len(f.read_text(encoding="utf-8").splitlines())
            except (OSError, UnicodeDecodeError):
                pass
        stats["line_count"] = total_lines

    except Exception as e:
        _logger.warning(f"获取项目统计失败: {e}")

    return stats


def get_hypotheses_data() -> List[Dict]:
    """获取假设数据"""
    data = read_aop_json("hypotheses.json/hypotheses.json")
    if data and "data" in data:
        return list(data["data"].values())
    return []


def get_sprint_data() -> Optional[Dict]:
    """获取最新的 Sprint 数据"""
    aop_dir = get_aop_dir()
    sprints_dir = aop_dir / "sprints"
    if sprints_dir.exists():
        sprint_files = sorted(sprints_dir.glob("sprint-*.json"), reverse=True)
        if sprint_files:
            try:
                return json.loads(sprint_files[0].read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError, UnicodeDecodeError):
                pass
    return None


def parse_md_section(content: str, section_title: str) -> str:
    """从 Markdown 内容中提取指定章节"""
    if not content:
        return ""
    lines = content.split("\n")
    in_section = False
    section_lines = []

    for line in lines:
        if line.startswith("## "):
            if section_title in line:
                in_section = True
            elif in_section:
                break
        elif in_section:
            section_lines.append(line)

    return "\n".join(section_lines).strip()


# ============ 页面组件 ============

def render_sidebar():
    """渲染侧边栏"""
    with st.sidebar:
        st.title("🤖 AOP")

        # 获取设置，决定是否显示开发者控制台
        sm = st.session_state.settings_manager
        show_dev_console = sm.get_show_dev_console()

        pages = ["🏠 首页", "💬 敏捷教练", "📚 项目记忆", "📁 工作区", "⚙️ 设置"]
        if show_dev_console:
            pages.append("🖥️ 开发者控制台")

        page = st.radio(
            "导航",
            pages,
            label_visibility="collapsed",
        )

        st.markdown("---")

        # 项目快速切换下拉菜单
        wm = st.session_state.workspace_manager
        workspaces = wm.list_workspaces()

        if workspaces:
            st.markdown("**项目切换**")
            workspace_options = {ws.name: ws for ws in workspaces}
            current_ws = st.session_state.current_workspace
            current_name = current_ws.name if current_ws else list(workspace_options.keys())[0]

            selected_name = st.selectbox(
                "选择项目",
                options=list(workspace_options.keys()),
                index=list(workspace_options.keys()).index(current_name) if current_name in workspace_options else 0,
                label_visibility="collapsed",
                key="sidebar_project_selector",
            )

            selected_ws = workspace_options.get(selected_name)
            if selected_ws and selected_ws.id != (current_ws.id if current_ws else None):
                st.session_state.current_workspace = selected_ws
                wm.set_current_workspace(selected_ws.id)

                # 检查新工作区的 primary_agent 设置并更新 current_agent
                if selected_ws.primary_agent:
                    agents = get_available_agents()
                    for agent in agents:
                        if agent.id == selected_ws.primary_agent:
                            st.session_state.current_agent = agent
                            break

                st.rerun()

        st.markdown("---")

        # 当前 Agent 状态
        if st.session_state.current_agent:
            agent = st.session_state.current_agent
            st.markdown(f"**Agent**: {agent.name}")

        st.markdown("---")
        st.markdown("""
**AOP v0.4.0**

[GitHub](https://github.com/xuha233/agent-orchestration-platform)
""")

    return page


def render_welcome():
    """渲染欢迎引导（首次使用）"""
    st.markdown("""
<div class="welcome-card">
    <h2>👋 欢迎使用 AOP</h2>
    <p>AOP (Agent Orchestration Platform) 是一个智能代理编排平台。</p>
    <p>选择一个项目开始你的 AI 辅助编程之旅！</p>
</div>
""", unsafe_allow_html=True)

    st.markdown("### 快速开始")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("""
<div class="quick-card">
    <h4>📁 选择项目</h4>
    <p>从左侧工作区选择或创建项目工作区</p>
</div>
""", unsafe_allow_html=True)

    with col2:
        st.markdown("""
<div class="quick-card">
    <h4>🤖 选择 Agent</h4>
    <p>选择可用的 AI Agent (Claude Code / OpenCode)</p>
</div>
""", unsafe_allow_html=True)

    with col3:
        st.markdown("""
<div class="quick-card">
    <h4>💬 开始对话</h4>
    <p>向 AI 提问，获取代码帮助和建议</p>
</div>
""", unsafe_allow_html=True)




def execute_agent_task(agent, workspace, prompt, session_id, workspace_id, cancel_event, result_buffer, error_buffer):
    """在后台线程中执行 Agent 任务

    Args:
        agent: PrimaryAgent 实例
        workspace: 工作区
        prompt: 用户输入
        session_id: 会话 ID（用于恢复对话）
        workspace_id: 工作区 ID（用于消息隔离）
        cancel_event: threading.Event 用于取消信号
        result_buffer: 字典用于存储执行结果（线程安全）
        error_buffer: 字典用于存储错误信息（线程安全）

    架构限制说明:
        agent.chat() 是一个阻塞调用，无法被中断。
        取消机制只能在调用前后检查，但一旦 chat() 开始执行，
        必须等待其自然完成。这是底层 Agent SDK 的限制。
        如需真正可中断的执行，需要 Agent SDK 支持异步取消接口。
    """
    try:
        # 检查是否已取消
        if cancel_event.is_set():
            error_buffer["error"] = "用户取消"
            return

        # 恢复之前的 session
        if session_id:
            agent.resume_session(session_id)

        # 获取当前工作区的消息历史
        messages = get_messages_for_workspace(workspace_id)

        context = AgentContext(
            workspace_path=Path(workspace.project_path),
            session_id=session_id,
            history=messages[:-1] if messages else [],
        )

        _logger.info(f"后台执行: agent={agent.id}, workspace={workspace.project_path}")

        # 使用 asyncio.run 在新线程中运行
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            # 注意：agent.chat() 是阻塞调用，无法被中断
            # 取消信号只能在调用前后检查
            response = loop.run_until_complete(agent.chat(prompt, context))
        finally:
            loop.close()

        # 再次检查是否已取消
        if cancel_event.is_set():
            error_buffer["error"] = "用户取消"
            return

        # 保存结果到缓冲区（线程安全）
        result_buffer["result"] = response
        error_buffer["error"] = None

        # 更新 session ID（按工作区保存）
        if agent.get_session_id():
            save_session_id_for_workspace(workspace_id, agent.get_session_id())

        _logger.info(f"后台执行完成: {len(response)} 字符")

    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        _logger.error(f"后台执行错误: {str(e)}\n{error_trace}")
        error_buffer["error"] = str(e)
        result_buffer["result"] = None
    finally:
        # 使用缓冲区通知主线程执行完成
        result_buffer["completed"] = True





def page_home():
    """首页 - 项目概览"""
    st.title("🏠 项目概览")

    wm = st.session_state.workspace_manager
    sm = st.session_state.settings_manager

    # === 1. 当前主 Agent 板块 ===
    st.markdown("### 🤖 当前主 Agent")
    primary_agent_id = sm.get_primary_agent()
    agents = get_available_agents()

    if primary_agent_id:
        # 显示设置的主 Agent
        agent_names = {
            "claude_code": "Claude Code",
            "opencode": "OpenCode",
            "openclaw": "OpenClaw",
        }
        agent_name = agent_names.get(primary_agent_id, primary_agent_id)
        is_available = any(a.id == primary_agent_id for a in agents)

        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"**{agent_name}**")
            st.caption("已锁定为主 Agent")
        with col2:
            if is_available:
                st.markdown('<span class="status-badge status-ok">🟢 可用</span>', unsafe_allow_html=True)
            else:
                st.markdown('<span class="status-badge status-error">🔴 不可用</span>', unsafe_allow_html=True)
    else:
        # 未设置主 Agent
        if agents:
            current = st.session_state.current_agent
            if current:
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"**{current.name}**")
                    st.caption(current.description)
                with col2:
                    st.markdown('<span class="status-badge status-ok">🟢 使用中</span>', unsafe_allow_html=True)
            else:
                st.info("请在「设置」页面设置主 Agent")
        else:
            st.warning("未检测到可用 Agent")
            st.caption("安装：Claude Code 或 OpenCode")

    st.markdown("---")

    # === 2. 子 Agent 状态列表 ===
    st.markdown("### 👥 子 Agent 状态")

    # 定义子 Agent 角色及其状态
    sub_agents = [
        {"name": "Developer", "role": "开发者", "status": "空闲", "progress": "待分配"},
        {"name": "Reviewer", "role": "审查者", "status": "空闲", "progress": "待分配"},
        {"name": "Tester", "role": "测试者", "status": "空闲", "progress": "待分配"},
    ]

    # 从 hypotheses 获取进度信息
    hypotheses = get_hypotheses_data()
    active_hypotheses = [h for h in hypotheses if h.get("state") == "testing"]

    if active_hypotheses:
        for h in active_hypotheses[:1]:
            statement = h.get("statement", "")
            if "Developer" in statement or "实现" in statement:
                sub_agents[0]["status"] = "忙碌"
                sub_agents[0]["progress"] = statement[:30] + "..." if len(statement) > 30 else statement
            if "Review" in statement or "审查" in statement:
                sub_agents[1]["status"] = "忙碌"
                sub_agents[1]["progress"] = statement[:30] + "..." if len(statement) > 30 else statement
            if "Test" in statement or "测试" in statement:
                sub_agents[2]["status"] = "忙碌"
                sub_agents[2]["progress"] = statement[:30] + "..." if len(statement) > 30 else statement

    # 显示子 Agent 列表
    for agent in sub_agents:
        status_icon = "🟢" if agent["status"] == "空闲" else "🟡"
        st.markdown(f"**{agent['name']}** | {status_icon} {agent['status']} | 进度：{agent['progress']}")

    st.markdown("---")

    # === 3. 项目进度报告 ===
    st.markdown("### 📈 项目进度报告")

    sprint = get_sprint_data()
    hypotheses = get_hypotheses_data()

    # 计算假设状态统计
    h_pending = len([h for h in hypotheses if h.get("state") == "pending"])
    h_testing = len([h for h in hypotheses if h.get("state") == "testing"])
    h_validated = len([h for h in hypotheses if h.get("state") == "validated"])
    h_total = len(hypotheses)

    # 进度百分比
    progress_pct = int((h_validated / h_total * 100) if h_total > 0 else 0)

    col1, col2 = st.columns([2, 1])

    with col1:
        # 当前任务
        if sprint:
            st.markdown(f"**当前任务**: {sprint.get('original_input', '无')}")
            st.caption(f"Sprint ID: {sprint.get('sprint_id', '-')}")
        else:
            st.markdown("**当前任务**: 无活动 Sprint")

        # 下一步计划
        if h_pending > 0:
            next_h = [h for h in hypotheses if h.get("state") == "pending"][0]
            st.markdown(f"**下一步计划**: {next_h.get('statement', '-')[:50]}...")
        else:
            st.markdown("**下一步计划**: 创建新假设")

    with col2:
        # 进度条
        st.metric("验证进度", f"{progress_pct}%")
        st.progress(progress_pct / 100)
        st.caption(f"已验证 {h_validated}/{h_total} 假设")

    st.markdown("---")

    # === 4. 项目统计 ===
    st.markdown("### 📊 项目统计")

    stats = get_project_stats()
    workspaces = wm.list_workspaces()

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("文件数", stats["file_count"])

    with col2:
        st.metric("代码行数", f"{stats['line_count']:,}")

    with col3:
        st.metric("Python 文件", stats["py_files"])

    with col4:
        st.metric("工作区", len(workspaces))

    st.markdown("---")

    # === 5. 最近活动 ===
    st.markdown("### 📋 最近活动")

    # 从假设和学习数据构建活动列表
    activities = []

    # 添加假设相关活动
    for h in hypotheses[:5]:
        state = h.get("state", "pending")
        statement = h.get("statement", "")[:40]
        if state == "validated":
            activities.append(f"✅ 假设验证成功: {statement}...")
        elif state == "testing":
            activities.append(f"🔬 假设测试中: {statement}...")
        elif state == "pending":
            activities.append(f"📝 假设待验证: {statement}...")

    # 添加 Sprint 活动
    if sprint:
        sprint_time = sprint.get("created_at", "")
        if sprint_time:
            activities.append(f"🚀 Sprint 创建: {sprint.get('original_input', '')[:40]}...")

    if activities:
        for i, activity in enumerate(activities[:10]):
            st.markdown(f"{i+1}. {activity}")
    else:
        st.info("暂无最近活动")

    st.markdown("---")

    # === 6. 待处理问题 ===
    st.markdown("### ⚠️ 待处理问题")

    issues = []

    # 待验证假设
    pending_hypotheses = [h for h in hypotheses if h.get("state") == "pending"]
    if pending_hypotheses:
        issues.append(f"📋 {len(pending_hypotheses)} 个待验证假设")

    # 测试中假设
    testing_hypotheses = [h for h in hypotheses if h.get("state") == "testing"]
    if testing_hypotheses:
        issues.append(f"🔬 {len(testing_hypotheses)} 个假设正在测试")

    # Agent 状态检查
    if not agents:
        issues.append("🔴 未检测到可用 Agent")

    if issues:
        for issue in issues:
            st.warning(issue)
    else:
        st.success("✅ 无待处理问题")

    st.markdown("---")

    # === 7. 当前迭代目标 ===
    st.markdown("### 🎯 当前迭代目标")

    # 从 PROJECT_MEMORY.md 读取进行中的任务
    memory_content = read_aop_file("PROJECT_MEMORY.md")
    if memory_content:
        in_progress = parse_md_section(memory_content, "进行中")
        if in_progress:
            st.markdown("**进行中**:")
            st.markdown(in_progress)
        else:
            st.info("暂无进行中的迭代目标")
    else:
        st.info("未找到项目记忆文件")

    # === 快速操作 ===
    st.markdown("---")
    st.markdown("### ⚡ 快速操作")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("💬 开始对话", use_container_width=True):
            st.info("请前往「敏捷教练」页面开始对话")

    with col2:
        if st.button("📁 管理工作区", use_container_width=True):
            st.info("请前往「工作区」页面管理")

    with col3:
        if st.button("⚙️ 系统设置", use_container_width=True):
            st.info("请前往「设置」页面配置")


def page_coach():
    """敏捷教练页面 - 快捷指令面板"""
    sm = st.session_state.settings_manager
    primary_agent = sm.get_primary_agent()

    st.title("🚀 敏捷教练")

    # === OpenClaw 状态检测 ===
    openclaw_running, openclaw_status = check_openclaw_status()
    if openclaw_running:
        st.success(f"✅ OpenClaw Gateway: {openclaw_status}")
    else:
        st.warning(f"⚠️ OpenClaw Gateway: {openclaw_status}")

    # === 项目状态概览 ===
    current_workspace = st.session_state.current_workspace
    project_path = current_workspace.project_path if current_workspace else None

    if project_path:
        # 显示项目信息
        st.markdown("### 📊 项目状态")
        col1, col2, col3 = st.columns(3)

        # 读取项目记忆
        from pathlib import Path
        aop_dir = Path(project_path) / ".aop"

        # 项目名称
        with col1:
            if current_workspace:
                st.metric("项目", current_workspace.name)
            else:
                st.metric("项目", Path(project_path).name)

        # 假设数量
        with col2:
            hypotheses_file = aop_dir / "hypotheses.json"
            if hypotheses_file.exists():
                import json
                try:
                    data = json.loads(hypotheses_file.read_text(encoding="utf-8"))
                    st.metric("假设", len(data.get("hypotheses", [])))
                except:
                    st.metric("假设", 0)
            else:
                st.metric("假设", 0)

        # 学习记录
        with col3:
            learning_file = aop_dir / "learning.json"
            if learning_file.exists():
                import json
                try:
                    data = json.loads(learning_file.read_text(encoding="utf-8"))
                    st.metric("学习", len(data.get("learnings", [])))
                except:
                    st.metric("学习", 0)
            else:
                st.metric("学习", 0)

        st.markdown("---")

    # === 启动 CLI 按钮 ===
    st.markdown("### 🖥️ 启动 CLI")

    # 检查是否选择了项目
    if not project_path:
        st.warning("请先选择一个项目工作区")
        st.info("前往「工作区」页面选择或创建工作区")
    else:
        st.caption(f"📁 当前项目: `{project_path}`")

        # 根据主 Agent 类型显示不同的启动选项
        if primary_agent == "openclaw":
            # OpenClaw 模式 - 打开 web 对话页
            col1, col2 = st.columns([3, 1])
            with col1:
                if st.button("🟢 打开 OpenClaw 对话", use_container_width=True, key="launch_openclaw"):
                    import webbrowser
                    webbrowser.open("http://127.0.0.1:18789/")
                    st.toast("已打开 OpenClaw 对话页", icon="✅")
            with col2:
                if st.button("🔄 刷新", use_container_width=True, key="refresh_status"):
                    st.rerun()
            st.caption("💡 OpenClaw 主 Agent - 直接在 Dashboard 中对话")

        elif primary_agent in ["claude_code", "opencode"]:
            # CLI 模式 - 启动命令行工具
            agent_names = {
                "claude_code": "Claude Code",
                "opencode": "OpenCode",
            }
            agent_name = agent_names.get(primary_agent, primary_agent)

            col1, col2 = st.columns([3, 1])
            with col1:
                if st.button(f"🟢 启动 {agent_name}", use_container_width=True, key="launch_primary"):
                    import subprocess
                    import tempfile
                    import os
                    from pathlib import Path

                    # 构建 AOP 敏捷教练系统提示
                    def build_aop_coach_prompt(project_path: str) -> str:
                        """构建 AOP 敏捷教练的完整系统提示"""
                        from pathlib import Path
                        import json

                        parts = []

                        # 1. 读取 AOP 自身的敏捷教练人设
                        aop_project_dir = Path(__file__).parent.parent.parent
                        aop_soul_file = aop_project_dir / ".aop" / "SOUL.md"

                        if aop_soul_file.exists():
                            parts.append(aop_soul_file.read_text(encoding="utf-8"))

                        # 2. 读取项目的专属记忆
                        project_aop_dir = Path(project_path) / ".aop"

                        # 项目人设
                        project_soul = project_aop_dir / "SOUL.md"
                        if project_soul.exists():
                            parts.append("\n\n--- 项目人设 ---\n\n" + project_soul.read_text(encoding="utf-8"))

                        # 项目记忆
                        project_memory = project_aop_dir / "PROJECT_MEMORY.md"
                        if project_memory.exists():
                            parts.append("\n\n--- 项目记忆 ---\n\n" + project_memory.read_text(encoding="utf-8"))

                        # 假设状态
                        hypotheses_file = project_aop_dir / "hypotheses.json"
                        if hypotheses_file.exists():
                            try:
                                data = json.loads(hypotheses_file.read_text(encoding="utf-8"))
                                hypotheses = data.get("hypotheses", [])
                                if hypotheses:
                                    hypo_text = "\n".join([
                                        f"- [{h.get('status', 'pending')}] {h.get('statement', '')}"
                                        for h in hypotheses[:10]
                                    ])
                                    parts.append(f"\n\n--- 当前假设 ---\n\n{hypo_text}")
                            except:
                                pass

                        # 学习记录
                        learning_file = project_aop_dir / "learning.json"
                        if learning_file.exists():
                            try:
                                data = json.loads(learning_file.read_text(encoding="utf-8"))
                                learnings = data.get("learnings", [])
                                if learnings:
                                    learn_text = "\n".join([
                                        f"- {l.get('insight', '')[:100]}"
                                        for l in learnings[-5:]
                                    ])
                                    parts.append(f"\n\n--- 最近学习 ---\n\n{learn_text}")
                            except:
                                pass

                        # 添加当前项目信息和交互要求
                        parts.append(f"""

---

# 当前项目信息

- **路径**: {project_path}
- **名称**: {Path(project_path).name}

# 首次交互要求

1. 自我介绍为「AOP 敏捷教练」
2. 汇报当前项目状态（假设数量、学习记录、进度）
3. 给出下一步建议
4. **回复语言必须和用户提问语言一致**

记住：你是协调者，帮助用户高效完成开发任务。""")

                        return "\n".join(parts)

                    # 使用新的记忆加载器构建系统提示（全局 + 项目记忆）
                    from pathlib import Path
                    import uuid
                    import shutil
                    
                    system_prompt = build_agent_system_prompt(Path(project_path))
                    
                    # 生成唯一的 session ID（用于会话隔离）
                    session_id = str(uuid.uuid4())
                    
                    # 将系统提示写入临时文件（避免命令行长度限制和引号转义问题）
                    prompt_file = os.path.join(tempfile.gettempdir(), "aop_system_prompt_" + session_id + ".txt")
                    with open(prompt_file, "w", encoding="utf-8") as f:
                        f.write(system_prompt)
                    
                    # 构建启动命令
                    cmd_name = "claude" if primary_agent == "claude_code" else "opencode"
                    
                    # 检测命令是否存在
                    if not shutil.which(cmd_name):
                        st.error(cmd_name + " 未安装或不在 PATH 中，请先安装")
                    else:
                        if sys.platform == "win32":
                            # Windows: 使用 PowerShell 读取多行系统提示
                            ps1_file = os.path.join(tempfile.gettempdir(), "aop_launch_" + session_id + ".ps1")
                            with open(ps1_file, "w", encoding="utf-8") as f:
                                f.write('$SystemPrompt = Get-Content -Path "' + prompt_file + '" -Raw\n')
                                f.write('Set-Location "' + project_path + '"\n')
                                if primary_agent == "claude_code":
                                    f.write('claude --system-prompt $SystemPrompt --session-id ' + session_id + '\n')
                                else:
                                    f.write('opencode "' + project_path + '" --prompt $SystemPrompt -s ' + session_id + '\n')
                            
                            # 使用 PowerShell 启动
                            project_name = Path(project_path).name
                            subprocess.Popen(
                                'powershell -NoExit -ExecutionPolicy Bypass -File "' + ps1_file + '"',
                                shell=True
                            )
                            
                            # 使用 start 命令打开新终端，/d 指定起始目录
                            project_name = Path(project_path).name
                            subprocess.Popen(
                                'cmd /c start "AOP 敏捷教练 - ' + project_name + '" /d "' + project_path + '" cmd /k "' + bat_file + '"',
                                shell=True
                            )
                        elif sys.platform == "darwin":
                            # macOS: 使用 Terminal
                            if primary_agent == "claude_code":
                                full_cmd = 'claude --system-prompt "$(cat \"' + prompt_file + '\")" --session-id ' + session_id
                            else:
                                full_cmd = 'opencode "' + project_path + '" --prompt "$(cat \"' + prompt_file + '\")" -s ' + session_id
                            apple_script = 'tell application "Terminal" to do script "cd \"' + project_path + '\" && ' + full_cmd + '"'
                            subprocess.Popen(["osascript", "-e", apple_script])
                        else:
                            # Linux: 尝试 gnome-terminal 或 xterm
                            if primary_agent == "claude_code":
                                full_cmd = 'claude --system-prompt "$(cat ' + prompt_file + ')" --session-id ' + session_id
                            else:
                                full_cmd = 'opencode "' + project_path + '" --prompt "$(cat ' + prompt_file + ')" -s ' + session_id
                            if shutil.which("gnome-terminal"):
                                subprocess.Popen(
                                    ["gnome-terminal", "--working-directory", project_path, "--", "bash", "-c", 
                                     full_cmd + "; exec bash"]
                                )
                            elif shutil.which("xterm"):
                                subprocess.Popen(["xterm", "-e", "bash", "-c", "cd " + project_path + "; " + full_cmd])
                            else:
                                st.warning("未检测到支持的终端，请在命令行手动运行")
                        
                        # 保存 session 信息到 session_state
                        st.session_state["last_session_id"] = session_id
                        st.session_state["last_project_path"] = project_path
                        
                    st.toast(f"已启动 {agent_name}（AOP 敏捷教练模式）", icon="✅")

            with col2:
                if st.button("🔄 刷新", use_container_width=True, key="refresh_status"):
                    st.rerun()

            st.caption(f"💡 将以 AOP 敏捷教练身份启动 {agent_name}")
        else:
            # 未设置主 Agent - 显示两个 CLI 按钮
            col1, col2, col3 = st.columns(3)

            with col1:
                if st.button("🟢 启动 Claude Code", use_container_width=True, key="launch_claude"):
                    st.info("请先在设置中选择主 Agent")
            with col2:
                if st.button("🟢 启动 OpenCode", use_container_width=True, key="launch_opencode"):
                    st.info("请先在设置中选择主 Agent")
            with col3:
                if st.button("🔄 刷新", use_container_width=True, key="refresh_status"):
                    st.rerun()

            st.caption("💡 请在设置中选择主 Agent（Claude Code / OpenCode / OpenClaw）")

    st.markdown("---")


    categories = {
        "🎯 任务执行": {
            "desc": "运行开发任务",
            "commands": [
                {"label": "实现功能", "cmd": "-aop run 实现以下功能：", "hint": "补充功能描述"},
                {"label": "修复 Bug", "cmd": "-aop run 修复以下问题：", "hint": "描述 Bug"},
                {"label": "优化代码", "cmd": "-aop run 优化以下代码：", "hint": "指定优化目标"},
                {"label": "添加测试", "cmd": "-aop run 为以下模块添加测试：", "hint": "指定模块"},
            ]
        },
        "🔍 代码审查": {
            "desc": "审查和改进代码",
            "commands": [
                {"label": "全面审查", "cmd": "-aop review 全面审查项目代码", "hint": ""},
                {"label": "安全审查", "cmd": "-aop review 检查安全性问题", "hint": ""},
                {"label": "性能审查", "cmd": "-aop review 检查性能瓶颈", "hint": ""},
                {"label": "代码风格", "cmd": "-aop review 检查代码风格和规范", "hint": ""},
            ]
        },
        "💡 假设管理": {
            "desc": "创建和验证假设",
            "commands": [
                {"label": "创建假设", "cmd": '-aop hypothesis create "', "hint": "输入假设陈述"},
                {"label": "列出假设", "cmd": "-aop hypothesis list", "hint": ""},
                {"label": "测试假设", "cmd": "-aop hypothesis test ", "hint": "输入假设 ID"},
            ]
        },
        "📊 状态查询": {
            "desc": "查看项目和 Agent 状态",
            "commands": [
                {"label": "项目状态", "cmd": "-aop status", "hint": ""},
                {"label": "Agent 状态", "cmd": "-aop status --agents", "hint": ""},
                {"label": "假设状态", "cmd": "-aop status --hypotheses", "hint": ""},
            ]
        },
        "🛠️ 开发工具": {
            "desc": "常用开发命令",
            "commands": [
                {"label": "生成文档", "cmd": "-aop run 生成项目文档", "hint": ""},
                {"label": "重构代码", "cmd": "-aop run 重构以下代码：", "hint": "指定模块"},
                {"label": "分析依赖", "cmd": "-aop run 分析项目依赖关系", "hint": ""},
                {"label": "清理代码", "cmd": "-aop run 清理无用代码和注释", "hint": ""},
            ]
        },
    }

    # 当前选中的指令（用于显示在输入框中）
    if "_selected_cmd" not in st.session_state:
        st.session_state._selected_cmd = ""

    # 渲染每个分类
    for category, data in categories.items():
        with st.expander(f"{category} - {data['desc']}", expanded=False):
            cols = st.columns(4)
            for i, cmd_info in enumerate(data["commands"]):
                col = cols[i % 4]
                with col:
                    key = f"cmd_{category}_{i}"
                    if st.button(cmd_info["label"], key=key, use_container_width=True):
                        st.session_state._selected_cmd = cmd_info["cmd"]
                        st.rerun()

    # 显示选中的指令（可手动复制）
    if st.session_state._selected_cmd:
        st.markdown("---")
        st.markdown("**📋 已选指令（可手动复制）：**")
        col1, col2 = st.columns([4, 1])
        with col1:
            st.code(st.session_state._selected_cmd, language="bash")
        with col2:
            if st.button("🗑️ 清除", use_container_width=True):
                st.session_state._selected_cmd = ""
                st.rerun()
        if st.button("✅ 已使用，清除", key="clear_after_use"):
            st.session_state._selected_cmd = ""
            st.rerun()

    # AOP 命令参考
    with st.expander("📖 AOP 命令参考", expanded=False):
        st.markdown("""
        **命令格式**：`-aop <command> [args]` 或 `aop <command> [args]`

        | 命令 | 说明 | 示例 |
        |------|------|------|
        | `run` | 运行任务 | `-aop run 实现登录功能` |
        | `review` | 代码审查 | `-aop review 检查安全性` |
        | `hypothesis` | 假设管理 | `-aop hypothesis create "缓存提升50%"` |
        | `status` | 查看状态 | `-aop status` |
        | `dashboard` | Dashboard | `-aop dashboard open` |
        | `doctor` | 环境检查 | `-aop doctor` |
        | `init` | 初始化项目 | `-aop init` |
        """)

def page_workspaces():
    """工作区管理页面"""
    st.title("📁 工作区")

    wm = st.session_state.workspace_manager
    sm = st.session_state.settings_manager
    primary_agent = sm.get_primary_agent()

    # 创建新工作区
    with st.expander("➕ 创建新工作区", expanded=False):
        name = st.text_input("工作区名称", placeholder="我的项目")
        project_path = st.text_input("项目路径", placeholder="/path/to/project")

        # Agent 选择 - 如果设置了主 Agent 则隐藏
        if primary_agent:
            st.markdown(f"**默认 Agent**: `{primary_agent}`")
            st.caption("（已由全局设置锁定）")
            selected_agent_id = primary_agent
        else:
            agents = get_available_agents()
            agent_options = {"Claude Code": "claude_code", "OpenCode": "opencode"}
            default_agent = agents[0].id if agents else "claude_code"

            primary_agent_name = st.selectbox(
                "默认 Agent",
                options=list(agent_options.keys()),
                index=0 if default_agent == "claude_code" else 1,
            )
            selected_agent_id = agent_options[primary_agent_name]

        if st.button("创建"):
            if name and project_path:
                path = Path(project_path)
                if path.exists():
                    workspace = wm.create_workspace(
                        name=name,
                        project_path=project_path,
                        primary_agent=selected_agent_id,
                    )
                    st.success(f"创建成功！ID: {workspace.id}")
                    st.rerun()
                else:
                    st.error("项目路径不存在")
            else:
                st.error("请填写名称和路径")

    # 工作区列表
    st.markdown("### 我的工作区")
    workspaces = wm.list_workspaces()

    if not workspaces:
        st.info("还没有工作区，创建一个开始使用！")
    else:
        for ws in workspaces:
            with st.container():
                col1, col2, col3, col4 = st.columns([3, 2, 1, 1])

                with col1:
                    st.markdown(f"**{ws.name}**")
                    st.caption(f"📂 {ws.project_path}")

                with col2:
                    st.markdown(f"Agent: `{ws.primary_agent}`")

                with col3:
                    if st.button("选择", key=f"select_{ws.id}"):
                        st.session_state.current_workspace = ws
                        wm.set_current_workspace(ws.id)

                        # 检查工作区的 primary_agent 设置并更新 current_agent
                        if ws.primary_agent:
                            agents = get_available_agents()
                            for agent in agents:
                                if agent.id == ws.primary_agent:
                                    st.session_state.current_agent = agent
                                    break

                        st.success(f"已切换到: {ws.name}")
                        st.rerun()

                with col4:
                    if st.button("🗑️", key=f"delete_{ws.id}", help="删除工作区"):
                        # 显示确认对话框
                        st.session_state[f"confirm_delete_{ws.id}"] = True

                # 删除确认
                if st.session_state.get(f"confirm_delete_{ws.id}", False):
                    st.warning(f"确定删除工作区「{ws.name}」？此操作仅删除软件内记录，不会影响本地文件。")
                    col_confirm, col_cancel = st.columns(2)
                    with col_confirm:
                        if st.button("确认删除", key=f"confirm_del_{ws.id}"):
                            wm.delete_workspace(ws.id)
                            # 清除当前工作区引用
                            if st.session_state.current_workspace and st.session_state.current_workspace.id == ws.id:
                                st.session_state.current_workspace = None
                            st.success(f"已删除工作区: {ws.name}")
                            st.session_state[f"confirm_delete_{ws.id}"] = False
                            st.rerun()
                    with col_cancel:
                        if st.button("取消", key=f"cancel_del_{ws.id}"):
                            st.session_state[f"confirm_delete_{ws.id}"] = False
                            st.rerun()

                st.markdown("---")


def page_settings():
    """设置页面"""
    st.title("⚙️ 设置")

    sm = st.session_state.settings_manager

    # 主 Agent 设置
    st.markdown("### 主 Agent 设置")

    agent_options = {
        "未设置（可切换）": None,
        "Claude Code": "claude_code",
        "OpenCode": "opencode",
        "OpenClaw": "openclaw",
    }

    current_primary = sm.get_primary_agent()
    current_index = 0
    for i, (name, agent_id) in enumerate(agent_options.items()):
        if agent_id == current_primary:
            current_index = i
            break

    selected = st.selectbox(
        "主 Agent",
        options=list(agent_options.keys()),
        index=current_index,
        help="设置主 Agent 后，项目界面将锁定使用该 Agent，无法切换",
    )

    selected_agent_id = agent_options[selected]

    if selected_agent_id != current_primary:
        sm.set_primary_agent(selected_agent_id)
        # 如果设置了主 Agent，自动选择该 Agent
        if selected_agent_id:
            agents = get_available_agents()
            for agent in agents:
                if agent.id == selected_agent_id:
                    st.session_state.current_agent = agent
                    break
        st.success(f"已设置主 Agent: {selected}")
        st.rerun()

    # OpenClaw 提示
    if selected_agent_id == "openclaw":
        st.info("💡 OpenClaw 已设为主 Agent，项目界面将自动使用 OpenClaw，Agent 选择器已隐藏。")

    st.markdown("---")

    # 开发者控制台设置
    st.markdown("### 开发者控制台")
    show_dev_console = sm.get_show_dev_console()
    new_show_dev = st.toggle(
        "显示开发者控制台",
        value=show_dev_console,
        help="开启后侧边栏将显示「开发者控制台」选项卡",
    )

    if new_show_dev != show_dev_console:
        sm.set_show_dev_console(new_show_dev)
        st.success(f"已{'开启' if new_show_dev else '关闭'}开发者控制台")
        st.rerun()

    st.markdown("---")

    # Agent 状态
    st.markdown("### Agent 状态")
    agents = get_available_agents()

    if not agents:
        st.warning("未检测到可用 Agent")
    else:
        for agent in agents:
            st.success(f"✅ {agent.name} - {agent.description}")

    # 安装指南
    st.markdown("### 安装指南")
    st.code("Claude Code: npm install -g @anthropic-ai/claude-code", language="bash")
    st.code("OpenCode: npm install -g opencode", language="bash")

    # 数据目录
    st.markdown("### 数据目录")
    aop_dir = Path.home() / ".aop"
    st.code(str(aop_dir))


def get_memory_files() -> List[Dict]:
    """获取记忆文件列表"""
    memories = []

    # 全局记忆文件 - SOUL.md（在用户主目录的 .aop 下）
    global_aop_dir = Path.home() / ".aop"
    soul_file = global_aop_dir / "SOUL.md"
    if soul_file.exists():
        stat = soul_file.stat()
        memories.append({
            "name": "SOUL.md",
            "path": soul_file,
            "type": "global",
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime),
        })

    # 项目记忆文件 - 当前项目的 .aop 目录
    aop_dir = get_aop_dir()
    if aop_dir.exists():
        for md_file in aop_dir.glob("*.md"):
            # 排除 SOUL.md（已作为全局记忆处理）
            if md_file.name == "SOUL.md":
                continue
            stat = md_file.stat()
            memories.append({
                "name": md_file.name,
                "path": md_file,
                "type": "project",
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime),
            })

    # 按修改时间排序
    memories.sort(key=lambda x: x["modified"], reverse=True)
    return memories


def page_memory():
    """项目记忆管理页面"""
    st.title("📚 项目记忆")

    # 检查是否选择了项目
    if not st.session_state.current_workspace:
        st.warning("请先选择一个项目工作区")
        st.info("前往「工作区」页面选择或创建工作区")
        return

    # 初始化编辑状态
    if "memory_editing" not in st.session_state:
        st.session_state.memory_editing = None
    if "memory_content" not in st.session_state:
        st.session_state.memory_content = ""
    if "memory_preview" not in st.session_state:
        st.session_state.memory_preview = False

    # 新建记忆文件
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(f"**项目**: {st.session_state.current_workspace.name}")
    with col2:
        if st.button("➕ 新建记忆", use_container_width=True):
            st.session_state.memory_creating = True

    # 新建记忆对话框
    if st.session_state.get("memory_creating", False):
        with st.container():
            st.markdown("---")
            st.markdown("**新建记忆文件**")
            new_name = st.text_input("文件名（自动添加 .md 后缀）", placeholder="my-memory")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("创建", use_container_width=True):
                    if new_name:
                        # 确保文件名以 .md 结尾
                        filename = new_name if new_name.endswith(".md") else f"{new_name}.md"
                        aop_dir = get_aop_dir()
                        aop_dir.mkdir(parents=True, exist_ok=True)
                        new_path = aop_dir / filename
                        if new_path.exists():
                            st.error("文件已存在")
                        else:
                            # 创建空文件
                            new_path.write_text(f"# {new_name}\n\n", encoding="utf-8")
                            st.success(f"已创建: {filename}")
                            st.session_state.memory_creating = False
                            st.rerun()
                    else:
                        st.error("请输入文件名")
            with col2:
                if st.button("取消", use_container_width=True):
                    st.session_state.memory_creating = False
                    st.rerun()

    st.markdown("---")

    # 如果正在编辑，显示编辑器
    if st.session_state.memory_editing:
        memory = st.session_state.memory_editing
        st.markdown(f"### 编辑: {memory['name']}")
        if memory["type"] == "global":
            st.caption("🌍 全局记忆 - 所有项目共享")
        else:
            st.caption("📁 项目记忆 - 仅当前项目可见")

        # 预览模式切换
        preview_mode = st.toggle("预览模式", value=st.session_state.memory_preview)
        st.session_state.memory_preview = preview_mode

        if preview_mode:
            # 预览模式
            st.markdown(st.session_state.memory_content)
        else:
            # 编辑模式
            new_content = st.text_area(
                "内容",
                value=st.session_state.memory_content,
                height=400,
                label_visibility="collapsed",
            )
            st.session_state.memory_content = new_content

        # 操作按钮
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("💾 保存", use_container_width=True):
                try:
                    memory["path"].write_text(st.session_state.memory_content, encoding="utf-8")
                    st.success("保存成功！")
                    st.session_state.memory_editing = None
                    st.rerun()
                except Exception as e:
                    st.error(f"保存失败: {e}")

        with col2:
            if st.button("❌ 取消", use_container_width=True):
                st.session_state.memory_editing = None
                st.session_state.memory_content = ""
                st.rerun()

        with col3:
            if memory["type"] != "global":  # 全局记忆不允许删除
                if st.button("🗑️ 删除", use_container_width=True):
                    st.session_state.memory_delete_confirm = memory

        # 删除确认
        if st.session_state.get("memory_delete_confirm"):
            st.warning(f"确定删除记忆文件「{memory['name']}」？此操作不可恢复。")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("确认删除", use_container_width=True):
                    try:
                        memory["path"].unlink()
                        st.success(f"已删除: {memory['name']}")
                        st.session_state.memory_editing = None
                        st.session_state.memory_delete_confirm = None
                        st.rerun()
                    except Exception as e:
                        st.error(f"删除失败: {e}")
            with col2:
                if st.button("取消", use_container_width=True):
                    st.session_state.memory_delete_confirm = None
                    st.rerun()

        st.markdown("---")
        st.markdown("### 所有记忆文件")

    # 显示记忆文件列表
    memories = get_memory_files()

    if not memories:
        st.info("暂无记忆文件。点击「新建记忆」创建第一个记忆。")
    else:
        # 统计信息
        global_count = len([m for m in memories if m["type"] == "global"])
        project_count = len([m for m in memories if m["type"] == "project"])
        st.caption(f"共 {len(memories)} 个记忆文件（{global_count} 全局 / {project_count} 项目）")

        st.markdown("---")

        for memory in memories:
            with st.container():
                col1, col2, col3, col4 = st.columns([3, 2, 1, 1])

                with col1:
                    # 名称和类型标签
                    if memory["type"] == "global":
                        st.markdown(f"🌍 **{memory['name']}**")
                        st.caption("全局记忆 - 所有项目共享")
                    else:
                        st.markdown(f"📁 **{memory['name']}**")
                        st.caption("项目记忆")

                with col2:
                    # 修改时间
                    st.caption(f"修改: {memory['modified'].strftime('%Y-%m-%d %H:%M')}")

                with col3:
                    # 文件大小
                    size_kb = memory["size"] / 1024
                    st.caption(f"{size_kb:.1f} KB")

                with col4:
                    if st.button("编辑", key=f"edit_{memory['name']}", use_container_width=True):
                        # 读取文件内容
                        content = memory["path"].read_text(encoding="utf-8")
                        st.session_state.memory_editing = memory
                        st.session_state.memory_content = content
                        st.session_state.memory_preview = False
                        st.rerun()

                st.markdown("---")


def page_dev_console():
    """开发者控制台页面"""
    st.title("🖥️ 开发者控制台")

    logger = get_dashboard_logger()

    # 工具栏
    col1, col2, col3, col4 = st.columns([2, 2, 1, 1])

    with col1:
        level_filter = st.selectbox(
            "日志级别",
            ["ALL", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            label_visibility="collapsed",
        )

    with col2:
        search = st.text_input("搜索", placeholder="输入关键词...", label_visibility="collapsed")

    with col3:
        # 一键复制按钮
        if st.button("📋 复制", use_container_width=True, key="copy_logs_btn"):
            entries_all = logger.get_entries(level=None if level_filter == "ALL" else level_filter, search=search or None)
            log_text = "\n".join([
                f"[{e.timestamp.strftime('%H:%M:%S')}] {e.level}: {e.message}"
                + (f"\n{e.exception}" if e.exception else "")
                for e in entries_all
            ])
            # 使用 JavaScript 复制到剪贴板
            import streamlit.components.v1 as components
            components.html(f"""
                <script>
                    navigator.clipboard.writeText(`{log_text.replace('`', '\\`').replace('</script>', '</script>')}`);
                    parent.document.querySelector('[data-testid="stToast"]').innerHTML = '<div style="padding:10px">✅ 已复制 {len(entries_all)} 条日志</div>';
                </script>
            """, height=0)
            st.toast(f"已复制 {len(entries_all)} 条日志", icon="✅")

    with col4:
        if st.button("🗑️ 清空", use_container_width=True):
            logger.clear()
            st.rerun()

    st.markdown("---")

    # 日志统计
    entries = logger.get_entries(level=None if level_filter == "ALL" else level_filter, search=search or None)
    total = logger.get_count()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("总日志数", total)
    with col2:
        error_count = len([e for e in entries if e.level == "ERROR"])
        st.metric("错误", error_count, delta_color="inverse")
    with col3:
        warn_count = len([e for e in entries if e.level == "WARNING"])
        st.metric("警告", warn_count, delta_color="inverse")
    with col4:
        st.metric("显示", len(entries))

    st.markdown("---")

    # 导出按钮（一键复制）
    if entries:
        log_text = "\n".join([
            f"[{e.timestamp.strftime('%H:%M:%S')}] {e.level}: {e.message}"
            + (f"\n{e.exception}" if e.exception else "")
            for e in entries
        ])
        st.download_button(
            "📋 复制全部日志",
            log_text,
            file_name=f"aop_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            mime="text/plain",
            use_container_width=True,
            key="download_logs_btn",
        )
        st.markdown("---")

    # 日志列表
    if not entries:
        st.info("暂无日志记录")
        return

    # 选项：切换显示模式
    view_mode = st.radio("显示模式", ["详细视图", "文本视图（可复制）"], horizontal=True, label_visibility="collapsed")

    if view_mode == "文本视图（可复制）":
        # 文本视图：用 st.code 显示（自带复制按钮）
        log_text = ""
        for e in entries:
            log_text += f"[{e.timestamp.strftime('%H:%M:%S')}] {e.level}: {e.message}"
            if e.exception:
                log_text += f"\n{e.exception}"
            log_text += "\n"
        st.code(log_text, language="log")
    else:
        # 详细视图：保持原有格式
        for entry in entries:
            # 级别颜色
            level_colors = {
                "DEBUG": "gray",
                "INFO": "blue",
                "WARNING": "orange",
                "ERROR": "red",
                "CRITICAL": "darkred",
            }
            color = level_colors.get(entry.level, "gray")

            with st.container():
                col1, col2 = st.columns([1, 4])
                with col1:
                    st.markdown(
                        f"<span style='color:{color}; font-weight:bold;'>{entry.level}</span>",
                        unsafe_allow_html=True,
                    )
                    st.caption(entry.timestamp.strftime("%H:%M:%S"))
                with col2:
                    st.markdown(f"**{entry.message}**")
                    if entry.exception:
                        with st.expander("查看堆栈", expanded=False):
                            st.code(entry.exception, language="python")

                st.markdown("---")


# ============ 主程序 ============


def cleanup_temp_files():
    """清理过期的临时文件"""
    import glob
    import time
    temp_dir = tempfile.gettempdir()
    patterns = ["aop_system_prompt_*.txt", "aop_launch_*.ps1", "aop_launch_*.bat"]
    current_time = time.time()
    cleaned = 0
    for pattern in patterns:
        for filepath in glob.glob(os.path.join(temp_dir, pattern)):
            try:
                # 删除超过 1 小时的临时文件
                if current_time - os.path.getmtime(filepath) > 3600:
                    os.remove(filepath)
                    cleaned += 1
            except Exception:
                pass
    return cleaned

# 在应用启动时清理
try:
    cleanup_temp_files()
except Exception:
    pass

def main():
    init_session_state()
    page = render_sidebar()

    if page == "🏠 首页":
        page_home()
    elif page == "💬 敏捷教练":
        page_coach()
    elif page == "📚 项目记忆":
        page_memory()
    elif page == "📁 工作区":
        page_workspaces()
    elif page == "⚙️ 设置":
        page_settings()
    elif page == "🖥️ 开发者控制台":
        page_dev_console()


if __name__ == "__main__":
    main()
