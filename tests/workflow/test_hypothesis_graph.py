"""
测试 HypothesisGraph - 假设依赖关系管理

测试假设图的核心功能：
- 节点添加和依赖关系
- 拓扑排序和执行顺序
- 循环依赖检测
- 序列化和反序列化
"""

from __future__ import annotations

import pytest

from aop.workflow.hypothesis.graph import HypothesisGraph, HypothesisNode


class TestHypothesisNode:
    """测试 HypothesisNode 数据类"""

    def test_create_node_with_defaults(self) -> None:
        """测试创建带默认值的节点"""
        node = HypothesisNode(
            hypothesis_id="h1",
            statement="测试假设",
        )

        assert node.hypothesis_id == "h1"
        assert node.statement == "测试假设"
        assert node.dependencies == []
        assert node.dependents == []
        assert node.estimated_effort == "medium"
        assert node.risk_level == "medium"
        assert node.state == "pending"

    def test_create_node_with_custom_values(self) -> None:
        """测试创建带自定义值的节点"""
        node = HypothesisNode(
            hypothesis_id="h2",
            statement="复杂假设",
            dependencies=["h1"],
            dependents=["h3"],
            estimated_effort="high",
            risk_level="high",
            state="in_progress",
        )

        assert node.hypothesis_id == "h2"
        assert node.dependencies == ["h1"]
        assert node.dependents == ["h3"]
        assert node.estimated_effort == "high"
        assert node.risk_level == "high"
        assert node.state == "in_progress"

    def test_node_to_dict(self) -> None:
        """测试节点转换为字典"""
        node = HypothesisNode(
            hypothesis_id="h1",
            statement="测试假设",
            dependencies=["h0"],
            dependents=["h2"],
        )

        result = node.to_dict()

        assert result["hypothesis_id"] == "h1"
        assert result["statement"] == "测试假设"
        assert result["dependencies"] == ["h0"]
        assert result["dependents"] == ["h2"]
        assert result["estimated_effort"] == "medium"
        assert result["risk_level"] == "medium"
        assert result["state"] == "pending"

    def test_node_from_dict(self) -> None:
        """测试从字典创建节点"""
        data = {
            "hypothesis_id": "h1",
            "statement": "测试假设",
            "dependencies": ["h0"],
            "dependents": ["h2"],
            "estimated_effort": "low",
            "risk_level": "low",
            "state": "verified",
        }

        node = HypothesisNode.from_dict(data)

        assert node.hypothesis_id == "h1"
        assert node.statement == "测试假设"
        assert node.dependencies == ["h0"]
        assert node.dependents == ["h2"]
        assert node.estimated_effort == "low"
        assert node.risk_level == "low"
        assert node.state == "verified"


