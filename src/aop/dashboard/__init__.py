"""AOP Dashboard - Web UI for Agent Orchestration Platform."""

import os

__version__ = "0.1.0"


def run_dashboard(port: int = 8501, host: str = "localhost"):
    """Run the Streamlit dashboard."""
    import subprocess
    import sys
    from pathlib import Path
    
    # Disable streamlit usage stats prompt
    os.environ["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    
    app_path = Path(__file__).parent / "app.py"
    
    subprocess.run([
        sys.executable, "-m", "streamlit", "run",
        str(app_path),
        "--server.port", str(port),
        "--server.headless", "true",
        "--browser.gatherUsageStats", "false",
    ])
