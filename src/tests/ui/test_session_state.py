"""
Unit tests for SessionState singleton.

Tests verify:
- Singleton pattern (same instance returned on each call)
- State updates (supplier, category)
- State retrieval (getters return correct values)
- Reset functionality (test isolation)
"""

import pytest

from src.ui.session_state import SessionState, get_session_state


@pytest.fixture(autouse=True)
def reset_session_state():
    """Reset session state before each test for isolation."""
    state = get_session_state()
    state.reset()
    yield
    state.reset()


class TestSessionStateSingleton:
    """Tests for singleton behavior."""

    def test_singleton_same_instance(self):
        """Verify SessionState returns same instance on multiple calls."""
        state1 = SessionState()
        state2 = SessionState()
        assert state1 is state2

    def test_get_session_state_returns_singleton(self):
        """Verify get_session_state() returns the singleton."""
        state1 = get_session_state()
        state2 = get_session_state()
        assert state1 is state2

    def test_get_session_state_same_as_direct_instantiation(self):
        """Verify convenience function returns same instance as direct call."""
        state1 = SessionState()
        state2 = get_session_state()
        assert state1 is state2


class TestSessionStateUpdates:
    """Tests for state update methods."""

    def test_update_supplier(self):
        """Verify supplier update stores the value."""
        state = get_session_state()
        state.update_supplier(42)
        assert state.get_last_supplier_id() == 42

    def test_update_supplier_overwrites_previous(self):
        """Verify updating supplier replaces previous value."""
        state = get_session_state()
        state.update_supplier(42)
        state.update_supplier(99)
        assert state.get_last_supplier_id() == 99

    def test_update_category(self):
        """Verify category update stores the value."""
        state = get_session_state()
        state.update_category("Baking")
        assert state.get_last_category() == "Baking"

    def test_update_category_overwrites_previous(self):
        """Verify updating category replaces previous value."""
        state = get_session_state()
        state.update_category("Baking")
        state.update_category("Dairy")
        assert state.get_last_category() == "Dairy"


class TestSessionStateGetters:
    """Tests for state retrieval methods."""

    def test_initial_supplier_is_none(self):
        """Verify supplier is None before any update."""
        state = get_session_state()
        assert state.get_last_supplier_id() is None

    def test_initial_category_is_none(self):
        """Verify category is None before any update."""
        state = get_session_state()
        assert state.get_last_category() is None


class TestSessionStateReset:
    """Tests for reset functionality."""

    def test_reset_clears_supplier(self):
        """Verify reset clears supplier."""
        state = get_session_state()
        state.update_supplier(42)
        state.reset()
        assert state.get_last_supplier_id() is None

    def test_reset_clears_category(self):
        """Verify reset clears category."""
        state = get_session_state()
        state.update_category("Baking")
        state.reset()
        assert state.get_last_category() is None

    def test_reset_clears_all_state(self):
        """Verify reset clears both supplier and category."""
        state = get_session_state()
        state.update_supplier(42)
        state.update_category("Baking")
        state.reset()
        assert state.get_last_supplier_id() is None
        assert state.get_last_category() is None


class TestSessionStatePersistence:
    """Tests for state persistence across calls."""

    def test_state_persists_across_get_calls(self):
        """Verify state set in one call is visible in another."""
        state1 = get_session_state()
        state1.update_supplier(42)
        state1.update_category("Baking")

        state2 = get_session_state()
        assert state2.get_last_supplier_id() == 42
        assert state2.get_last_category() == "Baking"
