"""Validation utilities."""

import os
import re
from typing import Dict, List, Any, Tuple
from pathlib import Path


def validate_env_vars(required_vars: List[str]) -> Tuple[bool, List[str]]:
    """
    Validate that required environment variables are set.
    
    Args:
        required_vars: List of required environment variable names
    
    Returns:
        Tuple of (is_valid, missing_vars)
    """
    missing = [var for var in required_vars if var not in os.environ]
    return len(missing) == 0, missing


def validate_config(config: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate configuration structure.
    
    Args:
        config: Configuration dictionary
    
    Returns:
        Tuple of (is_valid, errors)
    """
    errors = []
    
    if not isinstance(config, dict):
        errors.append("Config must be a dictionary")
        return False, errors
    
    required_keys = ["platform", "app_name"]
    for key in required_keys:
        if key not in config:
            errors.append(f"Missing required config key: {key}")
    
    return len(errors) == 0, errors


def validate_python_file(file_path: str) -> Tuple[bool, List[str]]:
    """
    Validate Python file syntax without executing it.
    
    Args:
        file_path: Path to Python file
    
    Returns:
        Tuple of (is_valid, errors)
    """
    errors = []
    
    if not Path(file_path).exists():
        errors.append(f"File not found: {file_path}")
        return False, errors
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            compile(f.read(), file_path, "exec")
    except SyntaxError as e:
        errors.append(f"Syntax error in {file_path}: {e}")
        return False, errors
    
    return True, errors


def validate_requirements_file(file_path: str) -> Tuple[bool, List[str]]:
    """
    Validate requirements.txt format.
    
    Args:
        file_path: Path to requirements file
    
    Returns:
        Tuple of (is_valid, errors)
    """
    errors = []
    
    if not Path(file_path).exists():
        errors.append(f"Requirements file not found: {file_path}")
        return False, errors
    
    with open(file_path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            
            # Basic validation for package specification
            if not re.match(r"^[a-zA-Z0-9\-_.]+", line):
                errors.append(f"Invalid requirement format on line {i}: {line}")
    
    return len(errors) == 0, errors
