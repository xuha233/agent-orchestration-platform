"""Team orchestration for AOP."""

from __future__ import annotations

from typing import List, Optional, Dict, Any

from ..core.types import ComplexityAssessment, TeamConfig, ProjectType


class TeamOrchestrator:
    """Orchestrates team configuration based on project complexity.

    Analyzes project characteristics and recommends appropriate team
    composition and workflow patterns.
    """

    def __init__(self):
        """Initialize the team orchestrator."""
        self._assessment: Optional[ComplexityAssessment] = None
        self._team_config: Optional[TeamConfig] = None

    def assess_project(
        self,
        problem_clarity: str = "medium",
        data_availability: str = "medium",
        tech_novelty: str = "medium",
        business_risk: str = "medium",
    ) -> ComplexityAssessment:
        """Assess project complexity.

        Args:
            problem_clarity: How well-defined is the problem (low/medium/high)
            data_availability: Availability of training/test data (low/medium/high)
            tech_novelty: Level of technical innovation required (low/medium/high)
            business_risk: Business impact of failure (low/medium/high)

        Returns:
            The complexity assessment
        """
        self._assessment = ComplexityAssessment(
            problem_clarity=problem_clarity,
            data_availability=data_availability,
            tech_novelty=tech_novelty,
            business_risk=business_risk,
        )
        return self._assessment

    def get_team_config(self) -> Optional[TeamConfig]:
        """Get team configuration based on assessment.

        Returns:
            The recommended team configuration, or None if not assessed
        """
        if self._assessment is None:
            return None

        project_type = self._assessment.to_project_type()
        self._team_config = TeamConfig.from_project_type(project_type)
        return self._team_config

    def get_recommended_iteration_length(self) -> str:
        """Get recommended iteration length.

        Returns:
            Recommended iteration length
        """
        if self._team_config:
            return self._team_config.iteration_length

        # Default recommendations based on project type
        if self._assessment:
            project_type = self._assessment.to_project_type()
            lengths = {
                ProjectType.EXPLORATORY: "1 week",
                ProjectType.OPTIMIZATION: "2 weeks",
                ProjectType.TRANSFORMATION: "2 weeks",
                ProjectType.COMPLIANCE_SENSITIVE: "4 weeks",
            }
            return lengths.get(project_type, "2 weeks")

        return "2 weeks"

    def get_agent_roles(self) -> List[Dict[str, str]]:
        """Get detailed agent role descriptions.

        Returns:
            List of agent role dictionaries
        """
        roles = [
            {
                "id": "product_owner",
                "name": "Product Owner",
                "description": "Defines requirements and priorities",
                "capabilities": ["planning", "prioritization", "stakeholder_management"],
            },
            {
                "id": "data",
                "name": "Data Engineer",
                "description": "Handles data pipeline and quality",
                "capabilities": ["data_pipeline", "etl", "data_quality"],
            },
            {
                "id": "ml",
                "name": "ML Engineer",
                "description": "Builds and deploys ML models",
                "capabilities": ["model_training", "feature_engineering", "model_deployment"],
            },
            {
                "id": "dev",
                "name": "Software Developer",
                "description": "Writes and maintains application code",
                "capabilities": ["coding", "testing", "code_review"],
            },
            {
                "id": "ux",
                "name": "UX Designer",
                "description": "Designs user experience",
                "capabilities": ["user_research", "prototyping", "usability_testing"],
            },
            {
                "id": "devops",
                "name": "DevOps Engineer",
                "description": "Manages infrastructure and deployment",
                "capabilities": ["ci_cd", "monitoring", "infrastructure"],
            },
            {
                "id": "ethics",
                "name": "Ethics Specialist",
                "description": "Ensures ethical AI practices",
                "capabilities": ["bias_detection", "fairness_analysis", "compliance"],
            },
        ]
        return roles

    def get_workflow_phases(self) -> List[Dict[str, Any]]:
        """Get recommended workflow phases.

        Returns:
            List of phase definitions
        """
        phases = [
            {
                "id": "discovery",
                "name": "Discovery",
                "description": "Understand requirements and constraints",
                "duration": "1-2 weeks",
                "deliverables": ["requirements_doc", "tech_spec"],
            },
            {
                "id": "design",
                "name": "Design",
                "description": "Design architecture and approach",
                "duration": "1-2 weeks",
                "deliverables": ["architecture_doc", "design_specs"],
            },
            {
                "id": "implementation",
                "name": "Implementation",
                "description": "Build and test solution",
                "duration": "2-4 weeks",
                "deliverables": ["code", "tests", "documentation"],
            },
            {
                "id": "validation",
                "name": "Validation",
                "description": "Validate against requirements",
                "duration": "1-2 weeks",
                "deliverables": ["validation_report", "metrics"],
            },
            {
                "id": "deployment",
                "name": "Deployment",
                "description": "Deploy to production",
                "duration": "1 week",
                "deliverables": ["deployment_guide", "runbook"],
            },
        ]
        return phases


__all__ = ["TeamOrchestrator"]
