"""Render platform deployer."""

import os
import re
import time
from typing import Dict, Any, List, Optional

import requests

from .base import BaseDeployer
from ..utils.helpers import file_exists, has_uncommitted_changes

RENDER_API_BASE = "https://api.render.com/v1"
REQUEST_TIMEOUT = 30  # seconds per API call
DEFAULT_WAIT_TIMEOUT = 900  # seconds to wait for a deploy to go live
POLL_INTERVAL = 10  # seconds between status checks
FAILED_DEPLOY_STATUSES = {
    "build_failed": "the build failed",
    "update_failed": "the deploy failed to start",
    "pre_deploy_failed": "the pre-deploy command failed",
    "canceled": "the deploy was canceled",
    "deactivated": "the deploy was replaced by a newer one",
}
DEV_SERVER_PATTERN = re.compile(r"^\s*python3?\s+\S+\.py\b|\bflask\s+run\b|\brunserver\b")


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

        wait_timeout = self._wait_timeout()
        if wait_timeout is None:
            return False

        service_id = self.config.get("render_service_id")
        if service_id:
            return self._trigger_deploy(api_key, str(service_id), wait_timeout)
        return self._create_service(api_key, wait_timeout)

    def _wait_timeout(self) -> Optional[int]:
        """Seconds to wait for a deploy to go live (0 = don't wait), or None if the config is invalid."""
        value = self.config.get("render_wait_timeout", DEFAULT_WAIT_TIMEOUT)
        if isinstance(value, bool) or not str(value).strip().isdigit():
            self.logger.error("'render_wait_timeout' must be a whole number of seconds (0 to skip waiting).")
            return None
        return int(str(value).strip())

    def _wait_for_deploy(self, api_key: str, service_id: str, deploy_id: Optional[str], timeout: int) -> bool:
        """
        Poll a deploy until it is live. Never retries the deploy itself.

        Returns False when the build fails, Render stops tracking it, the
        timeout passes, or the status cannot be read. The deploy may still be
        running on Render in the last two cases.
        """
        if self.dry_run or not deploy_id:
            return True
        if timeout == 0:
            self.logger.info("Not waiting for the build (render_wait_timeout is 0). Check the Render dashboard.")
            return True

        deadline = time.monotonic() + timeout
        last_status = None
        try:
            while True:
                data = self._api("GET", f"/services/{service_id}/deploys/{deploy_id}", api_key)
                if not isinstance(data, dict):
                    self.logger.error(
                        f"Could not read the status of deploy {deploy_id}. It may still be running; "
                        "check the Render dashboard."
                    )
                    return False
                status = str(data.get("status", "unknown"))
                if status != last_status:
                    self.logger.info(f"Deploy {deploy_id}: {status}")
                    last_status = status
                if status == "live":
                    return True
                if status in FAILED_DEPLOY_STATUSES:
                    self.logger.error(f"Deploy {deploy_id} did not go live: {FAILED_DEPLOY_STATUSES[status]}.")
                    return False
                if time.monotonic() + POLL_INTERVAL > deadline:
                    self.logger.error(
                        f"Deploy {deploy_id} was still '{status}' after {timeout} seconds. "
                        "It may still finish; check the Render dashboard."
                    )
                    return False
                time.sleep(POLL_INTERVAL)
        except KeyboardInterrupt:
            self.logger.error(f"Stopped waiting. Deploy {deploy_id} continues on Render.")
            return False

    def _git_ready_for_render(self) -> bool:
        """Render builds from the git remote, so local-only changes would not ship."""
        status = self._run_step(["git", "status", "--porcelain"])
        if status is None:
            self.logger.error("Render needs a git repository. Run 'git init' and push to GitHub or GitLab.")
            return False
        if has_uncommitted_changes(status):
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

    def _resolve_start_command(self) -> Optional[str]:
        """
        Return the configured start command, or None when a real deploy must stop.

        No single default fits Flask, Django and FastAPI, and a wrong guess only
        fails after the service already exists on Render, so it must be explicit.
        """
        command = str(self.config.get("start_command") or "").strip()
        if not command:
            message = (
                "No 'start_command' in your config. Render needs a production start command, for example: "
                "Flask 'gunicorn app:app', Django 'gunicorn <project>.wsgi', "
                "FastAPI 'uvicorn main:app --host 0.0.0.0 --port $PORT'. "
                "Add it to deployment.yaml and make sure the server is in requirements.txt."
            )
            if self.dry_run:
                self.logger.warning(f"[dry-run] {message}")
                return "<start_command required>"
            self.logger.error(message)
            return None

        if DEV_SERVER_PATTERN.search(command):
            self.logger.warning(
                f"'{command}' looks like a development server. Use gunicorn or uvicorn for production."
            )
        return command

    def _create_service(self, api_key: str, wait_timeout: int = DEFAULT_WAIT_TIMEOUT) -> bool:
        """Create a new Render web service from the current git branch."""
        start_command = self._resolve_start_command()
        if start_command is None:
            return False

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
            "autoDeployTrigger": "commit",
            "serviceDetails": {
                "runtime": "python",
                "region": str(self.config.get("render_region", "oregon")),
                "plan": str(self.config.get("render_plan", "free")),
                "envSpecificDetails": {
                    "buildCommand": "pip install -r requirements.txt",
                    "startCommand": start_command,
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
        return self._wait_for_deploy(api_key, str(new_id), data.get("deployId"), wait_timeout)

    def _trigger_deploy(self, api_key: str, service_id: str, wait_timeout: int = DEFAULT_WAIT_TIMEOUT) -> bool:
        """Start a new deploy of an existing Render service."""
        deploy = self._api("POST", f"/services/{service_id}/deploys", api_key, {})
        if deploy is None:
            return False

        service = self._api("GET", f"/services/{service_id}", api_key) or {}
        self.deployed_url = (service.get("serviceDetails") or {}).get("url")
        self.logger.info(f"Triggered a Render deploy for service {service_id}.")
        return self._wait_for_deploy(api_key, service_id, deploy.get("id"), wait_timeout)

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
                    "startCommand": self.config.get("start_command", "gunicorn app:app"),
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

    supports_live_rollback = True

    def rollback(self, deployment_state: Dict[str, Any]) -> bool:
        """Roll the live service back through Render's API. Never redeploys current code."""
        return self.rollback_live()

    def rollback_live(self) -> bool:
        """
        Roll the Render service back to its most recent earlier successful deploy.

        Uses Render's rollback API, which reuses the old build artifact, so no
        rebuild happens. Autodeploy may be switched off by Render as a result;
        the final log lines report its real state.
        """
        api_key = self._require_credential("RENDER_API_KEY")
        if api_key is None:
            return False

        service_id = self.config.get("render_service_id")
        if not service_id:
            self.logger.error(
                "Rollback needs 'render_service_id' in your deployment config "
                "(printed by the first deploy, also shown in the Render dashboard URL)."
            )
            return False

        list_path = f"/services/{service_id}/deploys?limit=20"
        if self.dry_run:
            self._api("GET", list_path, api_key)
            self._api("POST", f"/services/{service_id}/rollback", api_key, {"deployId": "<previous deploy id>"})
            return True

        items = self._api("GET", list_path, api_key)
        if items is None:
            return False

        target = self._pick_rollback_target(items if isinstance(items, list) else [])
        if target is None:
            self.logger.error(
                "No earlier successful deploy to roll back to. Either there is only one deploy, "
                "the live deploy is already a rollback, or Render no longer keeps the older build. "
                "Pick a deploy manually in the Render dashboard (service > Deploys > Rollback)."
            )
            return False

        message = str((target.get("commit") or {}).get("message", "")).strip().splitlines()
        self.logger.info(
            f"Rolling back to deploy {target['id']} "
            f"(created {target.get('createdAt', 'unknown')}, commit: {message[0][:60] if message else 'n/a'})."
        )
        if self._same_commit_as_live(items, target):
            self.logger.warning(
                "The deploy you are rolling back to has the same commit as the live one, so the running "
                "code will not change. Render may still switch auto-deploy off."
            )
        if self._api("POST", f"/services/{service_id}/rollback", api_key, {"deployId": target["id"]}) is None:
            return False

        self.logger.info("Render accepted the rollback. Watch the service's Events tab until it is live.")
        self._report_autodeploy_state(api_key, str(service_id))
        return True

    def _report_autodeploy_state(self, api_key: str, service_id: str) -> None:
        """
        Tell the user what Render actually did to autodeploy.

        Render's API docs say a rollback leaves autodeploy alone, but a live
        test showed it switched off, so read the real state instead of guessing.
        """
        service = self._api("GET", f"/services/{service_id}", api_key)
        state = None
        if isinstance(service, dict):
            state = service.get("autoDeployTrigger")
            if state is None:
                legacy = service.get("autoDeploy")
                state = {"yes": "commit", "no": "off"}.get(str(legacy)) if legacy else None

        if state == "off":
            self.logger.warning(
                "Autodeploy is now OFF for this service. New commits will not deploy until you "
                "turn it back on in the Render dashboard (Settings > Auto-Deploy)."
            )
        elif state:
            self.logger.warning(
                f"Autodeploy is still on ({state}). A new commit on the linked branch will deploy "
                "again and may undo this rollback. Turn it off in the Render dashboard if needed."
            )
        else:
            self.logger.warning(
                "Could not read the autodeploy setting. Check Settings > Auto-Deploy in the Render "
                "dashboard: a rollback can turn it off, and a later commit may undo the rollback if it is on."
            )

    @staticmethod
    def _same_commit_as_live(items: Any, target: Dict[str, Any]) -> bool:
        """True when the rollback target was built from the same commit as the live deploy."""
        deploys = [(item.get("deploy") or item) for item in items if isinstance(item, dict)] if isinstance(items, list) else []
        live = next((d for d in deploys if isinstance(d, dict) and d.get("status") == "live"), None)
        live_commit = ((live or {}).get("commit") or {}).get("id")
        target_commit = (target.get("commit") or {}).get("id")
        return bool(live_commit) and live_commit == target_commit

    @staticmethod
    def _pick_rollback_target(items: List[Any]) -> Optional[Dict[str, Any]]:
        """
        Choose the newest deactivated deploy that is older than the live one.

        Returns None when the live deploy was itself created by a rollback, so
        repeating the command cannot flip back and forth to the bad build.
        """
        deploys = [(item.get("deploy") or item) for item in items if isinstance(item, dict)]
        deploys = [d for d in deploys if isinstance(d, dict) and d.get("id")]
        deploys.sort(key=lambda d: str(d.get("createdAt", "")), reverse=True)

        live = next((d for d in deploys if d.get("status") == "live"), None)
        if live is not None and live.get("trigger") == "rollback":
            return None
        cutoff = str(live.get("createdAt", "")) if live else ""

        for deploy in deploys:
            if deploy.get("status") != "deactivated":
                continue
            if cutoff and str(deploy.get("createdAt", "")) >= cutoff:
                continue
            return deploy
        return None
