"""Hypothesis management for AOP."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from ..core.types import Hypothesis, HypothesisState


class HypothesisManager:
    """Manages hypothesis lifecycle.

    Provides methods for creating, updating, and querying hypotheses
    that are used to track experiments and validations in the AOP workflow.
    """

    def __init__(self, storage_path: Path | str | None = None):
        """Initialize the hypothesis manager.

        Args:
            storage_path: Path to the JSON file for persisting hypotheses.
                         Defaults to '.aop/hypotheses.json' in current directory.
        """
        if storage_path is None:
            self.storage_path = Path.cwd() / ".aop" / "hypotheses.json"
        elif isinstance(storage_path, str):
            self.storage_path = Path(storage_path)
        else:
            self.storage_path = storage_path

        self._hypotheses: Dict[str, Hypothesis] = {}
        self._persistence = self.storage_path is not None

        if self._persistence and self.storage_path.exists():
            self.load()

    def create(
        self,
        statement: str,
        validation_method: str = "",
        priority: str = "quick_win",
        success_criteria: List[str] | None = None,
    ) -> Hypothesis:
        """Create a new hypothesis.

        Args:
            statement: The hypothesis statement
            validation_method: How to validate this hypothesis
            priority: Priority level (quick_win or deep_dive)
            success_criteria: List of criteria for success

        Returns:
            The created hypothesis
        """
        # Generate ID
        count = len(self._hypotheses) + 1
        hypothesis_id = f"H-{count:03d}"

        hypothesis = Hypothesis(
            hypothesis_id=hypothesis_id,
            statement=statement,
            validation_method=validation_method,
            success_criteria=success_criteria or [],
            state=HypothesisState.PENDING,
            priority=priority,
        )

        self._hypotheses[hypothesis_id] = hypothesis
        return hypothesis

    def get(self, hypothesis_id: str) -> Optional[Hypothesis]:
        """Get a hypothesis by ID.

        Args:
            hypothesis_id: The hypothesis ID

        Returns:
            The hypothesis or None if not found
        """
        return self._hypotheses.get(hypothesis_id)

    def update_state(
        self, hypothesis_id: str, new_state: HypothesisState
    ) -> Optional[Hypothesis]:
        """Update the state of a hypothesis.

        Args:
            hypothesis_id: The hypothesis ID
            new_state: The new state

        Returns:
            The updated hypothesis or None if not found
        """
        hypothesis = self._hypotheses.get(hypothesis_id)
        if hypothesis:
            hypothesis.state = new_state
            return hypothesis
        return None

    def list_all(self) -> List[Hypothesis]:
        """List all hypotheses.

        Returns:
            List of all hypotheses
        """
        return list(self._hypotheses.values())

    def list_by_state(self, state: Optional[HypothesisState]) -> List[Hypothesis]:
        """List hypotheses filtered by state.

        Args:
            state: The state to filter by, or None for all

        Returns:
            List of matching hypotheses
        """
        if state is None:
            return self.list_all()
        return [h for h in self._hypotheses.values() if h.state == state]

    def delete(self, hypothesis_id: str) -> bool:
        """Delete a hypothesis.

        Args:
            hypothesis_id: The hypothesis ID

        Returns:
            True if deleted, False if not found
        """
        if hypothesis_id in self._hypotheses:
            del self._hypotheses[hypothesis_id]
            return True
        return False

    def save(self) -> None:
        """Save hypotheses to storage."""
        if not self._persistence:
            return

        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "version": 1,
            "saved_at": datetime.now().isoformat(),
            "hypotheses": {
                hid: {
                    "hypothesis_id": h.hypothesis_id,
                    "statement": h.statement,
                    "validation_method": h.validation_method,
                    "success_criteria": h.success_criteria,
                    "state": h.state.value if isinstance(h.state, HypothesisState) else str(h.state),
                    "priority": h.priority,
                    "findings": [],  # Serialize findings if needed
                }
                for hid, h in self._hypotheses.items()
            },
        }

        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def load(self) -> None:
        """Load hypotheses from storage."""
        if not self._persistence or not self.storage_path.exists():
            return

        with open(self.storage_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        hypotheses_data = data.get("hypotheses", data)
        for hid, hdata in hypotheses_data.items():
            if hid.startswith("_"):
                continue
            state_value = hdata.get("state", "pending")
            try:
                state = HypothesisState(state_value)
            except ValueError:
                state = HypothesisState.PENDING

            hypothesis = Hypothesis(
                hypothesis_id=hdata.get("hypothesis_id", hid),
                statement=hdata.get("statement", ""),
                validation_method=hdata.get("validation_method", ""),
                success_criteria=hdata.get("success_criteria", []),
                state=state,
                priority=hdata.get("priority", "quick_win"),
            )
            self._hypotheses[hid] = hypothesis

    def export_markdown(self, output_path: Path | str) -> Path:
        """Export hypotheses to a markdown file.

        Args:
            output_path: Path to the output file

        Returns:
            Path to the exported file
        """
        output = Path(output_path)
        lines = [
            "# Hypotheses",
            "",
            f"Exported: {datetime.now().isoformat()}",
            "",
            "## Quick Wins",
            "",
        ]

        quick_wins = [h for h in self._hypotheses.values() if h.priority == "quick_win"]
        deep_dives = [h for h in self._hypotheses.values() if h.priority == "deep_dive"]

        if quick_wins:
            lines.append("| ID | Statement | State |")
            lines.append("|----|-----------|-------|")
            for h in quick_wins:
                state_str = h.state.value if isinstance(h.state, HypothesisState) else str(h.state)
                lines.append(f"| {h.hypothesis_id} | {h.statement} | {state_str} |")
            lines.append("")

        lines.append("## Deep Dives")
        lines.append("")

        if deep_dives:
            lines.append("| ID | Statement | State |")
            lines.append("|----|-----------|-------|")
            for h in deep_dives:
                state_str = h.state.value if isinstance(h.state, HypothesisState) else str(h.state)
                lines.append(f"| {h.hypothesis_id} | {h.statement} | {state_str} |")
            lines.append("")

        with open(output, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        return output


__all__ = ["HypothesisManager"]
