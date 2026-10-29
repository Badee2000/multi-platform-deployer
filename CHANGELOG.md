# Changelog

## 0.3.0 - 2026-10-29

Only Render has been run against a real account, and only with a Flask app. Vercel, Railway and Heroku changes in this release are covered by mocked tests, not live runs. Railway and Heroku remain experimental.

### Breaking changes

- Python 3.11 or newer is required (was 3.8). 3.8, 3.9 and 3.10 are end of life.
- Render: the first deploy needs `start_command` in `deployment.yaml`. The old default, `python app.py`, started a development server. The deploy now stops before any API call if the command is missing. Dev-server commands are still accepted, with a warning.
- Vercel: no `vercel.json` is generated any more. Vercel detects Flask, FastAPI and Django itself. An existing file is left alone.
- Railway: `railway.json` is only generated when `start_command` is set. The old template guessed `python app.py`.
- Heroku: a `Procfile` is only created from `start_command`. The old code created `web: python app.py`.
- The config validator rejects `platform: aws`. No AWS deployer ever existed.
- `Deployer.rollback()` on Render no longer redeploys the current code (which could create a new service). Use `rollback_live()` for a real rollback.

### Added

- `rollback --live [--platform NAME] [--dry-run]` and `Deployer.rollback_live()`. Render only. It rolls the running service back to the most recent earlier successful deploy through Render's API, refuses to switch back to a bad build after a rollback, and reports whether Render turned auto-deploy off. Other platforms report "not supported".
- `setup` asks for an optional production `start_command`.
- Railway: optional `railway_project`, `railway_environment` and `railway_service` settings, passed to `railway up`.
- Vercel: accepts every Python entry point Vercel documents (`main.py`, `wsgi.py`, `asgi.py`, `manage.py`, files under `src/` and `app/`).
- GitHub Actions: tests on Python 3.11 to 3.14 on Linux and Windows, plus a package build check. A release workflow creates a GitHub release from a version tag. It does not publish to PyPI.
- A reference-style README with a status table, configuration table, security notes and limitations.

### Fixed

- Render: the create-service request used deprecated fields. It now sends `runtime` and `autoDeployTrigger`.
- The tool's own `.deployment/` folder no longer makes the next deploy refuse to run because of a "dirty" working tree.
- Heroku: the push no longer needs `heroku login`. It authenticates through a temporary git credential helper that reads `HEROKU_API_KEY` from the environment, so the key stays out of the command line.
- Railway: `RAILWAY_API_TOKEN` is removed for the run, because Railway rejects runs where both token variables are set.
- `setup` said `.env` was git-ignored without checking. It now adds `.env` to `.gitignore` when it saves secrets.
- `setup` no longer writes a Railway `services` block. Nothing read it, and its start command was a Django-only guess.
- `health` printed its summary twice.
- Package metadata pointed at `github.com/yourusername`. It now points at this repository. The license is declared as an SPDX expression.

### Known limitations

- Live rollback exists for Render only.
- Secrets are never uploaded to a platform. Set them in each platform's dashboard.
- `run` does not check health by itself. Run `health` afterwards.
- A health check treats any response below 500 as up, including 401 and 403.

## 0.2.0

First release with real deploys: Render through its REST API, Vercel and Railway through their CLIs, Heroku through `git push`. Added `--platform`, `--dry-run` and `--migrate`, and a health check that probes the base URL.
