"""Railway platform deployer."""

from typing import Dict, Any
from .base import BaseDeployer
from ..utils.helpers import file_exists


class RailwayDeployer(BaseDeployer):
    """Deployer for Railway.app platform."""
    
    @staticmethod
    def get_platform_name() -> str:
        """Get platform name."""
        return "Railway"
    
    def validate(self) -> bool:
        """
        Validate Railway deployment readiness.
        
        Returns:
            True if ready to deploy
        """
        self.logger.info("Validating Railway deployment readiness...")
        
        checks = [
            (self._check_requirements, "requirements.txt"),
            (self._check_procfile, "Start command (Procfile, railway.json or start_command in config)"),
        ]
        
        all_valid = True
        for check_func, description in checks:
            if not check_func():
                self.logger.warning(f"❌ {description} check failed")
                all_valid = False
            else:
                self.logger.info(f"✓ {description} check passed")
        
        return all_valid
    
    def prepare(self) -> bool:
        """
        Prepare Railway deployment.

        railway.json is only generated when 'start_command' is set in your config,
        so the command you chose is used. Without it, a Procfile or an existing
        railway.json decides how the app starts. Nothing is guessed.
        
        Returns:
            True if preparation successful
        """
        self.logger.info("Preparing Railway deployment...")
        
        if not file_exists(str(self.project_root / "railway.json")) and self.config.get("start_command"):
            self.generate_config_file("railway.json")
        
        return True
    
    def deploy(self) -> bool:
        """
        Deploy with the Railway CLI.

        Uses RAILWAY_TOKEN (a project token) from the environment. The project,
        environment and service must already exist, because Railway never
        creates projects in CI. Optional config keys 'railway_project',
        'railway_environment' and 'railway_service' are passed as --project,
        --environment and --service. Railway's CLI does not print a stable
        public URL; run `railway domain` to see it.
        """
        token = self._require_credential("RAILWAY_TOKEN")
        if token is None:
            return False

        command = ["railway", "up", "--ci"]
        for config_key, flag in (
            ("railway_project", "--project"),
            ("railway_environment", "--environment"),
            ("railway_service", "--service"),
        ):
            value = self.config.get(config_key)
            if value:
                command += [flag, str(value)]

        # Railway rejects runs where both token variables are set.
        output = self._run_step(
            command,
            env={"RAILWAY_TOKEN": token, "RAILWAY_API_TOKEN": None},
            secrets=[token],
        )
        if output is None:
            self.logger.error("Railway deployment failed; see the output above.")
            return False

        self.logger.info("Railway deployment finished. Run 'railway domain' to get the public URL.")
        return True
    
    def get_config_template(self) -> Dict[str, Any]:
        """
        Get Railway configuration template.
        
        Returns:
            Configuration template
        """
        deploy: Dict[str, Any] = {
            "restartPolicyType": "ON_FAILURE",
            "restartPolicyMaxRetries": 5,
        }
        start_command = self.config.get("start_command")
        if start_command:
            deploy["startCommand"] = str(start_command)
        return {
            "$schema": "https://railway.app/railway.schema.json",
            "build": {
                "builder": "NIXPACKS"
            },
            "deploy": deploy,
        }
    
    def _check_requirements(self) -> bool:
        """Railway's Nixpacks builder installs dependencies from requirements.txt."""
        return file_exists(str(self.project_root / "requirements.txt"))

    def _check_railway_config(self) -> bool:
        """Check if railway.json exists."""
        return file_exists(str(self.project_root / "railway.json")) or \
               file_exists(str(self.project_root / "railway.yaml"))
    
    def _check_procfile(self) -> bool:
        """Check that a start command is configured."""
        procfile_exists = file_exists(str(self.project_root / "Procfile"))
        has_start_command = "start_command" in self.config
        return procfile_exists or has_start_command or self._check_railway_config()

    def rollback(self, deployment_state: Dict[str, Any]) -> bool:
        """Redeploy restored snapshot for Railway deployments."""
        self.logger.info("Triggering Railway rollback by redeploying restored snapshot...")
        self.logger.info("Run 'railway up' to redeploy or push restored code to your repo.")
        return super().rollback(deployment_state)
