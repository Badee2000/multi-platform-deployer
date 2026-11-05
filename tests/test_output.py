"""Terminal output: plain text, one format, nothing printed by library code."""

import logging
import tempfile
from pathlib import Path

import pytest

from multi_platform_deployer import cli
from multi_platform_deployer.checkers import CheckResult, DjangoChecker, FlaskChecker
from multi_platform_deployer.deployers import RenderDeployer
from multi_platform_deployer.scripts.health_check import HealthChecker
from multi_platform_deployer.utils.logger import ConsoleFormatter


def _record(level: int, message: str) -> logging.LogRecord:
    return logging.LogRecord("x", level, __file__, 1, message, None, None)


class TestConsoleFormatter:
    def test_info_is_the_bare_message(self):
        assert (
            ConsoleFormatter().format(_record(logging.INFO, "Deployed")) == "Deployed"
        )

    @pytest.mark.parametrize(
        "level, prefix",
        [
            (logging.WARNING, "Warning: "),
            (logging.ERROR, "Error: "),
            (logging.CRITICAL, "Error: "),
            (logging.DEBUG, "Debug: "),
        ],
    )
    def test_problems_get_a_prefix(self, level, prefix):
        assert ConsoleFormatter().format(_record(level, "x")) == f"{prefix}x"


class TestCheckResult:
    def test_passed_and_failed_lines(self):
        assert (
            str(CheckResult("Secret key", True, "found")) == "[ok  ] Secret key: found"
        )
        assert (
            str(CheckResult("Secret key", False, "missing"))
            == "[FAIL] Secret key: missing"
        )

    def test_line_without_message(self):
        assert str(CheckResult("Static files", True)) == "[ok  ] Static files"


class TestPrintCheckResults:
    RESULTS = [CheckResult("A", True, "fine"), CheckResult("B", False, "broken")]

    def test_prints_every_result(self, capsys):
        cli.print_check_results(self.RESULTS)
        out = capsys.readouterr().out
        assert "[ok  ] A: fine" in out
        assert "[FAIL] B: broken" in out

    def test_failures_only(self, capsys):
        cli.print_check_results(self.RESULTS, failures_only=True)
        out = capsys.readouterr().out
        assert "[FAIL] B: broken" in out
        assert "A: fine" not in out


class TestLibraryCodeDoesNotPrint:
    def test_checkers_return_results_without_printing(self, capsys):
        with tempfile.TemporaryDirectory() as project:
            (Path(project) / "manage.py").write_text("")
            DjangoChecker(project).check_all()
            FlaskChecker(project).check_all()
        assert capsys.readouterr().out == ""


class TestPlainText:
    def test_help_is_ascii(self, capsys):
        cli.show_help()
        assert capsys.readouterr().out.isascii()

    def test_health_summary_is_ascii(self, capsys):
        HealthChecker().print_summary(
            {"server_up": True, "database": None, "endpoints": {"/": {"ok": False}}}
        )
        out = capsys.readouterr().out
        assert out.isascii()
        assert "[ok  ] Server up" in out
        assert "[FAIL] /" in out

    def test_help_names_the_real_command(self, capsys):
        cli.show_help()
        out = capsys.readouterr().out
        assert "py deploy.py" not in out
        assert "multi-platform-deployer run" in out


class TestSharedValidationLoop:
    def test_reports_each_check_and_fails_if_any_fails(self, tmp_path, caplog):
        deployer = RenderDeployer(str(tmp_path))
        checks = [(lambda: True, "good thing"), (lambda: False, "bad thing")]

        with caplog.at_level(logging.INFO):
            assert deployer._run_checks(checks) is False

        assert "Check passed: good thing" in caplog.text
        assert "Check failed: bad thing" in caplog.text

    def test_passes_when_every_check_passes(self, tmp_path):
        deployer = RenderDeployer(str(tmp_path))
        assert deployer._run_checks([(lambda: True, "x")]) is True

    def test_render_validate_needs_requirements_txt(self, tmp_path):
        deployer = RenderDeployer(str(tmp_path))
        assert deployer.validate() is False
        (tmp_path / "requirements.txt").write_text("flask\n")
        assert deployer.validate() is True
