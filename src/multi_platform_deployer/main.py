"""
The Deployer class: the programmatic entry point behind the command line.

It runs readiness checks, deploys to a platform, runs migrations, checks the
health of a deployed app and rolls back. Use it from the CLI or import it for
scripts and CI:

    deployer = Deployer(".")
    is_ready, results = deployer.check_deployment_readiness("flask")
    if is_ready:
        deployer.deploy("render")
"""

import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from .checkers import (
    BaseChecker,
    CheckResult,
    DjangoChecker,
    FastAPIChecker,
    FlaskChecker,
    SystemChecker,
)
from .config.loader import ConfigLoader
from .config.validator import ConfigValidator
from .deployers import (
    BaseDeployer,
    HerokuDeployer,
    RailwayDeployer,
    RenderDeployer,
    VercelDeployer,
)
from .scripts.health_check import HealthChecker
from .scripts.migrator import DatabaseMigrator
from .scripts.rollback import RollbackManager
from .utils.logger import setup_logger


class Deployer:
    """
    Coordinates checks, deployments, migrations, health checks and rollbacks.

    Example:
        deployer = Deployer(".")
        is_ready, results = deployer.check_deployment_readiness("flask")
        if is_ready:
            deployer.deploy("render", run_migrations=True)
    """

    AVAILABLE_DEPLOYERS: Dict[str, Callable[..., BaseDeployer]] = {
        "render": RenderDeployer,
        "railway": RailwayDeployer,
        "vercel": VercelDeployer,
        "heroku": HerokuDeployer,
    }

    AVAILABLE_CHECKERS: Dict[str, Callable[..., BaseChecker]] = {
        "flask": FlaskChecker,
        "django": DjangoChecker,
        "fastapi": FastAPIChecker,
    }

    def __init__(
        self,
        project_root: str = ".",
        config_file: Optional[str] = None,
        log_level: Optional[int] = None,
        dry_run: bool = False,
    ):
        """
        Args:
            project_root: Root directory of the project.
            config_file: Path to the deployment config. Found automatically if omitted.
            log_level: Logging level (10 debug, 20 info, 30 warning, 40 error).
            dry_run: Print every step and command instead of running them.
        """
        self.project_root = Path(project_root)
        self.dry_run = dry_run
        self.logger = setup_logger(level=log_level or logging.INFO)

        self.config_loader = ConfigLoader(project_root)
        self.config = self.config_loader.load_config(config_file) or {}

        # Created on first use.
        self.deployers: Dict[str, BaseDeployer] = {}
        self.checkers: Dict[str, BaseChecker] = {}
        self.system_results: List[CheckResult] = []

        self.migrator = DatabaseMigrator(project_root)
        self.health_checker = HealthChecker()
        self.rollback_manager = RollbackManager(project_root)

        self.logger.debug(f"Project: {project_root}")

    def _run_system_checks(self) -> Tuple[bool, List[CheckResult]]:
        """Run platform-agnostic checks before any framework logic."""

        system_checker = SystemChecker(str(self.project_root))
        system_ready, system_results = system_checker.check_all()
        self.checkers["system"] = system_checker
        self.system_results = system_results
        return system_ready, system_results

    def check_deployment_readiness(
        self,
        framework: str = "flask",
    ) -> Tuple[bool, List[CheckResult]]:
        """
        Run the system checks and the checks for one framework.

        Args:
            framework: "flask", "django" or "fastapi".

        Returns:
            (is_ready, results). Results cover every check, passed or not.
        """
        system_ready, system_results = self._run_system_checks()

        name = framework.lower()
        checker_class = self.AVAILABLE_CHECKERS.get(name)
        if checker_class is None:
            self.logger.error(f"Unknown framework: {framework}")
            return False, system_results

        checker = checker_class(str(self.project_root))
        is_ready, results = checker.check_all()
        self.checkers[name] = checker

        return system_ready and is_ready, system_results + results

    def initialize_deployer(self, platform: str) -> Optional[BaseDeployer]:
        """Create and remember the deployer for a platform, or None if it is unknown."""
        name = platform.lower()
        deployer_class = self.AVAILABLE_DEPLOYERS.get(name)
        if deployer_class is None:
            self.logger.error(f"Unknown platform: {platform}")
            return None

        deployer = deployer_class(
            str(self.project_root), self.config, dry_run=self.dry_run
        )
        self.deployers[name] = deployer
        return deployer

    def validate_deployment(self, platform: str) -> bool:
        """Check the configuration and the platform's own requirements."""
        is_valid, errors = ConfigValidator.validate(self.config)
        if not is_valid:
            self.logger.error(f"Configuration validation failed: {errors}")
            return False

        deployer = self.initialize_deployer(platform)
        if not deployer:
            return False

        if not deployer.validate():
            self.logger.error(f"Validation failed for {platform}")
            return False

        return True

    def prepare_deployment(self, platform: str) -> bool:
        """Let the platform's deployer generate any files it needs."""
        deployer = self.initialize_deployer(platform)
        if not deployer:
            return False

        if not deployer.prepare():
            self.logger.error(f"Preparation failed for {platform}")
            return False

        return True

    def deploy(self, platform: str, run_migrations: bool = True) -> bool:
        """
        Deploy to one platform.

        Runs the system checks, validates the config, optionally runs database
        migrations, then calls the platform's deployer. Failures are logged and
        returned as False. Nothing is raised.

        Args:
            platform: "render", "railway", "vercel" or "heroku".
            run_migrations: Run database migrations before deploying.
        """
        self.logger.info(f"Deploying to {platform}")

        system_ready, system_results = self._run_system_checks()
        if not system_ready:
            self.logger.error("System checks failed. Nothing was deployed.")
            for result in system_results:
                if not result.passed:
                    self.logger.error("  - %s: %s", result.name, result.message)
            return False

        # Fill in required keys that no deployment file sets.
        self.config.setdefault("platform", platform)
        self.config.setdefault(
            "app_name", self.project_root.resolve().name.replace(" ", "-")
        )
        if not self.validate_deployment(platform):
            self.logger.error("Validation failed. Nothing was deployed.")
            return False

        # Migrations run first and stop the deploy on failure: new code against
        # an unmigrated database can break the app.
        if run_migrations and self.dry_run:
            self.logger.info("[dry-run] Would run database migrations.")
        elif run_migrations:
            self.logger.info("Running database migrations")
            if not self.migrator.run_migrations():
                self.logger.error("Migrations failed. Nothing was deployed.")
                return False

        deployer = self.deployers.get(platform.lower()) or self.initialize_deployer(
            platform
        )
        if not deployer or not deployer.deploy():
            self.logger.error(f"Deployment to {platform} failed.")
            return False

        if self.dry_run:
            self.logger.info(f"[dry-run] Nothing was deployed to {platform}.")
            return True

        deployed_url = getattr(deployer, "deployed_url", None)
        self.logger.info(f"Deployed to {platform}.")
        if deployed_url:
            self.logger.info(f"URL: {deployed_url}")

        self.rollback_manager.create_checkpoint(
            platform=platform,
            metadata={
                "run_migrations": run_migrations,
                "config_snapshot": self.config,
                "checked_frameworks": list(self.checkers.keys()),
                "deployed_url": deployed_url,
            },
        )
        return True

    def deploy_to_multiple_platforms(
        self,
        platforms: List[str],
        run_migrations: bool = True,
    ) -> Dict[str, bool]:
        """
        Deploy to several platforms, one after another.

        A failure on one platform does not stop the others, and a successful
        deploy is not undone when a later one fails.

        Returns:
            Maps each platform name to True (deployed) or False (failed).
        """
        results = {}
        for platform in platforms:
            self.logger.info(f"\nDeploying to {platform}")
            results[platform] = self.deploy(platform, run_migrations)
        return results

    def check_health(
        self,
        base_url: str = "http://localhost:8000",
        endpoints: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Check that a deployed app answers, and print a summary.

        The server counts as up when the base URL answers with a status below
        500. Each endpoint is requested and its status reported. Database
        connectivity and response times are not checked.

        Args:
            base_url: Base URL of the app, for example https://my-app.onrender.com.
            endpoints: Paths to request, appended to the base URL. Defaults to "/".

        Returns:
            For example {"server_up": True, "endpoints": {"/": {"status": 200, "ok": True}}}.
        """
        self.health_checker.base_url = base_url
        results = self.health_checker.run_all_checks(endpoints)
        self.health_checker.print_summary(results)

        return results

    def rollback(self) -> bool:
        """
        Restore the previous deployment snapshot and hand it to the platform.

        The platform's deployer decides what that means. By default it redeploys
        the restored code. On Render it rolls the live service back. To roll back
        the running service without touching local files, use rollback_live().
        """

        def _redeploy_previous(state: Dict[str, Any]) -> bool:
            platform = state.get("platform")
            if not platform:
                self.logger.error("Rollback state missing platform information")
                return False
            platform = platform.lower()
            deployer = self.deployers.get(platform) or self.initialize_deployer(
                platform
            )
            if not deployer:
                return False
            return deployer.rollback(state)

        return self.rollback_manager.rollback_to_previous(_redeploy_previous)

    def rollback_live(self, platform: Optional[str] = None) -> bool:
        """
        Roll back the running service on its platform, without touching local files.

        Uses the platform from the most recent deployment record unless one is given.
        Returns False for platforms without a real live rollback.
        """
        if platform is None:
            records = self.rollback_manager.list_deployment_records()
            if not records:
                self.logger.error(
                    "No deployment record found. Pass the platform explicitly."
                )
                return False
            platform = str(records[0].get("platform", ""))
        if not platform:
            self.logger.error("Deployment record has no platform information")
            return False

        deployer = self.deployers.get(platform.lower()) or self.initialize_deployer(
            platform.lower()
        )
        if not deployer:
            return False
        return deployer.rollback_live()

    def print_summary(self) -> None:
        """Print the project root, configuration and available deployers and checkers."""
        print(f"Project root: {self.project_root}")
        print(f"Configuration: {self.config}")
        print(f"Deployers: {', '.join(self.AVAILABLE_DEPLOYERS)}")
        print(f"Checkers: {', '.join(self.AVAILABLE_CHECKERS)}")
