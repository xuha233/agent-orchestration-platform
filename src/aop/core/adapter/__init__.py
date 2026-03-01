"""Provider adapters."""

from __future__ import annotations

import shutil
import subprocess
import time
from dataclasses import dataclass
from typing import List, Optional, Protocol, runtime_checkable

from ..types import ProviderId, TaskInput, TaskResult, NormalizedFinding
from .parsers import get_parser


@dataclass
class ProviderPresence:
    provider: ProviderId
    detected: bool
    binary_path: Optional[str] = None
    version: Optional[str] = None
    auth_ok: bool = False


@runtime_checkable
class ProviderAdapter(Protocol):
    """Protocol for provider adapters."""
    
    @property
    def id(self) -> ProviderId: ...
    
    def detect(self) -> ProviderPresence: ...
    def run(self, task: TaskInput) -> TaskResult: ...


class BaseAdapter:
    """Base class for provider adapters."""
    
    def __init__(self, provider_id: ProviderId, binary_name: str):
        self._id = provider_id
        self._binary_name = binary_name
    
    @property
    def id(self) -> ProviderId:
        return self._id
    
    def detect(self) -> ProviderPresence:
        """Detect if provider is installed and available."""
        binary_path = shutil.which(self._binary_name)
        if not binary_path:
            return ProviderPresence(provider=self._id, detected=False)
        return ProviderPresence(provider=self._id, detected=True, binary_path=binary_path)
    
    def _parse_findings(self, output: str) -> List[NormalizedFinding]:
        """Parse output into normalized findings."""
        parser = get_parser(self._id)
        return parser.parse(output)
    
    def run(self, task: TaskInput) -> TaskResult:
        """Run a task using this provider."""
        start = time.time()
        try:
            result = subprocess.run(
                [self._binary_name, "--print", task.prompt],
                capture_output=True, 
                text=True, 
                timeout=task.timeout_seconds, 
                cwd=task.repo_root
            )
            output = result.stdout
            findings = self._parse_findings(output) if result.returncode == 0 else []
            return TaskResult(
                task_id=task.task_id,
                provider=self._id,
                success=result.returncode == 0,
                output=output,
                findings=findings,
                error=result.stderr if result.returncode else None,
                duration_seconds=time.time() - start
            )
        except subprocess.TimeoutExpired:
            return TaskResult(
                task_id=task.task_id,
                provider=self._id,
                success=False,
                error=f"Timeout after {task.timeout_seconds} seconds",
                duration_seconds=task.timeout_seconds
            )
        except Exception as e:
            return TaskResult(
                task_id=task.task_id,
                provider=self._id,
                success=False,
                error=str(e),
                duration_seconds=time.time() - start
            )

