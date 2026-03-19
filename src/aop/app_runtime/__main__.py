"""Entry point for desktop app bridge experiments."""

from __future__ import annotations

import argparse
import json

from .bridge import DesktopAppBridge


def main() -> None:
    """Run a simple desktop bridge action and print JSON."""
    parser = argparse.ArgumentParser(description="AOP desktop app runtime bridge")
    parser.add_argument("action", help="Bridge action, e.g. health/projects/providers")
    parser.add_argument("--project-id", default="", help="Project identifier")
    parser.add_argument("--run-id", default="", help="Workflow run identifier")
    parser.add_argument("--limit", type=int, default=12, help="Max number of runs")
    args = parser.parse_args()

    bridge = DesktopAppBridge()
    payload = {
        "project_id": args.project_id,
        "run_id": args.run_id,
        "limit": args.limit,
    }
    print(json.dumps(bridge.dispatch(args.action, payload), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
