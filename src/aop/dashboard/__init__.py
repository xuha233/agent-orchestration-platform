"""AOP Dashboard - Web UI for Agent Orchestration Platform."""

import os
import sys
import subprocess
import time
import webbrowser

__version__ = "0.1.0"


def run_dashboard(port: int = 8501, host: str = "localhost"):
    """Run the Streamlit dashboard."""
    from pathlib import Path
    
    # Disable streamlit usage stats prompt
    os.environ["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    
    app_path = Path(__file__).parent / "app.py"
    
    # Build the command
    python_exe = sys.executable
    cmd = f'"{python_exe}" -m streamlit run "{app_path}" --server.port {port} --server.headless true --browser.gatherUsageStats false'
    
    try:
        if sys.platform == "win32":
            # On Windows, use `start` command to launch in a new window
            # /B = start without creating a new window (but still detached)
            # This keeps the process running even when parent exits
            full_cmd = f'start /b "" {cmd}'
            subprocess.run(full_cmd, shell=True)
            
            # Wait a moment for the server to start
            time.sleep(2)
            
            # Check if the server is running
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('localhost', port))
            sock.close()
            
            if result == 0:
                print(f"Dashboard started at http://{host}:{port}")
                print("Press Ctrl+C to stop (or close this terminal)")
                
                # Open browser
                webbrowser.open(f"http://{host}:{port}")
                
                # Keep the script running to maintain the dashboard
                # This is a simple busy-wait loop
                while True:
                    time.sleep(1)
            else:
                print("Failed to start dashboard. Check if port is in use.")
                sys.exit(1)
        else:
            # On Unix-like systems
            subprocess.Popen(
                f'nohup {cmd} &',
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            print(f"Dashboard started at http://{host}:{port}")
        
    except KeyboardInterrupt:
        print("\nDashboard stopped. The server may still be running in the background.")
        print(f"To stop: taskkill /F /IM streamlit.exe 2>nul || pkill -f streamlit")
    except FileNotFoundError:
        print("Error: streamlit not found. Please install it:")
        print("  pip install streamlit")
        sys.exit(1)
    except Exception as e:
        print(f"Error starting dashboard: {e}")
        sys.exit(1)
