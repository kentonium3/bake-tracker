"""
Configuration management for the Seasonal Baking Tracker application.

This module handles:
- Database path configuration
- Application settings
- Environment-specific configuration (development vs. production)
- User preferences
"""

import os
from pathlib import Path
from typing import Optional

from .constants import (
    APP_NAME,
    APP_VERSION,
    DATABASE_FILENAME,
    DATABASE_VERSION,
)


class Config:
    """
    Application configuration manager.

    Handles all configuration settings including database paths,
    environment settings, and user preferences.
    """

    def __init__(self, environment: str = "production"):
        """
        Initialize configuration.

        Args:
            environment: Environment mode - 'production' or 'development'
        """
        self.environment = environment
        self._app_name = APP_NAME
        self._app_version = APP_VERSION
        self._database_version = DATABASE_VERSION

        # Determine base directory
        if environment == "development":
            # Use project data/ directory for development
            self._base_dir = self._get_project_data_dir()
        else:
            # Use user's Documents folder for production
            self._base_dir = self._get_user_documents_dir()

        # Database configuration
        self._database_dir = self._base_dir
        self._database_path = self._database_dir / DATABASE_FILENAME

        # Ensure directories exist
        self._ensure_directories()

    def _get_project_data_dir(self) -> Path:
        """
        Get the project's data directory for development.

        Returns:
            Path to project data/ directory
        """
        # Get the project root (4 levels up from this file)
        project_root = Path(__file__).parent.parent.parent
        data_dir = project_root / "data"
        return data_dir

    def _get_user_documents_dir(self) -> Path:
        """
        Get the user's Documents directory for production.

        Returns:
            Path to user's Documents folder with app subdirectory
        """
        # Try to get user's Documents folder
        if os.name == "nt":  # Windows
            # Try to get Documents folder from Windows
            documents = Path(os.path.expanduser("~")) / "Documents"
        else:  # Linux/Mac
            documents = Path.home() / "Documents"

        # Create app-specific subdirectory
        app_dir = documents / "BakeTracker"
        return app_dir

    def _ensure_directories(self):
        """Create necessary directories if they don't exist."""
        self._database_dir.mkdir(parents=True, exist_ok=True)

    @property
    def app_name(self) -> str:
        """Application name."""
        return self._app_name

    @property
    def app_version(self) -> str:
        """Application version."""
        return self._app_version

    @property
    def database_version(self) -> str:
        """Database schema version."""
        return self._database_version

    @property
    def database_path(self) -> Path:
        """Full path to the database file."""
        return self._database_path

    @property
    def database_url(self) -> str:
        """
        SQLAlchemy database URL.

        Returns:
            Database URL string for SQLAlchemy
        """
        # Use forward slashes for SQLite URL
        db_path_str = str(self._database_path).replace("\\", "/")
        return f"sqlite:///{db_path_str}"

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment == "development"

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.environment == "production"

    def get_backup_path(self, backup_name: Optional[str] = None) -> Path:
        """
        Get path for database backup.

        Args:
            backup_name: Optional custom backup name. If None, generates timestamp-based name.

        Returns:
            Path to backup file
        """
        if backup_name is None:
            from datetime import datetime

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"bake_tracker_backup_{timestamp}.db"

        return self._database_dir / backup_name

    def database_exists(self) -> bool:
        """
        Check if database file exists.

        Returns:
            True if database file exists, False otherwise
        """
        return self._database_path.exists()

    def __repr__(self) -> str:
        """String representation of config."""
        return (
            f"Config(environment='{self.environment}', " f"database_path='{self._database_path}')"
        )


# Global configuration instances
_config_instance: Optional[Config] = None


def get_config(environment: Optional[str] = None) -> Config:
    """
    Get the global configuration instance.

    This function implements a singleton pattern for the configuration.
    Once created, the singleton's environment cannot be changed by passing
    a different environment argument - this prevents accidental database
    switching mid-session.

    Args:
        environment: Optional environment for initial creation. If None, uses
                    BAKING_TRACKER_ENV or defaults to production. Ignored if
                    singleton already exists.

    Returns:
        Config instance
    """
    global _config_instance

    if _config_instance is None:
        # First call - create the singleton
        if environment is None:
            # Check environment variable, default to production
            environment = os.environ.get("BAKING_TRACKER_ENV", "production")
        _config_instance = Config(environment)
    elif environment is not None and environment != _config_instance.environment:
        # Singleton exists but caller requested different environment
        # Log warning but don't replace singleton to prevent data loss
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(
            f"get_config() called with environment='{environment}' but singleton "
            f"already exists with environment='{_config_instance.environment}'. "
            f"Returning existing singleton to prevent database switching."
        )

    return _config_instance


def reset_config():
    """
    Reset the global configuration instance.

    Useful for testing.
    """
    global _config_instance
    _config_instance = None


# Convenience function for common use case
def get_database_url() -> str:
    """
    Get the database URL.

    Returns:
        SQLAlchemy database URL string
    """
    return get_config().database_url


def get_database_path() -> Path:
    """
    Get the database file path.

    Returns:
        Path to database file
    """
    return get_config().database_path
