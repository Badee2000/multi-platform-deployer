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
    env: Optional[Dict[str, str]] = None,
    check: bool = True,
) -> subprocess.CompletedProcess:
    """
    Run a shell command and return the result.
    
    Args:
        command: Command and arguments as list
        cwd: Working directory for command
        env: Environment variables
        check: Raise exception if command fails
    
    Returns:
        CompletedProcess instance
    """
    full_env = os.environ.copy()
    if env:
        full_env.update(env)
    
    return subprocess.run(
        command,
        cwd=cwd,
        env=full_env,
        check=check,
        capture_output=True,
        text=True,
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
    return json.loads(read_file(file_path))


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