class TestHypothesisGraphBasic:
    """测试 HypothesisGraph 基础功能"""

    def test_create_empty_graph(self) -> None:
        """测试创建空图"""
        graph = HypothesisGraph()

        assert len(graph) == 0
        assert "h1" not in graph
        assert repr(graph) == "HypothesisGraph(nodes=0)"

    def test_add_single_node(self) -> None:
        """测试添加单个节点"""
        graph = HypothesisGraph()

        graph.add_node("h1", "第一个假设")

        assert len(graph) == 1
        assert "h1" in graph

        node = graph.get_node("h1")
        assert node is not None
        assert node.statement == "第一个假设"
        assert node.dependencies == []
        assert node.dependents == []

    def test_add_multiple_nodes(self) -> None:
        """测试添加多个节点"""
        graph = HypothesisGraph()

        graph.add_node("h1", "假设一")
        graph.add_node("h2", "假设二")
        graph.add_node("h3", "假设三")

        assert len(graph) == 3
        assert "h1" in graph
        assert "h2" in graph
        assert "h3" in graph

    def test_add_node_with_dependencies(self) -> None:
        """测试添加带依赖的节点"""
        graph = HypothesisGraph()

        graph.add_node("h1", "基础假设")
        graph.add_node("h2", "依赖假设", dependencies=["h1"])

        # 检查 h2 的依赖
        h2 = graph.get_node("h2")
        assert h2 is not None
        assert h2.dependencies == ["h1"]

        # 检查 h1 的反向依赖
        h1 = graph.get_node("h1")
        assert h1 is not None
        assert h1.dependents == ["h2"]

    def test_add_dependency_explicit(self) -> None:
        """测试显式添加依赖关系"""
        graph = HypothesisGraph()

        graph.add_node("h1", "假设一")
        graph.add_node("h2", "假设二")

        graph.add_dependency("h2", "h1")  # h2 依赖 h1

        h2 = graph.get_node("h2")
        assert h2 is not None
        assert "h1" in h2.dependencies

        h1 = graph.get_node("h1")
        assert h1 is not None
        assert "h2" in h1.dependents

    def test_add_dependency_nonexistent_node(self) -> None:
        """测试添加依赖到不存在的节点"""
        graph = HypothesisGraph()

        graph.add_node("h1", "假设一")

        # 尝试添加不存在的依赖
        with pytest.raises(ValueError, match="Node 'h2' does not exist"):
            graph.add_dependency("h1", "h2")

        with pytest.raises(ValueError, match="Node 'h3' does not exist"):
            graph.add_dependency("h3", "h1")

    def test_get_node_nonexistent(self) -> None:
        """测试获取不存在的节点"""
        graph = HypothesisGraph()

        result = graph.get_node("nonexistent")

        assert result is None

    def test_remove_node(self) -> None:
        """测试移除节点"""
        graph = HypothesisGraph()

        graph.add_node("h1", "假设一")
        graph.add_node("h2", "假设二", dependencies=["h1"])

        # 移除 h1
        result = graph.remove_node("h1")

        assert result is True
        assert len(graph) == 1
        assert "h1" not in graph

        # 检查 h2 的依赖被清除
        h2 = graph.get_node("h2")
        assert h2 is not None
        assert "h1" not in h2.dependencies

    def test_remove_nonexistent_node(self) -> None:
        """测试移除不存在的节点"""
        graph = HypothesisGraph()

        result = graph.remove_node("nonexistent")

        assert result is False


class TestHypothesisGraphExecution:
    """测试 HypothesisGraph 执行顺序功能"""

    def test_get_execution_order_empty_graph(self) -> None:
        """测试空图的执行顺序"""
        graph = HypothesisGraph()

        result = graph.get_execution_order()

        assert result == []

    def test_get_execution_order_single_node(self) -> None:
        """测试单节点的执行顺序"""
        graph = HypothesisGraph()

        graph.add_node("h1", "假设一")

        result = graph.get_execution_order()

        assert result == [["h1"]]

    def test_get_execution_order_linear(self) -> None:
        """测试线性依赖的执行顺序"""
        graph = HypothesisGraph()

        # h3 -> h2 -> h1 (h3 依赖 h2，h2 依赖 h1)
        graph.add_node("h1", "基础假设")
        graph.add_node("h2", "中间假设", dependencies=["h1"])
        graph.add_node("h3", "顶层假设", dependencies=["h2"])

        result = graph.get_execution_order()

        assert result == [["h1"], ["h2"], ["h3"]]

    def test_get_execution_order_parallel(self) -> None:
        """测试可并行执行的节点"""
        graph = HypothesisGraph()

        # h2, h3 都依赖 h1，可以并行
        graph.add_node("h1", "基础假设")
        graph.add_node("h2", "假设二", dependencies=["h1"])
        graph.add_node("h3", "假设三", dependencies=["h1"])

        result = graph.get_execution_order()

        assert len(result) == 2
        assert result[0] == ["h1"]
        assert set(result[1]) == {"h2", "h3"}

    def test_get_execution_order_complex(self) -> None:
        """测试复杂依赖关系的执行顺序"""
        graph = HypothesisGraph()

        # 构建复杂依赖图
        # h1 (无依赖)
        # h2 (无依赖)
        # h3 依赖 h1
        # h4 依赖 h1, h2
        # h5 依赖 h3, h4
        graph.add_node("h1", "假设一")
        graph.add_node("h2", "假设二")
        graph.add_node("h3", "假设三", dependencies=["h1"])
        graph.add_node("h4", "假设四", dependencies=["h1", "h2"])
        graph.add_node("h5", "假设五", dependencies=["h3", "h4"])

        result = graph.get_execution_order()

        assert len(result) == 3
        # 第一批：h1, h2 可并行
        assert set(result[0]) == {"h1", "h2"}
        # 第二批：h3, h4 可并行（都在第一批完成后可执行）
        assert set(result[1]) == {"h3", "h4"}
        # 第三批：h5
        assert result[2] == ["h5"]

    def test_get_execution_order_circular_dependency(self) -> None:
        """测试循环依赖检测"""
        graph = HypothesisGraph()

        # 创建循环依赖：h1 -> h2 -> h3 -> h1
        graph.add_node("h1", "假设一")
        graph.add_node("h2", "假设二", dependencies=["h1"])
        graph.add_node("h3", "假设三", dependencies=["h2"])

        # 手动添加循环依赖
        graph.nodes["h1"].dependencies.append("h3")
        graph.nodes["h3"].dependents.append("h1")

        with pytest.raises(ValueError, match="Circular dependency"):
            graph.get_execution_order()

    def test_get_ready_hypotheses_empty(self) -> None:
        """测试空图的可执行假设"""
        graph = HypothesisGraph()

        result = graph.get_ready_hypotheses(set())

        assert result == []

    def test_get_ready_hypotheses_all_ready(self) -> None:
        """测试所有假设都可执行"""
        graph = HypothesisGraph()

        graph.add_node("h1", "假设一")
        graph.add_node("h2", "假设二")

        result = graph.get_ready_hypotheses(set())

        assert set(result) == {"h1", "h2"}

    def test_get_ready_hypotheses_with_dependencies(self) -> None:
        """测试有依赖时的可执行假设"""
        graph = HypothesisGraph()

        graph.add_node("h1", "假设一")
        graph.add_node("h2", "假设二", dependencies=["h1"])
        graph.add_node("h3", "假设三", dependencies=["h1"])

        # 没有完成任何假设
        result = graph.get_ready_hypotheses(set())
        assert result == ["h1"]

        # 完成了 h1
        result = graph.get_ready_hypotheses({"h1"})
        assert set(result) == {"h2", "h3"}

        # 完成了 h1, h2
        result = graph.get_ready_hypotheses({"h1", "h2"})
        assert result == ["h3"]

    def test_get_ready_hypotheses_skip_completed(self) -> None:
        """测试跳过已完成的假设"""
        graph = HypothesisGraph()

        graph.add_node("h1", "假设一")
        graph.add_node("h2", "假设二")

        result = graph.get_ready_hypotheses({"h1"})

        assert result == ["h2"]


