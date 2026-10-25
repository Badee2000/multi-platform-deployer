"""Tests for the Deployer.deploy() flow using mocked migrators and deployers."""

from multi_platform_deployer.main import Deployer


class _FakeMigrator:
    def __init__(self, succeeds: bool):
        self._succeeds = succeeds
        self.calls = 0

    def run_migrations(self) -> bool:
        self.calls += 1
        return self._succeeds


class _FakeDeployer:
    def __init__(self, succeeds: bool = True):
        self._succeeds = succeeds
        self.calls = 0

    def deploy(self) -> bool:
        self.calls += 1
        return self._succeeds


class _FakeRollbackManager:
    def __init__(self):
        self.checkpoints = []

    def create_checkpoint(self, platform, metadata):
        self.checkpoints.append((platform, metadata))
        return "checkpoint-id"


def _make_deployer(tmp_path, monkeypatch, migrations_ok=True, platform_results=None):
    deployer = Deployer(str(tmp_path))
    monkeypatch.setattr(deployer, "_run_system_checks", lambda: (True, []))
    monkeypatch.setattr(deployer, "validate_deployment", lambda platform: True)
    deployer.migrator = _FakeMigrator(migrations_ok)
    deployer.rollback_manager = _FakeRollbackManager()

    platform_results = platform_results or {}
    fakes = {}

    def fake_initialize(platform):
        fake = _FakeDeployer(platform_results.get(platform, True))
        fakes[platform.lower()] = fake
        deployer.deployers[platform.lower()] = fake
        return fake

    monkeypatch.setattr(deployer, "initialize_deployer", fake_initialize)
    return deployer, fakes


def test_failed_migration_aborts_deploy(tmp_path, monkeypatch):
    deployer, fakes = _make_deployer(tmp_path, monkeypatch, migrations_ok=False)

    assert deployer.deploy("render", run_migrations=True) is False
    assert deployer.migrator.calls == 1
    assert fakes == {}, "no deployer should be called after a failed migration"
    assert deployer.rollback_manager.checkpoints == []


def test_successful_migration_then_deploy_creates_checkpoint(tmp_path, monkeypatch):
    deployer, fakes = _make_deployer(tmp_path, monkeypatch, migrations_ok=True)

    assert deployer.deploy("render", run_migrations=True) is True
    assert fakes["render"].calls == 1
    assert len(deployer.rollback_manager.checkpoints) == 1
    platform, metadata = deployer.rollback_manager.checkpoints[0]
    assert platform == "render"
    assert metadata["run_migrations"] is True


def test_skipping_migrations_does_not_run_migrator(tmp_path, monkeypatch):
    deployer, fakes = _make_deployer(tmp_path, monkeypatch, migrations_ok=False)

    assert deployer.deploy("render", run_migrations=False) is True
    assert deployer.migrator.calls == 0
    assert fakes["render"].calls == 1


def test_failed_deployer_returns_false_and_creates_no_checkpoint(tmp_path, monkeypatch):
    deployer, _ = _make_deployer(
        tmp_path, monkeypatch, platform_results={"railway": False}
    )

    assert deployer.deploy("railway", run_migrations=False) is False
    assert deployer.rollback_manager.checkpoints == []


def test_env_secret_never_reaches_checkpoint_or_logs(tmp_path, monkeypatch, caplog):
    secret = "s3cret-token-value-xyz"
    (tmp_path / ".env").write_text(f"API_TOKEN={secret}\n", encoding="utf-8")
    deployer, _ = _make_deployer(tmp_path, monkeypatch, migrations_ok=True)

    with caplog.at_level("DEBUG"):
        assert deployer.deploy("render", run_migrations=False) is True

    assert secret not in caplog.text
    assert secret not in repr(deployer.rollback_manager.checkpoints)


def test_multi_platform_partial_failure_attempts_all_and_reports_each(tmp_path, monkeypatch):
    deployer, fakes = _make_deployer(
        tmp_path,
        monkeypatch,
        platform_results={"render": False, "railway": True, "heroku": False},
    )

    results = deployer.deploy_to_multiple_platforms(
        ["render", "railway", "heroku"], run_migrations=False
    )

    assert results == {"render": False, "railway": True, "heroku": False}
    assert all(fake.calls == 1 for fake in fakes.values())
    assert [p for p, _ in deployer.rollback_manager.checkpoints] == ["railway"]


def test_multi_platform_migration_failure_skips_every_platform(tmp_path, monkeypatch):
    deployer, fakes = _make_deployer(tmp_path, monkeypatch, migrations_ok=False)

    results = deployer.deploy_to_multiple_platforms(["render", "railway"], run_migrations=True)

    assert results == {"render": False, "railway": False}
    assert fakes == {}
    assert deployer.migrator.calls == 2
