"""Phase 3 新模块测试"""

import pytest
import tempfile
import json
from pathlib import Path


class TestCodebaseAnalyzer:
    """测试代码库分析器"""
    
    def test_analyze_current_project(self):
        """分析当前项目"""
        from aop.agent.analyzer import CodebaseAnalyzer
        analyzer = CodebaseAnalyzer()
        info = analyzer.analyze(".")
        
        assert info.language == "python"
        assert info.framework in ["click", "fastapi", "streamlit", None]
        assert len(info.dependencies) > 0
    
    def test_detect_language_python(self, tmp_path):
        """检测 Python 项目"""
        (tmp_path / "main.py").write_text("print('hello')")
        from aop.agent.analyzer import CodebaseAnalyzer
        analyzer = CodebaseAnalyzer()
        assert analyzer.detect_language(tmp_path) == "python"
    
    def test_detect_language_javascript(self, tmp_path):
        """检测 JavaScript 项目"""
        (tmp_path / "index.js").write_text("console.log('hello')")
        from aop.agent.analyzer import CodebaseAnalyzer
        analyzer = CodebaseAnalyzer()
        assert analyzer.detect_language(tmp_path) == "javascript"
    
    def test_detect_framework_fastapi(self, tmp_path):
        """检测 FastAPI 框架"""
        (tmp_path / "requirements.txt").write_text("fastapi\nuvicorn")
        from aop.agent.analyzer import CodebaseAnalyzer
        analyzer = CodebaseAnalyzer()
        assert analyzer.detect_framework(tmp_path) == "fastapi"
    
    def test_find_entry_points(self, tmp_path):
        """查找入口文件"""
        (tmp_path / "main.py").write_text("")
        (tmp_path / "app.py").write_text("")
        from aop.agent.analyzer import CodebaseAnalyzer
        analyzer = CodebaseAnalyzer()
        entries = analyzer.find_entry_points(tmp_path)
        assert "main.py" in entries
        assert "app.py" in entries
    
    def test_detect_patterns_mvc(self, tmp_path):
        """检测 MVC 模式"""
        (tmp_path / "models").mkdir()
        (tmp_path / "views").mkdir()
        from aop.agent.analyzer import CodebaseAnalyzer
        analyzer = CodebaseAnalyzer()
        patterns = analyzer.detect_patterns(tmp_path)
        assert "MVC" in patterns


class TestTaskScheduler:
    """测试任务调度器"""
    
    def test_schedule_single_task(self):
        """调度单个任务"""
        from aop.agent.scheduler import TaskScheduler
        scheduler = TaskScheduler()
        hypotheses = [{"hypothesis_id": "h1", "statement": "test"}]
        assignments = scheduler.schedule(hypotheses)
        
        assert len(assignments) == 1
        assert assignments[0].hypothesis_id == "h1"
    
    def test_schedule_with_priority(self):
        """带优先级调度"""
        from aop.agent.scheduler import TaskScheduler
        scheduler = TaskScheduler()
        hypotheses = [
            {"hypothesis_id": "h1", "priority": "high"},
            {"hypothesis_id": "h2", "priority": "low"},
        ]
        assignments = scheduler.schedule(hypotheses)
        
        assert assignments[0].priority > assignments[1].priority
    
    def test_get_next_batch(self):
        """获取下一批任务"""
        from aop.agent.scheduler import TaskScheduler
        scheduler = TaskScheduler()
        scheduler.schedule([
            {"hypothesis_id": "h1"},
            {"hypothesis_id": "h2"},
        ])
        batch = scheduler.get_next_batch(max_tasks=1)
        
        assert len(batch) == 1
    
    def test_mark_completed(self):
        """标记任务完成"""
        from aop.agent.scheduler import TaskScheduler
        scheduler = TaskScheduler()
        scheduler.schedule([{"hypothesis_id": "h1"}])
        scheduler.mark_completed("task_h1", {"result": "ok"})
        
        assert "task_h1" in scheduler.completed_tasks
    
    def test_mark_failed_with_retry(self):
        """失败重试"""
        from aop.agent.scheduler import TaskScheduler
        scheduler = TaskScheduler()
        scheduler.schedule([{"hypothesis_id": "h1"}])
        
        scheduler.mark_failed("task_h1", "error")
        assert scheduler.assignments["task_h1"].status == "pending"  # 第一次重试
        
        scheduler.mark_failed("task_h1", "error")
        scheduler.mark_failed("task_h1", "error")
        assert scheduler.assignments["task_h1"].status == "failed"  # 超过最大重试
    
    def test_rebalance(self):
        """重新平衡任务"""
        from aop.agent.scheduler import TaskScheduler
        scheduler = TaskScheduler()
        scheduler.schedule([{"hypothesis_id": "h1"}])
        
        old_provider = scheduler.assignments["task_h1"].provider
        scheduler.mark_failed("task_h1", "error")
        scheduler.mark_failed("task_h1", "error")
        scheduler.mark_failed("task_h1", "error")
        scheduler.rebalance()
        
        # 应该换了一个 provider
        assert scheduler.assignments["task_h1"].provider != old_provider
    
    def test_get_statistics(self):
        """获取统计信息"""
        from aop.agent.scheduler import TaskScheduler
        scheduler = TaskScheduler()
        scheduler.schedule([{"hypothesis_id": "h1"}])
        scheduler.mark_completed("task_h1", {})
        
        stats = scheduler.get_statistics()
        assert stats["total"] == 1
        assert stats["completed"] == 1
        assert stats["success_rate"] == 1.0


