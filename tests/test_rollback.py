"""Tests for RollbackManager snapshots and restore flow."""

from pathlib import Path

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
    assert manager.rollback_to_previous()
    assert (project_dir / "app.py").read_text(encoding="utf-8") == "print('v1')\n"


def test_rollback_invokes_callback(tmp_path):
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    _write_app(project_dir, "print('start')\n")

    manager = RollbackManager(str(project_dir))
    manager.create_checkpoint("vercel")

    _write_app(project_dir, "print('broken')\n")

    invoked = {}

    def callback(state: dict) -> bool:
        invoked["platform"] = state.get("platform")
        return True

    assert manager.rollback_to_previous(callback)
    assert invoked["platform"] == "vercel"
    assert (project_dir / "app.py").read_text(encoding="utf-8") == "print('start')\n"
