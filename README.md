# Multi-Platform Deployer

[![PyPI - Version](https://img.shields.io/pypi/v/multi-platform-deployer.svg)](https://pypi.org/project/multi-platform-deployer/)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/multi-platform-deployer.svg?label=pip%20installs)](https://pypi.org/project/multi-platform-deployer/)

A command-line tool that checks a Flask, Django or FastAPI project for deployment problems and then deploys it to Render, Vercel, Railway or Heroku with one command.

It does three things:

- **Checks** the project before deploying (secret key, debug mode, pinned dependencies, git state, and so on).
- **Deploys** it by calling each platform's own API or CLI.
- **Verifies** the result with a health check, and can roll back on Render.

It does not provision databases, and it does not upload secrets. You set those in each platform's dashboard.

## What you can do with it

| Task | Command | Status |
|------|---------|--------|
| Check a Python web app before deploying it | `multi-platform-deployer check` | Works for Flask, Django and FastAPI |
| Deploy a Flask app to Render | `multi-platform-deployer run --platform render` | Verified live |
| Deploy a Django or FastAPI app to Render | `multi-platform-deployer run --platform render` | Not yet verified live |
| Deploy a Flask, Django or FastAPI app to Vercel | `multi-platform-deployer run --platform vercel` | Not yet verified live |
| Deploy a Python app to Railway or Heroku | `multi-platform-deployer run --platform railway` or `--platform heroku` | Experimental |
| Preview a deployment without changing anything | add `--dry-run` | Works on all platforms |
| Check that a deployed app is up | `multi-platform-deployer health --url <url>` | Works on any URL |
| Roll back a Render deployment from the command line | `multi-platform-deployer rollback --live` | Verified live |

## Status

Only what has been run against a real account is listed as verified. Everything else is implemented and covered by mocked tests, but has not been run live.

| Platform | Status | What has been run live |
|----------|--------|------------------------|
| Render | Verified | Flask: create service, build, health check, redeploy, live rollback. Django and FastAPI: not yet. |
| Vercel | Not verified | Nothing yet. |
| Railway | Experimental | Nothing. Not tested yet. |
| Heroku | Experimental | Nothing. Not tested yet. |

Tests run in CI on Python 3.11 to 3.14, on Linux and Windows. Use a throwaway app for your first real deploy.

## Requirements

- Python 3.11 or newer
- `git`
- For Vercel: Node.js and the Vercel CLI (`npm install -g vercel`)
- For Railway: the Railway CLI (`npm install -g @railway/cli`)
- For Heroku: the Heroku CLI
- Render needs nothing extra; it is called through its REST API.

## Install

```bash
pip install multi-platform-deployer
```

This installs the `multi-platform-deployer` command. You can also run it as `python -m multi_platform_deployer.cli`.

To work on the source:

```bash
git clone https://github.com/Badee2000/multi-platform-deployer.git
cd multi-platform-deployer
python -m venv .venv
.venv\Scripts\activate        # macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"
```

## Quick start

Run these from your project folder.

```bash
multi-platform-deployer setup                      # create deployment.yaml
multi-platform-deployer check                      # readiness checks
multi-platform-deployer run --platform render --dry-run   # preview, changes nothing
multi-platform-deployer run --platform render      # deploy
multi-platform-deployer health --url https://your-app.onrender.com
```

A real deploy needs a credential for the platform, set as an environment variable in the same terminal. See [Platforms](#platforms).

## Commands

| Command | What it does |
|---------|--------------|
| `setup` | Asks for platform, app name and start command, and writes `deployment.yaml` (or `deployment.json`). Can save secrets to a local `.env` and adds `.env` to `.gitignore`. |
| `check` | Runs the readiness checks for the detected framework. Exits non-zero if the project is not ready. |
| `run` | Deploys. Interactive by default. |
| `info` | Shows the detected framework and project details. |
| `health` | Sends requests to a deployed app and reports whether it is up. |
| `rollback` | Restores the previous project files, or with `--live` rolls back the running Render service. |

Options:

| Option | Applies to | Meaning |
|--------|-----------|---------|
| `--platform NAME` | `run`, `rollback --live` | `render`, `railway`, `vercel` or `heroku`. Skips the prompts. |
| `--dry-run` | `run`, `rollback --live` | Print what would happen. Nothing is executed or changed. Missing credentials are warnings in this mode. |
| `--migrate` | `run --platform` | Run Django or Alembic migrations before deploying. |
| `--multi` | `run` | Deploy to several platforms, one after another (interactive). A failure on one does not roll back the others. |
| `--live` | `rollback` | Roll back the running service. Render only. |
| `--url URL` | `health` | The deployed app's URL. |
| `--endpoints PATHS` | `health` | Comma-separated paths to request. Default `/`. |

All commands exit non-zero when they fail, so they can be used in scripts and CI.

## Configuration

Put a `deployment.yaml` in the project root. `deployment.json`, `deployment.yml` and the dot-prefixed variants also work.

```yaml
platform: render
app_name: my-app
start_command: gunicorn wsgi:app
```

| Key | Used by | Meaning |
|-----|---------|---------|
| `platform` | all | `render`, `railway`, `vercel` or `heroku`. Required. |
| `app_name` | all | Required. On Render it becomes the service name (lowercase letters, digits and hyphens). |
| `start_command` | Render, Railway, Heroku | The production command that starts your app. Required for the first Render deploy. On Railway and Heroku it is only used to create `railway.json` or a `Procfile` when you have none. |
| `render_service_id` | Render | Set after the first deploy so later runs update the same service. |
| `render_plan` | Render | Instance plan. Default `free`. |
| `render_region` | Render | Default `oregon`. |
| `railway_project`, `railway_environment`, `railway_service` | Railway | Passed to `railway up` as `--project`, `--environment` and `--service`. |

Keys that are not listed here are ignored.

Credentials are never read from this file. Use environment variables, set in the terminal you deploy from:

```powershell
$env:RENDER_API_KEY = Read-Host "Render API key"     # PowerShell
```
```bash
read -s -p "Render API key: " RENDER_API_KEY && export RENDER_API_KEY    # macOS / Linux
```

An environment variable exists only in the terminal where you set it. A new terminal window needs it set again.

## Platforms

### Render

Status: verified with Flask. Not yet verified with Django or FastAPI.

```bash
multi-platform-deployer run --platform render
```

- Uses the Render REST API. Credential: `RENDER_API_KEY`. If your account has more than one workspace, also set `RENDER_OWNER_ID`.
- Render builds from your git remote, not your local folder. The project must have an `origin` remote, a clean working tree, and no unpushed commits. The deploy refuses to run otherwise.
- The first deploy creates a free web service with auto-deploy on new commits. Build command: `pip install -r requirements.txt`.
- `start_command` is required for the first deploy. There is no default because Flask, Django and FastAPI start differently. The deploy stops before any API call if it is missing. Dev-server commands such as `python app.py`, `flask run` and `runserver` are accepted with a warning.

  | Framework | Typical `start_command` |
  |-----------|------------------------|
  | Flask | `gunicorn wsgi:app` |
  | Django | `gunicorn <project>.wsgi:application` |
  | FastAPI | `uvicorn main:app --host 0.0.0.0 --port $PORT` |

  Add the server (`gunicorn` or `uvicorn`) to `requirements.txt`.
- The first run prints the service ID. Add it to `deployment.yaml` as `render_service_id`, commit, and push. Later runs then redeploy that service instead of creating another.

### Vercel

Status: not yet verified live.

```bash
multi-platform-deployer run --platform vercel
```

- Runs `vercel deploy --prod --yes`. Credential: `VERCEL_TOKEN`. The Vercel CLI also reads `VERCEL_ORG_ID` and `VERCEL_PROJECT_ID` if you set them.
- Deploys your local folder, not a git commit.
- No `vercel.json` is generated. Vercel detects Flask, FastAPI and Django on its own. An existing `vercel.json` is left alone.
- Vercel needs an entry point it recognizes: `app.py`, `index.py`, `server.py`, `main.py`, `wsgi.py` or `asgi.py` (also under `src/` or `app/`), or a Django `manage.py`. The file must define `app` (Flask, FastAPI) or `application` (Django).
- Vercel supports Python 3.12 (default), 3.13 and 3.14. Set the version in `.python-version`.
- Functions run serverless with a read-only filesystem. Do not write to SQLite on Vercel.
- Environment variables must exist before the build when your settings need them at import time. Set them in the project's Environment Variables settings or with `vercel env add`.

### Railway

Status: experimental. Not run against a real account.

```bash
multi-platform-deployer run --platform railway
```

- Runs `railway up --ci`. Credential: `RAILWAY_TOKEN`, a project token created in the Railway project's settings. Do not also set `RAILWAY_API_TOKEN`: Railway rejects that combination, so the tool removes it for the run.
- The project, environment and service must already exist. Railway does not create projects in CI.
- Deploys your local folder.
- Your `Procfile` or `railway.json` decides how the app starts. If you have neither and set `start_command`, a `railway.json` is generated from it. No command is guessed.
- The command does not print a public URL. Run `railway domain` or check the dashboard.
- Not confirmed: whether the project token alone is enough without `railway link`. If the CLI cannot find the project, set `railway_project`, `railway_environment` and `railway_service`.

### Heroku

Status: experimental. Not run against a real account.

```bash
multi-platform-deployer run --platform heroku
```

- Credential: `HEROKU_API_KEY`. The tool runs `heroku auth:whoami`, then `git push heroku HEAD:main`.
- Heroku builds from the git commit. The project needs a clean working tree, a `heroku` remote over HTTPS (`heroku git:remote -a <app>`), and a `Procfile`. If you have no `Procfile` but set `start_command`, one is created and you must commit it before running again.
- The push authenticates through a temporary git credential helper that reads `HEROKU_API_KEY` from the environment. The key does not appear in the command line, and `heroku login` is not required. This has been tested with mocks only.
- Pin the Python version as `3.12` (major.minor) in `.python-version`. Heroku supports only the latest patch release of each version.

## Walkthrough: Flask on Render

This is the flow that was run live. Use a throwaway app. Commands are PowerShell; on macOS or Linux set variables with `export`.

1. **Prepare the app.** `requirements.txt` lists your server (for example `Flask==3.1.3` and `gunicorn==26.2.0`). Read secrets from the environment, for example `SECRET_KEY = os.environ["SECRET_KEY"]`. Add `.env` and `.deployment/` to `.gitignore`.
2. **Add `deployment.yaml`.**
   ```yaml
   platform: render
   app_name: my-flask-app
   start_command: gunicorn wsgi:app
   ```
3. **Push to GitHub.** A public repo needs no extra setup. For a private repo, connect GitHub to your Render account first (not tested here).
   ```powershell
   git remote add origin https://github.com/<you>/<repo>.git
   git push -u origin main
   ```
4. **Create an API key** in Render under Account Settings, API Keys. Set it in your terminal and keep it out of project files, chats and issues. If it leaks, revoke it and create a new one.
   ```powershell
   $env:RENDER_API_KEY = Read-Host "Render API key"
   ```
5. **Check and preview.**
   ```powershell
   multi-platform-deployer check
   multi-platform-deployer run --platform render --dry-run
   ```
6. **Deploy.**
   ```powershell
   multi-platform-deployer run --platform render
   ```
   The output includes the service ID and URL:
   ```
   Created Render service srv-xxxxxxxxxxxxxxxxxxxx.
   URL: https://my-flask-app.onrender.com
   ```
7. **Set secrets in Render.** Open the service, go to Environment, and add `SECRET_KEY` and anything else the app reads. Saving redeploys. Until then, an app that requires `SECRET_KEY` builds but fails on start.
8. **Check health** once the service shows Live. Free-plan services sleep when idle, so the first request can be slow.
   ```powershell
   multi-platform-deployer health --url https://my-flask-app.onrender.com
   ```
9. **Redeploy later.** Add `render_service_id: srv-xxxxxxxxxxxxxxxxxxxx` to `deployment.yaml`, commit, push, and run step 6 again.
10. **Clean up.** Delete the service in the dashboard so it stops running, and revoke the API key if you made it only for this test.

## Readiness checks

`check` runs system checks for every project, then checks for the framework it detects.

System checks:

- A Python version is declared (`runtime.txt`, `.python-version`, `pyproject.toml` or `Pipfile`).
- Most dependencies in `requirements.txt` are version-pinned.
- A deployment config file exists.
- `.env` or `.env.example` exists, and `.env` has no placeholder secrets.
- The git working tree is clean. The tool's own `.deployment/` folder is ignored.

Framework checks:

| Framework | Checks |
|-----------|--------|
| Flask | `requirements.txt`, app entry point, WSGI app, `SECRET_KEY` from the environment, debug not hardcoded, error handlers, database settings |
| Django | `manage.py`, security settings, static files, database, `SECRET_KEY`, `ALLOWED_HOSTS`, `DEBUG` |
| FastAPI | app instance, production ASGI server in requirements, CORS, middleware, exception handlers, database settings |

The framework is detected from `manage.py` and from imports in `app.py`, `main.py` and `wsgi.py`. If detection fails, the command asks.

## Health checks

```bash
multi-platform-deployer health --url https://my-app.example.com --endpoints "/,/health"
```

- The server counts as up when the base URL answers with any status below 500. A `/health` route is not required.
- Each endpoint is requested, and its real status code is reported, including 404 and 500.
- The command tries up to 10 times with a capped backoff, so a server that is down takes a few minutes to report. It exits non-zero if the server is down.
- Database connectivity is not checked. It is reported as `NOT CHECKED`.

A response below 500 includes 401 and 403. If a platform puts the app behind a login page, the check still reports the server as up. Request an endpoint that returns the status you expect.

## Rollback

**Live rollback (Render only):**

```bash
multi-platform-deployer rollback --live --dry-run    # preview the API calls
multi-platform-deployer rollback --live              # asks for confirmation first
```

- Calls Render's rollback API to put the service back on its most recent earlier successful deploy. Render reuses the old build, so it takes seconds.
- Needs `RENDER_API_KEY` and `render_service_id`. Local files are not touched.
- Failed builds are skipped.
- If the live deploy is itself a rollback, the command stops instead of switching back to the bad build. Pick a deploy in the dashboard (service, Deploys) instead.
- If there is no earlier successful deploy, or Render no longer keeps its build, nothing changes and the command exits non-zero.
- **Render may turn auto-deploy off.** Render's API documentation says a rollback leaves it alone, but in all three live tests it was switched off. After a rollback the tool reads the service and prints the real state. If it is off, new commits do not deploy until you turn it back on under Settings, Auto-Deploy. If it is still on, the next commit deploys again and can undo the rollback.
- Verified live with Flask: a deploy serving `"version":"v2"` was rolled back to the previous code in about 20 seconds.

**File rollback (any platform):**

```bash
multi-platform-deployer rollback
```

After every successful deploy the tool snapshots the project files into `.deployment/` (`.env` files are excluded). This command restores the snapshot from the deploy before the latest one. It restores files only. The running deployment is not changed, so you must redeploy.

On Vercel, Railway and Heroku, `rollback --live` prints "not supported" and exits non-zero. Use the platform's dashboard or CLI.

## Migrations

`run --platform <name> --migrate` (or "yes" in the interactive prompt) runs migrations before deploying:

- Django: `python manage.py migrate`
- Alembic: `alembic upgrade head`

If a migration fails, nothing is deployed. Other migration tools are not run.

## Python API

```python
from multi_platform_deployer.main import Deployer

deployer = Deployer("./my_project")

is_ready, results = deployer.check_deployment_readiness("flask")
if not is_ready:
    for result in results:
        if not result.passed:
            print(f"{result.name}: {result.message}")
    raise SystemExit(1)

if not deployer.deploy("render", run_migrations=False):
    raise SystemExit(1)

deployer.check_health("https://my-app.onrender.com", endpoints=["/", "/health"])
```

`Deployer(path, dry_run=True)` prints the steps without running them. `deployer.rollback_live()` is the API form of `rollback --live`.

## Security

- Credentials are read only from environment variables. They are never accepted on the command line, so they do not show up in process lists or shell history.
- Credentials are removed from logged command output and error messages.
- The wizard writes secrets only to a local `.env` with owner-only permissions where the OS supports it, and adds `.env` to `.gitignore`.
- The tool never uploads `.env` or other secrets to a platform.
- A dry run never calls a platform API or runs a platform CLI.

## Limitations

- Only Render has been run live, and only with a Flask app. Vercel, Railway and Heroku are implemented and mock-tested only.
- Live rollback exists for Render only.
- Secrets and environment variables are not uploaded. Set them in each platform's dashboard.
- The tool does not create databases.
- `run` does not run a health check on its own. Run `health` afterwards.
- Railway does not print a public URL after deploying.
- `--multi` does not undo a successful deploy when another platform fails.

## Examples

Small apps used to test the tool. Each has a `Procfile`, pinned requirements, a `deployment.yaml` and tests of its own.

| Framework | Repository | Deployed |
|-----------|------------|----------|
| Flask | [mpd-flask-example](https://github.com/Badee2000/mpd-flask-example) | Render |
| Django | [mpd-django-example](https://github.com/Badee2000/mpd-django-example) | Not yet |
| FastAPI | [mpd-fastapi-example](https://github.com/Badee2000/mpd-fastapi-example) | Not yet |

The `examples/` folder in this repository holds minimal starter files. They have not been deployed.

## Troubleshooting

**`RENDER_API_KEY is not set` (or another token).** The variable is not set in this terminal. Set it again in the window you are running from.

**`No 'start_command' in your config`.** Add `start_command` to `deployment.yaml`, for example `gunicorn wsgi:app`, and put `gunicorn` in `requirements.txt`.

**`Uncommitted changes would not be deployed`, or commits not pushed.** Render and Heroku deploy committed code. Run `git status`, commit, and `git push`.

**The Render service was created but the app does not start.** Open the service's Logs. A missing environment variable is the usual cause. Add it under Environment. Saving redeploys.

**`Could not auto-detect framework`.** Detection looks for `manage.py` or imports in `app.py`, `main.py` and `wsgi.py`. The command asks you to choose when it fails.

**Health check says the server is down.** Check that the deploy has finished, that the app listens on the port the platform provides (`$PORT`), and that the app does not start a dev server from an `if __name__ == "__main__":` block.

**A Django migration failed.** Check that the database is reachable and `DATABASE_URL` is set. The deploy was stopped, so nothing was deployed. Fix the migration and run again.

**`ModuleNotFoundError: No module named 'yaml'`.** Install the package again with `pip install multi-platform-deployer`, or `pip install -e .` from a source checkout.

## Testing

```bash
pip install -e ".[dev]"
pytest
mypy src
```

The suite runs 200 tests with mocks and temporary directories. It never deploys anything. Five tests are skipped unless you opt in to live credential checks, which are read-only (who am I, list owners):

```bash
MPD_LIVE_TESTS=1 RENDER_API_KEY=... pytest tests/test_live_deploy.py -v
```

Each platform's live test is skipped on its own when its token or CLI is missing.

## Project layout

```
src/multi_platform_deployer/
    cli.py             command-line interface
    main.py            Deployer class
    deployers/         one module per platform
    checkers/          system, Flask, Django and FastAPI checks
    config/            loading and validating deployment.yaml
    scripts/           migrations, health check, rollback snapshots
    utils/             command execution, logging, helpers
tests/                 test suite
examples/              minimal starter files
```

## Contributing

Issues and pull requests are welcome. Run `pytest` and `mypy src` before opening a pull request. Do not run real deployments from tests: use mocks and temporary directories.

## License

MIT. See [LICENSE](LICENSE).
