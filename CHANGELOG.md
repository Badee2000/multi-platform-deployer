# Changelog

## 0.5.0 - 2026-11-25

Vercel is now verified live with a Flask app. Railway and Heroku, and Vercel with Django or FastAPI, are still only covered by mocked tests.

### Changed

- `health` reports a failure when the URL redirects to a different host, for example the login page of a Vercel project with Deployment Protection. Before, the redirect was followed and the login page was reported as "up" with HTTP 200. The failure is reported without retries and names the host. Redirects that stay on the same host (http to https, `www.`) still count as up. Scripts that relied on the old result for protected deployments will now see exit code 1.

### Added

- Vercel: `rollback --live --platform vercel` lists the successful production deployments with `vercel list`, picks the second newest and runs `vercel rollback <url> --yes --timeout 3m`. It needs `VERCEL_TOKEN`, supports `--dry-run`, never retries, keeps the token out of logs, stops if fewer than two successful production deployments exist, and reminds you to run `vercel promote <url>` because Vercel stops promoting new deployments after a rollback. The target is always passed explicitly, because `vercel rollback` without one changes nothing when the newest production deployment failed to build (found live: the command reported success and production kept serving the same version).
- README: a Troubleshooting section with the tool's exact error messages, why each happens and how to fix it, for every platform, including the failed Vercel build and the `User not found (404)` token-scope error seen live.
- After a successful deploy, `run` prints the exact `health --url <url>` command to run next, when the platform reported a URL.
- Mocked tests for a Render deploy that is canceled, replaced, fails to start or fails its pre-deploy command. Each must make `run` fail, never retry the deploy, and keep the API key out of the log. Mocked tests for the Vercel rollback and for the Vercel file-snapshot rollback.

### Fixed

- Flask readiness check: "WSGI application" no longer fails when the app is `app.py` or `main.py` with a module-level `app` (or `application`). It used to require `wsgi.py`, which wrongly blocked Flask apps for Vercel.

### Verified live

- Vercel with Flask: first production deploy, a redeploy (v1 to v2, new deployment served the new code), a deliberately broken build (nonexistent package: exit code 1, no "Deployed" message, no state saved, the live app kept serving v2) and `rollback --live` (production domains went from v2 back to v1, then `vercel promote` put v2 back). Checked through `vercel curl`: `/`, `/health` and the JSON 404 handler answered correctly. `health` passes on an unprotected URL and fails on a protected one.
- Not verified live: Vercel with Django or FastAPI, Railway, Heroku.

## 0.4.0 - 2026-11-05

### Changed

- The terminal output is plain text. The banner, emoji and rule lines are gone, and so is the `py deploy.py` shim from the help text. Readiness results are one line each (`[ok  ]` or `[FAIL]`). Console log lines are just the message, with `Warning:` or `Error:` in front of problems. A log file, if you configure one, still records the time, level and logger name. Scripts that parse the old text will need updating.
- `check` no longer prints every framework result twice. The framework checkers no longer print anything themselves, so use the results they return, or `BaseChecker.print_results()`. `CheckResult.icon()` is replaced by `CheckResult.status()`.
- `run` prints only the failed checks, or a one-line summary when they all pass.
- A dry run no longer says "Triggered a Render deploy".
- Render: the "Environment variables" check, which always passed and checked nothing, is gone.
- The platform deployers share one validation loop (`BaseDeployer._run_checks`).
- Docstrings are shorter and describe what the code does. The code is formatted with black and isort, and `flake8` and `mypy` pass (a `.flake8` file sets the line length to 100).

### Added

- Render: `run` now waits for the deploy to go live instead of reporting success as soon as Render accepts the request. It prints each status change and exits non-zero if the build fails, the deploy is canceled or replaced, the status cannot be read, or the wait times out. The new `render_wait_timeout` setting (seconds, default 900, `0` to skip waiting) controls the wait. The tool never retries a deploy.
- Render: `rollback --live` warns when the deploy it rolls back to was built from the same commit as the live one.
- New tests for the waiting, the rollback warning, the terminal output and the shared validation loop, plus a Django start-command test and a Django readiness test for settings read from the environment.

### Verified live

- Render with Flask, Django and FastAPI: first deploy, health check, redeploy and `rollback --live`. Render turned auto-deploy off after every rollback.
- The wait: a redeploy that waited until live, a deliberately broken build (exit code 1, the live app kept the old code), a 5 second timeout (exit code 1, the deploy kept running on Render), and the wait after the first deploy. Canceled or replaced deploys and an unreadable status are covered by mocked tests only.
- Vercel, Railway and Heroku are still not verified live.

### Documentation

- The README says that Render deploys on every push by default, so `run` on an existing service starts a second deploy of the same commit. It explains that `health --url` takes the base URL, and shows the new output.

## 0.3.1 - 2026-10-29

Package metadata and documentation only. No code changes since 0.3.0.

- The PyPI page now shows the real author, Flask, Django and FastAPI classifiers, a Developer audience tag, an Alpha status, more keywords, and Documentation and Changelog links.
- The package description no longer says Vercel deploys are supported. Only Render has been verified live.
- The README has a table of common tasks with the true status of each.

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
