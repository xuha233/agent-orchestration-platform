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
from aop.primary.workspace import WorkspaceManager, Workspace
from aop.primary.listener import start_listener, submit_command

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

def init_session_state():
    """初始化 session state"""
    if "workspace_manager" not in st.session_state:
        st.session_state.workspace_manager = WorkspaceManager()
    if "current_workspace" not in st.session_state:
        st.session_state.current_workspace = None
    if "current_agent" not in st.session_state:
        st.session_state.current_agent = None
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "session_id" not in st.session_state:
        st.session_state.session_id = None
    if "listener_started" not in st.session_state:
        # 启动命令监听器
        start_listener()
        st.session_state.listener_started = True


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

        page = st.radio(
            "导航",
            ["🏠 首页", "📜 历史", "📁 工作区", "⚙️ 设置"],
            label_visibility="collapsed",
        )

        st.markdown("---")

        # 当前工作区状态
        if st.session_state.current_workspace:
            ws = st.session_state.current_workspace
            st.markdown(f"**当前项目**")
            st.markdown(f"📁 {ws.name}")
            st.caption(f"📂 {ws.project_path}")

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

                response = run_async(agent.chat(prompt, context))

                # 更新 session ID
                if agent.get_session_id():
                    st.session_state.session_id = agent.get_session_id()

                placeholder.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})

            except Exception as e:
                placeholder.error(f"错误: {str(e)}")


def render_quick_actions():
    """渲染快捷指令按钮"""
    st.markdown("---")
    st.markdown("**快捷指令**")

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
            if st.button(label, key=f"quick_{i}", use_container_width=True):
                if st.session_state.current_workspace and st.session_state.current_agent:
                    st.session_state.messages.append({"role": "user", "content": prompt})
                    st.rerun()
                else:
                    st.warning("请先选择项目和工作区")


# ============ 主页面 ============

def page_home():
    """首页"""
    # 顶部：项目选择器 + Agent 切换
    col1, col2 = st.columns(2)

    with col1:
        render_project_selector()

    with col2:
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
    else:
        # 就绪状态：显示聊天
        render_chat()

    # 快捷指令
    render_quick_actions()


def page_history():
    """历史记录页面"""
    st.title("📜 历史记录")

    if not st.session_state.messages:
        st.info("还没有对话记录。在首页开始对话！")
        return

    if st.button("🗑️ 清除对话历史", type="secondary"):
        st.session_state.messages = []
        st.session_state.session_id = None
        if st.session_state.current_agent:
            st.session_state.current_agent.clear_session()
        st.rerun()

    st.markdown("---")

    for msg in st.session_state.messages:
        role_emoji = "👤" if msg["role"] == "user" else "🤖"
        with st.expander(f"{role_emoji} {msg['role']}", expanded=False):
            st.markdown(msg["content"])


def page_workspaces():
    """工作区管理页面"""
    st.title("📁 工作区")

    wm = st.session_state.workspace_manager

    # 创建新工作区
    with st.expander("➕ 创建新工作区", expanded=False):
        name = st.text_input("工作区名称", placeholder="我的项目")
        project_path = st.text_input("项目路径", placeholder="/path/to/project")

        # Agent 选择
        agents = get_available_agents()
        agent_options = {"Claude Code": "claude_code", "OpenCode": "opencode"}
        default_agent = agents[0].id if agents else "claude_code"

        primary_agent = st.selectbox(
            "默认 Agent",
            options=list(agent_options.keys()),
            index=0 if default_agent == "claude_code" else 1,
        )

        if st.button("创建"):
            if name and project_path:
                path = Path(project_path)
                if path.exists():
                    workspace = wm.create_workspace(
                        name=name,
                        project_path=project_path,
                        primary_agent=agent_options[primary_agent],
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
                col1, col2, col3 = st.columns([3, 2, 1])

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

                st.markdown("---")


def page_settings():
    """设置页面"""
    st.title("⚙️ 设置")

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


# ============ 主程序 ============

def main():
    init_session_state()
    page = render_sidebar()

    if page == "🏠 首页":
        page_home()
    elif page == "📜 历史":
        page_history()
    elif page == "📁 工作区":
        page_workspaces()
    elif page == "⚙️ 设置":
        page_settings()


if __name__ == "__main__":
    main()
