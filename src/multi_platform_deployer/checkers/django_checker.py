"""Django deployment readiness checker."""

from typing import Tuple, List
from .base import BaseChecker, CheckResult
from ..utils.helpers import read_file, file_exists


class DjangoChecker(BaseChecker):
    """Check Django application readiness for production deployment."""
    
    def check_all(self) -> Tuple[bool, List[CheckResult]]:
        """
        Run all Django deployment readiness checks.
        
        Returns:
            Tuple of (all_passed, list_of_results)
        """
        self.logger.info("Checking Django application readiness...")
        
        self.results = [
            self.check_requirements_file(),
            self.check_manage_py(),
            self.check_settings_security(),
            self.check_environment_config(),
            self.check_static_files_config(),
            self.check_database_config(),
            self.check_secret_key(),
            self.check_allowed_hosts(),
            self.check_debug_mode(),
        ]
        
        all_passed = all(r.passed for r in self.results)
        self.print_results()
        
        return all_passed, self.results
    
    def check_manage_py(self) -> CheckResult:
        """Check if manage.py exists."""
        if file_exists(str(self.project_root / "manage.py")):
            return CheckResult(
                "Django manage.py",
                True,
                "manage.py found"
            )
        else:
            return CheckResult(
                "Django manage.py",
                False,
                "manage.py not found"
            )
    
    def check_settings_security(self) -> CheckResult:
        """Check if settings.py has production security settings."""
        settings_file = self.project_root / "config" / "settings.py"
        
        if not settings_file.exists():
            settings_file = self.project_root / "settings.py"
        
        if settings_file.exists():
            try:
                content = read_file(str(settings_file))
                # Check for security-related settings
                security_checks = [
                    "SECURE_SSL_REDIRECT",
                    "SESSION_COOKIE_SECURE",
                    "CSRF_COOKIE_SECURE",
                ]
                
                found_count = sum(1 for check in security_checks if check in content)
                
                if found_count >= 2:
                    return CheckResult(
                        "Settings security",
                        True,
                        f"Found {found_count} security settings"
                    )
            except Exception as e:
                self.logger.warning(f"Error reading settings.py: {e}")
        
        return CheckResult(
            "Settings security",
            False,
            "Production security settings not fully configured"
        )
    
    def check_static_files_config(self) -> CheckResult:
        """Check if static files are properly configured."""
        settings_file = self.project_root / "config" / "settings.py"
        
        if not settings_file.exists():
            settings_file = self.project_root / "settings.py"
        
        if settings_file.exists():
            try:
                content = read_file(str(settings_file))
                if "STATIC_ROOT" in content or "STATICFILES_STORAGE" in content:
                    return CheckResult(
                        "Static files",
                        True,
                        "Static files are configured"
                    )
            except Exception as e:
                self.logger.warning(f"Error reading settings.py: {e}")
        
        return CheckResult(
            "Static files",
            False,
            "Static files configuration not found"
        )
    
    def check_database_config(self) -> CheckResult:
        """Check if database is properly configured."""
        settings_file = self.project_root / "config" / "settings.py"
        
        if not settings_file.exists():
            settings_file = self.project_root / "settings.py"
        
        if settings_file.exists():
            try:
                content = read_file(str(settings_file))
                if "DATABASES" in content:
                    return CheckResult(
                        "Database configuration",
                        True,
                        "Database is configured"
                    )
            except Exception as e:
                self.logger.warning(f"Error reading settings.py: {e}")
        
        return CheckResult(
            "Database configuration",
            False,
            "Database configuration not found"
        )
    
    def check_secret_key(self) -> CheckResult:
        """Check if SECRET_KEY is properly configured."""
        settings_file = self.project_root / "config" / "settings.py"
        
        if not settings_file.exists():
            settings_file = self.project_root / "settings.py"
        
        if settings_file.exists():
            try:
                content = read_file(str(settings_file))
                if "SECRET_KEY" in content:
                    # Check if it's not hardcoded
                    if 'os.environ' in content or 'SECRET_KEY' in content:
                        return CheckResult(
                            "Secret key",
                            True,
                            "SECRET_KEY is configured"
                        )
            except Exception as e:
                self.logger.warning(f"Error reading settings.py: {e}")
        
        return CheckResult(
            "Secret key",
            False,
            "SECRET_KEY configuration not found"
        )
    
    def check_allowed_hosts(self) -> CheckResult:
        """Check if ALLOWED_HOSTS is configured."""
        settings_file = self.project_root / "config" / "settings.py"
        
        if not settings_file.exists():
            settings_file = self.project_root / "settings.py"
        
        if settings_file.exists():
            try:
                content = read_file(str(settings_file))
                if "ALLOWED_HOSTS" in content:
                    return CheckResult(
                        "ALLOWED_HOSTS",
                        True,
                        "ALLOWED_HOSTS is configured"
                    )
            except Exception as e:
                self.logger.warning(f"Error reading settings.py: {e}")
        
        return CheckResult(
            "ALLOWED_HOSTS",
            False,
            "ALLOWED_HOSTS not configured (required for production)"
        )
    
    def check_debug_mode(self) -> CheckResult:
        """Check if DEBUG is set to False in production."""
        settings_file = self.project_root / "config" / "settings.py"
        
        if not settings_file.exists():
            settings_file = self.project_root / "settings.py"
        
        if settings_file.exists():
            try:
                content = read_file(str(settings_file))
                if "DEBUG = False" in content or ("DEBUG" in content and "os.environ" in content):
                    return CheckResult(
                        "Debug mode",
                        True,
                        "DEBUG is properly configured"
                    )
            except Exception as e:
                self.logger.warning(f"Error reading settings.py: {e}")
        
        return CheckResult(
            "Debug mode",
            False,
            "DEBUG mode not properly configured for production"
        )
