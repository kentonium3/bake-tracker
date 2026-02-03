---
work_package_id: "WP02"
subtasks:
  - "T005"
  - "T006"
  - "T007"
title: "Core CRUD Services - Ingredient & Recipe"
phase: "Phase 2 - Documentation"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
dependencies: ["WP01"]
history:
  - timestamp: "2026-02-03T04:37:19Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP02 – Core CRUD Services - Ingredient & Recipe

## Objectives & Success Criteria

**Goal**: Add transaction boundary documentation to ingredient and recipe service files.

**Success Criteria**:
- [ ] All public functions in `ingredient_service.py` have "Transaction boundary:" section
- [ ] All public functions in `ingredient_crud_service.py` have "Transaction boundary:" section
- [ ] All public functions in `recipe_service.py` have "Transaction boundary:" section
- [ ] Documentation uses consistent templates (Pattern A/B/C)

**Implementation Command**:
```bash
spec-kitty implement WP02 --base WP01
```

**Parallel-Safe**: Yes - assign to Gemini

## Context & Constraints

**References**:
- Templates: `kitty-specs/091-transaction-boundary-documentation/research/docstring_templates.md`
- Inventory: `kitty-specs/091-transaction-boundary-documentation/research/service_inventory.md`
- Constitution: `.kittify/memory/constitution.md` (Principle VI.C.2)

**Key Constraints**:
- Do NOT change function logic - documentation only
- Use EXACT template phrasing for consistency
- Preserve existing Args/Returns/Raises sections - add "Transaction boundary:" after description

## Subtasks & Detailed Guidance

### Subtask T005 – Document ingredient_service.py (~14 functions)

**Purpose**: Add transaction boundary documentation to all public functions.

**Files**:
- Edit: `src/services/ingredient_service.py`

**Functions to document** (classifications from inventory):

| Function | Type | Template |
|----------|------|----------|
| `validate_density_fields` | READ | Pattern A |
| `create_ingredient` | SINGLE | Pattern B |
| `get_ingredient` | READ | Pattern A (already has some docs) |
| `search_ingredients` | READ | Pattern A |
| `update_ingredient` | MULTI | Pattern C (calls hierarchy service) |
| `delete_ingredient` | MULTI | Pattern C (calls check_dependencies) |
| `can_delete_ingredient` | READ | Pattern A |
| `delete_ingredient_safe` | MULTI | Pattern C |
| `check_ingredient_dependencies` | READ | Pattern A |
| `list_ingredients` | READ | Pattern A |
| `get_all_ingredients` | READ | Pattern A |
| `get_distinct_ingredient_categories` | READ | Pattern A |
| `get_all_distinct_categories` | READ | Pattern A |

**Example - Adding to existing docstring**:
```python
def get_ingredient(slug: str, session: Optional[Session] = None) -> Ingredient:
    """
    Retrieve an ingredient by its slug.

    Transaction boundary: Read-only, no transaction needed.
    Safe to call without session - uses temporary session for query.

    Args:
        slug: The unique slug identifier for the ingredient
        session: Optional session (for composition with other operations)

    Returns:
        Ingredient model instance

    Raises:
        IngredientNotFoundBySlug: If no ingredient exists with the given slug
    """
```

**Example - MULTI function (update_ingredient)**:
```python
def update_ingredient(slug: str, updates: dict, session: Optional[Session] = None) -> Ingredient:
    """
    Update an ingredient's attributes.

    Transaction boundary: Multi-step operation if hierarchy changes involved.
    Steps executed atomically:
    1. Retrieve ingredient by slug
    2. Apply updates to ingredient fields
    3. If hierarchy fields changed, update via ingredient_hierarchy_service

    CRITICAL: All nested service calls receive session parameter to ensure
    atomicity. Never create new session_scope() within this function.

    Args:
        slug: The unique slug identifier for the ingredient
        updates: Dictionary of fields to update
        session: Optional session for transactional composition

    Returns:
        Updated Ingredient model instance

    Raises:
        IngredientNotFoundBySlug: If no ingredient exists with the given slug
        ValidationError: If updates contain invalid values
    """
```

**Validation**:
- [ ] All 14 functions have "Transaction boundary:" in docstring
- [ ] grep -c "Transaction boundary:" ingredient_service.py returns 14

---

