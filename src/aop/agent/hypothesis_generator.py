"""
HypothesisGenerator - 假设生成器

基于澄清后的需求，自动生成可验证的假设。
支持双模式：
- OrchestratorClient 模式：使用中枢 Agent 进行决策（推荐）
- LLMClient 模式：直接调用 LLM API（向后兼容）
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, List, Dict, Any, Protocol, runtime_checkable

from .types import GeneratedHypothesis, HypothesisType, ClarifiedRequirement, HypothesisGenerationConfig

if TYPE_CHECKING:
    from ..llm import LLMClient, LLMMessage
    from ..orchestrator import OrchestratorClient


HYPOTHESIS_GENERATION_SYSTEM_PROMPT = """你是一个技术架构专家，负责分析项目需求并生成技术假设。

输出要求：
- 返回 JSON 格式，包含 hypotheses 数组
- 每个假设包含以下字段：

  基本字段：
  - statement: 假设陈述（字符串）
  - type: 假设类型（technical/architectural/performance/security/usability/business）
  - validation_method: 验证方法（字符串）
  - success_criteria: 成功标准（字符串数组）
  - priority: 优先级（quick_win/deep_dive/strategic）
  - estimated_effort: 预估工作量（字符串）
  - dependencies: 依赖项（字符串数组）
  - risk_level: 风险等级（low/medium/high）

  任务委托字段（Anthropic 推荐，用于 subagent 执行）：
  - objective: 明确目标（字符串，描述这个假设要解决的具体问题）
  - output_format: 输出格式（字符串，描述期望的输出结构，如"代码文件列表 + 修改说明"）
  - tools_guidance: 工具指导（字符串，建议使用的工具和方法，如"使用 grep 搜索关键词，使用 ast 分析代码结构"）
  - boundaries: 任务边界（字符串，明确不要做什么，如"不要修改测试文件"）
  - effort_budget: 预估工具调用次数（整数，简单任务 3-10，中等任务 10-15，复杂任务 15-25）

假设类型说明：
- technical: 技术实现相关假设
- architectural: 架构设计相关假设
- performance: 性能相关假设
- security: 安全相关假设
- usability: 可用性相关假设
- business: 业务相关假设

复杂度指导：
- 简单任务（单文件修改）：effort_budget = 3-10
- 中等任务（多文件修改）：effort_budget = 10-15
- 复杂任务（架构级别）：effort_budget = 15-25

