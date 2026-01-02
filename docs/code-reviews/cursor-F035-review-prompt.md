# Cursor Code Review Prompt - Feature 035: Ingredient Auto-Slug & Deletion Protection

## Role

You are a senior software engineer performing an independent code review of Feature 035 (ingredient-auto-slug). This feature implements ingredient deletion protection with historical data preservation, slug auto-generation, and UI integration for safe deletion with detailed error messages.

## Feature Summary

**Core Changes:**
1. Schema & Denormalization Fields: SnapshotIngredient FK changed to SET NULL/nullable, 3 new snapshot columns (WP01)
2. Cascade Delete Verification: Verified IngredientAlias/Crosswalk have CASCADE delete (WP02)
3. Deletion Protection Service: `can_delete_ingredient()`, `delete_ingredient_safe()`, `_denormalize_snapshot_ingredients()` (WP03)
4. Slug Field Mapping Fix: Field normalization "name" -> "display_name" in `create_ingredient()` (WP04)
5. UI Delete Handler Integration: Safe deletion with detailed error messages showing counts (WP05)
6. Deletion & Slug Tests: 9 new tests covering all deletion and slug scenarios (WP06)

**Problem Being Solved:**
- Gap Analysis Phase 3: Ingredient deletion protection needed before catalog entities (Products, Recipes, Children) can be safely managed
- Historical inventory snapshots must preserve ingredient names even after deletion
- UI must show clear error messages with counts when deletion is blocked
- Field name mismatch between UI ("name") and service ("display_name") needed normalization

**Solution:**
- Denormalization-then-nullify pattern: Copy ingredient hierarchy names to snapshot before deletion
- Blocking pattern: Products, Recipes, and Child ingredients block deletion
- Cascade pattern: IngredientAlias and IngredientCrosswalk auto-delete via DB CASCADE
- UI shows "Cannot delete this ingredient. It is referenced by 3 products, 2 recipes and 1 child ingredient."

## Files to Review

### Schema Changes (WP01)

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/035-ingredient-auto-slug/src/models/inventory_snapshot.py`
  - **WP01**: `ingredient_id` FK changed from `ondelete="RESTRICT"` to `ondelete="SET NULL"`, `nullable=True` (around line 95-97)
  - **WP01**: Added `ingredient_name_snapshot` column (String(200), nullable) (around line 100)
  - **WP01**: Added `parent_l1_name_snapshot` column (String(200), nullable) (around line 101)
  - **WP01**: Added `parent_l0_name_snapshot` column (String(200), nullable) (around line 102)

### Cascade Delete Configuration (WP02 - Verification Only)

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/035-ingredient-auto-slug/src/models/ingredient_alias.py`
  - **WP02**: Verify `ingredient_id` FK has `ondelete="CASCADE"` (line 32)
  - **WP02**: Verify relationship has `passive_deletes="all"` or similar (line 35-40)

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/035-ingredient-auto-slug/src/models/ingredient_crosswalk.py`
  - **WP02**: Verify `ingredient_id` FK has `ondelete="CASCADE"` (line 35)
  - **WP02**: Verify relationship has `passive_deletes="all"` or similar (line 38-43)

### Deletion Protection Service (WP03)

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/035-ingredient-auto-slug/src/services/ingredient_service.py`
  - **WP03**: `can_delete_ingredient(ingredient_id, session=None)` function added (after line 517)
  - **WP03**: `_denormalize_snapshot_ingredients(ingredient_id, session)` helper added
  - **WP03**: `delete_ingredient_safe(ingredient_id, session=None)` function added
  - **WP04**: Field normalization in `create_ingredient()` - "name" -> "display_name" (around line 171-174)

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/035-ingredient-auto-slug/src/services/exceptions.py`
  - **WP03**: `IngredientInUse` exception updated to expose `details` attribute (line 57-94)

### UI Integration (WP05)

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/035-ingredient-auto-slug/src/ui/ingredients_tab.py`
  - **WP05**: Import `delete_ingredient_safe` added (top of file)
  - **WP05**: Import `IngredientNotFound` exception added
  - **WP05**: `_delete_ingredient()` in IngredientsTab updated to use `delete_ingredient_safe(ingredient_id)`
  - **WP05**: `_show_deletion_blocked_message(details)` helper added to IngredientsTab
  - **WP05**: `_delete()` in IngredientFormDialog updated to use `delete_ingredient_safe(ingredient_id)`
  - **WP05**: `_show_dialog_deletion_blocked_message(details)` helper added to IngredientFormDialog

