"""
Preferences Service - Manage user directory preferences.

Feature 051: Stores preferences in a JSON config file in the user's platform-specific
config directory (e.g., ~/Library/Application Support/BakeTracker on macOS).
This design ensures preferences survive database resets (per FR-016) because
the config file is completely separate from the SQLite database.

Note: FR-016 originally specified app_config table storage, but JSON file storage
better achieves the "survives database reset" requirement since database resets
would clear the app_config table. The JSON file approach is equivalent in
functionality while being more robust to database operations.

Usage:
    from src.services.preferences_service import (
        get_import_directory,
        set_import_directory,
        reset_all_preferences,
    )

    # Get current import directory (or default if not set)
    import_dir = get_import_directory()

    # Set a new import directory
    set_import_directory("/path/to/imports")

    # Reset all preferences to defaults
    reset_all_preferences()
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


# ============================================================================
# Constants
# ============================================================================

# Preference keys
PREF_IMPORT_DIR = "import_directory"
PREF_EXPORT_DIR = "export_directory"
PREF_LOGS_DIR = "logs_directory"
PREF_BACKUP_DIR = "backup_directory"


# Config file location
# Use platform-appropriate config directory
def _get_config_dir() -> Path:
    """Get the platform-appropriate config directory for the application."""
    if os.name == "nt":  # Windows
        base = Path(os.environ.get("APPDATA", Path.home()))
    elif os.name == "posix":
        if "darwin" in os.uname().sysname.lower():  # macOS
            base = Path.home() / "Library" / "Application Support"
        else:  # Linux
            base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    else:
        base = Path.home()

    return base / "BakeTracker"


def _get_config_file() -> Path:
    """Get the preferences config file path."""
    return _get_config_dir() / "preferences.json"


# Default directories
def _get_default_import_dir() -> Path:
    """Get the default import directory."""
    return Path.home() / "Documents"


def _get_default_export_dir() -> Path:
    """Get the default export directory."""
    return Path.home() / "Documents"


def _get_default_logs_dir() -> Path:
    """Get the default logs directory."""
    # Use project docs/user_testing directory as default
    # This is relative to the source file location
    project_root = Path(__file__).parent.parent.parent
    return project_root / "docs" / "user_testing"


def _get_default_backup_dir() -> Path:
    """Get the default backup directory."""
    return Path.home() / "Documents" / "BakeTracker" / "backups"


# ============================================================================
# Internal Helpers
# ============================================================================


def _load_preferences() -> Dict[str, Any]:
    """
    Load preferences from the config file.

    Returns:
        Dictionary of preferences (empty dict if file doesn't exist)
    """
    config_file = _get_config_file()

    if not config_file.exists():
        return {}

    try:
        with open(config_file, "r", encoding="utf-8") as f:
            result = json.load(f)
            return result if isinstance(result, dict) else {}
    except (json.JSONDecodeError, IOError) as e:
        logger.warning(f"Failed to load preferences from {config_file}: {e}")
        return {}


def _save_preferences(prefs: dict) -> bool:
    """
    Save preferences to the config file.

    Args:
        prefs: Dictionary of preferences to save

    Returns:
        True if saved successfully, False otherwise
    """
    config_file = _get_config_file()
    config_dir = config_file.parent

    try:
        # Create config directory if it doesn't exist
        config_dir.mkdir(parents=True, exist_ok=True)

        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(prefs, f, indent=2)

        return True
    except (IOError, OSError) as e:
        logger.error(f"Failed to save preferences to {config_file}: {e}")
        return False


def _get_preference(key: str) -> Optional[str]:
    """
    Get a single preference value.

    Args:
        key: Preference key

    Returns:
        Preference value or None if not set
    """
    prefs = _load_preferences()
    return prefs.get(key)


def _set_preference(key: str, value: str) -> bool:
    """
    Set a single preference value.

    Args:
        key: Preference key
        value: Preference value

    Returns:
        True if saved successfully, False otherwise
    """
    prefs = _load_preferences()
    prefs[key] = value
    return _save_preferences(prefs)


def _delete_preference(key: str) -> bool:
    """
    Delete a single preference.

    Args:
        key: Preference key to delete

    Returns:
        True if saved successfully, False otherwise
    """
    prefs = _load_preferences()
    if key in prefs:
        del prefs[key]
        return _save_preferences(prefs)
    return True


def _validate_directory(path: Path, check_writable: bool = False) -> bool:
    """
    Validate that a path is a valid, accessible directory.

    Args:
        path: Path to validate
        check_writable: If True, also check write permission

    Returns:
        True if valid directory, False otherwise
    """
    try:
        if not path.exists():
            return False
        if not path.is_dir():
            return False
        if check_writable:
            # Try to check write permission
            test_file = path / ".baketracker_write_test"
            try:
                test_file.touch()
                test_file.unlink()
            except (IOError, OSError):
                return False
        return True
    except (IOError, OSError):
        return False


# ============================================================================
# Import Directory
# ============================================================================


def get_import_directory() -> Path:
    """
    Get the configured import directory.

    Returns the stored preference if valid, otherwise returns the default.

    Returns:
        Path to the import directory
    """
    stored = _get_preference(PREF_IMPORT_DIR)

    if stored:
        stored_path = Path(stored)
        if _validate_directory(stored_path):
            return stored_path
        else:
            logger.warning(
                f"Stored import directory '{stored}' is not valid, " f"falling back to default"
            )

    default = _get_default_import_dir()

    # Validate default exists
    if _validate_directory(default):
        return default

    # Ultimate fallback to home directory
    return Path.home()


def set_import_directory(path: str) -> bool:
    """
    Set the import directory preference.

    Args:
        path: Path to the import directory

    Returns:
        True if set successfully, False otherwise

    Raises:
        ValueError: If path is not a valid directory
    """
    dir_path = Path(path)

    if not _validate_directory(dir_path):
        raise ValueError(f"'{path}' is not a valid directory")

    return _set_preference(PREF_IMPORT_DIR, str(dir_path))


# ============================================================================
# Export Directory
# ============================================================================


def get_export_directory() -> Path:
    """
    Get the configured export directory.

    Returns the stored preference if valid, otherwise returns the default.

    Returns:
        Path to the export directory
    """
    stored = _get_preference(PREF_EXPORT_DIR)

    if stored:
        stored_path = Path(stored)
        if _validate_directory(stored_path):
            return stored_path
        else:
            logger.warning(
                f"Stored export directory '{stored}' is not valid, " f"falling back to default"
            )

    default = _get_default_export_dir()

    # Validate default exists
    if _validate_directory(default):
        return default

    # Ultimate fallback to home directory
    return Path.home()


def set_export_directory(path: str) -> bool:
    """
    Set the export directory preference.

    Args:
        path: Path to the export directory

    Returns:
        True if set successfully, False otherwise

    Raises:
        ValueError: If path is not a valid directory
    """
    dir_path = Path(path)

    if not _validate_directory(dir_path):
        raise ValueError(f"'{path}' is not a valid directory")

    return _set_preference(PREF_EXPORT_DIR, str(dir_path))


# ============================================================================
# Logs Directory
# ============================================================================


def get_logs_directory() -> Path:
    """
    Get the configured logs directory.

    Returns the stored preference if valid and writable, otherwise returns the default.
    Logs directory requires write permission.

    Returns:
        Path to the logs directory
    """
    stored = _get_preference(PREF_LOGS_DIR)

    if stored:
        stored_path = Path(stored)
        if _validate_directory(stored_path, check_writable=True):
            return stored_path
        else:
            logger.warning(
                f"Stored logs directory '{stored}' is not valid or not writable, "
                f"falling back to default"
            )

    default = _get_default_logs_dir()

    # Try to create default logs directory if it doesn't exist
    try:
        default.mkdir(parents=True, exist_ok=True)
    except (IOError, OSError):
        pass

    # Validate default exists and is writable
    if _validate_directory(default, check_writable=True):
        return default

    # Fallback to user's Documents folder
    docs = Path.home() / "Documents"
    if _validate_directory(docs, check_writable=True):
        logger.warning(f"Logs directory fallback to {docs}")
        return docs

    # Ultimate fallback to home directory
    logger.warning(f"Logs directory fallback to home directory")
    return Path.home()


def set_logs_directory(path: str) -> bool:
    """
    Set the logs directory preference.

    Args:
        path: Path to the logs directory

    Returns:
        True if set successfully, False otherwise

    Raises:
        ValueError: If path is not a valid writable directory
    """
    dir_path = Path(path)

    if not _validate_directory(dir_path, check_writable=True):
        raise ValueError(f"'{path}' is not a valid writable directory")

    return _set_preference(PREF_LOGS_DIR, str(dir_path))


# ============================================================================
# Backup Directory
# ============================================================================


def get_backup_directory() -> Path:
    """
    Get the configured backup directory.

    Returns the stored preference if valid, otherwise returns the default.
    Creates the default directory if it doesn't exist.

    Returns:
        Path to the backup directory
    """
    stored = _get_preference(PREF_BACKUP_DIR)

    if stored:
        stored_path = Path(stored)
        if _validate_directory(stored_path):
            return stored_path
        else:
            logger.warning(
                f"Stored backup directory '{stored}' is not valid, " f"falling back to default"
            )

    default = _get_default_backup_dir()

    # Try to create default backup directory if it doesn't exist
    try:
        default.mkdir(parents=True, exist_ok=True)
    except (IOError, OSError):
        pass

    # Validate default exists
    if _validate_directory(default):
        return default

    # Fallback to Documents folder
    docs = Path.home() / "Documents"
    if _validate_directory(docs):
        return docs

    # Ultimate fallback to home directory
    return Path.home()


def set_backup_directory(path: str) -> bool:
    """
    Set the backup directory preference.

    Args:
        path: Path to the backup directory

    Returns:
        True if set successfully, False otherwise

    Raises:
        ValueError: If path is not a valid directory
    """
    dir_path = Path(path)

    if not _validate_directory(dir_path):
        raise ValueError(f"'{path}' is not a valid directory")

    return _set_preference(PREF_BACKUP_DIR, str(dir_path))


# ============================================================================
# Reset
# ============================================================================


def reset_all_preferences() -> bool:
    """
    Reset all directory preferences to defaults.

    Removes all stored preferences so that subsequent get_* calls
    will return default values.

    Returns:
        True if reset successfully, False otherwise
    """
    config_file = _get_config_file()

    try:
        if config_file.exists():
            config_file.unlink()
        logger.info("All preferences reset to defaults")
        return True
    except (IOError, OSError) as e:
        logger.error(f"Failed to reset preferences: {e}")
        return False


# ============================================================================
# Utility Functions
# ============================================================================


def get_all_preferences() -> dict:
    """
    Get all current preference values (for UI display).

    Returns:
        Dictionary with current effective values for all preferences
    """
    return {
        PREF_IMPORT_DIR: str(get_import_directory()),
        PREF_EXPORT_DIR: str(get_export_directory()),
        PREF_LOGS_DIR: str(get_logs_directory()),
        PREF_BACKUP_DIR: str(get_backup_directory()),
    }


def get_config_file_path() -> Path:
    """
    Get the path to the preferences config file.

    Useful for debugging or displaying to user.

    Returns:
        Path to the config file
    """
    return _get_config_file()
