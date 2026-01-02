# Cursor Code Review Prompt - Feature 033: Phase 1 Ingredient Hierarchy Fixes

## Role

You are a senior software engineer performing an independent code review of Feature 033 (phase-1-ingredient). This feature fixes conceptual issues in the ingredient hierarchy UI from F032, adding validation convenience functions, fixing the edit form mental model, and improving hierarchy path display.

## Feature Summary

**Core Changes:**
1. Service Layer Functions: Add three validation/counting convenience functions (WP01)
2. UI Form Fix (MVP): Remove level selector, compute level from parent selection (WP02)
3. Hierarchy Path Display: Add single hierarchy path column showing full path (WP03)
4. Legacy Form Deprecation: Mark `ingredient_form.py` as deprecated (WP04)

**Scope:**
- Service layer: `ingredient_hierarchy_service.py` (3 new functions)
- Tests: `test_ingredient_hierarchy_service.py` (16 new tests)
- UI layer: `ingredients_tab.py` (form and list view changes)
- Forms layer: `ingredient_form.py` (deprecation only)

## Files to Review

### Service Layer (WP01)

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/033-phase-1-ingredient/src/services/ingredient_hierarchy_service.py`
  - **WP01**: `get_child_count(ingredient_id, session=None) -> int`
  - **WP01**: `get_product_count(ingredient_id, session=None) -> int`
  - **WP01**: `can_change_parent(ingredient_id, new_parent_id, session=None) -> Dict[str, Any]`
  - All functions follow session management pattern with optional `session` parameter
  - `can_change_parent()` returns structured dict: `{allowed, reason, warnings, child_count, product_count, new_level}`
  - Added imports: `Product` model, `Any` from typing

### Test Layer (WP01)

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/033-phase-1-ingredient/src/tests/services/test_ingredient_hierarchy_service.py`
  - **WP01**: `test_db_with_products` fixture with Product model instances
  - **WP01**: `TestGetChildCount` class (4 tests)
  - **WP01**: `TestGetProductCount` class (4 tests)
  - **WP01**: `TestCanChangeParent` class (8 tests)
  - Tests cover: happy paths, edge cases, circular references, depth exceeded, warnings

### UI Layer - Ingredients Tab (WP02, WP03)

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/033-phase-1-ingredient/src/ui/ingredients_tab.py`
  - **WP02**: `ingredient_level_dropdown` and `ingredient_level_var` REMOVED
  - **WP02**: `_on_ingredient_level_change()` method REMOVED
  - **WP02**: `_update_hierarchy_visibility()` method REMOVED
  - **WP02**: `level_display_var` and `level_display` label ADDED (read-only)
  - **WP02**: `warning_label` ADDED for parent change warnings
  - **WP02**: `_compute_and_display_level()` method ADDED
  - **WP02**: `_check_parent_change_warnings()` method ADDED
  - **WP02**: `_get_selected_parent_id()` method ADDED
  - **WP02**: `_on_l1_change()` method ADDED
  - **WP02**: L0 dropdown default changed to "(None - create root)"
  - **WP02**: L1 dropdown default changed to "(Select L0 first)" / "(None - create L1)"
  - **WP02**: `_populate_form()` updated for new dropdown behavior
  - **WP02**: `_save()` simplified to use `_compute_and_display_level()` and `_get_selected_parent_id()`
  - **WP03**: Grid columns changed from `("l0", "l1", "name", "density")` to `("hierarchy_path", "name", "density")`
  - **WP03**: `_build_hierarchy_cache()` renamed to `_build_hierarchy_path_cache()`
  - **WP03**: Cache returns `Dict[int, str]` (path string) instead of `Dict[int, tuple]`
  - **WP03**: `_hierarchy_cache` renamed to `_hierarchy_path_cache` in `__init__`
  - **WP03**: Sorting updated to support `hierarchy_path` column

### Forms Layer - Legacy Deprecation (WP04)

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/033-phase-1-ingredient/src/ui/forms/ingredient_form.py`
  - **WP04**: Module-level deprecation docstring with `.. deprecated::` directive
  - **WP04**: Class-level deprecation docstring on `IngredientFormDialog`
  - **WP04**: `import warnings` added
  - **WP04**: `warnings.warn()` call in `__init__` with `DeprecationWarning` and `stacklevel=2`
  - **WP04**: Call sites documented (none found in active codebase)

