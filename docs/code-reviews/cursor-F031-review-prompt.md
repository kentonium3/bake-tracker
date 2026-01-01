# Cursor Code Review Prompt - Feature 031: Ingredient Hierarchy Taxonomy

## Role

You are a senior software engineer performing an independent code review of Feature 031 (ingredient-hierarchy-taxonomy). This feature adds a 3-level hierarchical taxonomy system for ingredients, enabling category-based organization with leaf-only validation for recipes and products.

## Feature Summary

**Core Changes:**
1. Schema/Model: Self-referential FK on Ingredient model with `parent_ingredient_id` and `hierarchy_level` (WP01)
2. Hierarchy Service Core: Functions to query ancestors, descendants, and tree structures (WP02)
3. Hierarchy Service Validation: `is_leaf()`, `validate_hierarchy()`, `move_ingredient()` (WP03)
4. Service Validation Updates: Leaf-only enforcement in recipe, product, and ingredient services (WP04)
5. Tree Widget Component: CustomTkinter tree widget with lazy loading and breadcrumb (WP05)
6. UI Integration: Tree view in ingredients tab, recipe dialog tree selector, parent selection in forms (WP06)
7. Migration Tooling: Export/import scripts with hierarchy validation (WP07)

**Hierarchy Structure:**
- Level 0: Root categories (e.g., "Chocolate", "Flour")
- Level 1: Sub-categories (e.g., "Dark Chocolate", "Bread Flour")
- Level 2: Leaf ingredients (e.g., "Semi-Sweet Chocolate Chips", "King Arthur Bread Flour")

**Key Constraints:**
- Maximum 3 levels (0, 1, 2)
- Only leaf ingredients (level 2) can be used in recipes and products
- Non-leaf selection returns helpful error with suggestions

## Files to Review

### Model Layer - Ingredient Schema (WP01)

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/031-ingredient-hierarchy-taxonomy/src/models/ingredient.py`
  - `parent_ingredient_id` FK (nullable, self-referential)
  - `hierarchy_level` Integer (default=2 for leaf)
  - `parent` relationship (remote_side pattern)
  - `children` relationship (back_populates)
  - `get_ancestors()` method
  - `get_descendants()` method
  - `is_leaf` property

### Service Layer - Hierarchy Core (WP02)

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/031-ingredient-hierarchy-taxonomy/src/services/ingredient_hierarchy_service.py`
  - `get_root_ingredients()` - returns level 0 ingredients
  - `get_children(parent_id)` - returns direct children
  - `get_ancestors(ingredient_id)` - returns path to root
  - `get_descendants(ingredient_id)` - returns all descendants
  - `get_ingredient_tree()` - full tree structure
  - `get_ingredients_by_level(level)` - filter by hierarchy level
  - `get_leaf_ingredients(parent_id)` - leaf descendants
  - `get_ingredient_by_id(ingredient_id)` - single ingredient lookup
  - Session parameter pattern per CLAUDE.md

### Service Layer - Hierarchy Validation (WP03)

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/031-ingredient-hierarchy-taxonomy/src/services/ingredient_hierarchy_service.py`
  - `is_leaf(ingredient_id)` - check if ingredient is selectable
  - `validate_hierarchy(ingredient_id, proposed_parent_id)` - validate move
  - `move_ingredient(ingredient_id, new_parent_id)` - change parent
  - `would_create_cycle(ingredient_id, proposed_parent_id)` - cycle detection
  - `calculate_depth(ingredient_id, new_parent_id)` - depth calculation

### Service Layer - Exceptions (WP03/WP04)

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/031-ingredient-hierarchy-taxonomy/src/services/exceptions.py`
  - `NonLeafIngredientError` exception class
  - `suggestions` attribute with leaf alternatives
  - `HierarchyError` base exception (if added)

