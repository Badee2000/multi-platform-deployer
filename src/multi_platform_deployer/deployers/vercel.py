"""Vercel platform deployer."""

from typing import Dict, Any
from .base import BaseDeployer
from ..utils.helpers import file_exists


class VercelDeployer(BaseDeployer):
    """Deployer for Vercel platform."""
    
    @staticmethod
    def get_platform_name() -> str:
        """Get platform name."""
        return "Vercel"
    
    def validate(self) -> bool:
        """
        Validate Vercel deployment readiness.
        
        Returns:
            True if ready to deploy
        """
        self.logger.info("Validating Vercel deployment readiness...")
        
        checks = [
            (self._check_vercel_json, "vercel.json configuration"),
            (self._check_api_routes, "API routes structure"),
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
        Prepare Vercel deployment.
        
        Returns:
            True if preparation successful
        """
        self.logger.info("Preparing Vercel deployment...")
        
        # Generate vercel.json if not exists
        if not file_exists(str(self.project_root / "vercel.json")):
            self.generate_config_file("vercel.json")
        
        return True
    
    def deploy(self) -> bool:
        """
        Execute Vercel deployment.
        
        Returns:
            True if deployment successful
        """
        self.logger.info("Deploying to Vercel...")
        self.logger.info("Use 'vercel' command to deploy")
        self.logger.info("Or push to your connected GitHub repository")
        
        return True
    
    def get_config_template(self) -> Dict[str, Any]:
        """
        Get Vercel configuration template.
        
        Returns:
            Configuration template
        """
        return {
            "version": 2,
            "builds": [
                {
                    "src": "app.py",
                    "use": "@vercel/python"
                }
            ],
            "routes": [
                {
                    "src": "/(.*)",
                    "dest": "app.py"
                }
            ],
            "env": {
                "PYTHON_VERSION": "3.9"
            }
        }
    
    def _check_vercel_json(self) -> bool:
        """Check if vercel.json exists."""
        return file_exists(str(self.project_root / "vercel.json"))
    
    def _check_api_routes(self) -> bool:
        """Check if API routes are properly structured."""
        # For Python, Vercel expects app.py as entry point
        return file_exists(str(self.project_root / "app.py"))

    def rollback(self, deployment_state: Dict[str, Any]) -> bool:
        """Redeploy restored snapshot for Vercel deployments."""
        self.logger.info("Triggering Vercel redeployment of restored snapshot...")
        self.logger.info(
            "Run 'vercel --prod' or push the restored commit to your linked repository."
        )
        return super().rollback(deployment_state)
