"""Post-deployment health checks."""

import time
import urllib.error
import urllib.request
from typing import Any, Dict, Optional

from ..utils.logger import get_logger


class HealthChecker:
    """Check application health after deployment."""

    # Caps retry sleeps so a dead server fails in minutes, not ~17.
    MAX_BACKOFF_SECONDS = 30

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

        Probes the base URL. Any response below HTTP 500 counts as up, so an app
        without a /health route still passes. 5xx responses and connection
        failures are retried, then reported as down.

        Args:
            max_retries: Maximum number of connection attempts

        Returns:
            True if server is up
        """
        self.logger.info(f"Checking that {self.base_url} is up")

        for attempt in range(max_retries):
            try:
                response = urllib.request.urlopen(self.base_url, timeout=5)

                if response.status < 500:
                    self.logger.info("Server is responding")
                    return True
            except urllib.error.HTTPError as e:
                if e.code < 500:
                    self.logger.info(
                        f"Server is responding (HTTP {e.code} on the base URL)"
                    )
                    return True
            except Exception:
                pass
            if attempt < max_retries - 1:
                wait_time = min(2**attempt, self.MAX_BACKOFF_SECONDS)
                self.logger.info(
                    f"Server not responding yet (attempt {attempt + 1} of {max_retries}). "
                    f"Retrying in {wait_time}s"
                )
                time.sleep(wait_time)
            else:
                self.logger.error(f"Server not responding after {max_retries} attempts")

        return False

    def check_endpoints(self, endpoints: list) -> dict:
        """
        Request each endpoint and record its status.

        Args:
            endpoints: Paths to request, appended to the base URL.

        Returns:
            Maps each path to {"status", "ok"} and, on failure, "error".
        """
        self.logger.info(f"Checking {len(endpoints)} endpoint(s)")

        results = {}

        for endpoint in endpoints:
            try:
                url = f"{self.base_url}{endpoint}"
                response = urllib.request.urlopen(url, timeout=5)

                results[endpoint] = {
                    "status": response.status,
                    "ok": response.status == 200,
                }

                self.logger.info(f"{endpoint}: HTTP {response.status}")
            except urllib.error.HTTPError as e:
                results[endpoint] = {
                    "status": e.code,
                    "ok": False,
                    "error": f"HTTP {e.code}",
                }
                self.logger.warning(f"{endpoint}: HTTP {e.code}")
            except Exception as e:
                results[endpoint] = {
                    "status": None,
                    "ok": False,
                    "error": str(e),
                }
                self.logger.warning(f"{endpoint}: {e}")

        return results

    def check_database(self) -> Optional[bool]:
        """
        Database connectivity is not verified by this tool.

        A real check needs the project's database settings and credentials, which
        are not loaded here, so the result is unknown rather than a pass.

        Returns:
            None, meaning the database was not checked
        """
        self.logger.warning("Database connectivity is not checked by this tool.")
        return None

    def run_all_checks(
        self,
        endpoints: Optional[list] = None,
    ) -> Dict[str, Any]:
        """
        Run all health checks.

        Args:
            endpoints: Optional list of endpoints to check

        Returns:
            Dictionary of all check results
        """
        results: Dict[str, Any] = {}

        results["server_up"] = self.check_server_up()
        results["database"] = self.check_database()

        if endpoints:
            results["endpoints"] = self.check_endpoints(endpoints)

        return results

    def print_summary(self, results: dict) -> None:
        """Print one line per check: ok, FAIL, or not checked."""
        print("\nHealth check")
        for check_name, result in results.items():
            label = check_name.replace("_", " ").capitalize()
            if result is None:
                print(f"  [not checked] {label}")
            elif isinstance(result, bool):
                print(f"  [{'ok' if result else 'FAIL':<4}] {label}")
            elif isinstance(result, dict):
                for endpoint, status in result.items():
                    print(f"  [{'ok' if status.get('ok') else 'FAIL':<4}] {endpoint}")
        print()
