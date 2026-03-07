"""OpenCode implementation of PrimaryAgent with streaming support.

Uses the `opencode` CLI to interact with OpenCode.
"""

from __future__ import annotations

import asyncio
import platform
import subprocess
import shutil
from pathlib import Path
from typing import Optional, AsyncIterator, Callable

from .base import AgentContext, PrimaryAgent
from .memory_extractor import extract_and_save_memory


NPM_GLOBAL_PATHS = [
    Path.home() / "AppData" / "Roaming" / "npm",
    Path.home() / ".npm-global" / "bin",
    Path("/usr/local/bin"),
    Path("/usr/bin"),
]


def _find_binary(binary_name: str) -> Optional[str]:
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


class OpenCodeAgent(PrimaryAgent):
    """PrimaryAgent implementation using OpenCode CLI with streaming support."""

    id = "opencode"
    name = "OpenCode"
    description = "OpenCode CLI agent"

    def __init__(self) -> None:
        self._session_id: Optional[str] = None
        self._opencode_dir = Path.home() / ".opencode"
        self._binary_path: Optional[str] = None

    def is_available(self) -> bool:
        self._binary_path = _find_binary("opencode")
        return self._binary_path is not None

    async def chat(
        self,
        message: str,
        context: AgentContext,
        stream: bool = True,
    ) -> str:
        context_str = _load_context_files(context.workspace_path)
        if context_str:
            message = f"【项目上下文】\n{context_str}\n\n【用户消息】\n{message}"

        binary = self._binary_path or _find_binary("opencode") or "opencode"
        cmd = [binary, "run", message]

        if self._session_id:
            cmd.extend(["-s", self._session_id])
        elif context.session_id:
            cmd.extend(["-s", context.session_id])

        try:
            result = subprocess.run(
                cmd,
                cwd=str(context.workspace_path),
                capture_output=True,
                text=True,
                timeout=300,
            )

            output = result.stdout

            if result.returncode != 0:
                error_msg = result.stderr.strip() or f"Exit code: {result.returncode}"
                raise RuntimeError(f"OpenCode error: {error_msg}")

        except subprocess.TimeoutExpired:
            raise RuntimeError("OpenCode command timed out after 5 minutes")

        self._update_session_id()

        try:
            original_message = message
            if "【用户消息】" in message:
                original_message = message.split("【用户消息】\n")[-1]
            extract_and_save_memory(original_message, output, context.workspace_path)
        except Exception:
            pass

        return output

    async def chat_stream(
        self,
        message: str,
        context: AgentContext,
        on_token: Optional[Callable[[str], None]] = None,
    ) -> AsyncIterator[str]:
        context_str = _load_context_files(context.workspace_path)
        if context_str:
            message = f"【项目上下文】\n{context_str}\n\n【用户消息】\n{message}"

        binary = self._binary_path or _find_binary("opencode") or "opencode"
        cmd = [binary, "run", message]

        if self._session_id:
            cmd.extend(["-s", self._session_id])
        elif context.session_id:
            cmd.extend(["-s", context.session_id])

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(context.workspace_path),
        )

        full_response = []
        
        try:
            while True:
                chunk = await process.stdout.read(1024)
                if not chunk:
                    break
                
                text = chunk.decode('utf-8', errors='replace')
                full_response.append(text)
                
                if on_token:
                    on_token(text)
                
                yield text

            returncode = await process.wait()
            
            if returncode != 0:
                stderr = await process.stderr.read()
                error_msg = stderr.decode('utf-8', errors='replace').strip()
                raise RuntimeError(f"OpenCode error: {error_msg or returncode}")

        except asyncio.CancelledError:
            process.kill()
            raise

        self._update_session_id()

        try:
            complete_response = ''.join(full_response)
            original_message = message
            if "【用户消息】" in message:
                original_message = message.split("【用户消息】\n")[-1]
            extract_and_save_memory(original_message, complete_response, context.workspace_path)
        except Exception:
            pass

    def _update_session_id(self) -> None:
        if not self._opencode_dir.exists():
            return

        try:
            session_files = list(self._opencode_dir.glob("**/session*.json"))
            if session_files:
                latest = max(session_files, key=lambda p: p.stat().st_mtime)
                self._session_id = latest.stem
        except Exception:
            pass

    def get_session_id(self) -> Optional[str]:
        return self._session_id

    def resume_session(self, session_id: str) -> bool:
        self._session_id = session_id
        return True

    def clear_session(self) -> None:
        self._session_id = None
