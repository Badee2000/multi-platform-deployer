"""Configuration loader for deployment settings."""

import os
from typing import Dict, Any, Optional
from pathlib import Path
from ..utils.helpers import read_yaml, read_json, file_exists
from ..utils.logger import get_logger


class ConfigLoader:
    """Load and manage deployment configurations."""
    
    __all__ = ["ConfigLoader"]
    
    def __init__(self, project_root: str = "."):
        """
        Initialize config loader.
        
        Args:
            project_root: Root directory of the project
        """
        self.project_root = Path(project_root)
        self.logger = get_logger("ConfigLoader")
        self.config: Dict[str, Any] = {}
    
    def load_config(self, config_file: Optional[str] = None) -> Dict[str, Any]:
        """
        Load configuration from file.
        
        Args:
            config_file: Path to config file (yaml or json)
        
        Returns:
            Configuration dictionary
        """
        if config_file is None:
            # Look for default config files
            config_file = self._find_config_file()
        
        if config_file is None:
            self.logger.warning("No configuration file found")
            return self.config
        
        config_path = self.project_root / config_file
        
        if not config_path.exists():
            self.logger.warning(f"Config file not found: {config_file}")
            return self.config
        
        try:
            if config_file.endswith(".yaml") or config_file.endswith(".yml"):
                self.config = read_yaml(str(config_path))
            elif config_file.endswith(".json"):
                self.config = read_json(str(config_path))
            else:
                self.logger.error(f"Unsupported config format: {config_file}")
                return {}
            
            self.logger.info(f"Configuration loaded from {config_file}")
            return self.config
        except Exception as e:
            self.logger.error(f"Error loading config: {e}")
            return {}
    
    def _find_config_file(self) -> Optional[str]:
        """Find default configuration file."""
        default_files = [
            "deployment.yaml",
            "deployment.yml",
            "deployment.json",
            ".deployment.yaml",
            ".deployment.yml",
            ".deployment.json",
        ]
        
        for file in default_files:
            if (self.project_root / file).exists():
                return file
        
        return None
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set configuration value."""
        self.config[key] = value
    
    def load_env_file(self, env_file: str = ".env") -> Dict[str, str]:
        """
        Load environment variables from .env file.
        
        Args:
            env_file: Path to .env file
        
        Returns:
            Dictionary of environment variables
        """
        env_vars = {}
        env_path = self.project_root / env_file
        
        if not env_path.exists():
            self.logger.warning(f"Environment file not found: {env_file}")
            return env_vars
        
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    
                    if "=" in line:
                        key, value = line.split("=", 1)
                        env_vars[key.strip()] = value.strip()
            
            self.logger.info(f"Loaded {len(env_vars)} environment variables")
            return env_vars
        except Exception as e:
            self.logger.error(f"Error loading environment file: {e}")
            return {}
