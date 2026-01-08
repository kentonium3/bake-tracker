---
work_package_id: WP01
title: Service Layer Functions
lane: done
history:
- timestamp: '2026-01-02T00:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
agent: claude-reviewer
assignee: claude
phase: Phase 1 - Foundational
review_status: approved without changes
reviewed_by: claude-reviewer
shell_pid: '80081'
subtasks:
- T001
- T002
- T003
- T004
---

# Work Package Prompt: WP01 - Service Layer Functions

## Review Feedback

> **Populated by `/spec-kitty.review`** - Reviewers add detailed feedback here when work needs changes.

*[This section is empty initially.]*

---

## Objectives & Success Criteria

**Goal**: Add three validation/counting convenience functions to `ingredient_hierarchy_service.py`:
1. `get_child_count(ingredient_id, session=None) -> int`
2. `get_product_count(ingredient_id, session=None) -> int`
3. `can_change_parent(ingredient_id, new_parent_id, session=None) -> dict`

**Success Criteria**:
- All three functions implemented with correct signatures
- All functions accept optional `session` parameter (per session management pattern)
- `can_change_parent()` returns structured dict with: `{allowed, reason, warnings, child_count, product_count, new_level}`
- Unit tests achieve >90% coverage for new functions
- All existing tests still pass

## Context & Constraints

**Reference Documents**:
- Constitution: `.kittify/memory/constitution.md` (Principle IV: Test-Driven Development)
- Plan: `kitty-specs/033-phase-1-ingredient/plan.md`
- Data Model: `kitty-specs/033-phase-1-ingredient/data-model.md`

**Session Management Pattern** (CRITICAL):
All functions MUST accept `session=None` and follow this pattern:
```python
def some_function(..., session=None):
    def _impl(session):
        # actual implementation
        return result

    if session is not None:
        return _impl(session)
    with session_scope() as session:
        return _impl(session)
```

**Existing Functions to Leverage**:
- `validate_hierarchy(ingredient_id, proposed_parent_id, session)` - Validates parent change, raises exceptions
- `get_children(ingredient_id, session)` - Returns child ingredients
- `get_descendants(ingredient_id, session)` - Returns all descendants

## Subtasks & Detailed Guidance

### Subtask T001 - Implement `get_child_count()`

**Purpose**: Return count of direct child ingredients for a given ingredient.

**Steps**:
1. Add function after existing `get_children()` function in `src/services/ingredient_hierarchy_service.py`
2. Query: `SELECT COUNT(*) FROM ingredients WHERE parent_ingredient_id = :id`
3. Return integer count

**Files**: `src/services/ingredient_hierarchy_service.py`

**Parallel?**: Yes - can implement alongside T002

**Implementation**:
```python
def get_child_count(ingredient_id: int, session=None) -> int:
    """
    Count direct child ingredients.

    Args:
        ingredient_id: ID of ingredient to count children for
        session: Optional SQLAlchemy session

    Returns:
        Number of direct child ingredients
    """
    def _impl(session):
        return session.query(Ingredient).filter(
            Ingredient.parent_ingredient_id == ingredient_id
        ).count()

    if session is not None:
        return _impl(session)
    with session_scope() as session:
        return _impl(session)
```

### Subtask T002 - Implement `get_product_count()`

**Purpose**: Return count of products linked to a given ingredient.

**Steps**:
1. Add function in `src/services/ingredient_hierarchy_service.py`
2. Import `Product` model if not already imported
3. Query: `SELECT COUNT(*) FROM products WHERE ingredient_id = :id`
4. Return integer count

**Files**: `src/services/ingredient_hierarchy_service.py`

**Parallel?**: Yes - can implement alongside T001

