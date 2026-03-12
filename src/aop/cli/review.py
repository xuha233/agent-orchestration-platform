"""
Review CLI commands.

Two-stage review mechanism:
1. Spec compliance review
2. Quality review

Usage:
    aop review mvp <file> --spec <spec_file>
    aop review spec <file>
    aop review quality <file>
"""

import click
import json
import sys
from pathlib import Path
from typing import Optional

from aop.review import (
    ReviewStatus,
    SpecComplianceReviewer,
    QualityReviewer,
    TwoStageReviewer,
)


@click.group()
def review():
    """Review MVPs, code, and documents using two-stage review."""
    pass


@review.command()
@click.argument("file", type=click.Path(exists=True))
@click.option("--spec", "-s", "spec_file", type=click.Path(exists=True), required=True,
              help="Specification file to check against")
@click.option("--artifact-type", "-t", default="mvp",
              type=click.Choice(["mvp", "code", "doc"]),
              help="Type of artifact to review")
@click.option("--output", "-o", type=click.Path(),
              help="Output file for results (JSON)")
@click.option("--format", "-f", "output_format", default="text",
              type=click.Choice(["text", "json", "markdown"]),
              help="Output format")
def mvp(file: str, spec_file: str, artifact_type: str, output: Optional[str], output_format: str):
    """Review an MVP against a specification.
    
    Runs two-stage review:
    1. Spec compliance check
    2. Quality check (only if spec passes)
    
    Example:
        aop review mvp my_mvp.py --spec requirements.md
    """
    # Read files
    content = Path(file).read_text(encoding="utf-8")
    spec = Path(spec_file).read_text(encoding="utf-8")
    
    # Run review
    reviewer = TwoStageReviewer()
    result = reviewer.review(artifact_type, content, spec)
    
    # Output results
    if output_format == "json":
        output_data = result.to_dict()
        if output:
            Path(output).write_text(json.dumps(output_data, indent=2, ensure_ascii=False))
            click.echo(f"Results written to {output}")
        else:
            click.echo(json.dumps(output_data, indent=2, ensure_ascii=False))
    
    elif output_format == "markdown":
        md = _format_markdown(result, file, spec_file)
        if output:
            Path(output).write_text(md, encoding="utf-8")
            click.echo(f"Results written to {output}")
        else:
            click.echo(md)
    
    else:  # text format
        _print_text_result(result, file)
    
    # Exit with appropriate code
    if result.overall_status == ReviewStatus.APPROVED:
        sys.exit(0)
    else:
        sys.exit(1)


@review.command()
@click.argument("file", type=click.Path(exists=True))
@click.option("--spec", "-s", "spec_file", type=click.Path(exists=True),
              help="Specification file (optional, can be embedded in file)")
@click.option("--output", "-o", type=click.Path(),
              help="Output file for results (JSON)")
@click.option("--format", "-f", "output_format", default="text",
              type=click.Choice(["text", "json"]),
              help="Output format")
def spec(file: str, spec_file: Optional[str], output: Optional[str], output_format: str):
    """Run only spec compliance review.
    
    Checks if the artifact meets the specification requirements.
    
    Example:
        aop review spec my_mvp.py --spec requirements.md
    """
    content = Path(file).read_text(encoding="utf-8")
    spec = Path(spec_file).read_text(encoding="utf-8") if spec_file else ""
    
    reviewer = SpecComplianceReviewer()
    result = reviewer.review(content, {"spec": spec})
    
    if output_format == "json":
        output_data = result.to_dict()
        if output:
            Path(output).write_text(json.dumps(output_data, indent=2, ensure_ascii=False))
            click.echo(f"Results written to {output}")
        else:
            click.echo(json.dumps(output_data, indent=2, ensure_ascii=False))
    else:
        _print_spec_result(result, file)
    
    sys.exit(0 if result.status == ReviewStatus.APPROVED else 1)


@review.command()
@click.argument("file", type=click.Path(exists=True))
@click.option("--artifact-type", "-t", default="code",
              type=click.Choice(["mvp", "code", "doc"]),
              help="Type of artifact to review")
@click.option("--min-score", "-m", default=60.0,
              help="Minimum acceptable quality score")
