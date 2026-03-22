"""Entry point for desktop app bridge experiments."""

from __future__ import annotations

import argparse
import json

from .bridge import DesktopAppBridge
from .service import DesktopAppService


def main() -> None:
    """Run a simple desktop bridge action and print JSON."""
    parser = argparse.ArgumentParser(description="AOP desktop app runtime bridge")
    parser.add_argument("action", help="Bridge action, e.g. health/projects/providers")
    parser.add_argument("--project-id", default="", help="Project identifier")
    parser.add_argument("--run-id", default="", help="Workflow run identifier")
    parser.add_argument("--job-id", default="", help="Desktop async run job identifier")
    parser.add_argument("--limit", type=int, default=12, help="Max number of runs")
    parser.add_argument("--provider-id", default="", help="Provider identifier")
    parser.add_argument("--preferred", action="store_true", help="Mark provider as preferred")
    parser.add_argument("--dry-run", action="store_true", help="Preview mutation actions without writing")
    parser.add_argument("--global-enabled", action="store_true", help="Enable global memory toggle")
    parser.add_argument("--project-enabled", action="store_true", help="Enable project memory config")
    parser.add_argument("--backend", default="", help="Memory backend identifier")
    parser.add_argument("--search-top-k", type=int, default=None, help="Memory search top_k")
    parser.add_argument("--search-threshold", type=float, default=None, help="Memory search threshold")
    parser.add_argument("--prompt", default="", help="Prompt for run actions")
    parser.add_argument("--project-name", default="", help="Project display name")
    parser.add_argument("--project-path", default="", help="Project path")
    parser.add_argument("--primary-agent", default="", help="Primary agent identifier")
    parser.add_argument(
        "--env-values-json",
        default="{}",
        help="JSON object of provider env-style values",
    )
    args = parser.parse_args()

    if args.action == "worker-run":
        service = DesktopAppService()
        service.execute_run_job(args.job_id)
        return

    try:
        env_values = json.loads(args.env_values_json)
    except json.JSONDecodeError:
        env_values = {}
    if not isinstance(env_values, dict):
        env_values = {}

    bridge = DesktopAppBridge()
    payload = {
        "project_id": args.project_id,
        "run_id": args.run_id,
        "job_id": args.job_id,
        "limit": args.limit,
        "provider_id": args.provider_id,
        "preferred": args.preferred,
        "dry_run": args.dry_run,
        "global_enabled": args.global_enabled,
        "project_enabled": args.project_enabled,
        "backend": args.backend,
        "search_top_k": args.search_top_k,
        "search_threshold": args.search_threshold,
        "prompt": args.prompt,
        "project_name": args.project_name,
        "project_path": args.project_path,
        "primary_agent": args.primary_agent,
        "env_values": env_values,
    }
    print(json.dumps(bridge.dispatch(args.action, payload), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