### Service Layer - Validation Updates (WP04)

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/031-ingredient-hierarchy-taxonomy/src/services/ingredient_service.py`
  - `create_ingredient()` - validates parent, calculates level
  - `update_ingredient()` - handles parent change via move_ingredient
  - Defaults hierarchy_level=2 for backwards compatibility

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/031-ingredient-hierarchy-taxonomy/src/services/recipe_service.py`
  - `create_recipe()` - enforces leaf-only ingredients
  - `add_ingredient_to_recipe()` - enforces leaf-only
  - `update_recipe()` - enforces leaf-only on ingredient changes
  - Raises `NonLeafIngredientError` with suggestions

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/031-ingredient-hierarchy-taxonomy/src/services/product_service.py`
  - Enforces leaf-only for product-ingredient links
  - Raises `NonLeafIngredientError` with suggestions

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/031-ingredient-hierarchy-taxonomy/src/services/product_catalog_service.py`
  - Enforces leaf-only in catalog operations
  - Handles bulk operations with validation

### UI Layer - Tree Widget (WP05)

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/031-ingredient-hierarchy-taxonomy/src/ui/widgets/ingredient_tree_widget.py`
  - `IngredientTreeWidget` class (ttk.Treeview based)
  - `on_select_callback` parameter
  - `leaf_only` mode for recipe/product selection
  - `show_search` toggle
  - `show_breadcrumb` toggle
  - Lazy loading for performance
  - `search()` and `clear_search()` public methods
  - `refresh()` method

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/031-ingredient-hierarchy-taxonomy/src/ui/widgets/__init__.py`
  - Export of `IngredientTreeWidget`

### UI Layer - Ingredients Tab Integration (WP06)

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/031-ingredient-hierarchy-taxonomy/src/ui/ingredients_tab.py`
  - Flat/Tree view toggle (segmented button)
  - `_create_tree_view()` method
  - `_on_view_change()` handler
  - `_on_hierarchy_tree_select()` callback
  - Search wired to tree widget
  - `IngredientFormDialog` updates:
    - Parent selection dropdown
    - Level display label
    - `_build_parent_options()` helper
    - `_on_parent_change()` handler
    - `parent_ingredient_id` in save result

### UI Layer - Recipe Form Integration (WP06)

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/031-ingredient-hierarchy-taxonomy/src/ui/forms/recipe_form.py`
  - `IngredientSelectionDialog` class (new)
  - Tree widget with `leaf_only=True`
  - `RecipeIngredientRow` updates:
    - Browse button ("...") for tree selection
    - `_selected_ingredient_id` tracking
    - `_browse_ingredients()` method
  - `RecipeFormDialog` updates:
    - Filters `available_ingredients` to leaf-only

### Test Files

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/031-ingredient-hierarchy-taxonomy/src/tests/models/test_ingredient.py`
  - Tests for `parent_ingredient_id` and `hierarchy_level` fields
  - Tests for `get_ancestors()` and `get_descendants()` methods
  - Tests for `is_leaf` property
  - Tests for self-referential relationship

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/031-ingredient-hierarchy-taxonomy/src/tests/services/test_ingredient_hierarchy_service.py`
  - Tests for `get_root_ingredients()`
  - Tests for `get_children()`
  - Tests for `get_ancestors()`
  - Tests for `get_descendants()`
  - Tests for `is_leaf()`
  - Tests for `validate_hierarchy()`
  - Tests for `move_ingredient()`
  - Tests for cycle detection
  - Tests for depth validation

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/031-ingredient-hierarchy-taxonomy/src/tests/services/test_ingredient_service.py`
  - `TestCreateIngredientHierarchy` class
  - `TestUpdateIngredientHierarchy` class
  - Tests for parent validation on create
  - Tests for max depth validation
  - Tests for default leaf level

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/031-ingredient-hierarchy-taxonomy/src/tests/services/test_recipe_service.py`
  - `TestLeafOnlyIngredientValidation` class
  - Tests for create with leaf ingredient (success)
  - Tests for create with non-leaf ingredient (fail)
  - Tests for add ingredient with leaf (success)
  - Tests for add ingredient with non-leaf (fail)
  - Tests for error suggestions

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/031-ingredient-hierarchy-taxonomy/src/tests/services/test_product_catalog_service.py`
  - `TestLeafOnlyProductCatalogValidation` class
  - Tests for create with leaf (success)
  - Tests for create with non-leaf (fail)

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/031-ingredient-hierarchy-taxonomy/src/tests/conftest.py`
  - `hierarchy_ingredients` fixture
  - Creates 4-ingredient hierarchy for testing