@click.option("--output", "-o", type=click.Path(),
              help="Output file for results (JSON)")
@click.option("--format", "-f", "output_format", default="text",
              type=click.Choice(["text", "json"]),
              help="Output format")
def quality(file: str, artifact_type: str, min_score: float, output: Optional[str], output_format: str):
    """Run only quality review.
    
    Checks code/document quality (readability, completeness, consistency, best practices).
    
    Example:
        aop review quality my_code.py --min-score 70
    """
    content = Path(file).read_text(encoding="utf-8")
    
    reviewer = QualityReviewer()
    result = reviewer.review(content, {
        "artifact_type": artifact_type,
        "min_quality_score": min_score,
    })
    
    if output_format == "json":
        output_data = result.to_dict()
        if output:
            Path(output).write_text(json.dumps(output_data, indent=2, ensure_ascii=False))
            click.echo(f"Results written to {output}")
        else:
            click.echo(json.dumps(output_data, indent=2, ensure_ascii=False))
    else:
        _print_quality_result(result, file, min_score)
    
    sys.exit(0 if result.status == ReviewStatus.APPROVED else 1)


def _print_text_result(result, file: str):
    """Print text format result."""
    click.echo(f"\n{'='*60}")
    click.echo(f"Two-Stage Review: {file}")
    click.echo(f"{'='*60}")
    
    # Overall status
    status_color = "green" if result.overall_status == ReviewStatus.APPROVED else "red"
    click.secho(f"\nOverall Status: {result.overall_status.value.upper()}", fg=status_color)
    click.echo(f"Score: {result.overall_score:.1f}/100")
    
    # Stage 1: Spec Compliance
    click.echo(f"\n--- Stage 1: Spec Compliance ---")
    spec_status = "PASSED" if result.spec_result.status == ReviewStatus.APPROVED else "FAILED"
    spec_color = "green" if result.spec_result.status == ReviewStatus.APPROVED else "red"
    click.secho(f"Status: {spec_status}", fg=spec_color)
    
    if result.spec_result.score is not None:
        click.echo(f"Score: {result.spec_result.score:.1f}/100")
    
    if result.spec_result.issues:
        click.echo(f"\nIssues ({len(result.spec_result.issues)}):")
        for issue in result.spec_result.issues:
            severity_color = {"critical": "red", "important": "yellow", "minor": "white"}[issue.severity]
            click.secho(f"  [{issue.severity.upper()}] {issue.description}", fg=severity_color)
            click.echo(f"    Suggestion: {issue.suggestion}")
    
    # Stage 2: Quality
    if result.quality_result:
        click.echo(f"\n--- Stage 2: Quality ---")
        qual_status = "PASSED" if result.quality_result.status == ReviewStatus.APPROVED else "FAILED"
        qual_color = "green" if result.quality_result.status == ReviewStatus.APPROVED else "red"
        click.secho(f"Status: {qual_status}", fg=qual_color)
        
        if result.quality_result.score is not None:
            click.echo(f"Score: {result.quality_result.score:.1f}/100")
        
        if result.quality_result.issues:
            click.echo(f"\nIssues ({len(result.quality_result.issues)}):")
            for issue in result.quality_result.issues[:10]:  # Limit to 10
                severity_color = {"critical": "red", "important": "yellow", "minor": "white"}[issue.severity]
                click.secho(f"  [{issue.severity.upper()}][{issue.category}] {issue.description}", fg=severity_color)
                if issue.suggestion:
                    click.echo(f"    Suggestion: {issue.suggestion}")
    else:
        click.echo(f"\n--- Stage 2: Quality ---")
        click.secho("SKIPPED (spec issues found)", fg="yellow")
    
    click.echo(f"\n{'='*60}")
    click.echo(result.summary)
    click.echo(f"{'='*60}\n")


