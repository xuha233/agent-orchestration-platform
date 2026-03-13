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
from aop.session import get_session_manager
from aop.utils.claude_config import get_claude_full_cmd, get_claude_cmd_prefix
st.set_page_config(
    page_title="AOP Dashboard",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS - 现代化 SaaS 仪表板（玻璃态 + 橙黄主题）
st.markdown("""
<style>
    /* ========== CSS 变量 ========== */
    :root {
        --bg-primary: #0c0c0c;
        --bg-secondary: #141414;
        --bg-tertiary: #1c1c1c;
        --bg-glass: rgba(255, 255, 255, 0.02);
        --bg-glass-hover: rgba(255, 255, 255, 0.05);
        --border-glass: rgba(255, 255, 255, 0.06);
        --border-glass-hover: rgba(255, 255, 255, 0.12);
        
        --text-primary: #fafafa;
        --text-secondary: #a1a1aa;
        --text-muted: #71717a;
        
        --accent: #f59e0b;
        --accent-light: #fbbf24;
        --accent-glow: rgba(245, 158, 11, 0.25);
        --success: #22c55e;
        --success-glow: rgba(34, 197, 94, 0.15);
        --warning: #f59e0b;
        --warning-glow: rgba(245, 158, 11, 0.15);
        --error: #ef4444;
        --error-glow: rgba(239, 68, 68, 0.15);
        --info: #06b6d4;
        --info-glow: rgba(6, 182, 212, 0.15);
        
        --radius: 10px;
        --radius-lg: 14px;
        --blur: 16px;
    }
    
    /* ========== 全局 ========== */
    .main .block-container { padding: 1.25rem 1.5rem; }
    section.main > div { padding-top: 0.75rem; }
    
    /* ========== 玻璃卡片 ========== */
    .glass-card {
        background: var(--bg-glass);
        backdrop-filter: blur(var(--blur));
        -webkit-backdrop-filter: blur(var(--blur));
        border: 1px solid var(--border-glass);
        border-radius: var(--radius);
        padding: 0.875rem;
        transition: all 0.2s ease;
    }
    .glass-card:hover {
        background: var(--bg-glass-hover);
        border-color: var(--border-glass-hover);
    }
    
    /* ========== 指标卡片 ========== */
    .metric-card {
        background: linear-gradient(135deg, rgba(245, 158, 11, 0.08) 0%, rgba(251, 191, 36, 0.04) 100%);
        backdrop-filter: blur(var(--blur));
        border: 1px solid var(--border-glass);
        border-radius: var(--radius);
        padding: 1rem;
        text-align: center;
        transition: all 0.2s ease;
    }
    .metric-card:hover {
        border-color: rgba(245, 158, 11, 0.25);
        box-shadow: 0 0 24px var(--accent-glow);
        transform: translateY(-2px);
    }
    .metric-card .label {
        color: var(--text-muted);
        font-size: 0.65rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 0.35rem;
    }
    .metric-card .value {
        color: var(--text-primary);
        font-size: 1.75rem;
        font-weight: 700;
        line-height: 1.2;
    }
    .metric-card.success { border-color: rgba(34, 197, 94, 0.15); }
    .metric-card.success:hover { box-shadow: 0 0 24px var(--success-glow); }
    .metric-card.warning { border-color: rgba(245, 158, 11, 0.15); }
    .metric-card.warning:hover { box-shadow: 0 0 24px var(--warning-glow); }
    
    /* ========== 状态徽章 ========== */
    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.25rem;
        padding: 0.2rem 0.5rem;
        border-radius: 9999px;
        font-size: 0.65rem;
        font-weight: 500;
        backdrop-filter: blur(8px);
    }
    .status-online { background: var(--success-glow); color: var(--success); border: 1px solid rgba(34, 197, 94, 0.25); }
    .status-offline { background: var(--error-glow); color: var(--error); border: 1px solid rgba(239, 68, 68, 0.25); }
    .status-busy { background: var(--warning-glow); color: var(--warning); border: 1px solid rgba(245, 158, 11, 0.25); }
    .status-info { background: var(--info-glow); color: var(--info); border: 1px solid rgba(6, 182, 212, 0.25); }
    
    /* ========== 区块标题 ========== */
    .section-title {
        color: var(--text-primary);
        font-size: 0.75rem;
        font-weight: 600;
        margin-bottom: 0.6rem;
        padding-bottom: 0.4rem;
        border-bottom: 1px solid var(--border-glass);
        display: flex;
        align-items: center;
        gap: 0.4rem;
    }
    .section-title .icon { font-size: 0.9rem; }
    
    /* ========== Agent 行 ========== */
    .agent-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.5rem 0.65rem;
        background: var(--bg-glass);
        border: 1px solid var(--border-glass);
        border-radius: 6px;
        margin-bottom: 0.35rem;
        transition: all 0.15s ease;
    }
    .agent-row:hover { background: var(--bg-glass-hover); border-color: var(--border-glass-hover); }
    .agent-row .name { color: var(--text-primary); font-weight: 500; font-size: 0.8rem; }
    .agent-row .role { color: var(--text-muted); font-size: 0.65rem; }
    
    /* ========== 活动项 ========== */
    .activity-item {
        display: flex;
        gap: 0.5rem;
        padding: 0.4rem 0;
        border-bottom: 1px solid var(--border-glass);
        font-size: 0.75rem;
    }
    .activity-item:last-child { border-bottom: none; }
    .activity-item .icon { width: 18px; text-align: center; }
    .activity-item .text { color: var(--text-secondary); flex: 1; }
    
    /* ========== 进度条 ========== */
    .progress-bar {
        height: 5px;
        background: var(--bg-tertiary);
        border-radius: 3px;
        overflow: hidden;
        margin-top: 0.4rem;
    }
    .progress-bar .fill {
        height: 100%;
        background: linear-gradient(90deg, var(--accent), var(--success));
        border-radius: 3px;
    }
    
    /* ========== 问题徽章 ========== */
    .issue-badge {
        display: flex;
        align-items: center;
        gap: 0.4rem;
        padding: 0.4rem 0.6rem;
        background: var(--warning-glow);
        border-left: 2px solid var(--warning);
        border-radius: 0 5px 5px 0;
        margin-bottom: 0.35rem;
        font-size: 0.75rem;
        color: var(--text-primary);
    }
    .issue-badge.error { background: var(--error-glow); border-left-color: var(--error); }
    .issue-badge.info { background: var(--info-glow); border-left-color: var(--info); }
    
    /* ========== 快捷操作 ========== */
    .quick-action {
        background: var(--bg-glass);
        border: 1px solid var(--border-glass);
        border-radius: 6px;
        padding: 0.5rem 0.6rem;
        cursor: pointer;
        transition: all 0.2s ease;
        display: flex;
        align-items: center;
        gap: 0.4rem;
    }
    .quick-action:hover {
        background: var(--accent);
        border-color: var(--accent);
        box-shadow: 0 0 16px var(--accent-glow);
    }
    .quick-action .icon { font-size: 0.9rem; }
    .quick-action .label { color: var(--text-secondary); font-size: 0.75rem; }
    .quick-action:hover .label { color: white; }
    
    /* ========== 指令卡片 ========== */
    .cmd-card {
        background: var(--bg-glass);
        border: 1px solid var(--border-glass);
        border-radius: 6px;
        padding: 0.6rem 0.75rem;
        margin-bottom: 0.4rem;
        transition: all 0.15s ease;
        cursor: pointer;
    }
    .cmd-card:hover {
        border-color: var(--accent);
        background: var(--bg-glass-hover);
    }
    .cmd-card .cmd-label { color: var(--text-primary); font-weight: 500; font-size: 0.8rem; }
    .cmd-card .cmd-text { color: var(--accent); font-size: 0.7rem; font-family: monospace; margin-top: 0.2rem; }
    .cmd-card .cmd-hint { color: var(--text-muted); font-size: 0.65rem; margin-top: 0.15rem; }
    
    /* ========== Streamlit 覆盖 ========== */
    [data-testid="stMetric"] {
        background: var(--bg-glass);
        border: 1px solid var(--border-glass);
        border-radius: var(--radius);
        padding: 0.6rem;
        backdrop-filter: blur(8px);
    }
    [data-testid="stMetric"] label { color: var(--text-muted) !important; font-size: 0.65rem !important; }
    [data-testid="stMetric"] [data-testid="stMetricValue"] { color: var(--text-primary) !important; }
    
    [data-testid="stSidebar"] { background: var(--bg-primary); }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color: var(--text-secondary); }
    
    .stButton button {
        background: var(--bg-glass);
        border: 1px solid var(--border-glass);
        color: var(--text-primary);
        border-radius: 6px;
        backdrop-filter: blur(8px);
        transition: all 0.2s ease;
    }
    .stButton button:hover {
        background: var(--accent);
        border-color: var(--accent);
        box-shadow: 0 0 12px var(--accent-glow);
        color: #000;
    }
    
    .stProgress > div > div { background: var(--bg-tertiary); border-radius: 3px; }
    .stProgress > div > div > div { background: linear-gradient(90deg, var(--accent), var(--success)); }
    
    /* ========== 头部渐变 ========== */
    .header-gradient {
        background: linear-gradient(135deg, #78350f 0%, #b45309 50%, #d97706 100%);
        border-radius: var(--radius-lg);
        padding: 1.25rem;
        margin-bottom: 1.25rem;
        border: 1px solid rgba(245, 158, 11, 0.15);
        box-shadow: 0 0 32px rgba(245, 158, 11, 0.1);
    }
    
    /* ========== 工作区卡片 ========== */
    .workspace-card {
        background: var(--bg-glass);
        border: 1px solid var(--border-glass);
        border-radius: 6px;
        padding: 0.5rem 0.6rem;
        margin-bottom: 0.35rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        transition: all 0.15s ease;
    }
    .workspace-card:hover { border-color: var(--accent); background: var(--bg-glass-hover); }
    
    /* ========== 分类标题 ========== */
    .category-title {
        color: var(--text-primary);
        font-size: 0.85rem;
        font-weight: 600;
        margin-top: 1rem;
        margin-bottom: 0.5rem;
        padding-bottom: 0.35rem;
        border-bottom: 1px solid var(--border-glass);
    }
    .category-desc {
        color: var(--text-muted);
        font-size: 0.7rem;
        margin-bottom: 0.5rem;
    }

/* 紧凑布局 - 提升信息密度 */
div[data-testid="stVerticalBlock"] > div:has(> div[data-testid="stMetric"]) {
    gap: 0.25rem;
}

/* 按钮紧凑 */
.stButton button {
    padding: 0.4rem 0.75rem;
    font-size: 0.85rem;
}

/* 输入框紧凑 */
.stTextInput input, .stSelectbox select {
    padding: 0.35rem 0.5rem;
    font-size: 0.85rem;
}

/* expander 紧凑 */
.streamlit-expanderHeader {
    font-size: 0.9rem;
    padding: 0.5rem;
}

/* 项目切换下拉框 */
div[data-baseweb="select"] > div {
    min-height: 32px;
    font-size: 0.85rem;
}

/* 侧边栏优化 */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0c0c0c 0%, #141414 100%);
}

[data-testid="stSidebar"] [data-testid="stRadio"] > label {
    display: none;
}

[data-testid="stSidebar"] [data-testid="stRadio"] > div {
    gap: 0.25rem;
}

[data-testid="stSidebar"] [data-testid="stRadio"] > div > div {
    padding: 0.5rem 0.75rem;
    border-radius: 6px;
    background: transparent;
    border: 1px solid transparent;
    transition: all 0.2s ease;
}

[data-testid="stSidebar"] [data-testid="stRadio"] > div > div:hover {
    background: rgba(245, 158, 11, 0.1);
    border-color: rgba(245, 158, 11, 0.3);
}

[data-testid="stSidebar"] [data-testid="stRadio"] > div > div[data-checked="true"] {
    background: rgba(245, 158, 11, 0.15);
    border-color: rgba(245, 158, 11, 0.5);
    color: #fbbf24;
}

</style>
""", unsafe_allow_html=True)


# ============ 初始化 ============

# 启动命令监听器（模块加载时立即启动）
_listener_started = False

def check_openclaw_status() -> tuple:
    """检查 OpenClaw Gateway 是否运行
    返回: (is_running: bool, status_text: str)
    
    检测 Gateway WebSocket 端口 (18789)，而非 Chrome CDP 端口 (18792)
    """
    import socket
    GATEWAY_PORT = 18789  # Gateway WebSocket 端口
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex(("127.0.0.1", GATEWAY_PORT))
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


# ============ 会话持久化 ============

MESSAGES_DIR = Path.home() / ".aop" / "projects"


def _get_messages_file_path(workspace_id: str) -> Path:
    """获取工作区消息文件的路径"""
    messages_dir = MESSAGES_DIR / workspace_id / "sessions"
    messages_dir.mkdir(parents=True, exist_ok=True)
    return messages_dir / "messages.json"


def _load_messages_from_file(workspace_id: str) -> list:
    """从文件加载消息历史"""
    messages_file = _get_messages_file_path(workspace_id)
    if messages_file.exists():
        try:
            with open(messages_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            _logger.warning(f"Failed to load messages for {workspace_id}: {e}")
    return []


def _save_messages_to_file(workspace_id: str, messages: list) -> None:
    """保存消息历史到文件"""
    messages_file = _get_messages_file_path(workspace_id)
    try:
        with open(messages_file, 'w', encoding='utf-8') as f:
            json.dump(messages, f, ensure_ascii=False, indent=2)
    except IOError as e:
        _logger.error(f"Failed to save messages for {workspace_id}: {e}")


def get_messages_for_workspace(workspace_id: Optional[str]) -> list:
    """获取指定工作区的对话历史（支持持久化恢复）"""
    if not workspace_id:
        return []
    
    # 如果内存中有，直接返回
    if 'workspace_messages' not in st.session_state:
        st.session_state.workspace_messages = {}
    
    if workspace_id in st.session_state.workspace_messages:
        return st.session_state.workspace_messages[workspace_id]
    
    # 否则从文件加载
    messages = _load_messages_from_file(workspace_id)
    st.session_state.workspace_messages[workspace_id] = messages
    return messages


def save_messages_for_workspace(workspace_id: Optional[str], messages: list) -> None:
    """保存指定工作区的对话历史（持久化到文件）"""
    if not workspace_id:
        return
    
    # 保存到内存
    st.session_state.workspace_messages[workspace_id] = messages
    
    # 持久化到文件
    _save_messages_to_file(workspace_id, messages)


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
    """读取 .aop 目录下的文件内容（带文件锁处理）
    
    支持两种存储格式：
    1. 文件格式: .aop/hypotheses.json
    2. 目录格式: .aop/hypotheses.json/hypotheses.json (CLI PersistenceManager)
    """
    aop_dir = get_aop_dir()
    file_path = aop_dir / filename
    
    # 如果是目录，尝试读取目录内的同名文件
    if file_path.is_dir():
        inner_file = file_path / filename
        if inner_file.exists():
            file_path = inner_file
        else:
            return None
    
    if file_path.exists():
        try:
            return file_path.read_text(encoding="utf-8")
        except PermissionError:
            # 文件被其他进程锁定，返回 None
            return None
        except Exception:
            return None
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
    data = read_aop_json("hypotheses.json")
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



def get_project_progress_data(project_path: str) -> dict:
    """获取项目进度数据
    
    Args:
        project_path: 项目根目录路径
        
    Returns:
        包含假设、学习、Git、测试状态的字典
    """
    result = {
        "hypotheses": {"total": 0, "validated": 0, "testing": 0, "pending": 0},
        "learnings": {"total": 0, "latest": ""},
        "git": {"branch": "unknown", "changes": 0},
        "tests": {"passed": 0, "total": 0}
    }
    
    aop_dir = Path(project_path) / ".aop"
    
    # 假设数据
    hypotheses_file = aop_dir / "hypotheses.json"
    if hypotheses_file.exists():
        try:
            data = json.loads(hypotheses_file.read_text(encoding="utf-8"))
            hypotheses = list(data.get("data", {}).values())
            result["hypotheses"]["total"] = len(hypotheses)
            for h in hypotheses:
                status = h.get("state", "pending")
                if status == "validated":
                    result["hypotheses"]["validated"] += 1
                elif status == "testing":
                    result["hypotheses"]["testing"] += 1
                else:
                    result["hypotheses"]["pending"] += 1
        except Exception:
            pass
    
    # 学习记录
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
    
    # Git 状态
    try:
        branch_result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=5
        )
        result["git"]["branch"] = branch_result.stdout.strip() or "unknown"
        
        status_result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=5
        )
        changes = [line for line in status_result.stdout.strip().split("\n") if line]
        result["git"]["changes"] = len(changes)
    except Exception:
        pass
    
    # 测试状态（运行 pytest）
    try:
        test_result = subprocess.run(
            ["pytest", "--collect-only", "-q"],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=30
        )
        # 解析测试收集结果
        output = test_result.stdout + test_result.stderr
        import re as regex
        # 匹配 "X tests collected" 或 "X items collected"
        match = regex.search(r"(\d+)\s+(?:tests?|items?)\s+(?:collected|selected)", output, regex.IGNORECASE)
        if match:
            result["tests"]["total"] = int(match.group(1))
        
        # 运行测试获取通过数
        run_result = subprocess.run(
            ["pytest", "-q", "--tb=no", "-x"],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=60
        )
        # 解析测试结果
        run_output = run_result.stdout + run_result.stderr
        # 匹配 "X passed"
        passed_match = regex.search(r"(\d+)\s+passed", run_output)
        if passed_match:
            result["tests"]["passed"] = int(passed_match.group(1))
        elif result["tests"]["total"] > 0 and run_result.returncode == 0:
            # 如果测试全部通过，passed = total
            result["tests"]["passed"] = result["tests"]["total"]
    except Exception:
        pass
    
    return result


