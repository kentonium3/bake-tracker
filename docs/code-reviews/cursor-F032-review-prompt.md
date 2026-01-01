# Cursor Code Review Prompt - Feature 032: Complete F031 Hierarchy UI

## Role

You are a senior software engineer performing an independent code review of Feature 032 (complete-f031-hierarchy). This feature completes the three-tier ingredient hierarchy UI that was partially implemented in F031, replacing all deprecated "category" UI elements with proper L0/L1/L2 hierarchy displays and filters.

## Feature Summary

**Core Changes:**
1. Ingredients Tab Grid Columns: Replace "Category" column with "Root (L0)" and "Subcategory (L1)" columns (WP01)
2. Ingredients Tab Level Filter: Replace category dropdown with hierarchy level filter (WP02)
3. Ingredient Edit Form: Add cascading L0/L1 dropdowns and type selector (WP03)
4. Products Tab Hierarchy: Add hierarchy path display and cascading filters (WP04)
5. Inventory Tab Hierarchy: Add cascading hierarchy filters replacing category (WP05)
6. Inventory Form Labels: Add read-only hierarchy labels to form dialog (WP06)
7. Leaf-Only Validation: Enforce L2-only ingredient selection for products/recipes (WP07)
8. Manual Testing & Cleanup: Code verification and testing checklist (WP08)

**Scope:**
- UI layer: `ingredients_tab.py`, `products_tab.py`, `inventory_tab.py`
- Forms layer: `add_product_dialog.py`, `recipe_form.py`
- No new services (uses existing `ingredient_hierarchy_service.py`)
- No new tests (UI-only changes, manual testing required)

## Files to Review

### UI Layer - Ingredients Tab (WP01, WP02, WP03)

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/032-complete-f031-hierarchy/src/ui/ingredients_tab.py`
  - **WP01**: Grid columns changed from "Category" to "Root (L0)", "Subcategory (L1)", "Name"
  - **WP01**: `_build_hierarchy_cache()` method for N+1 query avoidance
  - **WP01**: `_hierarchy_cache` instance variable
  - **WP02**: Level filter dropdown replacing category dropdown
  - **WP02**: `_get_selected_level()` helper method
  - **WP02**: `_on_level_filter_change()` handler
  - **WP03**: `IngredientFormDialog` changes:
    - Modal pattern (withdraw/deiconify)
    - Ingredient type selector (Root/Subcategory/Leaf)
    - Cascading L0/L1 dropdowns
    - `_on_ingredient_level_change()` handler
    - `_on_l0_change()` cascade handler
    - `_update_hierarchy_visibility()` method
    - Updated `_populate_form()` for hierarchy pre-population
    - Updated `_save()` for hierarchy_level and parent_ingredient_id

### UI Layer - Products Tab (WP04)

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/032-complete-f031-hierarchy/src/ui/products_tab.py`
  - Grid column changed from "category" to "hierarchy_path"
  - `_hierarchy_path_cache` instance variable
  - `_build_hierarchy_path_cache()` method
  - Cascading L0 -> L1 -> L2 filter dropdowns
  - `_l0_map`, `_l1_map`, `_l2_map` for filter state
  - `_on_l0_filter_change()`, `_on_l1_filter_change()` handlers
  - `_apply_hierarchy_filters()` method
  - `_get_all_leaf_descendants()` recursive helper