请根据需求生成 3-7 个最具价值的假设，按优先级排序。每个假设都应包含完整的任务委托字段，以便 subagent 能够独立执行。"""


@runtime_checkable
class LLMClientProtocol(Protocol):
    """LLM 客户端协议，用于类型检查"""
    def complete(
        self,
        messages: List[Any],
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> Any:
        ...


class HypothesisGenerator:
    """
    假设生成器

    基于澄清后的需求，自动生成可验证的假设。

    支持三种模式：
    1. OrchestratorClient 模式：使用中枢 Agent 进行决策（推荐）
    2. LLMClient 模式：直接调用 LLM API（向后兼容）
    3. 回退模式：基于规则的硬编码假设生成

    假设生成策略:
    1. 从需求中提取关键决策点
    2. 将决策点转化为可验证的假设
    3. 为每个假设设置验证方法和成功标准
    4. 识别假设之间的依赖关系
    5. 评估风险和工作量
    """

    def __init__(
        self,
        llm_client: LLMClientProtocol | None = None,
        config: HypothesisGenerationConfig | None = None,
        orchestrator_client: OrchestratorClient | None = None,
    ):
        """
        初始化假设生成器

        Args:
            llm_client: LLM 客户端（向后兼容）
            config: 假设生成配置
            orchestrator_client: 中枢 Agent 客户端（推荐）
        """
        self.llm = llm_client
        self.config = config or HypothesisGenerationConfig()
        self.orchestrator = orchestrator_client

    def _has_decision_engine(self) -> bool:
        """检查是否有决策引擎可用"""
        return self.orchestrator is not None or self.llm is not None

    def generate(
        self,
        requirement: ClarifiedRequirement,
        project_context: dict[str, Any] | None = None,
    ) -> list[GeneratedHypothesis]:
        """
        生成假设列表

        Args:
            requirement: 澄清后的需求
            project_context: 项目上下文信息（可选）

        Returns:
            生成的假设列表
        """
        if not self._has_decision_engine():
            return self._fallback_generate(requirement)

        try:
            prompt = self._build_prompt(requirement, project_context)

            # 优先使用 OrchestratorClient
            if self.orchestrator:
                response = self.orchestrator.complete(
                    messages=[{"role": "user", "content": prompt}],
                    system=HYPOTHESIS_GENERATION_SYSTEM_PROMPT,
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens,
                )
                content = response.content
            # 回退到 LLMClient
            elif self.llm:
                # 导入 LLMMessage（运行时可能不存在）
                try:
                    from ..llm import LLMMessage
                    messages = [
                        LLMMessage(role="system", content=HYPOTHESIS_GENERATION_SYSTEM_PROMPT),
                        LLMMessage(role="user", content=prompt),
                    ]
                except ImportError:
                    # 如果 LLMMessage 不可用，使用字典格式
                    messages = [
                        {"role": "system", "content": HYPOTHESIS_GENERATION_SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ]

                response = self.llm.complete(
                    messages,
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens,
                )
                # 提取响应内容
                content = response.content if hasattr(response, 'content') else str(response)
            else:
                return self._fallback_generate(requirement)

            hypotheses = self._parse_response(content)

            if not hypotheses and self.config.enable_fallback:
                return self._fallback_generate(requirement)

            return self._sort_by_priority(hypotheses)

        except Exception as e:
            # 调用失败时记录错误并回退到规则生成
            import sys
            print(f"[AOP] Hypothesis generation failed: {e}", file=sys.stderr)
            if self.config.enable_fallback:
                return self._fallback_generate(requirement)
            return []

    def _build_prompt(
        self,
        requirement: ClarifiedRequirement,
        project_context: dict[str, Any] | None = None,
    ) -> str:
        """构建 LLM 提示词"""
        parts = [f"## 需求摘要\n{requirement.summary}"]
        
        if requirement.core_features:
            parts.append(f"\n## 核心功能\n" + "\n".join(f"- {f}" for f in requirement.core_features))
        
        if requirement.tech_constraints:
            parts.append(f"\n## 技术约束\n" + "\n".join(f"- {k}: {v}" for k, v in requirement.tech_constraints.items()))
        
        if requirement.success_criteria:
            parts.append(f"\n## 成功标准\n" + "\n".join(f"- {c}" for c in requirement.success_criteria))
        
        if requirement.risks:
            parts.append(f"\n## 已知风险\n" + "\n".join(f"- {r}" for r in requirement.risks))
        
        if project_context:
            parts.append(f"\n## 项目上下文\n" + "\n".join(f"- {k}: {v}" for k, v in project_context.items()))
        
        parts.append("\n\n请根据以上需求生成技术假设，以 JSON 格式返回。")
        
        return "\n".join(parts)

    def _parse_response(self, content: str) -> list[GeneratedHypothesis]:
        """解析 LLM JSON 响应为 GeneratedHypothesis 对象"""
        json_str = self._extract_json(content)
        if not json_str:
            return []
        
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError:
            return []
        
        hypotheses = []
        for h_data in data.get("hypotheses", []):
            try:
                # 安全解析 hypothesis_type
                type_str = h_data.get("type", "technical")
                try:
                    hypothesis_type = HypothesisType(type_str)
                except ValueError:
                    hypothesis_type = HypothesisType.TECHNICAL

                hypothesis = GeneratedHypothesis(
                    statement=h_data.get("statement", ""),
                    hypothesis_type=hypothesis_type,
                    validation_method=h_data.get("validation_method", ""),
                    success_criteria=h_data.get("success_criteria", []),
                    priority=h_data.get("priority", "quick_win"),
                    estimated_effort=h_data.get("estimated_effort", ""),
                    dependencies=h_data.get("dependencies", []),
                    risk_level=h_data.get("risk_level", "medium"),
                )
                hypotheses.append(hypothesis)
            except Exception:
                # 跳过解析失败的假设
                continue
        
        return hypotheses[:self.config.max_hypotheses]

    def _extract_json(self, content: str) -> str | None:
        """从内容中提取 JSON 字符串"""
        content = content.strip()
        
        # 尝试直接解析
        if content.startswith("{") and content.endswith("}"):
            return content
        
        # 尝试提取三反引号代码块中的 JSON (```json ... ```)
        triple_match = re.search(r'```(?:json)?\s*\n?([\s\S]*?)\n?```', content)
        if triple_match:
            return triple_match.group(1).strip()
        
        # 尝试提取单反引号代码块中的 JSON
        single_match = re.search(r'`(?:json)?\s*([\s\S]*?)`', content)
        if single_match:
            return single_match.group(1).strip()
        
        # 尝试查找 JSON 对象（处理嵌套花括号）
        brace_start = content.find("{")
        if brace_start != -1:
            depth = 0
            for i, char in enumerate(content[brace_start:], brace_start):
                if char == "{":
                    depth += 1
                elif char == "}":
                    depth -= 1
                    if depth == 0:
                        return content[brace_start:i + 1]
        
        return None

    def _sort_by_priority(self, hypotheses: list[GeneratedHypothesis]) -> list[GeneratedHypothesis]:
        """按优先级排序假设"""
        priority_order = {"quick_win": 0, "deep_dive": 1, "strategic": 2}
        return sorted(
            hypotheses,
            key=lambda h: priority_order.get(h.priority, 99)
        )

    def _fallback_generate(self, requirement: ClarifiedRequirement) -> list[GeneratedHypothesis]:
        """回退到基于规则的生成（当无 LLM 或 LLM 失败时）"""
        # 第一步：提取关键决策点
        decision_points = self._extract_decision_points(requirement)

        # 第二步：生成假设
        hypotheses = []
        for dp in decision_points:
            h = self._decision_to_hypothesis(dp, requirement)
            hypotheses.append(h)

        # 第三步：分析依赖关系
        hypotheses = self._analyze_dependencies(hypotheses)

        # 第四步：评估风险和工作量
        hypotheses = self._assess_risks_and_effort(hypotheses)

        return hypotheses

    def _extract_decision_points(self, requirement: ClarifiedRequirement) -> List[Dict[str, Any]]:
        """从需求中提取关键决策点"""
        # 基于规则的决策点提取
        decision_points = [
            {
                "description": "技术栈选择",
                "options": ["Next.js + Supabase", "Django + PostgreSQL", "Spring Boot + MySQL"],
                "risk": "medium",
                "impact": "全项目",
            },
            {
                "description": "认证方案",
                "options": ["JWT", "Session", "OAuth"],
                "risk": "high",
                "impact": "安全模块",
            },
        ]

        # 根据需求特征添加更多决策点
        if requirement.core_features:
            for feature in requirement.core_features[:3]:
                if "实时" in feature or "推送" in feature:
                    decision_points.append({
                        "description": f"{feature} - 通信方案",
                        "options": ["WebSocket", "Server-Sent Events", "长轮询"],
                        "risk": "medium",
                        "impact": feature,
                    })

        return decision_points

    def _decision_to_hypothesis(
        self,
        decision_point: dict,
        requirement: ClarifiedRequirement,
    ) -> GeneratedHypothesis:
        """将决策点转换为假设"""
        return GeneratedHypothesis(
            statement=f"采用 {decision_point['options'][0]} 可以满足项目需求",
            hypothesis_type=HypothesisType.TECHNICAL,
            validation_method="构建原型并测试核心功能",
            success_criteria=["原型可运行", "核心功能正常", "性能达标"],
            priority="quick_win" if decision_point["risk"] == "low" else "deep_dive",
            estimated_effort="1-2天" if decision_point["risk"] == "low" else "3-5天",
            dependencies=[],
            risk_level=decision_point["risk"],
        )

    def _analyze_dependencies(self, hypotheses: List[GeneratedHypothesis]) -> List[GeneratedHypothesis]:
        """分析假设之间的依赖关系"""
        # 简化实现
        return hypotheses

    def _assess_risks_and_effort(self, hypotheses: List[GeneratedHypothesis]) -> List[GeneratedHypothesis]:
        """评估风险和工作量"""
        effort_map = {
            HypothesisType.TECHNICAL: "2-3天",
            HypothesisType.ARCHITECTURAL: "5-7天",
            HypothesisType.PERFORMANCE: "3-5天",
            HypothesisType.SECURITY: "4-6天",
            HypothesisType.USABILITY: "1-3天",
            HypothesisType.BUSINESS: "1-2天",
        }

        for h in hypotheses:
            if not h.estimated_effort:
                h.estimated_effort = effort_map.get(h.hypothesis_type, "3-5天")

        return hypotheses