**Implementation**:
```python
from src.models.product import Product  # Add to imports if needed

def get_product_count(ingredient_id: int, session=None) -> int:
    """
    Count products linked to this ingredient.

    Args:
        ingredient_id: ID of ingredient to count products for
        session: Optional SQLAlchemy session

    Returns:
        Number of products linked to this ingredient
    """
    def _impl(session):
        return session.query(Product).filter(
            Product.ingredient_id == ingredient_id
        ).count()

    if session is not None:
        return _impl(session)
    with session_scope() as session:
        return _impl(session)
```

### Subtask T003 - Implement `can_change_parent()`

**Purpose**: Check if a parent change is allowed and gather impact information for UI display.

**Steps**:
1. Add function after `validate_hierarchy()` in `src/services/ingredient_hierarchy_service.py`
2. Wrap `validate_hierarchy()` call in try/except
3. On exception → return `{allowed: False, reason: exception_message, ...}`
4. On success → gather counts and compute warnings
5. Return structured dict

**Files**: `src/services/ingredient_hierarchy_service.py`

**Parallel?**: No - depends on T001 and T002 for count functions

**Implementation**:
```python
def can_change_parent(
    ingredient_id: int,
    new_parent_id: Optional[int],
    session=None
) -> Dict[str, Any]:
    """
    Check if parent change is allowed and gather impact information.

    Args:
        ingredient_id: ID of ingredient to change
        new_parent_id: Proposed new parent ID (None = make root)
        session: Optional SQLAlchemy session

    Returns:
        {
            "allowed": bool,
            "reason": str,  # Empty if allowed, error message if not
            "warnings": List[str],  # Informational warnings
            "child_count": int,
            "product_count": int,
            "new_level": int  # 0, 1, or 2
        }
    """
    def _impl(session):
        result = {
            "allowed": True,
            "reason": "",
            "warnings": [],
            "child_count": 0,
            "product_count": 0,
            "new_level": 0
        }

        # Get counts
        result["child_count"] = get_child_count(ingredient_id, session=session)
        result["product_count"] = get_product_count(ingredient_id, session=session)

        # Compute new level
        if new_parent_id is None:
            result["new_level"] = 0
        else:
            parent = session.query(Ingredient).filter(
                Ingredient.id == new_parent_id
            ).first()
            if parent:
                result["new_level"] = parent.hierarchy_level + 1

        # Try validation
        try:
            validate_hierarchy(ingredient_id, new_parent_id, session=session)
        except IngredientNotFound as e:
            result["allowed"] = False
            result["reason"] = str(e)
            return result
        except CircularReferenceError as e:
            result["allowed"] = False
            result["reason"] = f"Cannot change: would create circular reference"
            return result
        except MaxDepthExceededError as e:
            result["allowed"] = False
            result["reason"] = f"Cannot change: would exceed maximum hierarchy depth (3 levels)"
            return result

        # Add informational warnings (non-blocking)
        if result["product_count"] > 0:
            result["warnings"].append(
                f"This ingredient has {result['product_count']} linked products"
            )
        if result["child_count"] > 0:
            result["warnings"].append(
                f"This ingredient has {result['child_count']} child ingredients"
            )

        return result

    if session is not None:
        return _impl(session)
    with session_scope() as session:
        return _impl(session)
```

**Notes**:
- Make sure `Dict`, `Any`, `List` are imported from `typing`
- Exception types (`IngredientNotFound`, `CircularReferenceError`, `MaxDepthExceededError`) should already be defined in the file

### Subtask T004 - Add Unit Tests

**Purpose**: Achieve >90% test coverage for the three new functions.

**Steps**:
1. Open `src/tests/services/test_ingredient_hierarchy_service.py`
2. Add test class `TestGetChildCount` with tests for:
   - Ingredient with no children returns 0
   - Ingredient with children returns correct count
   - Non-existent ingredient (graceful handling)
3. Add test class `TestGetProductCount` with tests for:
   - Ingredient with no products returns 0
   - Ingredient with products returns correct count
