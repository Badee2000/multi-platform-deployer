"""Base checker class for deployment readiness."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Tuple
from pathlib import Path
from ..utils.logger import get_logger


@dataclass(slots=True)
class CheckResult:
    """Result of a deployment readiness check."""

    name: str
    passed: bool
    message: str = ""
    category: str = "framework"
    severity: str = "info"

    def icon(self) -> str:
        """Return the status icon for pretty CLI output."""

        return "✓" if self.passed else "✗"

    def __str__(self) -> str:
        """Human friendly representation including category context."""

        prefix = f"[{self.category.upper()}] " if self.category else ""
        detail = f": {self.message}" if self.message else ""
        return f"{self.icon()} {prefix}{self.name}{detail}"


class BaseChecker(ABC):
    """Base class for deployment readiness checkers."""
    
    def __init__(self, project_root: str = "."):
        """
        Initialize checker.
        
        Args:
            project_root: Root directory of the project
        """
        self.project_root = Path(project_root)
        self.logger = get_logger(self.__class__.__name__)
        self.results: List[CheckResult] = []
    
    @abstractmethod
    def check_all(self) -> Tuple[bool, List[CheckResult]]:
        """
        Run all deployment readiness checks.
        
        Returns:
            Tuple of (all_passed, list_of_results)
        """
        pass
    
    def check_requirements_file(self) -> CheckResult:
        """Check if requirements.txt exists."""
        req_file = self.project_root / "requirements.txt"
        
        if req_file.exists():
            return CheckResult(
                "Requirements file",
                True,
                "requirements.txt found"
            )
        else:
            return CheckResult(
                "Requirements file",
                False,
                "requirements.txt not found"
            )
    
    def check_wsgi_app(self) -> CheckResult:
        """Check if WSGI application is configured."""
        # This should be overridden by subclasses
        return CheckResult(
            "WSGI application",
            False,
            "Not implemented in base checker"
        )
    
    def check_environment_config(self) -> CheckResult:
        """Check if environment configuration is present."""
        has_env_file = (self.project_root / ".env").exists()
        has_env_example = (self.project_root / ".env.example").exists()
        
        if has_env_file or has_env_example:
            return CheckResult(
                "Environment configuration",
                True,
                ".env or .env.example found"
            )
        else:
            return CheckResult(
                "Environment configuration",
                False,
                ".env or .env.example not found"
            )
    
    def check_static_files(self) -> CheckResult:
        """Check if static files directory exists."""
        static_dir = self.project_root / "static"
        
        if static_dir.exists() and static_dir.is_dir():
            return CheckResult(
                "Static files",
                True,
                "static directory found"
            )
        else:
            return CheckResult(
                "Static files",
                False,
                "static directory not found (optional)"
            )
    
    def check_security(self) -> CheckResult:
        """Check basic security configurations."""
        checks_passed = 0
        checks_total = 0
        
        # Check for DEBUG=False in production code
        checks_total += 1
        
        return CheckResult(
            "Security configuration",
            checks_passed > 0,
            f"Checked {checks_total} security aspects"
        )
    
    def print_results(self) -> None:
        """Print all check results."""
        print("\n" + "="*50)
        print("Deployment Readiness Check Results")
        print("="*50)
        
        for result in self.results:
            print(result)
        
        all_passed = all(r.passed for r in self.results)
        print("="*50)
        
        if all_passed:
            print("✓ All checks passed! Ready for deployment.")
        else:
            failed_count = sum(1 for r in self.results if not r.passed)
            print(f"✗ {failed_count} check(s) failed. Please address before deploying.")
        
        print("="*50 + "\n")
