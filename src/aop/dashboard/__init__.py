"""AOP Dashboard - Web UI for Agent Orchestration Platform."""

import os
import sys
import subprocess
import signal

__version__ = "0.1.0"


def run_dashboard(port: int = 8501, host: str = "localhost"):
    """Run the Streamlit dashboard."""
    from pathlib import Path
    
    # Disable streamlit usage stats prompt
    os.environ["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    
    app_path = Path(__file__).parent / "app.py"
    
    # Build arguments for streamlit
    args = [
        sys.executable,  # Use the same Python interpreter
        "-m", "streamlit",
        "run",
        str(app_path),
        "--server.port", str(port),
        "--server.headless", "true",
        "--browser.gatherUsageStats", "false",
    ]
    
    try:
        # Use subprocess to run streamlit in a separate process
        # This avoids issues with running Click commands within Click commands
        process = subprocess.Popen(args)
        
        # Set up signal handler to forward Ctrl+C to the child process
        def handle_sigint(signum, frame):
            # On Windows, we need to terminate the process
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
            print("\nDashboard stopped.")
            sys.exit(0)
        
        # Register the signal handler
        signal.signal(signal.SIGINT, handle_sigint)
        
        # Wait for the streamlit process to complete
        process.wait()
        
    except KeyboardInterrupt:
        print("\nDashboard stopped.")
    except FileNotFoundError:
        print("Error: streamlit not found. Please install it:")
        print("  pip install streamlit")
        sys.exit(1)
    except Exception as e:
        print(f"Error starting dashboard: {e}")
        sys.exit(1)
