---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
  - "T003"
  - "T004"
title: "Model & Validation Foundation"
phase: "Phase 1 - Data Model & Validation"
lane: "done"
assignee: ""
agent: "claude"
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-16T22:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 – Model & Validation Foundation

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you understand the feedback and begin addressing it, update `review_status: acknowledged`.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

**Objective**: Establish the data model foundation for unified yield management by making Recipe yield fields nullable and adding service layer validation for FinishedUnit requirements.

**Success Criteria**:
1. Recipe model has nullable yield_quantity, yield_unit, yield_description fields
2. FinishedUnit validation requires item_unit when yield_mode is DISCRETE_COUNT
3. Service function `validate_recipe_has_finished_unit()` exists and returns errors
4. All existing tests pass (update fixtures as needed)
5. New tests cover the validation logic

## Context & Constraints

**Related Documents**:
- Spec: `kitty-specs/056-unified-yield-management/spec.md`
- Plan: `kitty-specs/056-unified-yield-management/plan.md`
- Data Model: `kitty-specs/056-unified-yield-management/data-model.md`
- Research: `kitty-specs/056-unified-yield-management/research.md`

**Architectural Constraints**:
- Layered architecture: Models define schema only; validation logic in services
- Constitution IV: Test-driven development required
- Constitution VI: No in-app migration; schema changes via export/reset/import

**Key Design Decision**: Validation is enforced at service layer, not model layer. This allows gradual migration without breaking existing data.

## Subtasks & Detailed Guidance

### Subtask T001 – Make Recipe yield fields nullable

**Purpose**: Allow recipes to exist without legacy yield fields during transition period.

**Steps**:
1. Open `src/models/recipe.py`
2. Locate yield field definitions (lines ~59-62):
   ```python
   yield_quantity = Column(Float, nullable=False)
   yield_unit = Column(String(50), nullable=False)
   yield_description = Column(String(200), nullable=True)
   ```
3. Change `nullable=False` to `nullable=True` for yield_quantity and yield_unit
4. Add deprecation comments above each field:
   ```python
   # DEPRECATED: Use FinishedUnit.items_per_batch instead
   yield_quantity = Column(Float, nullable=True)

   # DEPRECATED: Use FinishedUnit.item_unit instead
   yield_unit = Column(String(50), nullable=True)

   # DEPRECATED: Use FinishedUnit.display_name instead
   yield_description = Column(String(200), nullable=True)
   ```

**Files**: `src/models/recipe.py`
**Parallel?**: No (blocking change)
**Notes**: This does NOT require database migration for SQLite. The app uses reset/reimport.

### Subtask T002 – Add item_unit validation to FinishedUnit model

**Purpose**: Ensure DISCRETE_COUNT mode FinishedUnits have complete yield data.

**Steps**:
1. Open `src/models/finished_unit.py`
2. Locate the existing `items_per_batch` validation in CheckConstraint section
3. Add a new validation method or update existing constraint
4. The validation should be soft (warn) at model level, hard at service level

**Option A - Add validate method**:
```python
def validate_discrete_count_fields(self) -> List[str]:
    """Validate fields for DISCRETE_COUNT mode."""
    errors = []
    if self.yield_mode == YieldMode.DISCRETE_COUNT:
        if not self.items_per_batch or self.items_per_batch <= 0:
            errors.append("items_per_batch required and must be > 0")
        if not self.item_unit:
            errors.append("item_unit required for discrete count mode")
        if not self.display_name:
            errors.append("display_name required")
    return errors
```

**Files**: `src/models/finished_unit.py`
**Parallel?**: Yes (independent of T001)
**Notes**: Model-level validation is advisory; service layer enforces.

### Subtask T003 – Add validate_recipe_has_finished_unit() to recipe_service

**Purpose**: Provide service-layer validation that recipes have at least one complete FinishedUnit.

**Steps**:
1. Open `src/services/recipe_service.py`
2. Add new function:
   ```python
   def validate_recipe_has_finished_unit(recipe_id: int, session=None) -> List[str]:
       """
       Validate that a recipe has at least one complete FinishedUnit.

       A complete FinishedUnit has:
       - display_name (non-empty)
       - item_unit (non-empty for DISCRETE_COUNT mode)
       - items_per_batch (> 0 for DISCRETE_COUNT mode)

       Args:
           recipe_id: The recipe to validate
           session: Optional SQLAlchemy session

       Returns:
           List of validation error messages (empty if valid)
       """
       errors = []

       def _impl(sess):
           recipe = sess.query(Recipe).get(recipe_id)
           if not recipe:
               return ["Recipe not found"]

           finished_units = recipe.finished_units
           if not finished_units:
               return ["Recipe must have at least one yield type"]

           complete_count = 0
           for fu in finished_units:
               fu_errors = []
               if not fu.display_name:
                   fu_errors.append(f"Yield type missing name")
               if fu.yield_mode == YieldMode.DISCRETE_COUNT:
                   if not fu.item_unit:
                       fu_errors.append(f"Yield type '{fu.display_name or 'unnamed'}' missing unit")
                   if not fu.items_per_batch or fu.items_per_batch <= 0:
                       fu_errors.append(f"Yield type '{fu.display_name or 'unnamed'}' missing quantity")
               if not fu_errors:
                   complete_count += 1
               errors.extend(fu_errors)

           if complete_count == 0:
               errors.append("At least one complete yield type required")

           return errors

       if session is not None:
           return _impl(session)
       with session_scope() as sess:
           return _impl(sess)
   ```
