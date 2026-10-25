"""Helper functions for deployment operations."""

import subprocess
import os
from typing import Dict, List, Any, Optional
from pathlib import Path
import json
import yaml


__all__ = [
    "run_command",
    "write_yaml",
    "file_exists",
    "read_file",
    "write_file",
    "read_json",
    "write_json",
    "read_yaml",
    "dir_exists",
]

def run_command(
    command: List[str],
    cwd: Optional[str] = None,
    env: Optional[Dict[str, Optional[str]]] = None,
    check: bool = True,
    timeout: Optional[float] = None,
) -> subprocess.CompletedProcess:
    """
    Run a shell command and return the result.
    
    Args:
        command: Command and arguments as list
        cwd: Working directory for command
        env: Variables added to the inherited environment; a value of None removes the variable
        check: Raise exception if command fails
        timeout: Seconds before the command is killed (None means no limit).
            Raises subprocess.TimeoutExpired when exceeded.
    
    Returns:
        CompletedProcess instance
    """
    full_env = os.environ.copy()
    if env:
        for key, value in env.items():
            if value is None:
                full_env.pop(key, None)
            else:
                full_env[key] = value
    
    return subprocess.run(
        command,
        cwd=cwd,
        env=full_env,
        check=check,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def read_file(file_path: str) -> str:
    """Read file contents."""
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def write_file(file_path: str, content: str) -> None:
    """Write content to file."""
    Path(file_path).parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)


def read_json(file_path: str) -> Dict[str, Any]:
    """Read JSON file."""
    data: Dict[str, Any] = json.loads(read_file(file_path))
    return data


def write_json(file_path: str, data: Dict[str, Any]) -> None:
    """Write data to JSON file."""
    write_file(file_path, json.dumps(data, indent=2))


def read_yaml(file_path: str) -> Dict[str, Any]:
    """Read YAML file."""
    with open(file_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def write_yaml(file_path: str, data: Dict[str, Any]) -> None:
    """Write data to YAML file."""
    Path(file_path).parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False)


def file_exists(file_path: str) -> bool:
    """Check if file exists."""
    return Path(file_path).exists()


def dir_exists(dir_path: str) -> bool:
    """Check if directory exists."""
    return Path(dir_path).is_dir()


STATE_DIR = ".deployment"


def has_uncommitted_changes(porcelain_output: str) -> bool:
    """
    Tell whether 'git status --porcelain' output lists real changes.

    The tool's own rollback state folder is ignored. Otherwise every deploy
    would leave the project dirty and block the next one.
    """
    for line in porcelain_output.splitlines():
        if not line.strip():
            continue
        path = line[3:].strip().strip('"').replace("\\", "/")
        if path == STATE_DIR or path.startswith(STATE_DIR + "/"):
            continue
        return True
    return False
