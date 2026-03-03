"""LLM Client Layer - 抽象化LLM调用接口"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Any
from enum import Enum


class LLMProvider(Enum):
    """LLM提供商类型"""
    CLAUDE = "claude"
    OPENAI = "openai"
    LOCAL = "local"


@dataclass
class LLMResponse:
    """LLM响应结果"""
    content: str
    model: str
    usage: Dict[str, int]
    finish_reason: str
    raw: Dict[str, Any] | None = None


@dataclass
class LLMMessage:
    """LLM消息"""
    role: str  # system, user, assistant
    content: str


class LLMClient(ABC):
    """LLM客户端抽象基类"""
    
    @property
    @abstractmethod
    def provider(self) -> LLMProvider:
        """返回提供商类型"""
        pass
    
    @abstractmethod
    def complete(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs
    ) -> LLMResponse:
        """执行补全请求"""
        pass
    
    def count_tokens(self, text: str) -> int:
        """估算token数量（默认简单估算）"""
        return len(text) // 4
    
    def validate_connection(self) -> bool:
        """验证连接是否正常"""
        try:
            response = self.complete([
                LLMMessage(role="user", content="ping")
            ], max_tokens=10)
            return bool(response.content)
        except Exception:
            return False


# 导出具体实现
from .claude_client import ClaudeClient
from .local_client import LocalLLMClient

__all__ = [
    "LLMProvider",
    "LLMResponse",
    "LLMMessage",
    "LLMClient",
    "ClaudeClient",
    "LocalLLMClient",
]
