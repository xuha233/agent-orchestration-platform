"""
AOP Dashboard - 对话式界面

Run with: streamlit run app.py
Or: aop dashboard
"""

import asyncio
import streamlit as st
from pathlib import Path
from typing import Optional

from aop.primary import get_registry, AgentContext, PrimaryAgent
from aop.primary.workspace import WorkspaceManager, Workspace, SettingsManager
from aop.primary.listener import start_listener, submit_command
from aop.dashboard.logger import get_dashboard_logger, setup_dashboard_logging

import logging
_logger = logging.getLogger(__name__)

# Page config
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
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "session_id" not in st.session_state:
        st.session_state.session_id = None


def get_available_agents() -> list:
    """获取可用的 Agent 列表"""
    registry = get_registry()
    return registry.list_available()


def get_agent_by_id(agent_id: str) -> Optional[PrimaryAgent]:
    """根据 ID 获取 Agent"""
    registry = get_registry()
    return registry.get(agent_id)


# ============ 异步执行封装 ============

def run_async(coro):
    """在 Streamlit 中运行异步函数"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


# ============ 页面组件 ============

def render_sidebar():
    """渲染侧边栏"""
    with st.sidebar:
        st.title("🤖 AOP")

        # 获取设置，决定是否显示开发者控制台
        sm = st.session_state.settings_manager
        show_dev_console = sm.get_show_dev_console()

        pages = ["🏠 首页", "💬 敏捷教练", "📁 工作区", "⚙️ 设置"]
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


def render_empty_state():
    """渲染空状态提示"""
    col1, col2 = st.columns(2)

    with col1:
        if st.button("📁 选择项目", use_container_width=True):
            st.info("请从左侧菜单进入「工作区」页面")

    with col2:
        agents = get_available_agents()
        if not agents:
            st.button("⚙️ 配置 Agent", use_container_width=True)
            st.caption("未检测到可用 Agent，请先安装 Claude Code 或 OpenCode")


def render_agent_selector():
    """渲染 Agent 选择器"""
    agents = get_available_agents()

    if not agents:
        st.warning("⚠️ 未检测到可用 Agent")
        st.markdown("""
