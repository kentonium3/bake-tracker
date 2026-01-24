---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
  - "T003"
  - "T004"
  - "T005"
title: "Service Primitives"
phase: "Phase 1 - Foundation"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
dependencies: []
history:
  - timestamp: "2025-01-24T07:30:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 – Service Primitives

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you understand the feedback, update `review_status: acknowledged`.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Implementation Command

```bash
spec-kitty implement WP01
```

No dependencies - this is the foundation work package.

---

## Objectives & Success Criteria

Implement two service primitives in `recipe_service.py` that provide transparent yield access for both base and variant recipes. These primitives abstract the base/variant distinction so consuming services don't need variant-specific logic.

**Success Criteria**:
- [ ] `get_base_yield_structure(recipe_id, session=None)` returns base recipe yields for any recipe
- [ ] `get_finished_units(recipe_id, session=None)` returns a recipe's own FinishedUnits
- [ ] Both primitives follow the `session=None` pattern per CLAUDE.md
- [ ] Unit tests cover: base recipe, variant recipe, recipe with no FinishedUnits
- [ ] Comprehensive docstrings explain usage patterns

---

## Context & Constraints

**References**:
- Plan: `kitty-specs/063-variant-yield-inheritance/plan.md`
- Data Model: `kitty-specs/063-variant-yield-inheritance/data-model.md` (contracts)
- Spec: `kitty-specs/063-variant-yield-inheritance/spec.md` (FR-001, FR-002)
- CLAUDE.md: Session management pattern

**Architectural Constraints**:
- Functions go in `src/services/recipe_service.py` (add to Recipe Variant Management section)
- Follow existing session pattern: accept `session=None`, use `session_scope()` if not provided
- Return `List[Dict]` (not ORM objects) to avoid session detachment issues
- Use existing `Recipe.base_recipe_id` relationship

**Key Pattern** (from existing code):
```python
def get_recipe_variants(base_recipe_id: int, session=None) -> list:
    if session is not None:
        return _get_recipe_variants_impl(base_recipe_id, session)

    try:
        with session_scope() as session:
            return _get_recipe_variants_impl(base_recipe_id, session)
    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to get variants for recipe {base_recipe_id}", e)
```

---

## Subtasks & Detailed Guidance

### Subtask T001 – Implement `get_base_yield_structure(recipe_id, session=None)`

**Purpose**: Return yield specifications from the base recipe. For base recipes, return own yields. For variants, return base recipe's yields.

**Steps**:
1. Add function signature after the existing variant functions (~line 1930):
   ```python
   def get_base_yield_structure(
       recipe_id: int,
       session: Optional[Session] = None
   ) -> List[Dict]:
   ```

2. Implement the session pattern wrapper:
   ```python
   if session is not None:
       return _get_base_yield_structure_impl(recipe_id, session)

   try:
       with session_scope() as session:
           return _get_base_yield_structure_impl(recipe_id, session)
   except SQLAlchemyError as e:
       raise DatabaseError(f"Failed to get yield structure for recipe {recipe_id}", e)
   ```

3. Implement `_get_base_yield_structure_impl(recipe_id, session)`:
   ```python
   def _get_base_yield_structure_impl(recipe_id: int, session) -> List[Dict]:
       # Load recipe
       recipe = session.query(Recipe).filter_by(id=recipe_id).first()
       if not recipe:
           raise RecipeNotFound(recipe_id)

       # Resolve to base recipe if variant
       resolved_id = recipe.base_recipe_id if recipe.base_recipe_id else recipe_id

       # Query FinishedUnits for resolved recipe
       finished_units = (
           session.query(FinishedUnit)
           .filter_by(recipe_id=resolved_id)
           .all()
       )

       # Return as list of dicts
       return [
           {
               "slug": fu.slug,
               "display_name": fu.display_name,
               "items_per_batch": fu.items_per_batch,
               "item_unit": fu.item_unit,
           }
           for fu in finished_units
       ]
   ```

**Files**:
- `src/services/recipe_service.py` (modify, ~50 lines added)

**Validation**:
- [ ] Base recipe returns its own FinishedUnit yields
- [ ] Variant recipe returns base recipe's FinishedUnit yields
- [ ] Recipe with no FinishedUnits returns empty list
- [ ] Non-existent recipe_id raises RecipeNotFound

---

### Subtask T002 – Implement `get_finished_units(recipe_id, session=None)`

**Purpose**: Return a recipe's own FinishedUnits (not inherited). This is for accessing display_name and other recipe-specific FinishedUnit data.

**Steps**:
1. Add function signature after `get_base_yield_structure`:
   ```python
   def get_finished_units(
       recipe_id: int,
       session: Optional[Session] = None
   ) -> List[Dict]:
   ```

2. Implement the session pattern wrapper (same pattern as T001)

