"""Regression tests for dry-run output and config defaults used by 'run --platform'."""

import logging
import subprocess

import pytest

from multi_platform_deployer.main import Deployer
from multi_platform_deployer.utils.logger import get_logger


def test_deployer_loggers_live_under_package_namespace():
    logger = get_logger("VercelDeployer")
    assert logger.name == "multi_platform_deployer.VercelDeployer"
    assert get_logger("multi_platform_deployer").name == "multi_platform_deployer"


def test_dry_run_logs_plan_and_never_executes(tmp_path, monkeypatch, caplog):
    monkeypatch.setenv("VERCEL_TOKEN", "fake-token-for-test")
    monkeypatch.setattr(Deployer, "_run_system_checks", lambda self: (True, []))
    monkeypatch.setattr(Deployer, "validate_deployment", lambda self, platform: True)

    def _forbidden(*args, **kwargs):
        raise AssertionError("dry-run must not execute subprocesses")

    monkeypatch.setattr(subprocess, "run", _forbidden)
    monkeypatch.setattr(subprocess, "Popen", _forbidden)

    deployer = Deployer(str(tmp_path), dry_run=True)
    with caplog.at_level(logging.INFO, logger="multi_platform_deployer"):
        assert deployer.deploy("vercel") is True

    messages = " ".join(r.getMessage() for r in caplog.records)
    assert "would run: vercel deploy --prod --yes" in messages
    assert "fake-token-for-test" not in messages


def test_deploy_fills_required_config_keys_from_request(tmp_path, monkeypatch):
    monkeypatch.setattr(Deployer, "_run_system_checks", lambda self: (True, []))
    seen = {}

    def _capture(self, platform):
        seen["config"] = dict(self.config)
        return False

    monkeypatch.setattr(Deployer, "validate_deployment", _capture)

    deployer = Deployer(str(tmp_path), dry_run=True)
    assert deployer.deploy("render") is False
    assert seen["config"]["platform"] == "render"
    assert seen["config"]["app_name"] == tmp_path.resolve().name.replace(" ", "-")


def test_deploy_keeps_app_name_from_deployment_file(tmp_path, monkeypatch):
    (tmp_path / "deployment.yaml").write_text(
        "platform: railway\napp_name: my-service\n", encoding="utf-8"
    )
    monkeypatch.setattr(Deployer, "_run_system_checks", lambda self: (True, []))
    seen = {}

    def _capture(self, platform):
        seen["config"] = dict(self.config)
        return False

    monkeypatch.setattr(Deployer, "validate_deployment", _capture)

    deployer = Deployer(str(tmp_path), dry_run=True)
    deployer.deploy("vercel")
    assert seen["config"]["app_name"] == "my-service"
    assert seen["config"]["platform"] == "railway"


@pytest.mark.parametrize("platform", ["vercel", "render", "railway", "heroku"])
def test_dry_run_without_credentials_still_exits_cleanly(tmp_path, monkeypatch, platform):
    for var in ("VERCEL_TOKEN", "RENDER_API_KEY", "RAILWAY_TOKEN", "HEROKU_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr(Deployer, "_run_system_checks", lambda self: (True, []))
    monkeypatch.setattr(Deployer, "validate_deployment", lambda self, p: True)
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: (_ for _ in ()).throw(AssertionError("executed")))

    deployer = Deployer(str(tmp_path), dry_run=True)
    assert deployer.deploy(platform) is True