class TestHypothesisGraphCycleDetection:
    """测试循环依赖检测"""

    def test_detect_cycles_no_cycle(self) -> None:
        """测试无循环的图"""
        graph = HypothesisGraph()

        graph.add_node("h1", "假设一")
        graph.add_node("h2", "假设二", dependencies=["h1"])
        graph.add_node("h3", "假设三", dependencies=["h2"])

        cycles = graph.detect_cycles()

        assert cycles == []

    def test_detect_cycles_simple_cycle(self) -> None:
        """测试简单循环"""
        graph = HypothesisGraph()

        graph.add_node("h1", "假设一")
        graph.add_node("h2", "假设二")

        # 创建循环：h1 -> h2 -> h1
        graph.add_dependency("h1", "h2")
        graph.add_dependency("h2", "h1")

        cycles = graph.detect_cycles()

        assert len(cycles) > 0

    def test_detect_cycles_complex(self) -> None:
        """测试复杂循环"""
        graph = HypothesisGraph()

        # h1 -> h2 -> h3 -> h1
        graph.add_node("h1", "假设一")
        graph.add_node("h2", "假设二", dependencies=["h1"])
        graph.add_node("h3", "假设三", dependencies=["h2"])

        # 添加循环
        graph.nodes["h1"].dependencies.append("h3")

        cycles = graph.detect_cycles()

        assert len(cycles) > 0


