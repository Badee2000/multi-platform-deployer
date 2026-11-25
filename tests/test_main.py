"""Tests for the main Deployer class."""

import tempfile
from pathlib import Path

import pytest

from multi_platform_deployer.main import Deployer


class TestDeployer:
    """Test main Deployer class."""

    @pytest.fixture
    def temp_project(self):
        """Create temporary project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create Flask app
            app_file = Path(tmpdir) / "app.py"
            app_file.write_text("""
from flask import Flask

app = Flask(__name__)
app.config['SECRET_KEY'] = 'test-secret'

@app.route('/')
def index():
    return {'message': 'Hello'}

if __name__ == '__main__':
    app.run()
""")

            # Create requirements.txt
            req_file = Path(tmpdir) / "requirements.txt"
            req_file.write_text("Flask==2.0.0\n")

            yield tmpdir

    def test_deployer_initialization(self, temp_project):
        """Test deployer initialization."""
        deployer = Deployer(temp_project)

        assert deployer.project_root == Path(temp_project)
        assert len(deployer.AVAILABLE_DEPLOYERS) > 0
        assert len(deployer.AVAILABLE_CHECKERS) > 0

    def test_check_deployment_readiness(self, temp_project):
        """Test deployment readiness check."""
        deployer = Deployer(temp_project)
        is_ready, results = deployer.check_deployment_readiness("flask")

        assert isinstance(is_ready, bool)
        assert len(results) > 0

    def test_initialize_deployer(self, temp_project):
        """Test deployer initialization for platform."""
        deployer = Deployer(temp_project)

        render_deployer = deployer.initialize_deployer("render")
        assert render_deployer is not None

        railway_deployer = deployer.initialize_deployer("railway")
        assert railway_deployer is not None

    def test_invalid_platform(self, temp_project):
        """Test with invalid platform."""
        deployer = Deployer(temp_project)

        result = deployer.initialize_deployer("invalid-platform")
        assert result is None

    def test_invalid_framework(self, temp_project):
        """Test with invalid framework."""
        deployer = Deployer(temp_project)

        is_ready, results = deployer.check_deployment_readiness("invalid-framework")
        assert is_ready is False

    def test_deploy_prints_health_command_with_url(
        self, temp_project, monkeypatch, caplog
    ):
        """After a successful deploy, the log tells the user how to check it."""

        class StubDeployer:
            deployed_url = "https://app.onrender.com"

            def deploy(self):
                return True

        deployer = Deployer(temp_project)
        monkeypatch.setattr(deployer, "_run_system_checks", lambda: (True, []))
        monkeypatch.setattr(deployer, "validate_deployment", lambda _p: True)
        monkeypatch.setattr(
            deployer.rollback_manager, "create_checkpoint", lambda **_kw: None
        )
        deployer.deployers["render"] = StubDeployer()

        with caplog.at_level("INFO"):
            assert deployer.deploy("render", run_migrations=False) is True
        assert (
            "multi-platform-deployer health --url https://app.onrender.com"
            in caplog.text
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
