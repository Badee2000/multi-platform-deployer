"""Tests for post-deployment health checks, using mocked HTTP only."""

import io
import socket
import urllib.error

import pytest

from multi_platform_deployer.scripts import health_check
from multi_platform_deployer.scripts.health_check import HealthChecker


class _Response:
    def __init__(self, status: int):
        self.status = status


@pytest.fixture
def checker(monkeypatch):
    monkeypatch.setattr(health_check.time, "sleep", lambda seconds: None)
    return HealthChecker("https://example.test")


def test_check_database_reports_unknown_not_pass(checker):
    assert checker.check_database() is None


def test_run_all_checks_does_not_mark_database_as_passed(checker, monkeypatch):
    monkeypatch.setattr(checker, "check_server_up", lambda max_retries=10: True)
    results = checker.run_all_checks()
    assert results["server_up"] is True
    assert results["database"] is None


def test_print_summary_shows_database_as_not_checked(checker, capsys):
    checker.print_summary({"server_up": True, "database": None})
    output = capsys.readouterr().out
    assert "NOT CHECKED: Database" in output
    assert "PASS: Database" not in output


def test_server_up_true_on_200(checker, monkeypatch):
    monkeypatch.setattr(urllib_request(), "urlopen", lambda url, timeout: _Response(200))
    assert checker.check_server_up(max_retries=3) is True


def test_server_up_false_after_retries_on_network_error(checker, monkeypatch):
    calls = []

    def refuse(url, timeout):
        calls.append(url)
        raise urllib.error.URLError("connection refused")

    monkeypatch.setattr(urllib_request(), "urlopen", refuse)
    assert checker.check_server_up(max_retries=3) is False
    assert len(calls) == 3
    assert all(url == "https://example.test" for url in calls)


def test_server_up_true_when_root_returns_404(checker, monkeypatch):
    def not_found(url, timeout):
        raise urllib.error.HTTPError(url, 404, "Not Found", {}, io.BytesIO(b""))

    monkeypatch.setattr(urllib_request(), "urlopen", not_found)
    assert checker.check_server_up(max_retries=3) is True


def test_server_up_false_on_timeout(checker, monkeypatch):
    def timeout(url, timeout):
        raise socket.timeout("timed out")

    monkeypatch.setattr(urllib_request(), "urlopen", timeout)
    assert checker.check_server_up(max_retries=2) is False


def test_server_up_false_on_persistent_500(checker, monkeypatch):
    def server_error(url, timeout):
        raise urllib.error.HTTPError(url, 500, "boom", {}, io.BytesIO(b""))

    monkeypatch.setattr(urllib_request(), "urlopen", server_error)
    assert checker.check_server_up(max_retries=2) is False


def test_server_up_backoff_is_capped(checker, monkeypatch):
    sleeps = []
    monkeypatch.setattr(health_check.time, "sleep", sleeps.append)

    def refuse(url, timeout):
        raise urllib.error.URLError("connection refused")

    monkeypatch.setattr(urllib_request(), "urlopen", refuse)
    assert checker.check_server_up(max_retries=10) is False
    assert len(sleeps) == 9
    assert max(sleeps) == HealthChecker.MAX_BACKOFF_SECONDS
    assert sum(sleeps) <= 200


def test_endpoint_http_error_keeps_status_code(checker, monkeypatch):
    def not_found(url, timeout):
        raise urllib.error.HTTPError(url, 404, "Not Found", {}, io.BytesIO(b""))

    monkeypatch.setattr(urllib_request(), "urlopen", not_found)
    result = checker.check_endpoints(["/missing"])["/missing"]
    assert result["status"] == 404
    assert result["ok"] is False


def test_endpoint_success_reports_ok(checker, monkeypatch):
    monkeypatch.setattr(urllib_request(), "urlopen", lambda url, timeout: _Response(200))
    result = checker.check_endpoints(["/"])["/"]
    assert result == {"status": 200, "ok": True}


def test_endpoint_network_failure_has_no_status(checker, monkeypatch):
    def unreachable(url, timeout):
        raise urllib.error.URLError("no route to host")

    monkeypatch.setattr(urllib_request(), "urlopen", unreachable)
    result = checker.check_endpoints(["/"])["/"]
    assert result["status"] is None
    assert result["ok"] is False
    assert "no route to host" in result["error"]


def urllib_request():
    import urllib.request

    return urllib.request
