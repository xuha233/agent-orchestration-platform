# -*- coding: utf-8 -*-
"""
记忆配置管理

支持启用/禁用 mem0，以及多种后端配置。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


class MemoryBackend(Enum):
    """记忆后端类型"""
    FILE = "file"           # 文件存储（默认，向后兼容）
    MEM0_LOCAL = "mem0_local"  # mem0 本地模式（使用 FAISS）
    MEM0_QDRANT = "mem0_qdrant"  # mem0 + Qdrant
    MEM0_CHROMA = "mem0_chroma"  # mem0 + ChromaDB


@dataclass
class MemoryConfig:
    """记忆服务配置"""
    
    # 是否启用 mem0（默认禁用，保持向后兼容）
    enabled: bool = False
    
    # 后端类型
    backend: MemoryBackend = MemoryBackend.FILE
    
    # 项目隔离 ID（用于 mem0 的 user_id）
    project_id: str = "default"
    
    # Agent 隔离（多个 Agent 可能有不同的命名空间）
    agent_namespace: str = ""
    
    # mem0 配置
    mem0_config: Dict[str, Any] = field(default_factory=dict)
    
    # 向量存储路径（本地模式）
    vector_store_path: Optional[Path] = None
    
    # 嵌入模型配置
    embedding_model: str = "text-embedding-ada-002"
    embedding_dims: int = 1536
    
    # 搜索配置
    search_top_k: int = 5
    search_threshold: float = 0.7
    
    @classmethod
    def from_yaml(cls, path: Path) -> "MemoryConfig":
        """从 YAML 文件加载配置"""
        if not path.exists():
            return cls()
        
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        
        return cls.from_dict(data)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryConfig":
        """从字典创建配置"""
        backend_str = data.get("backend", "file")
        try:
            backend = MemoryBackend(backend_str)
        except ValueError:
            backend = MemoryBackend.FILE
        
        vector_path = data.get("vector_store_path")
        if vector_path:
            vector_path = Path(vector_path)
        
        return cls(
            enabled=data.get("enabled", False),
            backend=backend,
            project_id=data.get("project_id", "default"),
            agent_namespace=data.get("agent_namespace", ""),
            mem0_config=data.get("mem0_config", {}),
            vector_store_path=vector_path,
            embedding_model=data.get("embedding_model", "text-embedding-ada-002"),
            embedding_dims=data.get("embedding_dims", 1536),
            search_top_k=data.get("search_top_k", 5),
            search_threshold=data.get("search_threshold", 0.7),
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "enabled": self.enabled,
            "backend": self.backend.value,
            "project_id": self.project_id,
            "agent_namespace": self.agent_namespace,
            "mem0_config": self.mem0_config,
            "vector_store_path": str(self.vector_store_path) if self.vector_store_path else None,
            "embedding_model": self.embedding_model,
            "embedding_dims": self.embedding_dims,
            "search_top_k": self.search_top_k,
            "search_threshold": self.search_threshold,
        }
    
    def to_yaml(self, path: Path) -> None:
        """保存到 YAML 文件"""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(self.to_dict(), f, default_flow_style=False, allow_unicode=True)
    
    def get_mem0_user_id(self) -> str:
        """获取 mem0 user_id（项目隔离）"""
        if self.agent_namespace:
            return f"{self.project_id}_{self.agent_namespace}"
        return self.project_id


# 默认配置模板
DEFAULT_CONFIG_TEMPLATE = """# AOP 记忆配置
# 启用 mem0 后将获得语义搜索能力

# 是否启用 mem0（默认 false，保持向后兼容）
enabled: false

# 后端类型: file, mem0_local, mem0_qdrant, mem0_chroma
backend: mem0_local

# 项目 ID（用于隔离不同项目的记忆）
project_id: default

# Agent 命名空间（可选，用于同一项目内不同 Agent 隔离）
agent_namespace: ""

# 向量存储路径（本地模式）
vector_store_path: .aop/memory/vectors

# 嵌入模型配置
embedding_model: text-embedding-ada-002
embedding_dims: 1536

# 搜索配置
search_top_k: 5
search_threshold: 0.7

# mem0 高级配置（可选）
# mem0_config:
#   llm:
#     provider: openai
#     model: gpt-4
#   embedder:
#     provider: openai
#     model: text-embedding-ada-002
"""


def create_default_config(path: Path) -> None:
    """创建默认配置文件"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(DEFAULT_CONFIG_TEMPLATE)
