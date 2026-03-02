"""Learning capture with persistence support."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from ...core.types import LearningCapture
from ..persistence import PersistenceManager, get_persistence_manager


class LearningLog:
    """Manages learning records with optional persistence.
    
    Attributes:
        storage_path: Optional path for persistence
        learnings: List of captured learnings
        _persistence: Optional persistence manager
    """
    
    def __init__(self, storage_path: Path | None = None):
        """Initialize the learning log.
        
        Args:
            storage_path: Optional path for JSON file persistence
        """
        self.storage_path = storage_path
        self.learnings: List[LearningCapture] = []
        self._persistence: PersistenceManager | None = None
        
        if storage_path:
            sp = Path(storage_path) if isinstance(storage_path, str) else storage_path
            self._persistence = PersistenceManager(sp)
            self._load_from_storage()
    
    def _load_from_storage(self) -> None:
        """Load learnings from storage if available."""
        if not self._persistence:
            return
        
        data = self._persistence.load("learnings")
        if data:
            records = data.get("records", [])
            for record in records:
                self.learnings.append(LearningCapture(
                    phase=record.get("phase", ""),
                    what_worked=record.get("what_worked", []),
                    what_failed=record.get("what_failed", []),
                    insights=record.get("insights", []),
                ))
    
    def capture(self, phase: str, what_worked: List[str | None] = None,
                what_failed: List[str | None] = None, insights: List[str | None] = None) -> LearningCapture:
        """Capture learning from a phase.
        
        Args:
            phase: Phase name
            what_worked: List of things that worked
            what_failed: List of things that failed
            insights: List of key insights
            
        Returns:
            The created LearningCapture object
        """
        learning = LearningCapture(
            phase=phase,
            what_worked=what_worked or [],
            what_failed=what_failed or [],
            insights=insights or []
        )
        self.learnings.append(learning)
        return learning
    
    def get_lessons_learned(self) -> Dict[str, List[str]]:
        """Get aggregated lessons learned.
        
        Returns:
            Dictionary with 'what_worked', 'what_failed', and 'insights' lists
        """
        worked, failed, insights = [], [], []
        for learning in self.learnings:
            worked.extend(learning.what_worked)
            failed.extend(learning.what_failed)
            insights.extend(learning.insights)
        return {"what_worked": list(set(worked)), "what_failed": list(set(failed)), "insights": list(set(insights))}
    
    def save(self) -> Path | None:
        """Save learnings to persistent storage.
        
        Returns:
            Path to saved file, or None if no persistence configured
        """
        if not self._persistence:
            return None
        
        records = []
        for learning in self.learnings:
            records.append({
                "phase": learning.phase,
                "what_worked": list(learning.what_worked),
                "what_failed": list(learning.what_failed),
                "insights": list(learning.insights),
            })
        
        return self._persistence.save("learnings", {"records": records})
    
    def load(self) -> bool:
        """Load learnings from persistent storage.
        
        Returns:
            True if loaded successfully, False otherwise
        """
        if not self._persistence:
            return False
        
        self.learnings = []  # Clear existing before loading
        self._load_from_storage()
        return True
    
    def export_lessons(self, output_path: Path | None = None) -> Path | None:
        """Export lessons learned to a markdown file.
        
        Args:
            output_path: Optional output file path
            
        Returns:
            Path to exported file, or None if no persistence configured
        """
        if not self._persistence:
            if output_path:
                # Write directly to output path
                lines = ["# Lessons Learned", "", self._format_lessons_markdown()]
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write("\n".join(lines))
                return output_path
            return None
        
        return self._persistence.export_to_markdown("learnings", output_path)
    
    def _format_lessons_markdown(self) -> str:
        """Format lessons learned as markdown."""
        lessons = self.get_lessons_learned()
        lines = []
        
        if lessons["what_worked"]:
            lines.append("## What Worked")
            for item in lessons["what_worked"]:
                lines.append(f"- {item}")
            lines.append("")
        
        if lessons["what_failed"]:
            lines.append("## What Failed")
            for item in lessons["what_failed"]:
                lines.append(f"- {item}")
            lines.append("")
        
        if lessons["insights"]:
            lines.append("## Key Insights")
            for item in lessons["insights"]:
                lines.append(f"- {item}")
            lines.append("")
        
        return "\n".join(lines)
    
    def to_dict(self) -> Dict[str, Any]:
        """Export learnings as a dictionary.
        
        Returns:
            Dictionary with learning records
        """
        return {
            "records": [
                {
                    "phase": l.phase,
                    "what_worked": list(l.what_worked),
                    "what_failed": list(l.what_failed),
                    "insights": list(l.insights),
                }
                for l in self.learnings
            ]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], storage_path: Path | None = None) -> "LearningLog":
        """Create a LearningLog from a dictionary.
        
        Args:
            data: Dictionary with learning records
            storage_path: Optional storage path
            
        Returns:
            New LearningLog instance
        """
        log = cls(storage_path=storage_path)
        records = data.get("records", [])
        for record in records:
            log.learnings.append(LearningCapture(
                phase=record.get("phase", ""),
                what_worked=record.get("what_worked", []),
                what_failed=record.get("what_failed", []),
                insights=record.get("insights", []),
            ))
        return log
