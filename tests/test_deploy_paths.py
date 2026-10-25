"""Mocked tests for the real deploy paths. No platform CLI or API is ever called."""

import subprocess

import pytest

from multi_platform_deployer.deployers import base as base_module
from multi_platform_deployer.deployers import (
    HerokuDeployer,
    RailwayDeployer,
    RenderDeployer,
    VercelDeployer,
)
from multi_platform_deployer.deployers import render as render_module

SECRET = "tok-secret-123"


def _cp(stdout: str = "", stderr: str = "", returncode: int = 0):
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


class FakeCli:
    """Records every command and answers from a table keyed by the joined command."""

    def __init__(self, responses=None):
        self.responses = responses or {}
        self.calls = []

    def __call__(self, argv, cwd=None, env=None, check=False, timeout=None):
        self.calls.append({"argv": list(argv), "env": env, "timeout": timeout})
        return self.responses.get(" ".join(argv), _cp())

    @property
    def commands(self):
        return [" ".join(c["argv"]) for c in self.calls]


@pytest.fixture
def fake_cli(monkeypatch):
    """Replace subprocess execution and executable lookup with a recorder."""
    cli = FakeCli()
    monkeypatch.setattr(base_module, "run_command", cli)
    monkeypatch.setattr(base_module.shutil, "which", lambda name: name)
    return cli


