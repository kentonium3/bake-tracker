---
work_package_id: "WP02"
subtasks:
  - "T006"
  - "T007"
  - "T008"
  - "T009"
  - "T010"
  - "T011"
title: "Variant Creation Extension"
phase: "Phase 1 - Core"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
dependencies: ["WP01"]
history:
  - timestamp: "2025-01-24T07:30:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP02 – Variant Creation Extension

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
spec-kitty implement WP02 --base WP01
```

This work package depends on WP01 (service primitives).

---

## Objectives & Success Criteria

Extend the existing `create_recipe_variant()` function to accept a `finished_unit_names` parameter that creates variant FinishedUnits with NULL yield fields.

**Success Criteria**:
- [ ] `create_recipe_variant()` accepts optional `finished_unit_names` parameter
- [ ] Variant FinishedUnits created with correct display_names and NULL yield fields
- [ ] Validation rejects duplicate display_names (matching base)
- [ ] Slug generation produces unique, URL-safe slugs
- [ ] Existing callers (without `finished_unit_names`) continue to work unchanged
- [ ] Unit tests verify creation and validation logic

---

## Context & Constraints

**References**:
- Plan: `kitty-specs/063-variant-yield-inheritance/plan.md`
- Data Model: `kitty-specs/063-variant-yield-inheritance/data-model.md` (extended create_recipe_variant contract)
- Spec: `kitty-specs/063-variant-yield-inheritance/spec.md` (FR-003, FR-004, FR-005)

**Architectural Constraints**:
- Extend existing functions in `src/services/recipe_service.py`
- New parameter must have default value `None` (backward compatibility)
- Variant FinishedUnits MUST have `items_per_batch=None`, `item_unit=None`
- Variant display_name MUST differ from base display_name (validation)

**Existing Function** (in `recipe_service.py` ~line 1936):
```python
def create_recipe_variant(
    base_recipe_id: int,
    variant_name: str,
    name: str = None,
    copy_ingredients: bool = True,
    session=None,
) -> dict:
```

---

## Subtasks & Detailed Guidance

### Subtask T006 – Add `finished_unit_names` parameter

**Purpose**: Extend the function signature to accept FinishedUnit display names for the variant.

**Steps**:
1. Update `create_recipe_variant()` signature (~line 1936):
   ```python
   def create_recipe_variant(
       base_recipe_id: int,
       variant_name: str,
       name: str = None,
       copy_ingredients: bool = True,
       finished_unit_names: Optional[List[Dict]] = None,  # NEW
       session=None,
   ) -> dict:
   ```

2. Update `_create_recipe_variant_impl()` signature (~line 1977):
   ```python
   def _create_recipe_variant_impl(
       base_recipe_id: int,
       variant_name: str,
       name: str,
       copy_ingredients: bool,
       finished_unit_names: Optional[List[Dict]],  # NEW
       session
   ) -> dict:
   ```

3. Update the call to `_create_recipe_variant_impl` in `create_recipe_variant`:
   ```python
   if session is not None:
       return _create_recipe_variant_impl(
           base_recipe_id, variant_name, name, copy_ingredients, finished_unit_names, session
       )
   # ... same pattern for session_scope() branch
   ```

4. Update docstring to document new parameter:
   ```python
   """
   ...
   Args:
       ...
       finished_unit_names: Optional list of dicts specifying variant FinishedUnits:
           [{"base_slug": "plain-cookie", "display_name": "Raspberry Cookie"}, ...]
           If provided, creates variant FinishedUnits with NULL yield fields.
           If None (default), no FinishedUnits are created for the variant.
   ...
   Raises:
       ...
       ValidationError: If any display_name matches base FinishedUnit display_name
   """
   ```

**Files**:
- `src/services/recipe_service.py` (modify ~20 lines)

**Validation**:
- [ ] Function accepts new parameter
- [ ] Existing calls without parameter still work

---

### Subtask T007 – Implement FinishedUnit creation logic

**Purpose**: Create variant FinishedUnits with provided display_names and NULL yield fields.

**Steps**:
1. Add FinishedUnit creation logic in `_create_recipe_variant_impl()` after variant recipe is created:
   ```python
   # After: session.add(new_ri) loop for ingredients
   # Before: session.flush()

   # Create variant FinishedUnits if specified
   if finished_unit_names:
       # Get base FinishedUnits for reference
       base_fus = {fu.slug: fu for fu in session.query(FinishedUnit).filter_by(recipe_id=base_recipe_id).all()}

       for fu_spec in finished_unit_names:
           base_slug = fu_spec.get("base_slug")
           new_display_name = fu_spec.get("display_name")

           if not base_slug or not new_display_name:
               raise ValidationError(["finished_unit_names entries require 'base_slug' and 'display_name'"])

           base_fu = base_fus.get(base_slug)
           if not base_fu:
               raise ValidationError([f"Base FinishedUnit with slug '{base_slug}' not found"])

           # Create variant FinishedUnit
           variant_fu = FinishedUnit(
               recipe_id=variant.id,
               slug=_generate_variant_fu_slug(variant.name, new_display_name, variant.id),
               display_name=new_display_name,
               # Yield fields NULL for variants (inherited via primitives)
               items_per_batch=None,
               item_unit=None,
               # Copy non-yield fields from base
               yield_mode=base_fu.yield_mode,
               category=base_fu.category,
               batch_percentage=None,  # Clear this too if present
               portion_description=base_fu.portion_description,
               production_notes=base_fu.production_notes,
           )
           session.add(variant_fu)
   ```

2. Add helper function for slug generation:
   ```python
   def _generate_variant_fu_slug(recipe_name: str, display_name: str, recipe_id: int) -> str:
       """Generate unique slug for variant FinishedUnit."""
       from src.utils.slug_utils import slugify  # or implement inline

       base = slugify(f"{recipe_name}-{display_name}")
       # Ensure uniqueness by appending recipe_id if needed
       return f"{base}-{recipe_id}"
   ```

**Files**:
- `src/services/recipe_service.py` (modify ~40 lines)

**Validation**:
- [ ] Variant FinishedUnits created with correct display_name
- [ ] `items_per_batch` and `item_unit` are NULL
- [ ] Non-yield fields copied from base
- [ ] Slug is unique and URL-safe

---

### Subtask T008 – Add display_name validation

**Purpose**: Validate that variant display_name differs from base display_name (per FR-004, clarification).

**Steps**:
1. Add validation before creating FinishedUnits in `_create_recipe_variant_impl()`:
   ```python
   if finished_unit_names:
       # Get base FinishedUnits for reference and validation
       base_fus = {fu.slug: fu for fu in session.query(FinishedUnit).filter_by(recipe_id=base_recipe_id).all()}
       base_display_names = {fu.display_name for fu in base_fus.values()}

       for fu_spec in finished_unit_names:
           new_display_name = fu_spec.get("display_name")

           # Validate display_name differs from base
           if new_display_name in base_display_names:
               raise ValidationError([
                   f"Variant display_name '{new_display_name}' must differ from base FinishedUnit display_name"
               ])

       # ... continue with creation
   ```

**Files**:
- `src/services/recipe_service.py` (modify ~10 lines)

**Validation**:
- [ ] ValidationError raised if display_name matches base
- [ ] Error message clearly identifies the issue

---

### Subtask T009 – Generate variant FinishedUnit slug

**Purpose**: Ensure variant FinishedUnit slugs are unique and URL-safe.

**Steps**:
1. Check if `src/utils/slug_utils.py` exists with a `slugify` function. If not, implement inline:
   ```python
   import re

   def _generate_variant_fu_slug(recipe_name: str, display_name: str, recipe_id: int) -> str:
       """
       Generate unique slug for variant FinishedUnit.

       Format: {recipe-name}-{display-name}-{recipe_id}
       Example: "raspberry-thumbprint-cookies-raspberry-cookie-42"
       """
       combined = f"{recipe_name}-{display_name}"
       # Lowercase, replace spaces and special chars with hyphens
       slug = re.sub(r'[^a-z0-9]+', '-', combined.lower()).strip('-')
       # Append recipe_id for uniqueness
       return f"{slug}-{recipe_id}"
   ```

2. If `slugify` exists in utils, use it:
   ```python
   from src.utils.slug_utils import slugify

   def _generate_variant_fu_slug(recipe_name: str, display_name: str, recipe_id: int) -> str:
       base = slugify(f"{recipe_name} {display_name}")
       return f"{base}-{recipe_id}"
   ```

**Files**:
- `src/services/recipe_service.py` (add ~15 lines)

**Validation**:
- [ ] Generated slug is lowercase
- [ ] Special characters replaced with hyphens
- [ ] Recipe ID appended for uniqueness
- [ ] No leading/trailing hyphens

---

### Subtask T010 – Add unit tests for variant creation with FinishedUnits

**Purpose**: Verify variant creation correctly creates FinishedUnits with NULL yields.

**Steps**:
1. Add tests to `src/tests/test_recipe_service.py`:
   ```python
   def test_create_variant_with_finished_units(session, base_recipe_with_fu):
       """Variant creation with finished_unit_names creates variant FinishedUnits."""
       base, base_fu = base_recipe_with_fu

       result = create_recipe_variant(
           base_recipe_id=base.id,
           variant_name="Raspberry",
           finished_unit_names=[
               {"base_slug": base_fu.slug, "display_name": "Raspberry Cookie"}
           ],
           session=session,
       )

       # Verify variant created
       assert result["variant_name"] == "Raspberry"

       # Verify variant FinishedUnit created
       variant_fus = session.query(FinishedUnit).filter_by(recipe_id=result["id"]).all()
       assert len(variant_fus) == 1
       assert variant_fus[0].display_name == "Raspberry Cookie"
       assert variant_fus[0].items_per_batch is None  # NULL for variants
       assert variant_fus[0].item_unit is None  # NULL for variants

   def test_create_variant_without_finished_units(session, base_recipe_with_fu):
       """Variant creation without finished_unit_names creates no FinishedUnits."""
       base, _ = base_recipe_with_fu

       result = create_recipe_variant(
           base_recipe_id=base.id,
           variant_name="Chocolate",
           session=session,
       )

       # Verify no variant FinishedUnits
       variant_fus = session.query(FinishedUnit).filter_by(recipe_id=result["id"]).all()
       assert len(variant_fus) == 0

   def test_create_variant_copies_non_yield_fields(session, base_recipe_with_fu):
       """Variant FinishedUnit copies category and yield_mode from base."""
       base, base_fu = base_recipe_with_fu
       base_fu.category = "Cookies"
       session.flush()

       result = create_recipe_variant(
           base_recipe_id=base.id,
           variant_name="Strawberry",
           finished_unit_names=[
               {"base_slug": base_fu.slug, "display_name": "Strawberry Cookie"}
           ],
           session=session,
       )

       variant_fu = session.query(FinishedUnit).filter_by(recipe_id=result["id"]).first()
       assert variant_fu.category == "Cookies"  # Copied from base
       assert variant_fu.yield_mode == base_fu.yield_mode  # Copied from base
   ```

**Files**:
- `src/tests/test_recipe_service.py` (add ~60 lines)

**Validation**:
- [ ] Tests pass
- [ ] Covers: with FU names, without FU names, non-yield field copying

---

### Subtask T011 – Add unit tests for display_name validation

**Purpose**: Verify validation rejects duplicate display_names.

**Steps**:
1. Add validation tests:
   ```python
   def test_create_variant_rejects_duplicate_display_name(session, base_recipe_with_fu):
       """Variant creation rejects display_name matching base."""
       base, base_fu = base_recipe_with_fu

       with pytest.raises(ValidationError) as exc_info:
           create_recipe_variant(
               base_recipe_id=base.id,
               variant_name="Copy",
               finished_unit_names=[
                   {"base_slug": base_fu.slug, "display_name": base_fu.display_name}  # Same as base!
               ],
               session=session,
           )

       assert "must differ" in str(exc_info.value).lower()

   def test_create_variant_rejects_invalid_base_slug(session, base_recipe_with_fu):
       """Variant creation rejects non-existent base_slug."""
       base, _ = base_recipe_with_fu

       with pytest.raises(ValidationError) as exc_info:
           create_recipe_variant(
               base_recipe_id=base.id,
               variant_name="Test",
               finished_unit_names=[
                   {"base_slug": "nonexistent-slug", "display_name": "Test Cookie"}
               ],
               session=session,
           )

       assert "not found" in str(exc_info.value).lower()

   def test_create_variant_rejects_missing_required_fields(session, base_recipe_with_fu):
       """Variant creation rejects finished_unit_names without required fields."""
       base, base_fu = base_recipe_with_fu

       with pytest.raises(ValidationError):
           create_recipe_variant(
               base_recipe_id=base.id,
               variant_name="Test",
               finished_unit_names=[
                   {"base_slug": base_fu.slug}  # Missing display_name
               ],
               session=session,
           )
   ```

**Files**:
- `src/tests/test_recipe_service.py` (add ~50 lines)

**Validation**:
- [ ] Tests pass
- [ ] Covers: duplicate display_name, invalid base_slug, missing fields

---

## Definition of Done

- [ ] `create_recipe_variant` accepts `finished_unit_names` parameter
- [ ] Variant FinishedUnits created with NULL yield fields
- [ ] Display_name validation implemented and working
- [ ] Slug generation produces unique slugs
- [ ] All unit tests pass
- [ ] Existing callers unchanged (backward compatible)
- [ ] Docstrings updated

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Breaking existing callers | New param has default `None`; existing calls unchanged |
| Slug collision | Include recipe_id in slug for uniqueness |
| Missing base FinishedUnit | Validate base_slug exists before creation |

---

## Reviewer Guidance

When reviewing this work package, verify:

1. **Backward Compatibility**: Existing calls without `finished_unit_names` still work
2. **NULL Yields**: Variant FinishedUnits have `items_per_batch=None`, `item_unit=None`
3. **Validation**: Duplicate display_name rejected with clear error
4. **Non-Yield Fields**: Category, yield_mode copied from base
5. **Slug Uniqueness**: Generated slugs are unique and URL-safe
6. **Test Coverage**: All scenarios tested including error cases
