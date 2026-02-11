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
            (self._check_railway_config, "Railway configuration"),
            (self._check_procfile, "Procfile or start command"),
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
        Execute Railway deployment.
        
        Returns:
            True if deployment successful
        """
        self.logger.info("Deploying to Railway...")
        self.logger.info("Use 'railway up' command to deploy")
        self.logger.info("Or push to your connected version control system")
        
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
                "builder": "dockerfile"
            },
            "deploy": {
                "startCommand": "python app.py",
                "restartPolicyType": "on_failure",
                "restartPolicyMaxRetries": 5
            }
        }
    
    def _check_railway_config(self) -> bool:
        """Check if railway.json exists."""
        return file_exists(str(self.project_root / "railway.json")) or \
               file_exists(str(self.project_root / "railway.yaml"))
    
    def _check_procfile(self) -> bool:
        """Check if Procfile or start command is configured."""
        procfile_exists = file_exists(str(self.project_root / "Procfile"))
        has_start_command = "start_command" in self.config
        return procfile_exists or has_start_command

    def rollback(self, deployment_state: Dict[str, Any]) -> bool:
        """Redeploy restored snapshot for Railway deployments."""
        self.logger.info("Triggering Railway rollback by redeploying restored snapshot...")
        self.logger.info("Run 'railway up' to redeploy or push restored code to your repo.")
        return super().rollback(deployment_state)
