"""
RequirementClarifier - 需求澄清器

将模糊的需求描述转换为结构化的明确需求。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Callable, Dict, Any
from enum import Enum

from .types import ClarifiedRequirement, QAPair


class ClarificationStrategy(Enum):
    INTERACTIVE = "interactive"
    AUTO_INFER = "auto_infer"
    HYBRID = "hybrid"


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

    def __init__(self, strategy: ClarificationStrategy = ClarificationStrategy.HYBRID):
        self.strategy = strategy
        self.clarification_history: List[QAPair] = []

    def clarify(
        self,
        vague_input: str,
        max_rounds: int = 3,
        interactive_callback: Optional[Callable[[str], str]] = None,
    ) -> ClarifiedRequirement:
        """
        澄清需求

        Args:
            vague_input: 模糊的输入描述
            max_rounds: 最大追问轮数
            interactive_callback: 交互式回调，接收问题返回答案

        Returns:
            澄清后的结构化需求
        """
        # 第一轮：识别关键维度
        dimensions = self._identify_key_dimensions(vague_input)

        # 第二轮：生成澄清问题
        questions = self._generate_questions(dimensions)

        # 第三轮：收集答案
        answers = self._collect_answers(questions, interactive_callback)

        # 第四轮：综合生成需求
        requirement = self._synthesize_requirement(vague_input, answers)

        return requirement

    def _identify_key_dimensions(self, input_text: str) -> List[str]:
        """
        识别需求的关键维度

        当前实现返回默认维度。未来可集成 LLM 进行智能分析。

        TODO(design): 集成 LLM 进行智能维度识别
        - 决策点：选择 LLM 提供商（本地/云端）
        - 决策点：prompt 模板设计
        - 决策点：fallback 策略（LLM 失败时使用默认维度）
        - 决策点：是否缓存分析结果
        """
        default_dimensions = [
            "user_type",
            "core_features",
            "tech_stack",
            "success_criteria",
        ]
        return default_dimensions

    def _generate_questions(self, dimensions: List[str]) -> List[str]:
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
        callback: Optional[Callable[[str], str]],
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

    def _auto_infer_answer(self, question: str) -> tuple:
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
