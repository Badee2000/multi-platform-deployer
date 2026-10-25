"""Tests that CLI commands report real outcomes through exit codes."""

import argparse

from multi_platform_deployer import cli


class _FakeRollbackManager:
    def __init__(self, result: bool):
        self._result = result

    def rollback_to_previous(self, callback=None) -> bool:
        return self._result


class _FakeDeployer:
    def __init__(self, project_root, result: bool = True):
        self.rollback_manager = _FakeRollbackManager(result)


class _FakeHealthChecker:
    @staticmethod
    def print_summary(health):
        raise AssertionError("cmd_health must not print the summary again; check_health already does")


class _FakeHealthDeployer:
    health_checker = _FakeHealthChecker()

    def __init__(self, project_root):
        pass

    def check_health(self, url, endpoints):
        return {"server_up": False}


def test_cmd_run_returns_1_when_deploy_fails(monkeypatch):
    monkeypatch.setattr(cli, "deploy", lambda **kwargs: False)
    args = argparse.Namespace(multi=False, platform="render", dry_run=False, migrate=False)
    assert cli.cmd_run(args) == 1


def test_cmd_run_returns_0_when_deploy_succeeds(monkeypatch):
    monkeypatch.setattr(cli, "multi_deploy", lambda: True)
    assert cli.cmd_run(argparse.Namespace(multi=True)) == 0


def test_cmd_rollback_returns_1_when_restore_fails(monkeypatch):
    monkeypatch.setattr(cli, "ask_yes_no", lambda question: True)
    monkeypatch.setattr(cli, "Deployer", lambda root: _FakeDeployer(root, result=False))
    assert cli.cmd_rollback(argparse.Namespace()) == 1


def test_cmd_rollback_reports_live_deployment_unchanged(monkeypatch, capsys):
    monkeypatch.setattr(cli, "ask_yes_no", lambda question: True)
    monkeypatch.setattr(cli, "Deployer", lambda root: _FakeDeployer(root, result=True))
    assert cli.cmd_rollback(argparse.Namespace()) == 0
    assert "NOT changed" in capsys.readouterr().out


def test_cmd_health_returns_1_when_server_down(monkeypatch):
    monkeypatch.setattr(cli, "Deployer", _FakeHealthDeployer)
    args = argparse.Namespace(url="http://localhost:9", endpoints=None)
    assert cli.cmd_health(args) == 1


class _FakeLiveDeployer:
    instances = []

    def __init__(self, project_root, dry_run=False):
        self.dry_run = dry_run
        self.platform = "unset"
        self.result = True
        _FakeLiveDeployer.instances.append(self)

    def rollback_live(self, platform=None):
        self.platform = platform
        return self.result


def _live_args(**overrides):
    values = dict(live=True, platform=None, dry_run=False)
    values.update(overrides)
    return argparse.Namespace(**values)


def test_cmd_rollback_live_success(monkeypatch, capsys):
    _FakeLiveDeployer.instances.clear()
    monkeypatch.setattr(cli, "ask_yes_no", lambda question: True)
    monkeypatch.setattr(cli, "Deployer", _FakeLiveDeployer)

    assert cli.cmd_rollback(_live_args(platform="render")) == 0
    assert _FakeLiveDeployer.instances[0].platform == "render"
    assert "Rollback requested" in capsys.readouterr().out


def test_cmd_rollback_live_failure_returns_1(monkeypatch, capsys):
    _FakeLiveDeployer.instances.clear()
    monkeypatch.setattr(cli, "ask_yes_no", lambda question: True)

    def failing(project_root, dry_run=False):
        deployer = _FakeLiveDeployer(project_root, dry_run)
        deployer.result = False
        return deployer

    monkeypatch.setattr(cli, "Deployer", failing)

    assert cli.cmd_rollback(_live_args()) == 1
    assert "LIVE ROLLBACK FAILED" in capsys.readouterr().out


def test_cmd_rollback_live_declined_does_nothing(monkeypatch):
    _FakeLiveDeployer.instances.clear()
    monkeypatch.setattr(cli, "ask_yes_no", lambda question: False)
    monkeypatch.setattr(cli, "Deployer", _FakeLiveDeployer)

    assert cli.cmd_rollback(_live_args()) == 0
    assert _FakeLiveDeployer.instances[0].platform == "unset"


def test_cmd_rollback_live_dry_run_skips_confirmation(monkeypatch, capsys):
    _FakeLiveDeployer.instances.clear()

    def no_prompt(question):
        raise AssertionError("dry run must not prompt")

    monkeypatch.setattr(cli, "ask_yes_no", no_prompt)
    monkeypatch.setattr(cli, "Deployer", _FakeLiveDeployer)

    assert cli.cmd_rollback(_live_args(dry_run=True)) == 0
    assert _FakeLiveDeployer.instances[0].dry_run is True
    assert "Nothing was changed" in capsys.readouterr().out
