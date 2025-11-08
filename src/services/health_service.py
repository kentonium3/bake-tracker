"""
Health Check Service - Background monitoring for application health status.

This module provides a background service that periodically writes system health
information to a JSON file for external monitoring tools. The service runs on a
daemon thread and checks database connectivity, application status, and version
information every 30 seconds.

Example usage:
    from src.services.health_service import HealthCheckService

    service = HealthCheckService()
    service.start()  # Begins background monitoring
    # ... application runs ...
    service.stop()   # Clean shutdown
"""

import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

# For version reading (WP05)
try:
    import tomllib  # Python 3.11+
except ImportError:
    try:
        import tomli as tomllib  # Fallback package
    except ImportError:
        tomllib = None  # Will handle gracefully


class HealthCheckService:
    """
    Background service for writing periodic health status to file.

    The service runs on a daemon thread and updates `data/health.json` every
    30 seconds with current application status, database connectivity, timestamp,
    and version information.

    Attributes:
        _check_interval: Seconds between health checks (default: 30)
        _health_file: Path to health status JSON file
        _stop_event: Threading event for signaling shutdown
        _thread: Background daemon thread
        _app_version: Cached application version from pyproject.toml
    """

    def __init__(self, check_interval: int = 30, health_file: Optional[Path] = None):
        """
        Initialize the health check service.

        Args:
            check_interval: Seconds between health checks (default: 30)
            health_file: Custom path for health status file (default: data/health.json)
        """
        self._logger = logging.getLogger(__name__)
        self._check_interval = check_interval
        self._health_file = health_file or Path("data/health.json")
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._app_version = self._get_app_version()

        # Ensure data directory exists
        self._health_file.parent.mkdir(parents=True, exist_ok=True)

        self._logger.info(f"Health check service initialized (interval: {check_interval}s)")

    def start(self) -> None:
        """
        Start the health check background service.

        Launches a daemon thread that performs periodic health checks. If the
        service is already running, this method does nothing.

        Raises:
            RuntimeError: If thread fails to start
        """
        if self._thread and self._thread.is_alive():
            self._logger.warning("Health check service is already running")
            return

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._health_check_loop,
            name="HealthCheckThread",
            daemon=True,  # Auto-terminates when main thread exits
        )
        self._thread.start()
        self._logger.info("Health check service started")

    def stop(self, timeout: float = 2.0) -> None:
        """
        Stop the health check background service.

        Signals the background thread to stop and waits for clean shutdown.

        Args:
            timeout: Maximum seconds to wait for thread termination (default: 2.0)
        """
        if not self._thread or not self._thread.is_alive():
            self._logger.info("Health check service is not running")
            return

        self._logger.info("Stopping health check service...")
        self._stop_event.set()
        self._thread.join(timeout=timeout)

        if self._thread.is_alive():
            self._logger.warning("Health check thread did not stop within timeout")
        else:
            self._logger.info("Health check service stopped")

    def _health_check_loop(self) -> None:
        """
        Main loop for periodic health checks (runs in background thread).

        Continuously performs health checks every `_check_interval` seconds
        until stop() is called. Uses Event.wait() with timeout for clean
        shutdown without polling.
        """
        self._logger.info("Health check loop started")

        while not self._stop_event.is_set():
            try:
                # Perform health check and write status
                db_status = self._check_database()
                status_data = {
                    "status": "online" if db_status == "connected" else "degraded",
                    "database": db_status,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "app_version": self._app_version,  # WP05 will populate
                    "api_version": "v1",
                }

                # Write health status to file
                self._write_health_status(status_data)
                self._logger.debug(
                    f"Health check performed: status={status_data['status']}, "
                    f"db={status_data['database']}"
                )

            except Exception as e:
                # Never crash the health check thread
                self._logger.error(f"Error during health check: {e}", exc_info=True)

            # Wait for interval or until stop signal
            # This allows clean shutdown without busy-waiting
            self._stop_event.wait(timeout=self._check_interval)

        self._logger.info("Health check loop stopped")

    def _check_database(self) -> str:
        """
        Test database connectivity with timeout.

        Attempts to execute a simple query to verify database connection.
        Uses existing session_scope context manager for safe connection handling.

        Returns:
            "connected" if database is accessible
            "disconnected" if database connection fails
            "timeout" if connection attempt exceeds 3 seconds

        Note:
            This method must complete quickly to avoid blocking the health check loop.
            Maximum execution time is 3 seconds before timeout.
        """
        try:
            from src.services.database import session_scope
            from sqlalchemy import text
            from sqlalchemy.exc import SQLAlchemyError
            import signal

            def timeout_handler(signum, frame):
                raise TimeoutError("Database check timed out")

            # Set 3-second timeout
            # Note: signal.alarm only works on Unix/Linux
            # For Windows, this will skip timeout enforcement (acceptable for health check)
            try:
                signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(3)
            except AttributeError:
                # Windows doesn't have SIGALRM, continue without timeout
                pass

            # Attempt simple database query
            with session_scope() as session:
                session.execute(text("SELECT 1"))

            # Cancel timeout if it was set
            try:
                signal.alarm(0)
            except AttributeError:
                pass

            return "connected"

        except TimeoutError:
            self._logger.warning("Database connection check timed out after 3 seconds")
            return "timeout"

        except SQLAlchemyError as e:
            self._logger.error(f"Database connection failed: {e}")
            return "disconnected"

        except Exception as e:
            self._logger.error(
                f"Unexpected error checking database connectivity: {e}", exc_info=True
            )
            return "disconnected"

    def _write_health_status(self, status_data: Dict) -> bool:
        """
        Write health status to file using atomic write-and-rename pattern.

        Writes status data to a temporary file first, then atomically renames it
        to the target filename. This prevents monitoring tools from reading
        partially-written data.

        Args:
            status_data: Dictionary containing health status fields

        Returns:
            True if write successful, False if write failed

        Note:
            Errors are logged but do not raise exceptions to prevent
            disrupting the health check loop.
        """
        try:
            # Write to temporary file first
            tmp_file = self._health_file.with_suffix(".json.tmp")

            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(status_data, f, indent=2, ensure_ascii=False)

            # Atomic rename (on most file systems)
            tmp_file.rename(self._health_file)

            return True

        except (IOError, OSError) as e:
            self._logger.error(f"Failed to write health status file: {e}")
            return False

        except Exception as e:
            self._logger.error(f"Unexpected error writing health status: {e}", exc_info=True)
            return False

    def _get_app_version(self) -> str:
        """
        Read application version from pyproject.toml.

        Attempts to read the version from the project's pyproject.toml file.
        Uses tomllib (Python 3.11+) or tomli package as fallback.

        Returns:
            Application version string (e.g., "0.1.0") or "unknown" if read fails
        """
        try:
            # Locate pyproject.toml (relative to this file)
            toml_path = Path(__file__).parent.parent.parent / "pyproject.toml"

            if not toml_path.exists():
                self._logger.warning(f"pyproject.toml not found at {toml_path}")
                return "unknown"

            # Read and parse TOML
            if tomllib is not None:
                with open(toml_path, "rb") as f:
                    data = tomllib.load(f)
                return data.get("project", {}).get("version", "unknown")
            else:
                self._logger.warning("tomllib/tomli not available, cannot read version")
                return "unknown"

        except Exception as e:
            self._logger.warning(f"Could not read application version: {e}")
            return "unknown"
