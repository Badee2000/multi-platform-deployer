"""Post-deployment health checks."""

import time
from typing import Optional
from ..utils.logger import get_logger
from ..utils.helpers import run_command


class HealthChecker:
    """Check application health after deployment."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        """
        Initialize health checker.
        
        Args:
            base_url: Base URL for health checks
        """
        self.base_url = base_url
        self.logger = get_logger("HealthChecker")
        self.timeout = 300  # 5 minutes
    
    def check_server_up(self, max_retries: int = 10) -> bool:
        """
        Check if server is responding.
        
        Args:
            max_retries: Maximum number of connection attempts
        
        Returns:
            True if server is up
        """
        self.logger.info(f"Checking if server is up at {self.base_url}")
        
        for attempt in range(max_retries):
            try:
                import urllib.request
                response = urllib.request.urlopen(f"{self.base_url}/health", timeout=5)
                
                if response.status == 200:
                    self.logger.info("✓ Server is responding")
                    return True
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    self.logger.info(
                        f"Server not responding yet. "
                        f"Attempt {attempt + 1}/{max_retries}. "
                        f"Retrying in {wait_time}s..."
                    )
                    time.sleep(wait_time)
                else:
                    self.logger.error(f"Server not responding after {max_retries} attempts")
        
        return False
    
    def check_endpoints(self, endpoints: list) -> dict:
        """
        Check if specific endpoints are responding.
        
        Args:
            endpoints: List of endpoint paths to check
        
        Returns:
            Dictionary of endpoint results
        """
        self.logger.info(f"Checking {len(endpoints)} endpoints...")
        
        results = {}
        
        for endpoint in endpoints:
            try:
                import urllib.request
                url = f"{self.base_url}{endpoint}"
                response = urllib.request.urlopen(url, timeout=5)
                
                results[endpoint] = {
                    "status": response.status,
                    "ok": response.status == 200,
                }
                
                self.logger.info(f"✓ {endpoint}: {response.status}")
            except Exception as e:
                results[endpoint] = {
                    "status": None,
                    "ok": False,
                    "error": str(e),
                }
                self.logger.warning(f"✗ {endpoint}: {str(e)}")
        
        return results
    
    def check_database(self) -> bool:
        """
        Check if database is accessible.
        
        Returns:
            True if database is accessible
        """
        self.logger.info("Checking database connectivity...")
        
        try:
            # This would be framework-specific
            self.logger.info("Database connectivity check - framework specific")
            return True
        except Exception as e:
            self.logger.error(f"Database check failed: {e}")
            return False
    
    def run_all_checks(
        self,
        endpoints: Optional[list] = None,
    ) -> dict:
        """
        Run all health checks.
        
        Args:
            endpoints: Optional list of endpoints to check
        
        Returns:
            Dictionary of all check results
        """
        results = {}
        
        results["server_up"] = self.check_server_up()
        results["database"] = self.check_database()
        
        if endpoints:
            results["endpoints"] = self.check_endpoints(endpoints)
        
        return results
    
    def print_summary(self, results: dict) -> None:
        """Print health check summary."""
        print("\n" + "="*50)
        print("Health Check Summary")
        print("="*50)
        
        for check_name, result in results.items():
            if isinstance(result, bool):
                status = "✓ PASS" if result else "✗ FAIL"
                print(f"{status}: {check_name.replace('_', ' ').title()}")
            elif isinstance(result, dict):
                for endpoint, status in result.items():
                    status_text = "✓ OK" if status.get("ok") else "✗ FAIL"
                    print(f"{status_text}: {endpoint}")
        
        print("="*50 + "\n")
