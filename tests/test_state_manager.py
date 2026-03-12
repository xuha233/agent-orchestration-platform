"""
StateManager 单元测试

测试 STATE.md 跨会话记忆功能。
"""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime

from aop.state import StateManager


class TestStateManagerInit:
    """测试初始化"""
    
    def test_init_creates_manager(self):
        """测试创建管理器"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StateManager(project_path=Path(tmpdir))
            assert manager.project_path == Path(tmpdir)
            assert manager.session_id.startswith("session-")
    
    def test_init_with_custom_session_id(self):
        """测试使用自定义会话ID"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StateManager(
                project_path=Path(tmpdir),
                session_id="custom-session"
            )
            assert manager.session_id == "custom-session"


class TestStateManagerLoadSave:
    """测试加载和保存"""
    
    def test_load_creates_default_state(self):
        """测试加载时创建默认状态"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StateManager(project_path=Path(tmpdir))
            state = manager.load()
            
            assert state.current_task == "无"
            assert state.last_action == "无"
            assert state.next_step == "待确定"
            assert state.hypotheses == []
            assert state.decisions == []
            assert state.blockers == []
            assert state.learnings == []
    
    def test_save_and_load(self):
        """测试保存后重新加载"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StateManager(project_path=Path(tmpdir))
            
            # 更新状态
            manager.update_task(
                task="测试任务",
                action="测试行动",
                next_step="测试下一步"
            )
            
            # 重新加载
            manager2 = StateManager(project_path=Path(tmpdir))
            state = manager2.load()
            
            assert state.current_task == "测试任务"
            assert state.last_action == "测试行动"
            assert state.next_step == "测试下一步"
    
    def test_state_file_format(self):
        """测试 STATE.md 文件格式"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StateManager(project_path=Path(tmpdir))
            manager.update_task(
                task="测试任务",
                action="测试行动",
                next_step="测试下一步"
            )
            
            # 读取文件内容
            state_file = Path(tmpdir) / ".aop" / "STATE.md"
            assert state_file.exists()
            
            content = state_file.read_text(encoding="utf-8")
            assert "# STATE.md" in content
            assert "测试任务" in content
            assert "测试行动" in content
            assert "测试下一步" in content


class TestStateManagerTask:
    """测试任务更新"""
    
    def test_update_task(self):
        """测试更新任务"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StateManager(project_path=Path(tmpdir))
            manager.update_task(
                task="实现用户认证",
                action="完成登录 API",
                next_step="添加密码重置"
            )
            
            state = manager.load()
            assert state.current_task == "实现用户认证"
            assert state.last_action == "完成登录 API"
            assert state.next_step == "添加密码重置"
    
    def test_update_task_multiple_times(self):
        """测试多次更新任务"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StateManager(project_path=Path(tmpdir))
            
            manager.update_task(task="任务1", action="行动1", next_step="步骤1")
            manager.update_task(task="任务2", action="行动2", next_step="步骤2")
            
            state = manager.load()
            assert state.current_task == "任务2"
            assert state.last_action == "行动2"
            assert state.next_step == "步骤2"


class TestStateManagerDecisions:
    """测试决策记录"""
    
    def test_add_decision(self):
        """测试添加决策"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StateManager(project_path=Path(tmpdir))
            manager.add_decision(
                decision="使用 JWT 认证",
                reason="无状态，易扩展"
            )
            
            state = manager.load()
            assert len(state.decisions) == 1
            assert state.decisions[0]["decision"] == "使用 JWT 认证"
            assert state.decisions[0]["reason"] == "无状态，易扩展"
    
    def test_add_multiple_decisions(self):
        """测试添加多个决策"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StateManager(project_path=Path(tmpdir))
            
            manager.add_decision("决策1", "原因1")
            manager.add_decision("决策2", "原因2")
            manager.add_decision("决策3", "原因3")
            
            state = manager.load()
            assert len(state.decisions) == 3
    
    def test_decision_has_date(self):
        """测试决策包含日期"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StateManager(project_path=Path(tmpdir))
            manager.add_decision("测试决策", "测试原因")
            
            state = manager.load()
            assert "date" in state.decisions[0]
            # 日期格式: YYYY-MM-DD
            assert len(state.decisions[0]["date"]) == 10


