---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
  - "T003"
  - "T004"
  - "T005"
title: "Model Layer – Add yield_type Field"
phase: "Phase 1 - Foundation"
lane: "done"
assignee: ""
agent: "claude-opus"
shell_pid: "68199"
review_status: "approved"
reviewed_by: "Kent Gale"
dependencies: []
history:
  - timestamp: "2026-01-29T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 – Model Layer – Add yield_type Field

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you begin addressing feedback, update `review_status: acknowledged`.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Implementation Command

```bash
# No dependencies - start from main branch
spec-kitty implement WP01
```

---

## Objectives & Success Criteria

Add `yield_type` column to the FinishedUnit model with appropriate constraints:

- [ ] FinishedUnit model has `yield_type` column (String(10), NOT NULL, default='SERVING')
- [ ] CHECK constraint ensures yield_type is 'EA' or 'SERVING'
- [ ] UNIQUE constraint prevents duplicate (recipe_id, item_unit, yield_type) combinations
- [ ] Index exists for yield_type queries
- [ ] Unit tests verify constraint behavior

**Success metrics**:
- Model instantiation with yield_type='EA' succeeds
- Model instantiation with yield_type='INVALID' raises constraint error
- Creating two FinishedUnits with same (recipe_id, item_unit, yield_type) raises uniqueness error

---

## Context & Constraints

**Reference documents**:
- `kitty-specs/084-dual-yield-recipe-output-support/data-model.md` - Schema changes
- `kitty-specs/084-dual-yield-recipe-output-support/research.md` - Constraint patterns (Q2)
- `.kittify/memory/constitution.md` - Architecture principles

**Existing patterns** (from research.md):
```python
# CHECK constraint pattern
CheckConstraint("inventory_count >= 0", name="ck_finished_unit_inventory_non_negative")

# UNIQUE constraint pattern
UniqueConstraint("recipe_id", "component_recipe_id", name="uq_recipe_component_recipe_component")
```

**Constraint naming conventions**:
- CHECK: `ck_<table>_<description>`
- UNIQUE: `uq_<table>_<columns>`
- Index: `idx_<table>_<columns>`

---

## Subtasks & Detailed Guidance

### Subtask T001 – Add yield_type column to FinishedUnit model

**Purpose**: Add the core field that enables yield classification.

**Steps**:
1. Open `src/models/finished_unit.py`
2. Locate the `yield_mode` column definition (around line 90)
3. Add the new column immediately after `yield_mode`:

```python
yield_type = Column(
    String(10),
    nullable=False,
    default="SERVING",
    index=True,
    doc="Yield classification: 'EA' (whole unit) or 'SERVING' (consumption unit)"
)
```

**Files**: `src/models/finished_unit.py`

**Notes**:
- Default is 'SERVING' (conservative - most baked goods are servings)
- NOT NULL ensures every record has a classification
- Index added inline (will also add explicit index in T004)

---

### Subtask T002 – Add CHECK constraint for valid yield_type values

**Purpose**: Enforce that yield_type can only be 'EA' or 'SERVING' at the database level.

**Steps**:
1. In `src/models/finished_unit.py`, locate the `__table_args__` tuple
2. Add the CHECK constraint after existing constraints:

```python
CheckConstraint(
    "yield_type IN ('EA', 'SERVING')",
    name="ck_finished_unit_yield_type_valid",
),
```

**Files**: `src/models/finished_unit.py`

**Notes**:
- This provides database-level validation in addition to service-layer validation
- Follows existing pattern from `ck_finished_unit_inventory_non_negative`

---

### Subtask T003 – Add UNIQUE constraint on (recipe_id, item_unit, yield_type)

**Purpose**: Prevent duplicate yield definitions for the same item_unit on a recipe.

**Steps**:
1. In `src/models/finished_unit.py`, locate the `__table_args__` tuple
2. Add the UNIQUE constraint:

```python
UniqueConstraint(
    "recipe_id", "item_unit", "yield_type",
    name="uq_finished_unit_recipe_item_unit_yield_type",
),
```

**Files**: `src/models/finished_unit.py`

**Notes**:
- This allows: "small cake/EA" AND "small cake/SERVING" on same recipe
- This prevents: two "small cake/EA" on same recipe
- Matches pattern from `uq_recipe_component_recipe_component`

---

### Subtask T004 – Add index on yield_type for query performance

**Purpose**: Optimize queries that filter by yield_type.

**Steps**:
1. In `src/models/finished_unit.py`, locate the Index definitions in `__table_args__`
2. Add the index:

```python
Index("idx_finished_unit_yield_type", "yield_type"),
```

**Files**: `src/models/finished_unit.py`

**Notes**:
- Planning services will frequently filter by yield_type
- Index improves performance for `WHERE yield_type = 'SERVING'` queries

---

### Subtask T005 – Write model-level unit tests

**Purpose**: Verify that constraints behave correctly.

**Steps**:
1. Create `src/tests/models/test_finished_unit_yield_type.py`
2. Write tests for:

```python
"""Tests for FinishedUnit yield_type field and constraints."""
import pytest
from sqlalchemy.exc import IntegrityError

from src.models.finished_unit import FinishedUnit
from src.models.recipe import Recipe
from src.utils.db import session_scope


class TestFinishedUnitYieldType:
    """Test yield_type field behavior."""

    def test_yield_type_default_is_serving(self, test_db):
        """FinishedUnit defaults to yield_type='SERVING'."""
        with session_scope() as session:
            recipe = Recipe(name="Test Recipe", slug="test-recipe", category="Test")
            session.add(recipe)
            session.flush()

            fu = FinishedUnit(
                slug="test-fu",
                display_name="Test",
                recipe_id=recipe.id,
                item_unit="cookie",
                items_per_batch=24,
            )
            session.add(fu)
            session.commit()

            assert fu.yield_type == "SERVING"

    def test_yield_type_accepts_ea(self, test_db):
        """FinishedUnit accepts yield_type='EA'."""
        with session_scope() as session:
            recipe = Recipe(name="Test Recipe", slug="test-recipe", category="Test")
            session.add(recipe)
            session.flush()

            fu = FinishedUnit(
                slug="test-fu",
                display_name="Test",
                recipe_id=recipe.id,
                item_unit="cake",
                items_per_batch=1,
                yield_type="EA",
            )
            session.add(fu)
            session.commit()

            assert fu.yield_type == "EA"

    def test_yield_type_rejects_invalid_value(self, test_db):
        """FinishedUnit rejects invalid yield_type values."""
        with session_scope() as session:
            recipe = Recipe(name="Test Recipe", slug="test-recipe", category="Test")
            session.add(recipe)
            session.flush()

            fu = FinishedUnit(
                slug="test-fu",
                display_name="Test",
                recipe_id=recipe.id,
                item_unit="cookie",
                items_per_batch=24,
                yield_type="INVALID",
            )
            session.add(fu)

            with pytest.raises(IntegrityError):
                session.commit()

    def test_unique_constraint_allows_different_yield_types(self, test_db):
        """Same item_unit can have both EA and SERVING yield types."""
        with session_scope() as session:
            recipe = Recipe(name="Test Recipe", slug="test-recipe", category="Test")
            session.add(recipe)
            session.flush()

            fu1 = FinishedUnit(
                slug="test-fu-ea",
                display_name="Test (EA)",
                recipe_id=recipe.id,
                item_unit="cake",
                items_per_batch=1,
                yield_type="EA",
            )
            fu2 = FinishedUnit(
                slug="test-fu-serving",
                display_name="Test (Serving)",
                recipe_id=recipe.id,
                item_unit="cake",
                items_per_batch=8,
                yield_type="SERVING",
            )
            session.add_all([fu1, fu2])
            session.commit()

            assert fu1.id is not None
            assert fu2.id is not None

    def test_unique_constraint_rejects_duplicate_yield_type(self, test_db):
        """Cannot have two FinishedUnits with same (recipe, item_unit, yield_type)."""
        with session_scope() as session:
            recipe = Recipe(name="Test Recipe", slug="test-recipe", category="Test")
            session.add(recipe)
            session.flush()

            fu1 = FinishedUnit(
                slug="test-fu-1",
                display_name="Test 1",
                recipe_id=recipe.id,
                item_unit="cake",
                items_per_batch=1,
                yield_type="EA",
            )
            fu2 = FinishedUnit(
                slug="test-fu-2",
                display_name="Test 2",
                recipe_id=recipe.id,
                item_unit="cake",
                items_per_batch=1,
                yield_type="EA",  # Duplicate!
            )
            session.add_all([fu1, fu2])

            with pytest.raises(IntegrityError):
                session.commit()
```

**Files**: `src/tests/models/test_finished_unit_yield_type.py` (new file)

**Notes**:
- Use existing `test_db` fixture for database setup
- Test both positive cases (valid values) and negative cases (constraint violations)

---

## Test Strategy

**Required tests** (T005):
- `test_yield_type_default_is_serving` - Verify default value
- `test_yield_type_accepts_ea` - Verify 'EA' is valid
- `test_yield_type_rejects_invalid_value` - Verify CHECK constraint
- `test_unique_constraint_allows_different_yield_types` - Verify both EA and SERVING allowed
- `test_unique_constraint_rejects_duplicate_yield_type` - Verify UNIQUE constraint

**Run tests**:
```bash
./run-tests.sh src/tests/models/test_finished_unit_yield_type.py -v
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Constraint rejects existing data | Migration (WP05) adds yield_type='SERVING' before schema change |
| Index impacts insert performance | Minimal impact for single-user desktop app |

---

## Definition of Done Checklist

- [ ] T001: yield_type column added to FinishedUnit model
- [ ] T002: CHECK constraint added and named correctly
- [ ] T003: UNIQUE constraint added and named correctly
- [ ] T004: Index added for yield_type
- [ ] T005: All unit tests pass
- [ ] Code follows existing patterns (constraint naming, column placement)
- [ ] No regressions in existing tests

---

## Review Guidance

**Reviewers should verify**:
1. Column definition matches data-model.md specification
2. Constraint names follow project conventions
3. Tests cover both valid and invalid cases
4. Default value is 'SERVING' (conservative choice)

---

## Activity Log

- 2026-01-29T00:00:00Z – system – lane=planned – Prompt created via /spec-kitty.tasks
- 2026-01-29T16:39:14Z – claude-opus – shell_pid=64508 – lane=doing – Started implementation via workflow command
- 2026-01-29T17:05:22Z – claude-opus – shell_pid=64508 – lane=for_review – Ready for review: Added yield_type column with CHECK, UNIQUE constraints, index, and tests. Updated test fixtures to comply with new constraint.
- 2026-01-29T17:05:30Z – claude-opus – shell_pid=68199 – lane=doing – Started review via workflow command
- 2026-01-29T17:07:51Z – claude-opus – shell_pid=68199 – lane=done – Review passed: yield_type column added with correct constraints (CHECK, UNIQUE), index, to_dict update, and comprehensive tests. Test fixtures updated for new constraint. All 3227 tests pass.