### Subtask T006 – Document ingredient_crud_service.py (~13 functions)

**Purpose**: Add transaction boundary documentation to all public functions.

**Files**:
- Edit: `src/services/ingredient_crud_service.py`

**Functions to document**:

| Function | Type | Template |
|----------|------|----------|
| `create_ingredient` | SINGLE | Pattern B |
| `get_ingredient` | READ | Pattern A |
| `get_all_ingredients` | READ | Pattern A |
| `update_ingredient` | SINGLE | Pattern B |
| `delete_ingredient` | MULTI | Pattern C (checks dependencies) |
| `update_quantity` | SINGLE | Pattern B |
| `adjust_quantity` | SINGLE | Pattern B |
| `search_ingredients_by_name` | READ | Pattern A |
| `get_ingredients_by_category` | READ | Pattern A |
| `get_low_stock_ingredients` | READ | Pattern A |
| `get_ingredient_count` | READ | Pattern A |
| `get_category_list` | READ | Pattern A |
| `get_total_inventory_value` | READ | Pattern A |

**Validation**:
- [ ] All 13 functions have "Transaction boundary:" in docstring
- [ ] grep -c "Transaction boundary:" ingredient_crud_service.py returns 13

---

### Subtask T007 – Document recipe_service.py (~20+ functions)

**Purpose**: Add transaction boundary documentation to all public functions.

**Files**:
- Edit: `src/services/recipe_service.py`

**Note**: This is a large file (1700+ lines). Focus on PUBLIC functions only (no `_` prefix).

**Functions to document** (common patterns):

| Function Pattern | Type | Template |
|-----------------|------|----------|
| `get_recipe`, `get_recipe_by_*` | READ | Pattern A |
| `list_recipes`, `search_recipes` | READ | Pattern A |
| `create_recipe` | MULTI | Pattern C (creates recipe + components) |
| `update_recipe` | MULTI | Pattern C (updates recipe + components) |
| `delete_recipe` | MULTI | Pattern C (checks dependencies first) |
| `add_component`, `remove_component` | MULTI | Pattern C |
| `get_aggregated_ingredients` | READ | Pattern A |
| `calculate_*` | READ | Pattern A (pure calculation) |
| `validate_*` | READ | Pattern A |

**For MULTI functions, document the steps**:
```python
def create_recipe(recipe_data: dict, session: Optional[Session] = None) -> Recipe:
    """
    Create a new recipe with its components.

    Transaction boundary: ALL operations in single session (atomic).
    Atomicity guarantee: Either ALL steps succeed OR entire operation rolls back.
    Steps executed atomically:
    1. Validate recipe data and component references
    2. Create Recipe record
    3. Create RecipeComponent records for each ingredient/nested recipe
    4. Flush to get IDs for relationships

    CRITICAL: All nested service calls receive session parameter to ensure
    atomicity. Never create new session_scope() within this function.

    Args:
        recipe_data: Dictionary containing recipe name, description, components
        session: Optional session for transactional composition

    Returns:
        Created Recipe model instance with components loaded

    Raises:
        ValidationError: If recipe data is invalid
        IngredientNotFoundBySlug: If component ingredient doesn't exist
        RecipeNotFoundBySlug: If nested recipe doesn't exist
    """
```

**Validation**:
- [ ] All public functions have "Transaction boundary:" in docstring
- [ ] No private functions (`_` prefix) were modified
- [ ] Run grep to count: `grep -c "Transaction boundary:" recipe_service.py`

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Large recipe_service.py | Focus only on public functions |
| Existing partial docs | Preserve and enhance, don't overwrite |
| Template inconsistency | Copy exact phrasing from templates |

## Definition of Done Checklist

- [ ] ingredient_service.py: All 14 public functions documented
- [ ] ingredient_crud_service.py: All 13 public functions documented
- [ ] recipe_service.py: All public functions documented
- [ ] All use consistent template phrasing
- [ ] No functional code changes
- [ ] Tests still pass: `pytest src/tests -v -k "ingredient or recipe"`

## Review Guidance

**Reviewers should verify**:
1. "Transaction boundary:" appears in every public function
2. Classification matches actual behavior (MULTI functions call other services)
3. Template phrasing is consistent
4. Existing functionality unchanged

## Activity Log

- 2026-02-03T04:37:19Z – system – lane=planned – Prompt created.
