"""Learning capture and management for AOP."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from ..core.types import LearningCapture


class LearningLog:
    """Manages learning capture throughout the AOP workflow.

    Provides methods for capturing, storing, and exporting lessons learned
    from various phases of development and experimentation.
    """

    def __init__(self, storage_path: Path | str | None = None):
        """Initialize the learning log.

        Args:
            storage_path: Path to the JSON file for persisting learnings.
                         Defaults to '.aop/learning.json' in current directory.
        """
        if storage_path is None:
            self.storage_path = Path.cwd() / ".aop" / "learning.json"
        elif isinstance(storage_path, str):
            self.storage_path = Path(storage_path)
        else:
            self.storage_path = storage_path

        self.learnings: List[LearningCapture] = []
        self._persistence = self.storage_path is not None

        if self._persistence and self.storage_path.exists():
            self.load()

    def capture(
        self,
        phase: str,
        what_worked: List[str] | None = None,
        what_failed: List[str] | None = None,
        insights: List[str] | None = None,
    ) -> LearningCapture:
        """Capture learnings from a phase.

        Args:
            phase: Name of the phase
            what_worked: Things that worked well
            what_failed: Things that didn't work
            insights: Key insights gained

        Returns:
            The captured learning
        """
        learning = LearningCapture(
            phase=phase,
            what_worked=what_worked or [],
            what_failed=what_failed or [],
            insights=insights or [],
        )

        self.learnings.append(learning)
        return learning

    def get_by_phase(self, phase: str) -> List[LearningCapture]:
        """Get learnings by phase name.

        Args:
            phase: The phase name

        Returns:
            List of matching learnings
        """
        return [l for l in self.learnings if l.phase == phase]

    def list_phases(self) -> List[str]:
        """List all unique phases.

        Returns:
            List of phase names
        """
        return list(dict.fromkeys(l.phase for l in self.learnings))

    def save(self) -> None:
        """Save learnings to storage."""
        if not self._persistence:
            return

        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "version": 1,
            "saved_at": datetime.now().isoformat(),
            "learnings": [
                {
                    "phase": l.phase,
                    "what_worked": l.what_worked,
                    "what_failed": l.what_failed,
                    "insights": l.insights,
                }
                for l in self.learnings
            ],
        }

        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def load(self) -> None:
        """Load learnings from storage."""
        if not self._persistence or not self.storage_path.exists():
            return

        with open(self.storage_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        learnings_data = data.get("learnings", data if isinstance(data, list) else [])
        for ldata in learnings_data:
            if isinstance(ldata, dict):
                learning = LearningCapture(
                    phase=ldata.get("phase", "unknown"),
                    what_worked=ldata.get("what_worked", []),
                    what_failed=ldata.get("what_failed", []),
                    insights=ldata.get("insights", []),
                )
                self.learnings.append(learning)

    def export_lessons(self, output_path: Path | str) -> Path:
        """Export lessons learned to a markdown file.

        Args:
            output_path: Path to the output file

        Returns:
            Path to the exported file
        """
        output = Path(output_path)
        lines = [
            "# Lessons Learned",
            "",
            f"Exported: {datetime.now().isoformat()}",
            "",
        ]

        # Group by phase
        phases = {}
        for learning in self.learnings:
            if learning.phase not in phases:
                phases[learning.phase] = []
            phases[learning.phase].append(learning)

        for phase, phase_learnings in phases.items():
            lines.append(f"## {phase.title()} Phase")
            lines.append("")

            for i, learning in enumerate(phase_learnings, 1):
                if learning.what_worked:
                    lines.append("### What Worked")
                    for item in learning.what_worked:
                        lines.append(f"- {item}")
                    lines.append("")

                if learning.what_failed:
                    lines.append("### What Didn't Work")
                    for item in learning.what_failed:
                        lines.append(f"- {item}")
                    lines.append("")

                if learning.insights:
                    lines.append("### Key Insights")
                    for item in learning.insights:
                        lines.append(f"- {item}")
                    lines.append("")

        with open(output, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        return output

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of all learnings.

        Returns:
            Summary dictionary with counts
        """
        return {
            "total_learnings": len(self.learnings),
            "phases": len(self.list_phases()),
            "total_what_worked": sum(len(l.what_worked) for l in self.learnings),
            "total_what_failed": sum(len(l.what_failed) for l in self.learnings),
            "total_insights": sum(len(l.insights) for l in self.learnings),
        }


__all__ = ["LearningLog"]
