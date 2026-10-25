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

import os
import shutil
import subprocess
from abc import ABC, abstractmethod
from typing import Dict, Any, Iterable, List, Optional
from pathlib import Path
from ..utils.logger import get_logger
from ..utils.helpers import run_command, write_yaml
from ..config.loader import ConfigLoader

DEFAULT_STEP_TIMEOUT = 900  # seconds; deploys can be slow but must not hang forever


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
        dry_run: bool = False,
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
        # In dry-run mode every external step is printed, never executed.
        self.dry_run = dry_run
        # Set by deploy() when the platform reports a public URL.
        self.deployed_url: Optional[str] = None

    def _require_credential(self, env_name: str) -> Optional[str]:
        """
        Read an API token from the environment.

        Tokens are only ever passed to tools through environment variables,
        never as command-line arguments, so they cannot leak via process lists.
        In dry-run mode a missing token is a warning, not an error.
        """
        value = os.environ.get(env_name, "")
        if value:
            return value
        if self.dry_run:
            self.logger.warning(f"[dry-run] {env_name} is not set; a real deploy would fail.")
            return ""
        self.logger.error(
            f"{env_name} is not set. Export it in your shell before deploying "
            f"to {self.get_platform_name()}."
        )
        return None

    @staticmethod
    def _redact(text: str, secrets: Iterable[str]) -> str:
        """Remove secret values from text before it is logged or shown."""
        for secret in secrets:
            if secret:
                text = text.replace(secret, "***")
        return text

    def _run_step(
        self,
        command: List[str],
        env: Optional[Dict[str, Optional[str]]] = None,
        secrets: Iterable[str] = (),
        timeout: float = DEFAULT_STEP_TIMEOUT,
    ) -> Optional[str]:
        """
        Run one external step (a vendor CLI call).

        Returns:
            stdout on success (secrets redacted), "" in dry-run mode,
            or None on failure. Never raises.
        """
        secrets = [s for s in secrets if s]
        display = " ".join(command)
        if self.dry_run:
            self.logger.info(f"[dry-run] would run: {display}")
            return ""

        # Resolve the executable first; on Windows, npm tools are .cmd shims
        # that subprocess cannot start from a bare name.
        executable = shutil.which(command[0])
        if executable is None:
            self.logger.error(
                f"'{command[0]}' was not found on PATH. Install it and try again."
            )
            return None

        argv = [executable] + command[1:]
        try:
            result = run_command(
                argv,
                cwd=str(self.project_root),
                env=env,
                check=False,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            self.logger.error(f"Timed out after {timeout:.0f}s: {display}")
            return None
        except OSError as e:
            self.logger.error(f"Could not start {command[0]}: {self._redact(str(e), secrets)}")
            return None

        if result.returncode != 0:
            detail = self._redact((result.stderr or result.stdout or "").strip(), secrets)
            self.logger.error(
                f"Command failed (exit {result.returncode}): {display}\n{detail[-2000:]}"
            )
            return None

        self.logger.info(f"Command succeeded: {display}")
        return self._redact(result.stdout or "", secrets)
    
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

    supports_live_rollback = False

    def rollback_live(self) -> bool:
        """Roll the running service back on the platform. Only some platforms support it."""
        self.logger.error(
            f"Live rollback is not supported for {self.get_platform_name()} by this tool. "
            "Use the platform's own dashboard or CLI."
        )
        return False

    def rollback(self, deployment_state: Dict[str, Any]) -> bool:
        self.logger.info(
            "No custom rollback steps defined; redeploying restored snapshot."
        )
        return self.deploy()
