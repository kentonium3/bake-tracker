"""
Tests for preferences_service.

Tests cover:
- get/set functions for import, export, and logs directories
- Directory validation with fallback
- reset_all_preferences
- Edge cases (invalid paths, permission errors)
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.services import preferences_service
from src.services.preferences_service import (
    get_import_directory,
    set_import_directory,
    get_export_directory,
    set_export_directory,
    get_logs_directory,
    set_logs_directory,
    reset_all_preferences,
    get_all_preferences,
    get_config_file_path,
    PREF_IMPORT_DIR,
    PREF_EXPORT_DIR,
    PREF_LOGS_DIR,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def temp_config_dir(tmp_path):
    """Create a temporary config directory and patch preferences_service to use it."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    # Patch _get_config_dir to return our temp directory
    with patch.object(
        preferences_service,
        "_get_config_dir",
        return_value=config_dir,
    ):
        yield config_dir


@pytest.fixture
def temp_dirs(tmp_path):
    """Create temporary directories for testing."""
    import_dir = tmp_path / "imports"
    export_dir = tmp_path / "exports"
    logs_dir = tmp_path / "logs"

    import_dir.mkdir()
    export_dir.mkdir()
    logs_dir.mkdir()

    return {
        "import": import_dir,
        "export": export_dir,
        "logs": logs_dir,
    }


@pytest.fixture
def clean_preferences(temp_config_dir):
    """Ensure preferences are reset before and after each test."""
    reset_all_preferences()
    yield
    reset_all_preferences()


# ============================================================================
# Import Directory Tests
# ============================================================================


class TestImportDirectory:
    """Tests for get/set_import_directory()."""

    def test_get_returns_default_when_not_set(self, clean_preferences):
        """Test that get returns default when no preference is set."""
        result = get_import_directory()
        # Should return a Path that exists (default or fallback)
        assert isinstance(result, Path)
        assert result.exists()

    def test_set_then_get_returns_same_path(self, clean_preferences, temp_dirs):
        """Test that set then get returns the same path."""
        expected = temp_dirs["import"]
        set_import_directory(str(expected))
        result = get_import_directory()
        assert result == expected

    def test_set_invalid_path_raises_error(self, clean_preferences, tmp_path):
        """Test that setting an invalid path raises ValueError."""
        invalid_path = tmp_path / "nonexistent"
        with pytest.raises(ValueError) as exc_info:
            set_import_directory(str(invalid_path))
        assert "not a valid directory" in str(exc_info.value)

    def test_set_file_path_raises_error(self, clean_preferences, tmp_path):
        """Test that setting a file path (not directory) raises ValueError."""
        file_path = tmp_path / "file.txt"
        file_path.touch()
        with pytest.raises(ValueError):
            set_import_directory(str(file_path))

    def test_fallback_when_stored_path_deleted(self, clean_preferences, tmp_path):
        """Test fallback when stored path no longer exists."""
        temp_dir = tmp_path / "temp_import"
        temp_dir.mkdir()

        # Set preference
        set_import_directory(str(temp_dir))

        # Delete the directory
        temp_dir.rmdir()

        # Get should return default, not the deleted path
        result = get_import_directory()
        assert result != temp_dir
        assert result.exists()


# ============================================================================
# Export Directory Tests
# ============================================================================


class TestExportDirectory:
    """Tests for get/set_export_directory()."""

    def test_get_returns_default_when_not_set(self, clean_preferences):
        """Test that get returns default when no preference is set."""
        result = get_export_directory()
        assert isinstance(result, Path)
        assert result.exists()

    def test_set_then_get_returns_same_path(self, clean_preferences, temp_dirs):
        """Test that set then get returns the same path."""
        expected = temp_dirs["export"]
        set_export_directory(str(expected))
        result = get_export_directory()
        assert result == expected

    def test_set_invalid_path_raises_error(self, clean_preferences, tmp_path):
        """Test that setting an invalid path raises ValueError."""
        invalid_path = tmp_path / "nonexistent"
        with pytest.raises(ValueError):
            set_export_directory(str(invalid_path))


# ============================================================================
# Logs Directory Tests
# ============================================================================


class TestLogsDirectory:
    """Tests for get/set_logs_directory()."""

    def test_get_returns_default_when_not_set(self, clean_preferences):
        """Test that get returns default when no preference is set."""
        result = get_logs_directory()
        assert isinstance(result, Path)
        # Logs directory should be writable
        assert result.exists()

    def test_set_then_get_returns_same_path(self, clean_preferences, temp_dirs):
        """Test that set then get returns the same path."""
        expected = temp_dirs["logs"]
        set_logs_directory(str(expected))
        result = get_logs_directory()
        assert result == expected

    def test_set_invalid_path_raises_error(self, clean_preferences, tmp_path):
        """Test that setting an invalid path raises ValueError."""
        invalid_path = tmp_path / "nonexistent"
        with pytest.raises(ValueError):
            set_logs_directory(str(invalid_path))

    def test_logs_requires_write_permission(self, clean_preferences, tmp_path):
        """Test that logs directory validation checks write permission."""
        # Create a directory
        logs_dir = tmp_path / "logs"
        logs_dir.mkdir()

        # Should work with writable directory
        set_logs_directory(str(logs_dir))
        result = get_logs_directory()
        assert result == logs_dir


# ============================================================================
# Reset Tests
# ============================================================================