### UI Layer - Inventory Tab (WP05, WP06)

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/032-complete-f031-hierarchy/src/ui/inventory_tab.py`
  - **WP05**: Cascading L0 -> L1 -> L2 filter dropdowns
  - **WP05**: `_l0_map`, `_l1_map`, `_l2_map` for filter state
  - **WP05**: `_build_hierarchy_path_cache()` method
  - **WP05**: `_on_l0_filter_change()`, `_on_l1_filter_change()`, `_on_l2_filter_change()` handlers
  - **WP05**: `_apply_hierarchy_filters()` method
  - **WP05**: `_get_all_leaf_descendants()` recursive helper
  - **WP05**: Updated `filter_by_ingredient()` to reset hierarchy filters
  - **WP06**: `InventoryItemFormDialog` hierarchy labels:
    - `hierarchy_l0_value`, `hierarchy_l1_value`, `hierarchy_l2_value` labels
    - `_update_hierarchy_labels()` method
    - `_clear_hierarchy_labels()` method
    - Labels update on ingredient selection

### Forms Layer - Add Product Dialog (WP07)

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/032-complete-f031-hierarchy/src/ui/forms/add_product_dialog.py`
  - Import added for `ingredient_hierarchy_service`
  - `_load_data()` uses `get_leaf_ingredients()` instead of `get_all_ingredients()`
  - `ingredients_map` keyed by `display_name`
  - `_on_ingredient_change()` shows hierarchy path instead of category
  - `_validate()` includes leaf-only validation with user-friendly error message
  - Label changed from "Category" to "Hierarchy"

### Forms Layer - Recipe Form (WP07)

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/032-complete-f031-hierarchy/src/ui/forms/recipe_form.py`
  - Uses `ingredient_hierarchy_service.get_leaf_ingredients()` directly
  - Queries Ingredient model with leaf IDs for compatibility with existing code

### Specification Documents

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/032-complete-f031-hierarchy/kitty-specs/032-complete-f031-hierarchy/spec.md`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/032-complete-f031-hierarchy/kitty-specs/032-complete-f031-hierarchy/plan.md`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/032-complete-f031-hierarchy/kitty-specs/032-complete-f031-hierarchy/tasks.md`

