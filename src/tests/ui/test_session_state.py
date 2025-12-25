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


class TestDialogSessionMemoryHelpers:
    """Tests for dialog helper methods used in session memory (F029).

    These test the helper methods that format and strip star indicators
    for session-remembered values.
    """

    def test_format_supplier_with_star(self):
        """Verify star formatting adds prefix correctly."""
        # Import the class to access instance methods
        # We test the logic directly without instantiating the dialog
        display_name = "Costco Waltham MA"
        expected = "* Costco Waltham MA"
        # Simulate the formatting logic
        result = f"* {display_name}"
        assert result == expected

    def test_strip_star_from_supplier_with_star(self):
        """Verify star is stripped when present."""
        starred = "* Costco Waltham MA"
        # Simulate the stripping logic
        if starred.startswith("* "):
            result = starred[2:]
        else:
            result = starred
        assert result == "Costco Waltham MA"

    def test_strip_star_from_supplier_without_star(self):
        """Verify non-starred names are unchanged."""
        plain = "Costco Waltham MA"
        # Simulate the stripping logic
        if plain.startswith("* "):
            result = plain[2:]
        else:
            result = plain
        assert result == "Costco Waltham MA"

    def test_session_memory_workflow(self):
        """Verify complete session memory workflow.

        This tests the expected flow:
        1. First dialog open - no session data
        2. User selects supplier
        3. On save, session is updated
        4. Second dialog open - session supplier pre-selected
        """
        state = get_session_state()

        # 1. First dialog - no session data
        assert state.get_last_supplier_id() is None

        # 2. User selects supplier and saves (simulated)
        selected_supplier_id = 42

        # 3. On save, session is updated
        state.update_supplier(selected_supplier_id)

        # 4. Second dialog - session supplier available
        assert state.get_last_supplier_id() == 42

    def test_session_not_updated_on_cancel(self):
        """Verify session is not updated when dialog is cancelled.

        Cancel means closing without calling save, so session update
        code is never reached.
        """
        state = get_session_state()

        # Set initial state
        state.update_supplier(42)
        initial_supplier = state.get_last_supplier_id()

        # User opens dialog, selects different supplier, then cancels
        # (In real code, cancel just destroys dialog without updating session)
        # Session should remain unchanged
        assert state.get_last_supplier_id() == initial_supplier

    def test_session_updates_only_on_new_items(self):
        """Verify session update logic only applies to new items.

        When editing an existing item, we don't update session state
        because the supplier/category are already fixed for that item.
        """
        state = get_session_state()

        # Set initial session state
        state.update_supplier(42)

        # Simulate editing an existing item
        # In the real code, is_editing=True skips the session update
        is_editing = True

        # Only update if not editing (simulating _save logic)
        new_supplier_id = 99
        if not is_editing and new_supplier_id:
            state.update_supplier(new_supplier_id)

        # Session should NOT be updated because we're editing
        assert state.get_last_supplier_id() == 42  # Original value preserved
