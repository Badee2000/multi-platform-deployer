"""Tests that the setup wizard keeps secret values out of deployment config."""

import os

import pytest
import yaml

from multi_platform_deployer import cli


def _script_input(monkeypatch, answers):
    """Feed scripted answers to every input() call in the wizard."""
    iterator = iter(answers)
    monkeypatch.setattr("builtins.input", lambda prompt="": next(iterator))


def test_wizard_keeps_secret_values_out_of_config(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _script_input(
        monkeypatch,
        [
            "1",  # platform: Render
            "demo-app",  # app name
            "yes",  # add environment variables
            "SECRET_KEY=s3cret-value-123",
            "DATABASE_URL=postgres://user:pw@host/db",
            "",  # finish env entry
            "no",  # use YAML, not JSON
        ],
    )

    cli.setup_wizard()

    config_text = (tmp_path / "deployment.yaml").read_text(encoding="utf-8")
    assert "s3cret-value-123" not in config_text
    assert "pw@host" not in config_text
    config = yaml.safe_load(config_text)
    assert "env" not in config
    assert config["app_name"] == "demo-app"

    env_text = (tmp_path / ".env").read_text(encoding="utf-8")
    assert "SECRET_KEY=s3cret-value-123" in env_text
    assert "DATABASE_URL=postgres://user:pw@host/db" in env_text


def test_wizard_does_not_overwrite_existing_env_key(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("SECRET_KEY=original\n", encoding="utf-8")
    _script_input(
        monkeypatch,
        [
            "1",
            "demo-app",
            "yes",
            "SECRET_KEY=replacement",
            "NEW_TOKEN=abc",
            "",
            "no",
        ],
    )

    cli.setup_wizard()

    env_text = (tmp_path / ".env").read_text(encoding="utf-8")
    assert "SECRET_KEY=original" in env_text
    assert "replacement" not in env_text
    assert "NEW_TOKEN=abc" in env_text
    output = capsys.readouterr().out
    assert "left unchanged: SECRET_KEY" in output
    assert "replacement" not in output
    assert "abc" not in output


def test_wizard_without_env_vars_writes_no_env_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _script_input(monkeypatch, ["1", "demo-app", "no", "yes"])

    cli.setup_wizard()

    assert (tmp_path / "deployment.json").exists()
    assert not (tmp_path / ".env").exists()


@pytest.mark.skipif(os.name == "nt", reason="POSIX file modes are not enforced on Windows")
def test_new_env_file_is_owner_only(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _script_input(monkeypatch, ["1", "demo-app", "yes", "TOKEN=x", "", "no"])

    cli.setup_wizard()

    assert (tmp_path / ".env").stat().st_mode & 0o777 == 0o600
