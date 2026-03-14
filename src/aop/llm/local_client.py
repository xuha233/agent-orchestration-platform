"""本地LLM客户端实现（Ollama）"""

import subprocess
from typing import List
from . import LLMClient, LLMProvider, LLMMessage, LLMResponse


class LocalLLMClient(LLMClient):
    """本地LLM客户端（Ollama）"""
    
    def __init__(
        self,
        command: str = "ollama",
        model: str = "llama3",
        timeout: int = 300,
    ):
        self.command = command
        self.model = model
        self.timeout = timeout
    
    @property
    def provider(self) -> LLMProvider:
        return LLMProvider.LOCAL
    
    def complete(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs
    ) -> LLMResponse:
        """执行本地LLM补全请求"""
        prompt = self._build_prompt(messages)
        
        result = subprocess.run(
            [self.command, "run", self.model, prompt],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=self.timeout,
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"Local LLM error: {result.stderr}")
        
        return LLMResponse(
            content=result.stdout.strip(),
            model=self.model,
            usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            finish_reason="stop",
        )
    
    def _build_prompt(self, messages: List[LLMMessage]) -> str:
        """构建提示字符串"""
        parts = []
        for m in messages:
            if m.role == "system":
                parts.append(f"System: {m.content}")
            elif m.role == "user":
                parts.append(f"User: {m.content}")
            elif m.role == "assistant":
                parts.append(f"Assistant: {m.content}")
        return "\n\n".join(parts)