class TestHypothesisGraphSerialization:
    """测试序列化和反序列化"""

    def test_to_dict(self) -> None:
        """测试转换为字典"""
        graph = HypothesisGraph()

        graph.add_node("h1", "假设一")
        graph.add_node("h2", "假设二", dependencies=["h1"])

        result = graph.to_dict()

        assert "nodes" in result
        assert "h1" in result["nodes"]
        assert "h2" in result["nodes"]
        assert result["nodes"]["h1"]["statement"] == "假设一"
        assert result["nodes"]["h2"]["dependencies"] == ["h1"]

    def test_from_dict(self) -> None:
        """测试从字典创建"""
        data = {
            "nodes": {
                "h1": {
                    "hypothesis_id": "h1",
                    "statement": "假设一",
                    "dependencies": [],
                    "dependents": ["h2"],
                    "estimated_effort": "medium",
                    "risk_level": "medium",
                    "state": "pending",
                },
                "h2": {
                    "hypothesis_id": "h2",
                    "statement": "假设二",
                    "dependencies": ["h1"],
                    "dependents": [],
                    "estimated_effort": "medium",
                    "risk_level": "medium",
                    "state": "pending",
                },
            }
        }

        graph = HypothesisGraph.from_dict(data)

        assert len(graph) == 2
        assert "h1" in graph
        assert "h2" in graph

        h1 = graph.get_node("h1")
        assert h1 is not None
        assert h1.statement == "假设一"

    def test_roundtrip_serialization(self) -> None:
        """测试序列化往返"""
        original = HypothesisGraph()

        original.add_node("h1", "假设一", estimated_effort="high", risk_level="low")
        original.add_node("h2", "假设二", dependencies=["h1"], state="verified")
        original.add_node("h3", "假设三", dependencies=["h1", "h2"])

        # 序列化
        data = original.to_dict()

        # 反序列化
        restored = HypothesisGraph.from_dict(data)

        # 验证
        assert len(restored) == len(original)
        assert restored.get_node("h1").statement == "假设一"
        assert restored.get_node("h2").dependencies == ["h1"]
        assert set(restored.get_node("h3").dependencies) == {"h1", "h2"}


class TestHypothesisGraphStatistics:
    """测试统计功能"""

    def test_get_statistics_empty(self) -> None:
        """测试空图的统计"""
        graph = HypothesisGraph()

        stats = graph.get_statistics()

        assert stats["total_nodes"] == 0
        assert stats["total_dependencies"] == 0
        assert stats["state_distribution"] == {}

    def test_get_statistics_single_node(self) -> None:
        """测试单节点的统计"""
        graph = HypothesisGraph()

        graph.add_node("h1", "假设一")

        stats = graph.get_statistics()

        assert stats["total_nodes"] == 1
        assert stats["total_dependencies"] == 0
        assert stats["state_distribution"] == {"pending": 1}

    def test_get_statistics_complex(self) -> None:
        """测试复杂图的统计"""
        graph = HypothesisGraph()

        graph.add_node("h1", "假设一", state="verified")
        graph.add_node("h2", "假设二", state="verified", dependencies=["h1"])
        graph.add_node("h3", "假设三", state="in_progress", dependencies=["h1", "h2"])
        graph.add_node("h4", "假设四", state="rejected")

        stats = graph.get_statistics()

        assert stats["total_nodes"] == 4
        assert stats["total_dependencies"] == 3
        assert stats["state_distribution"]["verified"] == 2
        assert stats["state_distribution"]["in_progress"] == 1
        assert stats["state_distribution"]["rejected"] == 1


class TestHypothesisGraphEdgeCases:
    """测试边界情况"""

    def test_add_duplicate_dependency(self) -> None:
        """测试添加重复依赖"""
        graph = HypothesisGraph()

        graph.add_node("h1", "假设一")
        graph.add_node("h2", "假设二", dependencies=["h1"])

        # 重复添加依赖
        graph.add_dependency("h2", "h1")

        h2 = graph.get_node("h2")
        assert h2 is not None
        assert h2.dependencies.count("h1") == 1  # 应该只有一个

    def test_dependency_on_nonexistent_node(self) -> None:
        """测试依赖不存在的节点（通过 add_node）"""
        graph = HypothesisGraph()

        # 添加依赖不存在的节点的假设
        graph.add_node("h1", "假设一", dependencies=["nonexistent"])

        # 图应该正常创建，只是依赖关系不完整
        assert len(graph) == 1
        h1 = graph.get_node("h1")
        assert h1 is not None
        assert h1.dependencies == ["nonexistent"]

    def test_self_dependency(self) -> None:
        """测试自依赖"""
        graph = HypothesisGraph()

        graph.add_node("h1", "假设一")

        # 添加自依赖
        graph.add_dependency("h1", "h1")

        # 应该检测到循环
        with pytest.raises(ValueError, match="Circular dependency"):
            graph.get_execution_order()

    def test_empty_graph_operations(self) -> None:
        """测试空图的各种操作"""
        graph = HypothesisGraph()

        # 应该都能正常处理
        assert graph.get_execution_order() == []
        assert graph.get_ready_hypotheses(set()) == []
        assert graph.detect_cycles() == []
        assert graph.get_statistics()["total_nodes"] == 0
        assert graph.to_dict() == {"nodes": {}}
