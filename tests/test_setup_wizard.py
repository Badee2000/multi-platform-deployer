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
            "",  # start command: skip
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
            "",
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
    _script_input(monkeypatch, ["1", "demo-app", "", "no", "yes"])

    cli.setup_wizard()

    assert (tmp_path / "deployment.json").exists()
    assert not (tmp_path / ".env").exists()
    assert not (tmp_path / ".gitignore").exists()


@pytest.mark.skipif(os.name == "nt", reason="POSIX file modes are not enforced on Windows")
def test_new_env_file_is_owner_only(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _script_input(monkeypatch, ["1", "demo-app", "", "yes", "TOKEN=x", "", "no"])

    cli.setup_wizard()

    assert (tmp_path / ".env").stat().st_mode & 0o777 == 0o600


def test_wizard_saves_start_command(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _script_input(monkeypatch, ["1", "demo-app", "gunicorn wsgi:app", "no", "no"])

    cli.setup_wizard()

    config = yaml.safe_load((tmp_path / "deployment.yaml").read_text(encoding="utf-8"))
    assert config["start_command"] == "gunicorn wsgi:app"


def test_wizard_skipped_start_command_is_not_written(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _script_input(monkeypatch, ["1", "demo-app", "", "no", "no"])

    cli.setup_wizard()

    config = yaml.safe_load((tmp_path / "deployment.yaml").read_text(encoding="utf-8"))
    assert "start_command" not in config


def test_wizard_never_writes_a_guessed_railway_services_block(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _script_input(monkeypatch, ["2", "demo-app", "", "no", "no"])  # 2 = Railway

    cli.setup_wizard()

    config = yaml.safe_load((tmp_path / "deployment.yaml").read_text(encoding="utf-8"))
    assert config["platform"] == "railway"
    assert "services" not in config


def test_wizard_adds_env_to_gitignore_when_it_saves_secrets(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _script_input(monkeypatch, ["1", "demo-app", "", "yes", "TOKEN=x", "", "no"])

    cli.setup_wizard()

    assert (tmp_path / ".gitignore").read_text(encoding="utf-8").splitlines() == [".env"]


def test_wizard_appends_to_existing_gitignore_without_duplicating(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".gitignore").write_text("__pycache__/", encoding="utf-8")  # no trailing newline
    _script_input(monkeypatch, ["1", "demo-app", "", "yes", "A=1", "", "no"])

    cli.setup_wizard()
    lines = (tmp_path / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert lines == ["__pycache__/", ".env"]

    _script_input(monkeypatch, ["1", "demo-app", "", "yes", "B=2", "", "yes"])  # overwrite=yes
    (tmp_path / "deployment.yaml").unlink()
    cli.setup_wizard()
    assert (tmp_path / ".gitignore").read_text(encoding="utf-8").splitlines().count(".env") == 1


@pytest.mark.parametrize("existing", [".env", "/.env", ".env*", "*.env"])
def test_wizard_leaves_gitignore_alone_when_env_is_already_covered(tmp_path, monkeypatch, existing):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".gitignore").write_text(f"{existing}\n", encoding="utf-8")
    _script_input(monkeypatch, ["1", "demo-app", "", "yes", "A=1", "", "no"])

    cli.setup_wizard()

    assert (tmp_path / ".gitignore").read_text(encoding="utf-8") == f"{existing}\n"