### Specification Documents

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/033-phase-1-ingredient/kitty-specs/033-phase-1-ingredient/spec.md`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/033-phase-1-ingredient/kitty-specs/033-phase-1-ingredient/plan.md`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/033-phase-1-ingredient/kitty-specs/033-phase-1-ingredient/tasks.md`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/033-phase-1-ingredient/kitty-specs/033-phase-1-ingredient/research.md`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/033-phase-1-ingredient/kitty-specs/033-phase-1-ingredient/data-model.md`

## Review Checklist

### 1. Service Layer Functions (WP01)

- [ ] `get_child_count()` implemented with correct signature
- [ ] `get_child_count()` accepts optional `session` parameter
- [ ] `get_child_count()` follows session management pattern (inner `_impl` function)
- [ ] `get_child_count()` returns integer count of direct children
- [ ] `get_product_count()` implemented with correct signature
- [ ] `get_product_count()` accepts optional `session` parameter
- [ ] `get_product_count()` follows session management pattern
- [ ] `get_product_count()` returns integer count of linked products
- [ ] `Product` model imported at top of file
- [ ] `can_change_parent()` implemented with correct signature
- [ ] `can_change_parent()` accepts optional `session` parameter
- [ ] `can_change_parent()` returns dict with keys: `allowed`, `reason`, `warnings`, `child_count`, `product_count`, `new_level`
- [ ] `can_change_parent()` catches `IngredientNotFound`, `CircularReferenceError`, `MaxDepthExceededError`
- [ ] `can_change_parent()` computes `new_level` correctly based on parent
- [ ] `can_change_parent()` adds warnings for products and children (non-blocking)
- [ ] `Any` imported from typing module

### 2. Unit Tests (WP01)

- [ ] `test_db_with_products` fixture creates hierarchy with products
- [ ] Products use correct model fields (`product_name`, `brand`, `package_unit`, `package_unit_quantity`)
- [ ] `TestGetChildCount` has test for root with children
- [ ] `TestGetChildCount` has test for mid-tier with children
- [ ] `TestGetChildCount` has test for leaf (0 children)
- [ ] `TestGetChildCount` has test for nonexistent ingredient
- [ ] `TestGetProductCount` has test for ingredient with products
- [ ] `TestGetProductCount` has test for different product count
- [ ] `TestGetProductCount` has test for ingredient with no products
- [ ] `TestGetProductCount` has test for nonexistent ingredient
- [ ] `TestCanChangeParent` has test for valid change
- [ ] `TestCanChangeParent` has test for becoming root
- [ ] `TestCanChangeParent` has test for circular reference blocked
- [ ] `TestCanChangeParent` has test for depth exceeded blocked
- [ ] `TestCanChangeParent` has test for product warning
- [ ] `TestCanChangeParent` has test for child warning
- [ ] `TestCanChangeParent` has test for no warnings
- [ ] `TestCanChangeParent` has test for counts returned when blocked

### 3. UI Form Fix (WP02)

- [ ] `ingredient_level_dropdown` completely removed
- [ ] `ingredient_level_var` completely removed
- [ ] `_on_ingredient_level_change()` method removed
- [ ] `_update_hierarchy_visibility()` method removed
- [ ] `level_display_var` added as `ctk.StringVar`
- [ ] `level_display` label added as `ctk.CTkLabel`
- [ ] `warning_label` added as `ctk.CTkLabel` (hidden by default)
- [ ] `_compute_and_display_level()` returns correct level (0, 1, or 2)
- [ ] `_compute_and_display_level()` updates `level_display_var`
- [ ] `_compute_and_display_level()` calls `_check_parent_change_warnings()`
- [ ] `_check_parent_change_warnings()` only runs for existing ingredients
- [ ] `_check_parent_change_warnings()` calls `can_change_parent()` service
- [ ] `_check_parent_change_warnings()` shows red text for blocked changes
- [ ] `_check_parent_change_warnings()` shows orange text for warnings
- [ ] `_get_selected_parent_id()` returns `None` for root selection
- [ ] `_get_selected_parent_id()` returns L0 ID for L1 selection
- [ ] `_get_selected_parent_id()` returns L1 ID for L2 selection
- [ ] `_on_l1_change()` calls `_compute_and_display_level()`
- [ ] `_on_l0_change()` calls `_compute_and_display_level()`
- [ ] L0 dropdown has "(None - create root)" option
- [ ] L1 dropdown has "(None - create L1)" option when L0 selected
- [ ] `_populate_form()` handles L0 ingredients correctly
- [ ] `_save()` uses `_compute_and_display_level()` for hierarchy_level
- [ ] `_save()` uses `_get_selected_parent_id()` for parent_ingredient_id
- [ ] No references to `ingredient_level_var` remain

### 4. Hierarchy Path Display (WP03)

- [ ] Grid columns changed to `("hierarchy_path", "name", "density")`
- [ ] "Hierarchy" column header configured
- [ ] Column width set appropriately (~300)
- [ ] `_build_hierarchy_path_cache()` returns `Dict[int, str]`
- [ ] L0 ingredients show just their name (no " > ")
- [ ] L1 ingredients show "Parent > Name"
- [ ] L2 ingredients show "Grandparent > Parent > Name"
- [ ] `_hierarchy_path_cache` initialized in `__init__`
- [ ] `_update_ingredient_display()` uses `_hierarchy_path_cache`
- [ ] Values tuple updated to `(hierarchy_path, name, density)`
- [ ] Sorting supports `hierarchy_path` key
- [ ] Old `l0_name`/`l1_name` sort keys removed

### 5. Legacy Form Deprecation (WP04)

- [ ] Module-level docstring includes `.. deprecated::` directive
- [ ] Module-level docstring mentions Feature 033
- [ ] Module-level docstring directs to `ingredients_tab.py`
- [ ] Class-level docstring includes `.. deprecated::` directive
- [ ] Class-level docstring mentions L0/L1/L2 hierarchy not supported
- [ ] `import warnings` added
- [ ] `warnings.warn()` in `__init__` before `super().__init__()`
- [ ] Warning uses `DeprecationWarning` type
- [ ] Warning uses `stacklevel=2`
- [ ] Warning message mentions `ingredients_tab.py` alternative
- [ ] Existing functionality not broken (dialog still works)

## Verification Commands

Run these commands to verify the implementation:

```bash
cd /Users/kentgale/Vaults-repos/bake-tracker/.worktrees/033-phase-1-ingredient

