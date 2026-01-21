---
work_package_id: "WP05"
subtasks:
  - "T022"
  - "T023"
  - "T024"
  - "T025"
  - "T026"
  - "T027"
title: "Staleness Detection Enhancements"
phase: "Phase 2 - Parallel Track"
lane: "for_review"
assignee: ""
agent: "claude-opus"
shell_pid: "10342"
review_status: ""
reviewed_by: ""
dependencies: ["WP01"]
history:
  - timestamp: "2026-01-20T20:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP05 – Staleness Detection Enhancements

## Implementation Command

```bash
spec-kitty implement WP05 --base WP01
```

Depends on WP01 (session pattern established).

**Codex Parallelizable**: YES - This WP can be assigned to Codex for parallel execution with WP04, WP06, WP07 after WP01 completes.

**Schema Change Warning**: This WP adds `updated_at` to Composition model. Per constitution, this requires export/reset/import cycle.

---

## Objectives & Success Criteria

**Primary Objective**: Add missing mutation detection for Composition updates and FinishedUnit yield changes.

**Success Criteria**:
1. Composition model has `updated_at` timestamp field
2. Staleness detects when Composition is modified (not just created)
3. Staleness detects when FinishedUnit yield changes
4. Tests verify all mutation types trigger staleness
5. Schema change documented for export/reset/import

**Key Acceptance Checkpoints**:
- [ ] Composition.updated_at field added to model
- [ ] Plan marked stale when Composition updated
- [ ] Plan marked stale when FinishedUnit yield changed
- [ ] Non-schema changes (display name) do NOT trigger staleness

---

## Context & Constraints

### Supporting Documents
- **Research**: `kitty-specs/060-architecture-hardening-service-boundaries/research.md` - Section 4 (Staleness Detection Analysis)
- **Data Model**: `kitty-specs/060-architecture-hardening-service-boundaries/data-model.md` - Composition model change
- **Plan**: `kitty-specs/060-architecture-hardening-service-boundaries/plan.md` - WP05 section

### File Locations
- `src/models/composition.py` line 99: Add `updated_at` field
- `src/services/planning/planning_service.py`:
  - `_check_staleness_impl()` at lines 500-562
  - Currently checks Composition.created_at at line 555

### Currently Tracked Mutations (from research)
| Source | Field Checked | Line |
|--------|---------------|------|
| Event | `last_modified` | 515 |
| EventAssemblyTarget | `updated_at` | 523 |
| EventProductionTarget | `updated_at` | 531 |
| Recipe | `last_modified` | 539 |
| FinishedGood | `updated_at` | 547 |
| Composition | `created_at` only | 555 |

