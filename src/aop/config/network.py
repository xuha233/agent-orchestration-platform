"""Network configuration for AOP.

Allows configuring gateway host and port via environment variables.
Default values ensure backward compatibility with localhost deployments.
"""

import os

# Gateway WebSocket/API port
GATEWAY_PORT = int(os.environ.get("AOP_GATEWAY_PORT", "18789"))

# Gateway host (useful for remote deployments)
GATEWAY_HOST = os.environ.get("AOP_GATEWAY_HOST", "localhost")

# Full gateway base URL
GATEWAY_BASE_URL = f"http://{GATEWAY_HOST}:{GATEWAY_PORT}"

# Dashboard port
DASHBOARD_PORT = int(os.environ.get("AOP_DASHBOARD_PORT", "8501"))

# Dashboard host
DASHBOARD_HOST = os.environ.get("AOP_DASHBOARD_HOST", "localhost")

# Dashboard URL
DASHBOARD_URL = f"http://{DASHBOARD_HOST}:{DASHBOARD_PORT}"
