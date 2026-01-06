---
work_package_id: "WP03"
subtasks:
  - "T013"
  - "T014"
  - "T015"
  - "T016"
  - "T017"
  - "T018"
title: "Shopping List Service"
phase: "Phase 2 - Services"
lane: "done"
assignee: "claude"
agent: "claude-reviewer"
shell_pid: "67066"
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-06T03:09:20Z"
    lane: "planned"
    agent: "claude"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP03 - Shopping List Service

## Review Feedback

> **Populated by `/spec-kitty.review`** - Reviewers add detailed feedback here when work needs changes.

*[This section is empty initially.]*

---

## Objectives & Success Criteria

- Generate aggregated shopping list with Need/Have/Buy columns
- Calculate inventory gap: max(0, needed - available)
- Track shopping completion status
- Leverage existing event_service.get_shopping_list()

**Success Metrics (from spec):**
- SC-004: Users can identify all items to purchase in a single view
- SC-008: Shopping list correctly identifies inventory gaps - Buy = max(0, Need - Have) with 100% accuracy

---

## Context & Constraints

### Reference Documents
- **Contract**: `kitty-specs/039-planning-workspace/contracts/planning_service.py` - ShoppingListItem DTO
- **Research**: `kitty-specs/039-planning-workspace/research.md` - Existing event_service capabilities
- **Quickstart**: `kitty-specs/039-planning-workspace/quickstart.md` - Session management pattern

### Key Constraints
- MUST wrap existing `event_service.get_shopping_list(event_id)` - don't reimplement
- Session management: all functions accept optional `session` parameter
- Parallelizable with WP02, WP04, WP05

### Architectural Notes
- Located in `src/services/planning/shopping_list.py`
- Extend event_service with DTO formatting
- Follow session management pattern from CLAUDE.md

---

## Subtasks & Detailed Guidance

### Subtask T013 - Create shopping_list.py

- **Purpose**: Initialize shopping list module
- **Steps**:
  1. Create `src/services/planning/shopping_list.py`
  2. Add imports:
     ```python
     from dataclasses import dataclass
     from decimal import Decimal
     from typing import List, Optional
     from sqlalchemy.orm import Session
     from src.services.database import session_scope
     from src.services import event_service
     ```
  3. Define `ShoppingListItem` dataclass (per contract):
     ```python
     @dataclass
     class ShoppingListItem:
         ingredient_id: int
         ingredient_slug: str
         ingredient_name: str
         needed: Decimal
         in_stock: Decimal
         to_buy: Decimal
         unit: str
         is_sufficient: bool  # True if in_stock >= needed
     ```
- **Files**: `src/services/planning/shopping_list.py`
- **Parallel?**: Yes

### Subtask T014 - Implement get_shopping_list wrapper

- **Purpose**: Wrap event_service with DTO formatting (FR-015, FR-019)
- **Steps**:
  1. Add function:
     ```python
     def get_shopping_list(
         event_id: int,
         *,
         include_sufficient: bool = True,
         session: Optional[Session] = None,
     ) -> List[ShoppingListItem]:
         """Get shopping list with inventory comparison.

         Args:
             event_id: Event to get list for
             include_sufficient: If True, include items with sufficient stock
             session: Optional database session

         Returns:
             List of ShoppingListItem
         """
         if session is not None:
             return _get_shopping_list_impl(event_id, include_sufficient, session)
         with session_scope() as session:
             return _get_shopping_list_impl(event_id, include_sufficient, session)
     ```
  2. Implement `_get_shopping_list_impl()`:
     - Call `event_service.get_shopping_list(event_id, session=session)`
     - Transform results to ShoppingListItem DTOs
     - Filter out sufficient items if `include_sufficient=False`
- **Files**: `src/services/planning/shopping_list.py`
- **Parallel?**: Yes
- **Notes**: Pass session to event_service to maintain transactional integrity

### Subtask T015 - Implement ingredient aggregation

- **Purpose**: Aggregate ingredients across all recipes in plan (FR-016)
- **Steps**:
  1. Add function:
     ```python
     def aggregate_ingredients(
         recipe_batches: List[Dict],
         session: Session
     ) -> Dict[str, Decimal]:
         """Aggregate ingredient quantities across recipes.

         Args:
             recipe_batches: List with recipe_id and batches count
             session: Database session

         Returns:
             Dict mapping ingredient_slug -> total quantity needed
         """
     ```
  2. For each recipe in recipe_batches:
     - Call `recipe_service.get_aggregated_ingredients(recipe_id, multiplier=batches, session=session)`
     - Sum quantities for same ingredient_slug
  3. Handle unit conversions if needed (same unit assumption for now)