# Activate virtual environment
source /Users/kentgale/Vaults-repos/bake-tracker/venv/bin/activate

# Verify all modified modules import correctly
PYTHONPATH=. python3 -c "
from src.services.ingredient_hierarchy_service import get_child_count, get_product_count, can_change_parent
from src.ui.ingredients_tab import IngredientsTab, IngredientFormDialog
from src.ui.forms.ingredient_form import IngredientFormDialog as LegacyDialog
print('All imports successful')
"

# Verify new service functions exist with correct signatures
PYTHONPATH=. python3 -c "
import inspect
from src.services import ingredient_hierarchy_service as svc

# Check get_child_count
sig = inspect.signature(svc.get_child_count)
print('get_child_count params:', list(sig.parameters.keys()))

# Check get_product_count
sig = inspect.signature(svc.get_product_count)
print('get_product_count params:', list(sig.parameters.keys()))

# Check can_change_parent
sig = inspect.signature(svc.can_change_parent)
print('can_change_parent params:', list(sig.parameters.keys()))
"

# Verify Product import in hierarchy service
grep -n "from src.models.product import Product" src/services/ingredient_hierarchy_service.py

# Verify level dropdown removed from ingredients_tab
grep -n "ingredient_level_var\|ingredient_level_dropdown\|_on_ingredient_level_change\|_update_hierarchy_visibility" src/ui/ingredients_tab.py
# Should return nothing

