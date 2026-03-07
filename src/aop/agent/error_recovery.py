# -*- coding: utf-8 -*-
"""
Error Recovery - 错误恢复机制

基于 Anthropic 多智能体研究系统的可靠性最佳实践。

核心功能：
1. 错误分类 - 识别错误类型
2. 恢复策略 - 自动选择恢复方案
3. 重试机制 - 带退避的重试
4. 状态恢复 - 从检查点恢复
"""

from __future__ import annotations

import time
import random
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable, TypeVar
from enum import Enum
from datetime import datetime


class ErrorType(Enum):
    """错误类型"""
    TIMEOUT = "timeout"
    NETWORK = "network"
    RATE_LIMIT = "rate_limit"
    VALIDATION = "validation"
    DEPENDENCY = "dependency"
    RESOURCE = "resource"
    PERMISSION = "permission"
    UNKNOWN = "unknown"


class RecoveryAction(Enum):
    """恢复动作"""
    RETRY = "retry"                    # 重试
    RETRY_WITH_BACKOFF = "retry_with_backoff"  # 带退避的重试
    SKIP = "skip"                      # 跳过
    ESCALATE = "escalate"              # 上报
    MARK_COMPLETED = "mark_completed"  # 标记完成
    ABORT = "abort"                    # 中止
    FALLBACK = "fallback"              # 降级


@dataclass
class RecoveryDecision:
    """恢复决策"""
    action: RecoveryAction
    reason: str
    params: Dict[str, Any] = field(default_factory=dict)
    delay_seconds: float = 0.0
    max_retries: int = 3


@dataclass
class ErrorContext:
    """错误上下文"""
    error: Exception
    error_type: ErrorType
    timestamp: datetime = field(default_factory=datetime.now)
    retry_count: int = 0
    task_id: str = ""
    execution_result: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "error_type": self.error_type.value,
            "error_message": str(self.error),
            "timestamp": self.timestamp.isoformat(),
            "retry_count": self.retry_count,
            "task_id": self.task_id,
        }


@dataclass
class RetryState:
    """重试状态"""
    attempt: int = 0
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    last_error: Optional[Exception] = None
    last_attempt_time: Optional[datetime] = None
    
    def next_delay(self, strategy: str = "exponential") -> float:
        """计算下一次延迟"""
        if strategy == "exponential":
            delay = self.base_delay * (2 ** self.attempt)
        elif strategy == "linear":
            delay = self.base_delay * (self.attempt + 1)
        else:
            delay = self.base_delay
        
        # 添加抖动
        jitter = random.uniform(0, 0.1 * delay)
        return min(delay + jitter, self.max_delay)
    
    def can_retry(self) -> bool:
        """是否可以重试"""
        return self.attempt < self.max_attempts


class ErrorClassifier:
    """错误分类器"""
    
    # 错误模式映射
    ERROR_PATTERNS = {
        ErrorType.TIMEOUT: [
            "timeout", "timed out", "deadline exceeded",
            "超时", "超时了",
        ],
        ErrorType.NETWORK: [
            "connection", "network", "socket", "dns",
            "网络", "连接", "dns",
        ],
        ErrorType.RATE_LIMIT: [
            "rate limit", "too many requests", "429", "quota",
            "限流", "频率限制",
        ],
        ErrorType.VALIDATION: [
            "validation", "invalid", "schema", "format",
            "验证", "无效", "格式错误",
        ],
        ErrorType.DEPENDENCY: [
            "dependency", "import", "module", "package",
            "依赖", "模块", "包",
        ],
        ErrorType.RESOURCE: [
            "memory", "disk", "cpu", "resource", "oom",
            "内存", "磁盘", "资源",
        ],
        ErrorType.PERMISSION: [
            "permission", "forbidden", "unauthorized", "access denied",
            "权限", "禁止", "未授权",
        ],
    }
    
    def classify(self, error: Exception) -> ErrorType:
        """分类错误"""
        error_message = str(error).lower()
        error_class = type(error).__name__.lower()
        
        for error_type, patterns in self.ERROR_PATTERNS.items():
            for pattern in patterns:
                if pattern in error_message or pattern in error_class:
                    return error_type
        
        # 检查异常类型
        if isinstance(error, TimeoutError):
            return ErrorType.TIMEOUT
        
        if isinstance(error, ConnectionError):
            return ErrorType.NETWORK
        
        if isinstance(error, PermissionError):
            return ErrorType.PERMISSION
        
        return ErrorType.UNKNOWN


