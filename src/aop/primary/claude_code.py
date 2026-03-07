"""Claude Code implementation of PrimaryAgent with streaming support.

Uses the `claude` CLI to interact with Claude Code.
"""

from __future__ import annotations

import subprocess
import threading
import queue
import platform
import shutil
from pathlib import Path
from typing import Optional, AsyncIterator, Callable, Generator

from .base import AgentContext, PrimaryAgent
from .memory_extractor import extract_and_save_memory


# Windows 上常见的 npm 全局安装路径
NPM_GLOBAL_PATHS = [
    Path.home() / "AppData" / "Roaming" / "npm",
    Path.home() / ".npm-global" / "bin",
    Path("/usr/local/bin"),
    Path("/usr/bin"),
]


def _find_binary(binary_name: str) -> Optional[str]:
    """
    查找 CLI 二进制文件，支持 Windows 的 .cmd/.bat 扩展名
    """
    result = shutil.which(binary_name)
    if result:
        return result

    if platform.system() == "Windows":
        import os
        pathext = os.environ.get("PATHEXT", ".COM;.EXE;.BAT;.CMD").split(";")

        for npm_path in NPM_GLOBAL_PATHS:
            if not npm_path.exists():
                continue
            for ext in pathext:
                candidate = npm_path / f"{binary_name}{ext}"
                if candidate.exists():
                    return str(candidate)

        for npm_path in NPM_GLOBAL_PATHS:
            if not npm_path.exists():
                continue
            candidate = npm_path / f"{binary_name}.cmd"
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


class ClaudeCodeAgent(PrimaryAgent):
    """PrimaryAgent implementation using Claude Code CLI with streaming support."""

    id = "claude_code"
    name = "Claude Code"
    description = "Anthropic's Claude Code CLI agent"

    def __init__(self) -> None:
        self._session_id: Optional[str] = None
        self._claude_projects_dir = Path.home() / ".claude" / "projects"
        self._binary_path: Optional[str] = None

    def is_available(self) -> bool:
        self._binary_path = _find_binary("claude")
        return self._binary_path is not None

    async def chat(
        self,
        message: str,
        context: AgentContext,
        stream: bool = True,
    ) -> str:
        """Chat with Claude Code."""
        context_str = _load_context_files(context.workspace_path)
        if context_str:
            message = f"【项目上下文】\n{context_str}\n\n【用户消息】\n{message}"

        binary = self._binary_path or _find_binary("claude") or "claude"
        cmd = [binary, "-p", message, "--dangerously-skip-permissions"]
        
        # Session 隔离策略：
        # 1. 如果有 session_id（工作区专属），使用 --session-id 确保独立
        # 2. 否则使用 --no-session-persistence 禁用持久化（每次新对话）
        if self._session_id:
            # 使用 UUID 格式的 session-id
            import uuid
            try:
                # 验证是否为有效 UUID
                uuid.UUID(self._session_id)
                cmd.extend(["--session-id", self._session_id])
            except ValueError:
                # 如果不是 UUID，使用 --no-session-persistence
                cmd.append("--no-session-persistence")
        elif context.session_id:
            # 使用上下文中的 session
            import uuid
            try:
                uuid.UUID(context.session_id)
                cmd.extend(["--session-id", context.session_id])
            except ValueError:
                cmd.append("--no-session-persistence")
        else:
            # 新对话，禁用持久化避免跨工作区污染
            cmd.append("--no-session-persistence")

        try:
            result = subprocess.run(
                cmd,
                cwd=str(context.workspace_path),
                capture_output=True,
                text=True,
                timeout=300,
            )

            output = result.stdout
            stderr_output = result.stderr

            if result.returncode != 0:
                error_msg = stderr_output.strip() or f"Exit code: {result.returncode}"
                raise RuntimeError(f"Claude Code error: {error_msg}")

            if not output.strip() and stderr_output.strip():
                raise RuntimeError(f"Claude Code stderr: {stderr_output.strip()}")

        except subprocess.TimeoutExpired:
            raise RuntimeError("Claude Code command timed out after 5 minutes")

        self._update_session_id(context.workspace_path)

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
        """同步流式执行，兼容 Windows
        
        使用 subprocess.Popen + 线程读取 stdout 实现
        """
        context_str = _load_context_files(context.workspace_path)
        if context_str:
            message = f"【项目上下文】\n{context_str}\n\n【用户消息】\n{message}"

        binary = self._binary_path or _find_binary("claude") or "claude"
        cmd = [binary, "-p", message, "--dangerously-skip-permissions"]
        
        # Session 隔离策略：
        # 1. 如果有 session_id（工作区专属），使用 --session-id 确保独立
        # 2. 否则使用 --no-session-persistence 禁用持久化（每次新对话）
        if self._session_id:
            # 使用 UUID 格式的 session-id
            import uuid
            try:
                # 验证是否为有效 UUID
                uuid.UUID(self._session_id)
                cmd.extend(["--session-id", self._session_id])
            except ValueError:
                # 如果不是 UUID，使用 --no-session-persistence
                cmd.append("--no-session-persistence")
        elif context.session_id:
            # 使用上下文中的 session
            import uuid
            try:
                uuid.UUID(context.session_id)
                cmd.extend(["--session-id", context.session_id])
            except ValueError:
                cmd.append("--no-session-persistence")
        else:
            # 新对话，禁用持久化避免跨工作区污染
            cmd.append("--no-session-persistence")

        # 使用 Popen 启动进程
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='replace',
            cwd=str(context.workspace_path),
            bufsize=1,  # 行缓冲
        )

        # 使用队列传递输出
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

        # 启动读取线程
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
                        pass
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

        # 检查返回码
        if process.returncode != 0:
            stderr_output = process.stderr.read()
            raise RuntimeError(f"Claude Code error: {stderr_output or process.returncode}")

        # 更新 session
        self._update_session_id(context.workspace_path)

        # 提取记忆
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
        """异步流式执行 - 通过调用同步方法实现"""
        for token in self.chat_stream_sync(message, context, on_token):
            yield token

    def _update_session_id(self, workspace_path: Path) -> None:
        if not self._claude_projects_dir.exists():
            return

        try:
            path_str = str(workspace_path.absolute())
            for project_dir in self._claude_projects_dir.iterdir():
                if project_dir.is_dir():
                    if path_str.replace("\\", "/").replace(":", "") in project_dir.name.replace("-", ""):
                        session_files = list(project_dir.glob("*.json"))
                        if session_files:
                            latest = max(session_files, key=lambda p: p.stat().st_mtime)
                            self._session_id = latest.stem
                            return
        except Exception:
            pass

    def get_session_id(self) -> Optional[str]:
        return self._session_id

    def resume_session(self, session_id: str) -> bool:
        self._session_id = session_id
        return True

    def clear_session(self) -> None:
        self._session_id = None
