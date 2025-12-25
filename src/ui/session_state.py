"""
Session state management for inventory entry workflow.

This module provides a singleton SessionState class that remembers the user's
last-used supplier and category across inventory entries during a single
application session. This enables rapid multi-item entry without repetitive
selections.

Session state is intentionally in-memory only - it resets when the application
restarts. This is the expected behavior per spec.

Usage:
    from src.ui.session_state import get_session_state

    # In dialog code:
    session = get_session_state()
    last_supplier_id = session.get_last_supplier_id()

    # On successful Add:
    session.update_supplier(supplier_id)
    session.update_category(category)
"""

from typing import Optional


class SessionState:
    """
    Singleton class for managing session-level state across inventory entries.

    This class stores the last-used supplier ID and category to enable rapid
    multi-item entry. State is only updated on successful inventory additions,
    not on cancel or close operations.

    The singleton pattern ensures all dialogs share the same state instance.
    """

    _instance: Optional["SessionState"] = None

    def __new__(cls) -> "SessionState":
        """Create or return the singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self) -> None:
        """Initialize instance attributes. Called once on first creation."""
        self.last_supplier_id: Optional[int] = None
        self.last_category: Optional[str] = None

    def update_supplier(self, supplier_id: int) -> None:
        """
        Update last-used supplier.

        Call ONLY on successful Add operation, not on cancel/close.

        Args:
            supplier_id: The ID of the supplier that was just used.
        """
        self.last_supplier_id = supplier_id

    def update_category(self, category: str) -> None:
        """
        Update last-selected category.

        Call ONLY on successful Add operation, not on cancel/close.

        Args:
            category: The category name that was just used.
        """
        self.last_category = category

    def get_last_supplier_id(self) -> Optional[int]:
        """
        Get the last-used supplier ID.

        Returns:
            The supplier ID if set, None otherwise.
        """
        return self.last_supplier_id

    def get_last_category(self) -> Optional[str]:
        """
        Get the last-selected category.

        Returns:
            The category name if set, None otherwise.
        """
        return self.last_category

    def reset(self) -> None:
        """
        Reset all session state.

        This is primarily for test isolation - call in test fixtures to
        ensure tests don't interfere with each other.
        """
        self.last_supplier_id = None
        self.last_category = None


def get_session_state() -> SessionState:
    """
    Get the session state singleton instance.

    This is the preferred way to access session state from dialogs.

    Returns:
        The SessionState singleton instance.
    """
    return SessionState()
