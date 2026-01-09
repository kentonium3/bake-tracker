---
work_package_id: "WP01"
subtasks:
  - "T001"
title: "Model - Cascade Delete"
phase: "Phase 1 - Parallel Foundation"
lane: "done"
assignee: ""
agent: "claude"
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-09T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 - Model - Cascade Delete

## Objectives & Success Criteria

**Primary Objective**: Enable cascade deletion of FinishedUnits when their parent Recipe is deleted.

**Success Criteria**:
- When a Recipe with associated FinishedUnits is deleted, all its FinishedUnits are automatically deleted
- No orphaned FinishedUnit records remain in the database
- Existing functionality remains unaffected

## Context & Constraints

**Feature**: 044-finished-units-yield-type-management
**Spec Reference**: [spec.md](../spec.md) - Clarifications section, cascade delete decision
**Research Reference**: [research.md](../research.md) - Model Layer section

**Architectural Context**:
- Layered architecture: Models define schema only (no business logic)
- SQLite with WAL mode - FK constraints may not be enforced by default
- Existing relationship: Recipe.finished_units -> [FinishedUnit]

**Clarification Decision (2026-01-09)**:
> Q: When a Recipe is deleted, what should happen to its associated FinishedUnits?
> A: Cascade delete - FinishedUnits are automatically deleted with the recipe

## Subtasks & Detailed Guidance

### Subtask T001 - Change FK ondelete RESTRICT to CASCADE

**Purpose**: The current foreign key constraint prevents recipe deletion if it has yield types. This needs to change to CASCADE to auto-delete associated FinishedUnits.

**File**: `src/models/finished_unit.py`

**Current Code (line 84)**:
```python
recipe_id = Column(Integer, ForeignKey("recipes.id", ondelete="RESTRICT"), nullable=False)
```

**Required Change**:
```python
recipe_id = Column(Integer, ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False)
```

**Steps**:
1. Open `src/models/finished_unit.py`
2. Locate line 84 (the recipe_id column definition)
3. Change `ondelete="RESTRICT"` to `ondelete="CASCADE"`
4. No other changes needed to this file

**Verification**:
```python
# Quick verification (run in Python REPL after change):
from src.models.finished_unit import FinishedUnit
from sqlalchemy import inspect
# The FK constraint should now specify CASCADE
```

**Notes**:
- SQLite may not enforce FK constraints unless `PRAGMA foreign_keys=ON` is set
- The application handles this via session configuration
- No database migration is needed - this is a behavioral change for new deletions

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Accidental data loss | Low | Medium | This is the desired behavior per user clarification |
| Existing orphaned records | Low | Low | Verify no orphans exist before testing |

**Pre-flight Check**:
```sql
-- Run in SQLite to verify no orphaned records exist
SELECT fu.* FROM finished_units fu
LEFT JOIN recipes r ON fu.recipe_id = r.id
WHERE r.id IS NULL;
-- Should return 0 rows
```

## Definition of Done Checklist

- [ ] T001: FK constraint changed from RESTRICT to CASCADE
- [ ] File passes Python syntax check (`python -m py_compile src/models/finished_unit.py`)
- [ ] Application starts without import errors (`python src/main.py`)
- [ ] No regression in existing recipe functionality

## Review Guidance

**Key Verification Points**:
1. Confirm the exact line change (RESTRICT -> CASCADE)
2. Verify no other changes were made to the model
3. Confirm application still loads correctly

**Quick Test** (for reviewer):
1. Start application
2. Create a recipe with at least one yield type
3. Delete the recipe
4. Verify no error occurs (would fail with RESTRICT)

## Activity Log

- 2026-01-09T00:00:00Z - system - lane=planned - Prompt created.
- 2026-01-09T18:09:58Z – agent – lane=doing – Started implementation via workflow command
- 2026-01-09T18:10:51Z – unknown – lane=for_review – Changed FK ondelete from RESTRICT to CASCADE on line 84. Syntax check passed, import successful.
- 2026-01-09T18:37:29Z – claude – lane=done – Code review complete: Approved. FK constraint correctly changed to CASCADE.
