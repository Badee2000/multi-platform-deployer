"""Base class for platform deployers (Render, Railway, Vercel, Heroku)."""

import os
import shutil
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

from ..config.loader import ConfigLoader
from ..utils.helpers import run_command, write_yaml
from ..utils.logger import get_logger

DEFAULT_STEP_TIMEOUT = 900  # seconds; deploys can be slow but must not hang forever


class BaseDeployer(ABC):
    """
    Base class for platform deployers.

    Every platform follows the same steps: validate that the project is ready,
    prepare any files the platform needs, then deploy. A new platform only has
    to implement those three methods.
    """

    def __init__(
        self,
        project_root: str = ".",
        config: Optional[Dict[str, Any]] = None,
        dry_run: bool = False,
    ):
        """
        Args:
            project_root: Root directory of the project.
            config: Settings, usually loaded from deployment.yaml or deployment.json.
            dry_run: Print every external step instead of running it.
        """
        self.project_root = Path(project_root)
        self.config = config or {}
        self.logger = get_logger(self.__class__.__name__)
        self.config_loader = ConfigLoader(project_root)
        self.dry_run = dry_run
        # Set by deploy() when the platform reports a public URL.
        self.deployed_url: Optional[str] = None

    def _run_checks(self, checks: List[Tuple[Callable[[], bool], str]]) -> bool:
        """Run (check, description) pairs, log each result and return True if all passed."""
        all_passed = True
        for check, description in checks:
            if check():
                self.logger.info(f"Check passed: {description}")
            else:
                self.logger.warning(f"Check failed: {description}")
                all_passed = False
        return all_passed

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
            self.logger.warning(
                f"[dry-run] {env_name} is not set; a real deploy would fail."
            )
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
            self.logger.error(
                f"Could not start {command[0]}: {self._redact(str(e), secrets)}"
            )
            return None

        if result.returncode != 0:
            detail = self._redact(
                (result.stderr or result.stdout or "").strip(), secrets
            )
            self.logger.error(
                f"Command failed (exit {result.returncode}): {display}\n{detail[-2000:]}"
            )
            return None

        self.logger.info(f"Command succeeded: {display}")
        return self._redact(result.stdout or "", secrets)

    @abstractmethod
    def validate(self) -> bool:
        """Check the requirements specific to this platform. Return True if all are met."""

    @abstractmethod
    def prepare(self) -> bool:
        """Generate or check the files this platform needs (render.yaml, Procfile, ...)."""

    @abstractmethod
    def deploy(self) -> bool:
        """Deploy to the platform, through its API or CLI. Return True on success."""

    @abstractmethod
    def get_config_template(self) -> Dict[str, Any]:
        """Return the platform's configuration file as a dictionary."""

    def generate_config_file(self, output_path: Optional[str] = None) -> bool:
        """
        Write the platform's config file (render.yaml, railway.json, ...).

        Args:
            output_path: File to write, relative to the project root. Defaults
                to "<platform>.yaml".

        Returns:
            True if the file was written.
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
