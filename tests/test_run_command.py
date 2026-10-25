"""Tests for run_command timeout handling, using a mocked subprocess."""

import subprocess

import pytest

from multi_platform_deployer.utils import helpers


def test_run_command_passes_timeout(monkeypatch):
    captured = {}

    def fake_run(command, **kwargs):
        captured.update(kwargs)
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(helpers.subprocess, "run", fake_run)
    helpers.run_command(["echo", "hi"], timeout=12.5, check=False)
    assert captured["timeout"] == 12.5


def test_run_command_defaults_to_no_timeout(monkeypatch):
    captured = {}

    def fake_run(command, **kwargs):
        captured.update(kwargs)
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(helpers.subprocess, "run", fake_run)
    helpers.run_command(["echo", "hi"], check=False)
    assert captured["timeout"] is None


def test_run_command_propagates_timeout_expired(monkeypatch):
    def slow(command, **kwargs):
        raise subprocess.TimeoutExpired(command, kwargs["timeout"])

    monkeypatch.setattr(helpers.subprocess, "run", slow)
    with pytest.raises(subprocess.TimeoutExpired):
        helpers.run_command(["sleep", "99"], timeout=1, check=False)