3. Add necessary imports at top of file

**Files**: `src/services/recipe_service.py`
**Parallel?**: No (depends on T001 model changes)
**Notes**: Follow session management pattern per CLAUDE.md

### Subtask T004 – Add tests for recipe validation logic

**Purpose**: Ensure validation logic works correctly with comprehensive test coverage.

**Steps**:
1. Open or create `src/tests/test_recipe_service.py`
2. Add test class for validation:
   ```python
   class TestRecipeFinishedUnitValidation:
       """Tests for validate_recipe_has_finished_unit() function."""

       def test_recipe_without_finished_units_fails(self, session, sample_recipe):
           """Recipe with no FinishedUnits should fail validation."""
           errors = validate_recipe_has_finished_unit(sample_recipe.id, session)
           assert len(errors) > 0
           assert "at least one yield type" in errors[0].lower()

       def test_recipe_with_complete_finished_unit_passes(self, session, sample_recipe):
           """Recipe with complete FinishedUnit should pass validation."""
           fu = FinishedUnit(
               recipe_id=sample_recipe.id,
               slug="test_standard",
               display_name="Standard Test",
               yield_mode=YieldMode.DISCRETE_COUNT,
               items_per_batch=12,
               item_unit="cookie"
           )
           session.add(fu)
           session.flush()

           errors = validate_recipe_has_finished_unit(sample_recipe.id, session)
           assert len(errors) == 0

       def test_incomplete_finished_unit_fails(self, session, sample_recipe):
           """FinishedUnit missing item_unit should fail for DISCRETE_COUNT."""
           fu = FinishedUnit(
               recipe_id=sample_recipe.id,
               slug="test_incomplete",
               display_name="Incomplete",
               yield_mode=YieldMode.DISCRETE_COUNT,
               items_per_batch=12,
               item_unit=None  # Missing!
           )
           session.add(fu)
           session.flush()

           errors = validate_recipe_has_finished_unit(sample_recipe.id, session)
           assert len(errors) > 0
           assert "unit" in errors[0].lower()
   ```

**Files**: `src/tests/test_recipe_service.py`
**Parallel?**: Yes (can write tests while T003 is being implemented)
**Notes**: Use existing test fixtures; may need to update fixtures that assume non-null yield fields

## Test Strategy

**Required Tests**:
1. Recipe with no FinishedUnits → validation fails
2. Recipe with complete FinishedUnit → validation passes
3. Recipe with incomplete FinishedUnit (missing item_unit) → validation fails
4. Recipe with incomplete FinishedUnit (missing items_per_batch) → validation fails
5. Recipe with incomplete FinishedUnit (missing display_name) → validation fails
6. Recipe with multiple FinishedUnits, at least one complete → validation passes

**Commands**:
```bash
./run-tests.sh src/tests/test_recipe_service.py -v
./run-tests.sh -v --cov=src/services/recipe_service
```

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Existing tests fail with nullable changes | Update test fixtures to provide yield values explicitly |
| Session management issues | Follow session pattern per CLAUDE.md |
| Breaking existing recipe creation UI | Validation only runs when explicitly called; UI updated in WP05 |

## Definition of Done Checklist

- [ ] T001: Recipe yield fields are nullable with deprecation comments
- [ ] T002: FinishedUnit has validation method for DISCRETE_COUNT fields
- [ ] T003: validate_recipe_has_finished_unit() function exists in recipe_service
- [ ] T004: Tests written and passing for all validation scenarios
- [ ] All existing tests pass (may need fixture updates)
- [ ] `tasks.md` updated with completion status

## Review Guidance

**Key Checkpoints**:
1. Verify nullable changes in Recipe model are correct
2. Verify validation function follows session management pattern
3. Verify tests cover all validation edge cases
4. Ensure no layer violations (validation in service, not model)

## Activity Log

- 2026-01-16T22:00:00Z – system – lane=planned – Prompt created.
- 2026-01-17T03:04:50Z – agent – lane=doing – Started implementation via workflow command
- 2026-01-17T03:16:11Z – claude – lane=for_review – All subtasks complete: T001-T004. Model changes, validation function, and tests implemented. 2347 tests pass.
- 2026-01-17T17:56:14Z – claude – lane=doing – Started review via workflow command
- 2026-01-17T17:58:10Z – claude – lane=done – Review passed: All T001-T004 requirements verified. Recipe fields nullable, FinishedUnit validation method exists, service function follows session pattern, 11 tests pass.
