"""
Main entry point for the Seasonal Baking Tracker application.

This module initializes the application, sets up the database,
and launches the main window.
"""

import sys
import traceback
import customtkinter as ctk

from src.services.database import initialize_app_database
from src.ui.main_window import MainWindow
from src.utils.config import get_config


def initialize_application():
    """
    Initialize the application.

    Sets up the database and performs any necessary startup checks.

    Returns:
        True if initialization successful, False otherwise
    """
    try:
        # Initialize database
        print("Initializing database...")
        initialize_app_database()
        print("Database initialized successfully")

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

    print("Application closed successfully")
    sys.exit(0)


if __name__ == "__main__":
    main()