class RecoveryStrategy:
    """恢复策略"""
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
    
    def decide(
        self,
        error_context: ErrorContext,
        task_progress: float = 0.0,
    ) -> RecoveryDecision:
        """
        决定恢复策略
        
        Args:
            error_context: 错误上下文
            task_progress: 任务进度 (0.0 - 1.0)
            
        Returns:
            恢复决策
        """
        error_type = error_context.error_type
        retry_count = error_context.retry_count
        
        # 超时错误
        if error_type == ErrorType.TIMEOUT:
            return self._handle_timeout(error_context, task_progress)
        
        # 网络错误
        if error_type == ErrorType.NETWORK:
            return RecoveryDecision(
                action=RecoveryAction.RETRY_WITH_BACKOFF,
                reason="网络错误，稍后重试",
                params={
                    "base_delay": self.base_delay,
                    "max_delay": self.max_delay,
                },
                max_retries=5,
            )
        
        # 限流错误
        if error_type == ErrorType.RATE_LIMIT:
            return RecoveryDecision(
                action=RecoveryAction.RETRY_WITH_BACKOFF,
                reason="触发限流，等待后重试",
                params={
                    "base_delay": 5.0,  # 限流时等待更久
                    "max_delay": 120.0,
                },
                delay_seconds=5.0,
                max_retries=5,
            )
        
        # 验证错误
        if error_type == ErrorType.VALIDATION:
            if retry_count >= 2:
                return RecoveryDecision(
                    action=RecoveryAction.ESCALATE,
                    reason="验证错误重试失败，需要人工干预",
                )
            return RecoveryDecision(
                action=RecoveryAction.RETRY,
                reason="验证错误，重试",
                max_retries=2,
            )
        
        # 依赖错误
        if error_type == ErrorType.DEPENDENCY:
            return RecoveryDecision(
                action=RecoveryAction.ESCALATE,
                reason="依赖问题，需要手动解决",
            )
        
        # 资源错误
        if error_type == ErrorType.RESOURCE:
            if retry_count >= 1:
                return RecoveryDecision(
                    action=RecoveryAction.ABORT,
                    reason="资源不足，中止任务",
                )
            return RecoveryDecision(
                action=RecoveryAction.RETRY_WITH_BACKOFF,
                reason="资源不足，等待后重试",
                delay_seconds=10.0,
                max_retries=1,
            )
        
        # 权限错误
        if error_type == ErrorType.PERMISSION:
            return RecoveryDecision(
                action=RecoveryAction.ESCALATE,
                reason="权限不足，需要人工处理",
            )
        
        # 未知错误
        return RecoveryDecision(
            action=RecoveryAction.RETRY if retry_count < self.max_retries else RecoveryAction.ESCALATE,
            reason=f"未知错误，{'重试' if retry_count < self.max_retries else '上报'}",
            max_retries=self.max_retries,
        )
    
    def _handle_timeout(
        self,
        error_context: ErrorContext,
        task_progress: float,
    ) -> RecoveryDecision:
        """处理超时"""
        retry_count = error_context.retry_count
        
        # 检查任务进度
        if task_progress >= 0.9:
            return RecoveryDecision(
                action=RecoveryAction.MARK_COMPLETED,
                reason="任务进度已超过 90%，认为完成",
                params={"progress": task_progress},
            )
        
        if task_progress >= 0.5:
            # 进度超过一半，增加超时重试
            return RecoveryDecision(
                action=RecoveryAction.RETRY,
                reason=f"任务进度 {task_progress:.0%}，增加超时重试",
                params={
                    "timeout_multiplier": 1.5,
                },
                max_retries=3,
            )
        
        if retry_count >= 3:
            return RecoveryDecision(
                action=RecoveryAction.ESCALATE,
                reason="超时重试次数已达上限",
            )
        
        return RecoveryDecision(
            action=RecoveryAction.RETRY_WITH_BACKOFF,
            reason="超时，等待后重试",
            params={"timeout_multiplier": 1.5},
            max_retries=3,
        )


T = TypeVar('T')


