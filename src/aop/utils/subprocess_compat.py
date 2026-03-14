"""Cross-platform subprocess utilities for Windows compatibility."""

from __future__ import annotations

import subprocess
import shutil
from typing import List, Optional, Tuple


def run_command(
    args: List[str] | str,
    *,
    binary_path: Optional[str] = None,
    timeout: int = 30,
    input_text: Optional[str] = None,
) -> Tuple[int, str, str]:
    """
    Run a command with Windows .cmd/.bat file support.
    
    Args:
        args: Command arguments (list or string)
        binary_path: Full path to binary (from shutil.which)
        timeout: Timeout in seconds
        input_text: Text to pass to stdin
        
    Returns:
        Tuple of (returncode, stdout, stderr)
    """
    # Determine if we need shell=True for Windows .cmd/.bat files
    use_shell = False
    cmd_str: str
    
    if isinstance(args, str):
        cmd_str = args
        use_shell = True
    else:
        # Check if binary is a .cmd/.bat file on Windows
        if binary_path and binary_path.lower().endswith(('.cmd', '.bat')):
            use_shell = True
            cmd_str = ' '.join(f'"{arg}"' if ' ' in arg else arg for arg in args)
        elif args and args[0].lower().endswith(('.cmd', '.bat')):
            use_shell = True
            cmd_str = ' '.join(f'"{arg}"' if ' ' in arg else arg for arg in args)
        else:
            cmd_str = ''
    
    try:
        if use_shell:
            result = subprocess.run(
                cmd_str,
                capture_output=True,
                text=True,
                timeout=timeout,
                shell=True,
                encoding='utf-8',
                errors='replace',
                input=input_text,
            )
        else:
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding='utf-8',
                errors='replace',
                input=input_text,
            )
        return result.returncode, result.stdout, result.stderr
        
    except FileNotFoundError:
        # Fallback: try with shell=True using full binary path
        if binary_path and not use_shell:
            try:
                fallback_cmd = f'"{binary_path}" ' + ' '.join(f'"{arg}"' if ' ' in arg else arg for arg in args[1:])
                result = subprocess.run(
                    fallback_cmd,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    shell=True,
                    encoding='utf-8',
                    errors='replace',
                    input=input_text,
                )
                return result.returncode, result.stdout, result.stderr
            except Exception:
                pass
        return 1, '', 'File not found'
        
    except subprocess.TimeoutExpired:
        return -1, '', 'timeout'
    except Exception as e:
        return 1, '', str(e)[:100]


def find_binary(name: str) -> Optional[str]:
    """Find binary path using shutil.which."""
    return shutil.which(name)


def check_binary_available(name: str) -> Tuple[bool, Optional[str]]:
    """
    Check if a binary is available in PATH.
    
    Returns:
        Tuple of (available, path)
    """
    path = shutil.which(name)
    return path is not None, path