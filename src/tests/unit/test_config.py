"""Unit tests for Config class configuration properties.

Tests cover all new properties added in F090:
- Database connection settings (db_timeout, db_pool_size, db_pool_recycle)
- Database type and PostgreSQL URL support
- Feature flags
- UI configuration (ui_theme, ui_appearance)
- Health check interval

Each property is tested for:
- Default values when no environment variables set
- Environment variable overrides
- Invalid value handling (fallback to defaults with warning)
"""

import logging
import pytest
from src.utils.config import Config, reset_config


class TestDatabaseConfigProperties:
    """Tests for database configuration properties."""

    def setup_method(self):
        """Reset config singleton before each test."""
        reset_config()

    def teardown_method(self):
        """Clean up after each test."""
        reset_config()

    def test_db_timeout_default(self):
        """Default db_timeout is 30."""
        config = Config()
        assert config.db_timeout == 30

    def test_db_timeout_env_override(self, monkeypatch):
        """db_timeout can be overridden via environment variable."""
        monkeypatch.setenv("BAKE_TRACKER_DB_TIMEOUT", "60")
        config = Config()
        assert config.db_timeout == 60

    def test_db_timeout_invalid_uses_default(self, monkeypatch, caplog):
        """Invalid db_timeout falls back to default with warning."""
        monkeypatch.setenv("BAKE_TRACKER_DB_TIMEOUT", "invalid")
        with caplog.at_level(logging.WARNING):
            config = Config()
            assert config.db_timeout == 30
        assert "Invalid BAKE_TRACKER_DB_TIMEOUT" in caplog.text

    def test_db_pool_size_default(self):
        """Default db_pool_size is 5."""
        config = Config()
        assert config.db_pool_size == 5

    def test_db_pool_size_env_override(self, monkeypatch):
        """db_pool_size can be overridden via environment variable."""
        monkeypatch.setenv("BAKE_TRACKER_DB_POOL_SIZE", "10")
        config = Config()
        assert config.db_pool_size == 10

    def test_db_pool_size_invalid_uses_default(self, monkeypatch, caplog):
        """Invalid db_pool_size falls back to default with warning."""
        monkeypatch.setenv("BAKE_TRACKER_DB_POOL_SIZE", "invalid")
        with caplog.at_level(logging.WARNING):
            config = Config()
            assert config.db_pool_size == 5
        assert "Invalid BAKE_TRACKER_DB_POOL_SIZE" in caplog.text

    def test_db_pool_recycle_default(self):
        """Default db_pool_recycle is 3600."""
        config = Config()
        assert config.db_pool_recycle == 3600

    def test_db_pool_recycle_env_override(self, monkeypatch):
        """db_pool_recycle can be overridden via environment variable."""
        monkeypatch.setenv("BAKE_TRACKER_DB_POOL_RECYCLE", "7200")
        config = Config()
        assert config.db_pool_recycle == 7200

    def test_db_pool_recycle_invalid_uses_default(self, monkeypatch, caplog):
        """Invalid db_pool_recycle falls back to default with warning."""
        monkeypatch.setenv("BAKE_TRACKER_DB_POOL_RECYCLE", "invalid")
        with caplog.at_level(logging.WARNING):
            config = Config()
            assert config.db_pool_recycle == 3600
        assert "Invalid BAKE_TRACKER_DB_POOL_RECYCLE" in caplog.text