class ErrorRecoveryManager:
    """
    错误恢复管理器
    
    统一处理错误恢复逻辑。
    
    使用示例：
    ```python
    manager = ErrorRecoveryManager()
    
    result = manager.execute_with_recovery(
        func=lambda: risky_operation(),
        task_id="task-001",
        on_retry=lambda: print("Retrying..."),
    )
    ```
    """
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
    ):
        self.classifier = ErrorClassifier()
        self.strategy = RecoveryStrategy(
            max_retries=max_retries,
            base_delay=base_delay,
            max_delay=max_delay,
        )
        self.error_history: List[ErrorContext] = []
    
    def execute_with_recovery(
        self,
        func: Callable[[], T],
        task_id: str = "",
        on_retry: Optional[Callable[[int, Exception], None]] = None,
        on_failure: Optional[Callable[[Exception], None]] = None,
        get_progress: Optional[Callable[[], float]] = None,
    ) -> T:
        """
        执行函数并自动恢复
        
        Args:
            func: 要执行的函数
            task_id: 任务ID
            on_retry: 重试回调
            on_failure: 失败回调
            get_progress: 获取进度的函数
            
        Returns:
            函数返回值
            
        Raises:
            Exception: 最终失败时抛出异常
        """
        retry_state = RetryState(
            max_attempts=self.strategy.max_retries,
            base_delay=self.strategy.base_delay,
            max_delay=self.strategy.max_delay,
        )
        
        last_error: Optional[Exception] = None
        
        while retry_state.can_retry():
            try:
                return func()
            
            except Exception as e:
                last_error = e
                retry_state.attempt += 1
                retry_state.last_error = e
                retry_state.last_attempt_time = datetime.now()
                
                # 分类错误
                error_type = self.classifier.classify(e)
                
                # 创建错误上下文
                error_context = ErrorContext(
                    error=e,
                    error_type=error_type,
                    retry_count=retry_state.attempt - 1,
                    task_id=task_id,
                )
                
                # 记录错误
                self.error_history.append(error_context)
                
                # 获取进度
                progress = get_progress() if get_progress else 0.0
                
                # 决定恢复策略
                decision = self.strategy.decide(error_context, progress)
                
                # 处理决策
                if decision.action == RecoveryAction.MARK_COMPLETED:
                    # 标记完成，返回默认值或抛出特定异常
                    raise RecoveryCompletedException(decision.reason)
                
                if decision.action == RecoveryAction.ESCALATE:
                    if on_failure:
                        on_failure(e)
                    raise e
                
                if decision.action == RecoveryAction.ABORT:
                    if on_failure:
                        on_failure(e)
                    raise e
                
                if decision.action in (RecoveryAction.RETRY, RecoveryAction.RETRY_WITH_BACKOFF):
                    if not retry_state.can_retry():
                        if on_failure:
                            on_failure(e)
                        raise e
                    
                    # 计算延迟
                    if decision.action == RecoveryAction.RETRY_WITH_BACKOFF:
                        delay = retry_state.next_delay("exponential")
                    else:
                        delay = decision.delay_seconds
                    
                    # 回调
                    if on_retry:
                        on_retry(retry_state.attempt, e)
                    
                    # 等待
                    time.sleep(delay)
                    continue
                
                # 其他情况
                if on_failure:
                    on_failure(e)
                raise e
        
        # 不应该到达这里
        if last_error:
            raise last_error
        raise RuntimeError("Unexpected state in error recovery")
    
    def get_error_stats(self) -> Dict[str, Any]:
        """获取错误统计"""
        if not self.error_history:
            return {"total_errors": 0}
        
        by_type: Dict[str, int] = {}
        for ctx in self.error_history:
            error_type = ctx.error_type.value
            by_type[error_type] = by_type.get(error_type, 0) + 1
        
        return {
            "total_errors": len(self.error_history),
            "by_type": by_type,
            "recent_errors": [ctx.to_dict() for ctx in self.error_history[-5:]],
        }


class RecoveryCompletedException(Exception):
    """恢复完成异常 - 表示任务已通过其他方式完成"""
    pass


class CheckpointManager:
    """
    检查点管理器
    
    定期保存执行状态，支持断点续传。
    """
    
    def __init__(
        self,
        checkpoint_dir: str = ".aop/checkpoints",
        auto_save_interval: int = 60,  # 秒
    ):
        from pathlib import Path
        self.checkpoint_dir = Path(checkpoint_dir)
        self.auto_save_interval = auto_save_interval
        self.last_save_time: Optional[datetime] = None
        self._ensure_dir()
    
    def _ensure_dir(self):
        """确保目录存在"""
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
    
    def save_checkpoint(
        self,
        task_id: str,
        state: str,
        progress: float,
        data: Dict[str, Any],
    ) -> None:
        """保存检查点"""
        import json
        
        checkpoint = {
            "task_id": task_id,
            "state": state,
            "progress": progress,
            "data": data,
            "timestamp": datetime.now().isoformat(),
        }
        
        checkpoint_path = self.checkpoint_dir / f"{task_id}.checkpoint.json"
        
        # 原子写入
        temp_path = self.checkpoint_dir / f".tmp_{task_id}.json"
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(checkpoint, f, ensure_ascii=False, indent=2, default=str)
        
        temp_path.replace(checkpoint_path)
        self.last_save_time = datetime.now()
    
    def load_checkpoint(self, task_id: str) -> Optional[Dict[str, Any]]:
        """加载检查点"""
        import json
        
        checkpoint_path = self.checkpoint_dir / f"{task_id}.checkpoint.json"
        
        if not checkpoint_path.exists():
            return None
        
        try:
            with open(checkpoint_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
    
    def should_auto_save(self) -> bool:
        """检查是否应该自动保存"""
        if not self.last_save_time:
            return True
        
        elapsed = (datetime.now() - self.last_save_time).total_seconds()
        return elapsed >= self.auto_save_interval
    
    def clear_checkpoint(self, task_id: str) -> None:
        """清除检查点"""
        checkpoint_path = self.checkpoint_dir / f"{task_id}.checkpoint.json"
        if checkpoint_path.exists():
            checkpoint_path.unlink()
    
    def list_checkpoints(self) -> List[Dict[str, Any]]:
        """列出所有检查点"""
        import json
        
        checkpoints = []
        for path in self.checkpoint_dir.glob("*.checkpoint.json"):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                checkpoints.append(data)
            except Exception:
                continue
        
        return sorted(checkpoints, key=lambda x: x.get("timestamp", ""), reverse=True)
