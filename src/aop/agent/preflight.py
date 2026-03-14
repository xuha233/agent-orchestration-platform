# -*- coding: utf-8 -*-
"""
Pre-flight Validation - 任务前验证系统

基于 Anthropic 研究：在执行任务前进行验证，避免重复执行和浪费资源。

验证项：
1. 代码是否已存在
2. 任务是否已完成
3. 环境是否就绪
4. 工作目录是否正确
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum


class PreFlightStatus(Enum):
    """预检状态"""
    READY = "ready"                 # 准备就绪
    ALREADY_DONE = "already_done"   # 任务已完成
    SKIP_RECOMMENDED = "skip"       # 建议跳过
    BLOCKING_ISSUE = "blocked"      # 存在阻塞问题
    WARNING = "warning"             # 有警告但可继续


@dataclass
class PreFlightCheck:
    """单个预检项"""
    name: str
    description: str
    status: PreFlightStatus
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    recommendation: str = ""


@dataclass
class PreFlightResult:
    """预检结果"""
    overall_status: PreFlightStatus
    checks: List[PreFlightCheck]
    can_proceed: bool
    skip_reason: str = ""
    recommendations: List[str] = field(default_factory=list)

    def summary(self) -> str:
        """生成摘要"""
        lines = [f"预检状态: {self.overall_status.value}"]
        for check in self.checks:
            emoji = {
                PreFlightStatus.READY: "✅",
                PreFlightStatus.ALREADY_DONE: "⏭️",
                PreFlightStatus.SKIP_RECOMMENDED: "⏭️",
                PreFlightStatus.BLOCKING_ISSUE: "❌",
                PreFlightStatus.WARNING: "⚠️",
            }.get(check.status, "❓")
            lines.append(f"  {emoji} {check.name}: {check.message}")
        return "\n".join(lines)


class PreFlightValidator:
    """
    任务前验证器
    
    在执行任务前进行一系列检查，避免重复执行。
    
    使用示例：
    ```python
    validator = PreFlightValidator()
    result = validator.validate(task)
    if result.can_proceed:
        # 执行任务
        pass
    else:
        # 处理问题
        print(result.summary())
    ```
    """
    
    def __init__(self, repo_root: Path | str = "."):
        self.repo_root = Path(repo_root)
    
    def validate(
        self,
        task: Dict[str, Any],
        hypothesis: Dict[str, Any] | None = None,
    ) -> PreFlightResult:
        """
        执行预检
        
        Args:
            task: 任务信息（包含 objective, output_format, boundaries 等）
            hypothesis: 关联的假设信息
            
        Returns:
            预检结果
        """
        checks = []
        
        # 1. 检查代码是否已存在
        checks.append(self._check_code_exists(task))
        
        # 2. 检查任务是否已完成（通过成功标准判断）
        checks.append(self._check_task_completed(task, hypothesis))
        
        # 3. 检查工作目录
        checks.append(self._check_working_directory())
        
        # 4. 检查环境（可选）
        checks.append(self._check_environment(task))
        
        # 综合判断
        overall_status, can_proceed = self._determine_overall_status(checks)
        
        recommendations = [
            c.recommendation for c in checks 
            if c.recommendation
        ]
        
        skip_reason = ""
        if overall_status == PreFlightStatus.ALREADY_DONE:
            skip_reason = "任务已完成，无需重复执行"
        elif overall_status == PreFlightStatus.SKIP_RECOMMENDED:
            skip_reason = "建议跳过此任务"
        
        return PreFlightResult(
            overall_status=overall_status,
            checks=checks,
            can_proceed=can_proceed,
            skip_reason=skip_reason,
            recommendations=recommendations,
        )
    
    def _check_code_exists(self, task: Dict[str, Any]) -> PreFlightCheck:
        """
        检查代码是否已存在
        
        分析任务描述，提取关键文件名/功能名，检查是否已存在
        """
        objective = task.get("objective", "")
        boundaries = task.get("boundaries", "")
        
        # 提取可能的文件名关键词
        file_keywords = self._extract_file_keywords(objective)
        
        found_files = []
        for keyword in file_keywords:
            # 搜索匹配的文件
            for py_file in self.repo_root.rglob("*.py"):
                if keyword.lower() in py_file.name.lower():
                    found_files.append(str(py_file.relative_to(self.repo_root)))
        
        if found_files:
            return PreFlightCheck(
                name="代码存在检查",
                description="检查目标代码是否已存在",
                status=PreFlightStatus.ALREADY_DONE,
                message=f"发现可能已存在的文件: {', '.join(found_files[:3])}",
                details={"found_files": found_files},
                recommendation="请确认是否需要重新实现，或跳过此任务",
            )
        
        return PreFlightCheck(
            name="代码存在检查",
            description="检查目标代码是否已存在",
            status=PreFlightStatus.READY,
            message="未发现已存在的相关代码",
        )
    
    def _check_task_completed(
        self, 
        task: Dict[str, Any],
        hypothesis: Dict[str, Any] | None,
    ) -> PreFlightCheck:
        """
        检查任务是否已完成
        
        根据成功标准检查任务是否已完成
        """
        success_criteria = task.get("success_criteria", [])
        
        if not success_criteria:
            return PreFlightCheck(
                name="任务完成检查",
                description="检查任务是否已完成",
                status=PreFlightStatus.READY,
                message="无明确的成功标准，无法判断",
            )
        
        # 检查每个成功标准
        passed = []
        failed = []
        
        for criterion in success_criteria:
            if self._check_criterion(criterion):
                passed.append(criterion)
            else:
                failed.append(criterion)
        
        if not failed:
            return PreFlightCheck(
                name="任务完成检查",
                description="检查任务是否已完成",
                status=PreFlightStatus.ALREADY_DONE,
                message="所有成功标准已满足",
                details={"passed": passed},
                recommendation="任务已完成，可以跳过",
            )
        
        if passed:
            return PreFlightCheck(
                name="任务完成检查",
                description="检查任务是否已完成",
                status=PreFlightStatus.WARNING,
                message=f"部分成功标准已满足 ({len(passed)}/{len(success_criteria)})",
                details={"passed": passed, "failed": failed},
            )
        
        return PreFlightCheck(
            name="任务完成检查",
            description="检查任务是否已完成",
            status=PreFlightStatus.READY,
            message="成功标准尚未满足",
            details={"failed": failed},
        )
    
    def _check_working_directory(self) -> PreFlightCheck:
        """检查工作目录"""
        if not self.repo_root.exists():
            return PreFlightCheck(
                name="工作目录检查",
                description="检查工作目录是否存在",
                status=PreFlightStatus.BLOCKING_ISSUE,
                message=f"工作目录不存在: {self.repo_root}",
            )
        
        # 检查是否是 git 仓库
        git_dir = self.repo_root / ".git"
        if git_dir.exists():
            return PreFlightCheck(
                name="工作目录检查",
                description="检查工作目录是否存在",
                status=PreFlightStatus.READY,
                message=f"工作目录正常 (git 仓库)",
            )
        
        return PreFlightCheck(
            name="工作目录检查",
            description="检查工作目录是否存在",
            status=PreFlightStatus.WARNING,
            message=f"工作目录存在，但不是 git 仓库",
        )
    
    def _check_environment(self, task: Dict[str, Any]) -> PreFlightCheck:
        """检查环境（工具、依赖等）"""
        # 基本环境检查
        issues = []
        
        # 检查 Python
        try:
            result = subprocess.run(
                ["python", "--version"],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=5,
            )
            if result.returncode != 0:
                issues.append("Python 不可用")
        except Exception:
            issues.append("Python 检查失败")
        
        # 检查 git
        try:
            result = subprocess.run(
                ["git", "--version"],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=5,
            )
            if result.returncode != 0:
                issues.append("Git 不可用")
        except Exception:
            pass  # Git 可选
        
        if issues:
            return PreFlightCheck(
                name="环境检查",
                description="检查环境依赖",
                status=PreFlightStatus.WARNING,
                message=f"环境问题: {', '.join(issues)}",
                details={"issues": issues},
            )
        
        return PreFlightCheck(
            name="环境检查",
            description="检查环境依赖",
            status=PreFlightStatus.READY,
            message="环境检查通过",
        )
    
    def _extract_file_keywords(self, text: str) -> List[str]:
        """从文本中提取可能的文件名关键词"""
        keywords = []
        
        # 常见的模块/文件命名模式
        patterns = [
            # 直接提到文件名
            r'(\w+)\.py',
            r'(\w+)\.ts',
            r'(\w+)\.js',
            # 模块名
            r'创建\s+(\w+)\s+模块',
            r'实现\s+(\w+)\s+功能',
            r'添加\s+(\w+)\s+组件',
            r'构建\s+(\w+)\s+服务',
            r'编写\s+(\w+)\s+类',
        ]
        
        import re
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            keywords.extend(matches)
        
        # 过滤掉太短或太通用的词
        stop_words = {"the", "a", "an", "is", "are", "to", "for", "and", "or"}
        keywords = [
            k for k in keywords 
            if len(k) > 2 and k.lower() not in stop_words
        ]
        
        return list(set(keywords))
    
    def _check_criterion(self, criterion: str) -> bool:
        """
        检查单个成功标准
        
        这是一个简化实现，实际可以使用更复杂的逻辑
        """
        # 如果成功标准提到具体文件，检查是否存在
        import re
        
        # 提取文件路径
        file_match = re.search(r'[\w/\\]+\.(py|ts|js|json)', criterion)
        if file_match:
            file_path = self.repo_root / file_match.group()
            if file_path.exists():
                return True
        
        # 如果提到函数/类名，搜索代码
        func_match = re.search(r'(\w+)\s*(?:函数|类|方法)', criterion)
        if func_match:
            func_name = func_match.group(1)
            # 在代码中搜索
            for py_file in self.repo_root.rglob("*.py"):
                try:
                    content = py_file.read_text(encoding="utf-8")
                    if f"def {func_name}" in content or f"class {func_name}" in content:
                        return True
                except Exception:
                    continue
        
        return False
    
    def _determine_overall_status(
        self, 
        checks: List[PreFlightCheck]
    ) -> Tuple[PreFlightStatus, bool]:
        """确定整体状态"""
        statuses = [c.status for c in checks]
        
        # 如果有任何阻塞问题
        if PreFlightStatus.BLOCKING_ISSUE in statuses:
            return PreFlightStatus.BLOCKING_ISSUE, False
        
        # 如果任务已完成
        if PreFlightStatus.ALREADY_DONE in statuses:
            return PreFlightStatus.ALREADY_DONE, False
        
        # 如果建议跳过
        if PreFlightStatus.SKIP_RECOMMENDED in statuses:
            return PreFlightStatus.SKIP_RECOMMENDED, False
        
        # 如果有警告
        if PreFlightStatus.WARNING in statuses:
            return PreFlightStatus.WARNING, True
        
        return PreFlightStatus.READY, True


def run_preflight(
    task: Dict[str, Any],
    repo_root: Path | str = ".",
) -> PreFlightResult:
    """
    便捷函数：执行预检
    
    Args:
        task: 任务信息
        repo_root: 仓库根目录
        
    Returns:
        预检结果
    """
    validator = PreFlightValidator(repo_root)
    return validator.validate(task)


