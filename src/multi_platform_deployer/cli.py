"""Multi-Platform Deployer command line interface."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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


def print_banner() -> None:
    """Print the CLI banner."""

    print("\n" + "=" * 60)
    print("  🚀 MULTI-PLATFORM DEPLOYER")
    print("=" * 60 + "\n")


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
    """Run interactive readiness checks."""

    clear_screen()
    print_banner()
    print("📋 CHECKING DEPLOYMENT READINESS")
    print("-" * 60)

    framework = detect_framework()
    if not framework:
        print("\n⚠️  Could not auto-detect framework.")
        framework = choose_option(
            "Which framework are you using?",
            ["Flask", "Django", "FastAPI"],
        ).lower()
    else:
        print(f"\n✓ Detected: {framework.upper()}")

    print(f"\n🔍 Analyzing your {framework.upper()} application...")
    deployer = Deployer(".")
    is_ready, results = deployer.check_deployment_readiness(framework)

    print("\n" + "=" * 60)
    for result in results:
        icon = "✓" if result.passed else "✗"
        status = "PASS" if result.passed else "FAIL"
        category = getattr(result, "category", "framework").upper()
        print(f"{icon} [{category:<8}] {result.name:<30} [{status}]")
        if result.message:
            print(f"  └─ {result.message}")
    print("=" * 60)

    if is_ready:
        print("\n✅ YOUR APPLICATION IS READY FOR DEPLOYMENT!\n")
        return True

    failures = sum(1 for result in results if not result.passed)
    print(f"\n❌ {failures} ISSUE(S) FOUND - fix before deploying\n")
    return False


def deploy(
    platform: Optional[str] = None,
    dry_run: bool = False,
    run_migrations: bool = False,
) -> bool:
    """
    Deploy a single platform.

    Without a platform, runs the interactive wizard. With one, runs
    non-interactively (used by 'run --platform ...' and CI).
    Returns True on success.
    """
    interactive = platform is None

    if interactive:
        clear_screen()
    print_banner()
    print("🚀 DEPLOYMENT WIZARD" if interactive else "🚀 DEPLOYMENT")
    print("-" * 60)
    if dry_run:
        print("🔍 DRY RUN: commands will be printed, nothing will be executed.\n")

    framework = detect_framework()
    if framework is None:
        if not interactive:
            print("❌ Could not detect the framework (Flask, Django or FastAPI).\n")
            return False
        framework = choose_option(
            "Which framework are you using?",
            ["Flask", "Django", "FastAPI"],
        ).lower()

    deployer = Deployer(".", dry_run=dry_run)
    is_ready, _ = deployer.check_deployment_readiness(framework)
    if not is_ready:
        print("\n❌ Application not ready for deployment.\n")
        return False

    if interactive:
        platform = choose_option(
            "Which platform do you want to deploy to?",
            ["Render", "Railway", "Vercel", "Heroku"],
        ).lower()
        run_migrations = ask_yes_no("Run database migrations?")

    if platform is None:
        return False
    print(f"\n⏳ {'Planning' if dry_run else 'Deploying'} to {platform.upper()}...")
    success = deployer.deploy(platform, run_migrations=run_migrations)

    if not success:
        print("\n❌ DEPLOYMENT FAILED\n")
        return False

    if dry_run:
        print("\n✅ DRY RUN COMPLETE. Re-run without --dry-run to deploy.\n")
        return True

    print(f"\n✅ DEPLOYMENT SUCCESSFUL on {platform.upper()}!\n")
    if interactive and ask_yes_no("Check application health?"):
        url = input("Enter your app URL: ").strip()
        health = deployer.check_health(url)
        deployer.health_checker.print_summary(health)
    return True


def multi_deploy() -> bool:
    """Deploy to multiple platforms interactively. Returns True only if every platform succeeded."""

    clear_screen()
    print_banner()
    print("🚀 MULTI-PLATFORM DEPLOYMENT")
    print("-" * 60)

    framework = detect_framework() or choose_option(
        "Which framework are you using?",
        ["Flask", "Django", "FastAPI"],
    ).lower()

    deployer = Deployer(".")
    is_ready, _ = deployer.check_deployment_readiness(framework)
    if not is_ready:
        print("\n❌ Application not ready for deployment.\n")
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
    print(f"\n⏳ Deploying to: {', '.join(p.upper() for p in selected)}...")
    results = deployer.deploy_to_multiple_platforms(selected, run_migrations)

    print("\n" + "=" * 60)
    print("DEPLOYMENT RESULTS:")
    print("=" * 60)
    for platform, success in results.items():
        icon = "✓" if success else "✗"
        status = "SUCCESS" if success else "FAILED"
        print(f"{icon} {platform.upper():<20} [{status}]")
    print("\n")
    return bool(results) and all(results.values())


def show_project_info() -> None:
    """Display project metadata and detected files."""

    clear_screen()
    print_banner()
    cwd = Path(".")

    has_requirements = (cwd / "requirements.txt").exists()
    has_config = any(cwd.glob("deployment.*"))
    has_env = (cwd / ".env").exists()

    print("📁 PROJECT INFORMATION")
    print("-" * 60)
    print(f"\n📍 Location: {cwd.absolute()}")
    print("\n📦 Files detected:")
    print(f"  {'✓' if has_requirements else '✗'} requirements.txt")
    print(f"  {'✓' if has_config else '✗'} deployment config")
    print(f"  {'✓' if has_env else '✗'} .env file")

    framework = detect_framework()
    print(f"\n🐍 Detected Framework: {framework.upper() if framework else 'Unknown'}")

    print("\n📄 Common files:")
    for file_name in ["app.py", "manage.py", "wsgi.py", "requirements.txt", ".env"]:
        exists = "✓" if (cwd / file_name).exists() else "✗"
        print(f"  {exists} {file_name}")
    print("\n")


def quick_check() -> None:
    """Run a terse readiness check."""

    deployer = Deployer(".")
    framework = detect_framework()
    if not framework:
        print("Could not detect framework.")
        return

    print(f"\n🔍 Checking {framework.upper()} app...")
    is_ready, results = deployer.check_deployment_readiness(framework)

    print("\n" + "=" * 60)
    for result in results:
        icon = "✓" if result.passed else "✗"
        category = getattr(result, "category", "framework").upper()
        message = f" - {result.message}" if result.message else ""
        print(f"{icon} [{category:<8}] {result.name}{message}")
    print("=" * 60)

    if is_ready:
        print("\n✅ Ready to deploy!\n")
    else:
        print("\n❌ Not ready yet.\n")


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


def setup_wizard() -> None:
    """Interactive wizard to create deployment.yaml file."""

    clear_screen()
    print_banner()
    print("⚙️  DEPLOYMENT CONFIGURATION WIZARD")
    print("-" * 60)

    # Check if deployment config already exists
    cwd = Path(".")
    existing_config = None
    for config_file in ["deployment.yaml", "deployment.yml", "deployment.json"]:
        if (cwd / config_file).exists():
            existing_config = config_file
            break

    if existing_config:
        if not ask_yes_no(f"\n⚠️  Found existing {existing_config}. Overwrite it?"):
            print("\nSetup cancelled.\n")
            return

    print("\n📋 Let's set up your deployment configuration!\n")

    # Ask for platform
    platform = choose_option(
        "Which platform do you want to deploy to?",
        ["Render", "Railway", "Vercel", "Heroku"],
    ).lower()

    # Ask for app name
    while True:
        app_name = input("\nEnter your app name (no spaces): ").strip()
        if app_name and " " not in app_name:
            break
        print("Please enter a valid app name without spaces.")

    # Ask for environment variables
    config_data: Dict[str, Any] = {
        "platform": platform,
        "app_name": app_name,
    }

    if ask_yes_no("\nAdd environment variables?"):
        env_vars = {}
        print("\n(Enter each as KEY=VALUE, blank line to finish)")
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
                print(f"\n🔐 Saved to .env: {', '.join(written)}")
            if skipped:
                print(f"⚠️  Already in .env, left unchanged: {', '.join(skipped)}")
            print("   Values are stored only in .env (git-ignored), not in the deployment config.")

    # Ask for services (Railway-specific)
    if platform == "railway" and ask_yes_no("\nAdd services configuration?"):
        print("\n(Service configuration is optional for Railway)")
        config_data["services"] = [
            {
                "name": "web",
                "buildCommand": "pip install -r requirements.txt",
                "startCommand": "gunicorn config.wsgi",
                "port": 8000,
            }
        ]

    # Write configuration
    use_json = ask_yes_no("\nUse JSON format (vs YAML)?")

    if use_json:
        import json
        config_path = cwd / "deployment.json"
        with open(config_path, "w") as f:
            json.dump(config_data, f, indent=2)
        print(f"\n✅ Created {config_path.name}")
    else:
        import yaml
        config_path = cwd / "deployment.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)
        print(f"\n✅ Created {config_path.name}")

    print(f"\n📝 Configuration saved!")
    print(f"\nYou can now run: py deploy.py run\n")


def show_help() -> None:
    """Print CLI help."""

    print(
        """
