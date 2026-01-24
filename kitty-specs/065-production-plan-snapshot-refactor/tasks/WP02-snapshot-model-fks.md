---
work_package_id: "WP02"
subtasks:
  - "T005"
  - "T006"
  - "T007"
  - "T008"
  - "T009"
title: "Snapshot Model FK Updates"
phase: "Phase 1 - Model Changes (Foundation)"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
dependencies: []
history:
  - timestamp: "2026-01-24T19:47:15Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP02 – Snapshot Model FK Updates

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.

---

## Review Feedback

> **Populated by `/spec-kitty.review`** – Reviewers add detailed feedback here when work needs changes.

*[This section is empty initially.]*

---

## Implementation Command

```bash
# No dependencies - can run in parallel with WP01
spec-kitty implement WP02
```

---

## Objectives & Success Criteria

Add snapshot foreign keys to target models and enable planning context for RecipeSnapshot.

**Success Criteria**:
- [ ] RecipeSnapshot.production_run_id is nullable (allows planning context)
- [ ] EventProductionTarget has recipe_snapshot_id FK (nullable, indexed)
- [ ] EventAssemblyTarget has finished_good_snapshot_id FK (nullable, indexed)
- [ ] Relationship definitions added for new FKs
- [ ] F064 FinishedGoodSnapshot verified to support planning context
- [ ] No import errors or syntax errors after changes

## Context & Constraints

**Reference Documents**:
- `kitty-specs/065-production-plan-snapshot-refactor/data-model.md` - Schema changes specification
- `kitty-specs/065-production-plan-snapshot-refactor/research.md` - RQ-2 (snapshot patterns), RQ-5 (target changes)

**Key Constraints**:
- FKs must be nullable for backward compatibility (legacy events have no snapshots)
- Use ON DELETE RESTRICT for snapshot FKs (preserve integrity)
- Add index on new FK columns for query performance
- Follow existing FK patterns in codebase

## Subtasks & Detailed Guidance

### Subtask T005 – Make RecipeSnapshot.production_run_id nullable

**Purpose**: Currently RecipeSnapshot requires a production_run_id (created at production time). Making it nullable allows creating snapshots at planning time without a production run.

**Steps**:
1. Open `src/models/recipe_snapshot.py`
2. Find the production_run_id Column definition:
   ```python
   production_run_id = Column(
       Integer,
       ForeignKey("production_runs.id", ondelete="CASCADE"),
       nullable=False,  # ← Change this
       unique=True
   )
   ```
3. Change `nullable=False` to `nullable=True`:
   ```python
   production_run_id = Column(
       Integer,
       ForeignKey("production_runs.id", ondelete="CASCADE"),
       nullable=True,  # Planning context: no production_run_id
       unique=True     # Still unique when set
   )
   ```
4. Update class docstring to document planning context:
   ```python
   """Immutable snapshot of recipe state.

   Context:
   - Production context: production_run_id is set (created at production time)
   - Planning context: production_run_id is None (created at plan time,
     referenced via EventProductionTarget.recipe_snapshot_id)
   """
   ```

**Files**:
- `src/models/recipe_snapshot.py` (modify)

**Parallel?**: No - foundation for other subtasks

**Notes**: The unique=True constraint still applies when production_run_id is set; NULL values are not considered for uniqueness.

---

### Subtask T006 – Add recipe_snapshot_id FK to EventProductionTarget

**Purpose**: Link production targets to the RecipeSnapshot created at planning time, enabling snapshot reuse during production.

**Steps**:
1. Open `src/models/event.py`
2. Find the EventProductionTarget class (around line 329 per research.md)
3. Add the new FK column after existing columns:
   ```python
   class EventProductionTarget(BaseModel):
       __tablename__ = "event_production_targets"

       event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
       recipe_id = Column(Integer, ForeignKey("recipes.id", ondelete="RESTRICT"), nullable=False)
       target_batches = Column(Integer, nullable=False)
       notes = Column(Text, nullable=True)

       # NEW: Snapshot reference created at planning time
       recipe_snapshot_id = Column(
           Integer,
           ForeignKey("recipe_snapshots.id", ondelete="RESTRICT"),
           nullable=True,  # Backward compatibility for legacy events
           index=True
       )
   ```
4. Add import if needed:
   ```python
   from sqlalchemy import Column, Integer, ForeignKey, Text, Index
   ```

**Files**:
- `src/models/event.py` (modify)

**Parallel?**: Yes - can be done alongside T007

**Notes**:
- ON DELETE RESTRICT prevents accidental snapshot deletion
- nullable=True for backward compatibility (legacy events have no snapshot)
- index=True for efficient queries during production

---

### Subtask T007 – Add finished_good_snapshot_id FK to EventAssemblyTarget

**Purpose**: Link assembly targets to the FinishedGoodSnapshot created at planning time, enabling snapshot reuse during assembly.

