"""
Flask deployment readiness checker.

This module checks whether your Flask app is actually ready for production.
It validates things like:
- Do you have a requirements.txt?
- Is your Flask app properly created?
- Are secrets (SECRET_KEY) handled safely?
- Is debug mode turned off?
- Are error handlers configured?

The goal is to catch common problems BEFORE you deploy,
not after your app is live and broken.
"""

from typing import List, Tuple

from ..utils.helpers import file_exists, read_file
from .base import BaseChecker, CheckResult


class FlaskChecker(BaseChecker):
    """
    Check that a Flask application is ready for production.

    Checks that:
    - requirements.txt exists
    - the Flask app is created (app.py, wsgi.py or main.py)
    - a WSGI application exists
    - environment variables are configured
    - SECRET_KEY is set securely
    - a database is configured, if needed
    - debug mode is off
    - error handlers exist
    """

    def check_all(self) -> Tuple[bool, List[CheckResult]]:
        """
        Run all Flask readiness checks.

        Returns:
            (all_passed, results), with one result per check.
        """
        self.logger.debug("Checking Flask application readiness")

        self.results = [
            self.check_requirements_file(),
            self.check_flask_app(),
            self.check_wsgi_app(),
            self.check_environment_config(),
            self.check_secret_key(),
            self.check_database_config(),
            self.check_debug_mode(),
            self.check_error_handlers(),
        ]

        all_passed = all(r.passed for r in self.results)

        return all_passed, self.results

    def check_flask_app(self) -> CheckResult:
        """Check that app.py, wsgi.py or main.py exists."""
        for file_name in ["app.py", "wsgi.py", "main.py"]:
            if file_exists(str(self.project_root / file_name)):
                return CheckResult("Flask app entry point", True, f"{file_name} found")

        return CheckResult(
            "Flask app entry point", False, "app.py, wsgi.py, or main.py not found"
        )

    def check_wsgi_app(self) -> CheckResult:
        """Check if WSGI application is properly configured."""
        wsgi_file = self.project_root / "wsgi.py"

        if wsgi_file.exists():
            try:
                content = read_file(str(wsgi_file))
                if "application" in content or "app" in content:
                    return CheckResult(
                        "WSGI application", True, "WSGI application found in wsgi.py"
                    )
            except Exception as e:
                self.logger.warning(f"Error reading wsgi.py: {e}")

        return CheckResult(
            "WSGI application", False, "WSGI application not properly configured"
        )

    def check_secret_key(self) -> CheckResult:
        """Check if SECRET_KEY is configured."""
        app_file = self.project_root / "app.py"

        if app_file.exists():
            try:
                content = read_file(str(app_file))
                if "SECRET_KEY" in content or "secret_key" in content:
                    return CheckResult("Secret key", True, "SECRET_KEY is configured")
            except Exception as e:
                self.logger.warning(f"Error reading app.py: {e}")

        return CheckResult(
            "Secret key", False, "SECRET_KEY should be configured for security"
        )

    def check_database_config(self) -> CheckResult:
        """Check if database is configured."""
        # Look for SQLAlchemy or other database initialization
        app_file = self.project_root / "app.py"

        if app_file.exists():
            try:
                content = read_file(str(app_file))
                if "SQLAlchemy" in content or "DATABASE" in content or "db" in content:
                    return CheckResult(
                        "Database configuration",
                        True,
                        "Database appears to be configured",
                    )
            except Exception as e:
                self.logger.warning(f"Error reading app.py: {e}")

        return CheckResult(
            "Database configuration",
            True,
            "No database configuration found (OK for stateless apps; set DATABASE_URL if needed)",
        )

    def check_debug_mode(self) -> CheckResult:
        """Check if debug mode is not enabled in production code."""
        app_file = self.project_root / "app.py"

        if app_file.exists():
            try:
                content = read_file(str(app_file))
                # Check for dangerous debug=True in run
                if "debug=True" in content:
                    return CheckResult(
                        "Debug mode",
                        False,
                        "debug=True found in app.run(). Use environment variable instead.",
                    )
                else:
                    return CheckResult("Debug mode", True, "Debug mode not hardcoded")
            except Exception as e:
                self.logger.warning(f"Error reading app.py: {e}")

        return CheckResult(
            "Debug mode", False, "Could not verify debug mode configuration"
        )

    def check_error_handlers(self) -> CheckResult:
        """Check if error handlers are configured."""
        app_file = self.project_root / "app.py"

        if app_file.exists():
            try:
                content = read_file(str(app_file))
                if "@app.errorhandler" in content:
                    return CheckResult(
                        "Error handlers", True, "Error handlers are configured"
                    )
            except Exception as e:
                self.logger.warning(f"Error reading app.py: {e}")

        return CheckResult(
            "Error handlers", False, "Error handlers recommended for production"
        )