class ClaudeAdapter(BaseAdapter):
    """Adapter for Anthropic Claude CLI."""
    
    def __init__(self):
        super().__init__("claude", "claude")
    
    def detect(self) -> ProviderPresence:
        presence = super().detect()
        if presence.detected:
            try:
                result = subprocess.run(
                    ["claude", "--version"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    presence.version = result.stdout.strip()
            except Exception:
                pass
        return presence


class CodexAdapter(BaseAdapter):
    """Adapter for OpenAI Codex CLI."""
    
    def __init__(self):
        super().__init__("codex", "codex")


class GeminiAdapter(BaseAdapter):
    """Adapter for Google Gemini CLI.
    
    Supports Gemini models via the gemini-cli or gcloud ai tool.
    """
    
    def __init__(self):
        super().__init__("gemini", "gemini")
    
    def detect(self) -> ProviderPresence:
        binary_path = shutil.which("gemini")
        if binary_path:
            return ProviderPresence(
                provider=self._id,
                detected=True,
                binary_path=binary_path
            )
        
        gcloud_path = shutil.which("gcloud")
        if gcloud_path:
            try:
                result = subprocess.run(
                    ["gcloud", "ai", "--help"],
                    capture_output=True,
                    timeout=5
                )
                if result.returncode == 0:
                    return ProviderPresence(
                        provider=self._id,
                        detected=True,
                        binary_path=gcloud_path
                    )
            except Exception:
                pass
        
        return ProviderPresence(provider=self._id, detected=False)
    
    def run(self, task: TaskInput) -> TaskResult:
        start = time.time()
        use_gcloud = shutil.which("gemini") is None
        
        try:
            if use_gcloud:
                cmd = ["gcloud", "ai", "generate", task.prompt]
            else:
                cmd = ["gemini", "--print", task.prompt]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=task.timeout_seconds,
                cwd=task.repo_root
            )
            
            output = result.stdout
            findings = self._parse_findings(output) if result.returncode == 0 else []
            
            return TaskResult(
                task_id=task.task_id,
                provider=self._id,
                success=result.returncode == 0,
                output=output,
                findings=findings,
                error=result.stderr if result.returncode else None,
                duration_seconds=time.time() - start
            )
        except subprocess.TimeoutExpired:
            return TaskResult(
                task_id=task.task_id,
                provider=self._id,
                success=False,
                error=f"Timeout after {task.timeout_seconds} seconds",
                duration_seconds=task.timeout_seconds
            )
        except Exception as e:
            return TaskResult(
                task_id=task.task_id,
                provider=self._id,
                success=False,
                error=str(e),
                duration_seconds=time.time() - start
            )

class OpenCodeAdapter(BaseAdapter):
    """Adapter for OpenCode CLI.
    
    OpenCode is a unified interface for multiple AI code assistants.
    """
    
    def __init__(self):
        super().__init__("opencode", "opencode")
    
    def detect(self) -> ProviderPresence:
        presence = super().detect()
        if presence.detected:
            try:
                result = subprocess.run(
                    ["opencode", "--version"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    presence.version = result.stdout.strip().split('\n')[0]
            except Exception:
                pass
        return presence
    
    def run(self, task: TaskInput) -> TaskResult:
        start = time.time()
        
        try:
            result = subprocess.run(
                ["opencode", "ask", task.prompt, "--no-interactive"],
                capture_output=True,
                text=True,
                timeout=task.timeout_seconds,
                cwd=task.repo_root
            )
            
            output = result.stdout
            findings = self._parse_findings(output) if result.returncode == 0 else []
            
            return TaskResult(
                task_id=task.task_id,
                provider=self._id,
                success=result.returncode == 0,
                output=output,
                findings=findings,
                error=result.stderr if result.returncode else None,
                duration_seconds=time.time() - start
            )
        except subprocess.TimeoutExpired:
            return TaskResult(
                task_id=task.task_id,
                provider=self._id,
                success=False,
                error=f"Timeout after {task.timeout_seconds} seconds",
                duration_seconds=task.timeout_seconds
            )
        except Exception as e:
            return TaskResult(
                task_id=task.task_id,
                provider=self._id,
                success=False,
                error=str(e),
                duration_seconds=time.time() - start
            )


class QwenAdapter(BaseAdapter):
    """Adapter for Alibaba Qwen models.
    
    Supports qwen-cli, dashscope, or ollama with qwen model.
    """
    
    def __init__(self):
        super().__init__("qwen", "qwen")
        self._detected_backend = None
    
    def detect(self) -> ProviderPresence:
        qwen_path = shutil.which("qwen")
        if qwen_path:
            self._detected_backend = "qwen"
            return ProviderPresence(
                provider=self._id,
                detected=True,
                binary_path=qwen_path
            )
        
        dashscope_path = shutil.which("dashscope")
        if dashscope_path:
            self._detected_backend = "dashscope"
            return ProviderPresence(
                provider=self._id,
                detected=True,
                binary_path=dashscope_path
            )
        
        ollama_path = shutil.which("ollama")
        if ollama_path:
            try:
                result = subprocess.run(
                    ["ollama", "list"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if "qwen" in result.stdout.lower():
                    self._detected_backend = "ollama"
                    return ProviderPresence(
                        provider=self._id,
                        detected=True,
                        binary_path=ollama_path
                    )
            except Exception:
                pass
        
        return ProviderPresence(provider=self._id, detected=False)
    
    def run(self, task: TaskInput) -> TaskResult:
        start = time.time()
        
        try:
            if self._detected_backend == "qwen":
                cmd = ["qwen", "--print", task.prompt]
            elif self._detected_backend == "dashscope":
                cmd = ["dashscope", "chat", "--input", task.prompt]
            elif self._detected_backend == "ollama":
                cmd = ["ollama", "run", "qwen2.5-coder", task.prompt]
            else:
                cmd = ["qwen", "--print", task.prompt]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=task.timeout_seconds,
                cwd=task.repo_root
            )
            
            output = result.stdout
            findings = self._parse_findings(output) if result.returncode == 0 else []
            
            return TaskResult(
                task_id=task.task_id,
                provider=self._id,
                success=result.returncode == 0,
                output=output,
                findings=findings,
                error=result.stderr if result.returncode else None,
                duration_seconds=time.time() - start
            )
        except subprocess.TimeoutExpired:
            return TaskResult(
                task_id=task.task_id,
                provider=self._id,
                success=False,
                error=f"Timeout after {task.timeout_seconds} seconds",
                duration_seconds=task.timeout_seconds
            )
        except Exception as e:
            return TaskResult(
                task_id=task.task_id,
                provider=self._id,
                success=False,
                error=str(e),
                duration_seconds=time.time() - start
            )

def get_adapter_registry() -> dict:
    """Get registry of all available adapters."""
    return {
        "claude": ClaudeAdapter(),
        "codex": CodexAdapter(),
        "gemini": GeminiAdapter(),
        "opencode": OpenCodeAdapter(),
        "qwen": QwenAdapter(),
    }


def get_available_providers() -> List[ProviderId]:
    """Get list of available providers."""
    registry = get_adapter_registry()
    available = []
    for pid, adapter in registry.items():
        if adapter.detect().detected:
            available.append(pid)
    return available
