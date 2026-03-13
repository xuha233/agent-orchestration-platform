# -*- coding: utf-8 -*-
"""
记忆服务 - 统一记忆管理

封装 mem0 和文件存储，提供统一 API，支持回退机制。
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .config import MemoryBackend, MemoryConfig

logger = logging.getLogger(__name__)


class MemoryService:
    """
    记忆服务 - 统一的记忆管理接口
    
    功能:
    - 添加/更新/删除记忆
    - 语义搜索（mem0）或关键词搜索（文件）
    - 项目/Agent 级别隔离
    - 自动回退到文件存储
    
    使用示例:
        config = MemoryConfig.from_yaml(Path(".aop/memory_config.yaml"))
        service = MemoryService(config)
        
        # 添加记忆
        service.add("这是一个重要的发现", metadata={"phase": "build"})
        
        # 搜索记忆
        results = service.search("重要发现")
    """
    
    def __init__(
        self,
        config: Optional[MemoryConfig] = None,
        workspace_path: Optional[Path] = None,
    ):
        """
        初始化记忆服务
        
        Args:
            config: 记忆配置，如果为 None 则使用默认配置
            workspace_path: 工作空间路径，用于文件存储
        """
        self.config = config or MemoryConfig()
        self.workspace_path = workspace_path or Path.cwd()
        
        # mem0 客户端（延迟初始化）
        self._mem0_client = None
        self._mem0_available = False
        
        # 文件存储路径
        self._file_storage_path = self.workspace_path / ".aop" / "memory"
        
        # 初始化状态
        self._initialized = False
        self._init_error: Optional[str] = None
    
    def _ensure_initialized(self) -> None:
        """确保服务已初始化"""
        if self._initialized:
            return
        
        self._initialized = True
        
        if not self.config.enabled:
            logger.info("mem0 已禁用，使用文件存储")
            return
        
        if self.config.backend == MemoryBackend.FILE:
            logger.info("使用文件存储后端")
            return
        
        # 尝试初始化 mem0
        try:
            self._init_mem0()
        except Exception as e:
            logger.warning(f"mem0 初始化失败，回退到文件存储: {e}")
            self._init_error = str(e)
            self._mem0_available = False
    
    def _init_mem0(self) -> None:
        """初始化 mem0 客户端"""
        try:
            from mem0 import Memory
        except ImportError:
            raise ImportError(
                "mem0ai 未安装。请运行: pip install mem0ai faiss-cpu\n"
                "或使用: pip install agent-orchestration-platform[memory]"
            )
        
        # 构建 mem0 配置
        mem0_config = self._build_mem0_config()
        
        # 初始化 mem0
        self._mem0_client = Memory.from_config(mem0_config)
        self._mem0_available = True
        logger.info(f"mem0 初始化成功，后端: {self.config.backend.value}")
    
    def _build_mem0_config(self) -> Dict[str, Any]:
        """构建 mem0 配置"""
        base_config = {
            "vector_store": self._get_vector_store_config(),
        }
        
        # 合并用户自定义配置
        if self.config.mem0_config:
            base_config.update(self.config.mem0_config)
        
        return base_config
    
    def _get_vector_store_config(self) -> Dict[str, Any]:
        """获取向量存储配置"""
        vector_path = self.config.vector_store_path or (
            self._file_storage_path / "vectors"
        )
        
        if self.config.backend == MemoryBackend.MEM0_LOCAL:
            return {
                "provider": "faiss",
                "config": {
                    "collection_name": f"aop_{self.config.project_id}",
                    "path": str(vector_path),
                }
            }
        elif self.config.backend == MemoryBackend.MEM0_QDRANT:
            return {
                "provider": "qdrant",
                "config": self.config.mem0_config.get("qdrant", {
                    "collection_name": f"aop_{self.config.project_id}",
                })
            }
        elif self.config.backend == MemoryBackend.MEM0_CHROMA:
            return {
                "provider": "chroma",
                "config": {
                    "collection_name": f"aop_{self.config.project_id}",
                    "path": str(vector_path),
                }
            }
        
        # 默认 FAISS
        return {
            "provider": "faiss",
            "config": {
                "collection_name": f"aop_{self.config.project_id}",
                "path": str(vector_path),
            }
        }
    
    @property
    def is_mem0_available(self) -> bool:
        """检查 mem0 是否可用"""
        self._ensure_initialized()
        return self._mem0_available
    
    @property
    def current_backend(self) -> MemoryBackend:
        """获取当前使用的后端"""
        if not self.config.enabled:
            return MemoryBackend.FILE
        if self._mem0_available:
            return self.config.backend
        return MemoryBackend.FILE
    
    # ==================== 记忆操作 ====================
    
    def add(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        memory_id: Optional[str] = None,
    ) -> Optional[str]:
        """
        添加记忆
        
        Args:
            content: 记忆内容
            metadata: 元数据（如 phase, hypothesis_id 等）
            memory_id: 可选的记忆 ID（用于更新）
        
        Returns:
            记忆 ID，失败返回 None
        """
        self._ensure_initialized()
        
        metadata = metadata or {}
        metadata["timestamp"] = datetime.now().isoformat()
        metadata["project_id"] = self.config.project_id
        
        if self._mem0_available:
            return self._add_to_mem0(content, metadata, memory_id)
        else:
            return self._add_to_file(content, metadata, memory_id)
    
    def _add_to_mem0(
        self,
        content: str,
        metadata: Dict[str, Any],
        memory_id: Optional[str] = None,
    ) -> Optional[str]:
        """添加记忆到 mem0"""
        try:
            user_id = self.config.get_mem0_user_id()
            
            if memory_id:
                # 更新现有记忆
                result = self._mem0_client.update(
                    memory_id=memory_id,
                    data=content,
                )
                return memory_id
            else:
                # 添加新记忆
                result = self._mem0_client.add(
                    content,
                    user_id=user_id,
                    metadata=metadata,
                )
                
                # mem0 返回的格式可能是 {"results": [{"id": "..."}]}
                if isinstance(result, dict) and "results" in result:
                    results = result["results"]
                    if results:
                        return results[0].get("id")
                elif isinstance(result, list) and result:
                    return result[0].get("id")
                
                return result.get("id") if isinstance(result, dict) else None
                
        except Exception as e:
            logger.error(f"添加记忆到 mem0 失败: {e}")
            # 回退到文件存储
            return self._add_to_file(content, metadata, memory_id)
    
    def _add_to_file(
        self,
        content: str,
        metadata: Dict[str, Any],
        memory_id: Optional[str] = None,
    ) -> Optional[str]:
        """添加记忆到文件存储"""
        try:
            self._file_storage_path.mkdir(parents=True, exist_ok=True)
            
            memories_file = self._file_storage_path / "memories.json"
            
            # 加载现有记忆
            memories = {}
            if memories_file.exists():
                with open(memories_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    memories = data.get("memories", {})
            
            # 生成或使用现有 ID
            if not memory_id:
                import uuid
                memory_id = f"mem_{uuid.uuid4().hex[:8]}"
            
            # 添加记忆
            memories[memory_id] = {
                "id": memory_id,
                "content": content,
                "metadata": metadata,
                "created_at": metadata.get("timestamp", datetime.now().isoformat()),
            }
            
            # 保存
            with open(memories_file, "w", encoding="utf-8") as f:
                json.dump({
                    "_meta": {
                        "saved_at": datetime.now().isoformat(),
                        "version": 1,
                    },
                    "memories": memories,
                }, f, ensure_ascii=False, indent=2)
            
            return memory_id
            
        except Exception as e:
            logger.error(f"添加记忆到文件失败: {e}")
            return None
    
    def search(
        self,
        query: str,
        top_k: Optional[int] = None,
        threshold: Optional[float] = None,
        metadata_filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        搜索记忆
        
        Args:
            query: 搜索查询
            top_k: 返回结果数量
            threshold: 相似度阈值（仅语义搜索）
            metadata_filter: 元数据过滤条件
        
        Returns:
            记忆列表，每项包含 id, content, metadata, score
        """
        self._ensure_initialized()
        
        top_k = top_k or self.config.search_top_k
        threshold = threshold or self.config.search_threshold
        
        if self._mem0_available:
            return self._search_mem0(query, top_k, metadata_filter)
        else:
            return self._search_file(query, top_k, threshold, metadata_filter)
    
    def _search_mem0(
        self,
        query: str,
        top_k: int,
        metadata_filter: Optional[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """使用 mem0 进行语义搜索"""
        try:
            user_id = self.config.get_mem0_user_id()
            
            result = self._mem0_client.search(
                query,
                user_id=user_id,
                limit=top_k,
            )
            
            # 处理结果格式
            memories = []
            if isinstance(result, dict) and "results" in result:
                for item in result["results"]:
                    memories.append({
                        "id": item.get("id"),
                        "content": item.get("memory", item.get("content", "")),
                        "metadata": item.get("metadata", {}),
                        "score": item.get("score", 1.0),
                    })
            elif isinstance(result, list):
                for item in result:
                    memories.append({
                        "id": item.get("id"),
                        "content": item.get("memory", item.get("content", "")),
                        "metadata": item.get("metadata", {}),
                        "score": item.get("score", 1.0),
                    })
            
            return memories
            
        except Exception as e:
            logger.error(f"mem0 搜索失败: {e}")
            # 回退到关键词搜索
            return self._search_file(query, top_k, 0.0, metadata_filter)
    
    def _search_file(
        self,
        query: str,
        top_k: int,
        threshold: float,
        metadata_filter: Optional[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """使用文件进行关键词搜索"""
        try:
            memories_file = self._file_storage_path / "memories.json"
            
            if not memories_file.exists():
                return []
            
            with open(memories_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            memories = data.get("memories", {})
            
            # 关键词搜索
            query_lower = query.lower()
            results = []
            
            for mem_id, mem_data in memories.items():
                content = mem_data.get("content", "").lower()
                metadata = mem_data.get("metadata", {})
                
                # 元数据过滤
                if metadata_filter:
                    match = all(
                        metadata.get(k) == v
                        for k, v in metadata_filter.items()
                    )
                    if not match:
                        continue
                
                # 简单的关键词匹配
                if query_lower in content:
                    # 计算简单的"分数"
                    score = 1.0 if query_lower == content else 0.8
                    results.append({
                        "id": mem_id,
                        "content": mem_data.get("content", ""),
                        "metadata": metadata,
                        "score": score,
                    })
            
            # 排序并限制数量
            results.sort(key=lambda x: x["score"], reverse=True)
            return results[:top_k]
            
        except Exception as e:
            logger.error(f"文件搜索失败: {e}")
            return []
    
    def get(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """
        获取单个记忆
        
        Args:
            memory_id: 记忆 ID
        
        Returns:
            记忆数据，不存在返回 None
        """
        self._ensure_initialized()
        
        if self._mem0_available:
            try:
                result = self._mem0_client.get(memory_id)
                if result:
                    return {
                        "id": memory_id,
                        "content": result.get("memory", result.get("content", "")),
                        "metadata": result.get("metadata", {}),
                    }
            except Exception as e:
                logger.error(f"从 mem0 获取记忆失败: {e}")
        
        # 回退到文件
        return self._get_from_file(memory_id)
    
    def _get_from_file(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """从文件获取记忆"""
        try:
            memories_file = self._file_storage_path / "memories.json"
            
            if not memories_file.exists():
                return None
            
            with open(memories_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            memories = data.get("memories", {})
            mem_data = memories.get(memory_id)
            
            if mem_data:
                return {
                    "id": memory_id,
                    "content": mem_data.get("content", ""),
                    "metadata": mem_data.get("metadata", {}),
                }
            
            return None
            
        except Exception as e:
            logger.error(f"从文件获取记忆失败: {e}")
            return None
    
    def delete(self, memory_id: str) -> bool:
        """
        删除记忆
        
        Args:
            memory_id: 记忆 ID
        
        Returns:
            删除是否成功
        """
        self._ensure_initialized()
        
        if self._mem0_available:
            try:
                self._mem0_client.delete(memory_id)
                return True
            except Exception as e:
                logger.error(f"从 mem0 删除记忆失败: {e}")
        
        # 从文件删除
        return self._delete_from_file(memory_id)
    
    def _delete_from_file(self, memory_id: str) -> bool:
        """从文件删除记忆"""
        try:
            memories_file = self._file_storage_path / "memories.json"
            
            if not memories_file.exists():
                return False
            
            with open(memories_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            memories = data.get("memories", {})
            
            if memory_id not in memories:
                return False
            
            del memories[memory_id]
            
            with open(memories_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            return True
            
        except Exception as e:
            logger.error(f"从文件删除记忆失败: {e}")
            return False
    
    def list_all(
        self,
        metadata_filter: Optional[Dict[str, Any]] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        列出所有记忆
        
        Args:
            metadata_filter: 元数据过滤条件
            limit: 最大返回数量
        
        Returns:
            记忆列表
        """
        self._ensure_initialized()
        
        if self._mem0_available:
            try:
                user_id = self.config.get_mem0_user_id()
                result = self._mem0_client.get_all(user_id=user_id)
                
                memories = []
                items = result if isinstance(result, list) else result.get("results", [])
                
                for item in items[:limit]:
                    memories.append({
                        "id": item.get("id"),
                        "content": item.get("memory", item.get("content", "")),
                        "metadata": item.get("metadata", {}),
                    })
                
                return memories
                
            except Exception as e:
                logger.error(f"从 mem0 列出记忆失败: {e}")
        
        # 从文件列出
        return self._list_from_file(metadata_filter, limit)
    
    def _list_from_file(
        self,
        metadata_filter: Optional[Dict[str, Any]],
        limit: int,
    ) -> List[Dict[str, Any]]:
        """从文件列出记忆"""
        try:
            memories_file = self._file_storage_path / "memories.json"
            
            if not memories_file.exists():
                return []
            
            with open(memories_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            memories = data.get("memories", {})
            results = []
            
            for mem_id, mem_data in memories.items():
                metadata = mem_data.get("metadata", {})
                
                # 元数据过滤
                if metadata_filter:
                    match = all(
                        metadata.get(k) == v
                        for k, v in metadata_filter.items()
                    )
                    if not match:
                        continue
                
                results.append({
                    "id": mem_id,
                    "content": mem_data.get("content", ""),
                    "metadata": metadata,
                })
                
                if len(results) >= limit:
                    break
            
            return results
            
        except Exception as e:
            logger.error(f"从文件列出记忆失败: {e}")
            return []
    
    def clear(self) -> int:
        """
        清除所有记忆
        
        Returns:
            清除的记忆数量
        """
        self._ensure_initialized()
        
        if self._mem0_available:
            try:
                user_id = self.config.get_mem0_user_id()
                self._mem0_client.delete_all(user_id=user_id)
                return -1  # mem0 不返回数量
            except Exception as e:
                logger.error(f"从 mem0 清除记忆失败: {e}")
        
        # 从文件清除
        return self._clear_file()
    
    def _clear_file(self) -> int:
        """从文件清除记忆"""
        try:
            memories_file = self._file_storage_path / "memories.json"
            
            if not memories_file.exists():
                return 0
            
            with open(memories_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            count = len(data.get("memories", {}))
            
            # 清空但保留文件结构
            data["memories"] = {}
            
            with open(memories_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            return count
            
        except Exception as e:
            logger.error(f"从文件清除记忆失败: {e}")
            return 0
    
    # ==================== 兼容性方法 ====================
    
    def load_hypotheses(self) -> Dict[str, Any]:
        """加载假设记录（兼容现有 API）"""
        hypotheses_file = self.workspace_path / ".aop" / "hypotheses.json"
        
        if hypotheses_file.exists():
            with open(hypotheses_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("data", data)
        
        return {}
    
    def save_hypotheses(self, hypotheses: Dict[str, Any]) -> None:
        """保存假设记录（兼容现有 API）"""
        hypotheses_file = self.workspace_path / ".aop" / "hypotheses.json"
        hypotheses_file.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            "_meta": {
                "saved_at": datetime.now().isoformat(),
                "version": 1,
            },
            "data": hypotheses,
        }
        
        with open(hypotheses_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def load_learnings(self) -> List[Dict[str, Any]]:
        """加载学习记录（兼容现有 API）"""
        learning_file = self.workspace_path / ".aop" / "learning.json"
        
        if learning_file.exists():
            with open(learning_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("records", data.get("data", []))
        
        return []
    
    def save_learnings(self, learnings: List[Dict[str, Any]]) -> None:
        """保存学习记录（兼容现有 API）"""
        learning_file = self.workspace_path / ".aop" / "learning.json"
        learning_file.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            "_meta": {
                "saved_at": datetime.now().isoformat(),
                "version": 1,
            },
            "records": learnings,
        }
        
        with open(learning_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def get_status(self) -> Dict[str, Any]:
        """获取服务状态"""
        self._ensure_initialized()
        
        return {
            "enabled": self.config.enabled,
            "backend": self.current_backend.value,
            "mem0_available": self._mem0_available,
            "init_error": self._init_error,
            "project_id": self.config.project_id,
            "workspace": str(self.workspace_path),
        }
