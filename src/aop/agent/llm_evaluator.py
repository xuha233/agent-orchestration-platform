# -*- coding: utf-8 -*-
"""
LLM-as-Judge Evaluator - LLM 评估器

基于 Anthropic 研究：使用 LLM 评估输出质量，实现自动化质量保障。

评估维度：
1. 功能正确性 - 代码是否实现了预期功能
2. 代码质量 - 代码是否清晰、可读、遵循最佳实践
3. 架构合理性 - 架构设计是否合理
4. 安全性 - 是否存在安全隐患
5. 可维护性 - 代码是否易于维护和扩展
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum

from ..llm import LLMClient, LLMMessage
from ..config.models import DEFAULT_LLM_MODEL
from .prompts import VALIDATION_SYSTEM_PROMPT


class EvaluationVerdict(Enum):
    """评估结论"""
    ACCEPT = "accept"              # 接受
    NEEDS_REVISION = "needs_revision"  # 需要修改
    REJECT = "reject"              # 拒绝


@dataclass
class EvaluationScore:
    """评估分数"""
    functional_correctness: float = 0.0
    code_quality: float = 0.0
    architecture: float = 0.0
    security: float = 0.0
    maintainability: float = 0.0
    
    @property
    def overall(self) -> float:
        """计算总分"""
        scores = [
            self.functional_correctness,
            self.code_quality,
            self.architecture,
            self.security,
            self.maintainability,
        ]
        return sum(scores) / len(scores)


@dataclass
class EvaluationResult:
    """评估结果"""
    scores: EvaluationScore
    overall_score: float
    strengths: List[str]
    weaknesses: List[str]
    recommendations: List[str]
    verdict: EvaluationVerdict
    verdict_reason: str
    confidence: float = 0.8
    
    def is_acceptable(self, threshold: float = 7.0) -> bool:
        """判断是否可接受"""
        return self.overall_score >= threshold


@dataclass
class CodeArtifact:
    """代码产物"""
    file_path: str
    content: str
    language: str = "python"
    description: str = ""


class LLMEvaluator:
    """
    LLM-as-Judge 评估器
    
    使用 LLM 评估代码质量，基于 Anthropic 推荐。
    
    使用示例：
    ```python
    evaluator = LLMEvaluator(llm_client)
    result = evaluator.evaluate(
        code="def hello(): print('hello')",
        objective="实现 hello world 函数",
        success_criteria=["函数可以正常运行"]
    )
    print(f"Score: {result.overall_score}")
    ```
    """
    
    def __init__(
        self,
        llm_client: LLMClient | None = None,
        model: str = DEFAULT_LLM_MODEL,
    ):
        self.llm = llm_client
        self.model = model
    
    def evaluate(
        self,
        code: str | CodeArtifact | List[CodeArtifact],
        objective: str,
        success_criteria: List[str] | None = None,
        context: str = "",
    ) -> EvaluationResult:
        """
        评估代码质量
        
        Args:
            code: 代码内容（字符串、单个产物或产物列表）
            objective: 任务目标
            success_criteria: 成功标准
            context: 额外上下文
            
        Returns:
            评估结果
        """
        # 标准化输入
        artifacts = self._normalize_code_input(code)
        
        # 构建评估提示
        prompt = self._build_evaluation_prompt(
            artifacts=artifacts,
            objective=objective,
            success_criteria=success_criteria or [],
            context=context,
        )
        
        # 如果没有 LLM 客户端，使用启发式评估
        if not self.llm:
            return self._heuristic_evaluation(artifacts, objective, success_criteria)
        
        # 调用 LLM 评估
        try:
            response = self._call_llm(prompt)
            return self._parse_evaluation_response(response)
        except Exception as e:
            # 降级到启发式评估
            result = self._heuristic_evaluation(artifacts, objective, success_criteria)
            result.weaknesses.append(f"LLM 评估失败: {str(e)}")
            return result
    
    def evaluate_batch(
        self,
        items: List[Dict[str, Any]],
    ) -> List[EvaluationResult]:
        """批量评估"""
        return [self.evaluate(**item) for item in items]
    
    def _normalize_code_input(
        self,
        code: str | CodeArtifact | List[CodeArtifact],
    ) -> List[CodeArtifact]:
        """标准化代码输入"""
        if isinstance(code, str):
            return [CodeArtifact(
                file_path="unnamed.py",
                content=code,
            )]
        elif isinstance(code, CodeArtifact):
            return [code]
        elif isinstance(code, list):
            return code
        else:
            return [CodeArtifact(
                file_path="unknown",
                content=str(code),
            )]
    
    def _build_evaluation_prompt(
        self,
        artifacts: List[CodeArtifact],
        objective: str,
        success_criteria: List[str],
        context: str,
    ) -> str:
        """构建评估提示"""
        parts = []
        
        # 任务信息
        parts.append(f"## 任务目标\n{objective}\n")
        
        if success_criteria:
            parts.append("## 成功标准")
            for i, criterion in enumerate(success_criteria, 1):
                parts.append(f"{i}. {criterion}")
            parts.append("")
        
        if context:
            parts.append(f"## 上下文\n{context}\n")
        
        # 代码内容
        parts.append("## 待评估代码")
        for artifact in artifacts:
            parts.append(f"\n### 文件: {artifact.file_path}")
            if artifact.description:
                parts.append(f"描述: {artifact.description}")
            parts.append(f"```{artifact.language}")
            parts.append(artifact.content)
            parts.append("```\n")
        
        # 评估要求
        parts.append("""
