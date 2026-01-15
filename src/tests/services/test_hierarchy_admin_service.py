"""
Tests for hierarchy admin service shared utilities (Feature 052).

Tests cover:
- validate_unique_sibling_name()
- generate_slug()
- validate_no_cycle()
- validate_name_not_empty()
- trim_name()
"""

import pytest
from dataclasses import dataclass
from typing import Optional

from src.services import hierarchy_admin_service


@dataclass
class MockEntity:
    """Mock entity for testing sibling validation."""

    id: int
    display_name: Optional[str] = None
    name: Optional[str] = None


class TestValidateUniqueSiblingName:
    """Tests for validate_unique_sibling_name()."""

    def test_returns_true_for_unique_name(self):
        """Test that unique name among siblings returns True."""
        siblings = [
            MockEntity(id=1, display_name="Apple"),
            MockEntity(id=2, display_name="Banana"),
            MockEntity(id=3, display_name="Cherry"),
        ]
        result = hierarchy_admin_service.validate_unique_sibling_name(siblings, "Durian")
        assert result is True

    def test_returns_false_for_duplicate_name(self):
        """Test that duplicate name returns False."""
        siblings = [
            MockEntity(id=1, display_name="Apple"),
            MockEntity(id=2, display_name="Banana"),
        ]
        result = hierarchy_admin_service.validate_unique_sibling_name(siblings, "Apple")
        assert result is False

    def test_excludes_self_on_rename(self):
        """Test that exclude_id skips the item being renamed."""
        siblings = [
            MockEntity(id=1, display_name="Apple"),
            MockEntity(id=2, display_name="Banana"),
        ]
        # Renaming "Apple" to "Apple" should be allowed
        result = hierarchy_admin_service.validate_unique_sibling_name(
            siblings, "Apple", exclude_id=1
        )
        assert result is True

    def test_case_insensitive_comparison(self):
        """Test that name comparison is case-insensitive."""
        siblings = [MockEntity(id=1, display_name="Apple")]
        result = hierarchy_admin_service.validate_unique_sibling_name(siblings, "APPLE")
        assert result is False

    def test_trims_whitespace(self):
        """Test that whitespace is trimmed before comparison."""
        siblings = [MockEntity(id=1, display_name="Apple")]
        result = hierarchy_admin_service.validate_unique_sibling_name(siblings, "  Apple  ")
        assert result is False

    def test_works_with_name_attribute(self):
        """Test that it works with 'name' attribute (for materials)."""
        siblings = [MockEntity(id=1, name="Ribbon")]
        result = hierarchy_admin_service.validate_unique_sibling_name(siblings, "Ribbon")
        assert result is False

    def test_empty_siblings_list(self):
        """Test that empty siblings list returns True."""
        result = hierarchy_admin_service.validate_unique_sibling_name([], "AnyName")
        assert result is True


class TestGenerateSlug:
    """Tests for generate_slug()."""

    def test_basic_slug_generation(self):
        """Test basic slug generation."""
        result = hierarchy_admin_service.generate_slug("All Purpose Flour")
        assert result == "all-purpose-flour"

    def test_removes_special_characters(self):
        """Test that special characters are removed."""
        result = hierarchy_admin_service.generate_slug("Semi-Sweet (Chips)!")
        assert result == "semi-sweet-chips"

    def test_collapses_multiple_spaces(self):
        """Test that multiple spaces become single hyphen."""
        result = hierarchy_admin_service.generate_slug("Too   Many    Spaces")
        assert result == "too-many-spaces"

    def test_collapses_multiple_hyphens(self):
        """Test that multiple hyphens become single hyphen."""
        result = hierarchy_admin_service.generate_slug("Already---Hyphenated")
        assert result == "already-hyphenated"

    def test_replaces_underscores_with_hyphens(self):
        """Test that underscores become hyphens."""
        result = hierarchy_admin_service.generate_slug("has_underscores_here")
        assert result == "has-underscores-here"

    def test_removes_leading_trailing_hyphens(self):
        """Test that leading/trailing hyphens are removed."""
        result = hierarchy_admin_service.generate_slug(" - Test Name - ")
        assert result == "test-name"

    def test_empty_string_returns_empty(self):
        """Test that empty string returns empty."""
        result = hierarchy_admin_service.generate_slug("")
        assert result == ""

    def test_only_special_chars_returns_empty(self):
        """Test that string with only special chars returns empty."""
        result = hierarchy_admin_service.generate_slug("!@#$%^&*()")
        assert result == ""


