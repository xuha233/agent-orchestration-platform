"""Persistence utilities for workflow data."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, TypeVar, Generic, Protocol
from dataclasses import asdict, is_dataclass

T = TypeVar("T")


class Serializable(Protocol):
    """Protocol for objects that can be serialized."""
    def to_dict(self) -> Dict[str, Any]:
        ...
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Serializable":
        ...


class PersistenceManager:
    """Manages persistence of workflow data to JSON files.
    
    This class provides a unified interface for saving and loading
    various workflow data structures including hypotheses, learnings,
    and other data.
    """
    
    def __init__(self, base_path: Optional[Path | str] = None):
        """Initialize persistence manager.
        
        Args:
            base_path: Base directory for storing data files.
                      Defaults to '.aop/data' in current directory.
        """
        if base_path is None:
            self.base_path = Path(".aop/data")
        elif isinstance(base_path, str):
            self.base_path = Path(base_path)
        else:
            self.base_path = base_path
        self._ensure_directory()
    
    def _ensure_directory(self) -> None:
        """Ensure the base directory exists."""
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def _get_file_path(self, name: str) -> Path:
        """Get full path for a named data file.
        
        Args:
            name: Name of the data file (without extension)
            
        Returns:
            Full path to the JSON file
        """
        return self.base_path / f"{name}.json"
    
    def save(self, name: str, data: Dict[str, Any]) -> Path:
        """Save data to a JSON file.
        
        Args:
            name: Name for the data file
            data: Dictionary to save
            
        Returns:
            Path to the saved file
        """
        file_path = self._get_file_path(name)
        
        # Add metadata
        payload = {
            "_meta": {
                "saved_at": datetime.now().isoformat(),
                "version": 1,
            },
            "data": data,
        }
        
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False, default=str)
        
        return file_path
    
    def load(self, name: str) -> Optional[Dict[str, Any]]:
        """Load data from a JSON file.
        
        Args:
            name: Name of the data file
            
        Returns:
            Loaded data dictionary, or None if file does not exist
        """
        file_path = self._get_file_path(name)
        
        if not file_path.exists():
            return None
        
        with open(file_path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        
        # Handle both old and new format
        if "data" in payload:
            return payload["data"]
        return payload
    
    def exists(self, name: str) -> bool:
        """Check if a data file exists.
        
        Args:
            name: Name of the data file
            
        Returns:
            True if file exists, False otherwise
        """
        return self._get_file_path(name).exists()
    
    def delete(self, name: str) -> bool:
        """Delete a data file.
        
        Args:
            name: Name of the data file
            
        Returns:
            True if file was deleted, False if it did not exist
        """
        file_path = self._get_file_path(name)
        if file_path.exists():
            file_path.unlink()
            return True
        return False
    
    def list_saved(self) -> List[str]:
        """List all saved data file names.
        
        Returns:
            List of data file names (without extension)
        """
        if not self.base_path.exists():
            return []
        
        return [f.stem for f in self.base_path.glob("*.json")]
    
    def save_hypotheses(self, hypotheses: Dict[str, Any]) -> Path:
        """Save hypotheses data.
        
        Args:
            hypotheses: Dictionary of hypothesis data
            
        Returns:
            Path to the saved file
        """
        return self.save("hypotheses", hypotheses)
    
    def load_hypotheses(self) -> Optional[Dict[str, Any]]:
        """Load hypotheses data.
        
        Returns:
            Dictionary of hypothesis data, or None if not found
        """
        return self.load("hypotheses")
    
    def save_learnings(self, learnings: List[Dict[str, Any]]) -> Path:
        """Save learning records.
        
        Args:
            learnings: List of learning records
            
        Returns:
            Path to the saved file
        """
        return self.save("learnings", {"records": learnings})
    
    def load_learnings(self) -> Optional[List[Dict[str, Any]]]:
        """Load learning records.
        
        Returns:
            List of learning records, or None if not found
        """
        data = self.load("learnings")
        if data is None:
            return None
        return data.get("records", [])
    
    def export_to_markdown(self, name: str, output_path: Optional[Path] = None) -> Optional[Path]:
        """Export data to a markdown file.
        
        Args:
            name: Name of the data file to export
            output_path: Optional output path (defaults to same name with .md)
            
        Returns:
            Path to the exported file, or None if source does not exist
        """
        data = self.load(name)
        if data is None:
            return None
        
        output = output_path or self.base_path / f"{name}.md"
        
        lines = [f"# {name.title()}", "", f"Exported: {datetime.now().isoformat()}", ""]
        
        if name == "hypotheses":
            lines.extend(self._format_hypotheses_markdown(data))
        elif name == "learnings":
            lines.extend(self._format_learnings_markdown(data))
        else:
            lines.extend(self._format_generic_markdown(data))
        
        with open(output, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        
        return output
    
    def _format_hypotheses_markdown(self, data: Dict[str, Any]) -> List[str]:
        """Format hypotheses data as markdown."""
        lines = ["## Hypotheses", ""]
        
        for hid, h in data.items():
            if hid.startswith("_"):
                continue
            state = h.get("state", "pending")
            statement = h.get("statement", "")
            priority = h.get("priority", "")
            
            lines.append(f"### {hid}")
            lines.append(f"- **Statement:** {statement}")
            lines.append(f"- **State:** {state}")
            lines.append(f"- **Priority:** {priority}")
            lines.append("")
        
        return lines
    
    def _format_learnings_markdown(self, data: Dict[str, Any]) -> List[str]:
        """Format learnings data as markdown."""
        lines = ["## Learning Records", ""]
        
        records = data.get("records", [])
        for i, record in enumerate(records, 1):
            phase = record.get("phase", "unknown")
            lines.append(f"### {i}. {phase.title()} Phase")
            
            if record.get("what_worked"):
                lines.append("**What Worked:**")
                for item in record["what_worked"]:
                    lines.append(f"- {item}")
                lines.append("")
            
            if record.get("what_failed"):
                lines.append("**What Failed:**")
                for item in record["what_failed"]:
                    lines.append(f"- {item}")
                lines.append("")
            
            if record.get("insights"):
                lines.append("**Insights:**")
                for item in record["insights"]:
                    lines.append(f"- {item}")
                lines.append("")
        
        return lines
    
    def _format_generic_markdown(self, data: Dict[str, Any]) -> List[str]:
        """Format generic data as markdown."""
        lines = ["```json", json.dumps(data, indent=2, ensure_ascii=False), "```"]
        return lines


# Singleton instance for convenience
_default_manager: Optional[PersistenceManager] = None


def get_persistence_manager(base_path: Optional[Path] = None) -> PersistenceManager:
    """Get the default persistence manager instance.
    
    Args:
        base_path: Optional base path (only used on first call)
        
    Returns:
        PersistenceManager instance
    """
    global _default_manager
    if _default_manager is None:
        _default_manager = PersistenceManager(base_path)
    return _default_manager
