"""Claude API客户端实现"""

import os
from typing import List
from . import LLMClient, LLMProvider, LLMMessage, LLMResponse


class ClaudeClient(LLMClient):
    """Claude API客户端"""
    
    def __init__(
        self,
        api_key: str | None = None,
        model: str = "claude-sonnet-4-20250514",
    ):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.model = model
        self._client = None
    
    @property
    def provider(self) -> LLMProvider:
        return LLMProvider.CLAUDE
    
    def _get_client(self):
        """懒加载Anthropic客户端"""
        if self._client is None:
            import anthropic
            self._client = anthropic.Anthropic(api_key=self.api_key)
        return self._client
    
    def complete(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        system: str | None = None,
        **kwargs
    ) -> LLMResponse:
        """执行Claude补全请求"""
        client = self._get_client()
        api_messages = [{"role": m.role, "content": m.content} for m in messages]
        
        params = {
            "model": self.model,
            "messages": api_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if system:
            params["system"] = system
        
        response = client.messages.create(**params)
        
        return LLMResponse(
            content=response.content[0].text,
            model=response.model,
            usage={
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
            },
            finish_reason=response.stop_reason,
            raw=response.model_dump(),
        )