### Missing Checks
- Composition `updated_at` (field doesn't exist yet)
- FinishedUnit `updated_at` (field exists, not checked)

---

## Subtasks & Detailed Guidance

### Subtask T022 – Add updated_at to Composition model

**Purpose**: Enable tracking of Composition modifications for staleness detection.

**Steps**:

1. Open `src/models/composition.py`

2. Locate the existing `created_at` field (around line 99):
   ```python
   created_at = Column(DateTime, nullable=False, default=utc_now)
   ```

3. Add `updated_at` field immediately after:
   ```python
   from src.utils.db import utc_now

   class Composition(BaseModel):
       # ... existing fields ...

       created_at = Column(DateTime, nullable=False, default=utc_now)
       updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)
   ```

4. Verify the import for `utc_now` is present

5. Add test for auto-update behavior:
   ```python
   def test_composition_updated_at_auto_updates():
       """Verify updated_at changes when composition modified."""
       with session_scope() as session:
           # Create composition
           comp = Composition(...)
           session.add(comp)
           session.flush()
           original_updated = comp.updated_at

           # Wait briefly to ensure time difference
           import time
           time.sleep(0.01)

           # Modify composition
           comp.quantity = comp.quantity + 1
           session.flush()

           # updated_at should have changed
           assert comp.updated_at > original_updated
   ```

6. Document schema change (see T027)

**Files**:
- `src/models/composition.py` (add 1 line)
- `src/tests/models/test_composition.py` (add ~20 lines)

**Parallel?**: No - must complete before T023-T025

**Notes**:
- This is a schema change requiring export/reset/import
- Follow existing pattern from BaseModel for updated_at
- The `onupdate=utc_now` is crucial for auto-update behavior

---

### Subtask T023 – Add _get_latest_composition_updated_timestamp() helper

**Purpose**: Create helper function to find the latest Composition modification time for recipes in a plan.

**Steps**:

1. Open `src/services/planning/planning_service.py`

2. Locate the existing staleness helper pattern (around line 500-562)

3. Add new helper function following the same pattern:
   ```python
   def _get_latest_composition_updated_timestamp(
       recipe_ids: List[int], session
   ) -> Optional[datetime]:
       """
       Get the latest Composition.updated_at for given recipes.

       Args:
           recipe_ids: List of recipe IDs in the plan
           session: SQLAlchemy session

       Returns:
           Latest updated_at timestamp, or None if no compositions
       """
       from src.models.composition import Composition

       if not recipe_ids:
           return None

       result = session.query(func.max(Composition.updated_at)).filter(
           Composition.recipe_id.in_(recipe_ids)
       ).scalar()

       return result
   ```

4. Consider including nested recipe compositions:
   ```python
   # If recipes can reference other recipes, may need recursive query
   # Or collect all recipe IDs first, then query compositions
   ```

**Files**:
- `src/services/planning/planning_service.py` (add ~25 lines)

**Parallel?**: Yes - can proceed in parallel with T024 after T022

**Notes**:
- Follow pattern of existing `_get_latest_*` helpers
- Use `func.max()` for efficient database query
- Handle empty recipe list gracefully

---

### Subtask T024 – Add _get_latest_finished_unit_timestamp() helper

**Purpose**: Create helper function to find the latest FinishedUnit modification time for a plan.

**Steps**:

1. FinishedUnit already has `updated_at` (confirmed in research)

2. Add helper function:
   ```python
   def _get_latest_finished_unit_timestamp(
       finished_unit_ids: List[int], session
   ) -> Optional[datetime]:
       """
       Get the latest FinishedUnit.updated_at for given units.

       Args:
           finished_unit_ids: List of FinishedUnit IDs in the plan
           session: SQLAlchemy session

       Returns:
           Latest updated_at timestamp, or None if no units
       """
       from src.models.finished_unit import FinishedUnit

       if not finished_unit_ids:
           return None

       result = session.query(func.max(FinishedUnit.updated_at)).filter(
           FinishedUnit.id.in_(finished_unit_ids)
       ).scalar()

       return result
   ```

3. Identify where finished_unit_ids come from:
   - Production targets reference FinishedUnit
   - May need to extract IDs from EventProductionTarget

**Files**:
- `src/services/planning/planning_service.py` (add ~25 lines)

**Parallel?**: Yes - can proceed in parallel with T023 after T022

**Notes**:
- FinishedUnit already has updated_at - just need the query
- Yield changes affect batch calculations, so this is important

---

### Subtask T025 – Update _check_staleness_impl() to call new helpers

**Purpose**: Integrate new staleness checks into the main staleness detection logic.

**Steps**:

1. Locate `_check_staleness_impl()` (lines 500-562)

2. Add Composition.updated_at check after existing Composition.created_at check:
   ```python
   # Existing check (line ~555)
   latest_composition_created = _get_latest_composition_created_timestamp(...)
   if latest_composition_created and latest_composition_created > plan.calculated_at:
       return True, "New recipe composition added since plan calculation"

   # NEW: Check Composition updates
   latest_composition_updated = _get_latest_composition_updated_timestamp(
       recipe_ids, session
   )
   if latest_composition_updated and latest_composition_updated > plan.calculated_at:
       return True, "Recipe composition modified since plan calculation"
   ```

3. Add FinishedUnit check:
   ```python
   # NEW: Check FinishedUnit yield changes
   finished_unit_ids = _get_finished_unit_ids_from_plan(plan, session)
   latest_fu_updated = _get_latest_finished_unit_timestamp(
       finished_unit_ids, session
   )
   if latest_fu_updated and latest_fu_updated > plan.calculated_at:
       return True, "Finished unit yield changed since plan calculation"
   ```

4. Extract finished_unit_ids helper if needed:
   ```python
   def _get_finished_unit_ids_from_plan(plan, session) -> List[int]:
       """Extract FinishedUnit IDs from production targets."""
       from src.models.event import EventProductionTarget

       targets = session.query(EventProductionTarget).filter(
           EventProductionTarget.event_id == plan.event_id
       ).all()

       return [t.finished_unit_id for t in targets if t.finished_unit_id]
   ```

5. Verify timestamp comparison uses normalized datetime (existing pattern)

**Files**:
- `src/services/planning/planning_service.py` (modify ~30 lines)

**Parallel?**: No - depends on T023, T024

**Notes**:
- Follow existing pattern for timestamp comparison
- Use `_normalize_datetime()` if needed for SQLite compatibility
- Return descriptive reason string for UI display

---

### Subtask T026 – Add tests for each mutation type

**Purpose**: Comprehensive tests for staleness detection.

**Steps**:

1. Add test for Composition update staleness:
   ```python
   def test_staleness_detects_composition_update():
       """Verify plan marked stale when composition modified."""
       with session_scope() as session:
           # Create plan
           plan = planning_service.calculate_plan(event_id, session=session)
           session.flush()

           # Modify a composition
           comp = session.query(Composition).first()
           comp.quantity = comp.quantity + 1
           session.flush()

           # Check staleness
           is_stale, reason = planning_service.check_staleness(plan.id, session=session)
           assert is_stale is True
           assert "composition modified" in reason.lower()
   ```

2. Add test for FinishedUnit yield change:
   ```python
   def test_staleness_detects_finished_unit_yield_change():
       """Verify plan marked stale when yield changes."""
       with session_scope() as session:
           # Create plan with production target
           plan = planning_service.calculate_plan(event_id, session=session)
           session.flush()

           # Modify finished unit yield
           fu = session.query(FinishedUnit).first()
           fu.items_per_batch = fu.items_per_batch + 1  # Yield change
           session.flush()

           # Check staleness
           is_stale, reason = planning_service.check_staleness(plan.id, session=session)
           assert is_stale is True
           assert "yield" in reason.lower() or "finished unit" in reason.lower()
   ```

3. Add test for non-staleness (display name change):
   ```python
   def test_display_name_change_not_stale():
       """Verify display name change does NOT trigger staleness."""
       with session_scope() as session:
           # Create plan
           plan = planning_service.calculate_plan(event_id, session=session)
           session.flush()

           # Modify display name (non-schema change)
           # Note: This may update updated_at, which would trigger staleness
           # If that's not desired, need to be more selective about what triggers

           # This test documents expected behavior
           pass
   ```

4. Add test for fresh plan (no changes):
   ```python
   def test_fresh_plan_not_stale():
       """Verify plan not marked stale if nothing changed."""
       with session_scope() as session:
           plan = planning_service.calculate_plan(event_id, session=session)

           is_stale, reason = planning_service.check_staleness(plan.id, session=session)
           assert is_stale is False
   ```

**Files**:
- `src/tests/services/planning/test_planning_service.py` (add ~100 lines)

**Parallel?**: No - depends on T022-T025

**Notes**:
- Test each mutation type individually
- Document expected behavior for edge cases
- Consider: should display name change trigger staleness?

---

### Subtask T027 – Document schema change for export/reset/import

**Purpose**: Document the Composition.updated_at schema change for users upgrading.

**Steps**:

1. Update or create migration documentation:
   ```markdown
   # Schema Change: Composition.updated_at

   **Version**: 060-architecture-hardening
   **Date**: 2026-01-20

   ## Change
   Added `updated_at` column to `composition` table.

   ## Migration Required
   Per constitution principle VI (Desktop Phase), schema changes use export/reset/import:

   1. **Export data**: Use app's Export function to save all data to JSON
   2. **Reset database**: Delete `bake_tracker.db` file
   3. **Restart app**: Database will be recreated with new schema
   4. **Import data**: Use app's Import function to restore data

   ## Impact
   - Existing compositions will have `updated_at = created_at` after import
   - No data loss expected
   - Staleness detection will now track composition modifications
   ```

2. Add to release notes or changelog if applicable

3. Consider adding in-app notification for schema change (future feature)

**Files**:
- `docs/migrations/060-composition-updated-at.md` (new, ~30 lines)

**Parallel?**: Yes - can be done anytime after T022

**Notes**:
- This is documentation, not code
- Follow existing migration doc pattern if one exists
- May want to add to README or CHANGELOG

---

## Test Strategy

**Required Tests**:
1. Composition.updated_at auto-updates on modification
2. Staleness detects Composition update
3. Staleness detects FinishedUnit yield change
4. Fresh plan not marked stale
5. Existing staleness checks still work

**Test Commands**:
```bash
# Run composition model tests
./run-tests.sh src/tests/models/test_composition.py -v

# Run planning staleness tests
./run-tests.sh src/tests/services/planning/test_planning_service.py -v -k "stale"

# Run all tests
./run-tests.sh -v
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Schema change breaks existing data | Document export/reset/import; test import |
| Staleness over-triggers on display name | Document which changes should/shouldn't trigger |
| Missing timestamp comparison normalization | Use existing _normalize_datetime pattern |

---

## Definition of Done Checklist

- [ ] T022: Composition.updated_at field added
- [ ] T023: _get_latest_composition_updated_timestamp() helper implemented
- [ ] T024: _get_latest_finished_unit_timestamp() helper implemented
- [ ] T025: _check_staleness_impl() calls new helpers
- [ ] T026: Tests for all mutation types pass
- [ ] T027: Schema change documented
- [ ] Full test suite passes

---

## Review Guidance

**Key Review Checkpoints**:
1. Composition.updated_at has `onupdate=utc_now`
2. Staleness helpers follow existing pattern
3. Timestamp comparison uses normalization if needed
4. Tests verify each mutation type independently

---

## Activity Log

- 2026-01-20T20:00:00Z – system – lane=planned – Prompt generated via /spec-kitty.tasks
- 2026-01-21T03:44:36Z – claude-opus – shell_pid=10342 – lane=doing – Started implementation via workflow command
- 2026-01-21T03:52:49Z – claude-opus – shell_pid=10342 – lane=for_review – Ready for review: Added Composition.updated_at, enhanced staleness detection for composition updates and FinishedUnit yield changes, added 3 new tests, documented schema change. All 2560 tests pass.
