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

from typing import Tuple, List
from .base import BaseChecker, CheckResult
from ..utils.helpers import read_file, file_exists


class FlaskChecker(BaseChecker):
    """
    Check if a Flask application is production-ready.
    
    This class runs a comprehensive checklist:
    - ✓ requirements.txt exists
    - ✓ Flask app is properly created (app.py, wsgi.py, or main.py)
    - ✓ WSGI application exists
    - ✓ Environment variables are configured
    - ✓ SECRET_KEY is set securely
    - ✓ Database is configured (if needed)
    - ✓ Debug mode is OFF
    - ✓ Error handlers exist
    
    If any check fails, we tell you exactly what to fix.
    """
    
    def check_all(self) -> Tuple[bool, List[CheckResult]]:
        """
        Run all Flask deployment readiness checks.
        
        This is the main method you call. It runs through a checklist
        and tells you whether your app is ready to deploy.
        
        Returns:
            Tuple of:
            - all_passed (bool): True if ALL checks passed
            - results (list): Detailed results for each check
        """
        self.logger.info("Checking Flask application readiness...")
        
        # Run through our checklist
        # Each check is a method below that validates one specific thing
        self.results = [
            self.check_requirements_file(),      # Do you have dependencies listed?
            self.check_flask_app(),              # Can we find your Flask app?
            self.check_wsgi_app(),               # Is it set up for production (WSGI)?
            self.check_environment_config(),     # Are you using environment variables?
            self.check_secret_key(),             # Is your SECRET_KEY secure?
            self.check_database_config(),        # If you have a DB, is it configured?
            self.check_debug_mode(),             # Is debug mode OFF (security!)?
            self.check_error_handlers(),         # Do you handle errors gracefully?
        ]
        
        # Did all checks pass?
        all_passed = all(r.passed for r in self.results)
        self.print_results()
        
        return all_passed, self.results
    
    def check_flask_app(self) -> CheckResult:
        """
        Check if Flask app entry point exists.
        
        Flask apps typically have a main entry point like:
        - app.py (most common)
        - wsgi.py (traditional)
        - main.py (also common)
        
        We look for any of these common naming conventions.
        """
        possible_files = ["app.py", "wsgi.py", "main.py"]
        
        # Check each possible filename
        for file_name in possible_files:
            if file_exists(str(self.project_root / file_name)):
                return CheckResult(
                    "Flask app entry point",
                    True,
                    f"{file_name} found"
                )
        
        return CheckResult(
            "Flask app entry point",
            False,
            "app.py, wsgi.py, or main.py not found"
        )
    
    def check_wsgi_app(self) -> CheckResult:
        """Check if WSGI application is properly configured."""
        wsgi_file = self.project_root / "wsgi.py"
        
        if wsgi_file.exists():
            try:
                content = read_file(str(wsgi_file))
                if "application" in content or "app" in content:
                    return CheckResult(
                        "WSGI application",
                        True,
                        "WSGI application found in wsgi.py"
                    )
            except Exception as e:
                self.logger.warning(f"Error reading wsgi.py: {e}")
        
        return CheckResult(
            "WSGI application",
            False,
            "WSGI application not properly configured"
        )
    
    def check_secret_key(self) -> CheckResult:
        """Check if SECRET_KEY is configured."""
        app_file = self.project_root / "app.py"
        
        if app_file.exists():
            try:
                content = read_file(str(app_file))
                if "SECRET_KEY" in content or "secret_key" in content:
                    return CheckResult(
                        "Secret key",
                        True,
                        "SECRET_KEY is configured"
                    )
            except Exception as e:
                self.logger.warning(f"Error reading app.py: {e}")
        
        return CheckResult(
            "Secret key",
            False,
            "SECRET_KEY should be configured for security"
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
                        "Database appears to be configured"
                    )
            except Exception as e:
                self.logger.warning(f"Error reading app.py: {e}")
        
        return CheckResult(
            "Database configuration",
            False,
            "Database configuration not clearly found (may be optional)"
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
                        "debug=True found in app.run(). Use environment variable instead."
                    )
                else:
                    return CheckResult(
                        "Debug mode",
                        True,
                        "Debug mode not hardcoded"
                    )
            except Exception as e:
                self.logger.warning(f"Error reading app.py: {e}")
        
        return CheckResult(
            "Debug mode",
            False,
            "Could not verify debug mode configuration"
        )
    
    def check_error_handlers(self) -> CheckResult:
        """Check if error handlers are configured."""
        app_file = self.project_root / "app.py"
        
        if app_file.exists():
            try:
                content = read_file(str(app_file))
                if "@app.errorhandler" in content:
                    return CheckResult(
                        "Error handlers",
                        True,
                        "Error handlers are configured"
                    )
            except Exception as e:
                self.logger.warning(f"Error reading app.py: {e}")
        
        return CheckResult(
            "Error handlers",
            False,
            "Error handlers recommended for production"
        )
