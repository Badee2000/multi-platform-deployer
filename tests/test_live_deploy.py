"""
Live credential checks against real platforms.

These tests make read-only calls (who am I / list owners). They never create
or deploy anything. They run only when you opt in:

    set MPD_LIVE_TESTS=1
    set VERCEL_TOKEN=...      (and/or RAILWAY_TOKEN, HEROKU_API_KEY, RENDER_API_KEY)
    pytest tests/test_live_deploy.py -v

Each platform's test is skipped on its own if its token or CLI is missing.
"""

import os
import shutil
import subprocess

import pytest
import requests

LIVE = os.environ.get("MPD_LIVE_TESTS") == "1"
pytestmark = pytest.mark.skipif(not LIVE, reason="set MPD_LIVE_TESTS=1 to run live credential checks")


def _run_whoami(cli: str, args, env_name: str):
    token = os.environ.get(env_name)
    if not token:
        pytest.skip(f"{env_name} is not set")
    executable = shutil.which(cli)
    if executable is None:
        pytest.skip(f"'{cli}' CLI is not installed")
    result = subprocess.run(
        [executable, *args],
        env={**os.environ, env_name: token},
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, "credential check failed (token value is not shown)"


def test_vercel_token_is_accepted():
    _run_whoami("vercel", ["whoami"], "VERCEL_TOKEN")


def test_heroku_key_is_accepted():
    _run_whoami("heroku", ["auth:whoami"], "HEROKU_API_KEY")


def test_railway_token_is_accepted():
    _run_whoami("railway", ["whoami"], "RAILWAY_TOKEN")


def test_render_key_is_accepted():
    token = os.environ.get("RENDER_API_KEY")
    if not token:
        pytest.skip("RENDER_API_KEY is not set")
    response = requests.get(
        "https://api.render.com/v1/owners?limit=1",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        timeout=30,
    )
    assert response.status_code == 200, f"Render returned HTTP {response.status_code}"
