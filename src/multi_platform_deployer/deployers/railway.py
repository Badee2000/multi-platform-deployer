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
        
        Returns:
            True if preparation successful
        """
        self.logger.info("Preparing Railway deployment...")
        
        # Generate railway.json if not exists
        if not file_exists(str(self.project_root / "railway.json")):
            self.generate_config_file("railway.json")
        
        return True
    
    def deploy(self) -> bool:
        """
        Deploy with the Railway CLI.

        Uses RAILWAY_TOKEN (a project token) from the environment. The token
        identifies the project, so no interactive `railway link` is needed.
        Railway's CLI does not print a stable public URL; run `railway domain`
        to see it.
        """
        token = self._require_credential("RAILWAY_TOKEN")
        if token is None:
            return False

        output = self._run_step(
            ["railway", "up", "--ci"],
            env={"RAILWAY_TOKEN": token},
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
        return {
            "$schema": "https://railway.app/railway.schema.json",
            "build": {
                "builder": "NIXPACKS"
            },
            "deploy": {
                "startCommand": "python app.py",
                "restartPolicyType": "ON_FAILURE",
                "restartPolicyMaxRetries": 5
            }
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
