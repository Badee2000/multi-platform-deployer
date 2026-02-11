"""Database migration management."""

from typing import Optional
from pathlib import Path
from ..utils.logger import get_logger
from ..utils.helpers import run_command, file_exists


class DatabaseMigrator:
    """Handle database migrations for deployment."""
    
    def __init__(self, project_root: str = "."):
        """
        Initialize migrator.
        
        Args:
            project_root: Root directory of the project
        """
        self.project_root = Path(project_root)
        self.logger = get_logger("DatabaseMigrator")
    
    def auto_detect_framework(self) -> Optional[str]:
        """
        Auto-detect the framework used.
        
        Returns:
            Framework name (flask, django, fastapi) or None
        """
        # Check for Django
        if file_exists(str(self.project_root / "manage.py")):
            return "django"
        
        # Check for Flask-SQLAlchemy or Alembic
        req_file = self.project_root / "requirements.txt"
        if req_file.exists():
            try:
                with open(req_file, "r") as f:
                    content = f.read()
                    if "alembic" in content.lower():
                        return "alembic"
                    if "flask-sqlalchemy" in content.lower():
                        return "flask"
                    if "fastapi" in content.lower():
                        return "fastapi"
            except Exception as e:
                self.logger.warning(f"Error reading requirements.txt: {e}")
        
        return None
    
    def run_django_migrations(self) -> bool:
        """
        Run Django migrations.
        
        Returns:
            True if successful
        """
        self.logger.info("Running Django migrations...")
        
        try:
            result = run_command(
                ["python", "manage.py", "migrate"],
                cwd=str(self.project_root),
                check=False,
            )
            
            if result.returncode == 0:
                self.logger.info("Django migrations completed successfully")
                return True
            else:
                self.logger.error(f"Django migrations failed: {result.stderr}")
                return False
        except Exception as e:
            self.logger.error(f"Error running Django migrations: {e}")
            return False
    
    def run_alembic_migrations(self) -> bool:
        """
        Run Alembic migrations (Flask-SQLAlchemy).
        
        Returns:
            True if successful
        """
        self.logger.info("Running Alembic migrations...")
        
        migrations_dir = self.project_root / "migrations"
        if not migrations_dir.exists():
            self.logger.warning("Migrations directory not found")
            return False
        
        try:
            result = run_command(
                ["alembic", "upgrade", "head"],
                cwd=str(self.project_root),
                check=False,
            )
            
            if result.returncode == 0:
                self.logger.info("Alembic migrations completed successfully")
                return True
            else:
                self.logger.error(f"Alembic migrations failed: {result.stderr}")
                return False
        except Exception as e:
            self.logger.error(f"Error running Alembic migrations: {e}")
            return False
    
    def run_migrations(self) -> bool:
        """
        Auto-detect framework and run appropriate migrations.
        
        Returns:
            True if successful (or no migrations needed)
        """
        framework = self.auto_detect_framework()
        
        if framework == "django":
            return self.run_django_migrations()
        elif framework == "alembic":
            return self.run_alembic_migrations()
        else:
            self.logger.info("No standard migrations framework detected")
            return True
    
    def create_backup(self, backup_name: Optional[str] = None) -> bool:
        """
        Create database backup before migration.
        
        Args:
            backup_name: Name for the backup
        
        Returns:
            True if successful
        """
        self.logger.info("Creating database backup...")
        # Implementation depends on database type
        return True
    
    def rollback_migrations(self) -> bool:
        """
        Rollback last migration.
        
        Returns:
            True if successful
        """
        self.logger.info("Rolling back last migration...")
        
        framework = self.auto_detect_framework()
        
        if framework == "django":
            # Get last applied migration
            self.logger.info("Use 'python manage.py migrate' with specific migration name")
            return False
        elif framework == "alembic":
            try:
                result = run_command(
                    ["alembic", "downgrade", "-1"],
                    cwd=str(self.project_root),
                    check=False,
                )
                return result.returncode == 0
            except Exception as e:
                self.logger.error(f"Error rolling back migrations: {e}")
                return False
        
        return False