### Tests (WP06)

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/035-ingredient-auto-slug/src/tests/services/test_ingredient_service.py`
  - **WP06**: `TestDeletionProtectionAndSlug` test class added with 9 tests (T024-T032)

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/035-ingredient-auto-slug/src/tests/conftest.py`
  - **WP06**: SQLite `PRAGMA foreign_keys=ON` added to enable CASCADE in tests

### Specification Documents

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/035-ingredient-auto-slug/kitty-specs/035-ingredient-auto-slug/spec.md`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/035-ingredient-auto-slug/kitty-specs/035-ingredient-auto-slug/plan.md`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/035-ingredient-auto-slug/kitty-specs/035-ingredient-auto-slug/tasks.md`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/035-ingredient-auto-slug/kitty-specs/035-ingredient-auto-slug/research.md`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/035-ingredient-auto-slug/kitty-specs/035-ingredient-auto-slug/data-model.md`

### Work Package Prompts (for context)

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/035-ingredient-auto-slug/kitty-specs/035-ingredient-auto-slug/tasks/for_review/WP01-schema-denormalization-fields.md`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/035-ingredient-auto-slug/kitty-specs/035-ingredient-auto-slug/tasks/for_review/WP02-cascade-delete-config.md`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/035-ingredient-auto-slug/kitty-specs/035-ingredient-auto-slug/tasks/for_review/WP03-deletion-protection-service.md`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/035-ingredient-auto-slug/kitty-specs/035-ingredient-auto-slug/tasks/for_review/WP04-slug-field-mapping.md`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/035-ingredient-auto-slug/kitty-specs/035-ingredient-auto-slug/tasks/for_review/WP05-ui-delete-integration.md`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/035-ingredient-auto-slug/kitty-specs/035-ingredient-auto-slug/tasks/for_review/WP06-deletion-slug-tests.md`

## Review Checklist

### 1. Schema Changes (WP01)

- [ ] `SnapshotIngredient.ingredient_id` FK has `ondelete="SET NULL"`
- [ ] `SnapshotIngredient.ingredient_id` column has `nullable=True`
- [ ] `ingredient_name_snapshot` column added (String(200), nullable)
- [ ] `parent_l1_name_snapshot` column added (String(200), nullable)
- [ ] `parent_l0_name_snapshot` column added (String(200), nullable)
- [ ] New columns are included in `to_dict()` output (via BaseModel introspection or explicit)

### 2. Cascade Delete Configuration (WP02)

- [ ] `IngredientAlias.ingredient_id` FK has `ondelete="CASCADE"`
- [ ] `IngredientCrosswalk.ingredient_id` FK has `ondelete="CASCADE"`
- [ ] Relationships have `passive_deletes` to prevent ORM interference with DB CASCADE

### 3. Deletion Protection Service (WP03)

- [ ] `can_delete_ingredient(ingredient_id, session=None)` exists
- [ ] Returns `Tuple[bool, str, Dict[str, int]]` (can_delete, reason, details)
- [ ] Checks Product references (blocks deletion)
- [ ] Checks RecipeIngredient references (blocks deletion)
- [ ] Checks child ingredients via `get_child_count()` (blocks deletion)
- [ ] Checks SnapshotIngredient references (does NOT block, just counts)
- [ ] `_denormalize_snapshot_ingredients(ingredient_id, session)` exists
- [ ] Copies `ingredient.display_name` to `ingredient_name_snapshot`
- [ ] Copies parent L1 name to `parent_l1_name_snapshot`
- [ ] Copies parent L0 name to `parent_l0_name_snapshot`
- [ ] Sets `ingredient_id` to None after copying names
- [ ] `delete_ingredient_safe(ingredient_id, session=None)` exists
- [ ] Raises `IngredientNotFound` if ingredient doesn't exist
- [ ] Raises `IngredientInUse` with details dict if blocked
- [ ] Calls `_denormalize_snapshot_ingredients()` before deletion
- [ ] Deletes ingredient (Alias/Crosswalk cascade via DB)
- [ ] All functions follow session management pattern (accept optional session)

### 4. Exception Updates (WP03)

- [ ] `IngredientInUse` accepts dict for `deps` parameter
- [ ] `IngredientInUse` exposes `details` attribute (alias for `deps`)
- [ ] Message includes counts for products, recipes, children

### 5. Field Normalization (WP04)

- [ ] `create_ingredient()` checks for "name" field in input
- [ ] Maps "name" to "display_name" when display_name not present
- [ ] Preserves "display_name" if both are provided (display_name takes precedence)

### 6. UI Integration (WP05)

- [ ] `delete_ingredient_safe` imported in ingredients_tab.py
- [ ] `IngredientNotFound` exception imported
- [ ] `IngredientsTab._delete_ingredient()` uses `delete_ingredient_safe(ingredient_id)`
- [ ] `IngredientsTab._delete_ingredient()` catches `IngredientInUse` and shows detailed message
- [ ] `IngredientsTab._show_deletion_blocked_message(details)` exists
- [ ] Message formats counts correctly with proper pluralization
- [ ] Message uses "and" before last item (e.g., "3 products, 2 recipes and 1 child ingredient")
- [ ] `IngredientFormDialog._delete()` uses `delete_ingredient_safe(ingredient_id)`
- [ ] `IngredientFormDialog._show_dialog_deletion_blocked_message(details)` exists

### 7. Tests (WP06)

- [ ] `TestDeletionProtectionAndSlug` class exists
- [ ] `test_delete_blocked_by_products` - verifies product references block deletion
- [ ] `test_delete_blocked_by_recipes` - verifies recipe references block deletion
- [ ] `test_delete_blocked_by_children` - verifies child ingredients block deletion
- [ ] `test_delete_with_snapshots_denormalizes` - verifies snapshot preservation
- [ ] `test_delete_cascades_aliases` - verifies alias cascade delete
- [ ] `test_delete_cascades_crosswalks` - verifies crosswalk cascade delete
- [ ] `test_slug_auto_generation` - verifies slug from display_name
- [ ] `test_slug_conflict_resolution` - verifies numeric suffix handling
- [ ] `test_field_name_normalization` - verifies name->display_name mapping
- [ ] All 9 tests pass
- [ ] SQLite foreign key pragma enabled in conftest.py

### 8. Code Quality

- [ ] Feature comments reference "F035" or "Feature 035"
- [ ] Docstrings present for new functions
- [ ] No unused imports added
- [ ] No debug print statements left in code
- [ ] Session management pattern followed (functions accept optional session)
- [ ] No business logic in UI layer

## Verification Commands

Run these commands to verify the implementation:

```bash
cd /Users/kentgale/Vaults-repos/bake-tracker/.worktrees/035-ingredient-auto-slug

