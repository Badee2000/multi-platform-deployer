# Multi-Platform Deployer

[![PyPI - Version](https://img.shields.io/pypi/v/multi-platform-deployer.svg)](https://pypi.org/project/multi-platform-deployer/)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/multi-platform-deployer.svg?label=pip%20installs)](https://pypi.org/project/multi-platform-deployer/)

> **Check your Python app, then deploy it to Render, Railway, Vercel or Heroku from one tool.**

Deploying to different cloud platforms usually means learning completely different tools, config formats, and workflows. That's exhausting and error-prone. This package gives you a **single, simple interface** to check and deploy Flask, Django, and FastAPI applications to Render, Railway, Vercel, and Heroku.

### Platform status (what has actually been tested)

| Platform | Status | Evidence |
|----------|--------|----------|
| **Render** | ✅ Verified live | Service creation, build, health check, redeploy and live rollback were run against a real Render account with a Flask app (2026-10-25). |
| **Railway** | 🧪 Experimental | Uses the `railway` CLI. Covered by mocked tests only; never run against a real account. |
| **Vercel** | 🧪 Experimental | Uses the `vercel` CLI. Covered by mocked tests only; never run against a real account. |
| **Heroku** | 🧪 Experimental | Uses `git push` to the `heroku` remote. Covered by mocked tests only; never run against a real account. |

*Verified live* means it ran end to end on a real account. *Experimental* means it is implemented and tested with mocks, but not proven live. Make your first real deploy to a throwaway app. Frameworks: Flask is verified (on Render). Django and FastAPI projects pass the readiness checks and the dry run, but have not been deployed yet. Tests run in CI on Python 3.11 to 3.14, on Linux and Windows.

Think of it as a universal translator for cloud deployments.

---

## TL;DR Quickstart

1. **Install the tool once** (inside your project or globally):
  ```bash
  py -m pip install multi-platform-deployer
  ```
2. **Drop a 6-line shim** into the root of every project where you want the
  friendly `py deploy.py <command>` syntax:
  ```python
  # deploy.py
  from multi_platform_deployer.cli import main

  if __name__ == "__main__":
     raise SystemExit(main())
  ```
  > Prefer not to add a file? You can always run the package directly via
  > `python -m multi_platform_deployer.cli <command>`.
3. **Create your deployment config**:
  ```bash
  py deploy.py setup
  ```
  This guides you through creating `deployment.yaml` with your platform, app name, and more.
4. **Ship with commands**:
  ```bash
  py deploy.py check          # Pre-flight audit
  py deploy.py run            # Guided deployment (add --multi for several platforms)
  py deploy.py health --url https://your-app.com
  ```

That's it—config once, then treat `deploy.py` like any other project tool.

---

## What This Does

### The Problem
You've built a great Python web app and now you want to deploy it. But here's the thing:
- Render uses `render.yaml`
- Railway uses `railway.json`
- Vercel is completely different
- Heroku uses `Procfile`
- Each one has different environment variable management, different requirements

It's confusing. You end up copy-pasting from docs, getting things wrong, and spending hours debugging deployment issues.

### The Solution
I automated all of that. This package:

1. **Checks your app** - Validates that your app is actually ready for production (not just locally)
2. **Picks the platform** - Works with Render, Railway, Vercel, and Heroku (and you can add more)
3. **Handles the repetitive parts** - Optional Django/Alembic migrations, config files, health checks. (Secrets are never uploaded: set them in the platform dashboard.)
4. **Does one deploy** - Single command to deploy to one or multiple platforms simultaneously

That's it. You go from code to deployed in minutes, not hours.

---

## Installation

### Install from PyPI
```bash
py -m pip install multi-platform-deployer
```

### Install from this source folder (for development or unreleased changes)
```bash
# Run from the project folder that contains pyproject.toml
py -m pip install .
```

### Work on the Source Locally
```bash
git clone https://github.com/Badee2000/multi-platform-deployer.git
cd multi-platform-deployer
python -m venv .venv
.venv\Scripts\activate  # On macOS/Linux: source .venv/bin/activate
py -m pip install -e .
py -m pip install -e ".[dev]"  # Include lint/test extras while developing
```

---

## Deploy Your Project (Step by Step)

This is the path for deploying your own Flask, Django, or FastAPI app with your own accounts.

### 1. Check that your project fits the platform (no credentials needed)
```bash
py deploy.py check
py deploy.py run --platform vercel --dry-run   # or render, railway, heroku
```
`--dry-run` runs the readiness checks, then prints every command a real deploy would run. It executes nothing and creates nothing. Missing credentials show up as warnings here, not failures.

### 2. Set up the platform's CLI and credentials (one time)

| Platform | Install | Credential (environment variable) | What gets deployed |
|----------|---------|-----------------------------------|--------------------|
| Render | Nothing extra (uses the REST API) | `RENDER_API_KEY` (optional: `RENDER_OWNER_ID`) | The commit on your git remote `origin` |
| Railway | `npm install -g @railway/cli` | `RAILWAY_TOKEN` (a project token; not `RAILWAY_API_TOKEN`) | Your local folder (`railway up --ci`); the project and service must already exist |
| Vercel | `npm install -g vercel` | `VERCEL_TOKEN` | Your local folder (`vercel deploy --prod --yes`) |
| Heroku | Heroku CLI | `HEROKU_API_KEY` | The commit pushed to the `heroku` git remote |

Set credentials as environment variables in the shell you deploy from. Never put them in `deployment.yaml` or on the command line.

```powershell
$env:VERCEL_TOKEN = "your-token"     # PowerShell
```
```bash
export VERCEL_TOKEN="your-token"     # macOS / Linux
```

### 3. Deploy
```bash
py deploy.py run --platform vercel          # one platform, no prompts
py deploy.py run --platform vercel --migrate  # also run Django/Alembic migrations first
py deploy.py run                            # interactive wizard
```
Add `--dry-run` to any of these to preview. A real deploy exits non-zero on failure.

### Things to know before a real deploy
- **Git:** Render and Heroku deploy committed code. Commit and push first; the deployer refuses a dirty working tree (and, for Render, an unpushed `origin`). Heroku also needs a `heroku` remote (`heroku git:remote -a <app>`). Railway and Vercel deploy your local files.
- **Secrets are not uploaded.** Local `.env` values are never sent to a platform. Set them in the platform dashboard (Render: Environment; Railway: Variables; Vercel: Project Settings > Environment Variables) or with `heroku config:set`.
- **Production server:** Render has no default start command. A first deploy stops until you set `start_command` in `deployment.yaml` (for example `gunicorn wsgi:app`) and add the server to `requirements.txt`. Heroku uses your `Procfile`, and Railway your `Procfile` or `railway.json`; neither platform gets a guessed start command.
- **Railway URL:** `railway up` does not print a stable URL. Run `railway domain` to get it. If the CLI reports no linked project, run `railway link` once.
- **Render service ID:** the first real deploy creates the service and prints its ID. Add `render_service_id: <id>` to `deployment.yaml` so later runs redeploy that service instead of creating a new one.
- **Vercel config:** no `vercel.json` is generated. Vercel detects Flask, FastAPI and Django by itself (see the Vercel section for the entry points it needs).
- **Verify:** `py deploy.py health --url https://your-app.example.com`.

### Known limitations
- Live status: verified so far on Render with a Flask project: service creation, build, the post-deploy `health` check, a redeploy of the same service via `render_service_id`, and a live rollback (2026-10-25). Railway, Vercel and Heroku have not been run live at all. The rest is covered by mocked tests. Make your first real deploy to a throwaway app.
- Requires Python 3.11 or newer. Python 3.8, 3.9 and 3.10 are no longer supported (all end of life, and Heroku already deprecates 3.10). Tests run in CI on Python 3.11 to 3.14, on Linux and Windows.
- Railway and Heroku token behavior depends on each vendor's CLI. Both are unverified live; see their sections for what is and is not confirmed. The live read-only checks (see [Testing](#testing)) confirm a credential works before you deploy.

## Walkthrough: Deploy a Flask App to Render

This is the exact flow used to create a Render service from a small Flask project. Run it on a throwaway app first. Commands are PowerShell; on macOS or Linux use `export NAME=value` instead of `$env:NAME = "value"`.

**What you need:** Python 3.11+, `git`, a GitHub account, a Render account, and `pip install multi-platform-deployer` (or the source install above).

### 1. Prepare the app
- `requirements.txt` lists a production server, for example `Flask==3.1.3` and `gunicorn==26.2.0`.
- Read secrets from the environment. Do not hardcode them. Example: `SECRET_KEY = os.environ["SECRET_KEY"]`.
- Optional but useful: a `/health` route, and a pinned Python version (set it as Render documents; this project does not verify how Render reads it).
- Add `.env` and `.deployment/` to `.gitignore`. The deployer stores its rollback state in `.deployment/`.

### 2. Add `deployment.yaml`
```yaml
platform: render
app_name: my-flask-app
start_command: gunicorn wsgi:app
```
`start_command` is required for the first Render deploy. Use the module and variable that match your app (`wsgi:app` means a `wsgi.py` file that exposes `app`). Django uses `gunicorn <project>.wsgi:application`, and FastAPI uses `uvicorn main:app --host 0.0.0.0 --port $PORT`.

### 3. Push the project to GitHub
Render builds from your git remote, not your local folder. Commit everything, set `origin`, and push:
```powershell
git remote add origin https://github.com/<you>/<repo>.git
git push -u origin main
```
The deployer refuses to run with uncommitted changes or unpushed commits. A public repo needs no extra setup. For a private repo, connect GitHub to your Render account first (not tested here).

### 4. Create a Render API key
In Render: **Account Settings > API Keys > Create API Key**. Then set it in the terminal you will deploy from:
```powershell
$env:RENDER_API_KEY = Read-Host "Render key"
```
- The variable exists only in that terminal window. A new window needs it set again, otherwise the deploy stops with `RENDER_API_KEY is not set` and nothing is created.
- Never paste the key into a file in your project (including `.env.example`) or into a chat or issue. If it leaks, revoke it in Render and create a new one.

### 5. Check and preview
```powershell
multi-platform-deployer check
multi-platform-deployer run --platform render --dry-run
```
The dry run prints what would happen and executes nothing. It should not warn that the key is missing.

### 6. Deploy
```powershell
multi-platform-deployer run --platform render
```
On success the tool prints the new service ID and URL:
```
Created Render service srv-xxxxxxxxxxxxxxxxxxxx.
URL: https://my-flask-app.onrender.com
```
It creates a free-plan web service with auto-deploy on new commits. Change the plan or region with `render_plan` and `render_region` in `deployment.yaml`.

### 7. Set secrets in Render
The tool never uploads secrets. Open the service in the Render dashboard, go to **Environment**, and add `SECRET_KEY` (and anything else your app reads). Saving redeploys the service. Until you do this, an app that requires `SECRET_KEY` will build but crash on start.

### 8. Verify
The tool does not check health after deploying. Wait for the service to show **Live**, then:
```powershell
multi-platform-deployer health --url https://my-flask-app.onrender.com
```
Free-plan services sleep when idle, so the first request can be slow.

### 9. Redeploy later
Add the service ID to `deployment.yaml`, commit, push, and run the deploy again. It then redeploys the same service instead of creating a new one:
```yaml
render_service_id: srv-xxxxxxxxxxxxxxxxxxxx
```
The redeploy path is verified live on Render with the Flask example (the same service was updated, no duplicate created).

### 10. Clean up (for test apps)
Delete the service in the Render dashboard so it does not keep running, and revoke the API key if you created it only for this test.

## Get Started in 3 Steps

### Step 1: Set Up Your Deployment Configuration
```bash
py deploy.py setup
```

This launches an interactive wizard that creates your `deployment.yaml` file. You'll be asked for:
- **Platform** (Render, Railway, Vercel, or Heroku)
- **App name** (how your app will be named on the platform)
- **Environment variables** (optional, but recommended)
- **Services** (Railway-specific, optional)

When done, your `deployment.yaml` is ready to commit to git.

### Step 2: Check If Your App Is Ready
```bash
py deploy.py check
```

This runs a battery of checks to make sure your app is production-ready. It'll tell you:
- ✅ Do you have a requirements.txt?
- ✅ Is your SECRET_KEY properly configured?
- ✅ Is debug mode off?
- ✅ Are your database settings production-safe?
- ✅ Is your Python runtime/version pinned?
- ✅ Are your .env secrets real (no placeholders)?
- ✅ Is your git workspace clean before shipping?
- ...and more

If everything passes, you're good to go. If not, it tells you exactly what to fix.

### Step 3: Deploy
```bash
# Deploy to one platform
py deploy.py run

# Deploy to multiple platforms at once
py deploy.py run --multi
```

You'll be guided through a simple wizard:
1. Pick your platform(s) (or use config from `deployment.yaml`)
2. Decide if you want database migrations run
3. Watch it deploy (takes seconds)

That's actually it. Your app is live.

### Step 4: Verify It Works
```bash
py deploy.py health --url https://my-app.onrender.com
```

This checks that your deployed app is up and responding correctly. It verifies:
- Server is running (the base URL answers with any HTTP status below 500; a 5xx or no connection counts as down)
- Requested endpoints return their HTTP status codes

It does **not** verify database connectivity or response times. The database check is reported as `NOT CHECKED`.

---

## The CLI Commands

Everything is straightforward. Here's what you can do:

| Command | What It Does |
|---------|-------------|
| `py deploy.py setup` | Create/edit deployment.yaml configuration (first time?) |
| `py deploy.py check` | Verify your app is production-ready |
| `py deploy.py run` | Deploy to one platform (interactive) |
| `py deploy.py run --multi` | Deploy to multiple platforms at once |
| `py deploy.py info` | Show info about your project |
| `py deploy.py health --url <url>` | Check if deployed app is healthy |
| `py deploy.py health --url <url> --endpoints "/,/api,/health"` | Check specific endpoints |
| `py deploy.py rollback` | Restore the previous project files (does not change the live deployment) |
| `py deploy.py rollback --live` | Roll back the running Render service to its previous successful deploy |
| `py deploy.py --help` | See all commands |

---

## Real Examples

### Flask App (5 minutes to deployment)
```bash
# You have a simple Flask app. Check it's ready:
py deploy.py check

# Looks good! Deploy to Render:
py deploy.py run
# → Pick "Render" from the list
# → Say yes to migrations if using a database
# → Done! Visit your app

# Verify it's working:
py deploy.py health --url https://my-flask-app.onrender.com
```

### Django Project (even easier)
```bash
# Django projects are fully supported
py deploy.py check

# Deploy to Railway (or any other platform)
py deploy.py run
# → Pick "Railway"
# → Migrations run automatically
# → Your Django app is live

# Check that admin panel and everything works
py deploy.py health --url https://my-django-app.railway.app
```

### FastAPI App (super fast)
```bash
# FastAPI is speedy, and so is deployment
py deploy.py check

# Deploy to Vercel (serverless is perfect for FastAPI)
py deploy.py run

# Check endpoints
py deploy.py health --url https://my-fastapi-app.vercel.app --endpoints "/,/docs,/api/users"
```

---

## Using the Python API (For Scripts)

If you want to automate deployments (like in CI/CD), you can use the Python API directly:

```python
from multi_platform_deployer.main import Deployer

# Create a deployer for your project
deployer = Deployer("./my_project")

# Step 1: Check readiness
is_ready, results = deployer.check_deployment_readiness("flask")

if not is_ready:
    print("Not ready for deployment:")
    for result in results:
        if not result.passed:
            print(f"  ✗ {result.name}: {result.message}")
    exit(1)

# Step 2: Deploy
success = deployer.deploy("render", run_migrations=True)

if success:
    print("✓ Deployed successfully!")
    
    # Step 3: Check health
    health = deployer.check_health(
        base_url="https://my-app.onrender.com",
        endpoints=["/", "/api/health"]
    )
else:
    print("✗ Deployment failed")
    exit(1)
```

---

## Configuration

### Create `deployment.yaml` (recommended)
You can commit this to git so everyone deploys consistently:

```yaml
# deployment.yaml
platform: render  # or: railway, vercel, heroku

app_name: my-awesome-app

# Optional: Environment variables
env:
  DEBUG: "False"
  PYTHONUNBUFFERED: "1"

# Optional: Services (if using Railway)
services:
  - name: web
    buildCommand: pip install -r requirements.txt && python manage.py migrate
    startCommand: gunicorn config.wsgi
    port: 8000
```

### Or use `deployment.json`
```json
{
  "platform": ["render", "railway"],
  "app_name": "my-awesome-app",
  "env": {
    "DEBUG": "False"
  }
}
```

The deployer will auto-detect and load whichever you use.

---

## What Gets Checked

### For Flask Apps
- ✓ Requirements file exists
- ✓ App entry point found (app.py, wsgi.py, etc.)
- ✓ WSGI application configured
- ✓ SECRET_KEY set via environment
- ✓ Debug mode is OFF (not hardcoded)
- ✓ Error handlers configured
- ✓ Database configuration present
- ✓ Environment file exists

### For Django Projects
- ✓ manage.py exists
- ✓ settings.py properly configured
- ✓ SECRET_KEY via environment (not in code!)
- ✓ ALLOWED_HOSTS set
- ✓ Static files configured
- ✓ Database configured
- ✓ DEBUG=False in production
- ✓ Security settings (CSRF, SSL, etc.)

### For FastAPI Apps
- ✓ FastAPI app instance exists
- ✓ Uvicorn/Gunicorn in requirements
- ✓ CORS configured (if needed)
- ✓ Middleware setup
- ✓ Exception handlers
- ✓ Database connections configured

All checks give you **specific, actionable feedback**. Not vague errors. Real guidance.

---

## Supported Platforms

### Render
Best for: General purpose Python web apps. Uses the Render REST API.
**Status: ✅ verified live** (create, build, health, redeploy, live rollback with a Flask app).

```bash
py deploy.py run --platform render
```

**What it does:**
- Creates a web service from your `origin` git remote (or triggers a deploy when `render_service_id` is set)
- Build command: `pip install -r requirements.txt`
- Start command: `start_command` from your config. **Required** for the first deploy, because no one default fits Flask, Django and FastAPI. The deploy stops before any API call if it is missing. A dev-server command (`python app.py`, `flask run`, `runserver`) is accepted with a warning.
- Requires a clean git working tree and an `origin` remote. Only committed code is deployed.
- Needs `RENDER_API_KEY` (and optionally `RENDER_OWNER_ID`)

> Examples: Flask `gunicorn wsgi:app`, Django `gunicorn <project>.wsgi`, FastAPI `uvicorn main:app --host 0.0.0.0 --port $PORT`. Add the server package to `requirements.txt`.

### Railway
Best for: Apps that need the Railway runtime
**Status: 🧪 experimental** (mocked tests only, never run on a real account).

```bash
py deploy.py run --platform railway
```

**What it does:**
- Runs `railway up --ci` with the Railway CLI
- Needs the Railway CLI on your PATH and `RAILWAY_TOKEN`, a **project token** created in the Railway project's settings. Do not set `RAILWAY_API_TOKEN` as well: Railway rejects that, so the tool removes it for the run.
- The project, environment and service must already exist: Railway never creates projects in CI. Optional config keys `railway_project`, `railway_environment` and `railway_service` are passed as `--project`, `--environment` and `--service`.
- Start command: your `Procfile` or `railway.json` decides. If you set `start_command` and have no `railway.json`, one is generated from it. No start command is guessed.
- The deploy prints no stable public URL. Run `railway domain` or check the Railway dashboard.
- Not yet confirmed live: whether the project token alone is enough without `railway link`.

### Vercel
Best for: Serverless Python APIs (FastAPI, Flask, Django)
**Status: 🧪 experimental** (mocked tests only, never run on a real account).

```bash
py deploy.py run --platform vercel
```

**What it does:**
- Runs `vercel deploy --prod --yes` with the Vercel CLI
- Needs the Vercel CLI on your PATH and `VERCEL_TOKEN`. If your project is already linked, `VERCEL_ORG_ID` and `VERCEL_PROJECT_ID` are used when set.
- Vercel detects Flask, FastAPI and Django by itself, so **no `vercel.json` is generated**. An existing one is left alone.
- Needs a Python entry point Vercel recognizes: `app.py`, `index.py`, `server.py`, `main.py`, `wsgi.py` or `asgi.py` (also under `src/` or `app/`), or a Django `manage.py`. The file must define `app` (Flask, FastAPI) or `application` (Django).
- Serverless: the filesystem is read-only, so do not rely on SQLite writes.
- Prints the production URL when the CLI reports it

### Heroku
Best for: Apps deployed with git push
**Status: 🧪 experimental** (mocked tests only, never run on a real account).

```bash
py deploy.py run --platform heroku
```

**What it does:**
- Checks the key with `heroku auth:whoami`
- Requires a clean git working tree, a `heroku` git remote (`heroku git:remote -a <app>`, HTTPS), and a `Procfile`. If you have no Procfile but set `start_command`, one is created from it and you must commit it.
- Runs `git push heroku HEAD:main`, authenticating with `HEROKU_API_KEY` through a one-time git credential helper that reads the key from the environment, so the key never appears in the command line and `heroku login` is not required.
- Needs the Heroku CLI and `HEROKU_API_KEY`
- Not yet confirmed live: the credential-helper push has only been tested with mocks.
- Pin the Python version in `.python-version` as `3.12` (major.minor): Heroku supports only the latest patch of each version.

---

## Advanced Features

### Database Migrations
Run as part of `deploy()` when you enable them (the wizard asks; the default is on):

```bash
py deploy.py run
# During the wizard, say "Yes" to run migrations
```

Supported migration runners:
- **Django** - `python manage.py migrate`
- **Alembic** - `alembic upgrade head` (Flask-SQLAlchemy)

If migrations fail, the deployment is aborted before anything is deployed.
Other migration scripts are not run automatically.

### Health Checks
After deploying, verify everything works:

```bash
py deploy.py health \
  --url https://my-app.onrender.com \
  --endpoints "/,/api/health,/api/version"
```

This checks:
- Server is responding (the base URL answers with any status below 500, so a `/health` route is not required)
- Endpoint status codes (HTTP errors such as 500 or 404 are reported with their real code)

It does not check response times or database connectivity. The database is reported as `NOT CHECKED`. The command exits with a non-zero code if the server is not healthy.

### Rollback
Deployed something broken? There are two kinds of rollback.

**Live rollback (Render only):**
```bash
py deploy.py rollback --live --dry-run   # preview the API calls, change nothing
py deploy.py rollback --live             # asks for confirmation, then rolls back
```
This uses Render's rollback API to put the running service back on its most recent earlier successful deploy. Render reuses the old build, so no rebuild is needed. It needs `RENDER_API_KEY` and `render_service_id` in `deployment.yaml`, and it does not touch your local files.
- It picks the newest earlier deploy that was live before. Failed builds are skipped.
- If the live deploy is itself a rollback, the command stops instead of flipping back to the bad build. Choose a deploy in the Render dashboard (service > Deploys) in that case.
- If there is no earlier successful deploy, or Render no longer keeps its build, nothing is changed and the command exits non-zero.
- **Render may switch autodeploy off.** Render's API docs say a rollback leaves autodeploy alone, but in a live test it was switched off (the dashboard does this too). The tool reads the service afterwards and tells you the real state. If it is off, new commits will not deploy until you turn it back on in the Render dashboard (Settings > Auto-Deploy). If it is still on, a new commit will deploy again and may undo the rollback.
- Other platforms print "not supported" and exit non-zero. Use their own dashboard or CLI.

**File rollback (default, any platform):**
```bash
py deploy.py rollback
```
After every successful deployment record, the project files are snapshotted
(`.env` files are never included). A rollback restores the snapshot from the
deployment before the most recent one. It restores **files only**: the live
deployment on your platform is not changed, so you must redeploy the restored
code yourself. The command exits with a non-zero code if no previous snapshot
exists or the restore fails.

Live rollback was run against a real Render service (the Flask example). Test on 2026-10-25: a deploy served `"version":"v2"`, then `rollback --live` returned it to the previous code within about 20 seconds, with a monitor recording both states. The safety guard was also exercised live: with a rollback already live, a second `rollback --live` changed nothing and exited non-zero.

### Deploy to Multiple Platforms
Want your app on Render AND Railway for redundancy?

```bash
py deploy.py run --multi
# → Select both Render and Railway
```

> **Note:** `--multi` deploys to each platform in turn. Each platform's deploy needs its own CLI or API token, and a failure on one platform does not roll back the others.

Each platform gets properly configured. You now have failover coverage.

---

## Complete CLI Reference

```
USAGE:
  py deploy.py <command> [options]

COMMANDS:
  setup              Create/edit deployment.yaml configuration
  check              Check if your app is ready for deployment
  run                Deploy your app (interactive, or --platform for one platform)
  info               Show project information
  health             Check deployed app health
  rollback           Rollback to previous deployment (--live: roll back the running Render service)

OPTIONS:
  --platform NAME    Deploy to one platform without prompts (render, railway, vercel, heroku)
  --dry-run          With --platform (run) or --live (rollback): print what would happen, change nothing
  --live             With rollback: roll back the running service on its platform (Render only)
  --migrate          With --platform: run Django/Alembic migrations first
  --multi            Deploy to multiple platforms
  --url URL          App URL for health check
  --endpoints PATHS  Comma-separated endpoints to check (default: /)

EXAMPLES:
  py deploy.py setup                              # Create deployment config
  py deploy.py check                              # Check readiness
  py deploy.py run --platform vercel --dry-run    # Preview a Vercel deploy (no credentials needed)
  py deploy.py run --platform vercel              # Deploy to Vercel
  py deploy.py run --multi                        # Deploy to multiple platforms
  py deploy.py info                               # Show project info
  py deploy.py health --url https://...           # Check health
  py deploy.py rollback                           # Restore the previous project files
  py deploy.py rollback --live --dry-run          # Preview a live Render rollback
```

---

## Testing

I test everything thoroughly. Run the tests yourself:

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run all tests
pytest

# Run with coverage report
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_deployers.py -v

# Run one specific test
pytest tests/test_checkers.py::TestFlaskChecker -v
```

**Current status:** 112 tests passing, 5 skipped (the live deploy tests, which run only when you opt in), mypy clean on `src/`.

Live, read-only checks against real platforms run only when you set `MPD_LIVE_TESTS=1` plus the platform tokens. They never deploy. Without them, those tests are skipped.

---

## Project Structure

```
multi-platform-deployer/
│
├── src/                    # The actual package
│   ├── main.py            # Main Deployer class (orchestrates everything)
│   ├── deployers/         # Code for each platform
│   │   ├── render.py      # Render deployer
│   │   ├── railway.py     # Railway deployer
│   │   ├── vercel.py      # Vercel deployer
│   │   └── heroku.py      # Heroku deployer
│   ├── checkers/          # Readiness checkers
│   │   ├── flask_checker.py
│   │   ├── django_checker.py
│   │   └── fastapi_checker.py
│   ├── config/            # Config file handling
│   │   ├── loader.py      # Load YAML/JSON config
│   │   └── validator.py   # Validate config
│   ├── scripts/           # Helper scripts
│   │   ├── migrator.py    # Database migrations
│   │   ├── health_check.py
│   │   └── rollback.py
│   └── utils/             # Utility functions
│       ├── helpers.py     # Command execution, file I/O
│       ├── logger.py      # Logging setup
│       └── validators.py  # Validation functions
│
├── tests/                 # Test suite
│   ├── test_main.py       # Tests for Deployer
│   ├── test_deployers.py  # Tests for each platform
│   ├── test_checkers.py   # Tests for readiness checks
│   ├── test_config.py     # Tests for config management
│   └── test_utils.py      # Tests for utilities
│
├── examples/              # Example applications
│   ├── flask_app/         # Complete Flask example
│   ├── django_app/        # Complete Django example
│   └── fastapi_app/       # Complete FastAPI example
│
├── deploy.py              # CLI entry point (run this!)
├── cli.py                 # CLI implementation
├── pyproject.toml         # Project config and package metadata
├── requirements.txt       # Dependencies
├── README_COMPLETE.md     # This file
└── LICENSE                # MIT License
```

---

## Troubleshooting

### "ModuleNotFoundError: No module named 'yaml'"
You need to install dependencies:
```bash
pip install -e .
```

### "Could not auto-detect framework"
The checker couldn't figure out if you're using Flask, Django, or FastAPI. Just tell it:
```bash
py deploy.py check
# → When asked, type: 1 (Flask), 2 (Django), or 3 (FastAPI)
```

### "Deployment failed: API key not found"
Some platforms (Vercel, Heroku) need API credentials. Set them as environment variables:
```bash
# For Vercel
export VERCEL_TOKEN=your_token_here

# For Heroku  
export HEROKU_API_KEY=your_key_here

# For Render
export RENDER_API_KEY=your_key_here
```
Set it in the same terminal you deploy from. A variable set in one terminal window is not visible in another. In PowerShell: `$env:RENDER_API_KEY = "your_key_here"`.

### "No 'start_command' in your config" (Render)
The first Render deploy needs a production start command, and there is no default. Add it to `deployment.yaml`, for example `start_command: gunicorn wsgi:app`, and make sure `gunicorn` is in `requirements.txt`.

### "Uncommitted changes would not be deployed" / "commit(s) are not pushed"
Render and Heroku deploy committed code. Run `git status`, commit your changes, and `git push`. The tool's own `.deployment/` folder is ignored by this check.

### Render service was created but the app does not start
Open the service's **Logs** in the Render dashboard. A common cause is a missing environment variable. The tool does not upload secrets, so add them under **Environment** (for example `SECRET_KEY`). Saving redeploys the service.

### "Health check failed: Connection refused"
Your app isn't responding. Check:
1. Is the deployment actually finished? (refresh after a minute)
2. Is your app listening on the right port?
3. Do you have `if __name__ == '__main__'` in Flask apps? (remove it for production)

### "Django migration failed"
Make sure:
1. Your database is running and accessible
2. `DATABASE_URL` environment variable is set correctly
3. Your migrations are in the right folder

The deployment is aborted when migrations fail, so nothing is deployed. Fix the migration and run `deploy` again.

---

## Contributing

Have an idea? Found a bug? Want to add AWS support? I'd love help!

**Getting started:**
```bash
git clone https://github.com/Badee2000/multi-platform-deployer.git
cd multi-platform-deployer
pip install -e ".[dev]"

# Make your changes
pytest tests/ -v  # Make sure tests pass

# Push and create a PR!
```

**Code style (I use Black and isort):**
```bash
black src/ tests/
isort src/ tests/
```

---

## Roadmap

Things I'm working toward:

- [ ] AWS deployment (EC2, Elastic Beanstalk)
- [ ] Google Cloud Platform
- [ ] Azure
- [ ] Kubernetes support
- [ ] Automated Docker image generation
- [ ] Cost estimation before deployment
- [ ] Multi-region deployments
- [ ] Advanced monitoring/alerting integration
- [ ] Load balancer setup
- [ ] SSL certificate automation

---

## FAQ

**Q: Can I use this with my existing production app?**
A: Yes! Just run `py deploy.py check` to see if there are any issues. If it passes, you're good to deploy.

**Q: Does this support databases?**
A: Django (`manage.py migrate`) and Alembic (Flask-SQLAlchemy) migrations are run automatically when enabled. A failed migration aborts the deployment. Other database setups are not managed.

**Q: What if I don't want to use the CLI?**
A: The Python API works just fine for scripts and CI/CD pipelines. You have full control either way.

**Q: Can I deploy the same app to multiple platforms?**
A: Yes. Run `py deploy.py run --platform <name>` once per platform. Each platform needs its own CLI or API token. Note that `--multi` deploys each platform in turn and does not roll back the others on failure.

**Q: Is my data safe?**
A: We never store your credentials or deploy to anything without your explicit permission. Everything runs on your machine or the platforms you authorize.

**Q: How long do deployments take?**
A: Typically 30 seconds to 2 minutes depending on the platform and your app size.

**Q: Can I rollback?**
A: On Render, yes: `rollback --live` uses Render's rollback API (mocked-tested, not yet verified on a real account). On other platforms, `rollback` only restores the previous project snapshot's files. It does not change the live deployment, so you must redeploy afterwards.

**Q: Is this production-ready?**
A: Not yet. Real deploys exist for all four platforms, but only Render has been verified live (create, build, health check and redeploy, using a Flask example). Railway, Vercel and Heroku are mocked-tested only, and some health checks are placeholders.

---

## License

MIT License - You're free to use this however you want.

---

## Let's Deploy Something

There's no reason deployment should be complicated. This package takes the friction out of getting your app live.

**Get started right now:**

```bash
git clone https://github.com/Badee2000/multi-platform-deployer.git
cd multi-platform-deployer
pip install -e .
py deploy.py check
```

Then watch your app go live.

Good luck out there! 🚀

---

**Questions?** Open an issue on GitHub. Want to contribute? Pull requests welcome!

**Made with ❤️ to make deployment less awful.**

