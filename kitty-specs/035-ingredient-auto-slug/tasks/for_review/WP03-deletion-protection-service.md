---
work_package_id: "WP03"
subtasks:
  - "T011"
  - "T012"
  - "T013"
  - "T014"
  - "T015"
title: "Deletion Protection Service"
phase: "Phase 2 - Core Implementation"
lane: "for_review"
assignee: ""
agent: "claude"
shell_pid: "15513"
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-02T12:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP03 - Deletion Protection Service

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

**Objective**: Implement comprehensive deletion protection service that:
1. Blocks deletion when Products or Recipes reference the ingredient
2. Denormalizes historical snapshot data before deletion
3. Provides detailed error messages with counts

**Success Criteria**:
- `can_delete_ingredient()` correctly checks all blocking conditions
- `_denormalize_snapshot_ingredients()` copies hierarchy names before nullifying FK
- `delete_ingredient_safe()` orchestrates the safe deletion flow
- All operations use atomic transactions

## Context & Constraints

**Related Documents**:
- Spec: `kitty-specs/035-ingredient-auto-slug/spec.md` (FR-005 to FR-014)
- Plan: `kitty-specs/035-ingredient-auto-slug/plan.md` (Phase 3)
- Data Model: `kitty-specs/035-ingredient-auto-slug/data-model.md`
- Constitution: `.kittify/memory/constitution.md` (Session Management section)

**Key Constraints**:
- Follow session management pattern: functions accept optional `session` parameter
- Use `session_scope()` when no session provided
- Leverage existing F033 services: `get_child_count()`, `get_ancestors()`
- Error messages must include counts (FR-007, FR-008, FR-009)

**Dependencies**:
- WP01 must be complete (SnapshotIngredient has new fields)
- WP02 must be complete (cascade delete verified)

## Subtasks & Detailed Guidance

### Subtask T011 - Implement can_delete_ingredient()

**Purpose**: Pre-check whether an ingredient can be safely deleted.

**Steps**:
1. Add function to `src/services/ingredient_service.py`:

```python
def can_delete_ingredient(ingredient_id: int, session=None) -> Tuple[bool, str, Dict[str, int]]:
    """
    Check if ingredient can be deleted.

    Args:
        ingredient_id: ID of ingredient to check
        session: Optional SQLAlchemy session

    Returns:
        Tuple of (can_delete, reason, details)
        - can_delete: True if deletion is allowed
        - reason: Error message if blocked, empty string if allowed
        - details: Dict with counts {products: N, recipes: N, children: N, snapshots: N}
    """
    def _check(session):
        from ..models import Product, RecipeIngredient, Ingredient
        from .ingredient_hierarchy_service import get_child_count

        details = {
            "products": 0,
            "recipes": 0,
            "children": 0,
            "snapshots": 0
        }
        reasons = []

        # Check Product references (blocks deletion)
        product_count = session.query(Product).filter(
            Product.ingredient_id == ingredient_id
        ).count()
        details["products"] = product_count
        if product_count > 0:
            reasons.append(f"{product_count} products reference this ingredient")

        # Check RecipeIngredient references (blocks deletion)
        recipe_count = session.query(RecipeIngredient).filter(
            RecipeIngredient.ingredient_id == ingredient_id
        ).count()
        details["recipes"] = recipe_count
        if recipe_count > 0:
            reasons.append(f"{recipe_count} recipes use this ingredient")

        # Check child ingredients (blocks deletion)
        child_count = get_child_count(ingredient_id, session=session)
        details["children"] = child_count
        if child_count > 0:
            reasons.append(f"{child_count} child ingredients exist")

        # Check SnapshotIngredient references (does NOT block, just count)
        from ..models.inventory_snapshot import SnapshotIngredient
        snapshot_count = session.query(SnapshotIngredient).filter(
            SnapshotIngredient.ingredient_id == ingredient_id
        ).count()
        details["snapshots"] = snapshot_count

        if reasons:
            reason = "Cannot delete: " + "; ".join(reasons) + ". Reassign or remove references first."
            return False, reason, details

        return True, "", details

    if session is not None:
        return _check(session)
    with session_scope() as session:
        return _check(session)
```

**Files**: `src/services/ingredient_service.py`

### Subtask T012 - Implement _denormalize_snapshot_ingredients()

**Purpose**: Copy ingredient hierarchy names to snapshot records before deletion.

**Steps**:
1. Add helper function:

```python
def _denormalize_snapshot_ingredients(ingredient_id: int, session) -> int:
    """
    Copy ingredient names to snapshot records before deletion.

    This preserves historical data when the ingredient is deleted.
    After denormalization, the ingredient_id FK is set to NULL.

    Args:
        ingredient_id: ID of ingredient being deleted
        session: SQLAlchemy session (required, not optional)

    Returns:
        Count of records denormalized
    """
    from ..models import Ingredient
    from ..models.inventory_snapshot import SnapshotIngredient
    from .ingredient_hierarchy_service import get_ancestors

    # Get the ingredient being deleted
    ingredient = session.query(Ingredient).filter(
        Ingredient.id == ingredient_id
    ).first()

    if not ingredient:
        return 0

    # Get hierarchy ancestors for parent names
    ancestors = get_ancestors(ingredient_id, session=session)

    # Determine parent names from ancestors
    l1_name = None
    l0_name = None
    if len(ancestors) >= 1:
        l1_name = ancestors[0].display_name  # Immediate parent
    if len(ancestors) >= 2:
        l0_name = ancestors[1].display_name  # Grandparent (root)

    # Find all snapshot records referencing this ingredient
    snapshots = session.query(SnapshotIngredient).filter(
        SnapshotIngredient.ingredient_id == ingredient_id
    ).all()

    count = 0
    for snapshot in snapshots:
        # Denormalize names
        snapshot.ingredient_name_snapshot = ingredient.display_name
        snapshot.parent_l1_name_snapshot = l1_name
        snapshot.parent_l0_name_snapshot = l0_name
        # Nullify FK (ingredient will be deleted)
        snapshot.ingredient_id = None
        count += 1

    return count
```