class TestDatabaseTypeProperties:
    """Tests for database type and URL properties."""

    def setup_method(self):
        """Reset config singleton before each test."""
        reset_config()

    def teardown_method(self):
        """Clean up after each test."""
        reset_config()

    def test_database_type_default(self):
        """Default database_type is sqlite."""
        config = Config()
        assert config.database_type == "sqlite"

    def test_database_type_postgresql(self, monkeypatch):
        """database_type can be set to postgresql."""
        monkeypatch.setenv("BAKE_TRACKER_DB_TYPE", "postgresql")
        config = Config()
        assert config.database_type == "postgresql"

    def test_database_type_case_insensitive(self, monkeypatch):
        """database_type is case insensitive."""
        monkeypatch.setenv("BAKE_TRACKER_DB_TYPE", "PostgreSQL")
        config = Config()
        assert config.database_type == "postgresql"

    def test_database_type_invalid_uses_sqlite(self, monkeypatch, caplog):
        """Invalid database_type falls back to sqlite with warning."""
        monkeypatch.setenv("BAKE_TRACKER_DB_TYPE", "mysql")
        with caplog.at_level(logging.WARNING):
            config = Config()
            assert config.database_type == "sqlite"
        assert "Invalid BAKE_TRACKER_DB_TYPE" in caplog.text

    def test_database_url_sqlite_default(self):
        """SQLite database_url generated from path."""
        config = Config()
        assert config.database_url.startswith("sqlite:///")

    def test_database_url_postgresql(self, monkeypatch):
        """PostgreSQL database_url uses DATABASE_URL env var."""
        monkeypatch.setenv("BAKE_TRACKER_DB_TYPE", "postgresql")
        monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost/db")
        config = Config()
        assert config.database_url == "postgresql://user:pass@localhost/db"

    def test_database_url_postgresql_missing_raises(self, monkeypatch):
        """PostgreSQL without DATABASE_URL raises ValueError."""
        monkeypatch.setenv("BAKE_TRACKER_DB_TYPE", "postgresql")
        monkeypatch.delenv("DATABASE_URL", raising=False)
        config = Config()
        with pytest.raises(ValueError, match="DATABASE_URL environment variable required"):
            _ = config.database_url

    def test_db_connect_args_sqlite(self):
        """SQLite db_connect_args includes timeout."""
        config = Config()
        args = config.db_connect_args
        assert args["check_same_thread"] is False
        assert args["timeout"] == 30

    def test_db_connect_args_sqlite_with_custom_timeout(self, monkeypatch):
        """SQLite db_connect_args uses custom timeout from env."""
        monkeypatch.setenv("BAKE_TRACKER_DB_TIMEOUT", "60")
        config = Config()
        args = config.db_connect_args
        assert args["timeout"] == 60

    def test_db_connect_args_postgresql(self, monkeypatch):
        """PostgreSQL db_connect_args is empty dict."""
        monkeypatch.setenv("BAKE_TRACKER_DB_TYPE", "postgresql")
        config = Config()
        assert config.db_connect_args == {}


class TestFeatureFlagsProperties:
    """Tests for feature flags properties."""

    def setup_method(self):
        """Reset config singleton before each test."""
        reset_config()

    def teardown_method(self):
        """Clean up after each test."""
        reset_config()

    def test_feature_flags_defaults(self):
        """Default feature flags have expected values."""
        config = Config()
        flags = config.feature_flags
        assert flags["enable_audit_trail"] is False
        assert flags["enable_health_checks"] is True
        assert flags["enable_performance_monitoring"] is False

    def test_feature_flags_enable_audit(self, monkeypatch):
        """enable_audit_trail can be enabled via env var."""
        monkeypatch.setenv("ENABLE_AUDIT", "true")
        config = Config()
        flags = config.feature_flags
        assert flags["enable_audit_trail"] is True

    def test_feature_flags_disable_health(self, monkeypatch):
        """enable_health_checks can be disabled via env var."""
        monkeypatch.setenv("ENABLE_HEALTH", "false")
        config = Config()
        flags = config.feature_flags
        assert flags["enable_health_checks"] is False

    def test_feature_flags_enable_perf_mon(self, monkeypatch):
        """enable_performance_monitoring can be enabled via env var."""
        monkeypatch.setenv("ENABLE_PERF_MON", "1")
        config = Config()
        flags = config.feature_flags
        assert flags["enable_performance_monitoring"] is True

    def test_feature_flags_accepts_yes(self, monkeypatch):
        """Feature flags accept 'yes' as true."""
        monkeypatch.setenv("ENABLE_AUDIT", "yes")
        config = Config()
        flags = config.feature_flags
        assert flags["enable_audit_trail"] is True

    def test_feature_flags_case_insensitive(self, monkeypatch):
        """Feature flags are case insensitive."""
        monkeypatch.setenv("ENABLE_AUDIT", "TRUE")
        config = Config()
        flags = config.feature_flags
        assert flags["enable_audit_trail"] is True


