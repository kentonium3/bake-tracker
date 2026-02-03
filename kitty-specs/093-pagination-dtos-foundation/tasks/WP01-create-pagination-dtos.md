---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
  - "T003"
  - "T004"
  - "T005"
title: "Create Pagination DTOs and Tests"
phase: "Phase 1-2 - Implementation"
lane: "done"
assignee: ""
agent: "claude"
shell_pid: "96214"
review_status: "approved"
reviewed_by: "Kent Gale"
dependencies: []
history:
  - timestamp: "2026-02-03T12:45:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 – Create Pagination DTOs and Tests

## Objectives & Success Criteria

Create the pagination infrastructure (PaginationParams and PaginatedResult[T]) with comprehensive unit tests.

**Success Criteria**:
- [ ] `src/services/dto.py` exists with both dataclasses
- [ ] PaginationParams validates page >= 1 and 1 <= per_page <= 1000
- [ ] PaginationParams.offset() calculates correctly
- [ ] PaginatedResult[T] is generic and type-safe
- [ ] PaginatedResult has pages, has_next, has_prev properties
- [ ] All unit tests pass
- [ ] Docstrings document desktop vs web usage patterns

---

## Context & Constraints

### Related Documents
- **Spec**: `kitty-specs/093-pagination-dtos-foundation/spec.md`
- **Plan**: `kitty-specs/093-pagination-dtos-foundation/plan.md`
- **Func-Spec**: `docs/func-spec/F093_pagination_dtos_foundation.md` (contains implementation examples)

### Architectural Constraints
- DTOs go in `src/services/dto.py` (create file)
- Tests go in `src/tests/services/test_dto.py` (create file)
- Zero impact on existing code - no imports from dto.py yet
- Use stdlib only (dataclasses, typing) - no new dependencies

### Key Files
- `src/services/dto.py` - CREATE
- `src/tests/services/test_dto.py` - CREATE

---

## Subtasks & Detailed Guidance

### Subtask T001 – Create PaginationParams dataclass

**Purpose**: Provide input parameters for paginated queries.

**Implementation**:
```python
from dataclasses import dataclass

@dataclass
class PaginationParams:
    """Pagination parameters for list operations."""
    page: int = 1
    per_page: int = 50

    def offset(self) -> int:
        """Calculate SQL OFFSET value."""
        return (self.page - 1) * self.per_page
```

**Files**: `src/services/dto.py`

---

### Subtask T002 – Create PaginatedResult[T] generic dataclass

**Purpose**: Provide type-safe container for paginated results.

**Implementation**:
```python
from typing import Generic, TypeVar, List

T = TypeVar('T')

@dataclass
class PaginatedResult(Generic[T]):
    """Generic paginated result container."""
    items: List[T]
    total: int
    page: int
    per_page: int

    @property
    def pages(self) -> int:
        """Calculate total number of pages."""
        if self.total == 0:
            return 1
        return (self.total + self.per_page - 1) // self.per_page

    @property
    def has_next(self) -> bool:
        """Check if there's a next page."""
        return self.page < self.pages

    @property
    def has_prev(self) -> bool:
        """Check if there's a previous page."""
        return self.page > 1
```

**Files**: `src/services/dto.py`

---

### Subtask T003 – Add validation and docstrings

**Purpose**: Ensure invalid parameters are rejected and usage is documented.

**Add to PaginationParams**:
```python
def __post_init__(self):
    """Validate pagination parameters."""
    if self.page < 1:
        raise ValueError("page must be >= 1")
    if self.per_page < 1:
        raise ValueError("per_page must be >= 1")
    if self.per_page > 1000:
        raise ValueError("per_page must be <= 1000")
```

**Docstrings should include**:
- Desktop usage: `pagination=None` returns all items
- Web usage: `pagination=PaginationParams(...)` returns one page
- Examples for both patterns

**Files**: `src/services/dto.py`

---

### Subtask T004 – Create unit tests for PaginationParams

**Purpose**: Verify offset calculation and validation.

