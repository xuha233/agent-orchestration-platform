"""
Quality Reviewer.

Checks MVP code/document quality:
1. Readability - Is it clear and easy to understand?
2. Completeness - Are there missing parts?
3. Consistency - Is it internally consistent?
4. Best Practices - Does it follow recommended patterns?

Based on Superpowers research - code-quality-reviewer subagent.
"""

from __future__ import annotations

import re
from typing import List, Dict, Any, Optional

from .base import (
    ReviewStatus,
    ReviewIssue,
    ReviewResult,
    ReviewerBase,
)


class QualityReviewer(ReviewerBase):
    """
    Quality Reviewer.
    
    Checks MVP quality across multiple dimensions:
    - Readability
    - Completeness
    - Consistency
    - Best practices
    """
    
    def __init__(self):
        """Initialize the quality reviewer."""
        self._quality_checks = {
            "readability": self._check_readability,
            "completeness": self._check_completeness,
            "consistency": self._check_consistency,
            "best_practices": self._check_best_practices,
        }
    
    def get_description(self) -> str:
        """Return description of what this reviewer checks."""
        return "Checks code/document quality: readability, completeness, consistency, best practices"
    
    def review(self, content: str, context: dict) -> ReviewResult:
        """
        Execute quality review.
        
        Args:
            content: The content to review
            context: Optional context:
                - artifact_type: Type of artifact (mvp, code, doc)
                - language: Programming language (if code)
                - min_quality_score: Minimum acceptable score (default 60)
        
        Returns:
            ReviewResult with quality assessment
        """
        artifact_type = context.get("artifact_type", "mvp")
        language = context.get("language", "python")
        min_score = context.get("min_quality_score", 60)
        
        issues: List[ReviewIssue] = []
        scores: Dict[str, float] = {}
        
        # Run all quality checks
        for check_name, check_func in self._quality_checks.items():
            check_issues = check_func(content, artifact_type, context)
            issues.extend(check_issues)
            
            # Calculate score for this dimension
            scores[check_name] = self._calculate_dimension_score(
                check_issues,
                weight=1.0 if check_name in ["readability", "completeness"] else 0.8
            )
        
        # Calculate overall score
        overall_score = self._calculate_overall_score(scores)
        
        # Determine status based on issues and score
        critical_count = sum(1 for i in issues if i.severity == "critical")
        important_count = sum(1 for i in issues if i.severity == "important")
        
        if critical_count > 0:
            status = ReviewStatus.NEEDS_REVISION
        elif important_count > 2:
            status = ReviewStatus.NEEDS_REVISION
        elif overall_score < min_score:
            status = ReviewStatus.NEEDS_REVISION
        else:
            status = ReviewStatus.APPROVED
        
        summary = self._generate_summary(
            status=status,
            score=overall_score,
            scores=scores,
            issue_count=len(issues),
        )
        
        return self._create_result(
            status=status,
            issues=issues,
            summary=summary,
            score=overall_score,
        )
    
    def _check_readability(
        self,
        content: str,
        artifact_type: str,
        context: dict
    ) -> List[ReviewIssue]:
        """
        Check readability.
        
        Checks:
        - Clear naming
        - Appropriate comments
        - Logical structure
        - Not overly complex
        """
        issues: List[ReviewIssue] = []
        
        # Check for very long lines
        lines = content.split('\n')
        long_lines = [(i+1, line) for i, line in enumerate(lines) if len(line) > 120]
        for line_no, line in long_lines[:5]:  # Limit to 5 reports
            issues.append(self._create_issue(
                severity="minor",
                category="quality",
                description=f"Long line ({len(line)} chars) at line {line_no}",
                suggestion="Break into multiple lines for readability",
                location=f"line {line_no}",
            ))
        
        # Check for excessive nesting (code)
        if artifact_type == "code":
            nesting_issues = self._check_nesting(content)
            issues.extend(nesting_issues)
        
        # Check for unclear variable names
        naming_issues = self._check_naming(content, artifact_type)
        issues.extend(naming_issues)
        
        # Check for missing docstrings (Python)
        if artifact_type == "code" and context.get("language", "python") == "python":
            docstring_issues = self._check_docstrings(content)
            issues.extend(docstring_issues)
        
        # Check for unclear sections (docs)
        if artifact_type in ["doc", "mvp"]:
            section_issues = self._check_sections(content)
            issues.extend(section_issues)
        
        return issues
    
    def _check_nesting(self, content: str) -> List[ReviewIssue]:
        """Check for excessive code nesting."""
        issues: List[ReviewIssue] = []
        
        lines = content.split('\n')
        max_nesting = 0
        
        for i, line in enumerate(lines):
            # Count leading spaces/tabs
            stripped = line.lstrip()
            if not stripped:
                continue
            
            indent = len(line) - len(stripped)
            nesting = indent // 4  # Assume 4-space indent
            
            if nesting > max_nesting:
                max_nesting = nesting
        
        if max_nesting > 4:
            issues.append(self._create_issue(
                severity="important",
                category="quality",
                description=f"Excessive nesting detected (depth: {max_nesting})",
                suggestion="Refactor to reduce nesting (extract methods, early returns)",
            ))
        
        return issues
    
    def _check_naming(self, content: str, artifact_type: str) -> List[ReviewIssue]:
        """Check for unclear naming."""
        issues: List[ReviewIssue] = []
        
        # Single letter variable names (except common ones)
        single_letter_pattern = r'\b([xynijkm])\s*='
        matches = list(re.finditer(single_letter_pattern, content))
        
        if len(matches) > 5:
            issues.append(self._create_issue(
                severity="minor",
                category="quality",
                description=f"Many single-letter variable names ({len(matches)} found)",
                suggestion="Use descriptive names for better readability",
            ))
        
        # Very short function/class names
        short_name_pattern = r'(?:def|class|function)\s+([a-z]{1,2})\s*[\(:]'
        matches = list(re.finditer(short_name_pattern, content, re.IGNORECASE))
        
        for match in matches:
            issues.append(self._create_issue(
                severity="minor",
                category="quality",
                description=f"Short name '{match.group(1)}' may be unclear",
                suggestion="Use a more descriptive name",
                location=match.group(0),
            ))
        
        return issues
    
    def _check_docstrings(self, content: str) -> List[ReviewIssue]:
        """Check for missing docstrings in Python code."""
        issues: List[ReviewIssue] = []
        
        # Find functions without docstrings
        func_pattern = r'def\s+(\w+)\s*\([^)]*\)\s*:\s*\n(\s*)(?!\1["\'\'])'
        matches = list(re.finditer(func_pattern, content))
        
        for match in matches[:3]:  # Limit reports
            func_name = match.group(1)
            # Skip private/dunder methods
            if not func_name.startswith('_'):
                issues.append(self._create_issue(
                    severity="minor",
                    category="quality",
                    description=f"Function '{func_name}' missing docstring",
                    suggestion="Add a docstring explaining the function's purpose",
                ))
        
        return issues
    
    def _check_sections(self, content: str) -> List[ReviewIssue]:
        """Check document sections for clarity."""
        issues: List[ReviewIssue] = []
        
        # Check for clear section headers
        has_headers = bool(re.search(r'^#+\s+\w', content, re.MULTILINE))
        
        # Long document without headers
        if len(content) > 1000 and not has_headers:
            issues.append(self._create_issue(
                severity="important",
                category="quality",
                description="Long document without section headers",
                suggestion="Add headers (## Title) to improve navigation",
            ))
        
        return issues
    
    def _check_completeness(
        self,
        content: str,
        artifact_type: str,
        context: dict
    ) -> List[ReviewIssue]:
        """
        Check completeness.
        
        Checks:
        - No placeholder text
        - No TODO/FIXME
        - All sections have content
        """
        issues: List[ReviewIssue] = []
        
        # Check for placeholder text
        placeholders = [
            r'\[TBD\]',
            r'\[TODO\]',
            r'\[INSERT\s+.*?\]',
            r'\<\?.*?\?\>',
            r'\.\.\.+\s*$',
            r'待定',
            r'待补充',
            r'待完成',
        ]
        
        for pattern in placeholders:
            matches = list(re.finditer(pattern, content, re.IGNORECASE))
            for match in matches[:3]:
                issues.append(self._create_issue(
                    severity="important",
                    category="completeness",
                    description=f"Placeholder text found: {match.group(0)}",
                    suggestion="Replace with actual content",
                    location=f"position {match.start()}",
                ))
        
        # Check for empty sections
        empty_section_pattern = r'(#+\s+[^\n]+)\n\s*\n(?=#)'
        matches = list(re.finditer(empty_section_pattern, content))
        
        for match in matches[:3]:
            issues.append(self._create_issue(
                severity="important",
                category="completeness",
                description=f"Empty section: {match.group(1).strip()}",
                suggestion="Add content to this section",
            ))
        
        # Check for TODO comments
        todo_pattern = r'(TODO|FIXME|XXX|HACK):\s*(\S.*?)(?:\n|$)'
        matches = list(re.finditer(todo_pattern, content, re.IGNORECASE))
        
        for match in matches[:5]:
            issues.append(self._create_issue(
                severity="important",
                category="completeness",
                description=f"Unfinished work: {match.group(2).strip()}",
                suggestion="Complete or remove the TODO marker",
            ))
        
        return issues
    
    def _check_consistency(
        self,
        content: str,
        artifact_type: str,
        context: dict
    ) -> List[ReviewIssue]:
        """
        Check internal consistency.
        
        Checks:
        - Consistent terminology
        - Consistent formatting
        - Consistent naming conventions
        """
        issues: List[ReviewIssue] = []
        
        # Check for inconsistent terminology (simplified)
        # A more sophisticated version would use NLP
        
        # Check for mixed snake_case and camelCase (Python)
        if artifact_type == "code":
            snake_vars = re.findall(r'\b([a-z]+_[a-z_]+)\b', content)
            camel_vars = re.findall(r'\b([a-z]+[A-Z][a-z]+)\b', content)
            
            if snake_vars and camel_vars and len(snake_vars) > 5 and len(camel_vars) > 5:
                issues.append(self._create_issue(
                    severity="minor",
                    category="consistency",
                    description="Mixed naming conventions (snake_case and camelCase)",
                    suggestion="Use consistent naming throughout (snake_case for Python)",
                ))
        
        # Check for inconsistent header levels
        headers = re.findall(r'^(#{1,6})\s+', content, re.MULTILINE)
        if headers:
            levels = [len(h) for h in headers]
            # Check for skipped levels
            for i in range(len(levels) - 1):
                if levels[i+1] - levels[i] > 1:
                    issues.append(self._create_issue(
                        severity="minor",
                        category="consistency",
                        description=f"Header level jump from H{levels[i]} to H{levels[i+1]}",
                        suggestion="Don't skip header levels for better structure",
                    ))
                    break  # Only report once
        
        return issues
    
    def _check_best_practices(
        self,
        content: str,
        artifact_type: str,
        context: dict
    ) -> List[ReviewIssue]:
        """
        Check for best practices.
        
        Checks:
        - No hardcoded secrets
        - No deprecated patterns
        - Security best practices
        """
        issues: List[ReviewIssue] = []
        
        # Check for hardcoded secrets
        secret_patterns = [
            (r'password\s*=\s*["\'][^"\']+["\']', "password"),
            (r'api_key\s*=\s*["\'][^"\']+["\']', "API key"),
            (r'secret\s*=\s*["\'][^"\']+["\']', "secret"),
            (r'token\s*=\s*["\'][^"\']+["\']', "token"),
        ]
        
        for pattern, secret_type in secret_patterns:
            matches = list(re.finditer(pattern, content, re.IGNORECASE))
            for match in matches:
                issues.append(self._create_issue(
                    severity="critical",
                    category="security",
                    description=f"Hardcoded {secret_type} detected",
                    suggestion="Use environment variables or secure storage",
                    location=f"position {match.start()}",
                ))
        
        # Check for SQL injection risks
        sql_patterns = [
            r'execute\s*\(\s*["\'].*?\+.*?["\']',
            r'cursor\.execute\s*\(\s*f["\']',
        ]
        
        for pattern in sql_patterns:
            matches = list(re.finditer(pattern, content, re.IGNORECASE))
            for match in matches:
                issues.append(self._create_issue(
                    severity="critical",
                    category="security",
                    description="Potential SQL injection vulnerability",
                    suggestion="Use parameterized queries instead",
                    location=f"position {match.start()}",
                ))
        
        # Check for print statements in production code
        if artifact_type == "code":
            print_matches = list(re.finditer(r'\bprint\s*\(', content))
            if len(print_matches) > 3:
                issues.append(self._create_issue(
                    severity="minor",
                    category="quality",
                    description=f"Many print statements ({len(print_matches)} found)",
                    suggestion="Use logging instead of print for production code",
                ))
        
        return issues
    
    def _calculate_dimension_score(
        self,
        issues: List[ReviewIssue],
        weight: float = 1.0
    ) -> float:
        """Calculate score for a quality dimension."""
        # Start at 100
        score = 100.0
        
        # Deduct points for issues
        for issue in issues:
            if issue.severity == "critical":
                score -= 20 * weight
            elif issue.severity == "important":
                score -= 10 * weight
            else:
                score -= 5 * weight
        
        return max(0, min(100, score))
    
    def _calculate_overall_score(self, scores: Dict[str, float]) -> float:
        """Calculate overall quality score."""
        if not scores:
            return 100.0
        
        # Weighted average
        weights = {
            "readability": 1.0,
            "completeness": 1.0,
            "consistency": 0.8,
            "best_practices": 1.2,
        }
        
        total_weight = 0
        weighted_sum = 0
        
        for dimension, score in scores.items():
            weight = weights.get(dimension, 1.0)
            weighted_sum += score * weight
            total_weight += weight
        
        return weighted_sum / total_weight if total_weight > 0 else 100.0
    
    def _generate_summary(
        self,
        status: ReviewStatus,
        score: float,
        scores: Dict[str, float],
        issue_count: int,
    ) -> str:
        """Generate human-readable summary."""
        parts = [f"Quality review: {status.value}", f"Score: {score:.1f}/100"]
        
        # Show dimension scores
        if scores:
            score_parts = [f"{k}={v:.0f}" for k, v in scores.items()]
            parts.append(f"Dimensions: {', '.join(score_parts)}")
        
        if issue_count > 0:
            parts.append(f"{issue_count} issues found")
        
        return ". ".join(parts)
