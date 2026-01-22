"""Session utilities for UI layer.

This module provides session management utilities for UI components
that need to perform transactional database operations.

The ui_session() context manager is the standard pattern for UI code
to interact with service layer functions that require session parameters.
"""

from contextlib import contextmanager
from typing import Generator

from sqlalchemy.orm import Session

from src.services.database import session_scope


@contextmanager
def ui_session() -> Generator[Session, None, None]:
    """
    Context manager for UI operations requiring database sessions.

    Provides a SQLAlchemy Session that:
    - Commits automatically on successful exit
    - Rolls back automatically on exception
    - Can be passed to service functions requiring session

    Usage:
        from src.ui.utils import ui_session

        def handle_save_click(self):
            with ui_session() as session:
                event_service.create_event(name="My Event", session=session)
                event_service.assign_package(..., session=session)
                # All operations in same transaction

    Yields:
        Session: SQLAlchemy Session for database operations.

    Raises:
        Any exception from the wrapped code block (after rollback).
    """
    with session_scope() as session:
        yield session
