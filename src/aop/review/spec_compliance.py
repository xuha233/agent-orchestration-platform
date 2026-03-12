"""
Spec Compliance Reviewer.

Checks if MVP meets the confirmed specification requirements.
Detects overbuilding (extra features beyond spec) and missing requirements.

Based on Superpowers research - spec-reviewer subagent.
"""

from __future__ import annotations

import re
from typing import List, Optional, Dict, Any, Set

from .base import (
    ReviewStatus,
    ReviewIssue,
    ReviewResult,
    ReviewerBase,
)


class SpecComplianceReviewer(ReviewerBase):
    """
    Spec Compliance Reviewer.
    
    Checks MVP against confirmed specification:
    1. Are all required features implemented?
    2. Is there overbuilding (extra features)?
    3. Does implementation match the spec?
    
    The spec should be user-confirmed requirements document.
    """
    
    def __init__(self):
        """Initialize the spec compliance reviewer."""
        self._requirement_patterns = [
            # Common requirement patterns
            r'(?:must|should|shall|need to|required to)\s+(.+?)(?:\.|,|;|$)',
            r'(?:feature|function|capability):\s*(.+?)(?:\.|,|;|$)',
            r'(?:用户需要|必须|应该|要求)[：:]\s*(.+?)(?:\.|,|;|$)',
            r'-\s*\[([ x])\]\s*(.+?)(?:$)',  # Checkbox format
        ]
    
    def get_description(self) -> str:
        """Return description of what this reviewer checks."""
        return "Checks if MVP meets specification requirements and detects overbuilding"
    
    def review(self, content: str, context: dict) -> ReviewResult:
        """
        Execute spec compliance review.
        
        Args:
            content: The MVP content to review
            context: Must contain:
                - spec: The specification text
                - artifact_type: Type of artifact (mvp, code, doc)
                Optional:
                - requirements: Explicit list of requirements
                - strict_mode: If True, any extra feature is flagged
        
        Returns:
            ReviewResult with compliance status
        """
        spec = context.get("spec", "")
        artifact_type = context.get("artifact_type", "mvp")
        explicit_requirements = context.get("requirements", [])
        strict_mode = context.get("strict_mode", False)
        
        issues: List[ReviewIssue] = []
        
        # Extract requirements from spec
        requirements = self._extract_requirements(spec)
        if explicit_requirements:
            requirements.extend(explicit_requirements)
        
        # Check each requirement
        missing_requirements = []
        for req in requirements:
            if not self._check_requirement_met(content, req):
                missing_requirements.append(req)
                issues.append(self._create_issue(
                    severity="critical",
                    category="spec",
                    description=f"Missing requirement: {req}",
                    suggestion=f"Implement: {req}",
                ))
        
        # Check for overbuilding
        extras = self._find_extras(content, spec, artifact_type)
        for extra in extras:
            sev = "important" if strict_mode else "minor"
            issues.append(self._create_issue(
                severity=sev,
                category="overbuild",
                description=f"Overbuilding detected: {extra}",
                suggestion="Remove extra features or add to spec if intentional",
            ))
        
        # Check for spec deviations
        deviations = self._find_deviations(content, spec)
        for dev in deviations:
            issues.append(self._create_issue(
                severity="important",
                category="spec",
                description=f"Spec deviation: {dev['description']}",
                suggestion=dev.get("suggestion", "Align implementation with spec"),
            ))
        
        # Determine status
        if any(i.severity == "critical" for i in issues):
            status = ReviewStatus.NEEDS_REVISION
        elif any(i.severity == "important" for i in issues):
            status = ReviewStatus.NEEDS_REVISION
        else:
            status = ReviewStatus.APPROVED
        
        # Calculate compliance score
        score = self._calculate_compliance_score(
            total_requirements=len(requirements),
            met_requirements=len(requirements) - len(missing_requirements),
            overbuild_count=len(extras),
        )
        
        summary = self._generate_summary(
            status=status,
            requirements=len(requirements),
            missing=len(missing_requirements),
            extras=len(extras),
            deviations=len(deviations),
        )
        
        return self._create_result(
            status=status,
            issues=issues,
            summary=summary,
            score=score,
        )
    
    def _extract_requirements(self, spec: str) -> List[str]:
        """
        Extract requirements from specification text.
        
        Looks for:
        - Must/should/shall statements
        - Feature lists
        - Checkbox items
        - Chinese requirement patterns
        """
        if not spec:
            return []
        
        requirements: List[str] = []
        
        for pattern in self._requirement_patterns:
            matches = re.findall(pattern, spec, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                # Handle checkbox format (returns tuple)
                if isinstance(match, tuple):
                    req_text = match[1] if len(match) > 1 else match[0]
                else:
                    req_text = match
                
                req_text = req_text.strip()
                if req_text and len(req_text) > 3:
                    requirements.append(req_text)
        
        # Also look for bullet points
        bullet_pattern = r'^\s*[-*]\s*(.+?)$'
        for line in spec.split('\n'):
            match = re.match(bullet_pattern, line)
            if match:
                req = match.group(1).strip()
                if req and len(req) > 3 and req not in requirements:
                    # Only add if it looks like a requirement
                    if any(kw in req.lower() for kw in ['must', 'should', 'need', 'require', '必须', '应该', '要求']):
                        requirements.append(req)
        
        return list(set(requirements))  # Deduplicate
    
    def _check_requirement_met(self, content: str, requirement: str) -> bool:
        """
        Check if a single requirement is met in the content.
        
        Uses fuzzy matching to handle variations in how requirements
        are implemented vs specified.
        """
        if not content or not requirement:
            return False
        
        # Normalize both
        content_lower = content.lower()
        req_lower = requirement.lower()
        
        # Direct substring match
        if req_lower in content_lower:
            return True
        
        # Extract key terms from requirement
        key_terms = self._extract_key_terms(requirement)
        if not key_terms:
            return False
        
        # Check if most key terms are present
        matches = sum(1 for term in key_terms if term.lower() in content_lower)
        threshold = max(1, len(key_terms) * 0.6)  # 60% of terms should match
        
        return matches >= threshold
    
    def _extract_key_terms(self, text: str) -> List[str]:
        """Extract key terms from text, filtering out common words."""
        stop_words = {
            'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
            'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
            'would', 'could', 'should', 'may', 'might', 'must', 'shall',
            'can', 'need', 'to', 'of', 'in', 'for', 'on', 'with', 'at',
            'by', 'from', 'as', 'into', 'through', 'during', 'before',
            'after', 'above', 'below', 'between', 'under', 'again',
            'further', 'then', 'once', 'here', 'there', 'when', 'where',
            'why', 'how', 'all', 'each', 'few', 'more', 'most', 'other',
            'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same',
            'so', 'than', 'too', 'very', 'just', 'and', 'but', 'if',
            'or', 'because', 'until', 'while', 'this', 'that', 'these',
            'those', 'it', 'its', 'user', 'users', 'system', 'app',
            # Chinese stop words
            '的', '了', '是', '在', '有', '和', '与', '或', '等', '这', '那',
        }
        
        # Split on non-alphanumeric (keep Chinese characters)
        words = re.findall(r'[\w\u4e00-\u9fff]+', text.lower())
        
        return [w for w in words if w not in stop_words and len(w) > 1]
    
    def _find_extras(
        self, 
        content: str, 
        spec: str, 
        artifact_type: str
    ) -> List[str]:
        """
        Find overbuilt features not in spec.
        
        Detects features in content that weren't requested in spec.
        """
        extras: List[str] = []
        
        if not content or not spec:
            return extras
        
        # Extract all potential features from content
        content_features = self._extract_features(content, artifact_type)
        spec_features = self._extract_features(spec, artifact_type)
        
        # Normalize for comparison
        spec_normalized = {self._normalize_feature(f) for f in spec_features}
        
        for feature in content_features:
            normalized = self._normalize_feature(feature)
            
            # Check if this feature is mentioned in spec
            if normalized not in spec_normalized:
                # Check for partial match (feature might be part of larger requirement)
                is_covered = any(
                    normalized in spec_f or spec_f in normalized
                    for spec_f in spec_normalized
                )
                
                if not is_covered:
                    extras.append(feature)
        
        return extras[:10]  # Limit to 10 extras to avoid noise
    
    def _extract_features(self, text: str, artifact_type: str) -> List[str]:
        """Extract feature mentions from text."""
        features: List[str] = []
        
        # Look for common feature patterns
        patterns = [
            r'(?:add|implement|create|build|support)\s+(.+?)(?:\.|,|;|$)',
            r'(?:feature|function|capability):\s*(.+?)(?:\.|,|;|$)',
            r'(?:新增|添加|实现|创建|支持)[：:]\s*(.+?)(?:\.|,|;|$)',
            r'function\s+(\w+)\s*\(',  # Function definitions
            r'class\s+(\w+)\s*[:\{]',  # Class definitions
            r'def\s+(\w+)\s*\(',  # Python function definitions
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            features.extend(m.strip() for m in matches if isinstance(m, str))
        
        return list(set(features))
    
    def _normalize_feature(self, feature: str) -> str:
        """Normalize feature text for comparison."""
        # Lowercase and remove common prefixes/suffixes
        normalized = feature.lower().strip()
        
        # Remove articles
        normalized = re.sub(r'^\s*(the|a|an)\s+', '', normalized)
        
        # Remove trailing punctuation
        normalized = re.sub(r'[^\w\s\u4e00-\u9fff]$', '', normalized)
        
        return normalized
    
    def _find_deviations(self, content: str, spec: str) -> List[Dict[str, str]]:
        """
        Find cases where implementation deviates from spec.
        
        Looks for:
        - Different behavior than specified
        - Missing edge cases
        - Incorrect implementations
        """
        deviations: List[Dict[str, str]] = []
        
        # This is a simplified check - a real implementation would need
        # more sophisticated analysis (potentially using an LLM)
        
        # Check for TODO/FIXME markers (indicate incomplete implementation)
        todo_pattern = r'(TODO|FIXME|XXX|HACK):\s*(.+?)(?:$|\n)'
        for match in re.finditer(todo_pattern, content, re.IGNORECASE):
            deviations.append({
                "description": f"Unfinished implementation: {match.group(2).strip()}",
                "suggestion": "Complete the implementation or remove TODO marker",
            })
        
        return deviations
    
    def _calculate_compliance_score(
        self,
        total_requirements: int,
        met_requirements: int,
        overbuild_count: int,
    ) -> float:
        """Calculate compliance score (0-100)."""
        if total_requirements == 0:
            return 100.0  # No requirements = full compliance
        
        # Base score from requirement coverage
        coverage_score = (met_requirements / total_requirements) * 80
        
        # Penalty for overbuilding
        overbuild_penalty = min(20, overbuild_count * 5)
        
        return max(0, min(100, coverage_score - overbuild_penalty))
    
    def _generate_summary(
        self,
        status: ReviewStatus,
        requirements: int,
        missing: int,
        extras: int,
        deviations: int,
    ) -> str:
        """Generate human-readable summary."""
        parts = [f"Spec compliance: {status.value}"]
        
        if requirements > 0:
            met = requirements - missing
            parts.append(f"{met}/{requirements} requirements met")
        
        if missing > 0:
            parts.append(f"{missing} missing")
        
        if extras > 0:
            parts.append(f"{extras} extra features (overbuild)")
        
        if deviations > 0:
            parts.append(f"{deviations} deviations")
        
        return ". ".join(parts)
