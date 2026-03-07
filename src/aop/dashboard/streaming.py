"""
AOP Dashboard - 流式输出实现

这个模块提供了流式输出的核心功能：
1. TokenQueue - 线程安全的 token 队列
2. execute_agent_task_streaming - 流式执行 agent 任务
3. render_chat_streaming - 流式渲染聊天界面
"""

import asyncio
import queue
import threading
import time
from pathlib import Path
from typing import Optional, Dict, List, Any, Callable
import re


class TokenQueue:
    """线程安全的 token 队列，用于跨线程传递流式输出"""
    
    def __init__(self):
        self._queue = queue.Queue()
        self._done = threading.Event()
        self._error: Optional[str] = None
    
    def put(self, token: str) -> None:
        """添加一个 token"""
        self._queue.put(token)
    
    def get(self, timeout: float = 0.1) -> Optional[str]:
        """获取一个 token，超时返回 None"""
        try:
            return self._queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def done(self) -> None:
        """标记完成"""
        self._done.set()
    
    def is_done(self) -> bool:
        """检查是否完成"""
        return self._done.is_set()
    
    def set_error(self, error: str) -> None:
        """设置错误"""
        self._error = error
        self._done.set()
    
    def get_error(self) -> Optional[str]:
        """获取错误"""
        return self._error


def execute_agent_task_streaming(
    agent,
    workspace,
    prompt: str,
    session_id: Optional[str],
    workspace_id: str,
    token_queue: TokenQueue,
) -> None:
    """在后台线程中执行 Agent 任务，流式输出到队列

    Args:
        agent: PrimaryAgent 实例
        workspace: 工作区
        prompt: 用户输入
        session_id: 会话 ID
        workspace_id: 工作区 ID
        token_queue: TokenQueue 实例，用于传递流式输出
    """
    try:
        from aop.primary import AgentContext
        
        # 恢复 session
        if session_id:
            agent.resume_session(session_id)
        
        context = AgentContext(
            workspace_path=Path(workspace.project_path),
            session_id=session_id,
        )
        
        # 创建事件循环
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # 定义回调函数
            def on_token(token: str):
                token_queue.put(token)
            
            # 运行流式 chat
            async def run_stream():
                full_response = []
                async for token in agent.chat_stream(prompt, context, on_token=on_token):
                    full_response.append(token)
                return ''.join(full_response)
            
            response = loop.run_until_complete(run_stream())
            
            # 保存 session ID
            if agent.get_session_id():
                # 需要在外部保存
                pass
            
            token_queue.done()
            
        finally:
            loop.close()
            
    except Exception as e:
        import traceback
        token_queue.set_error(f"{str(e)}\n{traceback.format_exc()}")


def render_message_streaming(
    content: str,
    thinking_placeholder=None,
    content_placeholder=None,
    in_thinking: bool = False,
    thinking_content: str = "",
):
    """渲染流式消息，支持思考部分的折叠显示

    Args:
        content: 当前累计的内容
        thinking_placeholder: 思考部分的 placeholder
        content_placeholder: 普通内容的 placeholder
        in_thinking: 是否正在思考部分
        thinking_content: 思考部分的内容

    Returns:
        (in_thinking, thinking_content) 更新后的状态
    """
    import streamlit as st
    
    # 匹配 <thinking> 和 </thinking> 标签
    # 状态机处理
    
    lines = content.split('\n')
    normal_content = []
    thinking_parts = []
    current_thinking = []
    in_thinking_tag = False
    
    for line in lines:
        if '<thinking>' in line:
            in_thinking_tag = True
            # 提取 <thinking> 后面的内容
            after_tag = line.split('<thinking>', 1)[-1]
            if after_tag.strip():
                current_thinking.append(after_tag)
        elif '</thinking>' in line:
            # 提取 </thinking> 前面的内容
            before_tag = line.split('</thinking>', 1)[0]
            if before_tag.strip():
                current_thinking.append(before_tag)
            thinking_parts.append('\n'.join(current_thinking))
            current_thinking = []
            in_thinking_tag = False
        elif in_thinking_tag:
            current_thinking.append(line)
        else:
            normal_content.append(line)
    
    # 如果还在思考标签内
    if current_thinking:
        thinking_parts.append('\n'.join(current_thinking))
    
    # 渲染普通内容
    normal_text = '\n'.join(normal_content)
    if normal_text.strip() and content_placeholder:
        content_placeholder.markdown(normal_text)
    
    # 渲染思考部分（折叠）
    if thinking_parts and thinking_placeholder:
        all_thinking = '\n\n---\n\n'.join(thinking_parts)
        with thinking_placeholder.container():
            with st.expander("🤔 思考过程", expanded=False):
                st.markdown(all_thinking)
    
    return in_thinking_tag, '\n'.join(current_thinking)


def parse_thinking_tags(content: str) -> Dict[str, str]:
    """解析内容中的思考标签

    Returns:
        {
            'normal': 普通内容,
            'thinking': 思考内容（可能为空）
        }
    """
    thinking_pattern = r'<thinking>(.*?)</thinking>'
    matches = re.findall(thinking_pattern, content, flags=re.DOTALL)
    
    # 移除 thinking 标签得到普通内容
    normal = re.sub(thinking_pattern, '', content, flags=re.DOTALL).strip()
    
    return {
        'normal': normal,
        'thinking': '\n\n---\n\n'.join(matches) if matches else ''
    }
