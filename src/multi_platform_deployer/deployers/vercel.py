"""Vercel platform deployer."""

import json
from typing import Any, Dict, Optional

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

    supports_live_rollback = True

    def rollback_live(self) -> bool:
        """
        Point production back at the second newest successful production deployment.

        Passes that deployment to `vercel rollback` explicitly, because the CLI's
        no-argument form can treat a failed newest deployment as the current one
        and change nothing. Vercel reuses the old build, so nothing is rebuilt.
        Afterwards Vercel stops promoting new deployments to production by itself,
        and the final log lines say how to undo that.
        """
        token = self._require_credential("VERCEL_TOKEN")
        if token is None:
            return False

        target = self._previous_production_url(token)
        if target is None:
            return False

        output = self._run_step(
            ["vercel", "rollback", target, "--yes", "--timeout", "3m"],
            env={"VERCEL_TOKEN": token},
            secrets=[token],
        )
        if output is None:
            self.logger.error(
                "Vercel rollback failed; see the output above. "
                "Production was not changed by this tool."
            )
            return False

        if not self.dry_run:
            self.logger.info(
                f"Vercel accepted the rollback to {target}. Check that your "
                "production domain now serves the older version."
            )
            self.logger.warning(
                "Vercel now stops putting new deployments on your production domain. "
                "To resume normal deploys, run 'vercel promote <deployment-url>' "
                "(or use Manage on the project's Production Deployment tile)."
            )
        return True

    def _previous_production_url(self, token: str) -> Optional[str]:
        """URL of the second newest READY production deployment, or None."""
        output = self._run_step(
            [
                "vercel",
                "list",
                "--environment",
                "production",
                "--status",
                "READY",
                "--json",
            ],
            env={"VERCEL_TOKEN": token},
            secrets=[token],
        )
        if output is None:
            return None
        if self.dry_run:
            return "<previous production deployment>"

        try:
            data = json.loads(output[output.index("{") :])
        except ValueError:
            self.logger.error("Could not read the list of Vercel deployments.")
            return None
        deployments = [
            d
            for d in (data.get("deployments") or [] if isinstance(data, dict) else [])
            if isinstance(d, dict) and d.get("url")
        ]
        deployments.sort(key=lambda d: d.get("createdAt") or 0, reverse=True)
        if len(deployments) < 2:
            self.logger.error(
                "Rollback needs at least two successful production deployments, "
                f"found {len(deployments)}. Nothing was changed."
            )
            return None
        return f"https://{deployments[1]['url']}"
