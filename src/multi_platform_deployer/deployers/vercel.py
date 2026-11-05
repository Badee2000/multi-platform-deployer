"""Vercel platform deployer."""

from typing import Any, Dict

from ..utils.helpers import file_exists
from .base import BaseDeployer


class VercelDeployer(BaseDeployer):
    """Deployer for Vercel platform."""

    # Files Vercel's Python runtime detects as the app entry point (also looked up
    # under src/ and app/). manage.py covers Django, which Vercel resolves from
    # WSGI_APPLICATION. api/index.py is the older layout and still works.
    ENTRY_POINTS = (
        "app.py",
        "index.py",
        "server.py",
        "main.py",
        "wsgi.py",
        "asgi.py",
        "manage.py",
        "api/index.py",
    )
    ENTRY_POINT_DIRS = ("", "src/", "app/")

    @staticmethod
    def get_platform_name() -> str:
        """Get platform name."""
        return "Vercel"

    def validate(self) -> bool:
        """Check that the project has what Vercel needs."""
        self.logger.info("Validating Vercel deployment readiness")

        return self._run_checks(
            [
                (
                    self._check_api_routes,
                    "Python entry point (app.py, main.py, wsgi.py, asgi.py, manage.py, ...)",
                ),
                (self._check_requirements, "requirements.txt"),
            ]
        )

    def prepare(self) -> bool:
        """
        Prepare Vercel deployment.

        Vercel detects Flask, FastAPI and Django on its own, so no vercel.json is
        generated. An existing one is left untouched.

        Returns:
            True if preparation successful
        """
        self.logger.info(
            "Preparing Vercel deployment (no vercel.json needed for Flask, FastAPI or Django)..."
        )
        return True

    def deploy(self) -> bool:
        """
        Deploy to production with the Vercel CLI.

        Uses VERCEL_TOKEN from the environment. Returns True only if the CLI
        exits successfully.
        """
        token = self._require_credential("VERCEL_TOKEN")
        if token is None:
            return False

        output = self._run_step(
            ["vercel", "deploy", "--prod", "--yes"],
            env={"VERCEL_TOKEN": token},
            secrets=[token],
        )
        if output is None:
            self.logger.error("Vercel deployment failed; see the output above.")
            return False

        urls = [
            line.strip()
            for line in output.splitlines()
            if line.strip().startswith("https://")
        ]
        self.deployed_url = urls[-1] if urls else None
        self.logger.info(
            f"Vercel deployment finished: {self.deployed_url or 'URL not reported'}"
        )
        return True

    def get_config_template(self) -> Dict[str, Any]:
        """
        Get Vercel configuration template.

        Vercel needs no config file for supported Python frameworks, so this is
        deliberately empty. Add a vercel.json yourself only for custom routing.

        Returns:
            An empty template
        """
        return {}

    def _check_api_routes(self) -> bool:
        """Check that a Python entry point Vercel can detect exists."""
        return any(
            file_exists(str(self.project_root / (prefix + name)))
            for prefix in self.ENTRY_POINT_DIRS
            for name in self.ENTRY_POINTS
        )

    def _check_requirements(self) -> bool:
        """Vercel installs Python dependencies from requirements.txt."""
        return file_exists(str(self.project_root / "requirements.txt"))

    def rollback(self, deployment_state: Dict[str, Any]) -> bool:
        """Redeploy restored snapshot for Vercel deployments."""
        self.logger.info("Triggering Vercel redeployment of restored snapshot...")
        self.logger.info(
            "Run 'vercel --prod' or push the restored commit to your linked repository."
        )
        return super().rollback(deployment_state)
