"""System-wide deployment readiness checks.

This module hosts `SystemChecker`, a framework-agnostic set of safety nets that
catch critical deployment issues before any platform-specific logic runs. The
checks focus on fundamentals every production app should satisfy: locked Python
runtime, pinned dependencies, hardened environment files, a deployment config,
and a clean git state.
"""

from __future__ import annotations

import subprocess
from typing import List, Tuple

from .base import BaseChecker, CheckResult


class SystemChecker(BaseChecker):
    """Run mandatory sanity checks that apply to every project."""

    _ENV_PLACEHOLDER_TOKENS = {
        "changeme",
        "replace_me",
        "your-secret",
        "default",
        "todo",
        "placeholder",
    }

    def check_all(self) -> Tuple[bool, List[CheckResult]]:
        """Execute all system-level checks and aggregate the results."""

        self.results = [
            self.check_python_runtime_manifest(),
            self.check_dependency_pinning(),
            self.check_deployment_config_present(),
            self.check_env_secret_hardening(),
            self.check_git_status_clean(),
        ]
        all_passed = all(result.passed for result in self.results)
        return all_passed, self.results

    # ------------------------------------------------------------------
    # Individual checks
    # ------------------------------------------------------------------

    def check_python_runtime_manifest(self) -> CheckResult:
        """Ensure the project declares the Python runtime somewhere."""

        root = self.project_root
        runtime_file = root / "runtime.txt"
        pyenv_file = root / ".python-version"
        pyproject_file = root / "pyproject.toml"
        pipfile = root / "Pipfile"

        if runtime_file.exists():
            content = runtime_file.read_text(encoding="utf-8").strip()
            return CheckResult(
                name="Python runtime",
                passed=bool(content),
                message=f"runtime.txt -> {content or 'empty'}",
                category="system",
                severity="high",
            )

        if pyenv_file.exists():
            version = pyenv_file.read_text(encoding="utf-8").strip()
            if version:
                return CheckResult(
                    name="Python runtime",
                    passed=True,
                    message=f".python-version -> {version}",
                    category="system",
                    severity="high",
                )

        if pyproject_file.exists():
            content = pyproject_file.read_text(encoding="utf-8")
            if "requires-python" in content or "python =" in content or "python=" in content:
                return CheckResult(
                    name="Python runtime",
                    passed=True,
                    message="pyproject.toml declares Python requirements",
                    category="system",
                    severity="high",
                )

        if pipfile.exists():
            content = pipfile.read_text(encoding="utf-8")
            if "python_version" in content:
                return CheckResult(
                    name="Python runtime",
                    passed=True,
                    message="Pipfile pins python_version",
                    category="system",
                    severity="high",
                )

        return CheckResult(
            name="Python runtime",
            passed=True,
            message=(
                "No explicit runtime pin detected; interpreter version will come from "
                "your deployment environment"
            ),
            category="system",
            severity="low",
        )

    def check_dependency_pinning(self) -> CheckResult:
        """Verify most dependencies in requirements.txt are version constrained."""

        requirements = self.project_root / "requirements.txt"
        if not requirements.exists():
            return CheckResult(
                name="Dependency pinning",
                passed=False,
                message="requirements.txt is missing",
                category="system",
                severity="high",
            )

        pinned = 0
        total = 0
        for line in requirements.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            total += 1
            if any(op in stripped for op in ("==", ">=", "<=", "~=", "===")):
                pinned += 1

        if total == 0:
            return CheckResult(
                name="Dependency pinning",
                passed=False,
                message="requirements.txt is empty",
                category="system",
                severity="medium",
            )

        ratio = pinned / total
        if ratio >= 0.6:
            return CheckResult(
                name="Dependency pinning",
                passed=True,
                message=f"{pinned}/{total} dependencies pinned",
                category="system",
                severity="medium",
            )

        return CheckResult(
            name="Dependency pinning",
            passed=False,
            message=f"Only {pinned}/{total} dependencies pinned",
            category="system",
            severity="medium",
        )

    def check_deployment_config_present(self) -> CheckResult:
        """Ensure at least one deployment config file exists."""

        candidates = (
            "deployment.yaml",
            "deployment.yml",
            "deployment.json",
            "render.yaml",
            "railway.json",
            "vercel.json",
        )

        for file_name in candidates:
            if (self.project_root / file_name).exists():
                return CheckResult(
                    name="Deployment config",
                    passed=True,
                    message=f"Found {file_name}",
                    category="system",
                    severity="high",
                )

        return CheckResult(
            name="Deployment config",
            passed=False,
            message="No deployment config (deployment.* / render.yaml / railway.json / vercel.json)",
            category="system",
            severity="high",
        )

    def check_env_secret_hardening(self) -> CheckResult:
        """Validate .env handling and ensure secrets are not placeholders."""

        env_file = self.project_root / ".env"
        example_file = self.project_root / ".env.example"

        if not env_file.exists() and not example_file.exists():
            return CheckResult(
                name="Environment variables",
                passed=False,
                message="Provide .env or .env.example with production secrets",
                category="system",
                severity="high",
            )

        if not env_file.exists():
            return CheckResult(
                name="Environment variables",
                passed=True,
                message="Only template .env.example present - remember to supply real secrets",
                category="system",
                severity="medium",
            )

        placeholders = []
        for line in env_file.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            _, value = stripped.split("=", 1)
            lowered = value.strip().strip('"\'').lower()
            if any(token in lowered for token in self._ENV_PLACEHOLDER_TOKENS):
                placeholders.append(stripped)

        if placeholders:
            sample = placeholders[0]
            return CheckResult(
                name="Environment variables",
                passed=False,
                message=f"Placeholder secret detected ({sample})",
                category="system",
                severity="high",
            )

        return CheckResult(
            name="Environment variables",
            passed=True,
            message=".env present with non-placeholder values",
            category="system",
            severity="high",
        )

    def check_git_status_clean(self) -> CheckResult:
        """Fail if the git working tree has uncommitted changes."""

        try:
            repo_check = subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=False,
            )
        except FileNotFoundError:
            return CheckResult(
                name="Git workspace",
                passed=True,
                message="Git CLI not installed; skipping cleanliness check",
                category="system",
                severity="low",
            )

        if repo_check.returncode != 0:
            return CheckResult(
                name="Git workspace",
                passed=True,
                message="Not a git repository",
                category="system",
                severity="low",
            )

        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=self.project_root,
            capture_output=True,
            text=True,
            check=False,
        )

        if status.returncode != 0:
            return CheckResult(
                name="Git workspace",
                passed=False,
                message=status.stderr.strip() or "Unable to inspect git status",
                category="system",
                severity="medium",
            )

        is_clean = status.stdout.strip() == ""
        return CheckResult(
            name="Git workspace",
            passed=is_clean,
            message="Working tree clean" if is_clean else "Uncommitted changes detected",
            category="system",
            severity="medium",
        )
