"""FastAPI deployment readiness checker."""

from typing import Tuple, List
from .base import BaseChecker, CheckResult
from ..utils.helpers import read_file, file_exists


class FastAPIChecker(BaseChecker):
    """Check FastAPI application readiness for production deployment."""
    
    def check_all(self) -> Tuple[bool, List[CheckResult]]:
        """
        Run all FastAPI deployment readiness checks.
        
        Returns:
            Tuple of (all_passed, list_of_results)
        """
        self.logger.info("Checking FastAPI application readiness...")
        
        self.results = [
            self.check_requirements_file(),
            self.check_fastapi_app(),
            self.check_uvicorn_config(),
            self.check_environment_config(),
            self.check_cors_config(),
            self.check_middleware(),
            self.check_error_handlers(),
            self.check_database_config(),
        ]
        
        all_passed = all(r.passed for r in self.results)
        self.print_results()
        
        return all_passed, self.results
    
    def check_fastapi_app(self) -> CheckResult:
        """Check if FastAPI app is created."""
        possible_files = ["app.py", "main.py"]
        
        for file_name in possible_files:
            file_path = self.project_root / file_name
            if file_exists(str(file_path)):
                try:
                    content = read_file(str(file_path))
                    if "FastAPI" in content:
                        return CheckResult(
                            "FastAPI application",
                            True,
                            f"FastAPI app found in {file_name}"
                        )
                except Exception as e:
                    self.logger.warning(f"Error reading {file_name}: {e}")
        
        return CheckResult(
            "FastAPI application",
            False,
            "FastAPI application not found in app.py or main.py"
        )
    
    def check_uvicorn_config(self) -> CheckResult:
        """Check if Uvicorn is configured for production."""
        # Check if uvicorn is in requirements
        req_file = self.project_root / "requirements.txt"
        
        if req_file.exists():
            try:
                content = read_file(str(req_file))
                if "uvicorn" in content or "gunicorn" in content:
                    return CheckResult(
                        "Uvicorn/Gunicorn",
                        True,
                        "Production ASGI server found in requirements"
                    )
            except Exception as e:
                self.logger.warning(f"Error reading requirements.txt: {e}")
        
        return CheckResult(
            "Uvicorn/Gunicorn",
            False,
            "Production ASGI server (uvicorn or gunicorn) not in requirements"
        )
    
    def check_cors_config(self) -> CheckResult:
        """Check if CORS is properly configured."""
        possible_files = ["app.py", "main.py"]
        
        for file_name in possible_files:
            file_path = self.project_root / file_name
            if file_exists(str(file_path)):
                try:
                    content = read_file(str(file_path))
                    if "CORSMiddleware" in content or "cors" in content:
                        return CheckResult(
                            "CORS configuration",
                            True,
                            "CORS is configured"
                        )
                except Exception as e:
                    self.logger.warning(f"Error reading {file_name}: {e}")
        
        return CheckResult(
            "CORS configuration",
            False,
            "CORS should be configured for production APIs"
        )
    
    def check_middleware(self) -> CheckResult:
        """Check if security middleware is configured."""
        possible_files = ["app.py", "main.py"]
        
        for file_name in possible_files:
            file_path = self.project_root / file_name
            if file_exists(str(file_path)):
                try:
                    content = read_file(str(file_path))
                    middleware_checks = ["middleware", "@app.middleware"]
                    if any(check in content for check in middleware_checks):
                        return CheckResult(
                            "Middleware",
                            True,
                            "Middleware is configured"
                        )
                except Exception as e:
                    self.logger.warning(f"Error reading {file_name}: {e}")
        
        return CheckResult(
            "Middleware",
            False,
            "Security middleware is recommended for production"
        )
    
    def check_error_handlers(self) -> CheckResult:
        """Check if error handlers are configured."""
        possible_files = ["app.py", "main.py"]
        
        for file_name in possible_files:
            file_path = self.project_root / file_name
            if file_exists(str(file_path)):
                try:
                    content = read_file(str(file_path))
                    if "@app.exception_handler" in content:
                        return CheckResult(
                            "Error handlers",
                            True,
                            "Exception handlers are configured"
                        )
                except Exception as e:
                    self.logger.warning(f"Error reading {file_name}: {e}")
        
        return CheckResult(
            "Error handlers",
            False,
            "Exception handlers are recommended for production"
        )
    
    def check_database_config(self) -> CheckResult:
        """Check if database is configured."""
        possible_files = ["app.py", "main.py"]
        database_keywords = ["SQLAlchemy", "MongoDB", "database", "db"]
        
        for file_name in possible_files:
            file_path = self.project_root / file_name
            if file_exists(str(file_path)):
                try:
                    content = read_file(str(file_path))
                    if any(keyword in content for keyword in database_keywords):
                        return CheckResult(
                            "Database configuration",
                            True,
                            "Database appears to be configured"
                        )
                except Exception as e:
                    self.logger.warning(f"Error reading {file_name}: {e}")
        
        return CheckResult(
            "Database configuration",
            False,
            "Database configuration not found (may be optional)"
        )