## 评估要求

请对以上代码进行综合评估，输出 JSON 格式：

```json
{
  "scores": {
    "functional_correctness": 8,
    "code_quality": 7,
    "architecture": 8,
    "security": 9,
    "maintainability": 7
  },
  "overall_score": 7.8,
  "strengths": ["优点1", "优点2"],
  "weaknesses": ["弱点1", "弱点2"],
  "recommendations": ["建议1", "建议2"],
  "verdict": "accept|needs_revision|reject",
  "verdict_reason": "判断理由"
}
```

评分标准：
- 9-10分: 优秀，可直接使用
- 7-8分: 良好，小问题可接受
- 5-6分: 及格，需要小幅修改
- 3-4分: 较差，需要大幅修改
- 0-2分: 不可用，需要重写
""")
        
        return "\n".join(parts)
    
    def _call_llm(self, prompt: str) -> str:
        """调用 LLM"""
        messages = [
            LLMMessage(role="system", content=VALIDATION_SYSTEM_PROMPT),
            LLMMessage(role="user", content=prompt),
        ]
        
        response = self.llm.complete(messages)
        return response
    
    def _parse_evaluation_response(self, response: str) -> EvaluationResult:
        """解析 LLM 评估响应"""
        # 提取 JSON
        json_match = self._extract_json(response)
        
        if json_match:
            try:
                data = json.loads(json_match)
                
                scores = EvaluationScore(
                    functional_correctness=data.get("scores", {}).get("functional_correctness", 5.0),
                    code_quality=data.get("scores", {}).get("code_quality", 5.0),
                    architecture=data.get("scores", {}).get("architecture", 5.0),
                    security=data.get("scores", {}).get("security", 5.0),
                    maintainability=data.get("scores", {}).get("maintainability", 5.0),
                )
                
                verdict_str = data.get("verdict", "needs_revision")
                verdict = {
                    "accept": EvaluationVerdict.ACCEPT,
                    "needs_revision": EvaluationVerdict.NEEDS_REVISION,
                    "reject": EvaluationVerdict.REJECT,
                }.get(verdict_str, EvaluationVerdict.NEEDS_REVISION)
                
                return EvaluationResult(
                    scores=scores,
                    overall_score=data.get("overall_score", scores.overall),
                    strengths=data.get("strengths", []),
                    weaknesses=data.get("weaknesses", []),
                    recommendations=data.get("recommendations", []),
                    verdict=verdict,
                    verdict_reason=data.get("verdict_reason", ""),
                )
            except json.JSONDecodeError:
                pass
        
        # 解析失败，返回默认结果
        return EvaluationResult(
            scores=EvaluationScore(),
            overall_score=5.0,
            strengths=["LLM 响应解析失败"],
            weaknesses=["无法获取详细评估"],
            recommendations=["请检查 LLM 输出格式"],
            verdict=EvaluationVerdict.NEEDS_REVISION,
            verdict_reason="评估解析失败",
        )
    
    def _extract_json(self, text: str) -> str | None:
        """从文本中提取 JSON"""
        import re
        
        # 尝试找到代码块中的 JSON
        code_block = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
        if code_block:
            return code_block.group(1)
        
        # 尝试找到包含 scores 的 JSON 对象
        start = text.find('{')
        while start != -1:
            depth = 0
            end = start
            for i, char in enumerate(text[start:], start):
                if char == '{':
                    depth += 1
                elif char == '}':
                    depth -= 1
                    if depth == 0:
                        end = i
                        break
            
            if end > start:
                candidate = text[start:end+1]
                if '"scores"' in candidate:
                    return candidate
                start = text.find('{', start + 1)
            else:
                break
        
        return None

    def _heuristic_evaluation(
        self,
        artifacts: List[CodeArtifact],
        objective: str,
        success_criteria: List[str] | None,
    ) -> EvaluationResult:
        """
        启发式评估（无 LLM 时的降级方案）
        
        基于静态规则评估代码质量
        """
        scores = EvaluationScore()
        strengths = []
        weaknesses = []
        recommendations = []
        
        for artifact in artifacts:
            content = artifact.content
            lines = content.split('\n')
            
            # 功能正确性：检查是否有明显错误
            if "TODO" in content or "FIXME" in content:
                scores.functional_correctness += 5
                weaknesses.append(f"{artifact.file_path}: 包含未完成的 TODO/FIXME")
            else:
                scores.functional_correctness += 7
            
            # 代码质量：检查代码结构
            if len(lines) > 500:
                scores.code_quality += 4
                weaknesses.append(f"{artifact.file_path}: 文件过长 ({len(lines)} 行)")
            else:
                scores.code_quality += 7
            
            # 检查是否有文档字符串
            if '"""' in content or "'''" in content:
                scores.code_quality += 1
                strengths.append(f"{artifact.file_path}: 包含文档字符串")
            
            # 架构：检查是否有清晰的函数/类结构
            import re
            functions = re.findall(r'def \w+\(', content)
            classes = re.findall(r'class \w+', content)
            
            if functions or classes:
                scores.architecture += 7
                strengths.append(f"{artifact.file_path}: 结构清晰 ({len(functions)} 函数, {len(classes)} 类)")
            else:
                scores.architecture += 5
            
            # 安全性：检查常见安全问题
            security_issues = []
            if "eval(" in content:
                security_issues.append("使用了 eval()")
            if "exec(" in content:
                security_issues.append("使用了 exec()")
            if "password" in content.lower() and "=" in content:
                security_issues.append("可能硬编码了密码")
            
            if security_issues:
                scores.security += 4
                weaknesses.extend([f"{artifact.file_path}: {issue}" for issue in security_issues])
            else:
                scores.security += 8
            
            # 可维护性：检查代码复杂度
            avg_line_length = sum(len(line) for line in lines) / len(lines) if lines else 0
            if avg_line_length > 100:
                scores.maintainability += 4
                weaknesses.append(f"{artifact.file_path}: 平均行长度过长 ({avg_line_length:.0f})")
            else:
                scores.maintainability += 7
        
        # 平均分数
        n = len(artifacts) if artifacts else 1
        scores.functional_correctness /= n
        scores.code_quality /= n
        scores.architecture /= n
        scores.security /= n
        scores.maintainability /= n
        
        overall = scores.overall
        
        # 确定结论
        if overall >= 7.0:
            verdict = EvaluationVerdict.ACCEPT
            verdict_reason = "代码质量良好，可以接受"
        elif overall >= 5.0:
            verdict = EvaluationVerdict.NEEDS_REVISION
            verdict_reason = "代码需要小幅修改"
        else:
            verdict = EvaluationVerdict.REJECT
            verdict_reason = "代码质量较差，建议重写"
        
        if not strengths:
            strengths.append("启发式评估完成")
        
        recommendations.append("建议使用 LLM 进行更详细的评估")
        
        return EvaluationResult(
            scores=scores,
            overall_score=overall,
            strengths=strengths,
            weaknesses=weaknesses,
            recommendations=recommendations,
            verdict=verdict,
            verdict_reason=verdict_reason,
            confidence=0.6,  # 启发式评估置信度较低
        )


