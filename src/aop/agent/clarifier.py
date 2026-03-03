"""
RequirementClarifier - 需求澄清器

将模糊的需求描述转换为结构化的明确需求。
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import List, Callable, Dict, Any
from enum import Enum

from .types import ClarifiedRequirement, QAPair
from ..llm import LLMClient, LLMMessage


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
    ):
        self.llm = llm_client
        self.config = config or ClarificationConfig()
        self.clarification_history: List[QAPair] = []

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

        如果有 LLM 客户端，使用 LLM 进行智能维度识别；
        否则返回默认维度。
        """
        if not self.llm:
            return self._default_dimensions()

        prompt = f"分析以下需求，识别需要澄清的关键维度：\n\n{input_text}\n\n输出 JSON: {{\"dimensions\": [\"维度1\", \"维度2\"]}}"

        try:
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
        except Exception:
            return self._default_dimensions()

    def _extract_json(self, text: str) -> str:
        """从文本中提取 JSON 字符串"""
        # 尝试匹配 `json ... ` 块
        json_match = re.search(r"`(?:json)?\s*([\s\S]*?)`", text)
        if json_match:
            return json_match.group(1).strip()

        # 尝试匹配花括号包围的 JSON
        brace_match = re.search(r"\{[\s\S]*\}", text)
        if brace_match:
            return brace_match.group(0)

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
