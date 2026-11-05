"""Multi-Platform Deployer command line interface."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

from .main import Deployer
from .utils.logger import setup_logger

logger = setup_logger()


def clear_screen() -> None:
    """Clear the terminal screen when explicitly enabled."""

    if not sys.stdout.isatty():
        return
    if os.environ.get("MPD_ENABLE_CLEAR", "0") != "1":
        return
    os.system("cls" if os.name == "nt" else "clear")


def heading(title: str) -> None:
    """Print a section title with an underline."""
    print(f"\n{title}")
    print("-" * len(title))


def print_check_results(results: List[Any], failures_only: bool = False) -> None:
    """Print readiness results, one line each, or only the failed ones."""
    for result in results:
        if result.passed and failures_only:
            continue
        print(f"  {result}")


def detect_framework() -> Optional[str]:
    """Try to detect the current project framework."""

    cwd = Path(".")

    if (cwd / "manage.py").exists():
        return "django"

    markers = {
        "fastapi": ("from fastapi", "import fastapi", "FastAPI("),
        "flask": ("from flask", "import flask", "Flask("),
    }
    for file_name in ["app.py", "main.py", "wsgi.py"]:
        path = cwd / file_name
        if not path.exists():
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for framework, needles in markers.items():
            if any(needle in content for needle in needles):
                return framework

    if (cwd / "wsgi.py").exists():
        return "flask"

    return None


def ask_yes_no(question: str) -> bool:
    """Prompt the user for a yes/no answer."""

    while True:
        response = input(f"\n{question} (yes/no): ").strip().lower()
        if response in {"yes", "y"}:
            return True
        if response in {"no", "n"}:
            return False
        print("Please enter 'yes' or 'no'.")


def choose_option(question: str, options: List[str]) -> str:
    """Prompt the user to choose from a list of options."""

    print(f"\n{question}")
    for index, option in enumerate(options, start=1):
        print(f"  {index}. {option}")

    while True:
        try:
            choice = int(input("\nEnter your choice (number): ").strip())
            if 1 <= choice <= len(options):
                return options[choice - 1]
            print(f"Please enter a number between 1 and {len(options)}")
        except ValueError:
            print("Please enter a valid number.")


def check_readiness() -> bool:
    """Run the readiness checks and print every result."""
    clear_screen()
    heading("Readiness check")

    framework = detect_framework()
    if framework:
        print(f"Detected framework: {framework}")
    else:
        print("Could not detect the framework.")
        framework = choose_option(
            "Which framework are you using?",
            ["Flask", "Django", "FastAPI"],
        ).lower()

    deployer = Deployer(".")
    is_ready, results = deployer.check_deployment_readiness(framework)

    print()
    print_check_results(results)

    if is_ready:
        print("\nYour application is ready to deploy.\n")
        return True

    failures = sum(1 for result in results if not result.passed)
    print(f"\n{failures} check(s) failed. Fix them before deploying.\n")
    return False


def deploy(
    platform: Optional[str] = None,
    dry_run: bool = False,
    run_migrations: bool = False,
) -> bool:
    """
    Deploy to one platform. Returns True on success.

    Without a platform, asks the questions interactively. With one, runs
    without prompts, which is what scripts and CI use.
    """
    interactive = platform is None

    if interactive:
        clear_screen()
    if dry_run:
        print("Dry run: commands are printed and nothing is executed.\n")

    framework = detect_framework()
    if framework is None:
        if not interactive:
            print("Could not detect the framework (Flask, Django or FastAPI).\n")
            return False
        framework = choose_option(
            "Which framework are you using?",
            ["Flask", "Django", "FastAPI"],
        ).lower()

    deployer = Deployer(".", dry_run=dry_run)
    is_ready, results = deployer.check_deployment_readiness(framework)
    if not is_ready:
        print("Readiness checks failed:")
        print_check_results(results, failures_only=True)
        print("\nFix these before deploying.\n")
        return False
    print(f"Readiness checks passed ({len(results)}).\n")

    if interactive:
        platform = choose_option(
            "Which platform do you want to deploy to?",
            ["Render", "Railway", "Vercel", "Heroku"],
        ).lower()
        run_migrations = ask_yes_no("Run database migrations?")

    if platform is None:
        return False
    success = deployer.deploy(platform, run_migrations=run_migrations)

    if not success:
        print("\nDeployment failed.\n")
        return False

    if dry_run:
        print("\nDry run complete. Run again without --dry-run to deploy.\n")
        return True

    print(f"\nDeployed to {platform}.\n")
    if interactive and ask_yes_no("Check application health?"):
        url = input("Enter your app URL: ").strip()
        deployer.check_health(url)
    return True


def multi_deploy() -> bool:
    """Deploy to several platforms interactively. True only if every one succeeded."""
    clear_screen()
    heading("Deploy to multiple platforms")

    framework = (
        detect_framework()
        or choose_option(
            "Which framework are you using?",
            ["Flask", "Django", "FastAPI"],
        ).lower()
    )

    deployer = Deployer(".")
    is_ready, checks = deployer.check_deployment_readiness(framework)
    if not is_ready:
        print("Readiness checks failed:")
        print_check_results(checks, failures_only=True)
        print("\nFix these before deploying.\n")
        return False

    print("\nSelect platforms to deploy to (comma-separated numbers):")
    platforms_list = ["Render", "Railway", "Vercel", "Heroku"]
    for index, platform in enumerate(platforms_list, start=1):
        print(f"  {index}. {platform}")

    choices = input("\nEnter choices (e.g., 1,2,3): ").strip().split(",")
    selected = []
    for entry in choices:
        entry = entry.strip()
        if entry.isdigit():
            idx = int(entry)
            if 1 <= idx <= len(platforms_list):
                selected.append(platforms_list[idx - 1].lower())

    if not selected:
        print("No platforms selected.\n")
        return False

    run_migrations = ask_yes_no("Run database migrations?")
    results = deployer.deploy_to_multiple_platforms(selected, run_migrations)

    print("\nResults")
    for platform, success in results.items():
        print(f"  {platform:<10} {'deployed' if success else 'FAILED'}")
    print()
    return bool(results) and all(results.values())


def show_project_info() -> None:
    """Show the project location and which common files exist."""
    clear_screen()
    cwd = Path(".")

    heading("Project information")
    print(f"Location: {cwd.absolute()}")

    framework = detect_framework()
    print(f"Framework: {framework or 'not detected'}")

    print("\nFiles:")
    has_config = any(cwd.glob("deployment.*"))
    print(f"  {'found  ' if has_config else 'missing'}  deployment config")
    for file_name in ["app.py", "manage.py", "wsgi.py", "requirements.txt", ".env"]:
        found = (cwd / file_name).exists()
        print(f"  {'found  ' if found else 'missing'}  {file_name}")
    print()


def quick_check() -> None:
    """Run a short readiness check."""
    framework = detect_framework()
    if not framework:
        print("Could not detect the framework.")
        return

    deployer = Deployer(".")
    is_ready, results = deployer.check_deployment_readiness(framework)

    print()
    print_check_results(results)
    print("\nReady to deploy.\n" if is_ready else "\nNot ready yet.\n")


def _write_env_values(env_vars: dict, env_path: Path) -> Tuple[List[str], List[str]]:
    """Append KEY=VALUE pairs to a .env file without overwriting existing keys.

    Returns (written_keys, skipped_keys). Values are never printed. New files are
    created with owner-only permissions where the OS supports it.
    """
    existing_keys = set()
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and "=" in stripped:
                existing_keys.add(stripped.split("=", 1)[0].strip())

    written: List[str] = []
    skipped: List[str] = []
    lines: List[str] = []
    for key, value in env_vars.items():
        if key in existing_keys:
            skipped.append(key)
        else:
            lines.append(f"{key}={value}")
            written.append(key)

    if lines:
        needs_newline = (
            env_path.exists()
            and env_path.stat().st_size > 0
            and not env_path.read_bytes().endswith(b"\n")
        )
        fd = os.open(env_path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
        with os.fdopen(fd, "a", encoding="utf-8") as f:
            if needs_newline:
                f.write("\n")
            f.write("".join(line + "\n" for line in lines))
    return written, skipped


def _ensure_env_is_gitignored(project_dir: Path) -> bool:
    """Make sure .env is listed in .gitignore so secrets are not committed by accident.

    Returns True if the entry was added, False if it was already covered.
    """
    gitignore = project_dir / ".gitignore"
    covered = {".env", "/.env", ".env*", "*.env"}
    if gitignore.exists():
        entries = {
            line.strip() for line in gitignore.read_text(encoding="utf-8").splitlines()
        }
        if entries & covered:
            return False
        needs_newline = (
            gitignore.stat().st_size > 0 and not gitignore.read_bytes().endswith(b"\n")
        )
    else:
        needs_newline = False

    with open(gitignore, "a", encoding="utf-8") as f:
        if needs_newline:
            f.write("\n")
        f.write(".env\n")
    return True


def setup_wizard() -> None:
    """Ask a few questions and write deployment.yaml (or deployment.json)."""
    clear_screen()
    heading("Deployment setup")

    cwd = Path(".")
    existing_config = None
    for config_file in ["deployment.yaml", "deployment.yml", "deployment.json"]:
        if (cwd / config_file).exists():
            existing_config = config_file
            break

    if existing_config:
        if not ask_yes_no(f"Found existing {existing_config}. Overwrite it?"):
            print("\nSetup cancelled.\n")
            return

    platform = choose_option(
        "Which platform do you want to deploy to?",
        ["Render", "Railway", "Vercel", "Heroku"],
    ).lower()

    while True:
        app_name = input("\nEnter your app name (no spaces): ").strip()
        if app_name and " " not in app_name:
            break
        print("Please enter a valid app name without spaces.")

    config_data: Dict[str, Any] = {
        "platform": platform,
        "app_name": app_name,
    }

    # Optional here, but Render needs one for the first deploy and no single
    # default fits Flask, Django and FastAPI.
    start_command = input(
        "\nProduction start command, e.g. 'gunicorn wsgi:app' (Enter to skip): "
    ).strip()
    if start_command:
        config_data["start_command"] = start_command

    if ask_yes_no("Add environment variables?"):
        env_vars = {}
        print("\nEnter each as KEY=VALUE. Leave the line blank to finish.")
        while True:
            env_input = input("  > ").strip()
            if not env_input:
                break
            if "=" in env_input:
                key, value = env_input.split("=", 1)
                env_vars[key.strip()] = value.strip()
            else:
                print("  Format: KEY=VALUE")
        if env_vars:
            written, skipped = _write_env_values(env_vars, cwd / ".env")
            if written:
                print(f"\nSaved to .env: {', '.join(written)}")
            if skipped:
                print(f"Already in .env, left unchanged: {', '.join(skipped)}")
            if _ensure_env_is_gitignored(cwd):
                print("Added .env to .gitignore so it is not committed.")
            print("Values are stored only in .env, not in the deployment config.")
            print("They are not uploaded to the platform. Set them in its dashboard.")

    if ask_yes_no("Use JSON instead of YAML?"):
        config_path = cwd / "deployment.json"
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=2)
    else:
        config_path = cwd / "deployment.yaml"
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)

    print(f"\nCreated {config_path.name}.")
    print("Next: multi-platform-deployer check\n")


def show_help() -> None:
    """Print CLI help."""
    print("""