# Verify new form elements exist
grep -n "level_display_var\|level_display\|warning_label\|_compute_and_display_level\|_check_parent_change_warnings\|_get_selected_parent_id\|_on_l1_change" src/ui/ingredients_tab.py | head -20

# Verify hierarchy_path column
grep -n "hierarchy_path" src/ui/ingredients_tab.py | head -10

# Verify _build_hierarchy_path_cache method
grep -n "_build_hierarchy_path_cache\|_hierarchy_path_cache" src/ui/ingredients_tab.py | head -10

# Verify deprecation warning in legacy form
grep -n "warnings.warn\|DeprecationWarning\|stacklevel" src/ui/forms/ingredient_form.py

# Run ALL tests to verify no regressions
PYTHONPATH=. /Users/kentgale/Vaults-repos/bake-tracker/venv/bin/pytest src/tests -v --tb=short 2>&1 | tail -50

# Run specific WP01 tests
PYTHONPATH=. /Users/kentgale/Vaults-repos/bake-tracker/venv/bin/pytest src/tests/services/test_ingredient_hierarchy_service.py -v --tb=short -k "TestGetChildCount or TestGetProductCount or TestCanChangeParent"

# Count new tests
PYTHONPATH=. /Users/kentgale/Vaults-repos/bake-tracker/venv/bin/pytest src/tests/services/test_ingredient_hierarchy_service.py --collect-only 2>&1 | grep "test session starts" -A 5
```

## Key Implementation Patterns

### Session Management Pattern (WP01)
```python
def get_child_count(ingredient_id: int, session=None) -> int:
    """Count direct child ingredients."""
    def _impl(session):
        return session.query(Ingredient).filter(
            Ingredient.parent_ingredient_id == ingredient_id
        ).count()

    if session is not None:
        return _impl(session)
    with session_scope() as session:
        return _impl(session)
```

### can_change_parent Return Structure (WP01)
```python
result = {
    "allowed": True,           # bool - whether change is permitted
    "reason": "",              # str - error message if not allowed
    "warnings": [],            # List[str] - informational warnings
    "child_count": 0,          # int - number of children
    "product_count": 0,        # int - number of linked products
    "new_level": 0             # int - computed level after change (0, 1, or 2)
}
```

### Level Computation Pattern (WP02)
```python
def _compute_and_display_level(self):
    l0_selection = self.l0_var.get()
    l1_selection = self.l1_var.get()

    if l0_selection == "(None - create root)":
        level = 0
        level_text = "Level: L0 (Root Category)"
    elif l1_selection in ["(Select L0 first)", "(None - create L1)", ""]:
        level = 1
        level_text = "Level: L1 (Subcategory)"
    else:
        level = 2
        level_text = "Level: L2 (Leaf Ingredient)"

    self.level_display_var.set(level_text)
    self._check_parent_change_warnings()
    return level
```

### Hierarchy Path Cache Pattern (WP03)
```python
def _build_hierarchy_path_cache(self) -> Dict[int, str]:
    cache = {}
    for ingredient in self.ingredients:
        ing_id = ingredient.get("id")
        ing_name = ingredient.get("display_name", "")
        level = ingredient.get("hierarchy_level", 2)

        if level == 0:
            cache[ing_id] = ing_name
        elif level == 1:
            ancestors = get_ancestors(ing_id)
            l0_name = ancestors[0].get("display_name", "")
            cache[ing_id] = f"{l0_name} > {ing_name}"
        else:  # level == 2
            ancestors = get_ancestors(ing_id)
            l0_name = ancestors[1].get("display_name", "")
            l1_name = ancestors[0].get("display_name", "")
            cache[ing_id] = f"{l0_name} > {l1_name} > {ing_name}"
    return cache
```

### Deprecation Warning Pattern (WP04)
```python
import warnings

