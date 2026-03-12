"""
Base classes for the review system.

Provides the foundation for all reviewers with:
- ReviewStatus: Enum for review outcomes
- ReviewIssue: Dataclass for individual issues found
- ReviewResult: Dataclass for complete review results
- ReviewerBase: Abstract base class for all reviewers
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any


class ReviewStatus(Enum):
    """Review status enum."""
    
    PENDING = "pending"
    APPROVED = "approved"
    NEEDS_REVISION = "needs_revision"
    BLOCKED = "blocked"
    
    def __str__(self) -> str:
        return self.value


class IssueSeverity(Enum):
    """Issue severity levels."""
    
    CRITICAL = "critical"    # Must fix before proceeding
    IMPORTANT = "important"  # Should fix, but can proceed
    MINOR = "minor"          # Nice to fix, low priority
    
    def __str__(self) -> str:
        return self.value


class IssueCategory(Enum):
    """Issue category enum."""
    
    SPEC = "spec"              # Specification compliance
    QUALITY = "quality"        # Code/document quality
    SECURITY = "security"      # Security concerns
    PERFORMANCE = "performance"  # Performance issues
    MAINTAINABILITY = "maintainability"  # Maintainability
    COMPLETENESS = "completeness"  # Missing requirements
    CONSISTENCY = "consistency"  # Internal consistency
    OVERBUILD = "overbuild"    # Over-engineering
    
    def __str__(self) -> str:
        return self.value


@dataclass
class ReviewIssue:
    """
    A single issue found during review.
    
    Attributes:
        severity: Issue severity (critical, important, minor)
        category: Issue category (spec, quality, security, etc.)
        description: Clear description of the issue
        suggestion: How to fix the issue
        location: Optional file path or code location
        metadata: Additional metadata
    """
    
    severity: str  # critical, important, minor
    category: str  # spec, quality, security, etc.
    description: str
    suggestion: str
    location: Optional[str] = None  # File path or code location
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate severity and category."""
        valid_severities = {"critical", "important", "minor"}
        if self.severity not in valid_severities:
            raise ValueError(f"Invalid severity: {self.severity}. Must be one of {valid_severities}")
        
        valid_categories = {
            "spec", "quality", "security", "performance", 
            "maintainability", "completeness", "consistency", "overbuild"
        }
        if self.category not in valid_categories:
            raise ValueError(f"Invalid category: {self.category}. Must be one of {valid_categories}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "severity": self.severity,
            "category": self.category,
            "description": self.description,
            "suggestion": self.suggestion,
            "location": self.location,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ReviewIssue":
        """Create from dictionary."""
        return cls(
            severity=data["severity"],
            category=data["category"],
            description=data["description"],
            suggestion=data["suggestion"],
            location=data.get("location"),
            metadata=data.get("metadata", {}),
        )
    
    def __str__(self) -> str:
        """Human-readable string representation."""
        loc = f" [{self.location}]" if self.location else ""
        return f"[{self.severity.upper()}][{self.category}]{loc} {self.description}"


@dataclass
class ReviewResult:
    """
    Complete review result.
    
    Attributes:
        status: Overall review status
        issues: List of issues found
        summary: Human-readable summary
        score: Optional quality score (0-100)
        stage: Which review stage produced this result
        metadata: Additional metadata
    """
    
    status: ReviewStatus
    issues: List[ReviewIssue]
    summary: str
    score: Optional[float] = None  # 0-100 quality score
    stage: str = "unknown"  # spec_compliance, quality, etc.
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate score range."""
        if self.score is not None and not (0 <= self.score <= 100):
            raise ValueError(f"Score must be between 0 and 100, got {self.score}")
    
    @property
    def has_critical_issues(self) -> bool:
        """Check if there are any critical issues."""
        return any(i.severity == "critical" for i in self.issues)
    
    @property
    def has_important_issues(self) -> bool:
        """Check if there are any important issues."""
        return any(i.severity == "important" for i in self.issues)
    
    @property
    def issue_counts(self) -> Dict[str, int]:
        """Get counts by severity."""
        counts = {"critical": 0, "important": 0, "minor": 0}
        for issue in self.issues:
            counts[issue.severity] = counts.get(issue.severity, 0) + 1
        return counts
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "status": self.status.value,
            "issues": [i.to_dict() for i in self.issues],
            "summary": self.summary,
            "score": self.score,
            "stage": self.stage,
            "metadata": self.metadata,
            "has_critical_issues": self.has_critical_issues,
            "issue_counts": self.issue_counts,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ReviewResult":
        """Create from dictionary."""
        return cls(
            status=ReviewStatus(data["status"]),
            issues=[ReviewIssue.from_dict(i) for i in data["issues"]],
            summary=data["summary"],
            score=data.get("score"),
            stage=data.get("stage", "unknown"),
            metadata=data.get("metadata", {}),
        )
    
    def __str__(self) -> str:
        """Human-readable string representation."""
        counts = self.issue_counts
        issue_str = ", ".join(f"{k}={v}" for k, v in counts.items() if v > 0)
        return f"[{self.status.value.upper()}] {self.summary} ({issue_str})"


class ReviewerBase(ABC):
    """
    Abstract base class for all reviewers.
    
    Subclasses must implement:
    - review(): Execute the review
    
    Subclasses can override:
    - get_name(): Return a custom reviewer name
    - get_description(): Return a description of what this reviewer checks
    """
    
    @abstractmethod
    def review(self, content: str, context: dict) -> ReviewResult:
        """
        Execute the review.
        
        Args:
            content: The content to review (code, document, etc.)
            context: Additional context for the review
                - spec: The specification to check against
                - artifact_type: Type of artifact (mvp, code, doc, etc.)
                - requirements: List of requirements
                - metadata: Additional metadata
        
        Returns:
            ReviewResult with status, issues, and summary
        """
        pass
    
    def get_name(self) -> str:
        """Get the reviewer name."""
        return self.__class__.__name__
    
    def get_description(self) -> str:
        """Get a description of what this reviewer checks."""
        return "Base reviewer - override get_description() in subclass"
    
    def _create_result(
        self,
        status: ReviewStatus,
        issues: List[ReviewIssue],
        summary: str,
        score: Optional[float] = None,
    ) -> ReviewResult:
        """Helper to create a ReviewResult with the correct stage."""
        return ReviewResult(
            status=status,
            issues=issues,
            summary=summary,
            score=score,
            stage=self.get_name(),
        )
    
    def _create_issue(
        self,
        severity: str,
        category: str,
        description: str,
        suggestion: str,
        location: Optional[str] = None,
    ) -> ReviewIssue:
        """Helper to create a ReviewIssue."""
        return ReviewIssue(
            severity=severity,
            category=category,
            description=description,
            suggestion=suggestion,
            location=location,
        )