- **Files**: `src/services/planning/shopping_list.py`
- **Parallel?**: Yes
- **Notes**: Leverage existing recipe_service

### Subtask T016 - Implement gap calculation

- **Purpose**: Calculate purchase quantities (FR-018)
- **Steps**:
  1. Add function:
     ```python
     def calculate_purchase_gap(
         needed: Decimal,
         in_stock: Decimal
     ) -> Decimal:
         """Calculate how much to buy.

         Returns:
             max(0, needed - in_stock)
         """
         return max(Decimal(0), needed - in_stock)
     ```
  2. Ensure this is used in ShoppingListItem creation
  3. Set `is_sufficient = (in_stock >= needed)`
- **Files**: `src/services/planning/shopping_list.py`
- **Parallel?**: Yes
- **Notes**: Use Decimal for accuracy; never return negative

### Subtask T017 - Implement mark_shopping_complete

- **Purpose**: Track shopping completion status (FR-020)
- **Steps**:
  1. Add function:
     ```python
     def mark_shopping_complete(
         event_id: int,
         *,
         session: Optional[Session] = None,
     ) -> None:
         """Mark shopping as complete for the event.

         Updates ProductionPlanSnapshot.shopping_complete = True
         """
         if session is not None:
             return _mark_shopping_complete_impl(event_id, session)
         with session_scope() as session:
             return _mark_shopping_complete_impl(event_id, session)
     ```
  2. Implement `_mark_shopping_complete_impl()`:
     - Query latest ProductionPlanSnapshot for event
     - Set `shopping_complete = True`
     - Set `shopping_completed_at = utc_now()`
     - Commit
- **Files**: `src/services/planning/shopping_list.py`
- **Parallel?**: Yes
- **Notes**: Requires ProductionPlanSnapshot from WP01

### Subtask T018 - Write unit tests

- **Purpose**: Verify shopping list functions
- **Steps**:
  1. Create `src/tests/services/planning/test_shopping_list.py`
  2. Test cases for `get_shopping_list()`:
     - Event with ingredients needed
     - Filter sufficient items
     - Empty shopping list
  3. Test cases for `calculate_purchase_gap()`:
     - Need > Have: returns difference
     - Need == Have: returns 0
     - Need < Have: returns 0 (sufficient)
  4. Test cases for `mark_shopping_complete()`:
     - Sets shopping_complete flag
     - Sets shopping_completed_at timestamp
- **Files**: `src/tests/services/planning/test_shopping_list.py`
- **Parallel?**: Yes

---

## Test Strategy

**Unit Tests Required:**
- `src/tests/services/planning/test_shopping_list.py`

**Run with:**
```bash
pytest src/tests/services/planning/test_shopping_list.py -v
```

**Critical Test Cases:**
- Gap calculation never returns negative
- Sufficient flag is accurate
- Session is passed through to nested calls

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Session detachment | Always pass session to nested service calls |
| Unit conversion errors | Assume same units for now; document limitation |
| Decimal precision loss | Use Decimal throughout; avoid float |

---

## Definition of Done Checklist

- [ ] shopping_list.py created with all functions
- [ ] ShoppingListItem DTO matches contract
- [ ] get_shopping_list wraps event_service correctly
- [ ] Gap calculation: max(0, needed - in_stock)
- [ ] mark_shopping_complete updates snapshot
- [ ] Session parameter pattern followed
- [ ] All unit tests pass
- [ ] >70% test coverage on module
- [ ] `tasks.md` updated with status change

---

## Review Guidance

- Verify session is passed to all nested calls
- Check gap calculation never returns negative
- Validate DTO structure matches contract
- Ensure Decimal is used for quantities

---

## Activity Log

- 2026-01-06T03:09:20Z - claude - lane=planned - Prompt created.
- 2026-01-06T13:04:46Z – system – shell_pid= – lane=doing – Moved to doing
- 2026-01-06T13:10:38Z – system – shell_pid= – lane=for_review – Moved to for_review
- 2026-01-06T13:58:06Z – claude-reviewer – shell_pid=67066 – lane=done – Code review approved: Shopping list with Decimal precision, gap calculation never negative, completion tracking - 25 tests passing
