"""
AOP Dashboard - 对话式界面

Run with: streamlit run app.py
Or: aop dashboard
"""

import asyncio
import time
import threading
import streamlit as st
import json
import subprocess
from pathlib import Path
from typing import Optional, Dict, List, Any
from datetime import datetime

from aop.primary import get_registry, AgentContext, PrimaryAgent
from aop.primary.workspace import WorkspaceManager, Workspace, SettingsManager
from aop.primary.listener import start_listener, submit_command
from aop.dashboard.logger import get_dashboard_logger, setup_dashboard_logging
from aop.dashboard.streaming import TokenQueue, parse_thinking_tags

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
        # 检查是否切换了工作区
        current_ws = st.session_state.current_workspace
        is_switching = not current_ws or current_ws.id != selected_ws.id

        st.session_state.current_workspace = selected_ws
        wm.set_current_workspace(selected_ws.id)

        # 如果切换了工作区，检查并更新 Agent
        if is_switching and selected_ws.primary_agent:
            agents = get_available_agents()
            for agent in agents:
                if agent.id == selected_ws.primary_agent:
                    st.session_state.current_agent = agent
                    break

    return selected_ws


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


def execute_agent_task_streaming(
    agent, workspace, prompt, session_id, workspace_id, 
    token_queue: TokenQueue, result_buffer, error_buffer
):
    """流式执行 Agent 任务，实时输出 token
    
    Args:
        token_queue: TokenQueue 用于跨线程传递流式输出
    """
    try:
        if session_id:
            agent.resume_session(session_id)

        context = AgentContext(
            workspace_path=Path(workspace.project_path),
            session_id=session_id,
        )

        _logger.info(f"流式执行: agent={agent.id}, workspace={workspace.project_path}")

        # 使用同步流式方法（兼容 Windows）
        full_response = []
        
        # 定义回调
        def on_token(token):
            token_queue.put(token)
        
        # 调用 agent 的同步流式方法
        for token in agent.chat_stream_sync(prompt, context, on_token=on_token):
            full_response.append(token)
        
        response = ''.join(full_response)
        result_buffer["result"] = response
        token_queue.done()
        
        if agent.get_session_id():
            save_session_id_for_workspace(workspace_id, agent.get_session_id())
        
        _logger.info(f"流式执行完成: {len(response)} 字符")

    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        _logger.error(f"流式执行错误: {str(e)}\n{error_trace}")
        token_queue.set_error(str(e))
        error_buffer["error"] = str(e)
    finally:
        result_buffer["completed"] = True


def render_chat():
    """渲染聊天界面"""
    workspace_id = get_current_workspace_id()

    # === 检查后台执行状态 ===
    if st.session_state.execution_running:
        token_queue = st.session_state.token_queue
        elapsed = time.time() - st.session_state.execution_start_time if st.session_state.execution_start_time else 0

        # 获取当前工作区的消息
        messages = get_messages_for_workspace(workspace_id)

        # 显示已有的历史消息
        for msg in messages:
            with st.chat_message(msg["role"]):
                render_message_content(msg["content"])

        # === 使用 st.status 显示流式输出 ===
        with st.status("🤔 思考中...", expanded=True) as status:
            content_placeholder = st.empty()
            thinking_info = st.empty()  # 只显示思考摘要，不刷新完整内容
            
            streaming_content = st.session_state.get("streaming_content", "")
            
            if token_queue and not token_queue.is_done():
                # 持续读取 token，减少 rerun
                read_count = 0
                max_reads_per_cycle = 100  # 每次最多读取 100 个 token
                
                while read_count < max_reads_per_cycle:
                    token = token_queue.get(timeout=0.02)
                    
                    if token:
                        streaming_content += token
                        st.session_state.streaming_content = streaming_content
                        read_count += 1
                        
                        # 解析思考标签
                        parts = parse_thinking_tags(streaming_content)
                        
                        # 更新普通内容
                        if parts['normal']:
                            content_placeholder.markdown(parts['normal'])
                        
                        # 只在思考长度变化时更新摘要（减少刷新）
                        thinking_len = len(parts['thinking']) if parts['thinking'] else 0
                        if thinking_len > 0:
                            thinking_info.caption(f"💭 思考中... ({thinking_len} 字符)")
                    else:
                        # 没有 token，检查是否完成
                        if token_queue.is_done():
                            break
                        time.sleep(0.02)
                    
                    # 更新状态
                    elapsed = time.time() - st.session_state.execution_start_time
                    status.update(label=f"🤔 思考中... ({elapsed:.1f}s)")
                
                # 检查是否真正完成
                if token_queue.is_done():
                    status.update(label="✅ 完成", state="complete")
                    
                    # 保存最终消息
                    final_content = streaming_content
                    error = token_queue.get_error()
                    
                    if error:
                        messages.append({"role": "assistant", "content": f"❌ 错误: {error}"})
                    elif final_content:
                        messages.append({"role": "assistant", "content": final_content})
                    
                    save_messages_for_workspace(workspace_id, messages)
                    
                    # 清理状态
                    st.session_state.streaming_content = ""
                    st.session_state.token_queue = None
                    st.session_state.execution_running = False
                    st.session_state.execution_thread = None
                    st.session_state.execution_start_time = None
                    
                    time.sleep(0.3)
                    st.rerun()
                else:
                    # 继续下一轮读取
                    time.sleep(0.05)
                    st.rerun()
            
            else:
                # 没有 token_queue，等待初始化
                status.update(label=f"🤔 初始化中... ({elapsed:.1f}s)")
                time.sleep(0.2)
                st.rerun()
        
        return

    # 获取当前工作区的消息
    messages = get_messages_for_workspace(workspace_id)

    # === 检查是否有待处理的 prompt ===
    if st.session_state.get('pending_prompt'):
        prompt = st.session_state.pending_prompt
        del st.session_state.pending_prompt

        # 检查是否就绪
        if st.session_state.current_workspace and st.session_state.current_agent:
            # 添加用户消息到工作区消息
            messages.append({"role": "user", "content": prompt})
            save_messages_for_workspace(workspace_id, messages)
            _logger.info(f"快捷指令: {prompt[:100]}...")

            # 启动后台执行
            agent = st.session_state.current_agent
            workspace = st.session_state.current_workspace
            session_id = get_session_id_for_workspace(workspace_id)

            # 创建结果缓冲区和取消事件
            st.session_state.execution_running = True
            st.session_state.execution_start_time = time.time()
            st.session_state.execution_result_buffer = {}
            st.session_state.execution_error_buffer = {}
            st.session_state.cancel_event.clear()

            thread = threading.Thread(
                target=execute_agent_task,
                args=(agent, workspace, prompt, session_id, workspace_id,
                      st.session_state.cancel_event,
                      st.session_state.execution_result_buffer,
                      st.session_state.execution_error_buffer),
                daemon=False,
            )
            st.session_state.execution_thread = thread
            thread.start()

            st.rerun()

    # === 显示历史消息 ===
    for msg in messages:
        with st.chat_message(msg["role"]):
            render_message_content(msg["content"])

    # === 聊天输入 ===
    if prompt := st.chat_input("输入你的问题..."):
        # 检查是否就绪
        if not st.session_state.current_workspace:
            st.error("请先选择一个项目工作区")
            return

        if not st.session_state.current_agent:
            st.error("请先选择一个 Agent")
            return

        # 添加用户消息到工作区消息
        messages.append({"role": "user", "content": prompt})
        save_messages_for_workspace(workspace_id, messages)
        _logger.info(f"用户输入: {prompt[:100]}...")

        # 启动流式执行
        agent = st.session_state.current_agent
        workspace = st.session_state.current_workspace
        session_id = get_session_id_for_workspace(workspace_id)

        # 创建 token 队列和结果缓冲区
        token_queue = TokenQueue()
        st.session_state.token_queue = token_queue
        st.session_state.streaming_content = ""
        st.session_state.execution_running = True
        st.session_state.execution_start_time = time.time()
        st.session_state.execution_result_buffer = {}
        st.session_state.execution_error_buffer = {}
        st.session_state.cancel_event.clear()

        thread = threading.Thread(
            target=execute_agent_task_streaming,
            args=(agent, workspace, prompt, session_id, workspace_id,
                  token_queue,
                  st.session_state.execution_result_buffer,
                  st.session_state.execution_error_buffer),
            daemon=False,
        )
        st.session_state.execution_thread = thread
        thread.start()

        st.rerun()