### Specification Documents

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/031-ingredient-hierarchy-taxonomy/kitty-specs/031-ingredient-hierarchy-taxonomy/spec.md`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/031-ingredient-hierarchy-taxonomy/kitty-specs/031-ingredient-hierarchy-taxonomy/plan.md`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/031-ingredient-hierarchy-taxonomy/kitty-specs/031-ingredient-hierarchy-taxonomy/data-model.md`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/031-ingredient-hierarchy-taxonomy/kitty-specs/031-ingredient-hierarchy-taxonomy/tasks.md`

## Review Checklist

### 1. Ingredient Model Schema (WP01)

- [ ] `parent_ingredient_id` FK exists (nullable Integer, ForeignKey to ingredients.id)
- [ ] `hierarchy_level` Integer exists with default=2
- [ ] `parent` relationship uses `remote_side=[id]` pattern
- [ ] `children` relationship back_populates `parent`
- [ ] `get_ancestors()` returns list from leaf to root
- [ ] `get_descendants()` returns all children recursively
- [ ] `is_leaf` property returns True when `hierarchy_level == 2`
- [ ] Alembic migration exists (or schema created via create_all)

### 2. Hierarchy Service Core (WP02)

- [ ] `get_root_ingredients()` returns only level 0 ingredients
- [ ] `get_children(parent_id)` returns direct children only
- [ ] `get_ancestors(ingredient_id)` returns correct path
- [ ] `get_descendants(ingredient_id)` returns all descendants
- [ ] `get_ingredient_tree()` returns nested structure
- [ ] `get_ingredients_by_level(level)` filters correctly
- [ ] `get_leaf_ingredients(parent_id)` returns only leaves
- [ ] All functions follow `session=None` pattern per CLAUDE.md

### 3. Hierarchy Validation (WP03)

- [ ] `is_leaf(ingredient_id)` checks hierarchy_level == 2
- [ ] `validate_hierarchy()` checks for cycles
- [ ] `validate_hierarchy()` checks max depth (3 levels)
- [ ] `move_ingredient()` updates parent and recalculates levels
- [ ] `would_create_cycle()` detects circular references
- [ ] `NonLeafIngredientError` includes suggestions

### 4. Service Validation Updates (WP04)

- [ ] `ingredient_service.create_ingredient()` accepts `parent_ingredient_id`
- [ ] `ingredient_service.create_ingredient()` calculates `hierarchy_level` from parent
- [ ] `recipe_service` rejects non-leaf ingredients with `NonLeafIngredientError`
- [ ] `product_service` rejects non-leaf ingredients with `NonLeafIngredientError`
- [ ] `product_catalog_service` rejects non-leaf ingredients
- [ ] Error messages include top 3 leaf suggestions

### 5. Tree Widget Component (WP05)

- [ ] `IngredientTreeWidget` class exists
- [ ] Constructor accepts `on_select_callback`, `leaf_only`, `show_search`, `show_breadcrumb`
- [ ] Tree uses ttk.Treeview with expand/collapse
- [ ] `leaf_only=True` prevents selection of non-leaves
- [ ] Lazy loading implemented (children loaded on expand)
- [ ] `search()` method highlights matching items
- [ ] `clear_search()` resets highlight state
- [ ] `refresh()` reloads tree data
- [ ] Breadcrumb displays ancestor path

### 6. UI Integration (WP06)

- [ ] Ingredients tab has Flat/Tree view toggle
- [ ] Tree view shows hierarchical ingredient list
- [ ] Tree selection triggers detail display
- [ ] Search works in both flat and tree modes
- [ ] `IngredientFormDialog` has parent dropdown
- [ ] Parent dropdown shows level 0 and 1 ingredients
- [ ] Level label updates when parent changes
- [ ] Save includes `parent_ingredient_id` in result
- [ ] `IngredientSelectionDialog` exists in recipe_form.py
- [ ] Recipe ingredient row has Browse button
- [ ] Recipe form filters to leaf ingredients only

### 7. Test Coverage

- [ ] Model tests cover hierarchy fields and methods
- [ ] Hierarchy service tests cover all public functions
- [ ] Ingredient service tests cover hierarchy validation
- [ ] Recipe service tests cover leaf-only enforcement
- [ ] Product catalog tests cover leaf-only enforcement
- [ ] `hierarchy_ingredients` fixture provides test data

## Verification Commands

Run these commands to verify the implementation:

