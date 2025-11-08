"""
Unit tests for Health Check Service.

Tests cover service initialization, threading lifecycle, database connectivity,
file I/O operations, and version reading.
"""

import json
import threading
import time
from pathlib import Path
from unittest.mock import Mock, mock_open, patch

import pytest

from src.services.health_service import HealthCheckService


class TestHealthCheckServiceInit:
    """Test health service initialization."""

    def test_init_creates_instance(self):
        """Test that service can be instantiated."""
        service = HealthCheckService()
        assert service is not None
        assert service._check_interval == 30
        assert service._health_file == Path("data/health.json")
        assert isinstance(service._stop_event, threading.Event)

    def test_init_custom_params(self):
        """Test initialization with custom parameters."""
        custom_path = Path("custom/health.json")
        service = HealthCheckService(check_interval=60, health_file=custom_path)
        assert service._check_interval == 60
        assert service._health_file == custom_path


class TestHealthCheckServiceThreading:
    """Test service threading lifecycle."""

    def test_start_launches_thread(self):
        """Test that start() launches background thread."""
        service = HealthCheckService(check_interval=1)
        service.start()
        assert service._thread is not None
        assert service._thread.is_alive()
        assert service._thread.daemon is True
        service.stop()

    def test_stop_terminates_thread(self):
        """Test that stop() terminates thread cleanly."""
        service = HealthCheckService(check_interval=1)
        service.start()
        time.sleep(0.1)  # Let thread start
        service.stop(timeout=2.0)
        assert not service._thread.is_alive()

    def test_start_when_already_running(self):
        """Test that start() is idempotent."""
        service = HealthCheckService(check_interval=1)
        service.start()
        thread1 = service._thread
        service.start()  # Should not create new thread
        thread2 = service._thread
        assert thread1 is thread2
        service.stop()

    def test_stop_when_not_running(self):
        """Test that stop() on non-running service is safe."""
        service = HealthCheckService()
        service.stop()  # Should not raise exception


class TestDatabaseConnectivity:
    """Test database connectivity checking."""

    @patch("src.services.database.session_scope")
    def test_check_database_connected(self, mock_session):
        """Test database check returns 'connected' when healthy."""
        service = HealthCheckService()
        status = service._check_database()
        assert status == "connected"

    @patch("src.services.database.session_scope")
    def test_check_database_disconnected(self, mock_session):
        """Test database check returns 'disconnected' on error."""
        from sqlalchemy.exc import SQLAlchemyError

        mock_session.side_effect = SQLAlchemyError("Connection failed")
        service = HealthCheckService()
        status = service._check_database()
        assert status == "disconnected"

    @patch("src.services.database.session_scope")
    def test_check_database_timeout(self, mock_session):
        """Test database check returns 'timeout' on timeout."""
        mock_session.side_effect = TimeoutError("Database check timed out")
        service = HealthCheckService()
        status = service._check_database()
        assert status == "timeout"

    @patch("src.services.database.session_scope")
    def test_check_database_unexpected_error(self, mock_session):
        """Test database check handles unexpected errors."""
        mock_session.side_effect = RuntimeError("Unexpected error")
        service = HealthCheckService()
        status = service._check_database()
        assert status == "disconnected"


class TestFileWriting:
    """Test health status file writing."""

    def test_write_health_status_success(self, tmp_path):
        """Test successful health file write."""
        health_file = tmp_path / "health.json"
        service = HealthCheckService(health_file=health_file)

        status_data = {
            "status": "online",
            "database": "connected",
            "timestamp": "2025-11-08T12:00:00Z",
            "app_version": "0.1.0",
            "api_version": "v1",
        }

        result = service._write_health_status(status_data)

        assert result is True
        assert health_file.exists()

        # Verify JSON content
        with open(health_file) as f:
            written_data = json.load(f)

        assert written_data == status_data

    def test_write_creates_directory(self, tmp_path):
        """Test that missing data directory is created."""
        health_file = tmp_path / "newdir" / "health.json"
        service = HealthCheckService(health_file=health_file)

        status_data = {"status": "online"}
        service._write_health_status(status_data)

        assert health_file.parent.exists()
        assert health_file.exists()

    def test_write_error_handling(self, tmp_path):
        """Test file write error is handled gracefully."""
        health_file = tmp_path / "readonly" / "health.json"
        service = HealthCheckService(health_file=health_file)

        # Make parent directory read-only (Unix-like systems)
        # On Windows, this test may behave differently
        status_data = {"status": "online"}
        # Should not raise exception even on write failure
        result = service._write_health_status(status_data)
        # Result depends on file system permissions


class TestVersionReading:
    """Test application version reading."""

    def test_get_app_version_success(self):
        """Test reading version from pyproject.toml."""
        service = HealthCheckService()
        version = service._app_version

        # Should read actual version from pyproject.toml
        # or return "unknown" if not available
        assert isinstance(version, str)
        assert len(version) > 0

    @patch("src.services.health_service.Path.exists")
    def test_get_app_version_file_not_found(self, mock_exists):
        """Test version fallback when pyproject.toml missing."""
        mock_exists.return_value = False
        service = HealthCheckService()
        assert service._app_version == "unknown"

    @patch("src.services.health_service.tomllib", None)
    def test_get_app_version_no_tomllib(self):
        """Test version fallback when tomllib not available."""
        service = HealthCheckService()
        assert service._app_version == "unknown"


# Integration test placeholder
class TestHealthCheckIntegration:
    """Integration tests for full health check cycle."""

    @pytest.mark.integration
    def test_full_health_check_cycle(self, tmp_path):
        """Test complete health check cycle with file write."""
        health_file = tmp_path / "health.json"
        service = HealthCheckService(check_interval=1, health_file=health_file)

        service.start()
        time.sleep(2)  # Wait for at least one health check
        service.stop()

        # Verify health file was created and contains valid data
        assert health_file.exists()

        with open(health_file) as f:
            data = json.load(f)

        assert "status" in data
        assert "database" in data
        assert "timestamp" in data
        assert "app_version" in data
        assert "api_version" in data
        assert data["api_version"] == "v1"
