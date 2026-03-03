"""
动态超时管理器
允许 Agent 在运行时申请延长超时
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, Optional
from enum import Enum


class ExtensionRequestStatus(Enum):
    """延长请求状态"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass
class TimeoutExtensionRequest:
    """超时延长请求"""
    request_id: str
    current_task_id: str
    requested_seconds: int
    reason: str
    progress_summary: str  # 当前进度摘要
    status: ExtensionRequestStatus = ExtensionRequestStatus.PENDING
    created_at: float = field(default_factory=time.time)
    decided_at: Optional[float] = None


@dataclass
class TimeoutState:
    """超时状态"""
    started_at: float
    original_timeout: int
    extended_seconds: int = 0
    extension_requests: list[TimeoutExtensionRequest] = field(default_factory=list)
    max_extensions: int = 3
    max_total_extension: int = 1800  # 最大延长 30 分钟


class TimeoutManager:
    """动态超时管理器"""
    
    def __init__(
        self,
        original_timeout: int = 600,
        max_extensions: int = 3,
        max_total_extension: int = 1800,
        on_extension_request: Optional[Callable[[TimeoutExtensionRequest], bool]] = None,
    ):
        self.state = TimeoutState(
            started_at=time.time(),
            original_timeout=original_timeout,
            max_extensions=max_extensions,
            max_total_extension=max_total_extension,
        )
        self.on_extension_request = on_extension_request
        self._request_counter = 0
    
    def get_remaining_seconds(self) -> int:
        """获取剩余秒数"""
        elapsed = time.time() - self.state.started_at
        total_allowed = self.state.original_timeout + self.state.extended_seconds
        remaining = total_allowed - elapsed
        return max(0, int(remaining))
    
    def get_elapsed_seconds(self) -> int:
        """获取已用秒数"""
        return int(time.time() - self.state.started_at)
    
    def get_progress_percent(self) -> float:
        """获取进度百分比"""
        elapsed = time.time() - self.state.started_at
        total_allowed = self.state.original_timeout + self.state.extended_seconds
        return min(100.0, (elapsed / total_allowed) * 100)
    
    def is_timeout_imminent(self, threshold_seconds: int = 60) -> bool:
        """检查是否即将超时"""
        return self.get_remaining_seconds() <= threshold_seconds
    
    def request_extension(
        self,
        task_id: str,
        requested_seconds: int,
        reason: str,
        progress_summary: str,
    ) -> TimeoutExtensionRequest:
        """申请延长超时
        
        Args:
            task_id: 任务 ID
            requested_seconds: 请求延长的秒数
            reason: 延长原因
            progress_summary: 当前进度摘要
            
        Returns:
            TimeoutExtensionRequest: 延长请求对象
        """
        self._request_counter += 1
        request = TimeoutExtensionRequest(
            request_id=f"ext_{self._request_counter}",
            current_task_id=task_id,
            requested_seconds=requested_seconds,
            reason=reason,
            progress_summary=progress_summary,
        )
        
        # 检查是否可以延长
        can_extend = self._check_can_extend(request)
        
        if can_extend:
            # 如果有回调，让用户/主 Agent 决定
            if self.on_extension_request:
                approved = self.on_extension_request(request)
            else:
                # 默认自动批准
                approved = True
            
            if approved:
                request.status = ExtensionRequestStatus.APPROVED
                self.state.extended_seconds += requested_seconds
            else:
                request.status = ExtensionRequestStatus.REJECTED
        else:
            request.status = ExtensionRequestStatus.REJECTED
        
        request.decided_at = time.time()
        self.state.extension_requests.append(request)
        return request
    
    def _check_can_extend(self, request: TimeoutExtensionRequest) -> bool:
        """检查是否可以延长"""
        # 检查延长次数
        approved_count = sum(
            1 for r in self.state.extension_requests
            if r.status == ExtensionRequestStatus.APPROVED
        )
        if approved_count >= self.state.max_extensions:
            request.reason = f"已达到最大延长次数 ({self.state.max_extensions})"
            return False
        
        # 检查总延长时间
        potential_total = self.state.extended_seconds + request.requested_seconds
        if potential_total > self.state.max_total_extension:
            request.reason = f"总延长时间将超过最大限制 ({self.state.max_total_extension}s)"
            return False
        
        return True
    
    def get_status_report(self) -> dict:
        """获取状态报告"""
        return {
            "elapsed_seconds": self.get_elapsed_seconds(),
            "remaining_seconds": self.get_remaining_seconds(),
            "original_timeout": self.state.original_timeout,
            "extended_seconds": self.state.extended_seconds,
            "progress_percent": self.get_progress_percent(),
            "extension_count": len(self.state.extension_requests),
            "approved_extensions": sum(
                1 for r in self.state.extension_requests
                if r.status == ExtensionRequestStatus.APPROVED
            ),
        }
