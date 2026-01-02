---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
  - "T003"
  - "T004"
  - "T005"
  - "T006"
title: "Schema & Denormalization Fields"
phase: "Phase 1 - Foundation"
lane: "done"
assignee: "claude"
agent: "claude-reviewer"
shell_pid: "25817"
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-02T12:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 - Schema & Denormalization Fields

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

**Objective**: Add three denormalization fields to the SnapshotIngredient model to preserve ingredient hierarchy information when ingredients are deleted. Also update the FK constraint to allow nullification.

**Success Criteria**:
- Three new nullable String columns added to SnapshotIngredient
- `ingredient_id` FK changed from RESTRICT to SET NULL
- `ingredient_id` column is now nullable
- Database schema recreates successfully
- `to_dict()` includes new fields

## Context & Constraints

**Related Documents**:
- Spec: `kitty-specs/035-ingredient-auto-slug/spec.md` (FR-010, FR-011)
- Plan: `kitty-specs/035-ingredient-auto-slug/plan.md` (Phase 1)
- Data Model: `kitty-specs/035-ingredient-auto-slug/data-model.md`
- Constitution: `.kittify/memory/constitution.md` (Section VI - Schema Change Strategy)

**Key Constraints**:
- Per constitution: Schema auto-recreates, NO migration scripts
- Fields must be nullable (existing records will have NULL values)
- FK must allow SET NULL to enable denormalization-then-nullify pattern

## Subtasks & Detailed Guidance

### Subtask T001 - Add ingredient_name_snapshot column

**Purpose**: Store the L2 ingredient display_name before deletion.

**Steps**:
1. Open `src/models/inventory_snapshot.py`
2. Locate the SnapshotIngredient class
3. Add after the `quantity` column:
   ```python
   # Denormalized fields for historical preservation (F035)
   ingredient_name_snapshot = Column(String(200), nullable=True)
   ```

**Files**: `src/models/inventory_snapshot.py`

### Subtask T002 - Add parent_l1_name_snapshot column

**Purpose**: Store the L1 parent ingredient name before deletion.

**Steps**:
1. Add after `ingredient_name_snapshot`:
   ```python
   parent_l1_name_snapshot = Column(String(200), nullable=True)
   ```

**Files**: `src/models/inventory_snapshot.py`

### Subtask T003 - Add parent_l0_name_snapshot column

**Purpose**: Store the L0 root ingredient name before deletion.

**Steps**:
1. Add after `parent_l1_name_snapshot`:
   ```python
   parent_l0_name_snapshot = Column(String(200), nullable=True)
   ```

**Files**: `src/models/inventory_snapshot.py`

### Subtask T004 - Change ingredient_id FK to SET NULL

**Purpose**: Allow the FK to be nullified after denormalization, enabling ingredient deletion.

**Steps**:
1. Find the `ingredient_id` column definition (currently):
   ```python
   ingredient_id = Column(
       Integer, ForeignKey("ingredients.id", ondelete="RESTRICT"), nullable=False
   )
   ```
2. Change to:
   ```python
   ingredient_id = Column(
       Integer, ForeignKey("ingredients.id", ondelete="SET NULL"), nullable=True
   )
   ```

**Files**: `src/models/inventory_snapshot.py`

### Subtask T005 - Make ingredient_id nullable

**Purpose**: Combined with T004 - the column must be nullable for SET NULL to work.

**Steps**: Already done in T004 (`nullable=True`)

### Subtask T006 - Update to_dict() method

**Purpose**: Include new snapshot fields in dictionary serialization.

**Steps**:
1. Find the `to_dict()` method in SnapshotIngredient class
2. Ensure the base `to_dict()` is called (it should include all columns automatically)
3. If custom fields are added, include the new snapshot fields

**Files**: `src/models/inventory_snapshot.py`

**Notes**: SQLAlchemy's BaseModel.to_dict() typically includes all columns automatically. Verify this is the case.

## Test Strategy

**Manual Verification**:
1. Run the application - database should auto-recreate with new schema
2. Create a new InventorySnapshot - verify new fields exist (as NULL)
3. Check `to_dict()` output includes the new fields

**No automated tests required for schema changes** - tested via WP06.

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Schema change breaks existing data | Export data first, reimport after (per constitution) |
| New fields break import/export | WP06 tests will catch; may need import service update |
| NULL values cause issues | All consuming code must handle NULL gracefully |

## Definition of Done Checklist

- [ ] T001: `ingredient_name_snapshot` column added
- [ ] T002: `parent_l1_name_snapshot` column added
- [ ] T003: `parent_l0_name_snapshot` column added
- [ ] T004: FK changed to `ondelete="SET NULL"`
- [ ] T005: `ingredient_id` is `nullable=True`
- [ ] T006: `to_dict()` includes new fields
- [ ] Application starts without errors
- [ ] Database recreates successfully

## Review Guidance

- Verify all three snapshot fields are String(200), nullable=True
- Verify FK is SET NULL, not RESTRICT
- Check to_dict() output

## Activity Log

- 2026-01-02T12:00:00Z - system - lane=planned - Prompt created via /spec-kitty.tasks
- 2026-01-02T19:32:23Z – claude – shell_pid=15513 – lane=doing – Started Wave 1 implementation
- 2026-01-02T22:40:00Z – claude – shell_pid=15513 – lane=doing – Completed implementation: T001-T003 (3 snapshot columns), T004-T005 (FK SET NULL, nullable), T006 (to_dict verified)
- 2026-01-02T19:37:12Z – claude – shell_pid=15513 – lane=for_review – Ready for review - schema denormalization fields complete (T001-T006)
- 2026-01-02T20:48:13Z – claude-reviewer – shell_pid=25817 – lane=done – Code review approved: All schema changes verified (SET NULL, nullable, 3 snapshot columns)
