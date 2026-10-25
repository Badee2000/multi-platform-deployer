"""Render platform deployer."""

import os
import re
from typing import Dict, Any, Optional

import requests

from .base import BaseDeployer
from ..utils.helpers import file_exists

RENDER_API_BASE = "https://api.render.com/v1"
REQUEST_TIMEOUT = 30  # seconds per API call


class RenderDeployer(BaseDeployer):
    """Deployer for Render.com platform."""
    
    @staticmethod
    def get_platform_name() -> str:
        """Get platform name."""
        return "Render"
    
    def validate(self) -> bool:
        """
        Validate Render deployment readiness.
        
        Returns:
            True if ready to deploy
        """
        self.logger.info("Validating Render deployment readiness...")
        
        checks = [
            (self._check_requirements, "requirements.txt"),
            (self._check_environment_vars, "Environment variables"),
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
        Prepare Render deployment.
        
        Returns:
            True if preparation successful
        """
        self.logger.info("Preparing Render deployment...")
        
        # Generate render.yaml if not exists
        if not file_exists(str(self.project_root / "render.yaml")):
            self.generate_config_file("render.yaml")
        
        return True
    
    def deploy(self) -> bool:
        """
        Deploy through the Render REST API.

        First deploy: creates a web service from the current git branch and
        prints its ID. Add that ID to your config as 'render_service_id' so
        later runs redeploy the same service instead of creating a new one.
        """
        api_key = self._require_credential("RENDER_API_KEY")
        if api_key is None:
            return False

        if not self._git_ready_for_render():
            return False

        service_id = self.config.get("render_service_id")
        if service_id:
            return self._trigger_deploy(api_key, str(service_id))
        return self._create_service(api_key)

    def _git_ready_for_render(self) -> bool:
        """Render builds from the git remote, so local-only changes would not ship."""
        status = self._run_step(["git", "status", "--porcelain"])
        if status is None:
            self.logger.error("Render needs a git repository. Run 'git init' and push to GitHub or GitLab.")
            return False
        if status.strip():
            self.logger.error("Uncommitted changes would not be deployed. Commit them and push first.")
            return False
        if self.dry_run:
            return True

        unpushed = self._run_step(["git", "rev-list", "--count", "@{u}..HEAD"])
        if unpushed is None or not unpushed.strip().isdigit():
            self.logger.error("The current branch has no upstream. Run 'git push -u origin <branch>' first.")
            return False
        if int(unpushed) > 0:
            self.logger.error(f"{unpushed.strip()} commit(s) are not pushed. Push them before deploying.")
            return False
        return True

    def _create_service(self, api_key: str) -> bool:
        """Create a new Render web service from the current git branch."""
        owner_id = self._resolve_owner_id(api_key)
        if owner_id is None:
            return False

        repo_url = self._git_repo_url()
        branch = self._run_step(["git", "rev-parse", "--abbrev-ref", "HEAD"]) or "main"
        if repo_url is None:
            return False

        body = {
            "type": "web_service",
            "name": self._service_name(),
            "ownerId": owner_id,
            "repo": repo_url,
            "branch": branch.strip(),
            "autoDeploy": "yes",
            "serviceDetails": {
                "env": "python",
                "region": str(self.config.get("render_region", "oregon")),
                "plan": str(self.config.get("render_plan", "free")),
                "envSpecificDetails": {
                    "buildCommand": "pip install -r requirements.txt",
                    "startCommand": str(self.config.get("start_command", "python app.py")),
                },
            },
        }

        if self.dry_run:
            self.logger.info(f"[dry-run] would create a Render web service: {body['name']} from {repo_url}")
            return True

        data = self._api("POST", "/services", api_key, body)
        if data is None:
            return False
        service = data.get("service", data)
        new_id = service.get("id")
        if not new_id:
            self.logger.error("Render did not return a service ID.")
            return False

        self.deployed_url = (service.get("serviceDetails") or {}).get("url")
        self.logger.info(f"Created Render service {new_id}.")
        self.logger.info(
            f"Add 'render_service_id: {new_id}' to your deployment config so future "
            "deploys update this service instead of creating a new one."
        )
        return True

    def _trigger_deploy(self, api_key: str, service_id: str) -> bool:
        """Start a new deploy of an existing Render service."""
        if self._api("POST", f"/services/{service_id}/deploys", api_key, {}) is None:
            return False

        service = self._api("GET", f"/services/{service_id}", api_key) or {}
        self.deployed_url = (service.get("serviceDetails") or {}).get("url")
        self.logger.info(f"Triggered a Render deploy for service {service_id}.")
        return True

    def _resolve_owner_id(self, api_key: str) -> Optional[str]:
        """Use RENDER_OWNER_ID if set, otherwise the only owner on the account."""
        owner_id = os.environ.get("RENDER_OWNER_ID", "")
        if owner_id:
            return owner_id
        if self.dry_run:
            return "<owner-id>"

        data = self._api("GET", "/owners?limit=20", api_key)
        if data is None:
            return None
        items = data if isinstance(data, list) else []
        ids = [
            (item.get("owner") or item).get("id")
            for item in items
            if isinstance(item, dict)
        ]
        found = [str(i) for i in ids if i]
        if len(found) == 1:
            return found[0]
        self.logger.error(
            "Could not pick a Render owner automatically. Set RENDER_OWNER_ID to one of: "
            + (", ".join(found) or "(none found)")
        )
        return None

    def _git_repo_url(self) -> Optional[str]:
        """Return the origin remote as an https URL, which Render requires."""
        remote = self._run_step(["git", "remote", "get-url", "origin"])
        if remote is None:
            self.logger.error("No 'origin' git remote found. Push the project to GitHub or GitLab first.")
            return None
        remote = remote.strip()
        if not remote:
            if self.dry_run:
                return "https://github.com/<owner>/<repo>"
            self.logger.error("The 'origin' git remote has no URL. Push the project to GitHub or GitLab first.")
            return None
        # Convert git@github.com:owner/repo.git into https://github.com/owner/repo
        if remote.startswith("git@"):
            host, _, path = remote[4:].partition(":")
            remote = f"https://{host}/{path}"
        return remote[:-4] if remote.endswith(".git") else remote

    def _service_name(self) -> str:
        """Render service names allow lowercase letters, digits and hyphens."""
        raw = str(self.config.get("app_name", self.project_root.resolve().name))
        return re.sub(r"[^a-z0-9-]+", "-", raw.lower()).strip("-") or "app"

    def _api(
        self,
        method: str,
        path: str,
        api_key: str,
        body: Optional[Dict[str, Any]] = None,
    ) -> Optional[Any]:
        """
        Call the Render REST API. Returns the parsed JSON, {} for empty
        responses, or None on error. Never retries: creating a service is not
        safe to repeat.
        """
        url = RENDER_API_BASE + path
        if self.dry_run:
            self.logger.info(f"[dry-run] would call {method} {url}")
            return {}
        try:
            response = requests.request(
                method,
                url,
                headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"},
                json=body,
                timeout=REQUEST_TIMEOUT,
            )
        except requests.RequestException as e:
            self.logger.error(f"Render API request failed: {self._redact(str(e), [api_key])}")
            return None

        if response.status_code >= 400:
            detail = self._redact(response.text[:500], [api_key])
            self.logger.error(f"Render API returned HTTP {response.status_code} for {method} {path}: {detail}")
            return None
        if not response.content:
            return {}
        try:
            return response.json()
        except ValueError:
            return {}
    
    def get_config_template(self) -> Dict[str, Any]:
        """
        Get Render configuration template.
        
        Returns:
            Configuration template
        """
        return {
            "services": [
                {
                    "type": "web",
                    "name": self.config.get("app_name", "my-app"),
                    "env": "python",
                    "plan": "free",
                    "buildCommand": "pip install -r requirements.txt",
                    "startCommand": "python app.py",
                }
            ]
        }
    
    def _check_render_config(self) -> bool:
        """Check if render.yaml exists."""
        return file_exists(str(self.project_root / "render.yaml"))

    def _check_requirements(self) -> bool:
        """Render's Python build installs dependencies from requirements.txt."""
        return file_exists(str(self.project_root / "requirements.txt"))
    
    def _check_environment_vars(self) -> bool:
        """Environment variables must be set in the Render dashboard; they are not uploaded from .env."""
        return True

    def rollback(self, deployment_state: Dict[str, Any]) -> bool:
        """Redeploy restored snapshot for Render deployments."""
        self.logger.info("Triggering Render redeployment of restored snapshot...")
        self.logger.info(
            "Push the restored code or click 'Manual Deploy' inside Render dashboard."
        )
        return super().rollback(deployment_state)
