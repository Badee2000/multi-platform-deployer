"""Heroku platform deployer."""

from typing import Dict, Any
from .base import BaseDeployer
from ..utils.helpers import file_exists


class HerokuDeployer(BaseDeployer):
    """Deployer for Heroku platform."""
    
    @staticmethod
    def get_platform_name() -> str:
        """Get platform name."""
        return "Heroku"
    
    def validate(self) -> bool:
        """
        Validate Heroku deployment readiness.
        
        Returns:
            True if ready to deploy
        """
        self.logger.info("Validating Heroku deployment readiness...")
        
        checks = [
            (self._check_procfile, "Procfile"),
            (self._check_requirements, "requirements.txt"),
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
        Prepare Heroku deployment.
        
        Returns:
            True if preparation successful
        """
        self.logger.info("Preparing Heroku deployment...")
        
        # Ensure Procfile exists
        if not file_exists(str(self.project_root / "Procfile")):
            self._create_procfile()
        
        return True
    
    def deploy(self) -> bool:
        """
        Execute Heroku deployment.
        
        Returns:
            True if deployment successful
        """
        self.logger.info("Deploying to Heroku...")
        self.logger.info("Use 'heroku deploy' or 'git push heroku main'")
        
        return True
    
    def get_config_template(self) -> Dict[str, Any]:
        """
        Get Heroku configuration template.
        
        Returns:
            Configuration template (Procfile content)
        """
        return {
            "procfile": "web: python app.py",
        }

    def rollback(self, deployment_state: Dict[str, Any]) -> bool:
        """Redeploy restored snapshot by triggering Heroku deployment."""
        self.logger.info("Redeploying previous snapshot to Heroku...")
        self.logger.info(
            "Run 'heroku releases:rollback' if you maintain releases on Heroku."
        )
        return super().rollback(deployment_state)
    
    def _check_procfile(self) -> bool:
        """Check if Procfile exists."""
        return file_exists(str(self.project_root / "Procfile"))
    
    def _check_requirements(self) -> bool:
        """Check if requirements.txt exists."""
        return file_exists(str(self.project_root / "requirements.txt"))
    
    def _create_procfile(self) -> None:
        """Create Procfile."""
        procfile_content = f"web: python app.py"
        with open(self.project_root / "Procfile", "w") as f:
            f.write(procfile_content)
        self.logger.info("Procfile created")