def _print_spec_result(result, file: str):
    """Print spec compliance result."""
    click.echo(f"\n{'='*60}")
    click.echo(f"Spec Compliance Review: {file}")
    click.echo(f"{'='*60}")
    
    status_color = "green" if result.status == ReviewStatus.APPROVED else "red"
    click.secho(f"\nStatus: {result.status.value.upper()}", fg=status_color)
    
    if result.score is not None:
        click.echo(f"Score: {result.score:.1f}/100")
    
    if result.issues:
        click.echo(f"\nIssues ({len(result.issues)}):")
        for issue in result.issues:
            severity_color = {"critical": "red", "important": "yellow", "minor": "white"}[issue.severity]
            click.secho(f"  [{issue.severity.upper()}][{issue.category}] {issue.description}", fg=severity_color)
            click.echo(f"    Suggestion: {issue.suggestion}")
    
    click.echo(f"\n{result.summary}")
    click.echo(f"{'='*60}\n")


def _print_quality_result(result, file: str, min_score: float):
    """Print quality review result."""
    click.echo(f"\n{'='*60}")
    click.echo(f"Quality Review: {file}")
    click.echo(f"{'='*60}")
    
    status_color = "green" if result.status == ReviewStatus.APPROVED else "red"
    click.secho(f"\nStatus: {result.status.value.upper()}", fg=status_color)
    
    if result.score is not None:
        score_color = "green" if result.score >= min_score else "red"
        click.secho(f"Score: {result.score:.1f}/100 (min: {min_score})", fg=score_color)
    
    counts = result.issue_counts
    click.echo(f"\nIssues by severity:")
    click.echo(f"  Critical: {counts['critical']}")
    click.echo(f"  Important: {counts['important']}")
    click.echo(f"  Minor: {counts['minor']}")
    
    if result.issues:
        click.echo(f"\nTop Issues:")
        for issue in result.issues[:10]:
            severity_color = {"critical": "red", "important": "yellow", "minor": "white"}[issue.severity]
            click.secho(f"  [{issue.severity.upper()}][{issue.category}] {issue.description}", fg=severity_color)
            if issue.suggestion:
                click.echo(f"    → {issue.suggestion}")
    
    click.echo(f"\n{result.summary}")
    click.echo(f"{'='*60}\n")


def _format_markdown(result, file: str, spec_file: str) -> str:
    """Format result as markdown."""
    lines = [
        f"# Two-Stage Review Report",
        f"",
        f"**File:** `{file}`",
        f"**Spec:** `{spec_file}`",
        f"",
        f"## Overall Result",
        f"",
        f"- **Status:** {result.overall_status.value.upper()}",
        f"- **Score:** {result.overall_score:.1f}/100",
        f"",
        f"## Stage 1: Spec Compliance",
        f"",
        f"- **Status:** {'PASSED' if result.spec_result.status == ReviewStatus.APPROVED else 'FAILED'}",
    ]
    
    if result.spec_result.score is not None:
        lines.append(f"- **Score:** {result.spec_result.score:.1f}/100")
    
    if result.spec_result.issues:
        lines.append(f"")
        lines.append(f"### Issues")
        lines.append(f"")
        for issue in result.spec_result.issues:
            lines.append(f"- **[{issue.severity.upper()}]** {issue.description}")
            lines.append(f"  - Suggestion: {issue.suggestion}")
    
    if result.quality_result:
        lines.append(f"")
        lines.append(f"## Stage 2: Quality")
        lines.append(f"")
        lines.append(f"- **Status:** {'PASSED' if result.quality_result.status == ReviewStatus.APPROVED else 'FAILED'}")
        
        if result.quality_result.score is not None:
            lines.append(f"- **Score:** {result.quality_result.score:.1f}/100")
        
        if result.quality_result.issues:
            lines.append(f"")
            lines.append(f"### Issues")
            lines.append(f"")
            for issue in result.quality_result.issues[:10]:
                lines.append(f"- **[{issue.severity.upper()}][{issue.category}]** {issue.description}")
                if issue.suggestion:
                    lines.append(f"  - {issue.suggestion}")
    else:
        lines.append(f"")
        lines.append(f"## Stage 2: Quality")
        lines.append(f"")
        lines.append(f"*Skipped (spec issues found)*")
    
    lines.append(f"")
    lines.append(f"---")
    lines.append(f"")
    lines.append(f"*{result.summary}*")
    
    return "\n".join(lines)
