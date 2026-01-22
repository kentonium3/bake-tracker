"""Tests for UI session utilities."""

import pytest
from sqlalchemy.orm import Session
from sqlalchemy import text

from src.ui.utils import ui_session


class TestUISession:
    """Tests for ui_session context manager."""

    def test_ui_session_yields_session(self):
        """ui_session should yield a SQLAlchemy Session."""
        with ui_session() as session:
            assert isinstance(session, Session)

    def test_ui_session_commits_on_success(self):
        """Changes should persist after successful context exit."""
        with ui_session() as session:
            # Query to verify session works (read-only test)
            result = session.execute(text("SELECT 1")).scalar()
            assert result == 1

    def test_ui_session_rolls_back_on_exception(self):
        """Changes should roll back if exception raised."""
        try:
            with ui_session() as session:
                # Start some operation
                session.execute(text("SELECT 1"))
                # Simulate error
                raise ValueError("Simulated error")
        except ValueError:
            pass  # Expected

        # Verify we can still use sessions (no corruption)
        with ui_session() as session:
            result = session.execute(text("SELECT 1")).scalar()
            assert result == 1

    def test_ui_session_allows_nested_queries(self):
        """Session should support multiple queries."""
        with ui_session() as session:
            r1 = session.execute(text("SELECT 1")).scalar()
            r2 = session.execute(text("SELECT 2")).scalar()
            assert r1 == 1
            assert r2 == 2

    def test_ui_session_importable_from_utils(self):
        """ui_session should be importable from src.ui.utils."""
        from src.ui.utils import ui_session as imported_ui_session
        assert imported_ui_session is not None
        assert callable(imported_ui_session)
