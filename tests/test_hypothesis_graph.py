"""测试 HypothesisGraph - 假设依赖关系管理"""

import pytest
from aop.workflow.hypothesis.graph import HypothesisGraph, HypothesisNode


class TestHypothesisGraph:
    """测试 HypothesisGraph"""

    def test_add_node(self):
        """测试添加节点"""
        graph = HypothesisGraph()
        graph.add_node(
            hypothesis_id="H-001",
            statement="测试假设1",
            estimated_effort="low",
            risk_level="medium"
        )

        assert len(graph) == 1
        assert "H-001" in graph
        node = graph.get_node("H-001")
        assert node is not None
        assert node.statement == "测试假设1"
        assert node.estimated_effort == "low"
        assert node.state == "pending"

    def test_add_dependency(self):
        """测试添加依赖关系"""
        graph = HypothesisGraph()
        graph.add_node("H-001", "假设1")
        graph.add_node("H-002", "假设2")
        graph.add_dependency("H-002", "H-001")  # H-002 依赖 H-001

        node1 = graph.get_node("H-001")
        node2 = graph.get_node("H-002")

        assert "H-001" in node2.dependencies
        assert "H-002" in node1.dependents

    def test_get_execution_order_no_deps(self):
        """测试无依赖时的执行顺序"""
        graph = HypothesisGraph()
        graph.add_node("H-001", "假设1")
        graph.add_node("H-002", "假设2")
        graph.add_node("H-003", "假设3")

        order = graph.get_execution_order()

        # 无依赖，所有节点应该在第一批
        assert len(order) == 1
        assert len(order[0]) == 3
        assert "H-001" in order[0]
        assert "H-002" in order[0]
        assert "H-003" in order[0]

    def test_get_execution_order_linear_deps(self):
        """测试线性依赖的执行顺序"""
        graph = HypothesisGraph()
        graph.add_node("H-001", "假设1")
        graph.add_node("H-002", "假设2", dependencies=["H-001"])
        graph.add_node("H-003", "假设3", dependencies=["H-002"])

        order = graph.get_execution_order()

        # H-001 -> H-002 -> H-003
        assert len(order) == 3
        assert order[0] == ["H-001"]
        assert order[1] == ["H-002"]
        assert order[2] == ["H-003"]

    def test_get_execution_order_complex(self):
        """测试复杂依赖的执行顺序"""
        graph = HypothesisGraph()
        # H-001, H-002 无依赖
        # H-003 依赖 H-001, H-002
        # H-004 依赖 H-003
        graph.add_node("H-001", "假设1")
        graph.add_node("H-002", "假设2")
        graph.add_node("H-003", "假设3", dependencies=["H-001", "H-002"])
        graph.add_node("H-004", "假设4", dependencies=["H-003"])

        order = graph.get_execution_order()

        # 批次1: H-001, H-002 可并行
        # 批次2: H-003
        # 批次3: H-004
        assert len(order) == 3
        assert set(order[0]) == {"H-001", "H-002"}
        assert order[1] == ["H-003"]
        assert order[2] == ["H-004"]

    def test_detect_cycles_no_cycle(self):
        """测试无环检测"""
        graph = HypothesisGraph()
        graph.add_node("H-001", "假设1")
        graph.add_node("H-002", "假设2", dependencies=["H-001"])

        cycles = graph.detect_cycles()
        assert cycles == []

    def test_detect_cycles_with_cycle(self):
        """测试环检测"""
        graph = HypothesisGraph()
        graph.add_node("H-001", "假设1", dependencies=["H-003"])
        graph.add_node("H-002", "假设2", dependencies=["H-001"])
        graph.add_node("H-003", "假设3", dependencies=["H-002"])

        cycles = graph.detect_cycles()
        assert len(cycles) > 0

    def test_get_execution_order_raises_on_cycle(self):
        """测试循环依赖时抛出异常"""
        graph = HypothesisGraph()
        graph.add_node("H-001", "假设1", dependencies=["H-003"])
        graph.add_node("H-002", "假设2", dependencies=["H-001"])
        graph.add_node("H-003", "假设3", dependencies=["H-002"])

        with pytest.raises(ValueError, match="Circular dependency"):
            graph.get_execution_order()

    def test_get_ready_hypotheses(self):
        """测试获取可执行的假设"""
        graph = HypothesisGraph()
        graph.add_node("H-001", "假设1")
        graph.add_node("H-002", "假设2")
        graph.add_node("H-003", "假设3", dependencies=["H-001", "H-002"])

        # 无已完成，H-001 和 H-002 可执行
        ready = graph.get_ready_hypotheses(set())
        assert set(ready) == {"H-001", "H-002"}

        # H-001 完成后，H-002 可执行
        ready = graph.get_ready_hypotheses({"H-001"})
        assert ready == ["H-002"]

        # H-001 和 H-002 都完成后，H-003 可执行
        ready = graph.get_ready_hypotheses({"H-001", "H-002"})
        assert ready == ["H-003"]

    def test_remove_node(self):
        """测试移除节点"""
        graph = HypothesisGraph()
        graph.add_node("H-001", "假设1")
        graph.add_node("H-002", "假设2", dependencies=["H-001"])

        # 移除 H-001
        result = graph.remove_node("H-001")

        assert result is True
        assert "H-001" not in graph
        node2 = graph.get_node("H-002")
        assert "H-001" not in node2.dependencies

    def test_serialization(self):
        """测试序列化和反序列化"""
        graph = HypothesisGraph()
        graph.add_node("H-001", "假设1", estimated_effort="low")
        graph.add_node("H-002", "假设2", dependencies=["H-001"])

        # 序列化
        data = graph.to_dict()
        assert "nodes" in data
        assert "H-001" in data["nodes"]
        assert "H-002" in data["nodes"]

        # 反序列化
        graph2 = HypothesisGraph.from_dict(data)
        assert len(graph2) == 2
        assert "H-001" in graph2
        node2 = graph2.get_node("H-002")
        assert node2.dependencies == ["H-001"]

    def test_get_statistics(self):
        """测试统计信息"""
        graph = HypothesisGraph()
        graph.add_node("H-001", "假设1", state="verified")
        graph.add_node("H-002", "假设2", state="pending")
        graph.add_node("H-003", "假设3", state="pending", dependencies=["H-001"])

        stats = graph.get_statistics()

        assert stats["total_nodes"] == 3
        assert stats["total_dependencies"] == 1
        assert stats["state_distribution"]["verified"] == 1
        assert stats["state_distribution"]["pending"] == 2


class TestHypothesisNode:
    """测试 HypothesisNode"""

    def test_to_dict(self):
        """测试节点转字典"""
        node = HypothesisNode(
            hypothesis_id="H-001",
            statement="测试假设",
            dependencies=["H-000"],
            estimated_effort="high",
            risk_level="low",
            state="in_progress"
        )

        data = node.to_dict()

        assert data["hypothesis_id"] == "H-001"
        assert data["statement"] == "测试假设"
        assert data["dependencies"] == ["H-000"]
        assert data["estimated_effort"] == "high"
        assert data["risk_level"] == "low"
        assert data["state"] == "in_progress"

    def test_from_dict(self):
        """测试从字典创建节点"""
        data = {
            "hypothesis_id": "H-001",
            "statement": "测试假设",
            "dependencies": ["H-000"],
            "dependents": ["H-002"],
            "estimated_effort": "high",
            "risk_level": "low",
            "state": "verified"
        }

        node = HypothesisNode.from_dict(data)

        assert node.hypothesis_id == "H-001"
        assert node.statement == "测试假设"
        assert node.dependencies == ["H-000"]
        assert node.dependents == ["H-002"]
        assert node.estimated_effort == "high"
        assert node.state == "verified"
