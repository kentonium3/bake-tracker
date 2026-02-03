---
work_package_id: WP02
title: Pagination Documentation
lane: "for_review"
dependencies: []
subtasks:
- T006
phase: Phase 3 - Documentation
assignee: ''
agent: "claude"
shell_pid: "96355"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-02-03T12:45:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP02 – Pagination Documentation

## Objectives & Success Criteria

Document the pagination pattern in CLAUDE.md for future service adoption.

**Success Criteria**:
- [ ] CLAUDE.md contains "Pagination Pattern (Web Migration Ready)" section
- [ ] Optional pagination pattern explained with code example
- [ ] Desktop vs web usage examples provided
- [ ] Future adoption strategy clear (references web-prep/F003)

---

## Context & Constraints

### Related Documents
- **Spec**: `kitty-specs/093-pagination-dtos-foundation/spec.md`
- **Plan**: `kitty-specs/093-pagination-dtos-foundation/plan.md`
- **Func-Spec**: `docs/func-spec/F093_pagination_dtos_foundation.md` (contains documentation content)

### Dependencies
- **WP01**: Must be complete (DTOs must exist before documenting them)

### Key Files
- `CLAUDE.md` - UPDATE (add new section)

---

## Subtasks & Detailed Guidance

### Subtask T006 – Add pagination section to CLAUDE.md

**Purpose**: Make pagination DTOs discoverable and provide adoption guidance.

**Location**: Add after the "Session Management" section in CLAUDE.md (or another logical location near service-layer documentation).

**Content to add**:

```markdown
## Pagination Pattern (Web Migration Ready)

### DTOs Available

- `PaginationParams`: Page number and items per page
- `PaginatedResult[T]`: Generic result container with metadata

### Usage Pattern (Future Service Adoption)

When adding pagination to a service function:

**Pattern: Optional Pagination (Backward-Compatible)**

```python
from src.services.dto import PaginationParams, PaginatedResult

def list_items(
    filter: Optional[ItemFilter] = None,
    pagination: Optional[PaginationParams] = None,  # ← Optional!
    session: Optional[Session] = None
) -> PaginatedResult[Item]:
    """
    List items with optional pagination.

    Desktop usage: pagination=None returns all items (current behavior)
    Web usage: pagination=PaginationParams(...) returns one page
    """
    def _impl(sess: Session) -> PaginatedResult[Item]:
        query = sess.query(Item)

        # Apply filters...
        if filter:
            # ... filtering logic

        # Count total
        total = query.count()

        # Apply pagination (if provided)
        if pagination:
            # Web: return one page
            items = query.offset(pagination.offset()).limit(pagination.per_page).all()
            page = pagination.page
            per_page = pagination.per_page
        else:
            # Desktop: return all items (current behavior)
            items = query.all()
            page = 1
            per_page = total or 1

        return PaginatedResult(
            items=items,
            total=total,
            page=page,
            per_page=per_page
        )

    if session is not None:
        return _impl(session)
    with session_scope() as sess:
        return _impl(sess)
```

### Desktop vs Web Usage

**Desktop (current pattern unchanged):**
```python
# No pagination parameter - get all items
result = list_ingredients(filter=IngredientFilter(category="baking"))
all_items = result.items  # All ingredients
```

**Web (future FastAPI):**
```python
@app.get("/api/ingredients")
def get_ingredients(page: int = 1, per_page: int = 50):
    result = list_ingredients(
        pagination=PaginationParams(page=page, per_page=per_page)
    )
    return {
        "items": [serialize(i) for i in result.items],
        "total": result.total,
        "page": result.page,
        "pages": result.pages,
        "has_next": result.has_next
    }
```

### When to Adopt

- **New services**: Use pagination from the start
- **Existing services**: Adopt incrementally during refactoring
- **Desktop UI**: No changes needed (pagination=None)
- **Web migration**: See web-prep/F003 for comprehensive adoption plan
```

**Files**: `CLAUDE.md`

**Notes**:
- Escape the inner code blocks properly in the markdown
- Match the existing CLAUDE.md formatting style
- Place section logically (after Session Management or similar)

---

## Definition of Done Checklist

- [ ] CLAUDE.md updated with Pagination Pattern section
- [ ] Section includes DTOs Available subsection
- [ ] Section includes Usage Pattern code example
- [ ] Section includes Desktop vs Web examples
- [ ] Section includes When to Adopt guidance
- [ ] No formatting issues in markdown

---

## Review Guidance

**Reviewers should verify**:
1. Section is placed in a logical location in CLAUDE.md
2. Code examples are accurate and match actual DTO implementation
3. Desktop vs web distinction is clear
4. Future adoption path references web-prep/F003
5. No markdown formatting issues

---

## Activity Log

- 2026-02-03T12:45:00Z – system – lane=planned – Prompt generated via /spec-kitty.tasks
- 2026-02-03T15:58:54Z – claude – shell_pid=96355 – lane=doing – Started implementation via workflow command
- 2026-02-03T15:59:45Z – claude – shell_pid=96355 – lane=for_review – Ready for review: Added pagination pattern section to CLAUDE.md with usage examples.
