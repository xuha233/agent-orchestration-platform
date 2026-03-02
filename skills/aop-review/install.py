#!/usr/bin/env python3
"""Install script for AOP Review skill."""

import os
import shutil
from pathlib import Path

def install_skill():
    """Install the AOP Review skill to OpenClaw skills directory."""
    
    # Determine target directory
    home = Path.home()
    skills_dir = home / ".agents" / "skills" / "aop-review"
    
    # Create directory if it doesn't exist
    skills_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy SKILL.md
    skill_source = Path(__file__).parent / "SKILL.md"
    skill_target = skills_dir / "SKILL.md"
    
    if skill_source.exists():
        shutil.copy(skill_source, skill_target)
        print(f"Installed SKILL.md to {skill_target}")
    else:
        print(f"Warning: SKILL.md not found at {skill_source}")
    
    print("\nAOP Review skill installed successfully!")
    print("You can now use the skill by mentioning 'aop review' in your requests.")

if __name__ == "__main__":
    install_skill()
