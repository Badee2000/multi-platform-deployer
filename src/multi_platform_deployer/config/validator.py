"""Configuration validation."""

from typing import Dict, Any, List, Tuple
from ..utils.logger import get_logger


class ConfigValidator:
    """Validate deployment configurations."""
    
    REQUIRED_KEYS = ["platform", "app_name"]
    VALID_PLATFORMS = ["render", "railway", "vercel", "heroku", "aws"]
    
    @staticmethod
    def validate(config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate configuration dictionary.
        
        Args:
            config: Configuration dictionary
        
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        logger = get_logger("ConfigValidator")
        
        # Check if config is dict
        if not isinstance(config, dict):
            errors.append("Configuration must be a dictionary")
            return False, errors
        
        # Check required keys
        for key in ConfigValidator.REQUIRED_KEYS:
            if key not in config:
                errors.append(f"Missing required configuration key: {key}")
        
        # Validate platform
        if "platform" in config:
            platform = config["platform"]
            if isinstance(platform, str):
                if platform.lower() not in ConfigValidator.VALID_PLATFORMS:
                    errors.append(
                        f"Invalid platform: {platform}. "
                        f"Valid platforms: {ConfigValidator.VALID_PLATFORMS}"
                    )
            elif isinstance(platform, list):
                for p in platform:
                    if p.lower() not in ConfigValidator.VALID_PLATFORMS:
                        errors.append(f"Invalid platform in list: {p}")
            else:
                errors.append("Platform must be string or list of strings")
        
        # Validate app_name
        if "app_name" in config:
            app_name = config["app_name"]
            if not isinstance(app_name, str):
                errors.append("app_name must be a string")
            elif not app_name.strip():
                errors.append("app_name cannot be empty")
        
        is_valid = len(errors) == 0
        
        if not is_valid:
            logger.error(f"Configuration validation failed: {errors}")
        else:
            logger.info("Configuration validation passed")
        
        return is_valid, errors
    
    @staticmethod
    def validate_env_vars(config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate environment variables in configuration.
        
        Args:
            config: Configuration dictionary
        
        Returns:
            Tuple of (is_valid, missing_vars)
        """
        errors = []
        
        env_vars = config.get("env_vars", {})
        if not isinstance(env_vars, dict):
            errors.append("env_vars must be a dictionary")
            return False, errors
        
        required_env = config.get("required_env_vars", [])
        for var in required_env:
            if var not in env_vars:
                errors.append(f"Missing required environment variable: {var}")
        
        return len(errors) == 0, errors
