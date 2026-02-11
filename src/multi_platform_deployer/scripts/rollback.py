"""Deployment rollback management."""

from __future__ import annotations

import json
import os
import subprocess
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from ..utils.logger import get_logger


class RollbackManager:
    """Manage deployment rollbacks by snapshotting deployments."""

    EXCLUDED_DIRS = {".deployment", ".git", ".venv", "__pycache__"}

    def __init__(self, project_root: str = "."):
        """Initialize rollback manager with project root and logger."""
        self.project_root = Path(project_root)
        self.logger = get_logger("RollbackManager")
        self.deployment_history: List[dict] = []
    
    def create_checkpoint(self, platform: str, metadata: Optional[dict] = None) -> Optional[dict]:
        """Create a rollback checkpoint for a deployment."""
        deployment_id = self._generate_deployment_id(platform)
        now = datetime.now(UTC)
        state: Dict[str, Any] = {
            "id": deployment_id,
            "platform": platform.lower(),
            "timestamp": now.isoformat(),
            "git_commit": self._get_current_git_commit(),
        }
        if metadata:
            state.update(metadata)

        if self.save_deployment_state(deployment_id, state):
            self.clean_old_deployments()
            return state
        return None

    def save_deployment_state(self, deployment_id: str, state: dict) -> bool:
        """Persist the deployment metadata and snapshot for rollback."""
        self.logger.info(f"Saving deployment state: {deployment_id}")

        try:
            state_file = self.project_root / ".deployment" / f"{deployment_id}.json"
            state_file.parent.mkdir(parents=True, exist_ok=True)

            # Store snapshot of current project for file-level rollback
            artifact_path = self._create_project_snapshot(deployment_id)
            if artifact_path:
                state["artifact_path"] = artifact_path

            payload = self._make_json_safe(state)

            with open(state_file, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)

            self.logger.info(f"Deployment state saved to {state_file}")
            return True
        except Exception as e:
            self.logger.error(f"Error saving deployment state: {e}")
            return False
    
    def get_previous_deployment(self) -> Optional[dict]:
        """Return the most recent deployment metadata if it exists."""
        deployment_dir = self.project_root / ".deployment"

        if not deployment_dir.exists():
            self.logger.warning("No deployment history found")
            return None

        try:
            files = sorted(
                deployment_dir.glob("*.json"),
                key=lambda x: x.stat().st_mtime,
                reverse=True,
            )

            if files:
                with open(files[0], "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            self.logger.warning(f"Error reading deployment history: {e}")

        return None
    
    def rollback_to_previous(
        self,
        deploy_callback: Optional[Callable[[dict], bool]] = None,
    ) -> bool:
        """Restore previous snapshot and optionally redeploy via callback."""
        self.logger.warning("Initiating rollback to previous deployment...")

        previous = self.get_previous_deployment()
        if not previous:
            self.logger.error("No previous deployment found to rollback to")
            return False

        try:
            if not self._restore_snapshot(previous):
                return False

            if deploy_callback:
                self.logger.info("Triggering platform-specific rollback callback...")
                if not deploy_callback(previous):
                    self.logger.error("Rollback callback reported failure")
                    return False

            self.logger.info("Rollback completed")
            return True
        except Exception as e:
            self.logger.error(f"Rollback failed: {e}")
            return False
    
    def clean_old_deployments(self, keep_count: int = 5) -> None:
        """
        Clean up old deployment records.
        
        Args:
            keep_count: Number of recent deployments to keep
        """
        deployment_dir = self.project_root / ".deployment"
        
        if not deployment_dir.exists():
            return
        
        try:
            files = sorted(
                deployment_dir.glob("*.json"),
                key=lambda x: x.stat().st_mtime,
                reverse=True,
            )

            files_to_keep = {file.stem for file in files[:keep_count]}

            for file in files[keep_count:]:
                file.unlink(missing_ok=True)
                self.logger.debug(f"Removed old deployment record: {file.name}")

            artifact_dir = deployment_dir / "artifacts"
            if artifact_dir.exists():
                for artifact in artifact_dir.glob("*.zip"):
                    if artifact.stem not in files_to_keep:
                        artifact.unlink(missing_ok=True)
                        self.logger.debug(f"Removed old snapshot: {artifact.name}")

        except Exception as e:
            self.logger.warning(f"Error cleaning old deployments: {e}")

    # --- Internal helpers -------------------------------------------------

    def _generate_deployment_id(self, platform: str) -> str:
        timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        return f"{platform.lower()}_{timestamp}"

    def _get_current_git_commit(self) -> Optional[str]:
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception as exc:
            self.logger.debug(f"Unable to resolve git commit: {exc}")
        return None

    def _create_project_snapshot(self, deployment_id: str) -> Optional[str]:
        try:
            artifacts_dir = self.project_root / ".deployment" / "artifacts"
            artifacts_dir.mkdir(parents=True, exist_ok=True)
            snapshot_path = artifacts_dir / f"{deployment_id}.zip"

            with zipfile.ZipFile(snapshot_path, "w", zipfile.ZIP_DEFLATED) as archive:
                for root, dirs, files in os.walk(self.project_root):
                    relative_root = Path(root).relative_to(self.project_root)

                    dirs[:] = [d for d in dirs if d not in self.EXCLUDED_DIRS]

                    if any(part in self.EXCLUDED_DIRS for part in relative_root.parts):
                        continue

                    for file_name in files:
                        if file_name.endswith((".pyc", ".pyo")):
                            continue
                        source_path = Path(root) / file_name
                        relative_path = source_path.relative_to(self.project_root)
                        archive.write(source_path, relative_path.as_posix())

            return str(snapshot_path.relative_to(self.project_root))
        except Exception as exc:
            self.logger.error(f"Unable to create snapshot: {exc}")
            return None

    def _restore_snapshot(self, state: dict) -> bool:
        artifact_rel = state.get("artifact_path")
        if not artifact_rel:
            self.logger.error("No artifact snapshot available for rollback")
            return False

        artifact_path = self.project_root / artifact_rel
        if not artifact_path.exists():
            self.logger.error(f"Artifact missing: {artifact_path}")
            return False

        self.logger.info(f"Restoring files from snapshot {artifact_path}")
        try:
            with zipfile.ZipFile(artifact_path, "r") as archive:
                archive.extractall(self.project_root)
            return True
        except Exception as exc:
            self.logger.error(f"Failed to restore snapshot: {exc}")
            return False

    def _make_json_safe(self, value):
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value
        if isinstance(value, dict):
            return {str(k): self._make_json_safe(v) for k, v in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [self._make_json_safe(v) for v in value]
        return str(value)
