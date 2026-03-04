"""AOP Dashboard - Web UI for Agent Orchestration Platform."""

__version__ = "0.1.0"


def run_dashboard(port: int = 8501, host: str = "localhost"):
    """Run the Streamlit dashboard."""
    import subprocess
    import sys
    from pathlib import Path
    
    app_path = Path(__file__).parent / "app.py"
    
    subprocess.run([
        sys.executable, "-m", "streamlit", "run",
        str(app_path),
        "--server.port", str(port),
        "--server.headless", "true",
    ])