def render_message_content(content: str):
    """渲染消息内容，支持思考部分的折叠显示

    Args:
        content: 消息内容，可能包含 <thinking>...</thinking> 标签
    """
    import re

    # 匹配 <thinking>...</thinking> 标签
    thinking_pattern = r'<thinking>(.*?)</thinking>'
    parts = re.split(thinking_pattern, content, flags=re.DOTALL)

    if len(parts) > 1:
        # 有思考内容，交替渲染
        for i, part in enumerate(parts):
            if i % 2 == 0:
                # 普通内容
                if part.strip():
                    st.markdown(part)
            else:
                # 思考内容 - 使用折叠卡片
                with st.expander("🤔 思考过程", expanded=False):
                    st.markdown(part)
    else:
        # 没有思考内容，直接渲染
        st.markdown(content)


def render_quick_actions(is_openclaw: bool = False):
    """渲染快捷指令按钮

    Args:
        is_openclaw: 是否为 OpenClaw 模式，True 时按钮改为「复制指令」
    """
    st.markdown("---")
    st.markdown("**快捷指令**" if not is_openclaw else "**快捷指令（点击复制到剪贴板）**")

    col1, col2, col3, col4 = st.columns(4)

    # 根据模式使用不同的提示语
    if is_openclaw:
        quick_prompts = {
            "📋 run 任务": "-aop run ",
            "📋 review 审查": "-aop review ",
            "📋 hypothesis 假设": "-aop hypothesis create ",
            "📋 status 状态": "-aop status",
        }
    else:
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
                        # 正常模式：设置待处理 prompt 并触发 rerun
                        st.session_state.pending_prompt = prompt
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
        # OpenClaw 模式：显示命令帮助和提示
        st.success("🟢 OpenClaw 已连接 - 可直接在对话窗口使用 AOP 命令")

        with st.expander("📖 AOP 命令参考", expanded=True):
            st.markdown("""
            **命令格式**：`-aop <command> [args]` 或 `aop <command> [args]`

            | 命令 | 说明 | 示例 |
            |------|------|------|
            | `run` | 运行任务 | `-aop run 实现登录功能` |
            | `review` | 代码审查 | `-aop review 检查安全性` |
            | `hypothesis` | 假设管理 | `-aop hypothesis create "缓存提升50%"` |
            | `status` | 查看状态 | `-aop status` |
            | `dashboard` | Dashboard | `-aop dashboard open` |
            """)

        st.markdown("---")
        st.markdown("💡 **提示**：快捷指令已改为「复制指令」模式，点击按钮可复制指令到剪贴板。")
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
