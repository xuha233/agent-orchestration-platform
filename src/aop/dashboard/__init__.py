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


def run_dashboard(port: int = 8501, host: str = "localhost", foreground: bool = False, open_browser: bool = True):
    """Run the Streamlit dashboard.
    
    Args:
        port: Port to run on
        host: Host to bind to
        foreground: If True, run in foreground and show logs in current terminal.
                   If False (default), run in background in a new window.
        open_browser: If True, open browser after starting. Default: True
    """
    from pathlib import Path
    
    # Check if already running
    if _is_port_in_use(port):
        print(f"Dashboard is already running at http://{host}:{port}")
        if open_browser:
            webbrowser.open(f"http://{host}:{port}")
        return
    
    # Disable streamlit usage stats prompt
    os.environ["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    
    app_path = Path(__file__).parent / "app.py"
    
    try:
        if foreground:
            # 前台模式：直接运行，日志输出到当前终端
            cmd = [
                sys.executable, "-m", "streamlit", "run",
                str(app_path),
                "--server.port", str(port),
                "--server.headless", "true",
                "--browser.gatherUsageStats", "false"
            ]
            print(f"Starting Dashboard at http://{host}:{port}...")
            print("Press Ctrl+C to stop")
            print("-" * 50)
            subprocess.run(cmd)
            
        elif sys.platform == "win32":
            # 后台模式：使用 cmd /c start 弹出新窗口
            python_exe = sys.executable
            
            # 构建在新窗口中运行的命令
            inner_cmd = f'title AOP Dashboard & "{python_exe}" -m streamlit run "{app_path}" --server.port {port} --server.headless true & pause'
            
            # 使用 cmd /c start 弹出新窗口
            full_cmd = f'cmd /c start "AOP Dashboard" cmd /c "{inner_cmd}"'
            
            subprocess.run(full_cmd, shell=True)
            
            # Wait for the server to start
            print(f"Starting Dashboard at http://{host}:{port}...")
            
            for i in range(10):
                time.sleep(1)
                if _is_port_in_use(port):
                    print(f"Dashboard started at http://{host}:{port}")
                    print("A new window has opened. Close it to stop the server.")
                    if open_browser:
                        webbrowser.open(f"http://{host}:{port}")
                    return
            
            print("Failed to start Dashboard after 10 seconds.")
            print("Please check if streamlit is installed: pip install streamlit")
            
        else:
            # On Unix-like systems, use nohup
            cmd = f'nohup "{sys.executable}" -m streamlit run "{app_path}" --server.port {port} --server.headless true --browser.gatherUsageStats false &'
            subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(f"Dashboard started at http://{host}:{port}")
            if open_browser:
                webbrowser.open(f"http://{host}:{port}")
        
    except FileNotFoundError:
        print("Error: streamlit not found. Please install it:")
        print("  pip install streamlit")
        sys.exit(1)
    except Exception as e:
        print(f"Error starting dashboard: {e}")
        sys.exit(1)