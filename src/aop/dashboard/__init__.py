"""AOP Dashboard - Web UI for Agent Orchestration Platform."""

import os
import sys

__version__ = "0.1.0"


def run_dashboard(port: int = 8501, host: str = "localhost"):
    """Run the Streamlit dashboard."""
    from pathlib import Path
    
    # Disable streamlit usage stats prompt
    os.environ["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    
    app_path = Path(__file__).parent / "app.py"
    
    # Use os.execvp to replace current process with streamlit
    # This avoids subprocess issues with PowerShell pipes
    cmd = "streamlit"
    args = [
        "streamlit", "run",
        str(app_path),
        "--server.port", str(port),
        "--server.headless", "true",
        "--browser.gatherUsageStats", "false",
    ]
    
    try:
        os.execvp(cmd, args)
    except KeyboardInterrupt:
        print("\nDashboard stopped.")
    except FileNotFoundError:
        print("Error: streamlit not found. Please install it:")
        print("  pip install streamlit")
        sys.exit(1)
