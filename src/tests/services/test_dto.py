"""Tests for pagination DTOs (Feature F093).

Tests cover:
- PaginationParams offset calculation
- PaginationParams validation
- PaginatedResult pages calculation
- PaginatedResult navigation properties
- Generic typing
"""

import pytest
from src.services.dto import PaginationParams, PaginatedResult


class TestPaginationParams:
    """Tests for PaginationParams dataclass."""

    def test_offset_page_one(self):
        """Page 1 has offset 0."""
        params = PaginationParams(page=1, per_page=50)
        assert params.offset() == 0

    def test_offset_page_two(self):
        """Page 2 with 50 per page has offset 50."""
        params = PaginationParams(page=2, per_page=50)
        assert params.offset() == 50

    def test_offset_page_three_small_page_size(self):
        """Page 3 with 25 per page has offset 50."""
        params = PaginationParams(page=3, per_page=25)
        assert params.offset() == 50

    def test_offset_large_page_number(self):
        """Large page number calculates correctly."""
        params = PaginationParams(page=100, per_page=10)
        assert params.offset() == 990

    def test_default_values(self):
        """Default is page 1 with 50 per page."""
        params = PaginationParams()
        assert params.page == 1
        assert params.per_page == 50
        assert params.offset() == 0

    def test_validation_page_zero(self):
        """page=0 raises ValueError."""
        with pytest.raises(ValueError, match="page must be >= 1"):
            PaginationParams(page=0)

    def test_validation_page_negative(self):
        """Negative page raises ValueError."""
        with pytest.raises(ValueError, match="page must be >= 1"):
            PaginationParams(page=-1)

    def test_validation_per_page_zero(self):
        """per_page=0 raises ValueError."""
        with pytest.raises(ValueError, match="per_page must be >= 1"):
            PaginationParams(per_page=0)

    def test_validation_per_page_negative(self):
        """Negative per_page raises ValueError."""
        with pytest.raises(ValueError, match="per_page must be >= 1"):
            PaginationParams(per_page=-1)

    def test_validation_per_page_too_large(self):
        """per_page > 1000 raises ValueError."""
        with pytest.raises(ValueError, match="per_page must be <= 1000"):
            PaginationParams(per_page=1001)

    def test_validation_per_page_max_allowed(self):
        """per_page=1000 is valid."""
        params = PaginationParams(per_page=1000)
        assert params.per_page == 1000

    def test_validation_per_page_one(self):
        """per_page=1 is valid."""
        params = PaginationParams(per_page=1)
        assert params.per_page == 1


class TestPaginatedResult:
    """Tests for PaginatedResult dataclass."""

    def test_pages_exact_division(self):
        """100 items / 50 per page = 2 pages."""
        result = PaginatedResult(items=[], total=100, page=1, per_page=50)
        assert result.pages == 2

    def test_pages_with_remainder(self):
        """101 items / 50 per page = 3 pages."""
        result = PaginatedResult(items=[], total=101, page=1, per_page=50)
        assert result.pages == 3

    def test_pages_one_item_over(self):
        """51 items / 50 per page = 2 pages."""
        result = PaginatedResult(items=[], total=51, page=1, per_page=50)
        assert result.pages == 2

    def test_pages_empty_result(self):
        """0 items returns 1 page (empty page)."""
        result = PaginatedResult(items=[], total=0, page=1, per_page=50)
        assert result.pages == 1

    def test_pages_fewer_than_page_size(self):
        """10 items / 50 per page = 1 page."""
        result = PaginatedResult(items=[], total=10, page=1, per_page=50)
        assert result.pages == 1

    def test_pages_exactly_one_page(self):
        """50 items / 50 per page = 1 page."""
        result = PaginatedResult(items=[], total=50, page=1, per_page=50)
        assert result.pages == 1

    def test_has_next_on_first_of_many(self):
        """First page of 3 has next."""
        result = PaginatedResult(items=[], total=150, page=1, per_page=50)
        assert result.has_next is True

    def test_has_next_on_middle_page(self):
        """Middle page has next."""
        result = PaginatedResult(items=[], total=150, page=2, per_page=50)
        assert result.has_next is True

    def test_has_next_on_last_page(self):
        """Last page has no next."""
        result = PaginatedResult(items=[], total=100, page=2, per_page=50)
        assert result.has_next is False

    def test_has_next_single_page(self):
        """Single page has no next."""
        result = PaginatedResult(items=[], total=10, page=1, per_page=50)
        assert result.has_next is False

    def test_has_next_empty_result(self):
        """Empty result has no next."""
        result = PaginatedResult(items=[], total=0, page=1, per_page=50)
        assert result.has_next is False

    def test_has_prev_on_first_page(self):
        """First page has no prev."""
        result = PaginatedResult(items=[], total=100, page=1, per_page=50)
        assert result.has_prev is False

    def test_has_prev_on_second_page(self):
        """Second page has prev."""
        result = PaginatedResult(items=[], total=100, page=2, per_page=50)
        assert result.has_prev is True

    def test_has_prev_on_middle_page(self):
        """Middle page has prev."""
        result = PaginatedResult(items=[], total=150, page=2, per_page=50)
        assert result.has_prev is True

    def test_has_prev_on_last_page(self):
        """Last page has prev."""
        result = PaginatedResult(items=[], total=100, page=2, per_page=50)
        assert result.has_prev is True

    def test_generic_typing_with_strings(self):
        """PaginatedResult works with string items."""
        result: PaginatedResult[str] = PaginatedResult(
            items=["a", "b", "c"], total=3, page=1, per_page=10
        )
        assert result.items == ["a", "b", "c"]
        assert len(result.items) == 3

    def test_generic_typing_with_integers(self):
        """PaginatedResult works with integer items."""
        result: PaginatedResult[int] = PaginatedResult(
            items=[1, 2, 3, 4, 5], total=100, page=1, per_page=5
        )
        assert result.items == [1, 2, 3, 4, 5]
        assert result.total == 100

    def test_generic_typing_with_dicts(self):
        """PaginatedResult works with dict items."""
        items = [{"id": 1, "name": "foo"}, {"id": 2, "name": "bar"}]
        result: PaginatedResult[dict] = PaginatedResult(
            items=items, total=2, page=1, per_page=10
        )
        assert len(result.items) == 2
        assert result.items[0]["name"] == "foo"

    def test_combined_properties(self):
        """All properties work together correctly."""
        # Middle page scenario: page 2 of 3
        result = PaginatedResult(items=["x"] * 50, total=150, page=2, per_page=50)
        assert result.pages == 3
        assert result.has_prev is True
        assert result.has_next is True

    def test_first_page_properties(self):
        """First page of multi-page result."""
        result = PaginatedResult(items=["x"] * 50, total=150, page=1, per_page=50)
        assert result.pages == 3
        assert result.has_prev is False
        assert result.has_next is True

    def test_last_page_properties(self):
        """Last page of multi-page result."""
        result = PaginatedResult(items=["x"] * 50, total=150, page=3, per_page=50)
        assert result.pages == 3
        assert result.has_prev is True
        assert result.has_next is False

    def test_single_page_all_items(self):
        """Single page with all items (desktop scenario)."""
        result = PaginatedResult(items=["x"] * 100, total=100, page=1, per_page=100)
        assert result.pages == 1
        assert result.has_prev is False
        assert result.has_next is False
