---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
title: "Update Service Primitive Docstrings"
phase: "Phase 1 - Foundation"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
dependencies: []
history:
  - timestamp: "2026-01-25T03:23:15Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 – Update Service Primitive Docstrings

## Objectives & Success Criteria

**Goal**: Update docstrings for `get_finished_units()` and `get_base_yield_structure()` in recipe_service.py to accurately reflect post-Phase-1-fix behavior.

**Success Criteria**:
- [ ] `get_finished_units()` docstring no longer mentions NULL yield fields for variants
- [ ] `get_base_yield_structure()` docstring clarifies when to use it vs `get_finished_units()`
- [ ] Both docstrings accurately describe that variants have copied yield values
- [ ] No functional code changes - docstrings only

**Implementation Command**:
```bash
spec-kitty implement WP01
```

## Context & Constraints

**Background**:
Phase 1 of F066 fixed a critical bug where variant FinishedUnits were created with NULL yield fields. The fix copies `items_per_batch` and `item_unit` from the base recipe's FinishedUnits when creating variants.

The service primitives were implemented correctly but their docstrings were written assuming the old (buggy) NULL behavior. These docstrings now mislead developers about variant yield behavior.

**Key Documents**:
- Spec: `kitty-specs/066-recipe-variant-yield-remediation/spec.md`
- Plan: `kitty-specs/066-recipe-variant-yield-remediation/plan.md`
- Research: `kitty-specs/066-recipe-variant-yield-remediation/research.md`

**File to Update**: `src/services/recipe_service.py`

## Subtasks & Detailed Guidance

### Subtask T001 – Update `get_finished_units()` Docstring

**Purpose**: Remove misleading references to NULL yield fields for variants.

**Current Docstring Location**: `src/services/recipe_service.py` lines 2019-2054

**Current Problematic Text**:
```python
"""
Get a recipe's own FinishedUnits (not inherited from base).

Use this primitive to access a recipe's display-level FinishedUnit data,
such as display_name. For variants, this returns the variant's FinishedUnits
which have NULL yield fields - use get_base_yield_structure() for yields.
...
Returns:
    ...
    - items_per_batch: Optional[int] - NULL for variants
    - item_unit: Optional[str] - NULL for variants
...
"""
```

**Required Changes**:
1. Remove "which have NULL yield fields" from the description
2. Update return value descriptions to remove "NULL for variants"
3. Clarify that variants now have copied yield values from base
4. Explain when to use this function (display-level data, recipe's own FUs)

**Updated Docstring**:
```python
"""
Get a recipe's own FinishedUnits.

Use this primitive to access a recipe's FinishedUnit data including display_name
and yield values. For both base and variant recipes, this returns the recipe's
own FinishedUnits. Variants have yield values copied from their base recipe
at creation time.

Args:
    recipe_id: Recipe ID
    session: Optional SQLAlchemy session for transaction sharing.
             If not provided, creates its own session scope.

Returns:
    List of FinishedUnit dicts with keys:
    - id: int - FinishedUnit ID
    - slug: str - FinishedUnit slug
    - display_name: str - Display name
    - items_per_batch: int - Items produced per batch (copied from base for variants)
    - item_unit: str - Unit name (e.g., "cookie") (copied from base for variants)
    - yield_mode: str - "discrete_count" or "batch_portion"

Raises:
    RecipeNotFound: If recipe_id does not exist

Example:
    >>> # Get recipe's FinishedUnits (works for both base and variant):
    >>> fus = get_finished_units(recipe_id, session=session)
    >>> for fu in fus:
    ...     print(f"{fu['display_name']}: {fu['items_per_batch']} {fu['item_unit']}")
    Raspberry Cookie: 24 cookies
"""
```

**Files**: `src/services/recipe_service.py` (lines ~2019-2054)

---

### Subtask T002 – Update `get_base_yield_structure()` Docstring

**Purpose**: Clarify when to use this function vs `get_finished_units()`.

**Current Docstring Location**: `src/services/recipe_service.py` lines 1941-1987

**Current Text Analysis**:
The current docstring is mostly correct but could be clearer about:
1. When to use this vs `get_finished_units()`
2. That this function resolves to base recipe for variants
3. The relationship to Phase 1 fix

**Required Changes**:
1. Add clarification about when to use this function
2. Emphasize that for variants, this returns BASE recipe's FU data (not variant's)
3. Contrast with `get_finished_units()` which returns the recipe's own FUs

**Updated Docstring**:
```python
"""
Get yield structure from base recipe (resolves variants to their base).

Use this primitive when you need the ORIGINAL yield specifications from a
base recipe, even when given a variant recipe ID. This is useful for:
- Displaying "inherited from base" yield values
- Understanding the source of yield values for variants
- Comparing variant's yield display_name with base's structure

For variants: Returns the BASE recipe's FinishedUnit data (slug, display_name,
items_per_batch, item_unit from the parent recipe).

For base recipes: Returns the recipe's own FinishedUnit data (same as
get_finished_units()).

Note: Since Phase 1 fix (F066), variants have yield values copied at creation.
Use get_finished_units() to access a recipe's own FU data (including copied
yields for variants). Use get_base_yield_structure() when you specifically
need to reference the base recipe's original yield data.

Args:
    recipe_id: Recipe ID (can be base or variant recipe)
    session: Optional SQLAlchemy session for transaction sharing.
             If not provided, creates its own session scope.

Returns:
    List of yield dicts with keys:
    - slug: str - FinishedUnit slug (from base recipe)
    - display_name: str - FinishedUnit display name (from base recipe)
    - items_per_batch: int - Items produced per batch
    - item_unit: str - Unit name (e.g., "cookie")

Raises:
    RecipeNotFound: If recipe_id does not exist

Example:
    >>> # For a variant, get the base recipe's original yield structure:
    >>> base_yields = get_base_yield_structure(variant_id, session=session)
    >>> for y in base_yields:
    ...     print(f"Base defines: {y['display_name']} - {y['items_per_batch']} {y['item_unit']}")
    Base defines: Thumbprint Cookie - 24 cookies

    >>> # Compare with variant's own FUs:
    >>> variant_fus = get_finished_units(variant_id, session=session)
    >>> for fu in variant_fus:
    ...     print(f"Variant shows: {fu['display_name']} - {fu['items_per_batch']} {fu['item_unit']}")
    Variant shows: Raspberry Thumbprint - 24 cookies  # display_name differs, yields same
"""
```

**Files**: `src/services/recipe_service.py` (lines ~1941-1987)

## Test Strategy

**No new tests required** - this WP only updates docstrings.

**Verification**:
1. Run existing tests to ensure no regressions: `./run-tests.sh src/tests/test_recipe_yield_primitives.py -v`
2. Review docstrings for accuracy against actual behavior
3. Verify no functional changes were accidentally made

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Docstrings still unclear | Have another developer review for clarity |
| Accidentally modify code | Diff carefully before committing - only docstring changes |

## Definition of Done Checklist

- [ ] T001: `get_finished_units()` docstring updated
- [ ] T002: `get_base_yield_structure()` docstring updated
- [ ] All existing tests pass
- [ ] No functional code changes (docstrings only)
- [ ] Changes committed with clear message

## Review Guidance

- Verify only docstrings were changed (no functional code)
- Verify docstrings accurately describe post-Phase-1 behavior
- Verify examples in docstrings are correct
- Check that the contrast between the two functions is clear

## Activity Log

- 2026-01-25T03:23:15Z – system – lane=planned – Prompt created.
