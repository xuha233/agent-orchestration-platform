"""Codex CLI implementation of PrimaryAgent."""

from __future__ import annotations

import subprocess
import threading
import queue
import sys
import shutil
import logging
from pathlib import Path
from typing import Optional, AsyncIterator, Callable, Generator

from .base import AgentContext, PrimaryAgent
from .memory_extractor import extract_and_save_memory

_logger = logging.getLogger(__name__)

# 默认超时时间（秒）
DEFAULT_TIMEOUT = 300


def _find_codex_binary() -> Optional[str]:
    """查找 codex 命令路径"""
    result = shutil.which("codex")
    if result:
        return result

    # Windows: 检查 npm 全局路径
    if sys.platform == "win32":
        npm_path = Path.home() / "AppData" / "Roaming" / "npm"
        # 使用 PATHEXT 环境变量
        import os
        pathext = os.environ.get("PATHEXT", ".COM;.EXE;.BAT;.CMD").split(";")
        for ext in pathext:
            candidate = npm_path / f"codex{ext}"
            if candidate.exists():
                return str(candidate)

    return None


def _load_context_files(workspace_path: Path) -> str:
    """加载项目上下文文件"""
    context_dir = workspace_path / '.aop'
    if not context_dir.exists():
        return ''
    
    context_parts = []
    for filename in ['SOUL.md', 'PROJECT_MEMORY.md', 'WORKFLOW.md', 'TEAM.md']:
        filepath = context_dir / filename
        if filepath.exists():
            try:
                file_content = filepath.read_text(encoding='utf-8')
                context_parts.append(f'=== {filename} ===\n{file_content}\n')
            except Exception:
                pass
    
    return '\n'.join(context_parts)


