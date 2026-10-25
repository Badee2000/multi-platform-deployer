"""Tests for RollbackManager snapshots and restore flow."""

from pathlib import Path
import zipfile

from multi_platform_deployer.scripts.rollback import RollbackManager


def _write_app(project_dir: Path, content: str) -> None:
    (project_dir / "app.py").write_text(content, encoding="utf-8")


def test_checkpoint_creation_and_restore(tmp_path):
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    _write_app(project_dir, "print('v1')\n")

    manager = RollbackManager(str(project_dir))
    state = manager.create_checkpoint("render", {"notes": "first"})

    assert state is not None
    artifact = project_dir / state["artifact_path"]
    assert artifact.exists()

    _write_app(project_dir, "print('v2')\n")
    manager.create_checkpoint("render", {"notes": "second"})

    _write_app(project_dir, "print('v3')\n")
    assert manager.rollback_to_previous()
    assert (project_dir / "app.py").read_text(encoding="utf-8") == "print('v1')\n"


def test_rollback_invokes_callback(tmp_path):
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    _write_app(project_dir, "print('start')\n")

    manager = RollbackManager(str(project_dir))
    manager.create_checkpoint("vercel")

    _write_app(project_dir, "print('broken')\n")
    manager.create_checkpoint("vercel")

    invoked = {}

    def callback(state: dict) -> bool:
        invoked["platform"] = state.get("platform")
        return True

    assert manager.rollback_to_previous(callback)
    assert invoked["platform"] == "vercel"
    assert (project_dir / "app.py").read_text(encoding="utf-8") == "print('start')\n"


def test_rollback_without_previous_checkpoint_fails_and_keeps_files(tmp_path):
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    _write_app(project_dir, "print('only')\n")

    manager = RollbackManager(str(project_dir))
    manager.create_checkpoint("render")

    _write_app(project_dir, "print('changed')\n")
    assert not manager.rollback_to_previous()
    assert (project_dir / "app.py").read_text(encoding="utf-8") == "print('changed')\n"


def test_snapshot_excludes_env_files_and_restore_leaves_them(tmp_path):
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    _write_app(project_dir, "print('v1')\n")
    (project_dir / ".env").write_text("API_KEY=secret-one\n", encoding="utf-8")
    (project_dir / ".env.example").write_text("API_KEY=\n", encoding="utf-8")

    manager = RollbackManager(str(project_dir))
    state = manager.create_checkpoint("render")
    manager.create_checkpoint("render")

    with zipfile.ZipFile(project_dir / state["artifact_path"]) as archive:
        names = archive.namelist()
    assert ".env" not in names
    assert ".env.example" in names

    (project_dir / ".env").write_text("API_KEY=secret-two\n", encoding="utf-8")
    assert manager.rollback_to_previous()
    assert (project_dir / ".env").read_text(encoding="utf-8") == "API_KEY=secret-two\n"