### Bug Specification

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/032-complete-f031-hierarchy/docs/bugs/BUG_F031_incomplete_hierarchy_ui.md`

## Review Checklist

### 1. Ingredients Grid Columns (WP01)

- [ ] "Category" column removed from grid
- [ ] "Root (L0)" column added with header and sortable
- [ ] "Subcategory (L1)" column added with header and sortable
- [ ] "Name" column retained
- [ ] `_build_hierarchy_cache()` method exists and builds Dict[int, tuple]
- [ ] Cache built once per refresh, not per row
- [ ] L0 ingredients show "--" for both L0 and L1 columns
- [ ] L1 ingredients show L0 parent, "--" for L1 column
- [ ] L2 ingredients show L0 grandparent, L1 parent
- [ ] `ingredient_hierarchy_service` imported

### 2. Ingredients Level Filter (WP02)

- [ ] Category dropdown removed from filter area
- [ ] Level filter dropdown added with values: "All Levels", "Root Categories (L0)", "Subcategories (L1)", "Leaf Ingredients (L2)"
- [ ] `_get_selected_level()` returns None for "All Levels", 0/1/2 for specific levels
- [ ] `_apply_filters()` filters by `hierarchy_level` field
- [ ] Search works with level filter (AND logic)
- [ ] Clear button resets level filter to "All Levels"

### 3. Ingredient Edit Form Hierarchy (WP03)

- [ ] Modal pattern applied: `withdraw()` at start, `deiconify()` at end
- [ ] `wait_visibility()` wrapped in try/except
- [ ] Ingredient type selector with options: "Root Category (L0)", "Subcategory (L1)", "Leaf Ingredient (L2)"
- [ ] L0 dropdown populated from `get_root_ingredients()`
- [ ] L1 dropdown cascades based on L0 selection via `get_children()`
- [ ] `_on_ingredient_level_change()` shows/hides appropriate dropdowns
- [ ] `_on_l0_change()` populates L1 dropdown
- [ ] `_populate_form()` pre-populates hierarchy when editing
- [ ] `_save()` sets `hierarchy_level` and `parent_ingredient_id` correctly
- [ ] No deprecated "category" references in form save logic

### 4. Products Tab Hierarchy (WP04)

- [ ] "category" column removed from grid
- [ ] "hierarchy_path" column added showing "L0 -> L1 -> L2" format
- [ ] `_build_hierarchy_path_cache()` creates ingredient_id -> path string mapping
- [ ] Cascading L0 filter dropdown populated from `get_root_ingredients()`
- [ ] L1 filter cascades from L0 selection
- [ ] L2 filter cascades from L1 selection
- [ ] `_apply_hierarchy_filters()` filters products by ingredient hierarchy
- [ ] `_get_all_leaf_descendants()` recursively finds L2 descendants
- [ ] Category filter variables removed (ingredient_var, category_var)

### 5. Inventory Grid Hierarchy (WP05)

- [ ] Category filter removed from controls
- [ ] Ingredient filter removed from controls
- [ ] Cascading L0 -> L1 -> L2 filter dropdowns added
- [ ] `_build_hierarchy_path_cache()` exists
- [ ] `_on_l0_filter_change()` cascades to L1
- [ ] `_on_l1_filter_change()` cascades to L2
- [ ] `_apply_hierarchy_filters()` filters inventory items
- [ ] `_get_all_leaf_descendants()` exists
- [ ] `filter_by_ingredient()` resets hierarchy filters

### 6. Inventory Form Hierarchy Display (WP06)

- [ ] Hierarchy labels added to `InventoryItemFormDialog`
- [ ] Three labels: Category (L0), Subcategory (L1), Ingredient (L2)
- [ ] Labels are read-only (CTkLabel, not entry/dropdown)
- [ ] `_update_hierarchy_labels()` called on ingredient selection
- [ ] `_clear_hierarchy_labels()` resets to "--"
- [ ] Labels pre-populated when editing existing item
- [ ] Uses `get_ancestors()` to determine hierarchy

### 7. Leaf-Only Validation (WP07)

- [ ] `add_product_dialog.py` imports `ingredient_hierarchy_service`
- [ ] `_load_data()` uses `get_leaf_ingredients()` not `get_all_ingredients()`
- [ ] `ingredients_map` keyed by `display_name`
- [ ] `_validate()` checks `hierarchy_level != 2` with error message
- [ ] Error message explains leaf-only requirement
- [ ] `_on_ingredient_change()` shows hierarchy path instead of category
- [ ] "Hierarchy" label instead of "Category" label
- [ ] `recipe_form.py` uses `get_leaf_ingredients()` directly

### 8. Code Cleanup (WP08)

- [ ] No UI-visible "category" dropdown/column in affected components
- [ ] All imports verified successful
- [ ] No syntax errors in modified files

## Verification Commands

Run these commands to verify the implementation:

```bash
cd /Users/kentgale/Vaults-repos/bake-tracker/.worktrees/032-complete-f031-hierarchy

# Activate virtual environment
source /Users/kentgale/Vaults-repos/bake-tracker/venv/bin/activate

# Verify all modified UI modules import correctly
python3 -c "
from src.ui.ingredients_tab import IngredientsTab, IngredientFormDialog
from src.ui.products_tab import ProductsTab
from src.ui.inventory_tab import InventoryTab, InventoryItemFormDialog
from src.ui.forms.add_product_dialog import AddProductDialog
from src.ui.forms.recipe_form import RecipeFormDialog
print('All UI imports successful')
"

# Verify hierarchy service functions used
python3 -c "
from src.services import ingredient_hierarchy_service
print('get_root_ingredients:', hasattr(ingredient_hierarchy_service, 'get_root_ingredients'))
print('get_children:', hasattr(ingredient_hierarchy_service, 'get_children'))
print('get_ancestors:', hasattr(ingredient_hierarchy_service, 'get_ancestors'))
print('get_leaf_ingredients:', hasattr(ingredient_hierarchy_service, 'get_leaf_ingredients'))
print('get_ingredients_by_level:', hasattr(ingredient_hierarchy_service, 'get_ingredients_by_level'))
"

# Verify ingredients_tab has hierarchy cache method
grep -n "_build_hierarchy_cache\|_hierarchy_cache" src/ui/ingredients_tab.py | head -10