# Activate virtual environment
source /Users/kentgale/Vaults-repos/bake-tracker/venv/bin/activate

# Verify all modified modules import correctly
PYTHONPATH=. python3 -c "
from src.models.inventory_snapshot import SnapshotIngredient
from src.models.ingredient_alias import IngredientAlias
from src.models.ingredient_crosswalk import IngredientCrosswalk
from src.services.ingredient_service import can_delete_ingredient, delete_ingredient_safe
from src.services.exceptions import IngredientInUse, IngredientNotFound
from src.ui.ingredients_tab import IngredientsTab
print('All imports successful')
"

# Verify SnapshotIngredient schema changes
grep -n "ondelete" src/models/inventory_snapshot.py
grep -n "nullable=True" src/models/inventory_snapshot.py | head -5
grep -n "ingredient_name_snapshot\|parent_l1_name_snapshot\|parent_l0_name_snapshot" src/models/inventory_snapshot.py

# Verify CASCADE on Alias and Crosswalk
grep -n "ondelete" src/models/ingredient_alias.py
grep -n "ondelete" src/models/ingredient_crosswalk.py
grep -n "passive_deletes" src/models/ingredient_alias.py src/models/ingredient_crosswalk.py

# Verify deletion protection functions exist
grep -n "def can_delete_ingredient" src/services/ingredient_service.py
grep -n "def _denormalize_snapshot_ingredients" src/services/ingredient_service.py
grep -n "def delete_ingredient_safe" src/services/ingredient_service.py

# Verify IngredientInUse has details attribute
grep -n "self.details" src/services/exceptions.py

# Verify field normalization in create_ingredient
grep -n '"name".*"display_name"\|display_name.*name' src/services/ingredient_service.py | head -5