class IngredientFormDialog(ctk.CTkToplevel):
    """
    .. deprecated::
        Use the inline form in `ingredients_tab.py` instead.
    """

    def __init__(self, parent, ...):
        warnings.warn(
            "IngredientFormDialog is deprecated. Use the inline form in "
            "ingredients_tab.py instead, which supports ingredient hierarchy.",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(parent)
```

## Output Format

Please output your findings to:
`/Users/kentgale/Vaults-repos/bake-tracker/docs/code-reviews/cursor-F033-review.md`

Use this format:

```markdown
# Cursor Code Review: Feature 033 - Phase 1 Ingredient Hierarchy Fixes

**Date:** [DATE]
**Reviewer:** Cursor (AI Code Review)
**Feature:** 033-phase-1-ingredient
**Branch:** 033-phase-1-ingredient

## Summary

[Brief overview of findings]

## Verification Results

### Module Import Validation
- ingredient_hierarchy_service.py: [PASS/FAIL]
- ingredients_tab.py: [PASS/FAIL]
- ingredient_form.py: [PASS/FAIL]

### Test Results
- Full test suite: [X passed, Y skipped, Z failed]
- WP01 specific tests: [X passed, Y failed]

### Code Pattern Validation
- Session management pattern: [correct/issues found]
- Level computation pattern: [correct/issues found]
- Hierarchy path cache pattern: [correct/issues found]
- Deprecation warning pattern: [correct/issues found]

## Findings

### Critical Issues
[Any blocking issues that must be fixed]

### Warnings
[Non-blocking concerns]

### Observations
[General observations about code quality]

## Files Reviewed

| File | Status | Notes |
|------|--------|-------|
| src/services/ingredient_hierarchy_service.py | [status] | [notes] |
| src/tests/services/test_ingredient_hierarchy_service.py | [status] | [notes] |
| src/ui/ingredients_tab.py | [status] | [notes] |
| src/ui/forms/ingredient_form.py | [status] | [notes] |

## Architecture Assessment

### Session Management
[Assessment of proper session parameter handling in new service functions]

### Service Layer
[Assessment of service function implementation]

### UI Layer
[Assessment of form changes and hierarchy path display]

## Functional Requirements Verification

| Requirement | Status | Evidence |
|-------------|--------|----------|
| FR-001: get_child_count returns correct count | [PASS/FAIL] | [evidence] |
| FR-002: get_product_count returns correct count | [PASS/FAIL] | [evidence] |
| FR-003: can_change_parent returns structured dict | [PASS/FAIL] | [evidence] |
| FR-004: can_change_parent blocks circular refs | [PASS/FAIL] | [evidence] |
| FR-005: can_change_parent blocks depth exceeded | [PASS/FAIL] | [evidence] |
| FR-006: can_change_parent returns warnings | [PASS/FAIL] | [evidence] |
| FR-007: Level dropdown removed from form | [PASS/FAIL] | [evidence] |
| FR-008: Level computed from parent selection | [PASS/FAIL] | [evidence] |
| FR-009: Warning label shows for existing ingredients | [PASS/FAIL] | [evidence] |
| FR-010: L0 dropdown has "(None - create root)" | [PASS/FAIL] | [evidence] |
| FR-011: L1 dropdown has "(None - create L1)" | [PASS/FAIL] | [evidence] |
| FR-012: Hierarchy path column shows full path | [PASS/FAIL] | [evidence] |
| FR-013: L0 shows just name | [PASS/FAIL] | [evidence] |
| FR-014: L1 shows "Parent > Name" | [PASS/FAIL] | [evidence] |
| FR-015: L2 shows "Grandparent > Parent > Name" | [PASS/FAIL] | [evidence] |
| FR-016: Legacy form has deprecation docstring | [PASS/FAIL] | [evidence] |
| FR-017: Legacy form has runtime warning | [PASS/FAIL] | [evidence] |
| FR-018: All 16 new tests pass | [PASS/FAIL] | [evidence] |
| FR-019: No regressions in existing tests | [PASS/FAIL] | [evidence] |

## Work Package Verification

| Work Package | Status | Notes |
|--------------|--------|-------|
| WP01: Service Layer Functions | [PASS/FAIL] | [notes] |
| WP02: UI Form Fix (MVP) | [PASS/FAIL] | [notes] |
| WP03: Hierarchy Path Display | [PASS/FAIL] | [notes] |
| WP04: Legacy Form Deprecation | [PASS/FAIL] | [notes] |

## User Story Verification

Reference: `kitty-specs/033-phase-1-ingredient/spec.md`

| User Story | Status | Notes |
|------------|--------|-------|
| US-P1: Correct Parent Selection UX | [PASS/FAIL] | [notes] |
| US-P2: Validation Before Parent Change | [PASS/FAIL] | [notes] |
| US-P3: Hierarchy Path Display | [PASS/FAIL] | [notes] |

### Acceptance Scenarios

| Scenario | Status | Notes |
|----------|--------|-------|
| P1-S1: No parent = L0 (Root) | [PASS/FAIL] | [notes] |
| P1-S2: L0 parent = L1 (Subcategory) | [PASS/FAIL] | [notes] |
| P1-S3: L1 parent = L2 (Leaf) | [PASS/FAIL] | [notes] |
| P1-S4: Only L0/L1 in parent dropdown | [PASS/FAIL] | [notes] |
| P2-S1: Warning for linked products | [PASS/FAIL] | [notes] |
| P2-S2: Warning for child ingredients | [PASS/FAIL] | [notes] |
| P2-S3: Blocked circular reference | [PASS/FAIL] | [notes] |
| P2-S4: Blocked depth exceeded | [PASS/FAIL] | [notes] |
| P3-S1: L2 shows full path | [PASS/FAIL] | [notes] |
| P3-S2: L0 shows just name | [PASS/FAIL] | [notes] |

## Code Quality Assessment

### Removed Code Verification
| Item | Removed | Notes |
|------|---------|-------|
| ingredient_level_var | [Yes/No] | [notes] |
| ingredient_level_dropdown | [Yes/No] | [notes] |
| _on_ingredient_level_change() | [Yes/No] | [notes] |
| _update_hierarchy_visibility() | [Yes/No] | [notes] |
| _hierarchy_cache (old tuple version) | [Yes/No] | [notes] |
| l0_name/l1_name sort keys | [Yes/No] | [notes] |

### Added Code Verification
| Item | Added | Notes |
|------|-------|-------|
| get_child_count() | [Yes/No] | [notes] |
| get_product_count() | [Yes/No] | [notes] |
| can_change_parent() | [Yes/No] | [notes] |
| level_display_var | [Yes/No] | [notes] |
| warning_label | [Yes/No] | [notes] |
| _compute_and_display_level() | [Yes/No] | [notes] |
| _check_parent_change_warnings() | [Yes/No] | [notes] |
| _get_selected_parent_id() | [Yes/No] | [notes] |
| _on_l1_change() | [Yes/No] | [notes] |
| _build_hierarchy_path_cache() | [Yes/No] | [notes] |
| hierarchy_path column | [Yes/No] | [notes] |

## Conclusion

[APPROVED / APPROVED WITH CHANGES / NEEDS REVISION]

[Final summary and any recommendations]
```

## Additional Context

- The project uses SQLAlchemy 2.x with type hints
- CustomTkinter for UI
- pytest for testing
- The worktree is isolated from main branch at `.worktrees/033-phase-1-ingredient`
- Layered architecture: UI -> Services -> Models -> Database
- This feature builds on existing `ingredient_hierarchy_service.py` from F031/F032
- Key existing functions: `get_root_ingredients()`, `get_children()`, `get_ancestors()`, `get_leaf_ingredients()`, `validate_hierarchy()`
- All existing tests must pass (no regressions)
- Session management pattern is CRITICAL - all service functions accepting `session=None` must follow the inner `_impl` pattern
- The hierarchy is: L0 (Root) -> L1 (Subcategory) -> L2 (Leaf/Ingredient)
- Max depth is 3 levels (0, 1, 2)
- Warnings in `can_change_parent()` are informational only (non-blocking per planning decision)
- The legacy `ingredient_form.py` dialog uses category dropdown and should NOT be modified for hierarchy support - only deprecated