# Verify products_tab has hierarchy path cache
grep -n "_build_hierarchy_path_cache\|_hierarchy_path_cache" src/ui/products_tab.py | head -10

# Verify inventory_tab has hierarchy filters
grep -n "_on_l0_filter_change\|_on_l1_filter_change\|_on_l2_filter_change" src/ui/inventory_tab.py | head -10

# Verify add_product_dialog uses get_leaf_ingredients
grep -n "get_leaf_ingredients\|ingredient_hierarchy_service" src/ui/forms/add_product_dialog.py

# Verify recipe_form uses get_leaf_ingredients
grep -n "get_leaf_ingredients\|ingredient_hierarchy_service" src/ui/forms/recipe_form.py

# Check for remaining "category" references in grid columns
grep -n 'columns.*=.*"category"\|heading.*"category"' src/ui/ingredients_tab.py src/ui/products_tab.py src/ui/inventory_tab.py

# Check for removed category filter variables
grep -n "category_var\|category_dropdown" src/ui/ingredients_tab.py src/ui/products_tab.py src/ui/inventory_tab.py | grep -v "# "

# Run ALL tests to verify no regressions
PYTHONPATH=. python3 -m pytest src/tests -v --tb=short 2>&1 | tail -40

# Check specific service tests still pass
PYTHONPATH=. python3 -m pytest src/tests/services/test_ingredient_hierarchy_service.py -v --tb=short
```

## Key Implementation Patterns

### Hierarchy Cache Pattern (WP01, WP04, WP05)
```python
def _build_hierarchy_cache(self) -> Dict[int, Tuple[str, str]]:
    """Build cache mapping ingredient ID to (L0_name, L1_name)."""
    cache = {}
    for ingredient in self.ingredients:
        ing_id = ingredient.get("id")
        ancestors = ingredient_hierarchy_service.get_ancestors(ing_id)
        if len(ancestors) >= 2:
            l0_name = ancestors[1].get("display_name", "--")
            l1_name = ancestors[0].get("display_name", "--")
        elif len(ancestors) == 1:
            l0_name = ancestors[0].get("display_name", "--")
            l1_name = "--"
        else:
            l0_name = "--"
            l1_name = "--"
        cache[ing_id] = (l0_name, l1_name)
    return cache
```

### Cascading Dropdown Pattern (WP03, WP04, WP05)
```python
def _on_l0_filter_change(self, value: str):
    """Handle L0 category selection - populate L1 dropdown."""
    if value == "All Categories":
        self.l1_filter_dropdown.configure(values=["All"], state="disabled")
        self.l1_filter_var.set("All")
        return

    l0_id = self._l0_map[value].get("id")
    subcategories = ingredient_hierarchy_service.get_children(l0_id)
    self._l1_map = {sub.get("display_name"): sub for sub in subcategories}

    if subcategories:
        l1_values = ["All"] + sorted(self._l1_map.keys())
        self.l1_filter_dropdown.configure(values=l1_values, state="normal")
    else:
        self.l1_filter_dropdown.configure(values=["All"], state="disabled")
    self.l1_filter_var.set("All")
    self._apply_filters()
```

### Modal Dialog Pattern (WP03)
```python
def __init__(self, parent, ingredient_id=None, **kwargs):
    super().__init__(parent, **kwargs)

    self.withdraw()  # Hide while building
    self.transient(parent)

    # ... build UI ...

    self.deiconify()
    self.update()
    try:
        self.wait_visibility()
        self.grab_set()
    except Exception:
        if not self.winfo_exists():
            return
    self.lift()
    self.focus_force()
```

### Leaf-Only Validation Pattern (WP07)
```python
def _validate(self) -> bool:
    # ... other validation ...

    ingredient_name = self.ingredient_var.get()
    if ingredient_name in self.ingredients_map:
        ingredient = self.ingredients_map[ingredient_name]
        if ingredient.get("hierarchy_level") != 2:
            errors.append(
                "Only leaf ingredients (L2) can be assigned to products.\n"
                "Please select a specific ingredient, not a category."
            )
