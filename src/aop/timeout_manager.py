# -*- coding: utf-8 -*-
"""
AOP 子 Agent 超时管理方案

功能：
1. 子 Agent 自主申请超时时间
2. 动态调整超时
3. 超时预警和延长请求

使用方式：
- 子 Agent 在开始任务时申请初始超时
- 执行过程中可以申请延长
- Orchestrator 根据进度和复杂度审批
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum


class TaskComplexity(Enum):
    """任务复杂度"""
    SIMPLE = "simple"          # 简单任务：单文件修改，5分钟
    MODERATE = "moderate"      # 中等任务：多文件修改，10分钟
    COMPLEX = "complex"        # 复杂任务：跨模块重构，30分钟
    EXPLORATORY = "exploratory" # 探索性任务：研究代码，20分钟


@dataclass
class TimeoutRequest:
    """子 Agent 超时请求"""
    agent_id: str
    task_id: str
    requested_timeout: int        # 请求的超时时间（秒）
    reason: str                   # 申请原因
    current_progress: float       # 当前进度 (0.0 - 1.0)
    estimated_remaining: int      # 预估剩余时间（秒）
    complexity: TaskComplexity    # 任务复杂度
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class TimeoutExtension:
    """超时延长响应"""
    request_id: str
    approved: bool                # 是否批准
    granted_timeout: int          # 批准的超时时间
    message: str                  # 反馈消息
    conditions: List[str] = field(default_factory=list)


class SubagentTimeoutManager:
    """子 Agent 超时管理器"""
    
    # 默认超时配置（基于实际经验）
    DEFAULT_TIMEOUTS = {
        TaskComplexity.SIMPLE: 300,        # 5 分钟
        TaskComplexity.MODERATE: 600,      # 10 分钟
        TaskComplexity.COMPLEX: 1800,      # 30 分钟
        TaskComplexity.EXPLORATORY: 1200,  # 20 分钟
    }
    
    MAX_TIMEOUT = 3600  # 1 小时
    EXTENSION_THRESHOLD = 0.5  # 进度超过 50% 才能申请延长
    
    def __init__(self, orchestrator_id: str):
        self.orchestrator_id = orchestrator_id
        self.active_requests: Dict[str, TimeoutRequest] = {}
        self.timeout_history: List[TimeoutRequest] = []
    
    def request_timeout(
        self,
        agent_id: str,
        task_id: str,
        requested_timeout: int,
        reason: str,
        current_progress: float = 0.0,
        estimated_remaining: int = 0,
        complexity: TaskComplexity = TaskComplexity.MODERATE
    ) -> TimeoutExtension:
        """子 Agent 申请超时时间"""
        
        request = TimeoutRequest(
            agent_id=agent_id,
            task_id=task_id,
            requested_timeout=requested_timeout,
            reason=reason,
            current_progress=current_progress,
            estimated_remaining=estimated_remaining,
            complexity=complexity
        )
        
        extension = self._evaluate_request(request)
        self.active_requests[task_id] = request
        self.timeout_history.append(request)
        
        return extension
    
    def request_extension(
        self,
        agent_id: str,
        task_id: str,
        additional_timeout: int,
        reason: str,
        current_progress: float
    ) -> TimeoutExtension:
        """子 Agent 申请延长超时（动态调整）"""
        
        if task_id not in self.active_requests:
            return TimeoutExtension(
                request_id=task_id,
                approved=False,
                granted_timeout=0,
                message="未找到原始超时请求"
            )
        
        original_request = self.active_requests[task_id]
        
        # 进度检查
        if current_progress < self.EXTENSION_THRESHOLD:
            return TimeoutExtension(
                request_id=task_id,
                approved=False,
                granted_timeout=0,
                message=f"进度不足 {int(self.EXTENSION_THRESHOLD*100)}%，无法延长"
            )
        
        new_total = original_request.requested_timeout + additional_timeout
        
        if new_total > self.MAX_TIMEOUT:
            return TimeoutExtension(
                request_id=task_id,
                approved=True,
                granted_timeout=self.MAX_TIMEOUT - original_request.requested_timeout,
                message=f"已达到最大限制，这是最后延长",
                conditions=["请确保完成"]
            )
        
        return TimeoutExtension(
            request_id=task_id,
            approved=True,
            granted_timeout=additional_timeout,
            message=f"批准延长 {additional_timeout}s",
            conditions=["请定期报告进度"]
        )
    
    def _evaluate_request(self, request: TimeoutRequest) -> TimeoutExtension:
        """评估超时请求合理性"""
        default_timeout = self.DEFAULT_TIMEOUTS.get(request.complexity, 600)
        
        if request.requested_timeout <= default_timeout:
            return TimeoutExtension(
                request_id=request.task_id,
                approved=True,
                granted_timeout=request.requested_timeout,
                message=f"批准 {request.requested_timeout}s"
            )
        
        max_suggested = min(default_timeout * 2, self.MAX_TIMEOUT)
        
        if request.requested_timeout <= max_suggested:
            return TimeoutExtension(
                request_id=request.task_id,
                approved=True,
                granted_timeout=request.requested_timeout,
                message=f"批准延长到 {request.requested_timeout}s"
            )
        
        return TimeoutExtension(
            request_id=request.task_id,
            approved=True,
            granted_timeout=max_suggested,
            message=f"调整到 {max_suggested}s",
            conditions=["如需更多请申请延长"]
        )
    
    def estimate_complexity(self, task_description: str) -> TaskComplexity:
        """根据任务描述估算复杂度"""
        task_lower = task_description.lower()
        
        # 简单任务
        if any(kw in task_lower for kw in ["修改", "修复", "添加", "单个"]):
            return TaskComplexity.SIMPLE
        
        # 复杂任务
        if any(kw in task_lower for kw in ["重构", "架构", "跨模块", "多个模块"]):
            return TaskComplexity.COMPLEX
        
        # 探索性任务
        if any(kw in task_lower for kw in ["研究", "探索", "分析", "检查", "审查"]):
            return TaskComplexity.EXPLORATORY
        
        return TaskComplexity.MODERATE
    
    def get_suggested_timeout(self, complexity: TaskComplexity) -> int:
        """获取建议的超时时间"""
        return self.DEFAULT_TIMEOUTS.get(complexity, 600)


# ========== 使用示例 ==========

if __name__ == "__main__":
    manager = SubagentTimeoutManager("orchestrator-001")
    
    # 1. 初始申请
    result = manager.request_timeout(
        agent_id="agent-ui-001",
        task_id="h-014",
        requested_timeout=900,
        reason="需要检查多个 UI 文件并修改",
        complexity=TaskComplexity.MODERATE
    )
    print(f"初始申请: {result.message}")
    
    # 2. 执行中延长
    result = manager.request_extension(
        agent_id="agent-ui-001",
        task_id="h-014",
        additional_timeout=600,
        reason="发现需要探索项目结构",
        current_progress=0.7
    )
    print(f"延长申请: {result.message}, 批准: {result.granted_timeout}s")
