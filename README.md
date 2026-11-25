# Multi-Platform Deployer

[![PyPI - Version](https://img.shields.io/pypi/v/multi-platform-deployer.svg)](https://pypi.org/project/multi-platform-deployer/)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/multi-platform-deployer.svg?label=pip%20installs)](https://pypi.org/project/multi-platform-deployer/)
[![XERJ Corpus Hub contributor](https://hub.xerj.org/contributors/Badee2000/badge.svg)](https://hub.xerj.org/contributors/Badee2000)

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
| Deploy a Django app to Render | `multi-platform-deployer run --platform render` | Verified live |
| Deploy a FastAPI app to Render | `multi-platform-deployer run --platform render` | Verified live |
| Deploy a Flask app to Vercel | `multi-platform-deployer run --platform vercel` | Verified live |
| Deploy a Django or FastAPI app to Vercel | `multi-platform-deployer run --platform vercel` | Not yet verified live |
| Deploy a Python app to Railway or Heroku | `multi-platform-deployer run --platform railway` or `--platform heroku` | Experimental |
| Preview a deployment without changing anything | add `--dry-run` | Works on all platforms |
| Check that a deployed app is up | `multi-platform-deployer health --url <url>` | Works on any URL |
| Roll back a Render deployment from the command line | `multi-platform-deployer rollback --live` | Verified live |
| Roll back a Vercel deployment from the command line | `multi-platform-deployer rollback --live --platform vercel` | Verified live |

## Status

Only what has been run against a real account is listed as verified. Everything else is implemented and covered by mocked tests, but has not been run live.

| Platform | Status | What has been run live |
|----------|--------|------------------------|
| Render | Verified | Flask, Django and FastAPI: first deploy, health check, redeploy and live rollback. |
| Vercel | Partly verified | Flask: first production deploy, redeploy, a failed build (exit 1, live app untouched) and live rollback (v2 back to v1). Django and FastAPI not run yet. |
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

The output is plain text. `check` lists every result, and `run` prints one line per step:

```
$ multi-platform-deployer check

Readiness check
---------------
Detected framework: django

  [ok  ] Python runtime: .python-version -> 3.12.10
  [ok  ] Dependency pinning: 2/2 dependencies pinned
  [FAIL] Secret key: SECRET_KEY configuration not found

1 check(s) failed. Fix them before deploying.
```

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
| `--live` | `rollback` | Roll back the running service. Render and Vercel. |
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
| `render_wait_timeout` | Render | Seconds `run` waits for the deploy to go live. Default `900`. `0` means do not wait. |
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

Status: verified live with Flask, Django and FastAPI (see [Status](#status)).

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
- Because the service is created with auto-deploy on, every push to the linked branch already deploys on Render. Running `run` on an existing service then starts a second deploy of the same commit. The tool does not change this Render setting. It is still useful for the first deploy, the readiness checks, health checks and live rollback.
- `run` waits for the deploy to go live and prints each status change. It exits non-zero if the build fails, the deploy is canceled or replaced, the status cannot be read, or `render_wait_timeout` passes. After an unreadable status or a timeout the deploy may still finish on Render. The tool never retries a deploy.

  Run live: a redeploy that waited until live, a deliberately broken build (`build_failed`, exit code 1, the live app kept the old code), a 5 second timeout (exit code 1, the deploy kept running on Render), and the wait after the first deploy. Canceled or replaced deploys and an unreadable status are covered by mocked tests only.

### Vercel

Status: verified live with Flask only (see [Status](#status)). Django and FastAPI have not been run.

```bash
multi-platform-deployer run --platform vercel
```

- Runs `vercel deploy --prod --yes`. Credential: `VERCEL_TOKEN`. Create it with the scope set to your whole account, because a token limited to one team or project fails with `User not found` in some commands (see [Troubleshooting](#vercel-1)). The Vercel CLI also reads `VERCEL_ORG_ID` and `VERCEL_PROJECT_ID` if you set them.
- Deploys your local folder, not a git commit.
- No `vercel.json` is generated. Vercel detects Flask, FastAPI and Django on its own. An existing `vercel.json` is left alone.
- Vercel needs an entry point it recognizes: `app.py`, `index.py`, `server.py`, `main.py`, `wsgi.py` or `asgi.py` (also under `src/` or `app/`), or a Django `manage.py`. The file must define `app` (Flask, FastAPI) or `application` (Django).
- Vercel supports Python 3.12 (default), 3.13 and 3.14. Set the version in `.python-version`.
- Functions run serverless with a read-only filesystem. Do not write to SQLite on Vercel.
- Build failed, login redirect, 500 errors and rollback problems are explained in [Troubleshooting](#vercel-1).
- New Vercel projects have Deployment Protection on by default, so the deployment URL redirects visitors to a Vercel login page. `health --url` detects the redirect to another host and reports a failure instead of "up". To check the real app, use `vercel curl /health --deployment <url>`, or turn the protection off in the project's settings.
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
   The output includes the service ID, the build status and the URL:
   ```
   Created Render service srv-xxxxxxxxxxxxxxxxxxxx.
   Deploy dep-xxxxxxxxxxxxxxxxxxxx: build_in_progress
   Deploy dep-xxxxxxxxxxxxxxxxxxxx: live
   Deployed to render.
   URL: https://my-flask-app.onrender.com
   Check it: multi-platform-deployer health --url https://my-flask-app.onrender.com
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
- `--url` is the base URL of the app. The endpoints are appended to it, so use `--url https://my-app.example.com --endpoints /health/`, not the full health URL.
- Each endpoint is requested, and its real status code is reported, including 404 and 500.
- The command tries up to 10 times with a capped backoff, so a server that is down takes a few minutes to report. It exits non-zero if the server is down.
- Database connectivity is not checked. It is reported as `not checked`.

A response below 500 includes 401 and 403, so a login page that answers 401 or 403 still counts as up. A redirect to a different host (such as the login page of a protected Vercel deployment) is reported as a failure, because the app was not reached. See [Troubleshooting](#troubleshooting).

## Rollback

**Live rollback (Render and Vercel):**

```bash
multi-platform-deployer rollback --live --dry-run    # preview the API calls
multi-platform-deployer rollback --live              # asks for confirmation first
```

For Vercel, add `--platform vercel` if the project has no deployment record yet. Details for Render:
- Calls Render's rollback API to put the service back on its most recent earlier successful deploy. Render reuses the old build, so it takes seconds.
- Needs `RENDER_API_KEY` and `render_service_id`. Local files are not touched.
- Failed builds are skipped.
- If the deploy you are rolling back to was built from the same commit as the live one, the tool warns that the running code will not change. It still proceeds.
- If the live deploy is itself a rollback, the command stops instead of switching back to the bad build. Pick a deploy in the dashboard (service, Deploys) instead.
- If there is no earlier successful deploy, or Render no longer keeps its build, nothing changes and the command exits non-zero.
- **Render may turn auto-deploy off.** Render's API documentation says a rollback leaves it alone, but in all four live tests it was switched off. After a rollback the tool reads the service and prints the real state. If it is off, new commits do not deploy until you turn it back on under Settings, Auto-Deploy. If it is still on, the next commit deploys again and can undo the rollback.
- Verified live with Flask: a deploy serving `"version":"v2"` was rolled back to the previous code in about 20 seconds. Verified live with Django: a deploy serving `"version": 3` was rolled back to version 2. Verified live with FastAPI: the same, from version 3 back to version 2.

**Live rollback on Vercel** (verified live with Flask: production went from v2 back to v1):

- The tool lists your successful (`READY`) production deployments with `vercel list`, picks the **second newest**, and runs `vercel rollback <that-url> --yes --timeout 3m`. Vercel reuses the old build, so nothing is rebuilt. Needs `VERCEL_TOKEN` (full-account scope, see [Troubleshooting](#vercel-1)).
- It passes the target explicitly because `vercel rollback` without one did nothing when the newest production deployment had failed to build: the command reported success and production kept serving the same version.
- It stops without changing anything when fewer than two successful production deployments exist.
- On the Hobby plan Vercel only allows going back to the previous production deployment. Pro and Enterprise can go further back, but this tool always picks the second newest.
- After a rollback Vercel stops putting new deployments on your production domain. Run `vercel promote <deployment-url>` to resume normal deploys. The tool prints this reminder.
- The tool never retries a rollback. If a command fails, production was not changed by this tool.

**File rollback (any platform):**

```bash
multi-platform-deployer rollback
```

After every successful deploy the tool snapshots the project files into `.deployment/` (`.env` files are excluded). This command restores the snapshot from the deploy before the latest one. It restores files only. The running deployment is not changed, so you must redeploy.

On Railway and Heroku, `rollback --live` prints "not supported" and exits non-zero. Use the platform's dashboard or CLI.

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

## Troubleshooting

Each entry starts with the message you see, then says why it happens and how to fix it. Messages marked "(not yet seen live)" come from the code and mocked tests, not from a real run. The tool never retries a failed deploy, so check the platform dashboard before running it again.

### Any platform

**`<NAME> is not set. Export it in your shell before deploying to <platform>.`**
Why: the token (`RENDER_API_KEY`, `VERCEL_TOKEN`, `RAILWAY_TOKEN` or `HEROKU_API_KEY`) is not in this terminal's environment. A variable set in one terminal window does not exist in another.
Fix: set it in the same terminal you deploy from, for example `$env:VERCEL_TOKEN = Read-Host "Vercel token"` in PowerShell. In a dry run this is only a warning.

**`'vercel' was not found on PATH. Install it and try again.`** (same for `railway` and `heroku`)
Why: the platform's CLI is not installed, or the terminal was opened before it was installed.
Fix: install it (`npm install -g vercel`), open a new terminal, and check `vercel --version`.

**`Command failed (exit 1): vercel deploy --prod --yes`** followed by the CLI's own output
Why: the platform CLI refused or failed. The reason is the text after this line. Tokens in that text are replaced with `***`.
Fix: read the CLI output below the line and look it up here. The tool exits with code 1.

**`Timed out after 900s`**
Why: one step (a CLI call) took longer than 15 minutes, so the tool stopped it.
Fix: check the platform dashboard. The deploy may still have finished. Do not run again until you know.

**`[FAIL] WSGI application: WSGI application not properly configured`**
Why: versions up to 0.4.0 only accepted a `wsgi.py` file. An app whose `app.py` or `main.py` defines `app` at module level, which is what Vercel expects, was rejected.
Fix: use version 0.5.0 or newer (the check also accepts `app.py` and `main.py` that define `app` or `application` at module level), or add a `wsgi.py` containing `from app import app`.

**`[FAIL] Secret key: SECRET_KEY configuration not found`**
Why: the app does not read `SECRET_KEY` from the environment.
Fix: read it with `os.environ["SECRET_KEY"]` (Flask) or from the environment in Django settings, and set the value in the platform's dashboard.

**I pasted a token or secret into a file, chat or issue.**
Why: anyone who sees it can use your account.
Fix: revoke it now (Account Settings, Tokens or API Keys on the platform) and create a new one. Remove it from the file, for example `.env.example`, which is a public template and must only hold placeholders. If it was committed, rotating the secret matters more than rewriting git history.

### Vercel

**`Error: User not found. (404)`** from `vercel rollback` or `vercel whoami`. Seen live.
Why: the `VERCEL_TOKEN` was created with a Team or single-project scope. The Vercel CLI starts by asking for the user behind the token, and a scoped token is not allowed to ask, so it gets a 404. A browser login (`vercel login`) works with the same project, which makes this confusing. `vercel rollback` fails with it. Other commands may or may not, depending on the CLI version.
Fix: create a new token under Account Settings, Tokens with the scope set to your whole account (not a team or project), set `VERCEL_TOKEN` again, and check it with `vercel whoami`, which should print your username. Give the token a short expiry and revoke it when you are done. Source: a Vercel community thread on this behavior (Vercel has not documented it as of this writing).

**`vercel rollback` says it succeeded but production still serves the same version.** Seen live.
Why: `vercel rollback` run without a deployment goes back one step from the newest production deployment. If that newest deployment failed to build (it shows as `Error` in `vercel ls`), "one step back" is the deployment that is already live, so nothing changes. The tool's own `rollback --live` passes an explicit target since this was found.
Fix: pass the deployment yourself, `vercel rollback https://<older-deployment>.vercel.app`, or use `multi-platform-deployer rollback --live --platform vercel` with a version that has the fix. Always check the production domain afterwards. `vercel alias ls` shows which deployment each domain points to.

**Build fails: `No solution found when resolving dependencies ... was not found in the package registry`**, then `Vercel deployment failed; see the output above.` and `Deployment failed.`, exit code 1. Seen live.
Why: `requirements.txt` lists a package or version that does not exist, usually a typo or a version that was never released. Vercel could not build, so nothing new went live.
What happens: the previous production deployment keeps serving. The failed one is listed as `Error` in `vercel ls`, and the tool saves no deployment state.
Fix: correct the name or version, test with `pip install -r requirements.txt` in a clean virtual environment, commit, and run again.

**`health` fails: `redirected to vercel.com, so the app was not reached`**
Why: new Vercel projects have Deployment Protection on, so visitors are sent to a Vercel login page. Earlier versions counted that page as "up".
Fix: either turn off Vercel Authentication under the project's Settings, Deployment Protection (this makes the app public), or check the app while logged in with `vercel curl /health --deployment <url>`.

**The deploy succeeded but the app shows an error page (HTTP 500)**
Why: the app crashed on start. The usual cause is a setting that is read at import time, such as `SECRET_KEY`, but is not set on Vercel. The tool does not upload secrets.
Fix: add the variable under the project's Settings, Environment Variables, or with `vercel env add SECRET_KEY production` (choose Secret for passwords). Variables only apply to new deployments, so run again. Use `vercel logs <deployment-url>` to see the error.

**`Check failed: Python entry point`**
Why: Vercel needs a file it recognizes (`app.py`, `index.py`, `server.py`, `main.py`, `wsgi.py`, `asgi.py` or `manage.py`, also under `src/` or `app/`) that defines `app` (Flask, FastAPI) or `application` (Django).
Fix: rename your entry file or add one of these.

**`Vercel rollback failed` with `To rollback further than the previous production deployment, upgrade to pro.`** (not yet seen live)
Why: on the Hobby plan Vercel only allows a rollback to the previous production deployment, and that one is not available, for example because there was only one.
Fix: fix the code and deploy again, or roll back from the dashboard if a deployment is eligible there.

**After a rollback, new `run` deployments do not appear on the production domain** (not yet seen live)
Why: Vercel turns off automatic promotion of production deployments after a rollback.
Fix: run `vercel promote <deployment-url>` for the deployment you want live. This also turns automatic promotion back on.

### Render

**`Uncommitted changes would not be deployed. Commit them and push first.`**, **`The current branch has no upstream`**, **`N commit(s) are not pushed`**, **`No 'origin' git remote found`**, **`Render needs a git repository`**
Why: Render builds from your git remote, not your local folder, so local-only work would not ship.
Fix: `git add`, `git commit`, then `git push -u origin <branch>`. Add the remote first if you have none.

**`No 'start_command' in your config.`**
Why: Render needs a production start command and the tool does not guess one. It stops before any API call.
Fix: add `start_command` to `deployment.yaml` (`gunicorn wsgi:app`, `gunicorn <project>.wsgi:application`, or `uvicorn main:app --host 0.0.0.0 --port $PORT`) and list the server in `requirements.txt`.

**`Could not pick a Render owner automatically. Set RENDER_OWNER_ID to one of: ...`**
Why: your account has more than one workspace.
Fix: set `RENDER_OWNER_ID` to one of the IDs shown.

**`Render API returned HTTP 401 ...`**
Why: the API key is wrong, expired or revoked.
Fix: create a new key under Account Settings, API Keys, and set `RENDER_API_KEY` again.

**`Deploy dep-... did not go live: the build failed.`** (also `the deploy was canceled`, `the deploy was replaced by a newer one`, `the deploy failed to start`, `the pre-deploy command failed`)
Why: Render stopped that deploy. A failed build leaves the previous version running. Canceled and replaced deploys are covered by mocked tests only.
Fix: open the deploy's logs in the Render dashboard. For a replaced deploy, a newer commit probably started another one: look at that deploy instead.

**`Deploy dep-... was still 'build_in_progress' after 900 seconds.`**
Why: the build is slow, for example on the free plan, or stuck.
Fix: check the dashboard, since it may still finish. Raise `render_wait_timeout` in `deployment.yaml` if builds are normally slow. The tool does not start a second deploy.

**`Could not read the status of deploy dep-...`**
Why: Render's API answered with an error while the tool was waiting.
Fix: check the dashboard. The deploy may still be running.

**The build succeeds but the app fails on start.**
Why: a variable such as `SECRET_KEY` is not set on Render, and the tool does not upload secrets.
Fix: add it under the service's Environment tab. Saving redeploys.

**`No earlier successful deploy to roll back to.`** (rollback)
Why: there is only one deploy, the live deploy is already a rollback, or Render no longer keeps the older build.
Fix: pick a deploy in the dashboard (service, Deploys, Rollback).

**`Autodeploy is now OFF for this service.`** (after a rollback)
Why: Render switched auto-deploy off. Seen in every live rollback.
Fix: turn it back on under Settings, Auto-Deploy when you want new commits to deploy again.

### Railway and Heroku (not yet seen live)

**`Heroku rejected HEROKU_API_KEY (or the CLI is missing).`**
Fix: check the key with `heroku auth:whoami`, and that the Heroku CLI is installed.

**`Procfile created from 'start_command'. Heroku deploys committed code only: commit the Procfile, then run again.`**
Fix: `git add Procfile`, commit, run again.

**`Railway deployment failed; see the output above.`**
Why: often the CLI cannot find the project. The README notes that a project token alone may not be enough.
Fix: set `railway_project`, `railway_environment` and `railway_service` in `deployment.yaml`.

## Security

- Credentials are read only from environment variables. They are never accepted on the command line, so they do not show up in process lists or shell history.
- Credentials are removed from logged command output and error messages.
- The wizard writes secrets only to a local `.env` with owner-only permissions where the OS supports it, and adds `.env` to `.gitignore`.
- The tool never uploads `.env` or other secrets to a platform.
- A dry run never calls a platform API or runs a platform CLI.

## Limitations

- Render has been run live with Flask, Django and FastAPI apps. Vercel has been run live with a Flask app only. Railway and Heroku, and Vercel with Django or FastAPI, are implemented and mock-tested only.
- Live rollback exists for Render and Vercel only. The Vercel rollback has been run live with Flask only.
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
| Django | [mpd-django-example](https://github.com/Badee2000/mpd-django-example) | Render |
| FastAPI | [mpd-fastapi-example](https://github.com/Badee2000/mpd-fastapi-example) | Render |

The `examples/` folder in this repository holds minimal starter files. They have not been deployed.

## Troubleshooting

**`RENDER_API_KEY is not set` (or another token).** The variable is not set in this terminal. Set it again in the window you are running from.

**`No 'start_command' in your config`.** Add `start_command` to `deployment.yaml`, for example `gunicorn wsgi:app`, and put `gunicorn` in `requirements.txt`.

**`Uncommitted changes would not be deployed`, or commits not pushed.** Render and Heroku deploy committed code. Run `git status`, commit, and `git push`.

**The Render service was created but the app does not start.** Open the service's Logs. A missing environment variable is the usual cause. Add it under Environment. Saving redeploys.

**`Could not detect the framework`.** Detection looks for `manage.py` or imports in `app.py`, `main.py` and `wsgi.py`. The command asks you to choose when it fails.

**Health check says the server is down.** Check that the deploy has finished, that the app listens on the port the platform provides (`$PORT`), and that the app does not start a dev server from an `if __name__ == "__main__":` block.

**A Django migration failed.** Check that the database is reachable and `DATABASE_URL` is set. The deploy was stopped, so nothing was deployed. Fix the migration and run again.

**`ModuleNotFoundError: No module named 'yaml'`.** Install the package again with `pip install multi-platform-deployer`, or `pip install -e .` from a source checkout.

## Testing

```bash
pip install -e ".[dev]"
pytest
black --check src tests
isort --check-only src tests
flake8 src tests
mypy src
```

The suite has more than 200 tests, all with mocks and temporary directories. It never deploys anything. Five tests are skipped unless you opt in to live credential checks, which are read-only (who am I, list owners):

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

Issues and pull requests are welcome. Run `pytest`, `black`, `isort`, `flake8` and `mypy src` before opening a pull request. Do not run real deployments from tests: use mocks and temporary directories.

## License

MIT. See [LICENSE](LICENSE).

## Listed in the XERJ Corpus Hub

This repository is included in the [XERJ Corpus Hub](https://hub.xerj.org/contributors/Badee2000), an open index of code that AI coding agents search for worked examples. The selected commit is [`b078c24`](https://github.com/Badee2000/multi-platform-deployer/commit/b078c24faeb872ef4774d061cd046fb8b312e1b5), which fixes the Vercel, Railway and Heroku deployers against their official docs. It is indexed under this repository's MIT license, with attribution. XERJ is a separate project and is not affiliated with this one.