```bash
cd /Users/kentgale/Vaults-repos/bake-tracker/.worktrees/031-ingredient-hierarchy-taxonomy

# Activate virtual environment
source /Users/kentgale/Vaults-repos/bake-tracker/venv/bin/activate

# Verify model has hierarchy fields
python3 -c "
from src.models.ingredient import Ingredient
print('Checking Ingredient model fields...')
ing = Ingredient(name='Test', slug='test', display_name='Test', category='Test')
print(f'  parent_ingredient_id attr: {hasattr(ing, \"parent_ingredient_id\")}')
print(f'  hierarchy_level attr: {hasattr(ing, \"hierarchy_level\")}')
print(f'  parent relationship: {hasattr(ing, \"parent\")}')
print(f'  children relationship: {hasattr(ing, \"children\")}')
print(f'  is_leaf property: {hasattr(type(ing), \"is_leaf\")}')
print(f'  get_ancestors method: {hasattr(ing, \"get_ancestors\")}')
print(f'  get_descendants method: {hasattr(ing, \"get_descendants\")}')
print('Model check complete')
"

# Verify hierarchy service functions
python3 -c "
from src.services import ingredient_hierarchy_service
print('Checking ingredient_hierarchy_service functions...')
funcs = ['get_root_ingredients', 'get_children', 'get_ancestors', 'get_descendants',
         'get_ingredient_tree', 'get_ingredients_by_level', 'get_leaf_ingredients',
         'is_leaf', 'validate_hierarchy', 'move_ingredient', 'get_ingredient_by_id']
for f in funcs:
    print(f'  {f}: {hasattr(ingredient_hierarchy_service, f)}')
print('Service check complete')
"

# Verify NonLeafIngredientError exception
python3 -c "
from src.services.exceptions import NonLeafIngredientError
print('Checking NonLeafIngredientError...')
err = NonLeafIngredientError('Test Category', [{'display_name': 'Suggestion 1'}])
print(f'  Has suggestions attr: {hasattr(err, \"suggestions\")}')
print(f'  Message: {str(err)[:60]}...')
print('Exception check complete')
"

# Verify UI widgets
python3 -c "
from src.ui.widgets.ingredient_tree_widget import IngredientTreeWidget
print('IngredientTreeWidget imported successfully')
from src.ui.forms.recipe_form import IngredientSelectionDialog, RecipeIngredientRow
print('IngredientSelectionDialog imported successfully')
print('RecipeIngredientRow imported successfully')
"

# Verify session parameter pattern in hierarchy service
grep -n "session.*=.*None" src/services/ingredient_hierarchy_service.py | head -10

# Run hierarchy service tests
PYTHONPATH=. python3 -m pytest src/tests/services/test_ingredient_hierarchy_service.py -v --tb=short

# Run ingredient service hierarchy tests
PYTHONPATH=. python3 -m pytest src/tests/services/test_ingredient_service.py::TestCreateIngredientHierarchy -v --tb=short
PYTHONPATH=. python3 -m pytest src/tests/services/test_ingredient_service.py::TestUpdateIngredientHierarchy -v --tb=short

# Run recipe service leaf-only tests
PYTHONPATH=. python3 -m pytest src/tests/services/test_recipe_service.py::TestLeafOnlyIngredientValidation -v --tb=short

# Run product catalog leaf-only tests
PYTHONPATH=. python3 -m pytest src/tests/services/test_product_catalog_service.py::TestLeafOnlyProductCatalogValidation -v --tb=short

# Run model tests
PYTHONPATH=. python3 -m pytest src/tests/models/test_ingredient.py -v --tb=short

# Run ALL tests to verify no regressions
PYTHONPATH=. python3 -m pytest src/tests -v --tb=short 2>&1 | tail -50

# Check test coverage for hierarchy service
PYTHONPATH=. python3 -m pytest src/tests/services/test_ingredient_hierarchy_service.py -v --cov=src.services.ingredient_hierarchy_service --cov-report=term-missing
```

## Key Implementation Patterns

### Self-Referential Relationship Pattern
```python
class Ingredient(BaseModel):
    parent_ingredient_id = Column(Integer, ForeignKey("ingredients.id"), nullable=True)
    hierarchy_level = Column(Integer, default=2)  # 0=root, 1=mid, 2=leaf

    parent = relationship(
        "Ingredient",
        remote_side=[id],
        back_populates="children",
    )
    children = relationship(
        "Ingredient",
        back_populates="parent",
    )
```