class TestStateManagerHypotheses:
    """测试假设管理"""
    
    def test_add_hypothesis(self):
        """测试添加假设"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StateManager(project_path=Path(tmpdir))
            
            h_id = manager.add_hypothesis(
                statement="用户需要快速登录",
                validation_method="A/B 测试",
                priority="high"
            )
            
            assert h_id.startswith("H-")
            
            state = manager.load()
            assert len(state.hypotheses) == 1
            assert state.hypotheses[0]["statement"] == "用户需要快速登录"
    
    def test_update_hypothesis_status(self):
        """测试更新假设状态"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StateManager(project_path=Path(tmpdir))
            
            h_id = manager.add_hypothesis("测试假设")
            manager.update_hypothesis(h_id, "validated", "验证通过")
            
            state = manager.load()
            h = next(h for h in state.hypotheses if h["hypothesis_id"] == h_id)
            assert h["state"] == "validated"
            assert h["result"] == "验证通过"
    
    def test_get_active_hypotheses(self):
        """测试获取活跃假设"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StateManager(project_path=Path(tmpdir))
            
            h1 = manager.add_hypothesis("假设1")
            h2 = manager.add_hypothesis("假设2")
            h3 = manager.add_hypothesis("假设3")
            
            manager.update_hypothesis(h1, "validated")
            manager.update_hypothesis(h2, "rejected")
            # h3 保持 pending
            
            active = manager.get_active_hypotheses()
            assert len(active) == 1
            assert active[0]["hypothesis_id"] == h3


class TestStateManagerBlockers:
    """测试阻塞项管理"""
    
    def test_add_blocker(self):
        """测试添加阻塞项"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StateManager(project_path=Path(tmpdir))
            manager.add_blocker("等待 API Key")
            
            state = manager.load()
            assert len(state.blockers) == 1
            assert state.blockers[0]["blocker"] == "等待 API Key"
            assert state.blockers[0]["resolved"] == False
    
    def test_resolve_blocker(self):
        """测试解决阻塞项"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StateManager(project_path=Path(tmpdir))
            
            manager.add_blocker("等待 API Key")
            manager.resolve_blocker("等待 API Key")
            
            state = manager.load()
            assert state.blockers[0]["resolved"] == True
            assert state.blockers[0]["resolved_at"] != ""
    
    def test_get_active_blockers(self):
        """测试获取活跃阻塞项"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StateManager(project_path=Path(tmpdir))
            
            manager.add_blocker("阻塞项1")
            manager.add_blocker("阻塞项2")
            manager.resolve_blocker("阻塞项1")
            
            active = manager.get_active_blockers()
            assert len(active) == 1
            assert active[0]["blocker"] == "阻塞项2"
    
    def test_no_duplicate_blockers(self):
        """测试不添加重复阻塞项"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StateManager(project_path=Path(tmpdir))
            
            manager.add_blocker("相同的阻塞")
            manager.add_blocker("相同的阻塞")
            
            state = manager.load()
            assert len(state.blockers) == 1


class TestStateManagerLearnings:
    """测试学习笔记"""
    
    def test_add_learning(self):
        """测试添加学习笔记"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StateManager(project_path=Path(tmpdir))
            manager.add_learning(
                learning="用户更喜欢简洁界面",
                category="用户体验",
                source="用户访谈"
            )
            
            state = manager.load()
            assert len(state.learnings) == 1
            assert state.learnings[0]["content"] == "用户更喜欢简洁界面"
            assert state.learnings[0]["category"] == "用户体验"
            assert state.learnings[0]["source"] == "用户访谈"
    
    def test_add_multiple_learnings(self):
        """测试添加多个学习笔记"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StateManager(project_path=Path(tmpdir))
            
            manager.add_learning("学习1", "技术", "开发")
            manager.add_learning("学习2", "产品", "调研")
            manager.add_learning("学习3", "流程", "复盘")
            
            state = manager.load()
            assert len(state.learnings) == 3


class TestStateManagerContextSummary:
    """测试上下文摘要生成"""
    
    def test_get_context_summary_basic(self):
        """测试基本上下文摘要"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StateManager(project_path=Path(tmpdir))
            manager.update_task(
                task="开发功能",
                action="完成编码",
                next_step="进行测试"
            )
            
            summary = manager.get_context_summary()
            
            assert "开发功能" in summary
            assert "完成编码" in summary
            assert "进行测试" in summary
    
    def test_get_context_summary_with_blockers(self):
        """测试包含阻塞项的摘要"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StateManager(project_path=Path(tmpdir))
            manager.add_blocker("等待资源")
            
            summary = manager.get_context_summary()
            
            assert "阻塞项" in summary
            assert "等待资源" in summary
    
    def test_get_context_summary_with_hypotheses(self):
        """测试包含假设的摘要"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StateManager(project_path=Path(tmpdir))
            manager.add_hypothesis("用户需要 X 功能")
            
            summary = manager.get_context_summary()
            
            assert "活跃假设" in summary
            assert "用户需要 X 功能"[:30] in summary
    
    def test_get_context_summary_max_length(self):
        """测试摘要长度限制"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StateManager(project_path=Path(tmpdir))
            
            # 添加大量内容
            for i in range(50):
                manager.add_decision(f"决策 {i}" * 10, f"原因 {i}" * 10)
            
            summary = manager.get_context_summary(max_length=500)
            
            assert len(summary) <= 503  # max_length + "..."


class TestStateManagerSync:
    """测试与 hypotheses.json 同步"""
    
    def test_sync_loads_from_hypotheses_json(self):
        """测试从 hypotheses.json 同步"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建 hypotheses.json
            import json
            aop_dir = Path(tmpdir) / ".aop"
            aop_dir.mkdir(parents=True, exist_ok=True)
            
            hypotheses_data = {
                "_meta": {"version": 1},
                "data": {
                    "H-TEST123": {
                        "hypothesis_id": "H-TEST123",
                        "statement": "测试假设",
                        "state": "pending",
                        "validation_method": "测试方法",
                        "priority": "high"
                    }
                }
            }
            
            with open(aop_dir / "hypotheses.json", "w", encoding="utf-8") as f:
                json.dump(hypotheses_data, f)
            
            # 加载状态
            manager = StateManager(project_path=Path(tmpdir))
            state = manager.load()
            
            assert len(state.hypotheses) == 1
            assert state.hypotheses[0]["hypothesis_id"] == "H-TEST123"
            assert state.hypotheses[0]["statement"] == "测试假设"