# Verify UI imports
grep -n "delete_ingredient_safe\|IngredientNotFound" src/ui/ingredients_tab.py | head -5

# Verify UI helper methods
grep -n "_show_deletion_blocked_message\|_show_dialog_deletion_blocked_message" src/ui/ingredients_tab.py

# Verify test class exists
grep -n "class TestDeletionProtectionAndSlug" src/tests/services/test_ingredient_service.py

# Verify all 9 deletion/slug tests
grep -n "def test_delete_blocked_by_products\|def test_delete_blocked_by_recipes\|def test_delete_blocked_by_children\|def test_delete_with_snapshots_denormalizes\|def test_delete_cascades_aliases\|def test_delete_cascades_crosswalks\|def test_slug_auto_generation\|def test_slug_conflict_resolution\|def test_field_name_normalization" src/tests/services/test_ingredient_service.py

# Verify SQLite foreign key pragma in conftest
grep -n "foreign_keys" src/tests/conftest.py

# Run the new deletion/slug tests
PYTHONPATH=. python3 -m pytest src/tests/services/test_ingredient_service.py::TestDeletionProtectionAndSlug -v --tb=short

# Run all ingredient service tests (should be 50 total)
PYTHONPATH=. python3 -m pytest src/tests/services/test_ingredient_service.py -v --tb=short 2>&1 | tail -60

# Run full test suite to verify no regressions
PYTHONPATH=. python3 -m pytest src/tests -v --tb=short 2>&1 | tail -100

# Check git log for F035 commits
git log --oneline -15
```

## Key Implementation Patterns

### Denormalization-then-Nullify Pattern (WP03)
```python
def _denormalize_snapshot_ingredients(ingredient_id: int, session) -> int:
    """Copy ingredient names to snapshot records before deletion."""
    from ..models import Ingredient
    from ..models.inventory_snapshot import SnapshotIngredient
    from .ingredient_hierarchy_service import get_ancestors

    ingredient = session.query(Ingredient).filter(
        Ingredient.id == ingredient_id
    ).first()
    if not ingredient:
        return 0

    ancestors = get_ancestors(ingredient_id, session=session)
    l1_name = ancestors[0]["display_name"] if len(ancestors) >= 1 else None
    l0_name = ancestors[1]["display_name"] if len(ancestors) >= 2 else None

    snapshots = session.query(SnapshotIngredient).filter(
        SnapshotIngredient.ingredient_id == ingredient_id
    ).all()

    for snapshot in snapshots:
        snapshot.ingredient_name_snapshot = ingredient.display_name
        snapshot.parent_l1_name_snapshot = l1_name
        snapshot.parent_l0_name_snapshot = l0_name
        snapshot.ingredient_id = None  # Nullify FK

    return len(snapshots)
```

### Safe Deletion Pattern (WP03)
```python
def delete_ingredient_safe(ingredient_id: int, session=None) -> bool:
    """Safely delete an ingredient with full protection."""
    def _delete(session):
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
        _denormalize_snapshot_ingredients(ingredient_id, session)

        # Delete ingredient (Alias/Crosswalk cascade via DB)
        session.delete(ingredient)
        return True

    if session is not None:
        return _delete(session)
    with session_scope() as session:
        return _delete(session)
```

### UI Error Message Pattern (WP05)
```python
def _show_deletion_blocked_message(self, details: dict):
    """Display user-friendly message when deletion is blocked."""
    parts = []
    if details.get("products", 0) > 0:
        count = details["products"]
        parts.append(f"{count} product{'s' if count > 1 else ''}")
    if details.get("recipes", 0) > 0:
        count = details["recipes"]
        parts.append(f"{count} recipe{'s' if count > 1 else ''}")
    if details.get("children", 0) > 0:
        count = details["children"]
        parts.append(f"{count} child ingredient{'s' if count > 1 else ''}")

    if parts:
        if len(parts) > 1:
            items = ", ".join(parts[:-1]) + " and " + parts[-1]
        else:
            items = parts[0]
        message = (
            f"Cannot delete this ingredient.\n\n"
            f"It is referenced by {items}.\n\n"
            f"Please reassign or remove these references first."
        )
    else:
        message = "Cannot delete this ingredient. It has active references."

    messagebox.showerror("Cannot Delete", message)