3. Implement `_get_finished_units_impl(recipe_id, session)`:
   ```python
   def _get_finished_units_impl(recipe_id: int, session) -> List[Dict]:
       # Verify recipe exists
       recipe = session.query(Recipe).filter_by(id=recipe_id).first()
       if not recipe:
           raise RecipeNotFound(recipe_id)

       # Query this recipe's FinishedUnits (not resolved to base)
       finished_units = (
           session.query(FinishedUnit)
           .filter_by(recipe_id=recipe_id)
           .all()
       )

       # Return as list of dicts with all relevant fields
       return [
           {
               "id": fu.id,
               "slug": fu.slug,
               "display_name": fu.display_name,
               "items_per_batch": fu.items_per_batch,
               "item_unit": fu.item_unit,
               "yield_mode": fu.yield_mode.value if fu.yield_mode else None,
           }
           for fu in finished_units
       ]
   ```

**Files**:
- `src/services/recipe_service.py` (modify, ~40 lines added)

**Validation**:
- [ ] Returns recipe's own FinishedUnits (not base)
- [ ] Variant recipe returns variant's FinishedUnits (with NULL yield fields)
- [ ] Recipe with no FinishedUnits returns empty list
- [ ] Non-existent recipe_id raises RecipeNotFound

---

### Subtask T003 – Add unit tests for `get_base_yield_structure`

**Purpose**: Verify the primitive works correctly for base recipes, variant recipes, and edge cases.

**Steps**:
1. Create or extend test file: `src/tests/test_recipe_service.py` (or create `test_recipe_yield_primitives.py`)

2. Add test fixtures:
   ```python
   @pytest.fixture
   def base_recipe_with_fu(session):
       """Create a base recipe with a FinishedUnit."""
       recipe = Recipe(name="Plain Cookie", category="Cookies")
       session.add(recipe)
       session.flush()

       fu = FinishedUnit(
           recipe_id=recipe.id,
           slug="plain-cookie",
           display_name="Plain Cookie",
           items_per_batch=24,
           item_unit="cookie",
           yield_mode=YieldMode.DISCRETE_COUNT,
       )
       session.add(fu)
       session.flush()
       return recipe, fu

   @pytest.fixture
   def variant_recipe(session, base_recipe_with_fu):
       """Create a variant recipe with NULL yield FinishedUnit."""
       base, base_fu = base_recipe_with_fu
       variant = Recipe(
           name="Raspberry Cookie",
           category="Cookies",
           base_recipe_id=base.id,
           variant_name="Raspberry",
       )
       session.add(variant)
       session.flush()

       variant_fu = FinishedUnit(
           recipe_id=variant.id,
           slug="raspberry-cookie",
           display_name="Raspberry Cookie",
           items_per_batch=None,
           item_unit=None,
           yield_mode=YieldMode.DISCRETE_COUNT,
       )
       session.add(variant_fu)
       session.flush()
       return variant, variant_fu
   ```

3. Add tests:
   ```python
   def test_get_base_yield_structure_base_recipe(session, base_recipe_with_fu):
       """Base recipe returns its own yields."""
       recipe, fu = base_recipe_with_fu
       result = get_base_yield_structure(recipe.id, session=session)
       assert len(result) == 1
       assert result[0]["items_per_batch"] == 24
       assert result[0]["item_unit"] == "cookie"

   def test_get_base_yield_structure_variant_recipe(session, variant_recipe, base_recipe_with_fu):
       """Variant recipe returns base recipe's yields."""
       variant, _ = variant_recipe
       base, _ = base_recipe_with_fu
       result = get_base_yield_structure(variant.id, session=session)
       assert len(result) == 1
       assert result[0]["items_per_batch"] == 24  # From base
       assert result[0]["item_unit"] == "cookie"  # From base

   def test_get_base_yield_structure_no_finished_units(session):
       """Recipe with no FinishedUnits returns empty list."""
       recipe = Recipe(name="No FU Recipe", category="Test")
       session.add(recipe)
       session.flush()
       result = get_base_yield_structure(recipe.id, session=session)
       assert result == []

   def test_get_base_yield_structure_not_found(session):
       """Non-existent recipe raises RecipeNotFound."""
       with pytest.raises(RecipeNotFound):
           get_base_yield_structure(99999, session=session)
   ```

**Files**:
- `src/tests/test_recipe_service.py` or `src/tests/test_recipe_yield_primitives.py` (new/modify, ~80 lines)

**Validation**:
- [ ] All test cases pass
- [ ] Tests cover: base recipe, variant recipe, no FU, not found

---

### Subtask T004 – Add unit tests for `get_finished_units`

**Purpose**: Verify the primitive returns recipe's own FinishedUnits correctly.

**Steps**:
1. Add tests in same file as T003:
   ```python
   def test_get_finished_units_base_recipe(session, base_recipe_with_fu):
       """Base recipe returns its own FinishedUnits with yields."""
       recipe, fu = base_recipe_with_fu
       result = get_finished_units(recipe.id, session=session)
       assert len(result) == 1
       assert result[0]["display_name"] == "Plain Cookie"
       assert result[0]["items_per_batch"] == 24

   def test_get_finished_units_variant_recipe(session, variant_recipe):
       """Variant recipe returns its own FinishedUnits with NULL yields."""
       variant, fu = variant_recipe
       result = get_finished_units(variant.id, session=session)
       assert len(result) == 1
       assert result[0]["display_name"] == "Raspberry Cookie"
       assert result[0]["items_per_batch"] is None  # NULL for variants
       assert result[0]["item_unit"] is None

   def test_get_finished_units_not_found(session):
       """Non-existent recipe raises RecipeNotFound."""
       with pytest.raises(RecipeNotFound):
           get_finished_units(99999, session=session)
   ```

