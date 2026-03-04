"""
AOP Dashboard - 对话式界面

Run with: streamlit run app.py
Or: aop dashboard
"""

import streamlit as st
from pathlib import Path
import json
import sys
import os

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from aop.core.adapter import get_adapter_registry
from aop.workflow.hypothesis import HypothesisManager
from aop.workflow.learning import LearningLog

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
    .chat-container {
        max-width: 900px;
        margin: 0 auto;
    }
    .quick-btn {
        min-width: 120px;
    }
    .status-badge {
        display: inline-block;
        padding: 0.25rem 0.5rem;
        border-radius: 0.25rem;
        font-size: 0.875rem;
        margin: 0.25rem;
    }
    .status-ok { background: #d4edda; color: #155724; }
    .status-error { background: #f8d7da; color: #721c24; }
    .stChatMessage {
        padding: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Data paths
AOP_DIR = Path.home() / ".aop"
DATA_DIR = AOP_DIR / "data"
HYPOTHESES_FILE = DATA_DIR / "hypotheses.json"
LEARNINGS_FILE = DATA_DIR / "learnings.json"
TASKS_DIR = DATA_DIR / "tasks"
CHAT_HISTORY_FILE = DATA_DIR / "chat_history.json"

# Ensure dirs exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
TASKS_DIR.mkdir(parents=True, exist_ok=True)


@st.cache_data(ttl=60)
def get_provider_status():
    """Get status of all providers with caching (60s TTL)."""
    registry = get_adapter_registry()
    providers = ["claude", "codex", "gemini", "qwen", "opencode"]
    results = {}
    for pid in providers:
        adapter = registry.get(pid)
        if adapter:
            results[pid] = adapter.detect()
        else:
            from aop.core.types.contracts import ProviderPresence
            results[pid] = ProviderPresence(
                provider=pid,
                detected=False,
                binary_path=None,
                version=None,
                auth_ok=False,
                reason="not_registered"
            )
    return results


def load_hypotheses():
    """Load hypotheses from file."""
    if HYPOTHESES_FILE.exists():
        with open(HYPOTHESES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def load_learnings():
    """Load learnings from file."""
    if LEARNINGS_FILE.exists():
        with open(LEARNINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def load_tasks():
    """Load task history."""
    tasks = []
    for task_file in TASKS_DIR.glob("*.json"):
        with open(task_file, "r", encoding="utf-8") as f:
            tasks.append(json.load(f))
    return sorted(tasks, key=lambda x: x.get("timestamp", ""), reverse=True)


def load_chat_history():
    """Load chat history from file."""
    if CHAT_HISTORY_FILE.exists():
        with open(CHAT_HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_chat_history(history):
    """Save chat history to file."""
    with open(CHAT_HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def get_llm_client():
    """Check if Claude CLI is available."""
    import shutil
    return shutil.which("claude") is not None


def chat_with_streaming(messages: list, placeholder):
    """Execute chat using Claude CLI (subprocess)."""
    import subprocess
    import shutil
    
    # Build prompt from messages
    prompt_parts = []
    for m in messages:
        role = "用户" if m["role"] == "user" else "助手"
        prompt_parts.append(f"{role}: {m['content']}")
    
    full_prompt = "\n\n".join(prompt_parts)
    
    # Add system instruction
    system_instruction = """你是 AOP (Agent Orchestration Platform) 的助手。
你可以帮助用户：
- 进行代码审查和分析
- 创建和验证假设
- 查看项目状态
- 回答关于 AOP 使用的问题

请用简洁、专业的中文回答。如果用户要求执行代码审查，建议使用 aop review 命令。"""
    
    final_prompt = f"{system_instruction}\n\n{full_prompt}\n\n助手:"
    
    try:
        # Resolve claude binary path on Windows
        claude_bin = shutil.which("claude")
        if not claude_bin:
            placeholder.error("Claude CLI 未安装或未认证。请运行: claude auth login")
            return None
        
        # Run Claude CLI
        result = subprocess.run(
            [claude_bin, "-p", "--permission-mode", "plan", "--output-format", "text", final_prompt],
            capture_output=True,
            text=True,
            timeout=120,
        )
        
        if result.returncode != 0:
            # Check if it's just a permission issue
            if "permission" in result.stderr.lower():
                placeholder.warning("Claude 需要权限确认。请尝试在终端运行一次: claude -p 'hello'")
                return None
            placeholder.error(f"Claude 错误: {result.stderr[:200]}")
            return None
        
        response = result.stdout.strip()
        placeholder.markdown(response)
        return response
        
    except subprocess.TimeoutExpired:
        placeholder.error("请求超时。请稍后重试。")
        return None
    except Exception as e:
        placeholder.error(f"错误: {str(e)}")
        return None


# Initialize session state
if "chat_history" not in st.session_state:
    st.session_state.chat_history = load_chat_history()
if "messages" not in st.session_state:
    st.session_state.messages = []

# Sidebar
st.sidebar.title("🤖 AOP")
page = st.sidebar.radio(
    "导航",
    ["💬 首页", "📜 历史", "⚙️ 设置"],
    label_visibility="collapsed",
)

# ============ PAGES ============

if page == "💬 首页":
    # Header with status
    col_title, col_status = st.columns([3, 2])

    with col_title:
        st.title("AOP Assistant")

    with col_status:
        providers = get_provider_status()
        claude_status = providers.get("claude")
        if claude_status and claude_status.detected and claude_status.auth_ok:
            st.markdown('<span class="status-badge status-ok">✅ Claude Ready</span>', unsafe_allow_html=True)
        else:
            st.markdown('<span class="status-badge status-error">❌ Claude Not Ready</span>', unsafe_allow_html=True)

    st.markdown("---")

    # Chat container
    chat_container = st.container()

    with chat_container:
        # Display chat messages
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        # Chat input
        if prompt := st.chat_input("输入你的问题..."):
            # Add user message
            st.session_state.messages.append({"role": "user", "content": prompt})

            with st.chat_message("user"):
                st.markdown(prompt)

            # Get AI response
            with st.chat_message("assistant"):
                placeholder = st.empty()

                response = chat_with_streaming(
                    st.session_state.messages,
                    placeholder
                )

                if response:
                    st.session_state.messages.append({"role": "assistant", "content": response})
                    # Save to history
                    st.session_state.chat_history.append({
                        "role": "user",
                        "content": prompt,
                        "timestamp": str(Path(__file__).stat().st_mtime)
                    })
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": response,
                        "timestamp": str(Path(__file__).stat().st_mtime)
                    })
                    save_chat_history(st.session_state.chat_history)

    # Quick action buttons at bottom
    st.markdown("---")
    st.markdown("**快捷指令**")

    col1, col2, col3, col4 = st.columns(4)

    quick_prompts = {
        "代码审查": "请帮我审查当前项目的代码，找出潜在问题和改进建议。",
        "创建假设": "请帮我创建一个关于项目优化的假设，使用假设驱动开发方法。",
        "查看状态": "请总结当前 AOP 的状态，包括可用的 Provider、任务历史等。",
        "学习建议": "基于之前的执行记录，给我一些学习和改进建议。"
    }

    with col1:
        if st.button("🔍 代码审查", key="btn_review", use_container_width=True):
            st.session_state.messages.append({"role": "user", "content": quick_prompts["代码审查"]})
            st.rerun()

    with col2:
        if st.button("💡 创建假设", key="btn_hypothesis", use_container_width=True):
            st.session_state.messages.append({"role": "user", "content": quick_prompts["创建假设"]})
            st.rerun()

    with col3:
        if st.button("📊 查看状态", key="btn_status", use_container_width=True):
            st.session_state.messages.append({"role": "user", "content": quick_prompts["查看状态"]})
            st.rerun()

    with col4:
        if st.button("📚 学习建议", key="btn_learning", use_container_width=True):
            st.session_state.messages.append({"role": "user", "content": quick_prompts["学习建议"]})
            st.rerun()

    # Status summary in expander
    with st.expander("📊 系统状态概览", expanded=False):
        providers = get_provider_status()
        available_count = sum(1 for p in providers.values() if p.detected)

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("可用 Provider", f"{available_count} / {len(providers)}")

        with col2:
            hypotheses = load_hypotheses()
            pending = sum(1 for h in hypotheses if h.get("state") == "pending")
            st.metric("待验证假设", pending)

        with col3:
            learnings = load_learnings()
            st.metric("学习记录", len(learnings))

        with col4:
            tasks = load_tasks()
            st.metric("执行任务", len(tasks))

        # Provider status
        st.markdown("**Provider 状态**")
        cols = st.columns(len(providers))
        for i, (pid, presence) in enumerate(providers.items()):
            with cols[i]:
                if presence.detected:
                    if presence.auth_ok:
                        st.success(f"✅ {pid.upper()}")
                    else:
                        st.warning(f"⚠️ {pid.upper()}")
                else:
                    st.error(f"❌ {pid.upper()}")


elif page == "📜 历史":
    st.title("📜 历史记录")

    tab1, tab2, tab3, tab4 = st.tabs(["任务历史", "假设管理", "学习记录", "对话历史"])

    with tab1:
        tasks = load_tasks()

        if tasks:
            for task in tasks:
                status_emoji = "✅" if task.get("success") else "❌"
                with st.expander(f"{status_emoji} **{task.get('task_id', 'Unknown')}** - {task.get('timestamp', '')}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown(f"**状态**: {task.get('status', 'unknown')}")
                        st.markdown(f"**Provider**: {task.get('provider', '-')}")
                    with col2:
                        st.markdown(f"**耗时**: {task.get('duration', '-')}s")
                        st.markdown(f"**决策**: {task.get('decision', '-')}")

                    if task.get("prompt"):
                        st.markdown(f"**提示词**:\n```\n{task.get('prompt')}\n```")

                    if task.get("output"):
                        st.markdown(f"**输出**:\n{task.get('output')[:500]}...")
        else:
            st.info("还没有执行任务。运行 `aop review` 开始！")
            st.code("aop review -p \"检查这个项目\" -P claude", language="bash")

    with tab2:
        # Create new hypothesis
        with st.expander("➕ 创建新假设", expanded=False):
            statement = st.text_area("假设陈述", placeholder="如果 [想法]，那么 [预期结果]", key="new_hyp_statement")
            validation = st.text_input("验证方法", placeholder="如何验证这个假设？", key="new_hyp_validation")
            priority = st.selectbox("优先级", ["quick_win", "high", "medium", "low"], key="new_hyp_priority")

            if st.button("创建假设", key="create_hyp_btn"):
                if statement:
                    manager = HypothesisManager()
                    h = manager.create(
                        statement=statement,
                        validation_method=validation,
                        priority=priority,
                    )
                    st.success(f"创建成功！ID: {h.hypothesis_id}")
                    st.rerun()
                else:
                    st.error("请输入假设陈述")

        # List hypotheses
        hypotheses = load_hypotheses()

        if hypotheses:
            state_filter = st.selectbox("筛选状态", ["全部", "pending", "validated", "refuted", "inconclusive"], key="hyp_filter")

            for h in hypotheses:
                if state_filter != "全部" and h.get("state") != state_filter:
                    continue

                state_colors = {
                    "pending": "🟡",
                    "validated": "🟢",
                    "refuted": "🔴",
                    "inconclusive": "⚪",
                }

                with st.container():
                    col1, col2, col3 = st.columns([1, 5, 2])
                    with col1:
                        st.markdown(f"{state_colors.get(h.get('state'), '⚪')} **{h.get('hypothesis_id', '-')[:8]}**")
                    with col2:
                        st.write(h.get("statement", "-"))
                    with col3:
                        st.markdown(f"优先级: `{h.get('priority', '-')}`")

                    st.markdown("---")
        else:
            st.info("还没有假设。创建第一个假设开始！")
            st.code('aop hypothesis create "如果添加缓存，响应时间降低 50%"', language="bash")

    with tab3:
        learnings = load_learnings()

        if learnings:
            for i, learning in enumerate(learnings):
                with st.expander(f"📖 **{learning.get('phase', 'Unknown')}** - {learning.get('timestamp', '')}"):
                    col1, col2 = st.columns(2)

                    with col1:
                        st.markdown("#### ✅ 有效的做法")
                        for item in learning.get("what_worked", []):
                            st.markdown(f"- {item}")

                    with col2:
                        st.markdown("#### ❌ 失败的尝试")
                        for item in learning.get("what_failed", []):
                            st.markdown(f"- {item}")

                    st.markdown("#### 💡 关键洞察")
                    for item in learning.get("insights", []):
                        st.markdown(f"- {item}")
        else:
            st.info("还没有学习记录。运行任务后会自动提取学习！")
            st.code("aop learning capture", language="bash")

    with tab4:
        chat_history = load_chat_history()

        if chat_history:
            if st.button("清除对话历史", type="secondary"):
                save_chat_history([])
                st.session_state.messages = []
                st.rerun()

            st.markdown("---")

            for msg in chat_history[-50:]:  # Show last 50 messages
                role_emoji = "👤" if msg.get("role") == "user" else "🤖"
                st.markdown(f"**{role_emoji} {msg.get('role', 'unknown')}**")
                st.markdown(msg.get("content", ""))
                st.markdown("---")
        else:
            st.info("还没有对话历史。在首页开始对话！")


elif page == "⚙️ 设置":
    st.title("⚙️ 设置")

    st.markdown("### 配置文件")

    config_path = AOP_DIR / "config.yaml"
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            config_content = f.read()
        st.code(config_content, language="yaml")
    else:
        st.info("还没有配置文件。运行 `aop init` 创建！")

    st.markdown("### 数据目录")
    st.code(str(DATA_DIR))

    st.markdown("### Provider 状态")
    providers = get_provider_status()

    for pid, presence in providers.items():
        col1, col2, col3 = st.columns([2, 2, 6])

        with col1:
            if presence.detected:
                if presence.auth_ok:
                    st.success(f"✅ **{pid.upper()}**")
                else:
                    st.warning(f"⚠️ **{pid.upper()}**")
            else:
                st.error(f"❌ **{pid.upper()}**")

        with col2:
            if presence.version:
                st.write(f"版本: `{presence.version}`")
            else:
                st.write("版本: -")

        with col3:
            if presence.detected:
                if presence.auth_ok:
                    st.write(f"✅ 已认证 | 路径: `{presence.binary_path}`")
                else:
                    st.write(f"⚠️ 未认证")
            else:
                st.write(f"❌ 未安装")

    st.markdown("### 安装指南")

    install_commands = {
        "claude": "npm install -g @anthropic-ai/claude-code",
        "codex": "npm install -g @openai/codex",
        "gemini": "pip install google-generativeai",
        "qwen": "pip install dashscope",
        "opencode": "npm install -g opencode",
    }

    for provider, cmd in install_commands.items():
        col1, col2 = st.columns([1, 3])
        with col1:
            st.markdown(f"**{provider.upper()}**")
        with col2:
            st.code(cmd, language="bash")

    st.markdown("---")
    st.markdown("### 清除数据")
    if st.button("清除所有数据", type="secondary"):
        import shutil
        if DATA_DIR.exists():
            shutil.rmtree(DATA_DIR)
        st.success("数据已清除！")
        st.rerun()


# Footer
st.sidebar.markdown("---")
st.sidebar.markdown(f"""
**AOP v0.3.0**

[GitHub](https://github.com/xuha233/agent-orchestration-platform)
""")