```

### Field Normalization Pattern (WP04)
```python
def create_ingredient(ingredient_data: dict, session=None) -> Ingredient:
    # Normalize field names for backward compatibility (F035)
    if "name" in ingredient_data and "display_name" not in ingredient_data:
        ingredient_data["display_name"] = ingredient_data.pop("name")
    # ... rest of function
```

## Output Format

Please output your findings to:
`/Users/kentgale/Vaults-repos/bake-tracker/docs/code-reviews/cursor-F035-review.md`

Use this format:

```markdown
# Cursor Code Review: Feature 035 - Ingredient Auto-Slug & Deletion Protection

**Date:** [DATE]
**Reviewer:** Cursor (AI Code Review)
**Feature:** 035-ingredient-auto-slug
**Branch/Worktree:** `.worktrees/035-ingredient-auto-slug`

## Summary

[Brief overview of findings - were deletion protection patterns correctly implemented? Are there any issues?]

## Verification Results

### Module Import Validation
- inventory_snapshot.py: [PASS/FAIL]
- ingredient_alias.py: [PASS/FAIL]
- ingredient_crosswalk.py: [PASS/FAIL]
- ingredient_service.py: [PASS/FAIL]
- exceptions.py: [PASS/FAIL]
- ingredients_tab.py: [PASS/FAIL]
- test_ingredient_service.py: [PASS/FAIL]

### Test Results
- Deletion/Slug tests (9): [X passed, Y failed]
- Full ingredient service tests (50): [X passed, Y failed]
- Full test suite: [X passed, Y skipped, Z failed]

### Code Pattern Validation
- Schema changes (WP01): [correct/issues found]
- Cascade delete config (WP02): [correct/issues found]
- Deletion protection service (WP03): [correct/issues found]
- Field normalization (WP04): [correct/issues found]
- UI integration (WP05): [correct/issues found]
- Tests (WP06): [correct/issues found]

## Findings

### Critical Issues
[Any blocking issues that must be fixed before merge]

### Warnings
[Non-blocking concerns that should be addressed]

### Observations
[General observations about code quality, patterns, potential improvements]

## Files Reviewed

| File | Status | Notes |
|------|--------|-------|
| src/models/inventory_snapshot.py | [status] | [notes] |
| src/models/ingredient_alias.py | [status] | [notes] |
| src/models/ingredient_crosswalk.py | [status] | [notes] |
| src/services/ingredient_service.py | [status] | [notes] |
| src/services/exceptions.py | [status] | [notes] |
| src/ui/ingredients_tab.py | [status] | [notes] |
| src/tests/services/test_ingredient_service.py | [status] | [notes] |
| src/tests/conftest.py | [status] | [notes] |

## Functional Requirements Verification

| Requirement | Status | Evidence |
|-------------|--------|----------|
| FR-001: SnapshotIngredient FK allows NULL | [PASS/FAIL] | [evidence] |
| FR-002: Denormalization columns exist | [PASS/FAIL] | [evidence] |
| FR-003: Alias cascade delete works | [PASS/FAIL] | [evidence] |
| FR-004: Crosswalk cascade delete works | [PASS/FAIL] | [evidence] |
| FR-005: Products block deletion | [PASS/FAIL] | [evidence] |
| FR-006: Recipes block deletion | [PASS/FAIL] | [evidence] |
| FR-007: Children block deletion | [PASS/FAIL] | [evidence] |
| FR-008: Snapshots denormalized before deletion | [PASS/FAIL] | [evidence] |
| FR-009: Error messages include counts | [PASS/FAIL] | [evidence] |
| FR-010: UI shows detailed error on blocked deletion | [PASS/FAIL] | [evidence] |
| FR-011: Field normalization works (name -> display_name) | [PASS/FAIL] | [evidence] |
| FR-012: Session management pattern followed | [PASS/FAIL] | [evidence] |
| FR-013: All existing tests pass (no regressions) | [PASS/FAIL] | [evidence] |

## Work Package Verification

| Work Package | Status | Notes |
|--------------|--------|-------|
| WP01: Schema & Denormalization Fields | [PASS/FAIL] | [notes] |
| WP02: Cascade Delete Configuration | [PASS/FAIL] | [notes] |
| WP03: Deletion Protection Service | [PASS/FAIL] | [notes] |
| WP04: Slug Field Mapping Fix | [PASS/FAIL] | [notes] |
| WP05: UI Delete Handler Integration | [PASS/FAIL] | [notes] |
| WP06: Deletion & Slug Tests | [PASS/FAIL] | [notes] |

