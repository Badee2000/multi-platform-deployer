"""Heroku platform deployer."""

from typing import Dict, Any, Optional
from .base import BaseDeployer
from ..utils.helpers import file_exists, has_uncommitted_changes


class HerokuDeployer(BaseDeployer):
    """Deployer for Heroku platform."""

    # Git asks this helper for credentials. It reads the key from the process
    # environment at push time, so the key never appears in the command line.
    # The empty credential.helper before it clears any helper that could prompt.
    _CREDENTIAL_HELPER = "!f() { echo username=heroku; echo password=$HEROKU_API_KEY; }; f"
    
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
            (self._check_procfile, "Procfile (or 'start_command' in your config)"),
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

        A Procfile is only created from your 'start_command'. No start command
        is guessed, because a wrong guess only fails after the push.
        
        Returns:
            True if preparation successful
        """
        self.logger.info("Preparing Heroku deployment...")
        
        if not file_exists(str(self.project_root / "Procfile")) and self.config.get("start_command"):
            self._create_procfile()
            self.logger.warning(
                "Procfile created from 'start_command'. Heroku deploys committed code only: "
                "commit the Procfile, then run again."
            )
        
        return True
    
    def deploy(self) -> bool:
        """
        Deploy by pushing the committed code to Heroku's git remote.

        Preconditions checked here:
        - HEROKU_API_KEY is set and the Heroku CLI accepts it.
        - The project is a git repository with no uncommitted changes
          (git push only deploys commits, so uncommitted edits would be
          silently left out).
        - A 'heroku' git remote exists (created by 'heroku create' or
          'heroku git:remote -a <app>').
        """
        api_key = self._require_credential("HEROKU_API_KEY")
        if api_key is None:
            return False

        env: Dict[str, Optional[str]] = {"HEROKU_API_KEY": api_key}
        if self._run_step(["heroku", "auth:whoami"], env=env, secrets=[api_key]) is None:
            self.logger.error("Heroku rejected HEROKU_API_KEY (or the CLI is missing).")
            return False

        status = self._run_step(["git", "status", "--porcelain"])
        if status is None:
            self.logger.error("Could not read git status. Is this project a git repository?")
            return False
        if has_uncommitted_changes(status):
            self.logger.error(
                "Uncommitted changes would not be deployed. Commit them first, then run again."
            )
            return False

        output = self._run_step(
            [
                "git",
                "-c", "credential.helper=",
                "-c", f"credential.helper={self._CREDENTIAL_HELPER}",
                "push", "heroku", "HEAD:main",
            ],
            env={"HEROKU_API_KEY": api_key, "GIT_TERMINAL_PROMPT": "0"},
            secrets=[api_key],
        )
        if output is None:
            self.logger.error("Heroku deployment failed; see the output above.")
            return False

        self.logger.info("Heroku deployment finished. Run 'heroku open' to view the app.")
        return True
    
    def get_config_template(self) -> Dict[str, Any]:
        """
        Get Heroku configuration template.
        
        Returns:
            Configuration template (Procfile content)
        """
        return {
            "procfile": f"web: {self.config.get('start_command', 'gunicorn app:app')}",
        }

    def rollback(self, deployment_state: Dict[str, Any]) -> bool:
        """Redeploy restored snapshot by triggering Heroku deployment."""
        self.logger.info("Redeploying previous snapshot to Heroku...")
        self.logger.info(
            "Run 'heroku releases:rollback' if you maintain releases on Heroku."
        )
        return super().rollback(deployment_state)
    
    def _check_procfile(self) -> bool:
        """A Procfile, or a 'start_command' to create one from."""
        return file_exists(str(self.project_root / "Procfile")) or bool(self.config.get("start_command"))
    
    def _check_requirements(self) -> bool:
        """Check if requirements.txt exists."""
        return file_exists(str(self.project_root / "requirements.txt"))
    
    def _create_procfile(self) -> None:
        """Create a Procfile from the configured start command."""
        procfile_content = f"web: {self.config['start_command']}\n"
        with open(self.project_root / "Procfile", "w", encoding="utf-8") as f:
            f.write(procfile_content)
        self.logger.info("Procfile created")
