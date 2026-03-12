"""
Two-Stage Review Coordinator.

Implements the two-stage review process:
1. Spec Compliance Review - Must pass before quality review
2. Quality Review - Only runs if spec compliance passes

Based on Superpowers research - two-phase review pattern.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Callable, Optional, Dict, Any

from .base import (
    ReviewStatus,
    ReviewIssue,
    ReviewResult,
    ReviewerBase,
)
from .spec_compliance import SpecComplianceReviewer
from .quality import QualityReviewer


@dataclass
class TwoStageReviewResult:
    """
    Combined result from two-stage review.
    
    Contains results from both stages and overall assessment.
    """
    
    spec_result: ReviewResult
    quality_result: Optional[ReviewResult]
    overall_status: ReviewStatus
    overall_score: float
    all_issues: List[ReviewIssue]
    summary: str
    iterations: int = 1
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "spec_result": self.spec_result.to_dict(),
            "quality_result": self.quality_result.to_dict() if self.quality_result else None,
            "overall_status": self.overall_status.value,
            "overall_score": self.overall_score,
            "all_issues": [i.to_dict() for i in self.all_issues],
            "summary": self.summary,
            "iterations": self.iterations,
        }


class TwoStageReviewer:
    """
    Two-Stage Review Coordinator.
    
    Stage 1: Spec Compliance
    - Checks if all requirements are met
    - Checks for overbuilding
    - Must pass before Stage 2
    
    Stage 2: Quality Review
    - Checks code/document quality
    - Only runs if Stage 1 passes
    
    This ensures MVPs meet specifications before
    spending time on quality improvements.
    """
    
    def __init__(
        self,
        spec_reviewer: Optional[SpecComplianceReviewer] = None,
        quality_reviewer: Optional[QualityReviewer] = None,
    ):
        """
        Initialize two-stage reviewer.
        
        Args:
            spec_reviewer: Custom spec compliance reviewer
            quality_reviewer: Custom quality reviewer
        """
        self.spec_reviewer = spec_reviewer or SpecComplianceReviewer()
        self.quality_reviewer = quality_reviewer or QualityReviewer()
    
    def review(
        self,
        artifact_type: str,
        content: str,
        spec: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> TwoStageReviewResult:
        """
        Execute two-stage review.
        
        Args:
            artifact_type: Type of artifact (mvp, code, doc)
            content: The content to review
            spec: The specification to check against
            context: Additional context
        
        Returns:
            TwoStageReviewResult with both stage results
        """
        context = context or {}
        context["artifact_type"] = artifact_type
        context["spec"] = spec
        
        # Stage 1: Spec Compliance
        spec_result = self.spec_reviewer.review(content, context)
        
        # Stage 2: Quality (only if Stage 1 passes)
        quality_result = None
        
        if spec_result.status == ReviewStatus.APPROVED:
            # Spec passed, run quality review
            quality_result = self.quality_reviewer.review(content, context)
        
        # Combine results
        all_issues = list(spec_result.issues)
        if quality_result:
            all_issues.extend(quality_result.issues)
        
        # Determine overall status
        overall_status = self._determine_overall_status(spec_result, quality_result)
        
        # Calculate overall score
        overall_score = self._calculate_overall_score(spec_result, quality_result)
        
        # Generate summary
        summary = self._generate_summary(
            spec_result=spec_result,
            quality_result=quality_result,
            overall_status=overall_status,
        )
        
        return TwoStageReviewResult(
            spec_result=spec_result,
            quality_result=quality_result,
            overall_status=overall_status,
            overall_score=overall_score,
            all_issues=all_issues,
            summary=summary,
            iterations=1,
        )
    
    def review_with_fix_loop(
        self,
        artifact_type: str,
        content: str,
        spec: str,
        fix_callback: Callable[[List[ReviewIssue]], str],
        max_iterations: int = 3,
        context: Optional[Dict[str, Any]] = None,
    ) -> TwoStageReviewResult:
        """
        Execute two-stage review with automatic fix loop.
        
        After each review, if issues are found, calls fix_callback
        to get fixed content. Repeats until approved or max_iterations.
        
        Args:
            artifact_type: Type of artifact (mvp, code, doc)
            content: Initial content to review
            spec: The specification to check against
            fix_callback: Function that takes issues and returns fixed content
            max_iterations: Maximum fix iterations (default 3)
            context: Additional context
        
        Returns:
            TwoStageReviewResult from final iteration
        """
        current_content = content
        context = context or {}
        
        for iteration in range(1, max_iterations + 1):
            result = self.review(artifact_type, current_content, spec, context)
            result.iterations = iteration
            
            if result.overall_status == ReviewStatus.APPROVED:
                return result
            
            # If blocked or no fix needed, stop
            if result.overall_status == ReviewStatus.BLOCKED:
                return result
            
            # Get fixed content
            try:
                current_content = fix_callback(result.all_issues)
            except Exception as e:
                # Fix failed, return current result
                result.summary += f" Fix iteration failed: {str(e)}"
                return result
        
        # Max iterations reached
        final_result = self.review(artifact_type, current_content, spec, context)
        final_result.iterations = max_iterations
        final_result.summary += f" Max iterations ({max_iterations}) reached."
        
        return final_result
    
    def _determine_overall_status(
        self,
        spec_result: ReviewResult,
        quality_result: Optional[ReviewResult],
    ) -> ReviewStatus:
        """Determine overall review status."""
        # If spec failed, overall is needs revision
        if spec_result.status != ReviewStatus.APPROVED:
            return spec_result.status
        
        # Spec passed, check quality
        if quality_result is None:
            return ReviewStatus.APPROVED
        
        return quality_result.status
    
    def _calculate_overall_score(
        self,
        spec_result: ReviewResult,
        quality_result: Optional[ReviewResult],
    ) -> float:
        """Calculate overall quality score."""
        # Spec compliance is weighted higher
        spec_weight = 0.6
        quality_weight = 0.4
        
        spec_score = spec_result.score if spec_result.score is not None else 80.0
        
        if quality_result is None:
            # No quality review, spec score is the score
            return spec_score
        
        quality_score = quality_result.score if quality_result.score is not None else 80.0
        
        # If spec has issues, reduce quality contribution
        if spec_result.status != ReviewStatus.APPROVED:
            return spec_score * 0.8 + quality_score * 0.2
        
        return spec_score * spec_weight + quality_score * quality_weight
    
    def _generate_summary(
        self,
        spec_result: ReviewResult,
        quality_result: Optional[ReviewResult],
        overall_status: ReviewStatus,
    ) -> str:
        """Generate human-readable summary."""
        parts = [f"Two-stage review: {overall_status.value}"]
        
        # Stage 1 summary
        stage1_status = "PASSED" if spec_result.status == ReviewStatus.APPROVED else "FAILED"
        parts.append(f"Stage 1 (Spec): {stage1_status}")
        
        if spec_result.issues:
            parts.append(f"  {len(spec_result.issues)} spec issues")
        
        # Stage 2 summary
        if quality_result:
            stage2_status = "PASSED" if quality_result.status == ReviewStatus.APPROVED else "FAILED"
            parts.append(f"Stage 2 (Quality): {stage2_status}")
            
            if quality_result.issues:
                parts.append(f"  {len(quality_result.issues)} quality issues")
            
            if quality_result.score is not None:
                parts.append(f"  Score: {quality_result.score:.1f}/100")
        else:
            parts.append("Stage 2 (Quality): SKIPPED (spec issues)")
        
        return ". ".join(parts)


def review_mvp(
    content: str,
    spec: str,
    context: Optional[Dict[str, Any]] = None,
) -> TwoStageReviewResult:
    """
    Convenience function to review an MVP.
    
    Args:
        content: MVP content to review
        spec: Specification text
        context: Additional context
    
    Returns:
        TwoStageReviewResult
    """
    reviewer = TwoStageReviewer()
    return reviewer.review("mvp", content, spec, context)


def review_code(
    content: str,
    spec: str,
    context: Optional[Dict[str, Any]] = None,
) -> TwoStageReviewResult:
    """
    Convenience function to review code.
    
    Args:
        content: Code content to review
        spec: Specification text
        context: Additional context
    
    Returns:
        TwoStageReviewResult
    """
    reviewer = TwoStageReviewer()
    return reviewer.review("code", content, spec, context)


def review_document(
    content: str,
    spec: str,
    context: Optional[Dict[str, Any]] = None,
) -> TwoStageReviewResult:
    """
    Convenience function to review a document.
    
    Args:
        content: Document content to review
        spec: Specification text
        context: Additional context
    
    Returns:
        TwoStageReviewResult
    """
    reviewer = TwoStageReviewer()
    return reviewer.review("doc", content, spec, context)