===============================================================
          MULTI-PLATFORM DEPLOYER - CLI
===============================================================

USAGE:
    multi-platform-deployer <command> [options]
    py deploy.py <command> [options]        (if you added the deploy.py shim)
    python -m multi_platform_deployer.cli <command> [options]

COMMANDS:
    setup              Create deployment.yaml configuration (first time?)
    check              Check if your app is ready for deployment
    run                Deploy your app (use --multi for multiple platforms)
    info               Show project information
    health             Check deployed app health
    rollback           Rollback to previous deployment

EXAMPLES:
    py deploy.py setup
    py deploy.py check
    py deploy.py run
    py deploy.py run --multi
    py deploy.py info
    py deploy.py health --url https://...
    py deploy.py rollback

OPTIONS:
    --multi            Deploy to multiple platforms (with 'run')
    --url URL          App URL for health check
    --endpoints PATHS  Comma-separated endpoints to check (default: /)
    -h, --help         Show this help message

WORKFLOW:
    1. py deploy.py setup   (create deployment config)
    2. py deploy.py check   (verify app is ready)
    3. py deploy.py run     (deploy your app)
    4. py deploy.py health --url <your-url>

"""
    )


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
        print("❌ URL is required for health check.\n")
        return 1

    deployer = Deployer(".")
    endpoints = (
        args.endpoints.split(",")
        if args.endpoints
        else ["/"]
    )
    print(f"\n🏥 Checking health of {url}...")
    health = deployer.check_health(url, endpoints)
    deployer.health_checker.print_summary(health)
    return 0 if health.get("server_up") else 1


def cmd_rollback(args: argparse.Namespace) -> int:
    deployer = Deployer(".")
    if not ask_yes_no("⚠️  Are you sure you want to rollback?"):
        print("Rollback cancelled.\n")
        return 0

    print("\n⏳ Restoring project files from the previous deployment snapshot...")
    try:
        restored = deployer.rollback_manager.rollback_to_previous()
    except Exception as exc:  # pragma: no cover - user feedback path
        print(f"\n❌ ROLLBACK FAILED: {exc}\n")
        return 1

    if not restored:
        print("\n❌ ROLLBACK FAILED: no previous snapshot could be restored.\n")
        return 1

    print("\n✅ Project files restored from the previous snapshot.")
    print("⚠️  The live deployment was NOT changed. Redeploy the restored code on your platform.\n")
    return 0


def _use_utf8_output() -> None:
    """Windows consoles default to cp1252, which cannot print the emoji used in messages."""
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

    setup_parser = subparsers.add_parser("setup", help="Create deployment.yaml configuration")
    setup_parser.set_defaults(func=cmd_setup)

    check_parser = subparsers.add_parser("check", help="Check deployment readiness")
    check_parser.set_defaults(func=cmd_check)

    run_parser = subparsers.add_parser("run", help="Deploy your application")
    run_parser.add_argument("--multi", action="store_true", help="Deploy to multiple platforms (interactive)")
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
    health_parser.add_argument("--url", type=str, help="App URL (e.g., https://my-app.onrender.com)")
    health_parser.add_argument("--endpoints", type=str, help="Comma-separated endpoints to check")
    health_parser.set_defaults(func=cmd_health)

    rollback_parser = subparsers.add_parser("rollback", help="Rollback to previous deployment")
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
        print("\n\n⏸️  Operation cancelled by user.\n")
        return 1
    except Exception as exc:  # pragma: no cover - defensive logging
        print(f"\n❌ Error: {exc}\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