class HumanAICollaboration:
    """
    人机协作评估
    
    结合自动评估和人工审查，实现最佳质量保障。
    """
    
    def __init__(
        self,
        auto_threshold: float = 8.0,
        reject_threshold: float = 5.0,
    ):
        self.auto_threshold = auto_threshold
        self.reject_threshold = reject_threshold
    
    def should_request_human_review(
        self,
        auto_result: EvaluationResult,
        llm_result: EvaluationResult | None = None,
    ) -> bool:
        """
        判断是否需要人工审查
        
        规则：
        - 分数在 5.0-8.0 之间：需要人工审查
        - 有安全问题的：需要人工审查
        - LLM 和自动评估结果差异大的：需要人工审查
        """
        # 分数在灰色地带
        if self.reject_threshold < auto_result.overall_score < self.auto_threshold:
            return True
        
        # 有安全问题
        if auto_result.scores.security < 6.0:
            return True
        
        # LLM 评估结果差异
        if llm_result:
            score_diff = abs(auto_result.overall_score - llm_result.overall_score)
            if score_diff > 2.0:
                return True
            
            # 结论不一致
            if auto_result.verdict != llm_result.verdict:
                return True
        
        return False
    
    def create_review_request(
        self,
        auto_result: EvaluationResult,
        llm_result: EvaluationResult | None,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """创建人工审查请求"""
        return {
            "type": "human_review_request",
            "auto_evaluation": {
                "score": auto_result.overall_score,
                "verdict": auto_result.verdict.value,
                "strengths": auto_result.strengths[:3],
                "weaknesses": auto_result.weaknesses[:3],
            },
            "llm_evaluation": {
                "score": llm_result.overall_score if llm_result else None,
                "verdict": llm_result.verdict.value if llm_result else None,
                "strengths": llm_result.strengths[:3] if llm_result else [],
                "weaknesses": llm_result.weaknesses[:3] if llm_result else [],
            } if llm_result else None,
            "context": context,
            "questions": self._generate_review_questions(auto_result, llm_result),
        }
    
    def _generate_review_questions(
        self,
        auto_result: EvaluationResult,
        llm_result: EvaluationResult | None,
    ) -> List[str]:
        """生成审查问题"""
        questions = []
        
        if auto_result.scores.security < 7.0:
            questions.append("请确认代码是否存在安全隐患")
        
        if auto_result.scores.maintainability < 6.0:
            questions.append("代码可维护性较低，是否可以接受？")
        
        if llm_result and auto_result.verdict != llm_result.verdict:
            questions.append(f"自动评估({auto_result.verdict.value})与LLM评估({llm_result.verdict.value})不一致，请确认最终结论")
        
        if not questions:
            questions.append("请确认代码质量是否满足要求")
        
        return questions

