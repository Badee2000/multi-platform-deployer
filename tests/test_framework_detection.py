"""Tests for framework detection in the CLI, using temp directories only."""

import pytest

from multi_platform_deployer import cli


@pytest.fixture
def project(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_detects_fastapi_in_app_py(project):
    (project / "app.py").write_text("from fastapi import FastAPI\napp = FastAPI()\n")
    assert cli.detect_framework() == "fastapi"


def test_detects_fastapi_in_main_py(project):
    (project / "main.py").write_text("import fastapi\napp = fastapi.FastAPI()\n")
    assert cli.detect_framework() == "fastapi"


def test_detects_flask_in_app_py(project):
    (project / "app.py").write_text("from flask import Flask\napp = Flask(__name__)\n")
    assert cli.detect_framework() == "flask"


def test_detects_django_before_other_frameworks(project):
    (project / "manage.py").write_text("")
    (project / "app.py").write_text("from fastapi import FastAPI\n")
    assert cli.detect_framework() == "django"


def test_wsgi_without_markers_falls_back_to_flask(project):
    (project / "wsgi.py").write_text("application = object()\n")
    assert cli.detect_framework() == "flask"


def test_returns_none_for_unknown_project(project):
    (project / "app.py").write_text("print('hello')\n")
    assert cli.detect_framework() is None


def test_returns_none_for_empty_directory(project):
    assert cli.detect_framework() is None
