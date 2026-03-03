"""测试动态超时管理器"""

import time
import pytest
from aop.agent.timeout_manager import (
    TimeoutManager,
    TimeoutExtensionRequest,
    ExtensionRequestStatus,
)


class TestTimeoutManager:
    """测试 TimeoutManager"""
    
    def test_initial_state(self):
        """测试初始状态"""
        manager = TimeoutManager(original_timeout=600)
        
        assert manager.state.original_timeout == 600
        assert manager.state.extended_seconds == 0
        assert manager.get_remaining_seconds() > 500  # 刚开始，剩余时间接近 600
        assert manager.get_elapsed_seconds() < 10  # 刚开始，已用时间很短
    
    def test_elapsed_time(self):
        """测试时间流逝"""
        manager = TimeoutManager(original_timeout=600)
        
        time.sleep(1)
        assert manager.get_elapsed_seconds() >= 1
        assert manager.get_remaining_seconds() <= 600
    
    def test_is_timeout_imminent(self):
        """测试超时预警"""
        manager = TimeoutManager(original_timeout=5)  # 5 秒超时
        
        # 刚开始不应该预警
        assert not manager.is_timeout_imminent(threshold_seconds=1)
        
        time.sleep(4)
        # 等待 4 秒后，剩余时间 < 2 秒，应该预警
        assert manager.is_timeout_imminent(threshold_seconds=2)
    
    def test_request_extension_approved(self):
        """测试延长超时（批准）"""
        manager = TimeoutManager(original_timeout=600)
        
        request = manager.request_extension(
            task_id="task_001",
            requested_seconds=300,
            reason="任务复杂，需要更多时间",
            progress_summary="已完成 50%，剩余工作量较大",
        )
        
        assert request.status == ExtensionRequestStatus.APPROVED
        assert manager.state.extended_seconds == 300
        assert manager.get_remaining_seconds() > 600
    
    def test_request_extension_with_callback(self):
        """测试延长超时（回调决定）"""
        decisions = []
        
        def on_request(req: TimeoutExtensionRequest) -> bool:
            decisions.append(req.requested_seconds)
            return req.requested_seconds <= 300  # 只批准 <= 300 秒的请求
        
        manager = TimeoutManager(
            original_timeout=600,
            on_extension_request=on_request,
        )
        
        # 批准 300 秒
        req1 = manager.request_extension(
            task_id="task_001",
            requested_seconds=300,
            reason="需要更多时间",
            progress_summary="进度 50%",
        )
        assert req1.status == ExtensionRequestStatus.APPROVED
        
        # 拒绝 600 秒
        req2 = manager.request_extension(
            task_id="task_001",
            requested_seconds=600,
            reason="需要更多更多时间",
            progress_summary="进度 80%",
        )
        assert req2.status == ExtensionRequestStatus.REJECTED
    
    def test_max_extensions_limit(self):
        """测试最大延长次数限制"""
        manager = TimeoutManager(
            original_timeout=600,
            max_extensions=2,
        )
        
        # 第一次延长
        req1 = manager.request_extension("task_001", 300, "原因1", "进度1")
        assert req1.status == ExtensionRequestStatus.APPROVED
        
        # 第二次延长
        req2 = manager.request_extension("task_001", 300, "原因2", "进度2")
        assert req2.status == ExtensionRequestStatus.APPROVED
        
        # 第三次延长（超过限制）
        req3 = manager.request_extension("task_001", 300, "原因3", "进度3")
        assert req3.status == ExtensionRequestStatus.REJECTED
    
    def test_max_total_extension_limit(self):
        """测试最大总延长时间限制"""
        manager = TimeoutManager(
            original_timeout=600,
            max_total_extension=500,  # 最大延长 500 秒
        )
        
        # 延长 300 秒（成功）
        req1 = manager.request_extension("task_001", 300, "原因1", "进度1")
        assert req1.status == ExtensionRequestStatus.APPROVED
        
        # 再延长 300 秒（超过总限制）
        req2 = manager.request_extension("task_001", 300, "原因2", "进度2")
        assert req2.status == ExtensionRequestStatus.REJECTED
    
    def test_get_status_report(self):
        """测试状态报告"""
        manager = TimeoutManager(original_timeout=600)
        
        report = manager.get_status_report()
        
        assert report["original_timeout"] == 600
        assert report["extended_seconds"] == 0
        assert report["extension_count"] == 0
        
        # 延长后
        manager.request_extension("task_001", 300, "原因", "进度")
        report = manager.get_status_report()
        
        assert report["extended_seconds"] == 300
        assert report["extension_count"] == 1
        assert report["approved_extensions"] == 1
