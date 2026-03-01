"""Team configuration."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

from ...core.types import ComplexityAssessment, ProjectType, TeamConfig


class TeamOrchestrator:
    def __init__(self):
        self.assessment: Optional[ComplexityAssessment] = None
        self.team_config: Optional[TeamConfig] = None
    
    def assess_project(self, problem_clarity: str = "medium", data_availability: str = "medium",
                       tech_novelty: str = "medium", business_risk: str = "medium") -> ComplexityAssessment:
        self.assessment = ComplexityAssessment(
            problem_clarity=problem_clarity, data_availability=data_availability,
            tech_novelty=tech_novelty, business_risk=business_risk
        )
        pt = self.assessment.to_project_type()
        self.team_config = TeamConfig.from_project_type(pt)
        return self.assessment
    
    def get_team_config(self) -> Optional[TeamConfig]:
        return self.team_config
    
    def get_strategy(self) -> Dict[str, str]:
        if not self.team_config:
            return {}
        strategies = {
            ProjectType.EXPLORATORY: {"approach": "fast-fail", "focus": "learning"},
            ProjectType.OPTIMIZATION: {"approach": "predictable", "focus": "delivery"},
            ProjectType.TRANSFORMATION: {"approach": "value_gates", "focus": "balanced"},
            ProjectType.COMPLIANCE_SENSITIVE: {"approach": "strict", "focus": "compliance"},
        }
        return strategies.get(self.team_config.project_type, {})
