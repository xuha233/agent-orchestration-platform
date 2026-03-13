"""Port configuration for AOP.

All port numbers can be overridden via environment variables.
"""

import os

GATEWAY_PORT = int(os.environ.get("AOP_GATEWAY_PORT", 18789))
CDP_PORT = int(os.environ.get("AOP_CDP_PORT", 18792))
DASHBOARD_PORT = int(os.environ.get("AOP_DASHBOARD_PORT", 8501))