## Code Quality Assessment

### Schema Changes (WP01)
| Item | Status | Notes |
|------|--------|-------|
| ingredient_id FK SET NULL | [Yes/No] | [notes] |
| ingredient_id nullable | [Yes/No] | [notes] |
| ingredient_name_snapshot column | [Yes/No] | [notes] |
| parent_l1_name_snapshot column | [Yes/No] | [notes] |
| parent_l0_name_snapshot column | [Yes/No] | [notes] |

### Cascade Delete (WP02)
| Item | Status | Notes |
|------|--------|-------|
| Alias CASCADE configured | [Yes/No] | [notes] |
| Crosswalk CASCADE configured | [Yes/No] | [notes] |
| passive_deletes on relationships | [Yes/No] | [notes] |

### Deletion Protection Service (WP03)
| Item | Status | Notes |
|------|--------|-------|
| can_delete_ingredient() exists | [Yes/No] | [notes] |
| Checks products | [Yes/No] | [notes] |
| Checks recipes | [Yes/No] | [notes] |
| Checks children | [Yes/No] | [notes] |
| Checks snapshots (info only) | [Yes/No] | [notes] |
| _denormalize_snapshot_ingredients() exists | [Yes/No] | [notes] |
| Copies L0/L1/L2 names | [Yes/No] | [notes] |
| Nullifies FK | [Yes/No] | [notes] |
| delete_ingredient_safe() exists | [Yes/No] | [notes] |
| Raises IngredientNotFound | [Yes/No] | [notes] |
| Raises IngredientInUse with details | [Yes/No] | [notes] |
| Session management pattern | [Yes/No] | [notes] |

### UI Integration (WP05)
| Item | Status | Notes |
|------|--------|-------|
| delete_ingredient_safe imported | [Yes/No] | [notes] |
| IngredientNotFound imported | [Yes/No] | [notes] |
| IngredientsTab uses safe deletion | [Yes/No] | [notes] |
| IngredientFormDialog uses safe deletion | [Yes/No] | [notes] |
| Error message shows counts | [Yes/No] | [notes] |
| Proper pluralization | [Yes/No] | [notes] |
| "and" before last item | [Yes/No] | [notes] |

### Tests (WP06)
| Test | Status | Notes |
|------|--------|-------|
| test_delete_blocked_by_products | [PASS/FAIL] | [notes] |
| test_delete_blocked_by_recipes | [PASS/FAIL] | [notes] |
| test_delete_blocked_by_children | [PASS/FAIL] | [notes] |
| test_delete_with_snapshots_denormalizes | [PASS/FAIL] | [notes] |
| test_delete_cascades_aliases | [PASS/FAIL] | [notes] |
| test_delete_cascades_crosswalks | [PASS/FAIL] | [notes] |
| test_slug_auto_generation | [PASS/FAIL] | [notes] |
| test_slug_conflict_resolution | [PASS/FAIL] | [notes] |
| test_field_name_normalization | [PASS/FAIL] | [notes] |

## Potential Issues

### Session Management
[Any concerns about session handling in the new functions]

### Edge Cases
[Any edge cases that may not be handled properly]

### Data Integrity
[Any concerns about data integrity during deletion/denormalization]

## Conclusion

[APPROVED / APPROVED WITH CHANGES / NEEDS REVISION]

[Final summary and any recommendations]
```

## Additional Context

- The project uses SQLAlchemy 2.x with type hints
- CustomTkinter for UI
- pytest for testing
- The worktree is isolated from main branch at `.worktrees/035-ingredient-auto-slug`
- Layered architecture: UI -> Services -> Models -> Database
- This feature addresses Gap Analysis Phase 3 requirements
- The ingredient hierarchy is: L0 (Root) -> L1 (Subcategory) -> L2 (Leaf/Ingredient)
- Session management is CRITICAL: functions must accept optional `session` parameter and pass it through
- All existing tests must pass (no regressions)
- The denormalization-then-nullify pattern preserves historical data while allowing ingredient deletion
- UI must NOT contain business logic - only display service results
- Error messages must be user-friendly with counts and action guidance