```

### Hierarchy Path Display Pattern (WP04)
```python
def _build_hierarchy_path_cache(self):
    """Build cache mapping ingredient_id to hierarchy path string."""
    self._hierarchy_path_cache = {}
    for ingredient in self.ingredients:
        ing_id = ingredient.get("id")
        ancestors = ingredient_hierarchy_service.get_ancestors(ing_id)
        path_parts = [a.get("display_name", "?") for a in reversed(ancestors)]
        path_parts.append(ingredient.get("display_name", "?"))
        self._hierarchy_path_cache[ing_id] = " -> ".join(path_parts)
```

## Output Format

Please output your findings to:
`/Users/kentgale/Vaults-repos/bake-tracker/docs/code-reviews/cursor-F032-review.md`

Use this format:

```markdown
# Cursor Code Review: Feature 032 - Complete F031 Hierarchy UI

**Date:** [DATE]
**Reviewer:** Cursor (AI Code Review)
**Feature:** 032-complete-f031-hierarchy
**Branch:** 032-complete-f031-hierarchy

## Summary

[Brief overview of findings]

## Verification Results

### Module Import Validation
- ingredients_tab.py: [PASS/FAIL]
- products_tab.py: [PASS/FAIL]
- inventory_tab.py: [PASS/FAIL]
- add_product_dialog.py: [PASS/FAIL]
- recipe_form.py: [PASS/FAIL]

### Test Results
- Full test suite: [X passed, Y skipped, Z failed]
- Hierarchy service tests: [X passed, Y failed]

### Code Pattern Validation
- Hierarchy cache pattern: [correct/issues found]
- Cascading dropdown pattern: [correct/issues found]
- Modal dialog pattern: [correct/issues found]
- Leaf-only validation: [correct/issues found]

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
| src/ui/ingredients_tab.py | [status] | [notes] |
| src/ui/products_tab.py | [status] | [notes] |
| src/ui/inventory_tab.py | [status] | [notes] |
| src/ui/forms/add_product_dialog.py | [status] | [notes] |
| src/ui/forms/recipe_form.py | [status] | [notes] |

## Architecture Assessment

### Layered Architecture
[Assessment of UI -> Services -> Models dependency flow]

### Service Usage
[Assessment of proper ingredient_hierarchy_service usage]

### UI Consistency
[Assessment of consistent hierarchy display across tabs]

## Functional Requirements Verification

| Requirement | Status | Evidence |
|-------------|--------|----------|
| FR-001: L0/L1/Name columns in ingredients grid | [PASS/FAIL] | [evidence] |
| FR-002: Sortable hierarchy columns | [PASS/FAIL] | [evidence] |
| FR-003: "--" display for empty levels | [PASS/FAIL] | [evidence] |
| FR-004: Level filter dropdown | [PASS/FAIL] | [evidence] |
| FR-005: Level filter with All/L0/L1/L2 | [PASS/FAIL] | [evidence] |
| FR-006: Search across levels | [PASS/FAIL] | [evidence] |
| FR-007: Clear button resets filters | [PASS/FAIL] | [evidence] |
| FR-008: Ingredient type selector | [PASS/FAIL] | [evidence] |
| FR-009: L0 dropdown from get_root_ingredients | [PASS/FAIL] | [evidence] |
| FR-010: L1 cascading dropdown | [PASS/FAIL] | [evidence] |
| FR-011: Pre-populate on edit | [PASS/FAIL] | [evidence] |
| FR-012: Modal dialog pattern | [PASS/FAIL] | [evidence] |
| FR-013: Hierarchy path in products grid | [PASS/FAIL] | [evidence] |
| FR-014: Cascading hierarchy filters in products | [PASS/FAIL] | [evidence] |
| FR-015: Cascading hierarchy filters in inventory | [PASS/FAIL] | [evidence] |
| FR-016: Hierarchy labels in inventory form | [PASS/FAIL] | [evidence] |
| FR-017: Labels update on ingredient selection | [PASS/FAIL] | [evidence] |
| FR-018: Leaf-only in product form | [PASS/FAIL] | [evidence] |
| FR-019: Leaf-only in recipe form | [PASS/FAIL] | [evidence] |
| FR-020: User-friendly leaf-only error | [PASS/FAIL] | [evidence] |
| FR-021: No category UI elements remain | [PASS/FAIL] | [evidence] |