multi-platform-deployer: check a Flask, Django or FastAPI app and deploy it.

USAGE:
    multi-platform-deployer <command> [options]
    python -m multi_platform_deployer.cli <command> [options]

COMMANDS:
    setup       Create the deployment config (deployment.yaml)
    check       Check that your app is ready to deploy
    run         Deploy your app
    info        Show project information
    health      Check that a deployed app is up
    rollback    Restore the previous snapshot, or with --live roll back the running Render service

OPTIONS:
    --platform NAME    With 'run': deploy without prompts (render, railway, vercel or heroku)
    --multi            With 'run': deploy to several platforms
    --dry-run          With 'run' or 'rollback --live': print the steps and change nothing
    --migrate          With 'run': run database migrations first
    --url URL          With 'health': base URL of the app
    --endpoints PATHS  With 'health': comma-separated paths to request (default: /)
    --live             With 'rollback': roll back the running service (Render only)
    -h, --help         Show this help

EXAMPLES:
    multi-platform-deployer setup
    multi-platform-deployer check
    multi-platform-deployer run --platform render --dry-run
    multi-platform-deployer run --platform render
    multi-platform-deployer health --url https://my-app.onrender.com --endpoints /,/health
    multi-platform-deployer rollback --live --dry-run
""")


def cmd_setup(args: argparse.Namespace) -> int:
    setup_wizard()
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    return 0 if check_readiness() else 1


def cmd_run(args: argparse.Namespace) -> int:
    if args.multi:
        succeeded = multi_deploy()
    else:
        succeeded = deploy(
            platform=args.platform,
            dry_run=args.dry_run,
            run_migrations=args.migrate,
        )
    return 0 if succeeded else 1


def cmd_info(args: argparse.Namespace) -> int:
    show_project_info()
    return 0


def cmd_health(args: argparse.Namespace) -> int:
    url = args.url or input("Enter your deployed app URL: ").strip()
    if not url:
        print("A URL is required for the health check.\n")
        return 1

    deployer = Deployer(".")
    endpoints = args.endpoints.split(",") if args.endpoints else ["/"]
    print(f"\nChecking {url}")
    health = deployer.check_health(url, endpoints)  # prints the summary itself
    return 0 if health.get("server_up") else 1


def _cmd_rollback_live(args: argparse.Namespace) -> int:
    dry_run = bool(getattr(args, "dry_run", False))
    deployer = Deployer(".", dry_run=dry_run)
    if not dry_run and not ask_yes_no(
        "This rolls back the LIVE service on your platform. Continue?"
    ):
        print("Rollback cancelled.\n")
        return 0

    if not deployer.rollback_live(getattr(args, "platform", None)):
        print(
            "\nLive rollback failed. The running service was not changed by this tool.\n"
        )
        return 1

    if dry_run:
        print("\nDry run complete. Nothing was changed.\n")
    else:
        print(
            "\nRollback requested. Check the platform dashboard until the service is live.\n"
        )
    return 0


def cmd_rollback(args: argparse.Namespace) -> int:
    if getattr(args, "live", False):
        return _cmd_rollback_live(args)

    deployer = Deployer(".")
    if not ask_yes_no("Restore the project files from the previous snapshot?"):
        print("Rollback cancelled.\n")
        return 0

    print("\nRestoring project files from the previous deployment snapshot")
    try:
        restored = deployer.rollback_manager.rollback_to_previous()
    except Exception as exc:  # pragma: no cover - user feedback path
        print(f"\nRollback failed: {exc}\n")
        return 1

    if not restored:
        print("\nRollback failed: no previous snapshot could be restored.\n")
        return 1

    print("\nProject files restored from the previous snapshot.")
    print(
        "The live deployment was not changed. Redeploy the restored code on your platform.\n"
    )
    return 0


def _use_utf8_output() -> None:
    """Keep Windows consoles (cp1252) from failing on non-ASCII file names or messages."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")


