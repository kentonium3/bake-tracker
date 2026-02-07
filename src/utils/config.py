"""
Configuration management for the Seasonal Baking Tracker application.

This module handles:
- Database path configuration
- Application settings
- Environment-specific configuration (development vs. production)
- User preferences
"""

import logging
import os
import sys
from pathlib import Path
from typing import Optional

from .constants import (
    APP_NAME,
    APP_VERSION,
    DATABASE_FILENAME,
    DATABASE_VERSION,
)

logger = logging.getLogger(__name__)


class Config:
    """Application configuration manager.

    Handles all configuration settings including:
    - Database paths and connection settings
    - PostgreSQL/SQLite database URL abstraction
    - Environment settings (development/production)
    - Feature flags for gradual rollout
    - UI appearance and theme settings
    - Health check configuration

    All properties support environment variable overrides with sensible defaults.
    Invalid values fall back to defaults with warning logged.

    Environment Variables:
        BAKING_TRACKER_ENV: Environment mode (production/development)
        BAKE_TRACKER_DB_TYPE: Database type (sqlite/postgresql)
        BAKE_TRACKER_DB_TIMEOUT: Connection timeout (default: 30)
        BAKE_TRACKER_DB_POOL_SIZE: Connection pool size (default: 5)
        BAKE_TRACKER_DB_POOL_RECYCLE: Connection recycle time (default: 3600)
        DATABASE_URL: PostgreSQL connection URL (required if DB_TYPE=postgresql)
        ENABLE_AUDIT: Enable audit trail (default: false)
        ENABLE_HEALTH: Enable health checks (default: true)
        ENABLE_PERF_MON: Enable performance monitoring (default: false)
        BAKE_TRACKER_THEME: UI color theme (default: blue)
        BAKE_TRACKER_APPEARANCE: UI appearance mode (default: system)
        BAKE_TRACKER_HEALTH_INTERVAL: Health check interval (default: 30)
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
            # Use platform-specific app data dir (NOT Documents — iCloud sync corrupts SQLite WAL)
            self._base_dir = self._get_app_data_dir()

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

    def _get_app_data_dir(self) -> Path:
        """
        Get the platform-specific app data directory for production.

        Uses directories that are NOT synced by cloud services (iCloud, OneDrive)
        to prevent SQLite WAL corruption from cloud sync interference.

        Returns:
            Path to app data directory
        """
        if sys.platform == "darwin":
            return Path.home() / "Library" / "Application Support" / "BakeTracker"
        elif os.name == "nt":
            app_data = os.environ.get("APPDATA")
            if app_data:
                return Path(app_data) / "BakeTracker"
            return Path.home() / "AppData" / "Roaming" / "BakeTracker"
        else:
            return Path.home() / ".local" / "share" / "BakeTracker"

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
    def database_type(self) -> str:
        """Database type: 'sqlite' (default) or 'postgresql'.

        Environment variable: BAKE_TRACKER_DB_TYPE
        Default: sqlite
        """
        db_type = os.environ.get("BAKE_TRACKER_DB_TYPE", "sqlite").lower()
        if db_type not in ("sqlite", "postgresql"):
            logger.warning(f"Invalid BAKE_TRACKER_DB_TYPE '{db_type}', using sqlite")
            return "sqlite"
        return db_type

    @property
    def database_url(self) -> str:
        """SQLAlchemy database URL.

        For PostgreSQL: Uses DATABASE_URL environment variable.
        For SQLite: Generates path-based URL (current behavior).

        Returns:
            Database URL string for SQLAlchemy

        Raises:
            ValueError: If postgresql selected but DATABASE_URL not set.
        """
        if self.database_type == "postgresql":
            url = os.environ.get("DATABASE_URL")
            if not url:
                raise ValueError(
                    "DATABASE_URL environment variable required when "
                    "BAKE_TRACKER_DB_TYPE=postgresql"
                )
            return url

        # SQLite (default) - existing logic
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

    # =========================================================================
    # Database Connection Properties (T001)
    # =========================================================================

    @property
    def db_timeout(self) -> int:
        """Database connection timeout in seconds.

        Environment variable: BAKE_TRACKER_DB_TIMEOUT
        Default: 30
        """
        try:
            return int(os.environ.get("BAKE_TRACKER_DB_TIMEOUT", "30"))
        except ValueError:
            logger.warning("Invalid BAKE_TRACKER_DB_TIMEOUT, using default 30")
            return 30

    @property
    def db_pool_size(self) -> int:
        """Database connection pool size.

        Environment variable: BAKE_TRACKER_DB_POOL_SIZE
        Default: 5
        """
        try:
            return int(os.environ.get("BAKE_TRACKER_DB_POOL_SIZE", "5"))
        except ValueError:
            logger.warning("Invalid BAKE_TRACKER_DB_POOL_SIZE, using default 5")
            return 5

    @property
    def db_pool_recycle(self) -> int:
        """Database connection recycle time in seconds.

        Environment variable: BAKE_TRACKER_DB_POOL_RECYCLE
        Default: 3600 (1 hour)
        """
        try:
            return int(os.environ.get("BAKE_TRACKER_DB_POOL_RECYCLE", "3600"))
        except ValueError:
            logger.warning("Invalid BAKE_TRACKER_DB_POOL_RECYCLE, using default 3600")
            return 3600

    # =========================================================================
    # Database Connection Arguments (T003)
    # =========================================================================

    @property
    def db_connect_args(self) -> dict:
        """Database connection arguments for SQLAlchemy.

        Returns appropriate connect_args based on database_type:
        - SQLite: check_same_thread, timeout
        - PostgreSQL: (empty dict, connection params in URL)
        """
        if self.database_type == "postgresql":
            return {}

        # SQLite
        return {
            "check_same_thread": False,
            "timeout": self.db_timeout,
        }

    # =========================================================================
    # Feature Flags (T004)
    # =========================================================================

    def _parse_bool_env(self, var_name: str, default: bool) -> bool:
        """Parse boolean from environment variable.

        Args:
            var_name: Environment variable name
            default: Default value if not set

        Returns:
            Boolean value from environment or default
        """
        value = os.environ.get(var_name, str(default).lower())
        return value.lower() in ("true", "1", "yes")

    @property
    def feature_flags(self) -> dict:
        """Feature flags for gradual rollout of optional features.

        Flags:
            enable_audit_trail: Future observability (default: False)
                Env: ENABLE_AUDIT
            enable_health_checks: Current health service (default: True)
                Env: ENABLE_HEALTH
            enable_performance_monitoring: Future metrics (default: False)
                Env: ENABLE_PERF_MON
        """
        return {
            "enable_audit_trail": self._parse_bool_env("ENABLE_AUDIT", False),
            "enable_health_checks": self._parse_bool_env("ENABLE_HEALTH", True),
            "enable_performance_monitoring": self._parse_bool_env("ENABLE_PERF_MON", False),
        }

    # =========================================================================
    # UI Configuration Properties (T005)
    # =========================================================================

    @property
    def ui_theme(self) -> str:
        """CustomTkinter color theme.

        Environment variable: BAKE_TRACKER_THEME
        Default: blue
        Valid values: blue, dark-blue, green
        """
        valid_themes = ("blue", "dark-blue", "green")
        theme = os.environ.get("BAKE_TRACKER_THEME", "blue")
        if theme not in valid_themes:
            logger.warning(f"Invalid BAKE_TRACKER_THEME '{theme}', using blue")
            return "blue"
        return theme

    @property
    def ui_appearance(self) -> str:
        """CustomTkinter appearance mode.

        Environment variable: BAKE_TRACKER_APPEARANCE
        Default: system
        Valid values: system, light, dark
        """
        valid_modes = ("system", "light", "dark")
        mode = os.environ.get("BAKE_TRACKER_APPEARANCE", "system")
        if mode not in valid_modes:
            logger.warning(f"Invalid BAKE_TRACKER_APPEARANCE '{mode}', using system")
            return "system"
        return mode

    # =========================================================================
    # Health Check Configuration (T006)
    # =========================================================================

    @property
    def health_check_interval(self) -> int:
        """Health check interval in seconds.

        Environment variable: BAKE_TRACKER_HEALTH_INTERVAL
        Default: 30
        """
        try:
            return int(os.environ.get("BAKE_TRACKER_HEALTH_INTERVAL", "30"))
        except ValueError:
            logger.warning("Invalid BAKE_TRACKER_HEALTH_INTERVAL, using default 30")
            return 30

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
