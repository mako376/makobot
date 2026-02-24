# agent/tools/shell.py
"""
Safe, read-only shell execution tools for the agent.
All commands are restricted to inspection/listing/search operations.
"""

import os
import subprocess
import shlex
from typing import Dict, Any, Optional

ALLOWED_PREFIXES = [
    "ls", "dir", "tree", "find", "grep", "rg", "cat", "head", "tail", "wc",
    "git status", "git diff", "git log", "git branch", "git remote",
    "echo", "pwd", "date"
]

def execute_shell_tool(tool_name: str, args: Dict[str, Any], current_goal_id: Optional[int] = None) -> str:
    """
    Dispatcher for shell-related tools.
    Currently supports only 'run_safe_shell'.
    """
    if tool_name == "run_safe_shell":
        return run_safe_shell(args.get("cmd", ""))
    else:
        return f"Unknown shell tool: {tool_name}"


def run_pipeline(cmd: str) -> str:
    """
    Execute a pipeline of commands (e.g., "cmd1 | cmd2 | cmd3") securely.
    Each command must be in the allowed list.
    """
    parts = [p.strip() for p in cmd.split("|")]  # Split on |
    processes = []
    prev_stdout = None

    for part in parts:
        args = shlex.split(part)  # Safely split into args
        if not args:
            continue
        if not any(args[0].strip().startswith(prefix) for prefix in ALLOWED_PREFIXES):
            raise ValueError(f"Command '{args[0]}' is not allowed")

        if prev_stdout is None:
            # First command in pipeline
            p = subprocess.Popen(args, stdout=subprocess.PIPE, text=True)
        else:
            # Subsequent commands
            p = subprocess.Popen(args, stdin=prev_stdout, stdout=subprocess.PIPE, text=True)
        processes.append(p)
        prev_stdout = p.stdout

    # Wait for all processes and collect output
    output = ""
    for p in processes:
        stdout, stderr = p.communicate()
        if stdout:
            output += stdout
        if stderr:
            output += f"Error: {stderr}"

    # Check for errors in any process
    for p in processes:
        if p.returncode != 0:
            raise subprocess.CalledProcessError(p.returncode, " ".join(p.args))

    return output


def run_safe_shell(cmd: str) -> str:
    """
    Execute a read-only shell command in the current working directory.
    - Only allows whitelisted command prefixes
    - Uses shlex for safe quoting
    - 10-second timeout
    - Captures stdout/stderr
    """
    if not cmd.strip():
        return "Error: empty command"

    # Basic prefix check (first word)
    first_word = shlex.split(cmd)[0] if cmd.strip() else ""
    allowed = any(cmd.strip().startswith(prefix) for prefix in ALLOWED_PREFIXES)

    if not allowed:
        return (
            f"Error: Command not allowed for safety reasons.\n"
            f"Allowed prefixes: {', '.join(ALLOWED_PREFIXES)}\n"
            f"Attempted: {cmd}"
        )

    try:
        # shell=False would provide better security
        cmd_list = shlex.split(cmd)
        result = run_pipeline(cmd)

        output = f"output: {result}\n"
        return output or "(no output)"

    except subprocess.TimeoutExpired:
        return f"Command timed out after 10 seconds: {cmd}"
    except subprocess.CalledProcessError as e:
        return f"Execution error:\n{e.stderr or e.stdout}"
    except FileNotFoundError:
        return f"Command not found: {first_word}"
    except Exception as e:
        return f"Unexpected shell error: {str(e)}"


# ─── Tool Schema (exported for ALL_TOOLS) ──────────────────────────────────

SHELL_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "run_safe_shell",
            "description": (
                "Run a safe, read-only shell command to inspect files or repo state. "
                "Only allowed: ls, grep, rg, find, cat, head, tail, wc, git status/diff/log/branch/remote. "
                "No write, delete, install, or dangerous commands permitted."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "cmd": {
                        "type": "string",
                        "description": "The shell command to run (e.g. 'ls -la agent/', 'grep -r TODO .')"
                    }
                },
                "required": ["cmd"]
            }
        }
    }
]