## Work Package Verification

| Work Package | Status | Notes |
|--------------|--------|-------|
| WP01: Ingredients Grid Columns | [PASS/FAIL] | [notes] |
| WP02: Ingredients Level Filter | [PASS/FAIL] | [notes] |
| WP03: Ingredient Edit Form Hierarchy | [PASS/FAIL] | [notes] |
| WP04: Products Tab Hierarchy | [PASS/FAIL] | [notes] |
| WP05: Inventory Grid Hierarchy | [PASS/FAIL] | [notes] |
| WP06: Inventory Form Hierarchy Display | [PASS/FAIL] | [notes] |
| WP07: Leaf-Only Validation | [PASS/FAIL] | [notes] |
| WP08: Manual Testing & Cleanup | [PASS/FAIL] | [notes] |

## Bug Specification Verification

Reference: `docs/bugs/BUG_F031_incomplete_hierarchy_ui.md`

| Test Case | Status | Notes |
|-----------|--------|-------|
| TC1: Ingredients grid columns | [PASS/FAIL] | [notes] |
| TC2: Level filter | [PASS/FAIL] | [notes] |
| TC3: Edit form cascading dropdowns | [PASS/FAIL] | [notes] |
| TC4: Create L0/L1/L2 | [PASS/FAIL] | [notes] |
| TC5: Products tab hierarchy path | [PASS/FAIL] | [notes] |
| TC6: Products tab hierarchy filter | [PASS/FAIL] | [notes] |
| TC7: Inventory tab hierarchy | [PASS/FAIL] | [notes] |
| TC8: Inventory form hierarchy labels | [PASS/FAIL] | [notes] |
| TC9: Leaf-only validation | [PASS/FAIL] | [notes] |
| TC10: No category UI elements | [PASS/FAIL] | [notes] |

## Deprecated Code Removal

| Component | "Category" References Removed | Notes |
|-----------|-------------------------------|-------|
| ingredients_tab.py grid | [Yes/No] | [notes] |
| ingredients_tab.py filter | [Yes/No] | [notes] |
| products_tab.py grid | [Yes/No] | [notes] |
| products_tab.py filter | [Yes/No] | [notes] |
| inventory_tab.py filter | [Yes/No] | [notes] |
| add_product_dialog.py | [Yes/No] | [notes] |

## Conclusion

[APPROVED / APPROVED WITH CHANGES / NEEDS REVISION]

[Final summary and any recommendations]
```

## Additional Context

- The project uses SQLAlchemy 2.x with type hints
- CustomTkinter for UI
- pytest for testing
- The worktree is isolated from main branch at `.worktrees/032-complete-f031-hierarchy`
- Layered architecture: UI -> Services -> Models -> Database
- This feature uses existing `ingredient_hierarchy_service.py` from F031
- Key service functions: `get_root_ingredients()`, `get_children()`, `get_ancestors()`, `get_leaf_ingredients()`, `get_ingredients_by_level()`
- All existing tests must pass (no regressions)
- This is a UI-only feature - no new service layer code
- The hierarchy is: L0 (Root) -> L1 (Subcategory) -> L2 (Leaf/Ingredient)
- Only L2 (leaf) ingredients can be assigned to products and recipes
- The bug specification `BUG_F031_incomplete_hierarchy_ui.md` defines 10 test cases to verify