**Test cases**:
```python
# src/tests/services/test_dto.py
import pytest
from src.services.dto import PaginationParams

class TestPaginationParams:
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

    def test_default_values(self):
        """Default is page 1 with 50 per page."""
        params = PaginationParams()
        assert params.page == 1
        assert params.per_page == 50

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

    def test_validation_per_page_too_large(self):
        """per_page > 1000 raises ValueError."""
        with pytest.raises(ValueError, match="per_page must be <= 1000"):
            PaginationParams(per_page=1001)

    def test_validation_per_page_max_allowed(self):
        """per_page=1000 is valid."""
        params = PaginationParams(per_page=1000)
        assert params.per_page == 1000
```

**Files**: `src/tests/services/test_dto.py`

---

### Subtask T005 – Create unit tests for PaginatedResult

**Purpose**: Verify pages calculation and navigation properties.

**Test cases**:
```python
from src.services.dto import PaginatedResult

class TestPaginatedResult:
    def test_pages_exact_division(self):
        """100 items / 50 per page = 2 pages."""
        result = PaginatedResult(items=[], total=100, page=1, per_page=50)
        assert result.pages == 2

    def test_pages_with_remainder(self):
        """101 items / 50 per page = 3 pages."""
        result = PaginatedResult(items=[], total=101, page=1, per_page=50)
        assert result.pages == 3

    def test_pages_empty_result(self):
        """0 items returns 1 page (empty page)."""
        result = PaginatedResult(items=[], total=0, page=1, per_page=50)
        assert result.pages == 1

    def test_pages_fewer_than_page_size(self):
        """10 items / 50 per page = 1 page."""
        result = PaginatedResult(items=[], total=10, page=1, per_page=50)
        assert result.pages == 1

    def test_has_next_on_first_of_many(self):
        """First page of 3 has next."""
        result = PaginatedResult(items=[], total=100, page=1, per_page=50)
        assert result.has_next is True

    def test_has_next_on_last_page(self):
        """Last page has no next."""
        result = PaginatedResult(items=[], total=100, page=2, per_page=50)
        assert result.has_next is False

    def test_has_next_single_page(self):
        """Single page has no next."""
        result = PaginatedResult(items=[], total=10, page=1, per_page=50)
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

    def test_generic_typing(self):
        """PaginatedResult works with typed items."""
        result: PaginatedResult[str] = PaginatedResult(
            items=["a", "b", "c"],
            total=3,
            page=1,
            per_page=10
        )
        assert result.items == ["a", "b", "c"]
```

**Files**: `src/tests/services/test_dto.py`

---

## Test Strategy

### Test Commands
```bash
# Run DTO tests
./run-tests.sh src/tests/services/test_dto.py -v

# Verify no regressions
./run-tests.sh -v
```

---

## Definition of Done Checklist

- [ ] `src/services/dto.py` created with PaginationParams and PaginatedResult[T]
- [ ] PaginationParams.offset() works correctly
- [ ] PaginationParams validation rejects invalid parameters
- [ ] PaginatedResult.pages calculated correctly
- [ ] PaginatedResult.has_next/has_prev work correctly
- [ ] All unit tests pass
- [ ] Docstrings document desktop vs web usage
- [ ] No impact on existing tests (regression check)

---

## Review Guidance

**Reviewers should verify**:
1. offset() calculation: (page - 1) * per_page
2. pages calculation handles edge cases (0 items, remainder)
3. Validation messages are clear
4. Docstrings include usage examples
5. All tests pass

---

## Activity Log

- 2026-02-03T12:45:00Z – system – lane=planned – Prompt generated via /spec-kitty.tasks
- 2026-02-03T15:57:07Z – claude – shell_pid=95418 – lane=doing – Started implementation via workflow command
- 2026-02-03T15:58:34Z – claude – shell_pid=95418 – lane=for_review – Ready for review: Created PaginationParams and PaginatedResult[T] dataclasses with 34 unit tests. All tests pass.
- 2026-02-03T15:58:38Z – claude – shell_pid=96214 – lane=doing – Started review via workflow command
- 2026-02-03T15:58:50Z – claude – shell_pid=96214 – lane=done – Review passed: DTOs implemented correctly with comprehensive tests and documentation.
