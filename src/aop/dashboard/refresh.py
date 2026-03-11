"""
Dashboard 自动刷新组件
"""
import streamlit as st
import streamlit.components.v1 as components
from typing import Optional


def auto_refresh(interval_seconds: int = 30, enabled: bool = True) -> None:
    """
    自动刷新页面
    
    Args:
        interval_seconds: 刷新间隔（秒）
        enabled: 是否启用自动刷新
    """
    if not enabled:
        return
    
    # 使用 JavaScript 定时刷新
    components.html(f"""
        <script>
            setTimeout(function() {{
                window.parent.location.reload();
            }}, {interval_seconds * 1000});
        </script>
    """, height=0)


def render_refresh_controls(
    default_interval: int = 30,
    intervals: list = None,
    key: str = "refresh_interval"
) -> tuple:
    """
    渲染刷新控制组件
    
    Args:
        default_interval: 默认刷新间隔（秒）
        intervals: 可选的刷新间隔列表
        key: session_state key
        
    Returns:
        (interval, auto_refresh_enabled)
    """
    if intervals is None:
        intervals = [10, 30, 60, 120, 300]  # 10秒, 30秒, 1分钟, 2分钟, 5分钟
    
    # 初始化 session state
    if f"{key}_enabled" not in st.session_state:
        st.session_state[f"{key}_enabled"] = True
    if f"{key}_value" not in st.session_state:
        st.session_state[f"{key}_value"] = default_interval
    
    # 渲染控件
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        # 自动刷新开关
        enabled = st.toggle(
            "自动刷新",
            value=st.session_state[f"{key}_enabled"],
            key=f"{key}_toggle"
        )
        st.session_state[f"{key}_enabled"] = enabled
    
    with col2:
        # 刷新间隔选择
        interval = st.select_slider(
            "刷新间隔",
            options=intervals,
            value=st.session_state[f"{key}_value"],
            format_func=lambda x: f"{x}秒" if x < 60 else f"{x // 60}分钟",
            key=f"{key}_slider",
            disabled=not enabled
        )
        st.session_state[f"{key}_value"] = interval
    
    with col3:
        # 手动刷新按钮
        if st.button("🔄 刷新", use_container_width=True):
            st.rerun()
    
    return interval, enabled


def format_interval(seconds: int) -> str:
    """
    格式化时间间隔
    
    Args:
        seconds: 秒数
        
    Returns:
        格式化的字符串
    """
    if seconds < 60:
        return f"{seconds}秒"
    elif seconds < 3600:
        return f"{seconds // 60}分钟"
    else:
        return f"{seconds // 3600}小时"