4. Add test class `TestCanChangeParent` with tests for:
   - Valid parent change returns allowed=True
   - Invalid parent (would create cycle) returns allowed=False with reason
   - Invalid parent (would exceed depth) returns allowed=False with reason
   - Ingredient with products gets warning in warnings list
   - Ingredient with children gets warning in warnings list
   - new_level computed correctly for L0/L1/L2

**Files**: `src/tests/services/test_ingredient_hierarchy_service.py`

**Test Fixtures Needed**:
- L0 ingredient (root, no parent)
- L1 ingredient (child of L0)
- L2 ingredient (child of L1)
- Ingredient with linked products
- Ingredient with child ingredients

**Example Test Structure**:
```python
class TestGetChildCount:
    def test_ingredient_with_no_children_returns_zero(self, session, l2_ingredient):
        count = get_child_count(l2_ingredient.id, session=session)
        assert count == 0

    def test_ingredient_with_children_returns_correct_count(self, session, l0_with_children):
        count = get_child_count(l0_with_children.id, session=session)
        assert count == 3  # Assuming 3 children in fixture

class TestGetProductCount:
    def test_ingredient_with_no_products_returns_zero(self, session, l2_no_products):
        count = get_product_count(l2_no_products.id, session=session)
        assert count == 0

    def test_ingredient_with_products_returns_correct_count(self, session, l2_with_products):
        count = get_product_count(l2_with_products.id, session=session)
        assert count == 5  # Assuming 5 products in fixture

class TestCanChangeParent:
    def test_valid_change_returns_allowed(self, session, l2_ingredient, l1_other):
        result = can_change_parent(l2_ingredient.id, l1_other.id, session=session)
        assert result["allowed"] is True
        assert result["reason"] == ""

    def test_circular_reference_blocked(self, session, l0_ingredient, l2_child):
        # Try to make L0 a child of its own descendant
        result = can_change_parent(l0_ingredient.id, l2_child.id, session=session)
        assert result["allowed"] is False
        assert "circular" in result["reason"].lower()

    def test_depth_exceeded_blocked(self, session, l2_ingredient, l1_ingredient):
        # Try to make L2 a child of another L2 (would create L3)
        # ... test setup may vary
        pass

    def test_product_warning_included(self, session, l2_with_products, l1_ingredient):
        result = can_change_parent(l2_with_products.id, l1_ingredient.id, session=session)
        assert any("product" in w.lower() for w in result["warnings"])
```

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Session management pattern violation | Follow existing function patterns in file |
| Missing exception type imports | Check existing imports at top of file |
| Test fixtures missing | Create minimal fixtures or use existing ones |
| Product model not imported | Add import if needed |

## Definition of Done Checklist

- [ ] `get_child_count()` implemented with session parameter
- [ ] `get_product_count()` implemented with session parameter
- [ ] `can_change_parent()` implemented with full return dict
- [ ] All typing imports added (`Dict`, `Any`, `List` if needed)
- [ ] Unit tests added for all three functions
- [ ] Tests cover happy path, edge cases, and error conditions
- [ ] All existing tests still pass
- [ ] Code formatted with black
- [ ] `tasks.md` updated with status change

## Review Guidance

**Key Acceptance Checkpoints**:
1. Verify session parameter handling follows established pattern
2. Check that `can_change_parent()` catches all exception types from `validate_hierarchy()`
3. Confirm warnings are informational only (per planning decision)
4. Verify test coverage >90% for new functions
5. Run full test suite to confirm no regressions

## Activity Log

- 2026-01-02T00:00:00Z - system - lane=planned - Prompt created.
- 2026-01-02T05:34:05Z – claude – shell_pid=66160 – lane=doing – Started implementation
- 2026-01-02T05:44:19Z – claude – shell_pid=66160 – lane=for_review – Moved to for_review
- 2026-01-02T09:04:48Z – claude-reviewer – shell_pid=80081 – lane=done – Code review approved: All 3 service functions implemented correctly with session management pattern. 16 tests added, all 74 hierarchy service tests pass.