# ============ 页面组件 ============

def render_sidebar():
    """渲染侧边栏"""
    with st.sidebar:
        # Logo 区域
        st.markdown("""
        <div style="padding: 0.5rem 0; border-bottom: 1px solid rgba(255,255,255,0.1);">
            <div style="font-size: 1.25rem; font-weight: 700; color: #f59e0b;">🤖 AOP</div>
            <div style="font-size: 0.7rem; color: rgba(255,255,255,0.5);">Agent 编排平台</div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<div style='height: 0.75rem;'></div>", unsafe_allow_html=True)

        # 获取设置，决定是否显示调试日志
        sm = st.session_state.settings_manager
        show_dev_console = sm.get_show_dev_console()

        pages = ["🏠 首页", "💬 敏捷教练", "📚 项目记忆", "📁 工作区", "⚙️ 设置"]
        if show_dev_console:
            pages.append("🖥️ 调试日志")

        page = st.radio(
            "导航",
            pages,
            label_visibility="collapsed",
        )

        st.markdown("<div style='height: 0.5rem; border-bottom: 1px solid rgba(255,255,255,0.1);'></div>", unsafe_allow_html=True)

        # 项目快速切换下拉菜单
        wm = st.session_state.workspace_manager
        workspaces = wm.list_workspaces()

        if workspaces:
            st.markdown("""
            <div style="font-size: 0.7rem; color: rgba(255,255,255,0.5); margin: 0.5rem 0 0.25rem 0;">项目切换</div>
            """, unsafe_allow_html=True)
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

        st.markdown("<div style='height: 0.5rem; border-bottom: 1px solid rgba(255,255,255,0.1);'></div>", unsafe_allow_html=True)

        # 当前 Agent 状态
        if st.session_state.current_agent:
            agent = st.session_state.current_agent
            st.markdown(f"""
            <div style="background: rgba(245,158,11,0.1); border: 1px solid rgba(245,158,11,0.3); border-radius: 6px; padding: 0.5rem; margin: 0.5rem 0;">
                <div style="font-size: 0.65rem; color: rgba(255,255,255,0.5);">当前 Agent</div>
                <div style="font-size: 0.85rem; color: #fbbf24; font-weight: 500;">{agent.name}</div>
            </div>
            """, unsafe_allow_html=True)

        # 底部版本信息
        st.markdown("""
        <div style="position: fixed; bottom: 1rem; left: 1rem; right: 1rem; font-size: 0.65rem; color: rgba(255,255,255,0.3);">
            <div>AOP v0.4.0</div>
            <a href="https://github.com/xuha233/agent-orchestration-platform" style="color: rgba(245,158,11,0.6); text-decoration: none;">GitHub</a>
        </div>
        """, unsafe_allow_html=True)

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
    """首页 - 现代化 SaaS 分析仪表板（玻璃态 + 橙黄主题）"""
    wm = st.session_state.workspace_manager
    sm = st.session_state.settings_manager
    
    # ========== 数据准备 ==========
    primary_agent_id = sm.get_primary_agent()
    agents = get_available_agents()
    hypotheses = get_hypotheses_data()
    sprint = get_sprint_data()
    stats = get_project_stats()
    workspaces = wm.list_workspaces()
    
    # 假设统计
    h_pending = len([h for h in hypotheses if h.get("state") == "pending"])
    h_testing = len([h for h in hypotheses if h.get("state") == "testing"])
    h_validated = len([h for h in hypotheses if h.get("state") == "validated"])
    h_total = len(hypotheses)
    progress_pct = int((h_validated / h_total * 100) if h_total > 0 else 0)
    
    # 项目实时状态
    if st.session_state.current_workspace:
        project_path = st.session_state.current_workspace.project_path
    else:
        project_path = "G:/docker/aop"
    progress_data = get_project_progress_data(project_path)
    
    # ========== 头部 ========== 
    project_name = st.session_state.current_workspace.name if st.session_state.current_workspace else "AOP 仪表板"
    
    st.markdown(f"""
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
    """, unsafe_allow_html=True)
    
    # ========== 核心指标（4 个卡片）==========
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="label">假设验证</div>
            <div class="value">{h_validated}/{h_total}</div>
            <div class="progress-bar"><div class="fill" style="width: {progress_pct}%;"></div></div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        t = progress_data["tests"]
        test_status = f"{t['passed']}/{t['total']}" if t['total'] > 0 else "无"
        test_class = "success" if t['passed'] == t['total'] and t['total'] > 0 else "warning"
        st.markdown(f"""
        <div class="metric-card {test_class}">
            <div class="label">测试通过</div>
            <div class="value">{test_status}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="label">代码行数</div>
            <div class="value">{stats['line_count']:,}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        g = progress_data["git"]
        git_status = "✓" if g['changes'] == 0 else f"±{g['changes']}"
        st.markdown(f"""
        <div class="metric-card {'success' if g['changes'] == 0 else 'warning'}">
            <div class="label">Git: {g['branch']}</div>
            <div class="value">{git_status}</div>
        </div>
        """, unsafe_allow_html=True)
    
    # ========== 两栏布局 ==========
    left_col, right_col = st.columns([2, 1])
    
    # ========== 左栏 ==========
    with left_col:
        # === 1. 项目进度 ===
        st.markdown("""<div class="glass-card"><div class="section-title"><span class="icon">📈</span> 项目进度</div></div>""", unsafe_allow_html=True)
        
        if sprint:
            st.markdown(f"**当前冲刺**: {sprint.get('original_input', '无')[:60]}")
            st.caption(f"ID: {sprint.get('sprint_id', '-')}")
        else:
            st.info("暂无活跃冲刺")
        
        if h_pending > 0:
            next_h = [h for h in hypotheses if h.get("state") == "pending"][0]
            st.markdown(f"**下一个假设**: {next_h.get('statement', '-')[:50]}...")
        
        st.markdown("---")
        
        # === 2. 最近活动 ===
        st.markdown("""<div class="glass-card"><div class="section-title"><span class="icon">📋</span> 最近活动</div></div>""", unsafe_allow_html=True)
        
        activities = []
        for h in hypotheses[:6]:
            state = h.get("state", "pending")
            statement = h.get("statement", "")[:30]
            icon = "✅" if state == "validated" else "🔬" if state == "testing" else "📝"
            state_text = "已验证" if state == "validated" else "测试中" if state == "testing" else "待处理"
            activities.append({"icon": icon, "text": statement + "...", "state": state_text})
        
        if activities:
            for act in activities:
                st.markdown(f"""<div class="activity-item"><span class="icon">{act['icon']}</span><span class="text">{act['text']}</span><span style="color: var(--text-muted); font-size: 0.65rem;">{act['state']}</span></div>""", unsafe_allow_html=True)
        else:
            st.info("暂无最近活动")
        
        st.markdown("---")
        
        # === 3. 当前迭代 ===
        st.markdown("""<div class="glass-card"><div class="section-title"><span class="icon">🎯</span> 当前迭代</div></div>""", unsafe_allow_html=True)
        
        memory_content = read_aop_file("PROJECT_MEMORY.md")
        if memory_content:
            in_progress = parse_md_section(memory_content, "进行中")
            if in_progress:
                st.markdown(in_progress[:350])
            else:
                st.info("暂无进行中的迭代目标")
        else:
            st.info("未找到项目记忆文件")
    
    # ========== 右栏 ==========
    with right_col:
        # === 1. Agent 状态 ===
        st.markdown("""<div class="glass-card"><div class="section-title"><span class="icon">🤖</span> Agent 状态</div></div>""", unsafe_allow_html=True)
        
        # 主 Agent
        if primary_agent_id:
            agent_names = {"claude_code": "Claude Code", "opencode": "OpenCode", "openclaw": "OpenClaw"}
            agent_name = agent_names.get(primary_agent_id, primary_agent_id)
            is_available = any(a.id == primary_agent_id for a in agents)
            badge = "status-online" if is_available else "status-offline"
            status_icon = "●" if is_available else "○"
            status_text = "可用" if is_available else "离线"
            st.markdown(f"""
            <div class="agent-row">
                <div><div class="name">{agent_name}</div><div class="role">主 Agent · {status_text}</div></div>
                <span class="status-badge {badge}">{status_icon}</span>
            </div>
            """, unsafe_allow_html=True)
        
        # 子 Agent
        sub_agents = [
            {"name": "开发者", "role": "实现"},
            {"name": "审查者", "role": "代码审查"},
            {"name": "测试者", "role": "验证"},
        ]
        
        for agent in sub_agents:
            active_h = [h for h in hypotheses if h.get("state") == "testing"]
            status = "忙碌" if active_h else "空闲"
            badge = "status-busy" if active_h else "status-info"
            icon = "●" if active_h else "○"
            st.markdown(f"""
            <div class="agent-row">
                <div><div class="name">{agent['name']}</div><div class="role">{agent['role']}</div></div>
                <span class="status-badge {badge}">{icon} {status}</span>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # === 2. 待处理问题 ===
        st.markdown("""<div class="glass-card"><div class="section-title"><span class="icon">⚠️</span> 待处理</div></div>""", unsafe_allow_html=True)
        
        issues = []
        if h_pending > 0:
            issues.append({"text": f"📋 {h_pending} 个假设待验证", "type": ""})
        if h_testing > 0:
            issues.append({"text": f"🔬 {h_testing} 个假设测试中", "type": "info"})
        if not agents:
            issues.append({"text": "🔴 无可用 Agent", "type": "error"})
        
        if issues:
            for issue in issues:
                st.markdown(f"""<div class="issue-badge {issue['type']}">{issue['text']}</div>""", unsafe_allow_html=True)
        else:
            st.success("✅ 状态良好")
        
        st.markdown("---")
        
        # === 3. 快速操作 ===\n        # 技术债：功能重复，已移至其他页面
        
        st.markdown("---")
        
        # === 4. 工作区快速启动 ===\n        # 技术债：功能暂不可用，已移至工作区页面\n        # TODO: 重构为在工作区页面提供启动功能
    
    # ========== 刷新控制 ==========
    st.markdown("---")

def page_coach():
    """敏捷教练页面 - 快捷指令面板"""
    sm = st.session_state.settings_manager
    primary_agent = sm.get_primary_agent()

    # ========== 头部 ==========
    st.markdown("""
    <div class="header-gradient">
        <h1 style="margin: 0; font-size: 1.35rem; color: white; font-weight: 600;">🚀 敏捷教练</h1>
        <p style="margin: 0.2rem 0 0 0; color: rgba(255,255,255,0.75); font-size: 0.75rem;">任务执行与代码审查</p>
    </div>
    """, unsafe_allow_html=True)

    # === OpenClaw 状态检测 ===
    openclaw_running, openclaw_status = check_openclaw_status()
    if openclaw_running:
        st.markdown(f"""<div class="issue-badge info">✅ OpenClaw Gateway: {openclaw_status}</div>""", unsafe_allow_html=True)
    else:
        st.markdown(f"""<div class="issue-badge">⚠️ OpenClaw Gateway: {openclaw_status}</div>""", unsafe_allow_html=True)

    # === 项目状态概览 ===
    current_workspace = st.session_state.current_workspace
    project_path = current_workspace.project_path if current_workspace else None
    workspace_id = current_workspace.id if current_workspace else None

    if project_path:
        # 显示项目信息
        st.markdown("""<div class="glass-card"><div class="section-title"><span class="icon">📊</span> 项目状态</div></div>""", unsafe_allow_html=True)
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

    st.markdown("---")
    
    # === 启动 CLI 按钮 ===
    st.markdown("""<div class="glass-card"><div class="section-title"><span class="icon">🖥️</span> 启动 CLI</div></div>""", unsafe_allow_html=True)

    # 检查是否选择了项目
    if not project_path:
        st.warning("请先选择一个项目工作区")
        st.info("前往「工作区」页面选择或创建工作区")
    else:
        st.caption(f"📁 当前项目: `{project_path}`")

        # 根据主 Agent 类型显示不同的启动选项
        if primary_agent == "openclaw":
            # OpenClaw 模式 - TUI + session 隔离
            import subprocess
            import shutil
            import os
            import tempfile
            import uuid
            from pathlib import Path
            
            # 项目名称作为 session 标识（处理边缘情况）
            project_name_safe = Path(project_path).name
            sanitized = "".join(c if c.isalnum() else "_" for c in project_name_safe).strip("_")
            session_name = f"aop_{sanitized}" if sanitized else "aop_default"
            
            col1, col2, col3 = st.columns([2, 2, 1])
            
            with col1:
                if st.button("🎯 启动 TUI", use_container_width=True, key="launch_openclaw_tui"):
                    if not shutil.which("openclaw"):
                        st.error("openclaw 未安装或不在 PATH 中")
                    else:
                        # 构建 AOP 敏捷教练系统提示（复用 Claude Code 模式的逻辑）
                        system_prompt = build_agent_system_prompt(Path(project_path))
                        
                        # 将系统提示词写入项目的 .openclaw/SYSTEM.md（OpenClaw 会自动加载）
                        openclaw_system_dir = os.path.join(project_path, ".openclaw")
                        os.makedirs(openclaw_system_dir, exist_ok=True)
                        system_md_path = os.path.join(openclaw_system_dir, "SYSTEM.md")
                        
                        with open(system_md_path, "w", encoding="utf-8") as f:
                            f.write(system_prompt)
                        
                        # 安全处理：移除可能导致问题的字符
                        safe_project_name = project_name_safe.replace('"', '').replace("'", "")
                        safe_project_path = project_path.replace('"', '').replace("'", "")
                        
                        # 初始化消息（简洁的启动指令）
                        init_message = f"""当前项目：{safe_project_name}
路径：{safe_project_path}

请自我介绍为「AOP 敏捷教练」，并汇报当前项目状态和下一步建议。

注意：你已获得完整的 AOP 敏捷教练提示词（在 .openclaw/SYSTEM.md 中），请根据其中的假设状态和学习记录给出针对性建议。"""
                        
                        if sys.platform == "win32":
                            safe_title = project_name_safe.replace('"', '""')
                            safe_msg = init_message.replace('"', '""')
                            cmd = f'openclaw tui --session {session_name} --message "{safe_msg}"'
                            subprocess.Popen(
                                f'start "AOP 敏捷教练 - {safe_title}" cmd /k "cd /d {safe_project_path} && {cmd}"',
                                shell=True
                            )
                        elif sys.platform == "darwin":
                            # macOS: AppleScript 转义
                            safe_msg = init_message.replace('\\', '\\\\').replace('"', '\\"')
                            apple_script = f'tell application "Terminal" to do script "cd \"{project_path}\" && openclaw tui --session {session_name} --message \"{safe_msg}\""'
                            subprocess.Popen(["osascript", "-e", apple_script])
                        else:
                            # Linux: 尝试多种终端
                            safe_msg = init_message.replace('"', '\\"')
                            terminal = shutil.which("gnome-terminal") or shutil.which("konsole") or shutil.which("xterm")
                            if terminal:
                                subprocess.Popen([
                                    terminal, "--", "bash", "-c",
                                    f'cd "{project_path}" && openclaw tui --session {session_name} --message "{safe_msg}"; exec bash'
                                ])
                            else:
                                st.warning("未找到支持的终端模拟器 (gnome-terminal/konsole/xterm)")
                        st.toast(f"已启动 TUI (session: {session_name})", icon="✅")
            
            with col2:
                if st.button("🌐 打开 Web", use_container_width=True, key="launch_openclaw_web"):
                    import webbrowser
                    webbrowser.open("http://127.0.0.1:18789/")
                    st.toast("已打开 Web 对话", icon="✅")
            
            with col3:
                if st.button("🔄", use_container_width=True, key="refresh_status"):
                    st.rerun()
            
            st.caption(f"💡 Session: `{session_name}` | 项目: `{project_path}`")

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
                                hypotheses = list(data.get("data", {}).values())
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
                                learnings = data.get("data", {}).get("records", [])
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
                            # 输出捕获文件
                            capture_file = os.path.join(tempfile.gettempdir(), "aop_session_output.txt")
                            save_session_script = os.path.join(os.path.dirname(os.path.dirname(__file__)), "session", "save_session.py")
                            
                            # 将系统提示词写入项目的 CLAUDE.md（Claude Code 会自动加载）
                            claude_md_path = os.path.join(project_path, ".claude", "CLAUDE.md")
                            os.makedirs(os.path.dirname(claude_md_path), exist_ok=True)
                            
                            # 读取系统提示词并写入 CLAUDE.md
                            with open(prompt_file, 'r', encoding='utf-8') as pf:
                                system_prompt_content = pf.read()
                            
                            with open(claude_md_path, 'w', encoding='utf-8') as cf:
                                cf.write(system_prompt_content)
                            
                            with open(ps1_file, "w", encoding="utf-8") as f:
                                f.write('Set-Location "' + project_path + '"\n')
                                f.write('$ProjectId = "' + workspace_id + '"\n')
                                f.write('$Workspace = "' + project_path.replace('\\', '/') + '"\n')
                                f.write('\n')
                                
                                # 从 workspace metadata 读取会话 ID
                                saved_session_id = None
                                if current_workspace and current_workspace.metadata:
                                    if primary_agent == "claude_code":
                                        saved_session_id = current_workspace.metadata.get("claude_session_id")
                                    else:
                                        saved_session_id = current_workspace.metadata.get("opencode_session_id")
                                
                                if saved_session_id:
                                    f.write('Write-Host "========================================" -ForegroundColor Cyan\n')
                                    f.write('Write-Host "  Resuming session: ' + saved_session_id[:8] + '..." -ForegroundColor Green\n')
                                    f.write('Write-Host "========================================" -ForegroundColor Cyan\n')
                                    f.write('\n')
                                
                                # 启动命令（CLAUDE.md 会自动加载）
                                if primary_agent == "claude_code":
                                    if saved_session_id:
                                        f.write(' '.join(get_claude_cmd_prefix()) + ' --resume ' + saved_session_id + '\n')
                                    else:
                                        f.write(' '.join(get_claude_cmd_prefix()) + '\n')
                                else:
                                    if saved_session_id:
                                        f.write('opencode --resume ' + saved_session_id + '\n')
                                    else:
                                        f.write('opencode\n')
                                
                            project_name = Path(project_path).name
                            subprocess.Popen(
                                'start "AOP 敏捷教练 - ' + project_name + '" powershell -NoExit -ExecutionPolicy Bypass -File "' + ps1_file + '"',
                                shell=True
                            )
                        elif sys.platform == "darwin":
                            # macOS: 使用 Terminal
                            # 将系统提示词写入项目的 CLAUDE.md（Claude Code 和 OpenCode 都会自动加载）
                            claude_md_path = os.path.join(project_path, ".claude", "CLAUDE.md")
                            os.makedirs(os.path.dirname(claude_md_path), exist_ok=True)
                            
                            with open(prompt_file, 'r', encoding='utf-8') as pf:
                                system_prompt_content = pf.read()
                            
                            with open(claude_md_path, 'w', encoding='utf-8') as cf:
                                cf.write(system_prompt_content)
                            
                            # 检查是否有保存的会话 ID
                            saved_session_id = None
                            try:
                                sm = get_session_manager()
                                provider = "claude" if primary_agent == "claude_code" else "opencode"
                                session_info = sm.get_latest_session(workspace_id, provider)
                                if session_info:
                                    saved_session_id = session_info.session_id
                            except Exception:
                                pass
                            
                            if primary_agent == "claude_code":
                                if saved_session_id:
                                    full_cmd = get_claude_full_cmd() + ' --resume ' + saved_session_id
                                else:
                                    full_cmd = get_claude_full_cmd() + ' --system-prompt "$(cat \"' + prompt_file + '\")"'
                            else:
                                if saved_session_id:
                                    full_cmd = 'opencode --resume ' + saved_session_id
                                else:
                                    full_cmd = 'opencode'
                            apple_script = 'tell application "Terminal" to do script "cd \"' + project_path + '\" && ' + full_cmd + '"'
                            subprocess.Popen(["osascript", "-e", apple_script])
                        else:
                            # Linux: 尝试 gnome-terminal 或 xterm
                            # 将系统提示词写入项目的 CLAUDE.md（Claude Code 和 OpenCode 都会自动加载）
                            claude_md_path = os.path.join(project_path, ".claude", "CLAUDE.md")
                            os.makedirs(os.path.dirname(claude_md_path), exist_ok=True)
                            
                            with open(prompt_file, 'r', encoding='utf-8') as pf:
                                system_prompt_content = pf.read()
                            
                            with open(claude_md_path, 'w', encoding='utf-8') as cf:
                                cf.write(system_prompt_content)
                            
                            # 检查是否有保存的会话 ID
                            saved_session_id = None
                            try:
                                sm = get_session_manager()
                                provider = "claude" if primary_agent == "claude_code" else "opencode"
                                session_info = sm.get_latest_session(workspace_id, provider)
                                if session_info:
                                    saved_session_id = session_info.session_id
                            except Exception:
                                pass
                            
                            if primary_agent == "claude_code":
                                if saved_session_id:
                                    full_cmd = get_claude_full_cmd() + ' --resume ' + saved_session_id
                                else:
                                    full_cmd = get_claude_full_cmd() + ' --system-prompt "$(cat ' + prompt_file + ')"'
                            else:
                                if saved_session_id:
                                    full_cmd = 'opencode --resume ' + saved_session_id
                                else:
                                    full_cmd = 'opencode'
                            
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

    # ========== 假设驱动开发流程 ==========

    # 读取假设数据
    hypotheses_data = get_hypotheses_data()

    # 按状态和优先级分类
    pending_hypotheses = [h for h in hypotheses_data if h.get("state") == "pending"]
    testing_hypotheses = [h for h in hypotheses_data if h.get("state") == "testing"]
    validated_hypotheses = [h for h in hypotheses_data if h.get("state") == "validated"]

    # 优先级排序函数
    priority_order = {"high": 0, "medium": 1, "quick_win": 2, "low": 3}
    def sort_by_priority(h):
        return priority_order.get(h.get("priority", "medium"), 99)

    pending_hypotheses.sort(key=sort_by_priority)

    # 当前选中的指令
    if "_selected_cmds" not in st.session_state:
        st.session_state._selected_cmds = []

    # === 1. 🚀 快速开始 ===
    st.markdown("""<div class="glass-card"><div class="section-title"><span class="icon">🚀</span> 快速开始</div></div>""", unsafe_allow_html=True)

    st.markdown("""
    <div style="padding: 0.5rem 0; color: var(--text-secondary); font-size: 0.85rem;">
    让教练分析项目状态，告诉你下一步该做什么
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([3, 1])
    with col1:
        quick_start_cmd = "-aop run 你好，请分析项目状态并给出下一步建议"
        st.code(quick_start_cmd, language="bash")
    with col2:
        if st.button("☑️ 选择", use_container_width=True, key="copy_quick_start"):
            if quick_start_cmd not in st.session_state._selected_cmds:
                st.session_state._selected_cmds.append(quick_start_cmd)
            st.toast("已添加到选择篮", icon="✅")

    st.markdown("---")

    # === 2. 📝 我想验证... ===
    st.markdown("""<div class="glass-card"><div class="section-title"><span class="icon">📝</span> 我想验证...</div></div>""", unsafe_allow_html=True)

    st.markdown("""
    <div style="padding: 0.25rem 0; color: var(--text-muted); font-size: 0.75rem;">
    格式：我认为如果 <strong>______</strong>，就能 <strong>______</strong>
    </div>
    """, unsafe_allow_html=True)

    # 假设输入框
    hypothesis_if = st.text_input(
        "如果...",
        placeholder="添加缓存",
        key="hypothesis_if_input",
        label_visibility="collapsed"
    )

    hypothesis_then = st.text_input(
        "就能...",
        placeholder="提升页面加载速度50%",
        key="hypothesis_then_input",
        label_visibility="collapsed"
    )

    col1, col2 = st.columns([3, 1])
    with col1:
        if hypothesis_if and hypothesis_then:
            create_cmd = f'-aop hypothesis create "如果{hypothesis_if}，就能{hypothesis_then}"'
            st.code(create_cmd, language="bash")
        else:
            st.caption("示例：如果添加缓存，就能提升页面加载速度50%")
    with col2:
        if st.button("创建假设", use_container_width=True, key="create_hypothesis_btn", disabled=not (hypothesis_if and hypothesis_then)):
            if hypothesis_if and hypothesis_then:
                cmd = f'-aop hypothesis create "如果{hypothesis_if}，就能{hypothesis_then}"'
                if cmd not in st.session_state._selected_cmds:
                    st.session_state._selected_cmds.append(cmd)
                st.toast("已添加到选择篮", icon="✅")

    st.markdown("---")

    # === 3. 🔬 待验证假设 ===
    st.markdown("""<div class="glass-card"><div class="section-title"><span class="icon">🔬</span> 待验证假设</div></div>""", unsafe_allow_html=True)

    total_pending = len(pending_hypotheses) + len(testing_hypotheses)
    if total_pending == 0:
        st.info("🎉 暂无待验证假设！")
    else:
        st.caption(f"共 {total_pending} 个假设待验证")

        # 测试中的假设
        if testing_hypotheses:
            st.markdown("""<div style="font-size: 0.75rem; color: var(--warning); margin-bottom: 0.25rem;">⏳ 测试中</div>""", unsafe_allow_html=True)
            for h in testing_hypotheses[:3]:
                h_id = h.get("hypothesis_id", "?")
                statement = h.get("statement", "")[:50]
                with st.container():
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.markdown(f"□ **{h_id}**: {statement}...")
                    with col2:
                        verify_cmd = f"-aop run 验证假设 {h_id}"
                        if st.button("☑️", key=f"select_testing_{h_id}", help=f"复制: {verify_cmd}"):
                            if verify_cmd not in st.session_state._selected_cmds:
                                st.session_state._selected_cmds.append(verify_cmd)
                            st.toast("已添加到选择篮", icon="✅")
                st.markdown("---")

        # 待处理假设（按优先级）
        if pending_hypotheses:
            st.markdown("""<div style="font-size: 0.75rem; color: var(--text-muted); margin: 0.25rem 0;">📋 待处理</div>""", unsafe_allow_html=True)
            for h in pending_hypotheses[:5]:
                h_id = h.get("hypothesis_id", "?")
                statement = h.get("statement", "")[:50]
                priority = h.get("priority", "medium")
                priority_label = {"high": "高", "medium": "中", "quick_win": "快赢", "low": "低"}.get(priority, priority)
                priority_color = {"high": "#ef4444", "medium": "#f59e0b", "quick_win": "#22c55e", "low": "#71717a"}.get(priority, "#71717a")

                with st.container():
                    col1, col2, col3 = st.columns([4, 1, 1])
                    with col1:
                        st.markdown(f"□ **{h_id}**: {statement}...")
                    with col2:
                        priority_html = f'<span style="color: {priority_color}; font-size: 0.7rem;">{priority_label}</span>'
                        st.markdown(priority_html, unsafe_allow_html=True)
                    with col3:
                        verify_cmd = f"-aop run 验证假设 {h_id}"
                        if st.button("☑️", key=f"select_pending_{h_id}", help=f"复制: {verify_cmd}"):
                            if verify_cmd not in st.session_state._selected_cmds:
                                st.session_state._selected_cmds.append(verify_cmd)
                            st.toast("已添加到选择篮", icon="✅")
                st.markdown("---")

    # === 4. ✅ 已验证假设 ===
    st.markdown("""<div class="glass-card"><div class="section-title"><span class="icon">✅</span> 已验证假设</div></div>""", unsafe_allow_html=True)

    if not validated_hypotheses:
        st.info("暂无已验证假设")
    else:
        st.caption(f"共 {len(validated_hypotheses)} 个假设已验证")
        for h in validated_hypotheses[:5]:
            h_id = h.get("hypothesis_id", "?")
            statement = h.get("statement", "")[:50]
            st.markdown(f"✓ **{h_id}**: {statement}... (验证成功)")
            st.markdown("---")

    # === 5. 💡 下一步建议 ===
    st.markdown("""<div class="glass-card"><div class="section-title"><span class="icon">💡</span> 下一步建议</div></div>""", unsafe_allow_html=True)

    suggestions = []
    if pending_hypotheses:
        next_h = pending_hypotheses[0]
        suggestions.append(f"1. 验证假设 {next_h.get('hypothesis_id', '?')}（{next_h.get('priority', '中')}优先级）")
    if validated_hypotheses:
        suggestions.append("2. 记录已验证假设的学习经验")
    if not hypotheses_data:
        suggestions.append("创建第一个假设，开始假设驱动开发")

    if suggestions:
        for s in suggestions:
            st.markdown(f"- {s}")

        # 一键复制建议命令
        if pending_hypotheses:
            next_h = pending_hypotheses[0]
            suggest_cmd = f"-aop run 验证假设 {next_h.get('hypothesis_id', '?')}"
            col1, col2 = st.columns([3, 1])
            with col1:
                st.code(suggest_cmd, language="bash")
            with col2:
                if st.button("☑️ 选择", use_container_width=True, key="copy_suggestion"):
                    if suggest_cmd not in st.session_state._selected_cmds:
                        st.session_state._selected_cmds.append(suggest_cmd)
                    st.toast("已添加到选择篮", icon="✅")
        st.success("✅ 所有假设都已验证！考虑创建新的假设。")

    st.markdown("---")

    # === 显示选中的指令 ===
    if st.session_state._selected_cmds:
        st.markdown("""<div class="glass-card"><div class="section-title"><span class="icon">📋</span> 已选指令</div></div>""", unsafe_allow_html=True)
        st.caption(f"已选择 {len(st.session_state._selected_cmds)} 条指令（可自行复制文字）")
        for i, cmd in enumerate(st.session_state._selected_cmds):
            col1, col2 = st.columns([5, 1])
            with col1:
                st.code(cmd, language="bash")
            with col2:
                if st.button("🗑️", key=f"remove_cmd_{i}", help="移除"):
                    st.session_state._selected_cmds.pop(i)
                    st.rerun()
        if st.button("🗑️ 清空全部", key="clear_all_cmds"):
            st.session_state._selected_cmds = []
            st.rerun()

    # === AOP 命令参考（折叠）===
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
    st.markdown("""
    <div class="header-gradient">
        <h1 style="margin: 0; font-size: 1.35rem; color: white; font-weight: 600;">📁 工作区</h1>
        <p style="margin: 0.2rem 0 0 0; color: rgba(255,255,255,0.75); font-size: 0.75rem;">项目空间管理</p>
    </div>
    """, unsafe_allow_html=True)

    wm = st.session_state.workspace_manager
    sm = st.session_state.settings_manager
    primary_agent = sm.get_primary_agent()

    # 创建新工作区
    with st.expander("➕ 创建新工作区", expanded=False):
        st.markdown("""<div style="margin-bottom: 0.5rem;"></div>""", unsafe_allow_html=True)
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
    st.markdown("""<div class="section-title"><span class="icon">📋</span> 我的工作区</div>""", unsafe_allow_html=True)
    workspaces = wm.list_workspaces()

    if not workspaces:
        st.info("还没有工作区，创建一个开始使用！")
    else:
        for ws in workspaces:
            with st.container():
                col1, col2, col3, col4, col5 = st.columns([3, 2, 1, 1, 1])

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
                    if st.button("💾", key=f"session_{ws.id}", help="会话管理"):
                        st.session_state[f"show_session_dialog_{ws.id}"] = True

                with col5:
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

                # 会话管理对话框
                if st.session_state.get(f"show_session_dialog_{ws.id}", False):
                    with st.container(border=True):
                        st.markdown(f"**💾 会话管理 - {ws.name}**")
                        st.markdown("---")
                        
                        # Claude Code 会话
                        st.markdown("**Claude Code 会话 ID**")
                        claude_session = st.text_input(
                            "claude_session",
                            value=ws.metadata.get("claude_session_id", ""),
                            placeholder="xxxx-xxxx-xxxx-xxxx",
                            label_visibility="collapsed",
                            key=f"claude_session_input_{ws.id}"
                        )
                        
                        # OpenCode 会话
                        st.markdown("**OpenCode 会话 ID**")
                        opencode_session = st.text_input(
                            "opencode_session",
                            value=ws.metadata.get("opencode_session_id", ""),
                            placeholder="ses_xxxx",
                            label_visibility="collapsed",
                            key=f"opencode_session_input_{ws.id}"
                        )
                        
                        st.markdown("---")
                        st.caption("💡 查看会话 ID：在 CLI 窗口输入 `/q` 回车即可显示")
                        
                        # 保存按钮
                        col_save, col_close = st.columns(2)
                        with col_save:
                            if st.button("💾 保存", key=f"save_session_{ws.id}", use_container_width=True):
                                # 提取纯会话 ID（处理用户输入 ccr code --resume xxx 的情况）
                                import re
                                claude_id = claude_session.strip()
                                opencode_id = opencode_session.strip()
                                
                                # 从 ccr code --resume xxx 格式中提取 ID
                                claude_match = re.search(r'([a-f0-9-]{36})', claude_id)
                                if claude_match:
                                    claude_id = claude_match.group(1)
                                
                                # 从 opencode -s xxx 或 ses_xxx 格式中提取 ID
                                opencode_match = re.search(r'(ses_[a-zA-Z0-9]+)', opencode_id)
                                if opencode_match:
                                    opencode_id = opencode_match.group(1)
                                
                                # 更新 workspace metadata
                                ws.metadata["claude_session_id"] = claude_id
                                ws.metadata["opencode_session_id"] = opencode_id
                                # 保存到文件
                                wm.update_workspace(ws)
                                # 更新 session_state 中的 current_workspace
                                if st.session_state.current_workspace and st.session_state.current_workspace.id == ws.id:
                                    st.session_state.current_workspace = ws
                                st.success(f"会话 ID 已保存: {claude_id[:8] if claude_id else 'N/A'}...")
                                st.session_state[f"show_session_dialog_{ws.id}"] = False
                                st.rerun()
                        with col_close:
                            if st.button("关闭", key=f"close_session_{ws.id}", use_container_width=True):
                                st.session_state[f"show_session_dialog_{ws.id}"] = False
                                st.rerun()

                st.markdown("---")


def page_settings():
    """设置页面"""
    st.markdown("""
    <div class="header-gradient">
        <h1 style="margin: 0; font-size: 1.35rem; color: white; font-weight: 600;">⚙️ 设置</h1>
        <p style="margin: 0.2rem 0 0 0; color: rgba(255,255,255,0.75); font-size: 0.75rem;">系统配置与 Agent 管理</p>
    </div>
    """, unsafe_allow_html=True)

    sm = st.session_state.settings_manager

    # 主 Agent 设置
    st.markdown("""<div class="glass-card"><div class="section-title"><span class="icon">🤖</span> 主 Agent 设置</div></div>""", unsafe_allow_html=True)

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

    # 调试日志设置
    st.markdown("""<div class="glass-card"><div class="section-title"><span class="icon">🖥️</span> 调试日志</div></div>""", unsafe_allow_html=True)
    show_dev_console = sm.get_show_dev_console()
    new_show_dev = st.toggle(
        "显示调试日志",
        value=show_dev_console,
        help="开启后侧边栏将显示「调试日志」选项卡",
    )

    if new_show_dev != show_dev_console:
        sm.set_show_dev_console(new_show_dev)
        st.success(f"已{"开启" if new_show_dev else "关闭"}调试日志")
        st.rerun()

    st.markdown("---")

    # Agent 状态
    st.markdown("""<div class="glass-card"><div class="section-title"><span class="icon">📊</span> Agent 状态</div></div>""", unsafe_allow_html=True)
    agents = get_available_agents()

    if not agents:
        st.warning("未检测到可用 Agent")
    else:
        for agent in agents:
            st.success(f"✅ {agent.name} - {agent.description}")

    # 安装指南
    st.markdown("""<div class="glass-card"><div class="section-title"><span class="icon">📖</span> 安装指南</div></div>""", unsafe_allow_html=True)
    st.code("Claude Code: npm install -g @anthropic-ai/claude-code", language="bash")
    st.code("OpenCode: npm install -g opencode", language="bash")

    # 数据目录
    st.markdown("""<div class="glass-card"><div class="section-title"><span class="icon">📂</span> 数据目录</div></div>""", unsafe_allow_html=True)
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
    st.markdown("""
    <div class="header-gradient">
        <h1 style="margin: 0; font-size: 1.35rem; color: white; font-weight: 600;">📚 项目记忆</h1>
        <p style="margin: 0.2rem 0 0 0; color: rgba(255,255,255,0.75); font-size: 0.75rem;">跨会话知识持久化</p>
    </div>
    """, unsafe_allow_html=True)

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
        st.markdown("""<div class="glass-card"><div class="section-title"><span class="icon">📄</span> 所有记忆文件</div></div>""", unsafe_allow_html=True)

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
                col1, col2, col3, col4, col5 = st.columns([3, 2, 1, 1, 1])

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
    from datetime import datetime  # 修复局部变量问题
    """开发者控制台页面"""
    st.markdown("""
    <div class="header-gradient">
        <h1 style="margin: 0; font-size: 1.35rem; color: white; font-weight: 600;">🖥️ 调试日志</h1>
        <p style="margin: 0.2rem 0 0 0; color: rgba(255,255,255,0.75); font-size: 0.75rem;">系统运行日志</p>
    </div>
    """, unsafe_allow_html=True)

    logger = get_dashboard_logger()

    # 获取当前工作区
    workspace_id = None
    if 'current_workspace' in st.session_state and st.session_state.current_workspace:
        workspace_id = st.session_state.current_workspace.id

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
        if st.button("☑️ 选择", use_container_width=True, key="copy_logs_btn"):
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



    # ========== 会话管理 ==========
    st.markdown("---")
    st.subheader("💾 会话管理")
    
    # 获取当前项目的会话
    if workspace_id:
        try:
            sm = get_session_manager()
            sessions = sm.list_sessions(workspace_id)
            
            if sessions:
                st.write(f"**已保存的会话 ({len(sessions)})**")
                
                for session in sessions[:5]:  # 显示最近 5 个
                    with st.expander(f"{'🟢' if session.status == 'active' else '📦'} {session.session_id[:8]}... ({session.provider})"):
                        st.write(f"**Provider:** {session.provider}")
                        st.write(f"**创建时间:** {session.created_at[:10]}")
                        st.write(f"**最后使用:** {session.last_used[:10]}")
                        st.write(f"**消息数:** {session.message_count}")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("📋 复制 ID", key=f"copy_{session.session_id}"):
                                st.code(session.session_id, language=None)
                        with col2:
                            if st.button("🗑️ 归档", key=f"archive_{session.session_id}"):
                                sm.archive_session(workspace_id, session.session_id)
                                st.success("已归档")
                                st.rerun()
            else:
                st.info("暂无保存的会话")
        except Exception as e:
            st.error(f"加载会话失败: {e}")
    
    # 手动添加会话 ID
    st.write("**手动添加会话 ID**")
    st.caption("从 CLI 输出中复制会话 ID 粘贴到这里")
    
    new_session_id = st.text_input(
        "会话 ID",
        placeholder="xxxx-xxxx-xxxx-xxxx",
        key="manual_session_id_input"
    )
    
    provider_choice = st.selectbox(
        "Provider",
        ["claude", "opencode"],
        key="manual_provider_choice"
    )
    
    if st.button("💾 保存会话", key="save_manual_session"):
        if new_session_id and workspace_id:
            try:
                sm = get_session_manager()
                from aop.session import SessionInfo
                from datetime import datetime
                
                now = datetime.now().isoformat()
                session = SessionInfo(
                    session_id=new_session_id,
                    provider=provider_choice,
                    project_id=workspace_id,
                    workspace=project_path,
                    created_at=now,
                    last_used=now,
                    message_count=0,
                    status="active"
                )
                
                sessions = sm.load_sessions(workspace_id)
                sessions[new_session_id] = session
                sm.save_sessions(workspace_id, sessions)
                
                st.success(f"会话已保存: {new_session_id[:8]}...")
                st.rerun()
            except Exception as e:
                st.error(f"保存失败: {e}")
        else:
            st.warning("请输入会话 ID")


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
    elif page == "🖥️ 调试日志":
        page_dev_console()


if __name__ == "__main__":
    main()