**Files**:
- `src/tests/test_recipe_service.py` or `src/tests/test_recipe_yield_primitives.py` (modify, ~40 lines)

**Validation**:
- [ ] All test cases pass
- [ ] Tests verify variant returns NULL yields (not base yields)

---

### Subtask T005 – Add comprehensive docstrings with usage examples

**Purpose**: Document the primitives with clear usage patterns for consuming services.

**Steps**:
1. Update `get_base_yield_structure` docstring:
   ```python
   def get_base_yield_structure(
       recipe_id: int,
       session: Optional[Session] = None
   ) -> List[Dict]:
       """
       Get yield structure for a recipe, resolving to base recipe if variant.

       This primitive abstracts the base/variant distinction. Services performing
       batch calculations should use this function instead of accessing FinishedUnit
       yields directly. This ensures variants inherit yield specifications from
       their base recipe transparently.

       Args:
           recipe_id: Recipe ID (can be base or variant recipe)
           session: Optional SQLAlchemy session for transaction sharing.
                    If not provided, creates its own session scope.

       Returns:
           List of yield dicts with keys:
           - slug: str - FinishedUnit slug
           - display_name: str - FinishedUnit display name (from base)
           - items_per_batch: Optional[int] - Items produced per batch
           - item_unit: Optional[str] - Unit name (e.g., "cookie")

       Raises:
           RecipeNotFound: If recipe_id does not exist

       Example:
           >>> # For batch calculations, use this primitive:
           >>> yields = get_base_yield_structure(recipe_id, session=session)
           >>> for y in yields:
           ...     items_needed = target_quantity / y["items_per_batch"]

           >>> # Works identically for base and variant recipes:
           >>> get_base_yield_structure(base_id)    # Returns base yields
           >>> get_base_yield_structure(variant_id) # Returns same base yields
       """
   ```

2. Update `get_finished_units` docstring:
   ```python
   def get_finished_units(
       recipe_id: int,
       session: Optional[Session] = None
   ) -> List[Dict]:
       """
       Get a recipe's own FinishedUnits (not inherited from base).

       Use this primitive to access a recipe's display-level FinishedUnit data,
       such as display_name. For variants, this returns the variant's FinishedUnits
       which have NULL yield fields - use get_base_yield_structure() for yields.

       Args:
           recipe_id: Recipe ID
           session: Optional SQLAlchemy session for transaction sharing.
                    If not provided, creates its own session scope.

       Returns:
           List of FinishedUnit dicts with keys:
           - id: int - FinishedUnit ID
           - slug: str - FinishedUnit slug
           - display_name: str - Display name
           - items_per_batch: Optional[int] - NULL for variants
           - item_unit: Optional[str] - NULL for variants
           - yield_mode: str - "discrete_count" or "batch_portion"

       Raises:
           RecipeNotFound: If recipe_id does not exist

       Example:
           >>> # To display variant's FinishedUnit name with base yield:
           >>> variant_fus = get_finished_units(variant_id, session=session)
           >>> base_yields = get_base_yield_structure(variant_id, session=session)
           >>> for fu, y in zip(variant_fus, base_yields):
           ...     print(f"{fu['display_name']}: {y['items_per_batch']} {y['item_unit']}")
           Raspberry Cookie: 24 cookies
       """
   ```

**Files**:
- `src/services/recipe_service.py` (modify docstrings)

**Validation**:
- [ ] Docstrings explain purpose and usage
- [ ] Examples show common use patterns
- [ ] Session parameter documented correctly

---

## Definition of Done

- [ ] Both primitives implemented and working
- [ ] Session pattern followed consistently
- [ ] All unit tests pass
- [ ] Docstrings complete with examples
- [ ] No breaking changes to existing code
- [ ] Code follows existing service patterns

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Session detachment when accessing relationships | Return dicts (not ORM objects), eager load in query |
| Variant-of-variant chain (not supported) | Single `base_recipe_id` lookup - works because variants-of-variants prohibited |
| Empty FinishedUnit list edge case | Explicitly tested; returns empty list |

---

## Reviewer Guidance

When reviewing this work package, verify:

1. **Session Pattern**: Both functions accept `session=None` and use `session_scope()` fallback
2. **Return Format**: Returns `List[Dict]` per data-model.md contract
3. **Variant Resolution**: `get_base_yield_structure` resolves to base; `get_finished_units` does not
4. **Test Coverage**: All edge cases tested (base, variant, no FU, not found)
5. **Docstrings**: Clear examples showing usage patterns
