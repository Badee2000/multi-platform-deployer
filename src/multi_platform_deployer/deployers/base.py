"""
Base deployer class.

This module defines the abstract base class that all platform-specific
deployers inherit from (Render, Railway, Vercel, Heroku, etc.).

The idea is simple:
- Each platform has different deployment steps and config formats
- But they all follow the same basic pattern: validate -> prepare -> deploy
- We use abstract methods to enforce this pattern for every new platform

This makes it easy to add support for new platforms - just inherit from this
and implement the abstract methods.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pathlib import Path
from ..utils.logger import get_logger
from ..utils.helpers import run_command, write_yaml
from ..config.loader import ConfigLoader


class BaseDeployer(ABC):
    """
    Abstract base class for all platform deployers.
    
    Every cloud platform (Render, Railway, Vercel, Heroku) has:
    - Different deployment APIs
    - Different config file formats
    - Different environment setup
    
    But they all follow the same basic steps:
    1. Validate the app is ready
    2. Prepare by generating config files
    3. Deploy the app
    
    This base class enforces that pattern for all subclasses.
    If you want to add support for AWS or Google Cloud,
    just create a new deployer that inherits from this.
    """
    
    def __init__(
        self,
        project_root: str = ".",
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize a deployer.
        
        This sets up the basic infrastructure that all deployers need:
        - Where the project files are
        - Configuration (from deployment.yaml/json)
        - Logging so we can see what's happening
        
        Args:
            project_root: Root directory of the project (where your app code is)
            config: Configuration dictionary (usually loaded from deployment.yaml)
        """
        self.project_root = Path(project_root)
        self.config = config or {}
        self.logger = get_logger(self.__class__.__name__)
        self.config_loader = ConfigLoader(project_root)
    
    @abstractmethod
    def validate(self) -> bool:
        """
        Validate deployment readiness.
        
        Each platform has its own requirements:
        - Render might need certain buildpacks
        - Railway might need docker setup
        - Vercel might need specific Python version
        
        This method checks platform-specific requirements.
        Subclasses MUST implement this!
        """
        pass
    
    @abstractmethod
    def prepare(self) -> bool:
        """
        Prepare deployment by generating config files.
        
        Each platform needs its own config format:
        - Render uses render.yaml
        - Railway uses railway.json
        - Vercel uses vercel.json
        - Heroku uses Procfile
        
        This method generates the right format for your platform.
        Subclasses MUST implement this!
        """
        pass
    
    @abstractmethod
    def deploy(self) -> bool:
        """
        Execute the actual deployment.
        
        This is where the magic happens - ship your code to production!
        
        Each platform has its own deployment process:
        - Render: Uses REST API
        - Railway: Uses CLI or Git push
        - Vercel: Uses CLI or Git push
        - Heroku: Uses CLI
        
        This method does the platform-specific deployment.
        Subclasses MUST implement this!
        """
        pass
    
    @abstractmethod
    def get_config_template(self) -> Dict[str, Any]:
        """
        Get the platform-specific configuration template.
        
        Returns a dictionary representing the config file format
        for this platform (Render, Railway, etc.).
        
        Subclasses MUST implement this so we know what config
        this platform needs.
        """
        pass
    
    def generate_config_file(self, output_path: Optional[str] = None) -> bool:
        """
        Generate the platform configuration file.
        
        This creates the platform-specific config file
        (render.yaml, railway.json, etc.) so you can deploy.
        
        Args:
            output_path: Where to save the config file
        
        Returns:
            True if generation succeeded, False otherwise
        """
        try:
            template = self.get_config_template()
            output_file = output_path or self._get_default_config_path()
            
            write_yaml(str(self.project_root / output_file), template)
            self.logger.info(f"Configuration file generated: {output_file}")
            return True
        except Exception as e:
            self.logger.error(f"Error generating config file: {e}")
            return False
    
    def _get_default_config_path(self) -> str:
        """Get default configuration file path."""
        return f"{self.get_platform_name().lower()}.yaml"
    
    def run_command(
        self,
        command: list,
        check: bool = True,
    ) -> bool:
        """
        Run a shell command.
        
        Args:
            command: Command and arguments as list
            check: Raise exception if command fails
        
        Returns:
            True if successful
        """
        try:
            result = run_command(command, cwd=str(self.project_root), check=check)
            self.logger.info(f"Command executed: {' '.join(command)}")
            if result.stdout:
                self.logger.debug(f"Output: {result.stdout}")
            return result.returncode == 0
        except Exception as e:
            self.logger.error(f"Error running command: {e}")
            return False
    
    @staticmethod
    @abstractmethod
    def get_platform_name() -> str:
        """Get platform name."""
        pass

    def rollback(self, deployment_state: Dict[str, Any]) -> bool:
        """Redeploy the restored snapshot for this platform."""
        self.logger.info(
            "No custom rollback steps defined; redeploying restored snapshot."
        )
        return self.deploy()