class TestUIConfigProperties:
    """Tests for UI configuration properties."""

    def setup_method(self):
        """Reset config singleton before each test."""
        reset_config()

    def teardown_method(self):
        """Clean up after each test."""
        reset_config()

    def test_ui_theme_default(self):
        """Default ui_theme is blue."""
        config = Config()
        assert config.ui_theme == "blue"

    def test_ui_theme_env_override(self, monkeypatch):
        """ui_theme can be overridden via environment variable."""
        monkeypatch.setenv("BAKE_TRACKER_THEME", "dark-blue")
        config = Config()
        assert config.ui_theme == "dark-blue"

    def test_ui_theme_green(self, monkeypatch):
        """ui_theme accepts green."""
        monkeypatch.setenv("BAKE_TRACKER_THEME", "green")
        config = Config()
        assert config.ui_theme == "green"

    def test_ui_theme_invalid_uses_default(self, monkeypatch, caplog):
        """Invalid ui_theme falls back to blue with warning."""
        monkeypatch.setenv("BAKE_TRACKER_THEME", "red")
        with caplog.at_level(logging.WARNING):
            config = Config()
            assert config.ui_theme == "blue"
        assert "Invalid BAKE_TRACKER_THEME" in caplog.text

    def test_ui_appearance_default(self):
        """Default ui_appearance is system."""
        config = Config()
        assert config.ui_appearance == "system"

    def test_ui_appearance_env_override(self, monkeypatch):
        """ui_appearance can be overridden via environment variable."""
        monkeypatch.setenv("BAKE_TRACKER_APPEARANCE", "dark")
        config = Config()
        assert config.ui_appearance == "dark"

    def test_ui_appearance_light(self, monkeypatch):
        """ui_appearance accepts light."""
        monkeypatch.setenv("BAKE_TRACKER_APPEARANCE", "light")
        config = Config()
        assert config.ui_appearance == "light"

    def test_ui_appearance_invalid_uses_default(self, monkeypatch, caplog):
        """Invalid ui_appearance falls back to system with warning."""
        monkeypatch.setenv("BAKE_TRACKER_APPEARANCE", "auto")
        with caplog.at_level(logging.WARNING):
            config = Config()
            assert config.ui_appearance == "system"
        assert "Invalid BAKE_TRACKER_APPEARANCE" in caplog.text


class TestHealthCheckConfigProperties:
    """Tests for health check configuration properties."""

    def setup_method(self):
        """Reset config singleton before each test."""
        reset_config()

    def teardown_method(self):
        """Clean up after each test."""
        reset_config()

    def test_health_check_interval_default(self):
        """Default health_check_interval is 30."""
        config = Config()
        assert config.health_check_interval == 30

    def test_health_check_interval_env_override(self, monkeypatch):
        """health_check_interval can be overridden via environment variable."""
        monkeypatch.setenv("BAKE_TRACKER_HEALTH_INTERVAL", "60")
        config = Config()
        assert config.health_check_interval == 60

    def test_health_check_interval_invalid_uses_default(self, monkeypatch, caplog):
        """Invalid health_check_interval falls back to default with warning."""
        monkeypatch.setenv("BAKE_TRACKER_HEALTH_INTERVAL", "invalid")
        with caplog.at_level(logging.WARNING):
            config = Config()
            assert config.health_check_interval == 30
        assert "Invalid BAKE_TRACKER_HEALTH_INTERVAL" in caplog.text