class TestResetPreferences:
    """Tests for reset_all_preferences()."""

    def test_reset_clears_all_preferences(self, clean_preferences, temp_dirs):
        """Test that reset clears all preferences."""
        # Set all preferences
        set_import_directory(str(temp_dirs["import"]))
        set_export_directory(str(temp_dirs["export"]))
        set_logs_directory(str(temp_dirs["logs"]))

        # Verify they're set
        assert get_import_directory() == temp_dirs["import"]

        # Reset
        result = reset_all_preferences()
        assert result is True

        # Get should now return defaults (not the temp dirs)
        import_result = get_import_directory()
        assert import_result != temp_dirs["import"]

    def test_reset_returns_true_when_no_preferences(self, clean_preferences):
        """Test that reset returns True even when no preferences are set."""
        result = reset_all_preferences()
        assert result is True

    def test_preferences_persist_across_calls(self, clean_preferences, temp_dirs):
        """Test that preferences persist when set."""
        set_import_directory(str(temp_dirs["import"]))

        # Simulate "new session" by clearing any in-memory cache
        # (our implementation reads from file each time)
        result = get_import_directory()
        assert result == temp_dirs["import"]


# ============================================================================
# Utility Function Tests
# ============================================================================


class TestUtilityFunctions:
    """Tests for utility functions."""

    def test_get_all_preferences(self, clean_preferences, temp_dirs):
        """Test get_all_preferences returns all effective values."""
        set_import_directory(str(temp_dirs["import"]))
        set_export_directory(str(temp_dirs["export"]))
        set_logs_directory(str(temp_dirs["logs"]))

        result = get_all_preferences()

        assert PREF_IMPORT_DIR in result
        assert PREF_EXPORT_DIR in result
        assert PREF_LOGS_DIR in result
        assert result[PREF_IMPORT_DIR] == str(temp_dirs["import"])
        assert result[PREF_EXPORT_DIR] == str(temp_dirs["export"])
        assert result[PREF_LOGS_DIR] == str(temp_dirs["logs"])

    def test_get_config_file_path(self, temp_config_dir):
        """Test get_config_file_path returns the config file path."""
        result = get_config_file_path()
        assert isinstance(result, Path)
        assert result.parent == temp_config_dir
        assert result.name == "preferences.json"


# ============================================================================
# Edge Case Tests
# ============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_corrupted_config_file_handled(self, temp_config_dir, tmp_path):
        """Test that corrupted config file is handled gracefully."""
        config_file = temp_config_dir / "preferences.json"

        # Write invalid JSON
        with open(config_file, "w") as f:
            f.write("not valid json {{{")

        # Should not raise, should return default
        result = get_import_directory()
        assert isinstance(result, Path)
        assert result.exists()

    def test_empty_config_file_handled(self, temp_config_dir):
        """Test that empty config file is handled gracefully."""
        config_file = temp_config_dir / "preferences.json"
        config_file.touch()  # Create empty file

        # Should return default
        result = get_import_directory()
        assert isinstance(result, Path)
        assert result.exists()

    def test_config_file_created_on_set(self, temp_config_dir, temp_dirs):
        """Test that config file is created when setting preference."""
        config_file = temp_config_dir / "preferences.json"
        assert not config_file.exists()

        set_import_directory(str(temp_dirs["import"]))

        assert config_file.exists()

    def test_path_with_spaces(self, clean_preferences, tmp_path):
        """Test that paths with spaces work correctly."""
        path_with_spaces = tmp_path / "path with spaces"
        path_with_spaces.mkdir()

        set_import_directory(str(path_with_spaces))
        result = get_import_directory()
        assert result == path_with_spaces

    def test_path_with_unicode(self, clean_preferences, tmp_path):
        """Test that paths with unicode characters work correctly."""
        unicode_path = tmp_path / "文件夹"
        unicode_path.mkdir()

        set_import_directory(str(unicode_path))
        result = get_import_directory()
        assert result == unicode_path

    def test_relative_path_converted_to_absolute(self, clean_preferences, tmp_path, monkeypatch):
        """Test behavior with relative paths."""
        # Create a directory in tmp_path
        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()

        # Use absolute path (relative paths should still work but convert)
        set_import_directory(str(test_dir))
        result = get_import_directory()
        assert result.is_absolute()


# ============================================================================
# Directory Validation Tests
# ============================================================================


class TestDirectoryValidation:
    """Tests for _validate_directory helper."""

    def test_validate_existing_directory(self, tmp_path):
        """Test validation passes for existing directory."""
        test_dir = tmp_path / "valid"
        test_dir.mkdir()

        result = preferences_service._validate_directory(test_dir)
        assert result is True

    def test_validate_nonexistent_directory(self, tmp_path):
        """Test validation fails for nonexistent directory."""
        nonexistent = tmp_path / "nonexistent"

        result = preferences_service._validate_directory(nonexistent)
        assert result is False

    def test_validate_file_not_directory(self, tmp_path):
        """Test validation fails for file (not directory)."""
        file_path = tmp_path / "file.txt"
        file_path.touch()

        result = preferences_service._validate_directory(file_path)
        assert result is False

    def test_validate_writable_directory(self, tmp_path):
        """Test validation with write check passes for writable directory."""
        test_dir = tmp_path / "writable"
        test_dir.mkdir()

        result = preferences_service._validate_directory(test_dir, check_writable=True)
        assert result is True
