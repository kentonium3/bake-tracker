---
work_package_id: WP04
title: MaterialUnit & FinishedUnit Snapshot Import
lane: "doing"
dependencies: [WP02, WP03]
base_branch: 081-snapshot-export-coverage-WP03
base_commit: e7bc2958640944d1a1a5555b53a4b774fac3dc75
created_at: '2026-01-28T20:29:36.701686+00:00'
subtasks:
- T015
- T016
- T017
- T018
phase: Phase 2 - Import Functions
assignee: ''
agent: "claude"
shell_pid: "78693"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-01-28T18:40:28Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP04 – MaterialUnit & FinishedUnit Snapshot Import

## IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Implementation Command

```bash
spec-kitty implement WP04 --base WP03
```

Depends on WP02 (MaterialUnit/FinishedUnit exports) and WP03 (import infrastructure).

---

## Objectives & Success Criteria

Complete import handlers for all 4 snapshot types.

**Success Criteria:**
- [ ] All 4 snapshot types import correctly
- [ ] FK resolution works for all parent entity types
- [ ] Full export → import cycle works end-to-end
- [ ] Import completes in <10 seconds for 1000 snapshots (SC-005)
- [ ] Delete order correct for all 4 snapshot types

---

## Context & Constraints

**Prerequisites:**
- WP03 established import infrastructure (delete order, handler pattern)
- WP02 completed MaterialUnit and FinishedUnit exports

**Key Files to Modify:**
- `src/services/coordinated_export_service.py` - Add remaining import handlers

---

## Subtasks & Detailed Guidance

### Subtask T015 – Implement `material_unit_snapshots` Import Handler

**Purpose**: Import MaterialUnitSnapshot records with FK resolution.

**Steps**:

1. Add model import and delete statement in `_import_complete_impl()`:
   ```python
   from src.models.material_unit_snapshot import MaterialUnitSnapshot
   # In delete section (before MaterialUnit deletion):
   session.query(MaterialUnitSnapshot).delete()
   ```

2. Add handler in `_import_entity_records()`:

```python
elif entity_type == "material_unit_snapshots":
    # Feature 081: MaterialUnitSnapshot import with slug-based FK resolution
    from src.models.material_unit_snapshot import MaterialUnitSnapshot
    from src.models.material_unit import MaterialUnit
    from uuid import UUID

    mu_slug = record.get("material_unit_slug")
    if not mu_slug:
        logger.warning(f"MaterialUnitSnapshot skipped: no material_unit_slug provided")
        continue

    # Resolve material_unit FK by slug
    material_unit = (
        session.query(MaterialUnit)
        .filter(MaterialUnit.slug == mu_slug)
        .first()
    )
    if not material_unit:
        logger.warning(
            f"MaterialUnitSnapshot skipped: material_unit '{mu_slug}' not found"
        )
        continue

    # Parse UUID - preserve exactly from export
    uuid_str = record.get("uuid")
    uuid_val = UUID(uuid_str) if uuid_str else None

    # Parse snapshot_date
    snapshot_date = None
    snapshot_date_str = record.get("snapshot_date")
    if snapshot_date_str:
        from datetime import datetime
        try:
            if snapshot_date_str.endswith('Z'):
                snapshot_date_str = snapshot_date_str[:-1] + '+00:00'
            snapshot_date = datetime.fromisoformat(snapshot_date_str)
        except ValueError:
            logger.warning(f"MaterialUnitSnapshot: invalid snapshot_date '{snapshot_date_str}'")

    obj = MaterialUnitSnapshot(
        uuid=uuid_val,
        material_unit_id=material_unit.id,
        snapshot_date=snapshot_date,
        is_backfilled=record.get("is_backfilled", False),
        # JSON data preserved exactly
        definition_data=record.get("definition_data", "{}"),
    )
    session.add(obj)
    imported_count += 1
```

**Files**:
- `src/services/coordinated_export_service.py`

**Parallel?**: Yes - can be implemented alongside T016

**Validation**:
- [ ] FK resolved via material_unit_slug
- [ ] Delete order includes MaterialUnitSnapshot before MaterialUnit
- [ ] Follows same pattern as WP03 handlers

