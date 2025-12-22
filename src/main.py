"""
Main entry point for the Seasonal Baking Tracker application.

This module initializes the application, sets up the database,
and launches the main window.
"""

import os
import sys
import traceback
import customtkinter as ctk

from src.services.database import initialize_app_database
from src.services.health_service import HealthCheckService
from src.ui.main_window import MainWindow
from src.utils.config import get_config, Config

# Global health service instance
_health_service = None


def check_database_environment():
    """
    Check for potential database environment issues.

    Warns if the current database is empty but the alternate environment
    has data, which could indicate data was written to the wrong location.
    """
    import sqlite3
    from pathlib import Path

    config = get_config()
    current_db = config.database_path
    current_env = config.environment

    # Determine alternate environment database path
    if current_env == "production":
        # Check development database
        alt_config = Config("development")
        alt_db = alt_config.database_path
        alt_env = "development"
    else:
        # Check production database
        alt_config = Config("production")
        alt_db = alt_config.database_path
        alt_env = "production"

    def get_row_count(db_path: Path) -> int:
        """Get total row count from key tables."""
        if not db_path.exists():
            return 0
        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            total = 0
            for table in ["ingredients", "recipes", "products", "inventory_items"]:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    total += cursor.fetchone()[0]
                except sqlite3.OperationalError:
                    pass  # Table doesn't exist
            conn.close()
            return total
        except Exception:
            return 0

    current_count = get_row_count(current_db)
    alt_count = get_row_count(alt_db)

    print(f"Database path: {current_db}")
    print(f"  - Current ({current_env}): {current_count} records")
    print(f"  - Alternate ({alt_env}): {alt_count} records")

    if current_count == 0 and alt_count > 0:
        print("\n" + "=" * 60)
        print("WARNING: Current database is empty but alternate has data!")
        print(f"  Your data may be in the {alt_env} database at:")
        print(f"  {alt_db}")
        print(f"\n  To use {alt_env} mode, set BAKING_TRACKER_ENV={alt_env}")
        print(f"  Or import data from: test_data/sample_data.json")
        print("=" * 60 + "\n")


def initialize_application():
    """
    Initialize the application.

    Sets up the database and performs any necessary startup checks.

    Returns:
        True if initialization successful, False otherwise
    """
    try:
        global _health_service

        # Initialize database
        print("Initializing database...")
        initialize_app_database()
        print("Database initialized successfully")

        # Initialize and start health check service
        print("Starting health check service...")
        _health_service = HealthCheckService()
        _health_service.start()
        print("Health check service started")

        return True

    except Exception as e:
        print(f"ERROR: Failed to initialize application: {e}")
        traceback.print_exc()
        return False


def main():
    """
    Main application entry point.

    Initializes the application and launches the main window.
    """
    # Set CustomTkinter appearance
    ctk.set_appearance_mode("system")  # Modes: system, light, dark
    ctk.set_default_color_theme("blue")  # Themes: blue, dark-blue, green

    # Get configuration
    config = get_config()
    print(f"Starting Seasonal Baking Tracker v{config.app_version}")
    print(f"Environment: {config.environment}")

    # Check for database environment issues
    check_database_environment()

    # Initialize application
    if not initialize_application():
        print("Application initialization failed. Exiting.")
        sys.exit(1)

    # Create and run main window
    try:
        app = MainWindow()
        app.mainloop()

    except Exception as e:
        print(f"ERROR: Application crashed: {e}")
        traceback.print_exc()
        sys.exit(1)

    finally:
        # Cleanup health service
        if _health_service:
            print("Stopping health check service...")
            _health_service.stop()

    print("Application closed successfully")
    sys.exit(0)


if __name__ == "__main__":
    main()
