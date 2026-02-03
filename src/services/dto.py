"""Data Transfer Objects for service layer.

This module provides type-safe data structures for pagination and other
cross-cutting concerns in the service layer.

Feature: F093 Pagination DTOs Foundation
"""

from dataclasses import dataclass
from typing import Generic, TypeVar, List

T = TypeVar("T")


@dataclass
class PaginationParams:
    """Pagination parameters for list operations.

    Provides page-based pagination with configurable page size. Use this
    when calling service functions that support pagination.

    Desktop usage: Optional - pass None to get all items (current behavior)
    Web usage: Required - pass page/per_page for paginated results

    Attributes:
        page: Page number (1-indexed, default 1)
        per_page: Items per page (default 50, max 1000)

    Examples:
        # Desktop (get all items - pass pagination=None to service)
        result = list_items(pagination=None)  # Returns all items

        # Web (paginated)
        params = PaginationParams(page=2, per_page=25)
        result = list_items(pagination=params)
        print(f"Showing items {params.offset() + 1} to {params.offset() + len(result.items)}")

    Raises:
        ValueError: If page < 1, per_page < 1, or per_page > 1000
    """

    page: int = 1
    per_page: int = 50

    def __post_init__(self) -> None:
        """Validate pagination parameters."""
        if self.page < 1:
            raise ValueError("page must be >= 1")
        if self.per_page < 1:
            raise ValueError("per_page must be >= 1")
        if self.per_page > 1000:
            raise ValueError("per_page must be <= 1000")

    def offset(self) -> int:
        """Calculate SQL OFFSET value.

        Returns:
            Offset for SQL query: (page - 1) * per_page

        Examples:
            >>> PaginationParams(page=1, per_page=50).offset()
            0
            >>> PaginationParams(page=2, per_page=50).offset()
            50
            >>> PaginationParams(page=3, per_page=25).offset()
            50
        """
        return (self.page - 1) * self.per_page


@dataclass
class PaginatedResult(Generic[T]):
    """Generic paginated result container.

    Type-safe container for paginated query results with metadata for
    navigation. Works with any model type through Generic[T].

    Desktop usage: All items in single page (pagination=None in service)
    Web usage: One page of items (pagination=PaginationParams in service)

    Attributes:
        items: List of items for this page
        total: Total number of items across all pages
        page: Current page number (1-indexed)
        per_page: Items per page

    Properties:
        pages: Total number of pages
        has_next: Whether there's a next page
        has_prev: Whether there's a previous page

    Examples:
        # Desktop (all items in one "page")
        result = PaginatedResult(
            items=all_items,
            total=len(all_items),
            page=1,
            per_page=len(all_items) or 1
        )

        # Web (paginated)
        result = PaginatedResult(
            items=page_items,
            total=1000,
            page=2,
            per_page=50
        )
        print(f"Page {result.page} of {result.pages}")
        if result.has_next:
            print("More results available")

        # Type-safe with any model
        ingredients: PaginatedResult[Ingredient] = list_ingredients(pagination=params)
        for ingredient in ingredients.items:
            print(ingredient.display_name)  # IDE knows this is an Ingredient
    """

    items: List[T]
    total: int
    page: int
    per_page: int

    @property
    def pages(self) -> int:
        """Calculate total number of pages.

        Returns:
            Total pages (minimum 1, even for empty results)

        Examples:
            >>> PaginatedResult(items=[], total=100, page=1, per_page=50).pages
            2
            >>> PaginatedResult(items=[], total=101, page=1, per_page=50).pages
            3
            >>> PaginatedResult(items=[], total=0, page=1, per_page=50).pages
            1
        """
        if self.total == 0:
            return 1
        return (self.total + self.per_page - 1) // self.per_page

    @property
    def has_next(self) -> bool:
        """Check if there's a next page.

        Returns:
            True if current page is not the last page

        Examples:
            >>> PaginatedResult(items=[], total=100, page=1, per_page=50).has_next
            True
            >>> PaginatedResult(items=[], total=100, page=2, per_page=50).has_next
            False
        """
        return self.page < self.pages

    @property
    def has_prev(self) -> bool:
        """Check if there's a previous page.

        Returns:
            True if current page is not the first page

        Examples:
            >>> PaginatedResult(items=[], total=100, page=1, per_page=50).has_prev
            False
            >>> PaginatedResult(items=[], total=100, page=2, per_page=50).has_prev
            True
        """
        return self.page > 1