---

### Subtask T016 – Implement `finished_unit_snapshots` Import Handler

**Purpose**: Import FinishedUnitSnapshot records with FK resolution.

**Steps**:

1. Add model import and delete statement:
   ```python
   from src.models.finished_unit_snapshot import FinishedUnitSnapshot
   # In delete section (before FinishedUnit deletion):
   session.query(FinishedUnitSnapshot).delete()
   ```

2. Add handler in `_import_entity_records()`:

```python
elif entity_type == "finished_unit_snapshots":
    # Feature 081: FinishedUnitSnapshot import with slug-based FK resolution
    from src.models.finished_unit_snapshot import FinishedUnitSnapshot
    from src.models.finished_unit import FinishedUnit
    from uuid import UUID

    fu_slug = record.get("finished_unit_slug")
    if not fu_slug:
        logger.warning(f"FinishedUnitSnapshot skipped: no finished_unit_slug provided")
        continue

    # Resolve finished_unit FK by slug
    finished_unit = (
        session.query(FinishedUnit)
        .filter(FinishedUnit.slug == fu_slug)
        .first()
    )
    if not finished_unit:
        logger.warning(
            f"FinishedUnitSnapshot skipped: finished_unit '{fu_slug}' not found"
        )
        continue

    # Parse UUID - preserve exactly from export
    uuid_str = record.get("uuid")
    uuid_val = UUID(uuid_str) if uuid_str else None

    # Parse snapshot_date
    snapshot_date = None
    snapshot_date_str = record.get("snapshot_date")
    if snapshot_date_str:
        from datetime import datetime
        try:
            if snapshot_date_str.endswith('Z'):
                snapshot_date_str = snapshot_date_str[:-1] + '+00:00'
            snapshot_date = datetime.fromisoformat(snapshot_date_str)
        except ValueError:
            logger.warning(f"FinishedUnitSnapshot: invalid snapshot_date '{snapshot_date_str}'")

    obj = FinishedUnitSnapshot(
        uuid=uuid_val,
        finished_unit_id=finished_unit.id,
        snapshot_date=snapshot_date,
        is_backfilled=record.get("is_backfilled", False),
        # JSON data preserved exactly
        definition_data=record.get("definition_data", "{}"),
    )
    session.add(obj)
    imported_count += 1
```

**Files**:
- `src/services/coordinated_export_service.py`

**Parallel?**: Yes - can be implemented alongside T015

---

### Subtask T017 – Verify Complete Delete Order for All 4 Snapshot Types

**Purpose**: Ensure delete order is correct to avoid FK constraint violations.

**Steps**:

1. **Review delete section** in `_import_complete_impl()` (around line 1153-1175)

2. **Verify order** - snapshots must be deleted BEFORE their parent entities:
   ```python
   # Correct delete order (snapshots before parents)
   session.query(RecipeSnapshot).delete()
   session.query(FinishedGoodSnapshot).delete()
   session.query(MaterialUnitSnapshot).delete()
   session.query(FinishedUnitSnapshot).delete()
   # ... then parent deletions ...
   session.query(ProductionRun).delete()
   session.query(FinishedUnit).delete()  # After FinishedUnitSnapshot
   session.query(FinishedGood).delete()  # After FinishedGoodSnapshot
   session.query(MaterialUnit).delete()  # After MaterialUnitSnapshot
   session.query(Recipe).delete()        # After RecipeSnapshot
   # ... etc
   ```

3. **Add comment block** documenting the delete order rationale:
   ```python
   # Feature 081: Delete snapshots before their parents to avoid FK violations
   # Order: RecipeSnapshot, FinishedGoodSnapshot, MaterialUnitSnapshot, FinishedUnitSnapshot
   # Then existing delete order for parent entities
   ```

**Files**:
- `src/services/coordinated_export_service.py` (verify delete order ~line 1153-1175)

**Parallel?**: No - must verify after T015/T016

**Validation**:
- [ ] All 4 snapshot types deleted before their parents
- [ ] Comment documents the order rationale
- [ ] No FK constraint violations on import

