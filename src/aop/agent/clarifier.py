"""
RequirementClarifier - 需求澄清器

将模糊的需求描述转换为结构化的明确需求。
支持双模式：
- OrchestratorClient 模式：使用中枢 Agent 进行决策
- LLMClient 模式：直接调用 LLM API（向后兼容）
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import List, Callable, Dict, Any, TYPE_CHECKING
from enum import Enum

from .types import ClarifiedRequirement, QAPair

if TYPE_CHECKING:
    from ..llm import LLMClient, LLMMessage
    from ..orchestrator import OrchestratorClient


CLARIFICATION_SYSTEM_PROMPT = """你是一个需求分析师，负责将模糊的项目描述转化为清晰的结构化需求。

重点关注：
- 用户类型和规模
- 核心功能和优先级
- 技术约束和偏好
- 成功标准和可衡量指标

输出 JSON 格式。"""


class ClarificationStrategy(Enum):
    INTERACTIVE = "interactive"
    AUTO_INFER = "auto_infer"
    HYBRID = "hybrid"


@dataclass
class ClarificationConfig:
    """澄清器配置"""
    max_rounds: int = 3
    strategy: ClarificationStrategy = ClarificationStrategy.HYBRID
    llm_temperature: float = 0.3
    llm_max_tokens: int = 512


class RequirementClarifier:
    """
    需求澄清器

    将模糊的需求描述转换为结构化的明确需求。

    支持两种模式：
    1. OrchestratorClient 模式：使用中枢 Agent 进行决策（推荐）
    2. LLMClient 模式：直接调用 LLM API（向后兼容）

    工作流程:
    1. 分析模糊输入，识别关键维度
    2. 生成澄清问题
    3. 收集答案（交互式或自动推断）
    4. 综合生成结构化需求
    """

    def __init__(
        self,
        llm_client: LLMClient | None = None,
        config: ClarificationConfig | None = None,
        orchestrator_client: OrchestratorClient | None = None,
    ):
        """
        初始化需求澄清器

        Args:
            llm_client: LLM 客户端（向后兼容）
            config: 澄清器配置
            orchestrator_client: 中枢 Agent 客户端（推荐）
        """
        self.llm = llm_client
        self.config = config or ClarificationConfig()
        self.orchestrator = orchestrator_client
        self.clarification_history: List[QAPair] = []

    def _has_decision_engine(self) -> bool:
        """检查是否有决策引擎可用"""
        return self.orchestrator is not None or self.llm is not None

    def clarify(
        self,
        vague_input: str,
        interactive_callback: Callable[[str], str] | None = None,
    ) -> ClarifiedRequirement:
        """
        澄清需求

        Args:
            vague_input: 模糊的输入描述
            interactive_callback: 交互式回调，接收问题返回答案

        Returns:
            澄清后的结构化需求
        """
        # 第一轮：识别关键维度
        dimensions = self._identify_key_dimensions(vague_input)

        # 第二轮：生成澄清问题
        questions = self._generate_questions(vague_input, dimensions)

        # 第三轮：收集答案
        answers = []
        for question in questions:
            if interactive_callback:
                answer = interactive_callback(question)
                confidence = 1.0
            else:
                answer, confidence = self._auto_infer_answer(question)
            answers.append(QAPair(question=question, answer=answer, confidence=confidence))

        # 第四轮：综合生成需求
        requirement = self._synthesize_requirement(vague_input, answers)

        return requirement

    def _default_dimensions(self) -> list[str]:
        """返回默认的关键维度"""
        return [
            "user_type",
            "core_features",
            "tech_stack",
            "success_criteria",
        ]

    def _identify_key_dimensions(self, input_text: str) -> list[str]:
        """
        识别需求的关键维度

        优先使用 OrchestratorClient，其次使用 LLMClient，最后返回默认维度。
        """
        if not self._has_decision_engine():
            return self._default_dimensions()

        prompt = f"分析以下需求，识别需要澄清的关键维度：\n\n{input_text}\n\n输出 JSON: {{\"dimensions\": [\"维度1\", \"维度2\"]}}"

        try:
            # 优先使用 OrchestratorClient
            if self.orchestrator:
                return self._call_decision_engine(prompt, CLARIFICATION_SYSTEM_PROMPT)

            # 回退到 LLMClient
            if self.llm:
                from ..llm import LLMMessage
                response = self.llm.complete(
                    [
                        LLMMessage(role="system", content=CLARIFICATION_SYSTEM_PROMPT),
                        LLMMessage(role="user", content=prompt),
                    ],
                    temperature=self.config.llm_temperature,
                    max_tokens=self.config.llm_max_tokens,
                )

                data = json.loads(self._extract_json(response.content))
                dimensions = data.get("dimensions", self._default_dimensions())
                return dimensions if dimensions else self._default_dimensions()

        except Exception as e:
            import sys
            print(f"[AOP] Dimension identification failed: {e}", file=sys.stderr)

        return self._default_dimensions()

    def _call_decision_engine(self, prompt: str, system_prompt: str) -> list[str]:
        """
        调用决策引擎（OrchestratorClient）

        Args:
            prompt: 用户提示
            system_prompt: 系统提示

        Returns:
            解析后的维度列表
        """
        if not self.orchestrator:
            return self._default_dimensions()

        try:
            response = self.orchestrator.complete(
                messages=[{"role": "user", "content": prompt}],
                system=system_prompt,
                temperature=self.config.llm_temperature,
                max_tokens=self.config.llm_max_tokens,
            )

            data = json.loads(self._extract_json(response.content))
            dimensions = data.get("dimensions", self._default_dimensions())
            return dimensions if dimensions else self._default_dimensions()

        except Exception as e:
            import sys
            print(f"[AOP] Orchestrator call failed: {e}", file=sys.stderr)
            return self._default_dimensions()

    def _extract_json(self, text: str) -> str:
        """从文本中提取 JSON 字符串"""
        text = text.strip()
        
        # 尝试直接解析
        if text.startswith("{") and text.endswith("}"):
            return text
        
        # 尝试提取三反引号代码块 (```json ... ```)
        triple_match = re.search(r"```(?:json)?\s*\n?([\s\S]*?)\n?```", text)
        if triple_match:
            return triple_match.group(1).strip()
        
        # 尝试提取单反引号代码块
        single_match = re.search(r"`(?:json)?\s*([\s\S]*?)`", text)
        if single_match:
            return single_match.group(1).strip()
        
        # 尝试匹配花括号包围的 JSON（处理嵌套）
        brace_start = text.find("{")
        if brace_start != -1:
            depth = 0
            for i, char in enumerate(text[brace_start:], brace_start):
                if char == "{":
                    depth += 1
                elif char == "}":
                    depth -= 1
                    if depth == 0:
                        return text[brace_start:i + 1]
        
        return text

    def _generate_questions(self, vague_input: str, dimensions: List[str]) -> List[str]:
        """生成澄清问题"""
        question_templates = {
            "user_type": "目标用户是谁？（B2C消费者/B2B企业客户/内部员工）",
            "core_features": "核心功能有哪些？请按优先级排序。",
            "tech_stack": "有技术栈偏好吗？或者需要建议？",
            "success_criteria": "如何定义项目成功？有哪些可衡量的指标？",
            "performance": "对性能有具体要求吗？（响应时间/并发量）",
            "security": "有安全合规要求吗？（GDPR/等保/内网隔离）",
            "integration": "需要对接现有系统吗？",
            "timeline": "预期的交付时间？",
        }

        return [question_templates.get(d, f"请补充关于 {d} 的信息") for d in dimensions]

    def _collect_answers(
        self,
        questions: List[str],
        callback: Callable[[str], str] | None,
    ) -> List[QAPair]:
        """收集答案"""
        answers = []

        for question in questions:
            if callback:
                # 交互式收集
                answer = callback(question)
                confidence = 1.0
            else:
                # 自动推断
                answer, confidence = self._auto_infer_answer(question)

            qa = QAPair(question=question, answer=answer, confidence=confidence)
            answers.append(qa)
            self.clarification_history.append(qa)

        return answers

    def _auto_infer_answer(self, question: str) -> tuple[str, float]:
        """自动推断答案"""
        default_answers = {
            "用户类型": ("B2C消费者", 0.3),
            "核心功能": ("需要进一步分析", 0.1),
            "技术栈": ("Next.js + TypeScript", 0.2),
            "成功": ("功能完整可用", 0.3),
        }

        for key, (answer, confidence) in default_answers.items():
            if key in question:
                return answer, confidence

        return "需要更多信息", 0.1

    def _synthesize_requirement(
        self,
        original_input: str,
        answers: List[QAPair],
    ) -> ClarifiedRequirement:
        """综合生成结构化需求"""
        # 构建 requirement 对象
        user_type = "B2C"
        core_features = []
        success_criteria = ["功能完整"]

        for qa in answers:
            if "用户" in qa.question:
                user_type = qa.answer if qa.answer else "B2C"
            elif "功能" in qa.question:
                core_features = [qa.answer] if qa.answer else []
            elif "成功" in qa.question:
                success_criteria = [qa.answer] if qa.answer else ["功能完整"]

        return ClarifiedRequirement(
            summary=original_input,
            user_type=user_type,
            core_features=core_features,
            tech_constraints={},
            success_criteria=success_criteria,
            priority_order=core_features,
            risks=["需求不明确"],
            clarifications=answers,
        )

