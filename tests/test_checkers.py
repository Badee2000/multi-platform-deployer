"""Tests for deployment checkers."""

import pytest
import tempfile
from pathlib import Path
from multi_platform_deployer.checkers import (
    FlaskChecker,
    DjangoChecker,
    FastAPIChecker,
    SystemChecker,
)


class TestFlaskChecker:
    """Test FlaskChecker class."""
    
    @pytest.fixture
    def temp_project(self):
        """Create temporary Flask project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create necessary files
            app_file = Path(tmpdir) / "app.py"
            app_file.write_text("""
from flask import Flask

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret'

@app.route('/health')
def health():
    return {'status': 'ok'}

if __name__ == '__main__':
    app.run(debug=False)
""")
            
            req_file = Path(tmpdir) / "requirements.txt"
            req_file.write_text("Flask==2.0.0\n")
            
            yield tmpdir
    
    def test_check_all(self, temp_project):
        """Test comprehensive Flask checks."""
        checker = FlaskChecker(temp_project)
        is_ready, results = checker.check_all()
        
        # Should have multiple checks
        assert len(results) > 0
        # Check that there are results
        assert any(r.passed for r in results)
    
    def test_check_flask_app(self, temp_project):
        """Test Flask app detection."""
        checker = FlaskChecker(temp_project)
        result = checker.check_flask_app()
        
        assert result.passed is True
    
    def test_check_debug_mode(self, temp_project):
        """Test debug mode check."""
        checker = FlaskChecker(temp_project)
        result = checker.check_debug_mode()
        
        # Since we set debug=False, this should pass
        assert result.passed is True


class TestDjangoChecker:
    """Test DjangoChecker class."""
    
    @pytest.fixture
    def temp_project(self):
        """Create temporary Django project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create manage.py
            manage_file = Path(tmpdir) / "manage.py"
            manage_file.write_text("#!/usr/bin/env python")
            
            # Create settings.py
            settings_file = Path(tmpdir) / "settings.py"
            settings_file.write_text("""
DEBUG = False
ALLOWED_HOSTS = ['*']
SECRET_KEY = 'django-secret'
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'mydb',
    }
}
STATIC_ROOT = '/static/'
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
""")
            
            yield tmpdir
    
    def test_check_all(self, temp_project):
        """Test comprehensive Django checks."""
        checker = DjangoChecker(temp_project)
        is_ready, results = checker.check_all()
        
        assert len(results) > 0
    
    def test_check_manage_py(self, temp_project):
        """Test manage.py detection."""
        checker = DjangoChecker(temp_project)
        result = checker.check_manage_py()
        
        assert result.passed is True


class TestFastAPIChecker:
    """Test FastAPIChecker class."""
    
    @pytest.fixture
    def temp_project(self):
        """Create temporary FastAPI project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create app.py
            app_file = Path(tmpdir) / "app.py"
            app_file.write_text("""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.exception_handler(Exception)
async def exception_handler(request, exc):
    return {"error": str(exc)}
""")
            
            req_file = Path(tmpdir) / "requirements.txt"
            req_file.write_text("fastapi==0.95.0\nuvicorn==0.21.0\n")
            
            yield tmpdir
    
    def test_check_all(self, temp_project):
        """Test comprehensive FastAPI checks."""
        checker = FastAPIChecker(temp_project)
        is_ready, results = checker.check_all()
        
        assert len(results) > 0
    
    def test_check_fastapi_app(self, temp_project):
        """Test FastAPI app detection."""
        checker = FastAPIChecker(temp_project)
        result = checker.check_fastapi_app()
        
        assert result.passed is True


class TestSystemChecker:
    """Test the framework-agnostic SystemChecker."""

    @pytest.fixture
    def healthy_project(self):
        """Create a project that satisfies all system checks."""

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            (tmp_path / "runtime.txt").write_text("python-3.11.0\n", encoding="utf-8")
            (tmp_path / "requirements.txt").write_text("Flask==2.3.2\n", encoding="utf-8")
            (tmp_path / "deployment.yaml").write_text("platform: render\n", encoding="utf-8")
            (tmp_path / ".env").write_text("SECRET_KEY=super-secret-value\n", encoding="utf-8")
            yield tmpdir

    def test_system_checker_passes(self, healthy_project):
        """SystemChecker should approve a well-prepared project."""

        checker = SystemChecker(healthy_project)
        is_ready, results = checker.check_all()

        assert is_ready is True
        assert any(r.name == "Python runtime" and r.passed for r in results)

    def test_placeholder_env_detection(self, tmp_path):
        """Placeholder secrets should cause a failure."""

        project = tmp_path / "proj"
        project.mkdir()
        (project / "requirements.txt").write_text("Flask==2.3.2\n", encoding="utf-8")
        (project / "deployment.yaml").write_text("platform: render\n", encoding="utf-8")
        (project / "runtime.txt").write_text("python-3.11.0\n", encoding="utf-8")
        (project / ".env").write_text("SECRET_KEY=changeme\n", encoding="utf-8")

        checker = SystemChecker(str(project))
        is_ready, results = checker.check_all()

        env_result = next(r for r in results if r.name == "Environment variables")
        assert env_result.passed is False
        assert is_ready is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