class TestKnowledgeBase:
    """测试知识库"""
    
    def test_create_learning(self, tmp_path):
        """创建学习经验"""
        from aop.agent.knowledge import KnowledgeBase
        kb = KnowledgeBase(storage_path=str(tmp_path / "kb"))
        
        learning = kb.create_learning(
            pattern="fastapi",
            context={"framework": "fastapi"},
            solution="Use FastAPI",
            tags=["python", "web"],
            project="test"
        )
        
        assert learning.learning_id.startswith("learn_")
        assert learning.pattern == "fastapi"
    
    def test_find_similar(self, tmp_path):
        """查找相似学习"""
        from aop.agent.knowledge import KnowledgeBase
        kb = KnowledgeBase(storage_path=str(tmp_path / "kb"))
        
        kb.create_learning("p1", {"framework": "fastapi"}, "s1")
        kb.create_learning("p2", {"framework": "django"}, "s2")
        
        similar = kb.find_similar({"framework": "fastapi"})
        assert len(similar) >= 1
        assert similar[0].pattern == "p1"
    
    def test_get_by_tag(self, tmp_path):
        """按标签查询"""
        from aop.agent.knowledge import KnowledgeBase
        kb = KnowledgeBase(storage_path=str(tmp_path / "kb"))
        
        kb.create_learning("p1", {}, "s1", tags=["python", "web"])
        kb.create_learning("p2", {}, "s2", tags=["java"])
        
        results = kb.get_by_tag("python")
        assert len(results) == 1
        assert results[0].pattern == "p1"
    
    def test_update_success_rate(self, tmp_path):
        """更新成功率"""
        from aop.agent.knowledge import KnowledgeBase
        kb = KnowledgeBase(storage_path=str(tmp_path / "kb"))
        
        learning = kb.create_learning("p1", {}, "s1")
        kb.update_success_rate(learning.learning_id, True)
        kb.update_success_rate(learning.learning_id, True)
        
        # 两次更新: 0.0 -> 0.1 -> 0.19
        assert kb.get_learning(learning.learning_id).success_rate > 0.1
    
    def test_export_import(self, tmp_path):
        """导出导入"""
        from aop.agent.knowledge import KnowledgeBase
        kb1 = KnowledgeBase(storage_path=str(tmp_path / "kb1"))
        kb1.create_learning("p1", {}, "s1")
        
        export_path = tmp_path / "export.json"
        kb1.export(str(export_path))
        
        kb2 = KnowledgeBase(storage_path=str(tmp_path / "kb2"))
        count = kb2.import_from(str(export_path))
        
        assert count == 1
        assert len(kb2.learnings) == 1


class TestSprintPersistence:
    """测试冲刺持久化"""
    
    def test_save_and_load(self, tmp_path):
        """保存和加载"""
        from aop.agent.persistence import SprintPersistence
        from aop.agent.types import SprintContext, SprintState
        
        persistence = SprintPersistence(storage_path=str(tmp_path / "sprints"))
        context = SprintContext(
            sprint_id="test-123",
            original_input="test input",
            state=SprintState.INITIALIZED,
        )
        
        persistence.save(context)
        loaded = persistence.load("test-123")
        
        assert loaded is not None
        assert loaded.sprint_id == "test-123"
        assert loaded.original_input == "test input"
    
    def test_list_sprints(self, tmp_path):
        """列出冲刺"""
        from aop.agent.persistence import SprintPersistence
        from aop.agent.types import SprintContext, SprintState
        
        persistence = SprintPersistence(storage_path=str(tmp_path / "sprints"))
        persistence.save(SprintContext(sprint_id="s1", original_input="t1", state=SprintState.INITIALIZED))
        persistence.save(SprintContext(sprint_id="s2", original_input="t2", state=SprintState.COMPLETED))
        
        all_sprints = persistence.list_sprints()
        assert len(all_sprints) == 2
        
        completed = persistence.list_sprints(status="completed")
        assert len(completed) == 1
    
    def test_get_latest(self, tmp_path):
        """获取最新冲刺"""
        from aop.agent.persistence import SprintPersistence
        from aop.agent.types import SprintContext, SprintState
        
        persistence = SprintPersistence(storage_path=str(tmp_path / "sprints"))
        persistence.save(SprintContext(sprint_id="s1", original_input="t1", state=SprintState.INITIALIZED))
        
        latest = persistence.get_latest()
        assert latest is not None
        assert latest.sprint_id == "s1"
    
    def test_delete(self, tmp_path):
        """删除冲刺"""
        from aop.agent.persistence import SprintPersistence
        from aop.agent.types import SprintContext, SprintState
        
        persistence = SprintPersistence(storage_path=str(tmp_path / "sprints"))
        persistence.save(SprintContext(sprint_id="s1", original_input="t1", state=SprintState.INITIALIZED))
        
        assert persistence.delete("s1") is True
        assert persistence.load("s1") is None
    
    def test_archive(self, tmp_path):
        """归档冲刺"""
        from aop.agent.persistence import SprintPersistence
        from aop.agent.types import SprintContext, SprintState
        
        persistence = SprintPersistence(storage_path=str(tmp_path / "sprints"))
        persistence.save(SprintContext(sprint_id="s1", original_input="t1", state=SprintState.COMPLETED))
        
        assert persistence.archive("s1") is True
        assert persistence.load("s1") is None  # 已移到归档

