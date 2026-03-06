"""AOP Dashboard - Web UI for Agent Orchestration Platform."""

import os
import sys
import subprocess
import time
import webbrowser
import socket

__version__ = "0.1.0"


def _is_port_in_use(port: int) -> bool:
    """Check if a port is already in use."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('localhost', port))
    sock.close()
    return result == 0


def run_dashboard(port: int = 8501, host: str = "localhost"):
    """Run the Streamlit dashboard."""
    from pathlib import Path
    
    # Check if already running
    if _is_port_in_use(port):
        print(f"Dashboard is already running at http://{host}:{port}")
        webbrowser.open(f"http://{host}:{port}")
        return
    
    # Disable streamlit usage stats prompt
    os.environ["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    
    app_path = Path(__file__).parent / "app.py"
    
    try:
        if sys.platform == "win32":
            # On Windows, use `start` command to launch in a NEW window
            # This creates a completely independent process
            python_exe = sys.executable
            cmd = f'"{python_exe}" -m streamlit run "{app_path}" --server.port {port} --server.headless true --browser.gatherUsageStats false'
            
            # start command: open a new command prompt window and run the command
            # The dashboard will continue running even after this script exits
            full_cmd = f'cmd /c start "AOP Dashboard" cmd /c "{cmd}"'
            
            subprocess.run(full_cmd, shell=True)
            
            # Wait for the server to start
            print(f"Starting Dashboard at http://{host}:{port}...")
            
            for i in range(10):
                time.sleep(1)
                if _is_port_in_use(port):
                    print(f"Dashboard started! Opening browser...")
                    webbrowser.open(f"http://{host}:{port}")
                    print(f"Dashboard is running at http://{host}:{port}")
                    print("Close the Dashboard window to stop the server.")
                    return
            
            print("Failed to start Dashboard after 10 seconds.")
            print("Please check if streamlit is installed: pip install streamlit")
            
        else:
            # On Unix-like systems, use nohup
            cmd = f'nohup "{sys.executable}" -m streamlit run "{app_path}" --server.port {port} --server.headless true --browser.gatherUsageStats false &'
            subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(f"Dashboard started at http://{host}:{port}")
            webbrowser.open(f"http://{host}:{port}")
        
    except FileNotFoundError:
        print("Error: streamlit not found. Please install it:")
        print("  pip install streamlit")
        sys.exit(1)
    except Exception as e:
        print(f"Error starting dashboard: {e}")
        sys.exit(1)
