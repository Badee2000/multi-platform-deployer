"""Multi-Platform Deployer command line interface."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import List, Optional

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

    flask_files = ["app.py", "wsgi.py", "main.py"]
    if any((cwd / file_name).exists() for file_name in flask_files):
        return "flask"

    fastapi_files = ["app.py", "main.py"]
    if any((cwd / file_name).exists() for file_name in fastapi_files):
        return "fastapi"

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


def deploy() -> None:
    """Run the interactive deployment wizard for a single platform."""

    clear_screen()
    print_banner()
    print("🚀 DEPLOYMENT WIZARD")
    print("-" * 60)

    framework = detect_framework() or choose_option(
        "Which framework are you using?",
        ["Flask", "Django", "FastAPI"],
    ).lower()

    deployer = Deployer(".")
    is_ready, _ = deployer.check_deployment_readiness(framework)
    if not is_ready:
        print("\n❌ Application not ready for deployment.\n")
        return

    platform = choose_option(
        "Which platform do you want to deploy to?",
        ["Render", "Railway", "Vercel", "Heroku"],
    ).lower()

    run_migrations = ask_yes_no("Run database migrations?")
    print(f"\n⏳ Deploying to {platform.upper()}...")
    success = deployer.deploy(platform, run_migrations=run_migrations)

    if success:
        print(f"\n✅ DEPLOYMENT SUCCESSFUL on {platform.upper()}!\n")
        if ask_yes_no("Check application health?"):
            url = input("Enter your app URL: ").strip()
            health = deployer.check_health(url)
            deployer.health_checker.print_summary(health)
    else:
        print("\n❌ DEPLOYMENT FAILED\n")


def multi_deploy() -> None:
    """Deploy to multiple platforms interactively."""

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
        return

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
        return

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
    config_data = {
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
            config_data["env"] = env_vars

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
        config_file = cwd / "deployment.json"
        with open(config_file, "w") as f:
            json.dump(config_data, f, indent=2)
        print(f"\n✅ Created {config_file.name}")
    else:
        import yaml
        config_file = cwd / "deployment.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)
        print(f"\n✅ Created {config_file.name}")

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
    py deploy.py <command> [options]
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
        multi_deploy()
    else:
        deploy()
    return 0


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
    return 0


def cmd_rollback(args: argparse.Namespace) -> int:
    deployer = Deployer(".")
    if not ask_yes_no("⚠️  Are you sure you want to rollback?"):
        print("Rollback cancelled.\n")
        return 0

    print("\n⏳ Rolling back to previous deployment...")
    try:
        deployer.rollback_manager.rollback_to_previous()
        print("\n✅ ROLLBACK SUCCESSFUL!\n")
        return 0
    except Exception as exc:  # pragma: no cover - user feedback path
        print(f"\n❌ ROLLBACK FAILED: {exc}\n")
        return 1


def main() -> int:
    """CLI entry point."""

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
    run_parser.add_argument("--multi", action="store_true", help="Deploy to multiple platforms")
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
        return args.func(args)
    except KeyboardInterrupt:  # pragma: no cover - user interrupt
        print("\n\n⏸️  Operation cancelled by user.\n")
        return 1
    except Exception as exc:  # pragma: no cover - defensive logging
        print(f"\n❌ Error: {exc}\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

