"""Report generation."""

from datetime import datetime
from pathlib import Path
from typing import List, Optional

from ..core.types import NormalizedFinding


class ReportGenerator:
    """Generate reports from review results."""
    
    @staticmethod
    def generate_markdown(findings, provider_results, duration, output_path=None):
        """Generate a markdown report."""
        lines = [
            "# Code Review Report",
            "",
            "**Generated:** " + datetime.now().isoformat(),
            "**Duration:** " + str(round(duration, 2)) + "s",
            "**Providers:** " + ", ".join(provider_results.keys()),
            "",
        ]
        
        lines.append("## Summary")
        lines.append("")
        lines.append("- **Total Findings:** " + str(len(findings)))
        
        severity_counts = {}
        for f in findings:
            severity_counts[f.severity] = severity_counts.get(f.severity, 0) + 1
        
        for sev in ["critical", "high", "medium", "low"]:
            if sev in severity_counts:
                lines.append("- **" + sev.upper() + ":** " + str(severity_counts[sev]))
        
        lines.append("")
        
        if findings:
            lines.append("## Findings")
            lines.append("")
            
            for f in findings:
                sev_emoji = {"critical": "X", "high": "!", "medium": "-", "low": "i"}
                emoji = sev_emoji.get(f.severity, "o")
                lines.append("### " + emoji + " " + f.title)
                lines.append("")
                lines.append("- **Severity:** " + f.severity)
                lines.append("- **Category:** " + f.category)
                lines.append("- **Detected by:** " + ", ".join(f.detected_by))
                
                if f.evidence.file:
                    lines.append("- **File:** " + f.evidence.file)
                    if f.evidence.line:
                        lines.append("- **Line:** " + str(f.evidence.line))
                
                lines.append("")
                lines.append("**Recommendation:** " + f.recommendation)
                lines.append("")
        
        report_text = "\n".join(lines)
        
        if output_path:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(report_text)
        
        return report_text