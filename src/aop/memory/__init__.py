# -*- coding: utf-8 -*-
"""AOP Memory module - 统一记忆管理

支持 mem0 语义记忆和文件存储，自动回退机制。

使用示例:
    from aop.memory import MemoryService, MemoryConfig
    
    # 从配置文件加载
    config = MemoryConfig.from_yaml(Path(".aop/memory_config.yaml"))
    service = MemoryService(config)
    
    # 添加记忆
    service.add("这是一个重要的发现", metadata={"phase": "build"})
    
    # 搜索记忆
    results = service.search("重要发现")
"""

from .loader import load_combined_memory, build_agent_system_prompt, get_global_aop_dir
from .config import MemoryBackend, MemoryConfig, create_default_config, DEFAULT_CONFIG_TEMPLATE
from .service import MemoryService
from .migration import MemoryMigrator

__all__ = [
    # 原有 API（向后兼容）
    'load_combined_memory',
    'build_agent_system_prompt',
    'get_global_aop_dir',
    
    # 新增 API
    'MemoryBackend',
    'MemoryConfig',
    'MemoryService',
    'MemoryMigrator',
    'create_default_config',
    'DEFAULT_CONFIG_TEMPLATE',
]