class FakeResponse:
    def __init__(self, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload
        self.text = text or ("{}" if payload is None else "")
        self.content = self.text.encode() or b"x"

    def json(self):
        if self._payload is None:
            raise ValueError("no json")
        return self._payload


# --- shared runner -----------------------------------------------------------


def test_run_step_dry_run_executes_nothing(tmp_path, fake_cli):
    deployer = VercelDeployer(str(tmp_path), dry_run=True)
    assert deployer._run_step(["vercel", "deploy"]) == ""
    assert fake_cli.calls == []


def test_run_step_missing_executable_returns_none(tmp_path, fake_cli, monkeypatch):
    monkeypatch.setattr(base_module.shutil, "which", lambda name: None)
    deployer = VercelDeployer(str(tmp_path))
    assert deployer._run_step(["vercel", "deploy"]) is None
    assert fake_cli.calls == []


def test_run_step_timeout_returns_none(tmp_path, monkeypatch, caplog):
    def boom(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="vercel", timeout=5)

    monkeypatch.setattr(base_module, "run_command", boom)
    monkeypatch.setattr(base_module.shutil, "which", lambda name: name)
    deployer = VercelDeployer(str(tmp_path))
    with caplog.at_level("ERROR"):
        assert deployer._run_step(["vercel", "deploy"], timeout=5) is None
    assert "Timed out" in caplog.text


def test_run_step_redacts_secret_from_failure_output(tmp_path, fake_cli, caplog):
    fake_cli.responses["vercel deploy"] = _cp(stderr=f"auth failed for {SECRET}", returncode=1)
    deployer = VercelDeployer(str(tmp_path))
    with caplog.at_level("ERROR"):
        assert deployer._run_step(["vercel", "deploy"], secrets=[SECRET]) is None
    assert SECRET not in caplog.text
    assert "***" in caplog.text


# --- Vercel ------------------------------------------------------------------


def test_vercel_deploy_success_reports_url_and_passes_token_in_env(tmp_path, fake_cli, monkeypatch):
    monkeypatch.setenv("VERCEL_TOKEN", SECRET)
    fake_cli.responses["vercel deploy --prod --yes"] = _cp(
        stdout="Inspect: https://vercel.com/x\nhttps://app-abc.vercel.app\n"
    )
    deployer = VercelDeployer(str(tmp_path))

    assert deployer.deploy() is True
    assert deployer.deployed_url == "https://app-abc.vercel.app"
    call = fake_cli.calls[0]
    assert call["env"]["VERCEL_TOKEN"] == SECRET
    assert SECRET not in " ".join(call["argv"])


def test_vercel_deploy_failure_returns_false_and_hides_token(tmp_path, fake_cli, monkeypatch, caplog):
    monkeypatch.setenv("VERCEL_TOKEN", SECRET)
    fake_cli.responses["vercel deploy --prod --yes"] = _cp(stderr=f"invalid {SECRET}", returncode=1)
    deployer = VercelDeployer(str(tmp_path))

    with caplog.at_level("ERROR"):
        assert deployer.deploy() is False
    assert deployer.deployed_url is None
    assert SECRET not in caplog.text


def test_vercel_missing_token_never_runs_cli(tmp_path, fake_cli, monkeypatch):
    monkeypatch.delenv("VERCEL_TOKEN", raising=False)
    assert VercelDeployer(str(tmp_path)).deploy() is False
    assert fake_cli.calls == []


def test_vercel_dry_run_runs_nothing(tmp_path, fake_cli, monkeypatch):
    monkeypatch.delenv("VERCEL_TOKEN", raising=False)
    assert VercelDeployer(str(tmp_path), dry_run=True).deploy() is True
    assert fake_cli.calls == []


# --- Railway -----------------------------------------------------------------


def test_railway_deploy_success(tmp_path, fake_cli, monkeypatch):
    monkeypatch.setenv("RAILWAY_TOKEN", SECRET)
    deployer = RailwayDeployer(str(tmp_path))

    assert deployer.deploy() is True
    assert fake_cli.commands == ["railway up --ci"]
    assert fake_cli.calls[0]["env"]["RAILWAY_TOKEN"] == SECRET


def test_railway_missing_token_never_runs_cli(tmp_path, fake_cli, monkeypatch):
    monkeypatch.delenv("RAILWAY_TOKEN", raising=False)
    assert RailwayDeployer(str(tmp_path)).deploy() is False
    assert fake_cli.calls == []


# --- Heroku ------------------------------------------------------------------


def test_heroku_refuses_uncommitted_changes(tmp_path, fake_cli, monkeypatch):
    monkeypatch.setenv("HEROKU_API_KEY", SECRET)
    fake_cli.responses["git status --porcelain"] = _cp(stdout=" M app.py\n")
    deployer = HerokuDeployer(str(tmp_path))

    assert deployer.deploy() is False
    assert not any(c.startswith("git push") for c in fake_cli.commands)


def test_heroku_pushes_head_to_main_when_clean(tmp_path, fake_cli, monkeypatch):
    monkeypatch.setenv("HEROKU_API_KEY", SECRET)
    deployer = HerokuDeployer(str(tmp_path))

    assert deployer.deploy() is True
    assert "git push heroku HEAD:main" in fake_cli.commands


def test_heroku_auth_failure_stops_before_push(tmp_path, fake_cli, monkeypatch):
    monkeypatch.setenv("HEROKU_API_KEY", SECRET)
    fake_cli.responses["heroku auth:whoami"] = _cp(stderr="unauthorized", returncode=1)
    deployer = HerokuDeployer(str(tmp_path))

    assert deployer.deploy() is False
    assert fake_cli.commands == ["heroku auth:whoami"]


# --- Render (REST API) -------------------------------------------------------


def _render_git_responses(fake_cli, status="", unpushed="0\n", remote="git@github.com:acme/app.git\n"):
    fake_cli.responses["git status --porcelain"] = _cp(stdout=status)
    fake_cli.responses["git rev-list --count @{u}..HEAD"] = _cp(stdout=unpushed)
    fake_cli.responses["git remote get-url origin"] = _cp(stdout=remote)
    fake_cli.responses["git rev-parse --abbrev-ref HEAD"] = _cp(stdout="main\n")


@pytest.fixture
def fake_http(monkeypatch):
    calls = []
    queue = []

    def request(method, url, headers=None, json=None, timeout=None):
        calls.append({"method": method, "url": url, "headers": headers, "json": json})
        return queue.pop(0)

    monkeypatch.setattr(render_module.requests, "request", request)
    return {"calls": calls, "queue": queue}


def test_render_refuses_uncommitted_changes(tmp_path, fake_cli, fake_http, monkeypatch):
    monkeypatch.setenv("RENDER_API_KEY", SECRET)
    _render_git_responses(fake_cli, status=" M app.py\n")

    assert RenderDeployer(str(tmp_path)).deploy() is False
    assert fake_http["calls"] == []


def test_render_ignores_its_own_state_folder(tmp_path, fake_cli, fake_http, monkeypatch):
    monkeypatch.setenv("RENDER_API_KEY", SECRET)
    _render_git_responses(fake_cli, status="?? .deployment/\n")
    fake_http["queue"].extend([FakeResponse(201, {}), FakeResponse(200, {})])

    assert RenderDeployer(str(tmp_path), {"render_service_id": "srv-9"}).deploy() is True


def test_render_still_refuses_real_changes_next_to_state_folder(tmp_path, fake_cli, fake_http, monkeypatch):
    monkeypatch.setenv("RENDER_API_KEY", SECRET)
    _render_git_responses(fake_cli, status="?? .deployment/\n M app.py\n")

    assert RenderDeployer(str(tmp_path), {"render_service_id": "srv-9"}).deploy() is False
    assert fake_http["calls"] == []


def test_render_refuses_unpushed_commits(tmp_path, fake_cli, fake_http, monkeypatch):
    monkeypatch.setenv("RENDER_API_KEY", SECRET)
    _render_git_responses(fake_cli, unpushed="2\n")

    assert RenderDeployer(str(tmp_path)).deploy() is False
    assert fake_http["calls"] == []


def test_render_creates_service_and_reports_url(tmp_path, fake_cli, fake_http, monkeypatch):
    monkeypatch.setenv("RENDER_API_KEY", SECRET)
    monkeypatch.setenv("RENDER_OWNER_ID", "own-1")
    _render_git_responses(fake_cli)
    fake_http["queue"].append(
        FakeResponse(
            201,
            {"service": {"id": "srv-1", "serviceDetails": {"url": "https://app.onrender.com"}}},
        )
    )
    deployer = RenderDeployer(str(tmp_path), {"app_name": "My App", "start_command": "gunicorn app:app"})

    assert deployer.deploy() is True
    assert deployer.deployed_url == "https://app.onrender.com"
    call = fake_http["calls"][0]
    assert call["method"] == "POST"
    assert call["url"].endswith("/services")
    assert call["headers"]["Authorization"] == f"Bearer {SECRET}"
    assert call["json"]["repo"] == "https://github.com/acme/app"
    assert call["json"]["ownerId"] == "own-1"
    assert call["json"]["name"] == "my-app"
    assert call["json"]["autoDeployTrigger"] == "commit"
    assert call["json"]["serviceDetails"]["runtime"] == "python"
    assert call["json"]["serviceDetails"]["envSpecificDetails"]["startCommand"] == "gunicorn app:app"


def test_render_refuses_to_create_without_start_command(tmp_path, fake_cli, fake_http, monkeypatch, caplog):
    monkeypatch.setenv("RENDER_API_KEY", SECRET)
    monkeypatch.setenv("RENDER_OWNER_ID", "own-1")
    _render_git_responses(fake_cli)

    with caplog.at_level("ERROR"):
        assert RenderDeployer(str(tmp_path)).deploy() is False
    assert fake_http["calls"] == []
    assert "start_command" in caplog.text
    assert SECRET not in caplog.text


@pytest.mark.parametrize("blank", ["", "   ", None])
def test_render_treats_blank_start_command_as_missing(tmp_path, fake_cli, fake_http, monkeypatch, blank):
    monkeypatch.setenv("RENDER_API_KEY", SECRET)
    monkeypatch.setenv("RENDER_OWNER_ID", "own-1")
    _render_git_responses(fake_cli)

    assert RenderDeployer(str(tmp_path), {"start_command": blank}).deploy() is False
    assert fake_http["calls"] == []


@pytest.mark.parametrize("command", ["python app.py", "flask run", "python manage.py runserver 0.0.0.0:$PORT"])
def test_render_warns_about_dev_server_but_respects_choice(
    tmp_path, fake_cli, fake_http, monkeypatch, caplog, command
):
    monkeypatch.setenv("RENDER_API_KEY", SECRET)
    monkeypatch.setenv("RENDER_OWNER_ID", "own-1")
    _render_git_responses(fake_cli)
    fake_http["queue"].append(FakeResponse(201, {"service": {"id": "srv-1"}}))

    with caplog.at_level("WARNING"):
        assert RenderDeployer(str(tmp_path), {"start_command": command}).deploy() is True
    assert "development server" in caplog.text
    assert fake_http["calls"][0]["json"]["serviceDetails"]["envSpecificDetails"]["startCommand"] == command


def test_render_production_command_gets_no_warning(tmp_path, fake_cli, fake_http, monkeypatch, caplog):
    monkeypatch.setenv("RENDER_API_KEY", SECRET)
    monkeypatch.setenv("RENDER_OWNER_ID", "own-1")
    _render_git_responses(fake_cli)
    fake_http["queue"].append(FakeResponse(201, {"service": {"id": "srv-1"}}))

    with caplog.at_level("WARNING"):
        deployer = RenderDeployer(str(tmp_path), {"start_command": "gunicorn wsgi:app"})
        assert deployer.deploy() is True
    assert "development server" not in caplog.text


def test_render_redeploy_does_not_need_start_command(tmp_path, fake_cli, fake_http, monkeypatch):
    monkeypatch.setenv("RENDER_API_KEY", SECRET)
    _render_git_responses(fake_cli)
    fake_http["queue"].extend([FakeResponse(201, {}), FakeResponse(200, {})])

    assert RenderDeployer(str(tmp_path), {"render_service_id": "srv-9"}).deploy() is True


def test_render_dry_run_warns_when_start_command_missing(tmp_path, fake_cli, fake_http, monkeypatch, caplog):
    monkeypatch.delenv("RENDER_API_KEY", raising=False)
    monkeypatch.delenv("RENDER_OWNER_ID", raising=False)

    with caplog.at_level("WARNING"):
        assert RenderDeployer(str(tmp_path), dry_run=True).deploy() is True
    assert "start_command" in caplog.text
    assert fake_http["calls"] == []

def test_render_redeploys_configured_service(tmp_path, fake_cli, fake_http, monkeypatch):
    monkeypatch.setenv("RENDER_API_KEY", SECRET)
    _render_git_responses(fake_cli)
    fake_http["queue"].extend(
        [
            FakeResponse(201, {}),
            FakeResponse(200, {"serviceDetails": {"url": "https://app.onrender.com"}}),
        ]
    )
    deployer = RenderDeployer(str(tmp_path), {"render_service_id": "srv-9"})

    assert deployer.deploy() is True
    assert fake_http["calls"][0]["method"] == "POST"
    assert fake_http["calls"][0]["url"].endswith("/services/srv-9/deploys")
    assert deployer.deployed_url == "https://app.onrender.com"


def test_render_api_error_hides_key(tmp_path, fake_cli, fake_http, monkeypatch, caplog):
    monkeypatch.setenv("RENDER_API_KEY", SECRET)
    monkeypatch.setenv("RENDER_OWNER_ID", "own-1")
    _render_git_responses(fake_cli)
    fake_http["queue"].append(FakeResponse(401, text=f"bad token {SECRET}"))

    with caplog.at_level("ERROR"):
        assert RenderDeployer(str(tmp_path), {"start_command": "gunicorn app:app"}).deploy() is False
    assert SECRET not in caplog.text
    assert "HTTP 401" in caplog.text


def test_render_missing_key_never_calls_api(tmp_path, fake_cli, fake_http, monkeypatch):
    monkeypatch.delenv("RENDER_API_KEY", raising=False)
    assert RenderDeployer(str(tmp_path)).deploy() is False
    assert fake_http["calls"] == []
    assert fake_cli.calls == []


def test_render_dry_run_makes_no_requests(tmp_path, fake_cli, fake_http, monkeypatch):
    monkeypatch.delenv("RENDER_API_KEY", raising=False)
    monkeypatch.delenv("RENDER_OWNER_ID", raising=False)

    assert RenderDeployer(str(tmp_path), dry_run=True).deploy() is True
    assert fake_http["calls"] == []
    assert fake_cli.calls == []


# --- Render live rollback (REST API) ------------------------------------------


def _deploy(deploy_id, status, created, trigger="new_commit", message="change"):
    return {
        "deploy": {
            "id": deploy_id,
            "status": status,
            "createdAt": created,
            "trigger": trigger,
            "commit": {"id": "abc", "message": message},
        },
        "cursor": deploy_id,
    }


def _rollback_deployer(tmp_path, **kwargs):
    return RenderDeployer(str(tmp_path), {"render_service_id": "srv-1"}, **kwargs)


def test_render_rollback_targets_previous_successful_deploy(tmp_path, fake_cli, fake_http, monkeypatch):
    monkeypatch.setenv("RENDER_API_KEY", SECRET)
    fake_http["queue"].extend(
        [
            FakeResponse(
                200,
                [
                    _deploy("dpl-3", "live", "2026-01-03T00:00:00Z"),
                    _deploy("dpl-2", "deactivated", "2026-01-02T00:00:00Z"),
                    _deploy("dpl-1", "deactivated", "2026-01-01T00:00:00Z"),
                ],
            ),
            FakeResponse(201, {"id": "dpl-4"}),
            FakeResponse(200, {"autoDeployTrigger": "commit"}),
        ]
    )

    assert _rollback_deployer(tmp_path).rollback_live() is True
    get_call, post_call, state_call = fake_http["calls"]
    assert get_call["method"] == "GET" and "/services/srv-1/deploys" in get_call["url"]
    assert post_call["method"] == "POST" and post_call["url"].endswith("/services/srv-1/rollback")
    assert post_call["json"] == {"deployId": "dpl-2"}
    assert state_call["method"] == "GET" and state_call["url"].endswith("/services/srv-1")
    assert not any(c["url"].endswith("/deploys") and c["method"] == "POST" for c in fake_http["calls"])
    assert fake_cli.calls == []


def test_render_rollback_skips_failed_builds(tmp_path, fake_cli, fake_http, monkeypatch):
    monkeypatch.setenv("RENDER_API_KEY", SECRET)
    fake_http["queue"].extend(
        [
            FakeResponse(
                200,
                [
                    _deploy("dpl-4", "build_failed", "2026-01-04T00:00:00Z"),
                    _deploy("dpl-3", "live", "2026-01-03T00:00:00Z"),
                    _deploy("dpl-2", "update_failed", "2026-01-02T12:00:00Z"),
                    _deploy("dpl-1", "deactivated", "2026-01-01T00:00:00Z"),
                ],
            ),
            FakeResponse(201, {}),
            FakeResponse(200, {"autoDeployTrigger": "commit"}),
        ]
    )

    assert _rollback_deployer(tmp_path).rollback_live() is True
    assert fake_http["calls"][1]["json"] == {"deployId": "dpl-1"}


def test_render_rollback_without_previous_deploy_does_nothing(tmp_path, fake_cli, fake_http, monkeypatch, caplog):
    monkeypatch.setenv("RENDER_API_KEY", SECRET)
    fake_http["queue"].append(FakeResponse(200, [_deploy("dpl-1", "live", "2026-01-01T00:00:00Z")]))

    with caplog.at_level("ERROR"):
        assert _rollback_deployer(tmp_path).rollback_live() is False
    assert [c["method"] for c in fake_http["calls"]] == ["GET"]
    assert "No earlier successful deploy" in caplog.text


def test_render_rollback_with_no_deploys_at_all(tmp_path, fake_cli, fake_http, monkeypatch):
    monkeypatch.setenv("RENDER_API_KEY", SECRET)
    fake_http["queue"].append(FakeResponse(200, []))

    assert _rollback_deployer(tmp_path).rollback_live() is False
    assert [c["method"] for c in fake_http["calls"]] == ["GET"]


def test_render_rollback_refuses_to_flip_back_after_a_rollback(tmp_path, fake_cli, fake_http, monkeypatch):
    monkeypatch.setenv("RENDER_API_KEY", SECRET)
    fake_http["queue"].append(
        FakeResponse(
            200,
            [
                _deploy("dpl-3", "live", "2026-01-03T00:00:00Z", trigger="rollback"),
                _deploy("dpl-2", "deactivated", "2026-01-02T00:00:00Z"),
                _deploy("dpl-1", "deactivated", "2026-01-01T00:00:00Z"),
            ],
        )
    )

    assert _rollback_deployer(tmp_path).rollback_live() is False
    assert [c["method"] for c in fake_http["calls"]] == ["GET"]


def test_render_rollback_needs_service_id(tmp_path, fake_cli, fake_http, monkeypatch, caplog):
    monkeypatch.setenv("RENDER_API_KEY", SECRET)

    with caplog.at_level("ERROR"):
        assert RenderDeployer(str(tmp_path)).rollback_live() is False
    assert "render_service_id" in caplog.text
    assert fake_http["calls"] == []


def test_render_rollback_needs_api_key(tmp_path, fake_cli, fake_http, monkeypatch):
    monkeypatch.delenv("RENDER_API_KEY", raising=False)

    assert _rollback_deployer(tmp_path).rollback_live() is False
    assert fake_http["calls"] == []


def test_render_rollback_api_error_is_reported_and_hides_key(tmp_path, fake_cli, fake_http, monkeypatch, caplog):
    monkeypatch.setenv("RENDER_API_KEY", SECRET)
    fake_http["queue"].extend(
        [
            FakeResponse(
                200,
                [
                    _deploy("dpl-2", "live", "2026-01-02T00:00:00Z"),
                    _deploy("dpl-1", "deactivated", "2026-01-01T00:00:00Z"),
                ],
            ),
            FakeResponse(400, text=f"artifact gone {SECRET}"),
        ]
    )

    with caplog.at_level("ERROR"):
        assert _rollback_deployer(tmp_path).rollback_live() is False
    assert "HTTP 400" in caplog.text
    assert SECRET not in caplog.text


def _autodeploy_scenario(tmp_path, fake_http, service_payload):
    fake_http["queue"].extend(
        [
            FakeResponse(
                200,
                [
                    _deploy("dpl-2", "live", "2026-01-02T00:00:00Z"),
                    _deploy("dpl-1", "deactivated", "2026-01-01T00:00:00Z"),
                ],
            ),
            FakeResponse(201, {}),
            FakeResponse(200, service_payload),
        ]
    )
    return _rollback_deployer(tmp_path)


def test_render_rollback_reports_autodeploy_switched_off(tmp_path, fake_cli, fake_http, monkeypatch, caplog):
    """A live test showed Render turns autodeploy off on rollback despite its docs."""
    monkeypatch.setenv("RENDER_API_KEY", SECRET)
    deployer = _autodeploy_scenario(tmp_path, fake_http, {"autoDeployTrigger": "off"})

    with caplog.at_level("WARNING"):
        assert deployer.rollback_live() is True
    assert "Autodeploy is now OFF" in caplog.text


def test_render_rollback_reports_autodeploy_still_on(tmp_path, fake_cli, fake_http, monkeypatch, caplog):
    monkeypatch.setenv("RENDER_API_KEY", SECRET)
    deployer = _autodeploy_scenario(tmp_path, fake_http, {"autoDeployTrigger": "commit"})

    with caplog.at_level("WARNING"):
        assert deployer.rollback_live() is True
    assert "Autodeploy is still on (commit)" in caplog.text


@pytest.mark.parametrize("legacy, expected", [("no", "Autodeploy is now OFF"), ("yes", "Autodeploy is still on")])
def test_render_rollback_reads_legacy_autodeploy_field(
    tmp_path, fake_cli, fake_http, monkeypatch, caplog, legacy, expected
):
    monkeypatch.setenv("RENDER_API_KEY", SECRET)
    deployer = _autodeploy_scenario(tmp_path, fake_http, {"autoDeploy": legacy})

    with caplog.at_level("WARNING"):
        assert deployer.rollback_live() is True
    assert expected in caplog.text


def test_render_rollback_still_succeeds_when_autodeploy_state_is_unreadable(
    tmp_path, fake_cli, fake_http, monkeypatch, caplog
):
    monkeypatch.setenv("RENDER_API_KEY", SECRET)
    deployer = _autodeploy_scenario(tmp_path, fake_http, {})

    with caplog.at_level("WARNING"):
        assert deployer.rollback_live() is True
    assert "Could not read the autodeploy setting" in caplog.text


def test_render_rollback_dry_run_makes_no_requests(tmp_path, fake_cli, fake_http, monkeypatch):
    monkeypatch.delenv("RENDER_API_KEY", raising=False)

    assert _rollback_deployer(tmp_path, dry_run=True).rollback_live() is True
    assert fake_http["calls"] == []


def test_render_rollback_method_never_redeploys_current_code(tmp_path, fake_cli, fake_http, monkeypatch):
    """The old behavior called deploy(), which could create a new service."""
    monkeypatch.setenv("RENDER_API_KEY", SECRET)
    fake_http["queue"].append(FakeResponse(200, []))

    assert _rollback_deployer(tmp_path).rollback({"platform": "render"}) is False
    assert [c["method"] for c in fake_http["calls"]] == ["GET"]
    assert fake_cli.calls == []


def test_platforms_without_live_rollback_say_so(tmp_path, fake_cli, caplog):
    with caplog.at_level("ERROR"):
        assert VercelDeployer(str(tmp_path)).rollback_live() is False
    assert "not supported" in caplog.text
    assert VercelDeployer.supports_live_rollback is False
    assert RenderDeployer.supports_live_rollback is True
    assert fake_cli.calls == []


def _write_project(tmp_path, with_record=True):
    (tmp_path / "deployment.yaml").write_text(
        "platform: render\nstart_command: gunicorn app:app\nrender_service_id: srv-1\n", encoding="utf-8"
    )
    if with_record:
        record = tmp_path / ".deployment"
        record.mkdir()
        (record / "render_1.json").write_text(
            '{"id": "render_1", "platform": "render", "timestamp": "2026-01-01T00:00:00+00:00"}',
            encoding="utf-8",
        )


def test_deployer_rollback_live_uses_platform_from_latest_record(tmp_path, fake_cli, fake_http, monkeypatch):
    from multi_platform_deployer import Deployer

    monkeypatch.setenv("RENDER_API_KEY", SECRET)
    _write_project(tmp_path)
    fake_http["queue"].extend(
        [
            FakeResponse(
                200,
                [
                    _deploy("dpl-2", "live", "2026-01-02T00:00:00Z"),
                    _deploy("dpl-1", "deactivated", "2026-01-01T00:00:00Z"),
                ],
            ),
            FakeResponse(201, {}),
            FakeResponse(200, {"autoDeployTrigger": "commit"}),
        ]
    )

    assert Deployer(str(tmp_path)).rollback_live() is True
    assert fake_http["calls"][1]["json"] == {"deployId": "dpl-1"}


def test_deployer_rollback_live_without_records_fails_cleanly(tmp_path, fake_cli, fake_http, monkeypatch):
    from multi_platform_deployer import Deployer

    monkeypatch.setenv("RENDER_API_KEY", SECRET)
    _write_project(tmp_path, with_record=False)

    assert Deployer(str(tmp_path)).rollback_live() is False
    assert fake_http["calls"] == []
