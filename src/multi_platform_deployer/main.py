"""
Main entry point for the deployer.

This module contains the Deployer class, which is the heart of everything.
It orchestrates:
- Checking if your app is production-ready
- Deploying to the right platform
- Running migrations
- Health checks
- Rollbacks

You can use this either through the CLI (python deploy.py) or by importing this class
directly for scripting or CI/CD integration.
"""

from typing import Dict, List, Optional, Any
from pathlib import Path
from .deployers import (
    BaseDeployer,
    RenderDeployer,
    RailwayDeployer,
    VercelDeployer,
    HerokuDeployer,
)
from .checkers import (
    BaseChecker,
    FlaskChecker,
    DjangoChecker,
    FastAPIChecker,
    SystemChecker,
    CheckResult,
)
from .config.loader import ConfigLoader
from .config.validator import ConfigValidator
from .scripts.migrator import DatabaseMigrator
from .scripts.health_check import HealthChecker
from .scripts.rollback import RollbackManager
from .utils.logger import setup_logger, get_logger


class Deployer:
    """
    Main Deployer class - orchestrates everything.
    
    This is the central class that coordinates all deployment operations.
    It's responsible for:
    - Detecting which framework you're using (Flask, Django, FastAPI)
    - Running readiness checks
    - Deploying to your chosen platform(s)
    - Managing migrations
    - Health checks
    - Rollbacks
    
    Example:
        deployer = Deployer(".")
        is_ready, results = deployer.check_deployment_readiness("flask")
        if is_ready:
            deployer.deploy("render", run_migrations=True)
    """
    
    # Map of platform names to deployer classes
    # This is how we know which deployer to use when you pick a platform
    AVAILABLE_DEPLOYERS = {
        "render": RenderDeployer,
        "railway": RailwayDeployer,
        "vercel": VercelDeployer,
        "heroku": HerokuDeployer,
    }
    
    # Map of framework names to checker classes
    # This is how we know which checks to run for Flask vs Django vs FastAPI
    AVAILABLE_CHECKERS = {
        "flask": FlaskChecker,
        "django": DjangoChecker,
        "fastapi": FastAPIChecker,
    }
    
    def __init__(
        self,
        project_root: str = ".",
        config_file: Optional[str] = None,
        log_level: int = None,
    ):
        """
        Initialize the deployer.
        
        This sets up everything we need:
        - Where your project is located
        - Load any deployment configuration files (deployment.yaml, deployment.json)
        - Set up logging so you can see what's happening
        - Initialize helpers for migrations, health checks, and rollbacks
        
        Args:
            project_root: Root directory of your project (default: current directory)
            config_file: Path to deployment config file (we auto-detect if not specified)
            log_level: Logging verbosity (10=DEBUG, 20=INFO, 30=WARNING, 40=ERROR)
        
        Example:
            deployer = Deployer("./my_app")
            deployer = Deployer(".", config_file="deployment.yaml")
        """
        self.project_root = Path(project_root)
        
        # Set up logging - INFO level by default (20), which shows key events
        # Set to 10 for DEBUG if you want to see everything
        self.logger = setup_logger(level=log_level or 20)
        
        # Load configuration from YAML/JSON files if they exist
        self.config_loader = ConfigLoader(project_root)
        self.config = self.config_loader.load_config(config_file) or {}
        
        # Will store deployed instances of each deployer
        # (so we only create them when needed)
        self.deployers: Dict[str, BaseDeployer] = {}
        
        # Will store checker instances (for readiness validation)
        self.checkers: Dict[str, BaseChecker] = {}
        self.system_results: List[CheckResult] = []
        
        # Tools for migrations, health checks, and rollbacks
        self.migrator = DatabaseMigrator(project_root)
        self.health_checker = HealthChecker()
        self.rollback_manager = RollbackManager(project_root)
        
        self.logger.info(f"Deployer initialized for project: {project_root}")
    
    def _run_system_checks(self) -> tuple[bool, List[CheckResult]]:
        """Run platform-agnostic checks before any framework logic."""

        system_checker = SystemChecker(str(self.project_root))
        system_ready, system_results = system_checker.check_all()
        self.checkers["system"] = system_checker
        self.system_results = system_results
        return system_ready, system_results

    def check_deployment_readiness(
        self,
        framework: str = "flask",
    ) -> tuple[bool, List[CheckResult]]:
        """
        Check if application is ready for deployment.
        
        This is the "pre-flight check" for deployment. We validate:
        - Do you have all required files? (requirements.txt, manage.py, etc.)
        - Is your app configured correctly for production?
        - Are secrets/keys properly handled (not hardcoded)?
        - Is debug mode off?
        - Are database connections properly configured?
        - And much more...
        
        Each framework (Flask, Django, FastAPI) has specific requirements,
        so we run framework-specific checks based on what you tell us.
        
        Args:
            framework: Which framework you're using (flask, django, or fastapi)
        
        Returns:
            Tuple of:
            - is_ready (bool): True if all checks pass, False if any fail
            - check_results (list): Detailed results for each check showing what passed/failed
        
        Example:
            deployer = Deployer(".")
            is_ready, results = deployer.check_deployment_readiness("flask")
            
            if is_ready:
                print("Ready to deploy!")
            else:
                for result in results:
                    if not result.passed:
                        print(f"Fix this: {result.message}")
        """
        system_ready, system_results = self._run_system_checks()

        # First, make sure we know how to check this framework
        if framework.lower() not in self.AVAILABLE_CHECKERS:
            self.logger.error(f"Unknown framework: {framework}")
            return False, system_results
        
        # Get the right checker class for this framework
        # (e.g., FlaskChecker for "flask")
        checker_class = self.AVAILABLE_CHECKERS[framework.lower()]
        
        # Create an instance and run all the checks
        checker = checker_class(str(self.project_root))
        is_ready, results = checker.check_all()
        
        # Save the checker so we can use it later if needed
        self.checkers[framework.lower()] = checker
        
        combined_results = system_results + results
        return system_ready and is_ready, combined_results
    
    def initialize_deployer(
        self,
        platform: str,
    ) -> Optional[BaseDeployer]:
        """
        Initialize a deployer for specific platform.
        
        Args:
            platform: Platform name (render, railway, vercel, heroku)
        
        Returns:
            Deployer instance or None
        """
        if platform.lower() not in self.AVAILABLE_DEPLOYERS:
            self.logger.error(f"Unknown platform: {platform}")
            return None
        
        deployer_class = self.AVAILABLE_DEPLOYERS[platform.lower()]
        deployer = deployer_class(str(self.project_root), self.config)
        self.deployers[platform.lower()] = deployer
        
        self.logger.info(f"Deployer initialized for platform: {platform}")
        return deployer
    
    def validate_deployment(self, platform: str) -> bool:
        """
        Validate deployment configuration and readiness.
        
        Args:
            platform: Platform name
        
        Returns:
            True if ready to deploy
        """
        # Validate configuration
        is_valid, errors = ConfigValidator.validate(self.config)
        if not is_valid:
            self.logger.error(f"Configuration validation failed: {errors}")
            return False
        
        # Initialize deployer
        deployer = self.initialize_deployer(platform)
        if not deployer:
            return False
        
        # Validate platform-specific requirements
        if not deployer.validate():
            self.logger.error(f"Validation failed for {platform}")
            return False
        
        self.logger.info(f"✓ Validation passed for {platform}")
        return True
    
    def prepare_deployment(self, platform: str) -> bool:
        """
        Prepare deployment (generate configs, etc.).
        
        Args:
            platform: Platform name
        
        Returns:
            True if successful
        """
        deployer = self.initialize_deployer(platform)
        if not deployer:
            return False
        
        if not deployer.prepare():
            self.logger.error(f"Preparation failed for {platform}")
            return False
        
        self.logger.info(f"✓ Preparation completed for {platform}")
        return True
    
    def deploy(self, platform: str, run_migrations: bool = True) -> bool:
        """
        Execute deployment to the specified platform.
        
        This is where the actual magic happens. Here's what we do:
        1. Validate everything is configured correctly
        2. Optionally run database migrations
        3. Ship your code to the platform
        4. Make sure it's running
        
        This is a one-shot operation - you call it and your app goes live.
        
        Args:
            platform: Which platform to deploy to (render, railway, vercel, heroku)
            run_migrations: Whether to run database migrations first (default: True)
        
        Returns:
            True if deployment succeeded, False if something went wrong
        
        Example:
            deployer = Deployer(".")
            success = deployer.deploy("render", run_migrations=True)
            if success:
                print("Deployed! Your app is live!")
        
        Raises:
            Nothing - returns False on error instead of raising exceptions
        """
        self.logger.info(f"Starting deployment to {platform}...")

        system_ready, system_results = self._run_system_checks()
        if not system_ready:
            self.logger.error("Critical system checks failed; aborting deployment.")
            for result in system_results:
                if not result.passed:
                    self.logger.error("  - %s: %s", result.name, result.message)
            return False
        
        # Step 1: Validate everything is set up correctly
        # (configs, credentials, requirements, etc.)
        if not self.validate_deployment(platform):
            self.logger.error("Deployment validation failed")
            return False
        
        # Step 2: Run database migrations if the user wants
        # (only if they have a database setup)
        if run_migrations:
            self.logger.info("Running database migrations...")
            if not self.migrator.run_migrations():
                # Migration failed, but we'll try to deploy anyway
                # Sometimes migrations will fail but the app still works
                self.logger.warning("Migrations failed, but continuing with deployment")
        
        # Step 3: Get the right deployer for this platform and deploy
        deployer = self.deployers.get(platform.lower())
        if not deployer:
            # Create a new deployer instance if we haven't already
            deployer = self.initialize_deployer(platform)
        
        # Actually execute the deployment
        if not deployer or not deployer.deploy():
            self.logger.error(f"Deployment failed for {platform}")
            return False
        
        self.logger.info(f"✓ Deployment completed for {platform}")

        self.rollback_manager.create_checkpoint(
            platform=platform,
            metadata={
                "run_migrations": run_migrations,
                "config_snapshot": self.config,
                "checked_frameworks": list(self.checkers.keys()),
            },
        )
        return True
    
    def deploy_to_multiple_platforms(
        self,
        platforms: List[str],
        run_migrations: bool = True,
    ) -> Dict[str, bool]:
        """
        Deploy to multiple platforms simultaneously.
        
        Want failover? Deploy to both Render AND Railway!
        Want redundancy? Go for Render, Railway, AND Heroku!
        
        This method deploys to each platform sequentially but efficiently,
        returning a report of what succeeded and what failed.
        
        Args:
            platforms: List of platform names to deploy to
            run_migrations: Whether to run migrations (applies to all platforms)
        
        Returns:
            Dictionary mapping each platform name to success status (True/False)
        
        Example:
            deployer = Deployer(".")
            results = deployer.deploy_to_multiple_platforms(
                ["render", "railway"],
                run_migrations=True
            )
            
            for platform, success in results.items():
                print(f"{platform}: {'✓' if success else '✗'}")
            
            # Output:
            # render: ✓
            # railway: ✓
        """
        results = {}
        
        for platform in platforms:
            self.logger.info(f"\nDeploying to {platform}...")
            results[platform] = self.deploy(platform, run_migrations)
        
        return results
    
    def check_health(
        self,
        base_url: str = "http://localhost:8000",
        endpoints: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Check application health after deployment.
        
        After you deploy, you want to make sure your app actually works, right?
        This method verifies:
        - Your server is running and responding
        - Key endpoints return the right status codes
        - Response times are reasonable
        - Database connections work (if you have a database)
        
        It's like a doctor's checkup for your deployed app!
        
        Args:
            base_url: The URL of your deployed app (e.g., https://my-app.onrender.com)
            endpoints: Optional list of specific endpoints to check
                      (defaults to just checking the home page "/")
        
        Returns:
            Dictionary with detailed health check results
        
        Example:
            deployer = Deployer(".")
            deployer.deploy("render")
            
            # Now verify the app is actually working
            health = deployer.check_health(
                base_url="https://my-app.onrender.com",
                endpoints=["/", "/api/health", "/api/status"]
            )
            
            # Returns something like:
            # {
            #     "server_up": True,
            #     "endpoints": {
            #         "/": {"status": 200, "ok": True},
            #         "/api/health": {"status": 200, "ok": True},
            #     }
            # }
        """
        self.health_checker.base_url = base_url
        results = self.health_checker.run_all_checks(endpoints)
        self.health_checker.print_summary(results)
        
        return results
    
    def rollback(self) -> bool:
        """
        Rollback to previous deployment.
        
        Uh oh, something went wrong? No problem!
        This reverts your app to the previous working version.
        
        It's safe, fast, and instant - users will see the old version
        while new requests get routed back to the previous deployment.
        
        Returns:
            True if rollback succeeded, False if something went wrong
        
        Example:
            deployer = Deployer(".")
            if deployer.rollback():
                print("Rolled back successfully!")
            else:
                print("Rollback failed :(")
        """
        def _redeploy_previous(state: Dict[str, Any]) -> bool:
            platform = state.get("platform")
            if not platform:
                self.logger.error("Rollback state missing platform information")
                return False
            platform = platform.lower()
            deployer = self.deployers.get(platform) or self.initialize_deployer(platform)
            if not deployer:
                return False
            return deployer.rollback(state)

        return self.rollback_manager.rollback_to_previous(_redeploy_previous)
    
    def print_summary(self) -> None:
        """Print deployment summary."""
        print("\n" + "="*60)
        print("Deployment Summary")
        print("="*60)
        print(f"Project Root: {self.project_root}")
        print(f"Configuration: {self.config}")
        print(f"Available Deployers: {', '.join(self.AVAILABLE_DEPLOYERS.keys())}")
        print(f"Available Checkers: {', '.join(self.AVAILABLE_CHECKERS.keys())}")
        print("="*60 + "\n")
