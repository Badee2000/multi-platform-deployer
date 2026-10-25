"""Smoke tests for the CLI help output, run in a subprocess (no deployment actions)."""

import subprocess
import sys


def _run_cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "multi_platform_deployer.cli", *args],
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_help_exits_zero_and_lists_commands():
    result = _run_cli("--help")

    assert result.returncode == 0, result.stderr
    assert "USAGE" in result.stdout
    assert "multi-platform-deployer <command>" in result.stdout
    for command in ("setup", "check", "run", "info", "health", "rollback"):
        assert command in result.stdout


def test_no_arguments_shows_help_and_exits_zero():
    result = _run_cli()

    assert result.returncode == 0, result.stderr
    assert "COMMANDS" in result.stdout