class TestValidateNoCycle:
    """Tests for validate_no_cycle()."""

    def test_returns_true_for_safe_move(self):
        """Test that safe move returns True."""
        descendants = [
            MockEntity(id=2, name="Child"),
            MockEntity(id=3, name="Grandchild"),
        ]
        proposed_parent = MockEntity(id=4, name="Unrelated")
        result = hierarchy_admin_service.validate_no_cycle(descendants, proposed_parent)
        assert result is True

    def test_returns_false_for_cycle_to_child(self):
        """Test that moving under own child returns False."""
        child = MockEntity(id=2, name="Child")
        descendants = [child, MockEntity(id=3, name="Grandchild")]
        result = hierarchy_admin_service.validate_no_cycle(descendants, child)
        assert result is False

    def test_returns_false_for_cycle_to_grandchild(self):
        """Test that moving under own grandchild returns False."""
        grandchild = MockEntity(id=3, name="Grandchild")
        descendants = [MockEntity(id=2, name="Child"), grandchild]
        result = hierarchy_admin_service.validate_no_cycle(descendants, grandchild)
        assert result is False

    def test_returns_true_for_none_parent(self):
        """Test that moving to root (None parent) returns True."""
        descendants = [MockEntity(id=2, name="Child")]
        result = hierarchy_admin_service.validate_no_cycle(descendants, None)
        assert result is True

    def test_empty_descendants_returns_true(self):
        """Test that empty descendants list returns True."""
        proposed_parent = MockEntity(id=4, name="Some Parent")
        result = hierarchy_admin_service.validate_no_cycle([], proposed_parent)
        assert result is True


class TestValidateNameNotEmpty:
    """Tests for validate_name_not_empty()."""

    def test_returns_true_for_valid_name(self):
        """Test that valid name returns True."""
        result = hierarchy_admin_service.validate_name_not_empty("Valid Name")
        assert result is True

    def test_returns_false_for_empty_string(self):
        """Test that empty string returns False."""
        result = hierarchy_admin_service.validate_name_not_empty("")
        assert result is False

    def test_returns_false_for_whitespace_only(self):
        """Test that whitespace-only string returns False."""
        result = hierarchy_admin_service.validate_name_not_empty("   ")
        assert result is False

    def test_returns_false_for_none(self):
        """Test that None returns False."""
        result = hierarchy_admin_service.validate_name_not_empty(None)
        assert result is False


class TestTrimName:
    """Tests for trim_name()."""

    def test_trims_leading_whitespace(self):
        """Test that leading whitespace is trimmed."""
        result = hierarchy_admin_service.trim_name("   Name")
        assert result == "Name"

    def test_trims_trailing_whitespace(self):
        """Test that trailing whitespace is trimmed."""
        result = hierarchy_admin_service.trim_name("Name   ")
        assert result == "Name"

    def test_trims_both_ends(self):
        """Test that both ends are trimmed."""
        result = hierarchy_admin_service.trim_name("  Name  ")
        assert result == "Name"

    def test_preserves_internal_whitespace(self):
        """Test that internal whitespace is preserved."""
        result = hierarchy_admin_service.trim_name("  Two Words  ")
        assert result == "Two Words"

    def test_empty_string_returns_empty(self):
        """Test that empty string returns empty."""
        result = hierarchy_admin_service.trim_name("")
        assert result == ""

    def test_none_returns_empty(self):
        """Test that None returns empty string."""
        result = hierarchy_admin_service.trim_name(None)
        assert result == ""