**Files**: `src/services/ingredient_service.py`

### Subtask T013 - Implement delete_ingredient_safe()

**Purpose**: Orchestrate safe deletion with all protections.

**Steps**:
1. Add main deletion function:

```python
def delete_ingredient_safe(ingredient_id: int, session=None) -> bool:
    """
    Safely delete an ingredient with full protection.

    This function:
    1. Checks if deletion is allowed (no Product/Recipe/child references)
    2. Denormalizes snapshot records to preserve historical data
    3. Deletes the ingredient (cascades Alias/Crosswalk via DB)

    Args:
        ingredient_id: ID of ingredient to delete
        session: Optional SQLAlchemy session

    Returns:
        True if deleted successfully

    Raises:
        IngredientNotFound: If ingredient doesn't exist
        IngredientInUse: If ingredient has blocking references
        DatabaseError: If database operation fails
    """
    def _delete(session):
        from ..models import Ingredient

        # Verify ingredient exists
        ingredient = session.query(Ingredient).filter(
            Ingredient.id == ingredient_id
        ).first()
        if not ingredient:
            raise IngredientNotFound(ingredient_id)

        # Check if deletion is allowed
        can_delete, reason, details = can_delete_ingredient(ingredient_id, session=session)
        if not can_delete:
            raise IngredientInUse(ingredient_id, details)

        # Denormalize snapshot records
        denorm_count = _denormalize_snapshot_ingredients(ingredient_id, session)
        logger.info(f"Denormalized {denorm_count} snapshot records for ingredient {ingredient_id}")

        # Delete ingredient (Alias/Crosswalk cascade via DB)
        session.delete(ingredient)

        return True

    try:
        if session is not None:
            return _delete(session)
        with session_scope() as session:
            return _delete(session)
    except (IngredientNotFound, IngredientInUse):
        raise
    except Exception as e:
        raise DatabaseError(f"Failed to delete ingredient {ingredient_id}", e)
```

**Files**: `src/services/ingredient_service.py`

### Subtask T014 - Add Required Imports

**Purpose**: Ensure all necessary model imports are present.

**Steps**:
1. Add to imports section at top of file:
```python
from ..models import Product, RecipeIngredient, Ingredient
from ..models.inventory_snapshot import SnapshotIngredient
```

**Note**: Some imports may already exist; don't duplicate.

**Files**: `src/services/ingredient_service.py`

### Subtask T015 - Follow Session Management Pattern

**Purpose**: Ensure all functions follow the session management pattern per CLAUDE.md.

**Verification Checklist**:
- [ ] `can_delete_ingredient()` accepts optional `session` parameter
- [ ] `delete_ingredient_safe()` accepts optional `session` parameter
- [ ] `_denormalize_snapshot_ingredients()` requires session (internal helper)
- [ ] When calling other services, pass session if provided
- [ ] Use `session_scope()` only when no session provided

## Test Strategy

Tests are in WP06. Key scenarios to verify:
- Deletion blocked when products exist
- Deletion blocked when recipes exist
- Deletion blocked when children exist
- Snapshots denormalized correctly
- Cascade delete works for Alias/Crosswalk

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Transaction failure mid-delete | Single atomic transaction, rollback on any error |
| Session detachment | Follow session management pattern strictly |
| Missing ancestor data | Handle None gracefully in denormalization |
| IngredientInUse needs details | Exception modified to accept details dict |

**Note**: May need to update `IngredientInUse` exception class to accept details dict.

## Definition of Done Checklist

- [ ] T011: `can_delete_ingredient()` implemented with all checks
- [ ] T012: `_denormalize_snapshot_ingredients()` implemented
- [ ] T013: `delete_ingredient_safe()` implemented
- [ ] T014: All required imports added
- [ ] T015: Session management pattern verified
- [ ] All functions have proper docstrings
- [ ] Error messages include counts per FR-007, FR-008, FR-009

## Review Guidance

- Verify all blocking conditions are checked
- Verify session management pattern is followed
- Verify denormalization captures L0, L1, L2 names correctly
- Verify atomic transaction covers entire operation

## Activity Log

- 2026-01-02T12:00:00Z - system - lane=planned - Prompt created via /spec-kitty.tasks
- 2026-01-02T19:37:49Z – claude – shell_pid=15513 – lane=doing – Started Wave 2 implementation
- 2026-01-02T22:45:00Z – claude – shell_pid=15513 – lane=doing – Completed implementation:
  - T011: can_delete_ingredient() - checks products, recipes, children (blocking) and snapshots (info only)
  - T012: _denormalize_snapshot_ingredients() - copies L0/L1/L2 names before nullifying FK
  - T013: delete_ingredient_safe() - orchestrates validation, denormalization, deletion in atomic transaction
  - T014: Imports added inside functions to avoid circular dependencies
  - T015: Session management pattern followed (optional session parameter)
  - Also updated IngredientInUse exception to expose details attribute
- 2026-01-02T19:41:07Z – claude – shell_pid=15513 – lane=for_review – Ready for review - deletion protection service complete (T011-T015)