class CodexAgent(PrimaryAgent):
    """PrimaryAgent implementation using Codex CLI."""

    id = "codex"
    name = "Codex"
    description = "OpenAI Codex CLI agent"

    def __init__(self) -> None:
        self._session_id: Optional[str] = None
        self._binary_path: Optional[str] = None
        self._codex_dir = Path.home() / ".codex" / "sessions"

    def is_available(self) -> bool:
        """检查 Codex CLI 是否可用"""
        self._binary_path = _find_codex_binary()
        return self._binary_path is not None

    async def chat(
        self,
        message: str,
        context: AgentContext,
        stream: bool = True,
    ) -> str:
        """执行聊天命令"""
        context_str = _load_context_files(context.workspace_path)
        if context_str:
            message = f"【项目上下文】\n{context_str}\n\n【用户消息】\n{message}"

        binary = self._binary_path or _find_codex_binary() or "codex"
        
        # 使用 exec 子命令进行非交互式执行
        cmd = [binary, "exec"]
        
        # 会话恢复：优先使用 self._session_id，其次使用 context.session_id
        session_to_use = self._session_id or context.session_id
        if session_to_use:
            cmd.extend(["resume", session_to_use])

        _logger.info(f"[Codex CLI] Binary: {binary}")
        _logger.info(f"[Codex CLI] Command: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                input=message,
                cwd=str(context.workspace_path),
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=DEFAULT_TIMEOUT,
            )

            output = result.stdout
            _logger.info(f"[Codex CLI] Output length: {len(output)}")

            if result.returncode != 0:
                error_msg = result.stderr.strip() or f"Exit code: {result.returncode}"
                _logger.error(f"[Codex CLI] Error: {error_msg}")
                raise RuntimeError(f"Codex error: {error_msg}")

        except subprocess.TimeoutExpired:
            raise RuntimeError(f"Codex command timed out after {DEFAULT_TIMEOUT} seconds")

        # 更新 session ID
        self._update_session_id()

        try:
            original_message = message
            if "【用户消息】" in message:
                original_message = message.split("【用户消息】\n")[-1]
            extract_and_save_memory(original_message, output, context.workspace_path)
        except Exception:
            pass

        return output

    def chat_stream_sync(
        self,
        message: str,
        context: AgentContext,
        on_token: Optional[Callable[[str], None]] = None,
    ) -> Generator[str, None, None]:
        """同步流式执行"""
        context_str = _load_context_files(context.workspace_path)
        if context_str:
            message = f"【项目上下文】\n{context_str}\n\n【用户消息】\n{message}"

        binary = self._binary_path or _find_codex_binary() or "codex"
        
        # 使用 exec 子命令 + JSON 输出
        cmd = [binary, "exec", "--json"]
        
        session_to_use = self._session_id or context.session_id
        if session_to_use:
            cmd.extend(["resume", session_to_use])

        _logger.info(f"[Codex CLI] Binary: {binary}")
        _logger.info(f"[Codex CLI] Command: {' '.join(cmd)}")

        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='replace',
            cwd=str(context.workspace_path),
            bufsize=1,
        )

        # 写入消息到 stdin
        process.stdin.write(message)
        process.stdin.close()

        output_queue = queue.Queue()

        def read_stdout():
            try:
                for line in iter(process.stdout.readline, ''):
                    if line:
                        output_queue.put(('stdout', line))
            except Exception as e:
                output_queue.put(('error', str(e)))
            finally:
                output_queue.put(('done', None))

        def read_stderr():
            try:
                for line in iter(process.stderr.readline, ''):
                    if line:
                        output_queue.put(('stderr', line))
            except Exception:
                pass

        stdout_thread = threading.Thread(target=read_stdout, daemon=True)
        stderr_thread = threading.Thread(target=read_stderr, daemon=True)
        stdout_thread.start()
        stderr_thread.start()

        full_response = []

        try:
            while True:
                try:
                    msg_type, content = output_queue.get(timeout=0.1)

                    if msg_type == 'done':
                        break
                    elif msg_type == 'stdout':
                        full_response.append(content)
                        if on_token:
                            on_token(content)
                        yield content
                    elif msg_type == 'stderr':
                        _logger.warning(f"[Codex CLI] stderr: {content}")
                    elif msg_type == 'error':
                        raise RuntimeError(content)

                except queue.Empty:
                    if process.poll() is not None:
                        break
                    continue

        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()

        if process.returncode != 0:
            stderr_output = process.stderr.read()
            raise RuntimeError(f"Codex error: {stderr_output or process.returncode}")

        # 更新 session ID
        self._update_session_id()

        try:
            complete_response = ''.join(full_response)
            original_message = message
            if "【用户消息】" in message:
                original_message = message.split("【用户消息】\n")[-1]
            extract_and_save_memory(original_message, complete_response, context.workspace_path)
        except Exception:
            pass

    async def chat_stream(
        self,
        message: str,
        context: AgentContext,
        on_token: Optional[Callable[[str], None]] = None,
    ) -> AsyncIterator[str]:
        """异步流式执行"""
        for token in self.chat_stream_sync(message, context, on_token):
            yield token

    def _update_session_id(self) -> None:
        """更新 session ID（从 Codex session 目录读取最新的）"""
        if not self._codex_dir.exists():
            return

        try:
            session_files = list(self._codex_dir.glob("**/*.json"))
            if session_files:
                latest = max(session_files, key=lambda p: p.stat().st_mtime)
                # 提取 session ID（可能是文件名或目录名）
                self._session_id = latest.stem
                _logger.info(f"[Codex CLI] Updated session ID: {self._session_id}")
        except Exception as e:
            _logger.warning(f"[Codex CLI] Failed to update session ID: {e}")

    def get_session_id(self) -> Optional[str]:
        """获取当前 session ID"""
        return self._session_id

    def resume_session(self, session_id: str) -> bool:
        """恢复指定 session"""
        self._session_id = session_id
        return True

    def clear_session(self) -> None:
        """清除当前 session"""
        self._session_id = None