### NonLeafIngredientError Pattern
```python
class NonLeafIngredientError(Exception):
    def __init__(self, ingredient_name: str, suggestions: List[Dict]):
        self.ingredient_name = ingredient_name
        self.suggestions = suggestions
        suggestion_names = [s.get("display_name", "Unknown") for s in suggestions[:3]]
        super().__init__(
            f"Cannot use category '{ingredient_name}' directly. "
            f"Please select a specific ingredient. Suggestions: {', '.join(suggestion_names)}"
        )
```

### Session Parameter Pattern (per CLAUDE.md)
```python
def get_children(parent_id: int, session: Session = None) -> List[Dict]:
    if session is not None:
        return _get_children_impl(parent_id, session)
    with session_scope() as session:
        return _get_children_impl(parent_id, session)
```

### Leaf-Only Validation Pattern
```python
from src.services import ingredient_hierarchy_service
from src.services.exceptions import NonLeafIngredientError

if not ingredient_hierarchy_service.is_leaf(ingredient_id, session=session):
    suggestions = ingredient_hierarchy_service.get_leaf_ingredients(
        parent_id=ingredient_id, session=session
    )[:3]
    raise NonLeafIngredientError(ingredient.display_name, suggestions)
```

## Output Format

Please output your findings to:
`/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/031-ingredient-hierarchy-taxonomy/docs/code-reviews/cursor-F031-review.md`

Use this format:

```markdown
# Cursor Code Review: Feature 031 - Ingredient Hierarchy Taxonomy

**Date:** [DATE]
**Reviewer:** Cursor (AI Code Review)
**Feature:** 031-ingredient-hierarchy-taxonomy
**Branch:** 031-ingredient-hierarchy-taxonomy

## Summary

[Brief overview of findings]

## Verification Results

### Module/Import Validation
- ingredient.py (model): [PASS/FAIL]
- ingredient_hierarchy_service.py: [PASS/FAIL]
- ingredient_service.py (hierarchy updates): [PASS/FAIL]
- recipe_service.py (leaf-only validation): [PASS/FAIL]
- product_service.py (leaf-only validation): [PASS/FAIL]
- product_catalog_service.py (leaf-only validation): [PASS/FAIL]
- exceptions.py (NonLeafIngredientError): [PASS/FAIL]
- ingredient_tree_widget.py: [PASS/FAIL]
- ingredients_tab.py (UI integration): [PASS/FAIL]
- recipe_form.py (tree selector): [PASS/FAIL]

### Test Results
- Full test suite: [X passed, Y skipped, Z failed]
- Hierarchy service tests: [X passed, Y failed]
- Ingredient service hierarchy tests: [X passed, Y failed]
- Recipe service leaf-only tests: [X passed, Y failed]
- Product catalog leaf-only tests: [X passed, Y failed]
- Model tests: [X passed, Y failed]

### Code Pattern Validation
- Self-referential FK: [correct/issues found]
- Session parameter pattern: [present/missing in which files]
- NonLeafIngredientError usage: [correct/issues found]
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
| src/models/ingredient.py | [status] | [notes] |
| src/services/ingredient_hierarchy_service.py | [status] | [notes] |
| src/services/ingredient_service.py | [status] | [notes] |
| src/services/recipe_service.py | [status] | [notes] |
| src/services/product_service.py | [status] | [notes] |
| src/services/product_catalog_service.py | [status] | [notes] |
| src/services/exceptions.py | [status] | [notes] |
| src/ui/widgets/ingredient_tree_widget.py | [status] | [notes] |
| src/ui/ingredients_tab.py | [status] | [notes] |
| src/ui/forms/recipe_form.py | [status] | [notes] |
| src/tests/services/test_ingredient_hierarchy_service.py | [status] | [notes] |
| src/tests/services/test_ingredient_service.py | [status] | [notes] |
| src/tests/services/test_recipe_service.py | [status] | [notes] |
| src/tests/services/test_product_catalog_service.py | [status] | [notes] |
| src/tests/models/test_ingredient.py | [status] | [notes] |
| src/tests/conftest.py | [status] | [notes] |

## Architecture Assessment

### Layered Architecture
[Assessment of UI -> Services -> Models dependency flow]

### Session Management
[Assessment of session=None parameter pattern per CLAUDE.md]

### Self-Referential Design
[Assessment of parent/children relationship implementation]

### Validation Strategy
[Assessment of leaf-only enforcement across services]

## Functional Requirements Verification

| Requirement | Status | Evidence |
|-------------|--------|----------|
| FR-001: 3-level hierarchy (0, 1, 2) | [PASS/FAIL] | [evidence] |
| FR-002: Self-referential FK | [PASS/FAIL] | [evidence] |
| FR-003: get_root_ingredients() | [PASS/FAIL] | [evidence] |
| FR-004: get_children(parent_id) | [PASS/FAIL] | [evidence] |
| FR-005: get_ancestors(id) | [PASS/FAIL] | [evidence] |
| FR-006: get_descendants(id) | [PASS/FAIL] | [evidence] |
| FR-007: is_leaf(id) check | [PASS/FAIL] | [evidence] |
| FR-008: validate_hierarchy() | [PASS/FAIL] | [evidence] |
| FR-009: move_ingredient() | [PASS/FAIL] | [evidence] |
| FR-010: Cycle detection | [PASS/FAIL] | [evidence] |
| FR-011: Max depth validation | [PASS/FAIL] | [evidence] |
| FR-012: Recipe leaf-only | [PASS/FAIL] | [evidence] |
| FR-013: Product leaf-only | [PASS/FAIL] | [evidence] |
| FR-014: Error suggestions | [PASS/FAIL] | [evidence] |
| FR-015: Tree widget | [PASS/FAIL] | [evidence] |
| FR-016: Lazy loading | [PASS/FAIL] | [evidence] |
| FR-017: Breadcrumb display | [PASS/FAIL] | [evidence] |
| FR-018: View toggle (Flat/Tree) | [PASS/FAIL] | [evidence] |
| FR-019: Parent selection in forms | [PASS/FAIL] | [evidence] |
| FR-020: Recipe tree selector | [PASS/FAIL] | [evidence] |

## Work Package Verification

| Work Package | Status | Notes |
|--------------|--------|-------|
| WP01: Schema/Model Foundation | [PASS/FAIL] | [notes] |
| WP02: Hierarchy Service Core | [PASS/FAIL] | [notes] |
| WP03: Hierarchy Validation | [PASS/FAIL] | [notes] |
| WP04: Service Validation Updates | [PASS/FAIL] | [notes] |
| WP05: Tree Widget Component | [PASS/FAIL] | [notes] |
| WP06: UI Integration | [PASS/FAIL] | [notes] |
| WP07: Migration Tooling | [PASS/FAIL] | [notes] |

## Test Coverage Assessment

| Test File | Tests | Coverage | Notes |
|-----------|-------|----------|-------|
| test_ingredient_hierarchy_service.py | [count] | [%] | [notes] |
| test_ingredient_service.py (hierarchy) | [count] | [%] | [notes] |
| test_recipe_service.py (leaf-only) | [count] | [%] | [notes] |
| test_product_catalog_service.py (leaf-only) | [count] | [%] | [notes] |
| test_ingredient.py (model) | [count] | [%] | [notes] |

## Conclusion

[APPROVED / APPROVED WITH CHANGES / NEEDS REVISION]

[Final summary and any recommendations]
```

## Additional Context

- The project uses SQLAlchemy 2.x with type hints
- CustomTkinter for UI with ttk.Treeview for tree widget
- pytest for testing with pytest-cov for coverage
- The worktree is isolated from main branch at `.worktrees/031-ingredient-hierarchy-taxonomy`
- Layered architecture: UI -> Services -> Models -> Database
- Session management pattern: functions accept `session=None` per CLAUDE.md
- 70%+ coverage target for service layer
- All existing tests must pass (no regressions)
- Pre-existing test failures exist in recipe_service tests (category validation issues, not hierarchy-related)
- Feature was implemented using multi-agent orchestration:
  - Claude Code handled most work packages
  - Gemini CLI assisted with WP05 (tree widget) and WP07 (migration tooling)
- Hierarchy defaults: new ingredients without parent are level 2 (leaf) for backwards compatibility
- Maximum 3 hierarchy levels enforced (0, 1, 2)