**安装指南：**
- Claude Code: `npm install -g @anthropic-ai/claude-code`
- OpenCode: `npm install -g opencode`
""")
        return None

    agent_options = {agent.name: agent for agent in agents}

    # 默认选择第一个可用 Agent
    default_agent = agents[0]
    if st.session_state.current_agent:
        default_agent = st.session_state.current_agent

    selected_name = st.selectbox(
        "选择 Agent",
        options=list(agent_options.keys()),
        index=list(agent_options.keys()).index(default_agent.name) if default_agent.name in agent_options else 0,
    )

    return agent_options.get(selected_name)


def render_project_selector():
    """渲染项目选择器"""
    wm = st.session_state.workspace_manager
    workspaces = wm.list_workspaces()

    if not workspaces:
        if st.button("➕ 创建工作区"):
            st.info("请在「工作区」页面创建新工作区")
        return None

    workspace_options = {ws.name: ws for ws in workspaces}

    # 默认选择当前工作区或第一个
    default_ws = st.session_state.current_workspace or workspaces[0]
    default_name = default_ws.name if default_ws else list(workspace_options.keys())[0]

    selected_name = st.selectbox(
        "选择项目",
        options=list(workspace_options.keys()),
        index=list(workspace_options.keys()).index(default_name) if default_name in workspace_options else 0,
    )

    selected_ws = workspace_options.get(selected_name)
    if selected_ws:
        st.session_state.current_workspace = selected_ws
        wm.set_current_workspace(selected_ws.id)

    return selected_ws


def render_chat():
    """渲染聊天界面"""
    # 显示历史消息
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # 聊天输入
    if prompt := st.chat_input("输入你的问题..."):
        # 检查是否就绪
        if not st.session_state.current_workspace:
            st.error("请先选择一个项目工作区")
            return

        if not st.session_state.current_agent:
            st.error("请先选择一个 Agent")
            return

        # 添加用户消息
        st.session_state.messages.append({"role": "user", "content": prompt})
        _logger.info(f"用户输入: {prompt[:100]}...")

        with st.chat_message("user"):
            st.markdown(prompt)

        # 获取 AI 响应
        with st.chat_message("assistant"):
            placeholder = st.empty()
            placeholder.markdown("🤔 思考中...")

            try:
                agent = st.session_state.current_agent
                workspace = st.session_state.current_workspace

                context = AgentContext(
                    workspace_path=Path(workspace.project_path),
                    session_id=st.session_state.session_id,
                    history=st.session_state.messages[:-1],  # 不包含刚添加的消息
                )

                _logger.info(f"执行命令: agent={agent.id}, workspace={workspace.project_path}")

                response = run_async(agent.chat(prompt, context))

                # 更新 session ID
                if agent.get_session_id():
                    st.session_state.session_id = agent.get_session_id()

                placeholder.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
                _logger.info(f"响应成功: {len(response)} 字符")

            except Exception as e:
                import traceback
                error_trace = traceback.format_exc()
                _logger.error(f"执行错误: {str(e)}\n{error_trace}")
                placeholder.error(f"错误: {str(e)}")


def render_quick_actions(is_openclaw: bool = False):
    """渲染快捷指令按钮

    Args:
        is_openclaw: 是否为 OpenClaw 模式，True 时按钮改为「复制指令」
    """
    st.markdown("---")
    st.markdown("**快捷指令**" if not is_openclaw else "**快捷指令（点击复制）**")

    col1, col2, col3, col4 = st.columns(4)

    quick_prompts = {
        "🔍 代码审查": "请帮我审查当前项目的代码，找出潜在问题和改进建议。",
        "💡 创建假设": "请帮我创建一个关于项目优化的假设。",
        "📊 查看状态": "请总结当前项目的状态和结构。",
        "🔧 重构建议": "请分析代码并提供重构建议。",
    }

    for i, (label, prompt) in enumerate(quick_prompts.items()):
        col = [col1, col2, col3, col4][i]
        with col:
            # OpenClaw 模式下修改按钮标签
            button_label = label.replace("🔍", "📋").replace("💡", "📋").replace("📊", "📋").replace("🔧", "📋") if is_openclaw else label

            if st.button(button_label, key=f"quick_{i}", use_container_width=True):
                if st.session_state.current_workspace and st.session_state.current_agent:
                    if is_openclaw:
                        # OpenClaw 模式：复制到剪贴板
                        st.session_state.copied_prompt = prompt
                        st.toast("已复制到剪贴板", icon="✅")
                    else:
                        # 正常模式：发送消息
                        st.session_state.messages.append({"role": "user", "content": prompt})
                        st.rerun()
                else:
                    st.warning("请先选择项目和工作区")

    # OpenClaw 模式下显示复制的内容
    if is_openclaw and st.session_state.get("copied_prompt"):
        st.caption(f"已复制: {st.session_state.copied_prompt[:50]}...")
        # 使用 JavaScript 复制到剪贴板
        st.markdown(f"""
        <script>
            navigator.clipboard.writeText(`{st.session_state.copied_prompt}`);
        </script>
        """, unsafe_allow_html=True)


# ============ 主页面 ============

def page_home():
    """首页 - 项目概览"""
    st.title("🏠 项目概览")

    wm = st.session_state.workspace_manager
    sm = st.session_state.settings_manager

    # === Agent 团队状态 ===
    st.markdown("### 🤖 Agent 团队状态")
    agents = get_available_agents()

    if not agents:
        st.warning("未检测到可用 Agent")
        st.markdown("""
        **安装指南：**
        - Claude Code: `npm install -g @anthropic-ai/claude-code`
        - OpenCode: `npm install -g opencode`
        """)
    else:
        cols = st.columns(min(len(agents), 3))
        for i, agent in enumerate(agents):
            with cols[i % 3]:
                is_current = st.session_state.current_agent and st.session_state.current_agent.id == agent.id
                status_color = "🟢" if is_current else "⚪"

                st.markdown(f"""
                <div class="quick-card">
                    <h4>{status_color} {agent.name}</h4>
                    <p>{agent.description}</p>
                </div>
                """, unsafe_allow_html=True)

                if is_current:
                    st.caption("当前使用中")

    st.markdown("---")

    # === 项目统计 ===
    st.markdown("### 📊 项目统计")
    workspaces = wm.list_workspaces()

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("工作区总数", len(workspaces))

    with col2:
        # 当前工作区
        current_ws = st.session_state.current_workspace
        st.metric("当前工作区", current_ws.name if current_ws else "未选择")

    with col3:
        # 会话消息数
        msg_count = len(st.session_state.messages)
        st.metric("对话消息数", msg_count)

    with col4:
        # 主 Agent
        primary = sm.get_primary_agent()
        st.metric("主 Agent", primary or "未设置")

    st.markdown("---")

    # === 工作区列表 ===
    st.markdown("### 📁 工作区列表")

    if not workspaces:
        st.info("还没有工作区，请在「工作区」页面创建")
    else:
        for ws in workspaces:
            is_current = current_ws and current_ws.id == ws.id

            with st.container():
                col1, col2, col3 = st.columns([3, 2, 1])

                with col1:
                    name_display = f"**{ws.name}** {'(当前)' if is_current else ''}"
                    st.markdown(name_display)
                    st.caption(f"📂 {ws.project_path}")

                with col2:
                    st.markdown(f"Agent: `{ws.primary_agent}`")

                with col3:
                    if not is_current:
                        if st.button("切换", key=f"home_select_{ws.id}"):
                            st.session_state.current_workspace = ws
                            wm.set_current_workspace(ws.id)
                            st.rerun()
                    else:
                        st.markdown("✅")

                st.markdown("---")

    # === 快速操作 ===
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
    """敏捷教练页面 - 对话入口"""
    sm = st.session_state.settings_manager
    primary_agent = sm.get_primary_agent()
    is_openclaw = primary_agent == "openclaw"

    # 如果设置了主 Agent，自动选择
    if primary_agent and not st.session_state.current_agent:
        agents = get_available_agents()
        for agent in agents:
            if agent.id == primary_agent:
                st.session_state.current_agent = agent
                break

    st.title("💬 敏捷教练")

    # 顶部：项目选择器 + Agent 切换
    col1, col2 = st.columns(2)

    with col1:
        render_project_selector()

    with col2:
        # 如果设置了主 Agent，隐藏选择器
        if primary_agent:
            if st.session_state.current_agent:
                st.markdown(f"**Agent**: {st.session_state.current_agent.name}")
                st.caption("（已由全局设置锁定）")
        else:
            agent = render_agent_selector()
            if agent:
                st.session_state.current_agent = agent

    st.markdown("---")

    # 检查是否就绪
    workspace_ready = st.session_state.current_workspace is not None
    agent_ready = st.session_state.current_agent is not None

    if not workspace_ready or not agent_ready:
        # 未就绪状态
        if not any([workspace_ready, agent_ready]):
            render_welcome()
        render_empty_state()
    elif is_openclaw:
        # OpenClaw 模式：显示提示，不显示聊天框
        st.info("💡 请在 OpenClaw 对话窗口继续操作")
        st.markdown("快捷指令已改为「复制指令」模式，点击按钮可将指令复制到剪贴板。")
    else:
        # 就绪状态：显示聊天
        render_chat()

    # 快捷指令
    render_quick_actions(is_openclaw=is_openclaw)


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


def page_dev_console():
    """开发者控制台页面"""
    st.title("🖥️ 开发者控制台")

    logger = get_dashboard_logger()

    # 工具栏
    col1, col2, col3 = st.columns([2, 2, 1])

    with col1:
        level_filter = st.selectbox(
            "日志级别",
            ["ALL", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            label_visibility="collapsed",
        )

    with col2:
        search = st.text_input("搜索", placeholder="输入关键词...", label_visibility="collapsed")

    with col3:
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

    # 日志列表
    if not entries:
        st.info("暂无日志记录")
        return

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

def main():
    init_session_state()
    page = render_sidebar()

    if page == "🏠 首页":
        page_home()
    elif page == "💬 敏捷教练":
        page_coach()
    elif page == "📁 工作区":
        page_workspaces()
    elif page == "⚙️ 设置":
        page_settings()
    elif page == "🖥️ 开发者控制台":
        page_dev_console()


if __name__ == "__main__":
    main()
