"""测试 KnowledgeBase - 跨项目知识库"""

import json
import pytest
import tempfile
from pathlib import Path

from aop.agent.knowledge import KnowledgeBase, SharedLearning


class TestSharedLearning:
    """测试 SharedLearning"""

    def test_create_learning(self):
        """测试创建学习经验"""
        learning = SharedLearning(
            learning_id="learn_001",
            pattern="单元测试模式",
            context={"language": "Python", "framework": "pytest"},
            solution="使用 mock 对象隔离依赖"
        )

        assert learning.learning_id == "learn_001"
        assert learning.pattern == "单元测试模式"
        assert learning.success_rate == 0.0
        assert learning.created_at != ""

    def test_auto_generate_id(self):
        """测试自动生成 ID"""
        learning = SharedLearning(
            learning_id="",
            pattern="测试模式",
            context={},
            solution="测试方案"
        )

        assert learning.learning_id.startswith("learn_")

    def test_matches_context(self):
        """测试上下文匹配"""
        learning = SharedLearning(
            learning_id="learn_001",
            pattern="测试模式",
            context={"language": "Python", "framework": "pytest"},
            solution="测试方案"
        )

        # 完全匹配
        score = learning.matches_context({"language": "Python", "framework": "pytest"})
        assert score == 1.0

        # 部分匹配 - 查询中有1个键匹配，总共1个键，所以是100%
        score = learning.matches_context({"language": "Python"})
        assert score == 1.0

        # 不匹配 - 查询的键存在于 learning，但值不同
        score = learning.matches_context({"language": "JavaScript"})
        assert score == 0.0

        # 额外键 - 匹配1个，总共2个键，所以是50%
        score = learning.matches_context({"language": "Python", "extra": "value"})
        assert score == 0.5

    def test_to_dict_from_dict(self):
        """测试序列化"""
        learning = SharedLearning(
            learning_id="learn_001",
            pattern="测试模式",
            context={"language": "Python"},
            solution="测试方案",
            success_rate=0.8,
            tags=["test", "python"]
        )

        data = learning.to_dict()
        assert data["learning_id"] == "learn_001"
        assert data["success_rate"] == 0.8

        learning2 = SharedLearning.from_dict(data)
        assert learning2.learning_id == learning.learning_id
        assert learning2.pattern == learning.pattern


class TestKnowledgeBase:
    """测试 KnowledgeBase"""

    @pytest.fixture
    def temp_storage(self, tmp_path):
        """创建临时存储目录"""
        return str(tmp_path / "knowledge")

    def test_create_knowledge_base(self, temp_storage):
        """测试创建知识库"""
        kb = KnowledgeBase(storage_path=temp_storage)

        assert kb.storage_path.exists()
        assert len(kb.learnings) == 0

    def test_add_learning(self, temp_storage):
        """测试添加学习经验"""
        kb = KnowledgeBase(storage_path=temp_storage)

        learning = kb.create_learning(
            pattern="单元测试模式",
            context={"language": "Python"},
            solution="使用 mock 隔离依赖",
            tags=["test", "python"],
            project="myproject"
        )

        assert learning.learning_id in kb.learnings
        assert len(kb.learnings) == 1

    def test_get_learning(self, temp_storage):
        """测试获取学习经验"""
        kb = KnowledgeBase(storage_path=temp_storage)

        learning = kb.create_learning(
            pattern="测试模式",
            context={"language": "Python"},
            solution="测试方案"
        )

        retrieved = kb.get_learning(learning.learning_id)
        assert retrieved is not None
        assert retrieved.pattern == "测试模式"

    def test_find_similar(self, temp_storage):
        """测试查找相似经验"""
        kb = KnowledgeBase(storage_path=temp_storage)

        # 添加多个学习经验
        kb.create_learning(
            pattern="Python 单元测试",
            context={"language": "Python", "type": "unit"},
            solution="使用 pytest",
            tags=["test"]
        )
        kb.create_learning(
            pattern="JavaScript 单元测试",
            context={"language": "JavaScript", "type": "unit"},
            solution="使用 Jest",
            tags=["test"]
        )

        # 查找 Python 相关
        similar = kb.find_similar({"language": "Python", "type": "unit"})
        assert len(similar) >= 1
        assert similar[0].pattern == "Python 单元测试"

    def test_get_patterns_for(self, temp_storage):
        """测试按标签获取模式"""
        kb = KnowledgeBase(storage_path=temp_storage)

        kb.create_learning(
            pattern="模式1",
            context={},
            solution="方案1",
            tags=["testing", "python"]
        )
        kb.create_learning(
            pattern="模式2",
            context={},
            solution="方案2",
            tags=["testing", "javascript"]
        )

        patterns = kb.get_patterns_for("testing")
        assert len(patterns) == 2

    def test_get_by_project(self, temp_storage):
        """测试按项目获取"""
        kb = KnowledgeBase(storage_path=temp_storage)

        kb.create_learning(
            pattern="模式1",
            context={},
            solution="方案1",
            project="project_a"
        )
        kb.create_learning(
            pattern="模式2",
            context={},
            solution="方案2",
            project="project_b"
        )

        learnings = kb.get_by_project("project_a")
        assert len(learnings) == 1
        assert learnings[0].pattern == "模式1"

    def test_update_success_rate(self, temp_storage):
        """测试更新成功率"""
        kb = KnowledgeBase(storage_path=temp_storage)

        learning = kb.create_learning(
            pattern="测试模式",
            context={},
            solution="测试方案"
        )

        # 初始成功率 0
        assert learning.success_rate == 0.0

        # 更新成功
        kb.update_success_rate(learning.learning_id, True)
        assert kb.learnings[learning.learning_id].success_rate > 0

        # 再次成功
        kb.update_success_rate(learning.learning_id, True)
        assert kb.learnings[learning.learning_id].success_rate > 0.1

    def test_export_import(self, temp_storage):
        """测试导出导入"""
        kb = KnowledgeBase(storage_path=temp_storage)

        # 添加学习经验
        kb.create_learning(
            pattern="模式1",
            context={"language": "Python"},
            solution="方案1"
        )

        # 导出
        export_path = Path(temp_storage) / "export.json"
        kb.export(str(export_path))

        assert export_path.exists()

        # 创建新知识库并导入
        kb2 = KnowledgeBase(storage_path=temp_storage + "2")
        count = kb2.import_from(str(export_path))

        assert count == 1
        assert len(kb2.learnings) == 1

    def test_persistence(self, temp_storage):
        """测试持久化"""
        kb = KnowledgeBase(storage_path=temp_storage)

        # 添加学习经验
        learning = kb.create_learning(
            pattern="持久化测试",
            context={},
            solution="测试方案"
        )

        # 创建新实例，应该从文件加载
        kb2 = KnowledgeBase(storage_path=temp_storage)
        assert learning.learning_id in kb2.learnings

    def test_get_statistics(self, temp_storage):
        """测试统计信息"""
        kb = KnowledgeBase(storage_path=temp_storage)

        kb.create_learning("模式1", {}, "方案1")
        kb.create_learning("模式2", {}, "方案2")

        stats = kb.get_statistics()

        assert stats["total"] == 2
        assert stats["avg_success_rate"] == 0.0
