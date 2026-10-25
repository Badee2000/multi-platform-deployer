"""Tests for run_command's environment handling."""

import subprocess

from multi_platform_deployer.utils import helpers


def _capture_env(monkeypatch):
    captured = {}

    def fake_run(command, cwd=None, env=None, **kwargs):
        captured["env"] = env
        return subprocess.CompletedProcess(args=command, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(helpers.subprocess, "run", fake_run)
    return captured


def test_run_command_adds_variables_to_inherited_environment(monkeypatch):
    monkeypatch.setenv("KEEP_ME", "1")
    captured = _capture_env(monkeypatch)

    helpers.run_command(["tool"], env={"ADDED": "2"}, check=False)

    assert captured["env"]["KEEP_ME"] == "1"
    assert captured["env"]["ADDED"] == "2"


def test_run_command_none_value_removes_inherited_variable(monkeypatch):
    monkeypatch.setenv("REMOVE_ME", "secret")
    captured = _capture_env(monkeypatch)

    helpers.run_command(["tool"], env={"REMOVE_ME": None}, check=False)

    assert "REMOVE_ME" not in captured["env"]


def test_run_command_removing_a_missing_variable_is_fine(monkeypatch):
    monkeypatch.delenv("NOT_SET", raising=False)
    captured = _capture_env(monkeypatch)

    helpers.run_command(["tool"], env={"NOT_SET": None}, check=False)

    assert "NOT_SET" not in captured["env"]