**Steps**:
1. In `src/models/event.py`, find EventAssemblyTarget class
2. Add the new FK column after existing columns:
   ```python
   class EventAssemblyTarget(BaseModel):
       __tablename__ = "event_assembly_targets"

       event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
       finished_good_id = Column(Integer, ForeignKey("finished_goods.id", ondelete="RESTRICT"), nullable=False)
       target_quantity = Column(Integer, nullable=False)
       notes = Column(Text, nullable=True)

       # NEW: Snapshot reference created at planning time (F064 complete)
       finished_good_snapshot_id = Column(
           Integer,
           ForeignKey("finished_good_snapshots.id", ondelete="RESTRICT"),
           nullable=True,  # Backward compatibility for legacy events
           index=True
       )
   ```

**Files**:
- `src/models/event.py` (modify)

**Parallel?**: Yes - can be done alongside T006

**Notes**: Mirrors the pattern from T006 for consistency.

---

### Subtask T008 – Add relationship definitions for new FKs

**Purpose**: Add SQLAlchemy relationship() definitions to enable ORM navigation between targets and snapshots.

**Steps**:
1. In EventProductionTarget, add relationship:
   ```python
   # Relationship to RecipeSnapshot
   recipe_snapshot = relationship(
       "RecipeSnapshot",
       foreign_keys=[recipe_snapshot_id],
       lazy="joined"  # Eager load for planning queries
   )
   ```

2. In EventAssemblyTarget, add relationship:
   ```python
   # Relationship to FinishedGoodSnapshot
   finished_good_snapshot = relationship(
       "FinishedGoodSnapshot",
       foreign_keys=[finished_good_snapshot_id],
       lazy="joined"  # Eager load for planning queries
   )
   ```

3. Add relationship import if needed:
   ```python
   from sqlalchemy.orm import relationship
   ```

**Files**:
- `src/models/event.py` (modify)

**Parallel?**: No - should be done after T006, T007

**Notes**:
- `lazy="joined"` enables eager loading for get_plan_summary() performance
- `foreign_keys=[...]` explicitly specifies which FK to use (avoids ambiguity)

---

### Subtask T009 – Verify FinishedGoodSnapshot supports planning context (F064)

**Purpose**: Confirm that F064 implemented planning_snapshot_id FK on FinishedGoodSnapshot, enabling planning context.

**Steps**:
1. Open `src/models/finished_good_snapshot.py`
2. Verify these fields exist:
   ```python
   planning_snapshot_id = Column(
       Integer,
       ForeignKey("planning_snapshots.id", ondelete="CASCADE"),
       nullable=True  # Planning context
   )
   assembly_run_id = Column(
       Integer,
       ForeignKey("assembly_runs.id", ondelete="CASCADE"),
       nullable=True  # Assembly context
   )
   ```
3. If planning_snapshot_id is MISSING (F064 incomplete):
   - Add the FK following the pattern above
   - Document that F064 was incomplete

4. Verify both FKs are nullable (dual-context pattern)

5. Document verification result in activity log

**Files**:
- `src/models/finished_good_snapshot.py` (verify, possibly modify)

**Parallel?**: No - verification task

**Notes**:
- F064 spec stated this would be implemented
- If missing, this WP should add it
- The dual-context pattern (either planning_snapshot_id OR assembly_run_id) is the target architecture

---

## Test Strategy

**Verification Commands**:
```bash
# Verify models compile without errors
python -c "from src.models.recipe_snapshot import RecipeSnapshot; print('RecipeSnapshot OK')"
python -c "from src.models.event import EventProductionTarget, EventAssemblyTarget; print('Targets OK')"
python -c "from src.models.finished_good_snapshot import FinishedGoodSnapshot; print('FGSnapshot OK')"

# Check FK definitions
python -c "
from src.models.event import EventProductionTarget
print('recipe_snapshot_id:', EventProductionTarget.recipe_snapshot_id.property.columns[0].nullable)
"
```

**Test Database Recreation**:
```bash
# After model changes, recreate test database to verify schema
# (Uses reset/re-import pattern per constitution)
```

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| F064 incomplete | Add missing FK in T009 if needed |
| Circular import issues | Use string references for relationships ("RecipeSnapshot") |
| Index creation fails | Verify index syntax matches existing patterns |

## Definition of Done Checklist

- [ ] RecipeSnapshot.production_run_id is nullable=True
- [ ] EventProductionTarget.recipe_snapshot_id FK added (nullable, indexed)
- [ ] EventAssemblyTarget.finished_good_snapshot_id FK added (nullable, indexed)
- [ ] Relationships defined for both new FKs
- [ ] FinishedGoodSnapshot verified to have planning_snapshot_id
- [ ] All models import without errors
- [ ] Activity log entry added

## Review Guidance

Reviewers should verify:
1. FK definitions match data-model.md specification
2. ON DELETE behavior is RESTRICT for snapshot FKs
3. Nullable and index settings correct
4. Relationships use lazy="joined" for eager loading
5. F064 verification documented

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

- 2026-01-24T19:47:15Z – system – lane=planned – Prompt created.