def main() -> int:
    """CLI entry point."""
    _use_utf8_output()

    parser = argparse.ArgumentParser(
        prog="multi-platform-deployer",
        description="Deploy applications to multiple cloud platforms",
        add_help=False,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    setup_parser = subparsers.add_parser(
        "setup", help="Create deployment.yaml configuration"
    )
    setup_parser.set_defaults(func=cmd_setup)

    check_parser = subparsers.add_parser("check", help="Check deployment readiness")
    check_parser.set_defaults(func=cmd_check)

    run_parser = subparsers.add_parser("run", help="Deploy your application")
    run_parser.add_argument(
        "--multi",
        action="store_true",
        help="Deploy to multiple platforms (interactive)",
    )
    run_parser.add_argument(
        "--platform",
        choices=["render", "railway", "vercel", "heroku"],
        help="Deploy to this platform without prompts (for scripts and CI)",
    )
    run_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show the exact steps and commands without executing anything",
    )
    run_parser.add_argument(
        "--migrate",
        action="store_true",
        help="Run database migrations before deploying (non-interactive mode)",
    )
    run_parser.set_defaults(func=cmd_run)

    info_parser = subparsers.add_parser("info", help="Show project information")
    info_parser.set_defaults(func=cmd_info)

    health_parser = subparsers.add_parser("health", help="Check deployed app health")
    health_parser.add_argument(
        "--url", type=str, help="App URL (e.g., https://my-app.onrender.com)"
    )
    health_parser.add_argument(
        "--endpoints", type=str, help="Comma-separated endpoints to check"
    )
    health_parser.set_defaults(func=cmd_health)

    rollback_parser = subparsers.add_parser(
        "rollback", help="Rollback to previous deployment"
    )
    rollback_parser.add_argument(
        "--live",
        action="store_true",
        help=(
            "Roll back the running service on its platform (Render only). "
            "Does not touch local files."
        ),
    )
    rollback_parser.add_argument(
        "--platform",
        choices=["render", "railway", "vercel", "heroku"],
        help=(
            "With --live: platform to roll back "
            "(default: the platform of the latest deployment record)"
        ),
    )
    rollback_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="With --live: show the API calls without making them",
    )
    rollback_parser.set_defaults(func=cmd_rollback)

    parser.add_argument("-h", "--help", action="store_true", help="Show help message")

    args = parser.parse_args()

    if args.help or not args.command:
        show_help()
        return 0

    try:
        exit_code: int = args.func(args)
        return exit_code
    except KeyboardInterrupt:  # pragma: no cover - user interrupt
        print("\n\nCancelled.\n")
        return 1
    except Exception as exc:  # pragma: no cover - defensive logging
        print(f"\nError: {exc}\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
