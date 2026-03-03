"""
HypothesisGraph - 假设依赖关系管理

实现假设之间的依赖关系图，支持拓扑排序和并行执行。
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional
from collections import deque


@dataclass
class HypothesisNode:
    """假设节点，表示一个可验证的假设"""
    hypothesis_id: str
    statement: str
    dependencies: List[str] = field(default_factory=list)  # 依赖的假设ID列表
    dependents: List[str] = field(default_factory=list)    # 被依赖的假设ID列表
    estimated_effort: str = "medium"  # low, medium, high
    risk_level: str = "medium"        # low, medium, high
    state: str = "pending"            # pending, in_progress, verified, rejected

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "hypothesis_id": self.hypothesis_id,
            "statement": self.statement,
            "dependencies": self.dependencies,
            "dependents": self.dependents,
            "estimated_effort": self.estimated_effort,
            "risk_level": self.risk_level,
            "state": self.state
        }

    @classmethod
    def from_dict(cls, data: dict) -> "HypothesisNode":
        """从字典创建节点"""
        return cls(
            hypothesis_id=data["hypothesis_id"],
            statement=data["statement"],
            dependencies=data.get("dependencies", []),
            dependents=data.get("dependents", []),
            estimated_effort=data.get("estimated_effort", "medium"),
            risk_level=data.get("risk_level", "medium"),
            state=data.get("state", "pending")
        )


class HypothesisGraph:
    """
    假设依赖图

    管理假设之间的依赖关系，支持：
    - 添加假设节点
    - 建立依赖关系
    - 拓扑排序获取执行顺序
    - 检测循环依赖
    - 获取可执行的假设
    """

    def __init__(self):
        self.nodes: Dict[str, HypothesisNode] = {}

    def add_node(
        self,
        hypothesis_id: str,
        statement: str,
        estimated_effort: str = "medium",
        risk_level: str = "medium",
        state: str = "pending",
        dependencies: Optional[List[str]] = None
    ) -> None:
        """
        添加假设节点

        Args:
            hypothesis_id: 假设唯一标识
            statement: 假设陈述
            estimated_effort: 预估工作量 (low/medium/high)
            risk_level: 风险等级 (low/medium/high)
            state: 状态 (pending/in_progress/verified/rejected)
            dependencies: 依赖的假设ID列表
        """
        node = HypothesisNode(
            hypothesis_id=hypothesis_id,
            statement=statement,
            dependencies=dependencies or [],
            dependents=[],
            estimated_effort=estimated_effort,
            risk_level=risk_level,
            state=state
        )
        self.nodes[hypothesis_id] = node

        # 建立反向依赖关系
        for dep_id in node.dependencies:
            if dep_id in self.nodes:
                self.nodes[dep_id].dependents.append(hypothesis_id)

    def add_dependency(self, from_id: str, to_id: str) -> None:
        """
        添加依赖关系：from_id 依赖于 to_id

        Args:
            from_id: 依赖方假设ID
            to_id: 被依赖方假设ID

        Raises:
            ValueError: 如果节点不存在
        """
        if from_id not in self.nodes:
            raise ValueError(f"Node '{from_id}' does not exist")
        if to_id not in self.nodes:
            raise ValueError(f"Node '{to_id}' does not exist")

        # 避免重复添加
        if to_id not in self.nodes[from_id].dependencies:
            self.nodes[from_id].dependencies.append(to_id)
        if from_id not in self.nodes[to_id].dependents:
            self.nodes[to_id].dependents.append(from_id)

    def get_execution_order(self) -> List[List[str]]:
        """
        使用 Kahn 拓扑排序获取执行顺序

        Returns:
            执行批次列表，每个批次内的假设可以并行执行
            例如: [["h1", "h2"], ["h3"], ["h4", "h5"]]
            表示 h1 和 h2 可以并行，完成后执行 h3，再执行 h4 和 h5

        Raises:
            ValueError: 如果存在循环依赖
        """
        if not self.nodes:
            return []

        # 计算每个节点的入度（依赖数量）
        in_degree: Dict[str, int] = {}
        for node_id, node in self.nodes.items():
            # 只计算存在的依赖节点
            in_degree[node_id] = sum(
                1 for dep_id in node.dependencies
                if dep_id in self.nodes
            )

        # 使用队列存储入度为0的节点
        queue: deque = deque([
            node_id for node_id, degree in in_degree.items()
            if degree == 0
        ])

        result: List[List[str]] = []
        processed_count = 0

        while queue:
            # 当前批次：所有入度为0的节点可以并行执行
            batch = []
            batch_size = len(queue)
            for _ in range(batch_size):
                node_id = queue.popleft()
                batch.append(node_id)
                processed_count += 1

                # 减少依赖此节点的其他节点的入度
                node = self.nodes[node_id]
                for dependent_id in node.dependents:
                    if dependent_id in in_degree:
                        in_degree[dependent_id] -= 1
                        if in_degree[dependent_id] == 0:
                            queue.append(dependent_id)

            result.append(batch)

        # 检测循环依赖
        if processed_count != len(self.nodes):
            cycles = self.detect_cycles()
            raise ValueError(f"Circular dependency detected: {cycles}")

        return result

    def get_ready_hypotheses(self, completed: Set[str]) -> List[str]:
        """
        获取可以立即执行的假设（所有依赖已完成）

        Args:
            completed: 已完成的假设ID集合

        Returns:
            可以立即执行的假设ID列表
        """
        ready = []
        for node_id, node in self.nodes.items():
            # 跳过已完成的
            if node_id in completed:
                continue
            # 检查所有依赖是否已完成
            if all(dep_id in completed for dep_id in node.dependencies):
                ready.append(node_id)
        return ready

    def detect_cycles(self) -> List[List[str]]:
        """
        检测图中的循环依赖

        Returns:
            检测到的所有循环路径列表
        """
        cycles: List[List[str]] = []
        visited: Set[str] = set()
        rec_stack: Set[str] = set()
        path: List[str] = []

        def dfs(node_id: str) -> bool:
            """深度优先搜索检测环"""
            visited.add(node_id)
            rec_stack.add(node_id)
            path.append(node_id)

            # 遍历依赖节点（反向：当前节点依赖哪些节点）
            node = self.nodes.get(node_id)
            if node:
                for dep_id in node.dependencies:
                    if dep_id not in self.nodes:
                        continue
                    if dep_id not in visited:
                        if dfs(dep_id):
                            return True
                    elif dep_id in rec_stack:
                        # 找到环，记录路径
                        cycle_start = path.index(dep_id)
                        cycle = path[cycle_start:] + [dep_id]
                        cycles.append(cycle)

            path.pop()
            rec_stack.remove(node_id)
            return False

        for node_id in self.nodes:
            if node_id not in visited:
                dfs(node_id)

        return cycles

    def to_dict(self) -> dict:
        """
        将图序列化为字典

        Returns:
            包含所有节点信息的字典
        """
        return {
            "nodes": {
                node_id: node.to_dict()
                for node_id, node in self.nodes.items()
            }
        }

    @classmethod
    def from_dict(cls, data: dict) -> "HypothesisGraph":
        """
        从字典反序列化图

        Args:
            data: 序列化的图数据

        Returns:
            HypothesisGraph 实例
        """
        graph = cls()
        nodes_data = data.get("nodes", {})

        # 先创建所有节点
        for node_id, node_data in nodes_data.items():
            node = HypothesisNode.from_dict(node_data)
            graph.nodes[node_id] = node

        return graph

    def get_node(self, hypothesis_id: str) -> Optional[HypothesisNode]:
        """获取指定假设节点"""
        return self.nodes.get(hypothesis_id)

    def remove_node(self, hypothesis_id: str) -> bool:
        """
        移除假设节点

        Args:
            hypothesis_id: 要移除的假设ID

        Returns:
            是否成功移除
        """
        if hypothesis_id not in self.nodes:
            return False

        node = self.nodes[hypothesis_id]

        # 从依赖节点的 dependents 列表中移除
        for dep_id in node.dependencies:
            if dep_id in self.nodes:
                self.nodes[dep_id].dependents = [
                    d for d in self.nodes[dep_id].dependents
                    if d != hypothesis_id
                ]

        # 从被依赖节点的 dependencies 列表中移除
        for dependent_id in node.dependents:
            if dependent_id in self.nodes:
                self.nodes[dependent_id].dependencies = [
                    d for d in self.nodes[dependent_id].dependencies
                    if d != hypothesis_id
                ]

        del self.nodes[hypothesis_id]
        return True

    def get_statistics(self) -> dict:
        """
        获取图的统计信息

        Returns:
            包含节点数量、依赖关系数量等统计信息
        """
        total_deps = sum(len(node.dependencies) for node in self.nodes.values())
        states = {}
        for node in self.nodes.values():
            states[node.state] = states.get(node.state, 0) + 1

        return {
            "total_nodes": len(self.nodes),
            "total_dependencies": total_deps,
            "state_distribution": states
        }

    def __len__(self) -> int:
        """返回节点数量"""
        return len(self.nodes)

    def __contains__(self, hypothesis_id: str) -> bool:
        """检查假设是否存在"""
        return hypothesis_id in self.nodes

    def __repr__(self) -> str:
        """字符串表示"""
        return f"HypothesisGraph(nodes={len(self.nodes)})"