---

### Subtask T018 – Manual Smoke Test: Export → Clear → Import Cycle

**Purpose**: Verify end-to-end export/import works with all 4 snapshot types.

**Steps**:

1. **Create test script** or run interactively:

```python
# smoke_test_snapshots.py (or run in Python REPL)
import tempfile
import os
from src.services.coordinated_export_service import export_complete, import_complete
from src.services.database import session_scope

# Step 1: Export current database
with tempfile.TemporaryDirectory() as export_dir:
    print(f"Exporting to {export_dir}")
    manifest = export_complete(export_dir)

    # Check snapshot files exist
    snapshot_files = [f.filename for f in manifest.files if 'snapshot' in f.filename]
    print(f"Snapshot files: {snapshot_files}")

    # Step 2: Count records before import
    with session_scope() as session:
        from src.models.recipe_snapshot import RecipeSnapshot
        from src.models.finished_good_snapshot import FinishedGoodSnapshot
        from src.models.material_unit_snapshot import MaterialUnitSnapshot
        from src.models.finished_unit_snapshot import FinishedUnitSnapshot

        counts_before = {
            "recipe_snapshots": session.query(RecipeSnapshot).count(),
            "finished_good_snapshots": session.query(FinishedGoodSnapshot).count(),
            "material_unit_snapshots": session.query(MaterialUnitSnapshot).count(),
            "finished_unit_snapshots": session.query(FinishedUnitSnapshot).count(),
        }
        print(f"Counts before: {counts_before}")

    # Step 3: Import (which clears and re-imports)
    result = import_complete(export_dir)
    print(f"Import result: {result}")

    # Step 4: Verify counts match
    with session_scope() as session:
        counts_after = {
            "recipe_snapshots": session.query(RecipeSnapshot).count(),
            "finished_good_snapshots": session.query(FinishedGoodSnapshot).count(),
            "material_unit_snapshots": session.query(MaterialUnitSnapshot).count(),
            "finished_unit_snapshots": session.query(FinishedUnitSnapshot).count(),
        }
        print(f"Counts after: {counts_after}")

    # Verify counts match
    for key in counts_before:
        assert counts_before[key] == counts_after[key], f"Count mismatch for {key}"

    print("SUCCESS: Export/import cycle completed with matching counts")
```

2. **Run the test**:
   ```bash
   cd /Users/kentgale/Vaults-repos/bake-tracker
   source venv/bin/activate
   python -c "exec(open('smoke_test_snapshots.py').read())"
   ```

3. **Expected output**:
   - 4 snapshot files in export
   - Counts match before and after import
   - No errors or FK violations

**Files**:
- No file changes (manual verification)

**Parallel?**: No - must run after all handlers complete

**Validation**:
- [ ] Export produces 4 snapshot JSON files
- [ ] Import completes without errors
- [ ] Record counts match before and after

---

## Definition of Done Checklist

- [ ] material_unit_snapshots import handler implemented
- [ ] finished_unit_snapshots import handler implemented
- [ ] All 4 snapshot types in delete order (before parents)
- [ ] Manual smoke test passes
- [ ] Export → import cycle preserves all snapshot data
- [ ] No FK constraint violations
- [ ] No lint errors

---

## Risks & Mitigations

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| FK constraint on import | Medium | Verify delete order explicitly |
| Count mismatch after import | Low | Smoke test catches this |

---

## Review Guidance

**Reviewers should verify:**
1. All 4 import handlers follow consistent pattern
2. Delete order is correct (snapshots before parents)
3. Smoke test demonstrates working export/import cycle
4. Missing parent handling is consistent (skip + warning)

---

## Activity Log

- 2026-01-28T18:40:28Z – system – lane=planned – Prompt created.
- 2026-01-28T20:32:03Z – unknown – shell_pid=77961 – lane=for_review – MaterialUnitSnapshot and FinishedUnitSnapshot import handlers complete
- 2026-01-28T20:32:10Z – claude – shell_pid=78693 – lane=doing – Started review via workflow command
