---
work_package_id: WP02
title: MaterialUnit & FinishedUnit Snapshot Export
lane: "doing"
dependencies: []
base_branch: main
base_commit: 14b21af6aec34176a033e5281672c3e9f43e6b31
created_at: '2026-01-28T18:48:41.568875+00:00'
subtasks:
- T006
- T007
- T008
- T009
- T010
phase: Phase 1 - Export Functions
assignee: ''
agent: "claude-lead"
shell_pid: "76436"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-01-28T18:40:28Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP02 – MaterialUnit & FinishedUnit Snapshot Export

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
spec-kitty implement WP02 --base WP01
```

Depends on WP01 - branches from WP01's completed work.

---

## Objectives & Success Criteria

Complete the export functions for remaining snapshot types: MaterialUnitSnapshot and FinishedUnitSnapshot.

**Success Criteria:**
- [ ] `material_unit_snapshots.json` exported with correct structure
- [ ] `finished_unit_snapshots.json` exported with correct structure
- [ ] All 4 snapshot types now export successfully
- [ ] Manifest includes all 4 snapshot file entries
- [ ] Export completes in <5 seconds for 1000 snapshots (SC-004)

---

## Context & Constraints

**Reference Documents:**
- Feature spec: `kitty-specs/081-snapshot-export-coverage/spec.md`
- Data model: `kitty-specs/081-snapshot-export-coverage/data-model.md`

**Key Files to Modify:**
- `src/services/coordinated_export_service.py` - Add remaining export functions

**Prerequisites (from WP01):**
- RecipeSnapshot and FinishedGoodSnapshot exports already implemented
- DEPENDENCY_ORDER structure established
- Pattern for snapshot export functions defined

---

## Subtasks & Detailed Guidance

### Subtask T006 – Add MaterialUnitSnapshot Model Import and DEPENDENCY_ORDER Entry

**Purpose**: Register MaterialUnitSnapshot in the export system.

**Steps**:
1. Add import at top of `coordinated_export_service.py`:
   ```python
   from src.models.material_unit_snapshot import MaterialUnitSnapshot
   ```

2. Add entry to DEPENDENCY_ORDER:
   ```python
   "material_unit_snapshots": (21, ["material_units"]),
   ```
   - Import order 21 (after finished_good_snapshots at 20)
   - Dependency on "material_units"

**Files**:
- `src/services/coordinated_export_service.py`

**Parallel?**: No - must complete before T007

---

### Subtask T007 – Implement `_export_material_unit_snapshots()` Function

**Purpose**: Export all MaterialUnitSnapshot records to JSON.

**Steps**:
1. Add function after `_export_finished_good_snapshots()`:

```python
def _export_material_unit_snapshots(output_dir: Path, session: Session) -> FileEntry:
    """Export all material unit snapshots to JSON file with FK resolution.

    Feature 081: MaterialUnitSnapshot export for material pricing history.
    Exports in chronological order (oldest first) per FR-015.
    """
    snapshots = (
        session.query(MaterialUnitSnapshot)
        .options(joinedload(MaterialUnitSnapshot.material_unit))
        .order_by(MaterialUnitSnapshot.snapshot_date)
        .all()
    )

    records = []
    for snap in snapshots:
        records.append(
            {
                "uuid": str(snap.uuid) if snap.uuid else None,
                # FK resolved by material_unit slug
                "material_unit_slug": snap.material_unit.slug if snap.material_unit else None,
                # Snapshot metadata
                "snapshot_date": snap.snapshot_date.isoformat() if snap.snapshot_date else None,
                "is_backfilled": snap.is_backfilled,
                # JSON data preserved exactly
                "definition_data": snap.definition_data,
            }
        )

    return _write_entity_file(output_dir, "material_unit_snapshots", records)
```

**Files**:
- `src/services/coordinated_export_service.py`

**Parallel?**: Yes - can be implemented alongside T008/T009

**Validation**:
- [ ] Function follows same pattern as recipe/finished_good snapshot exports
- [ ] Uses material_unit_slug for FK resolution
- [ ] Preserves definition_data exactly

---

### Subtask T008 – Add FinishedUnitSnapshot Model Import and DEPENDENCY_ORDER Entry

**Purpose**: Register FinishedUnitSnapshot in the export system.

**Steps**:
1. Add import at top of file:
   ```python
   from src.models.finished_unit_snapshot import FinishedUnitSnapshot
   ```

2. Add entry to DEPENDENCY_ORDER:
   ```python
   "finished_unit_snapshots": (22, ["finished_units"]),
   ```
   - Import order 22 (after material_unit_snapshots at 21)
   - Dependency on "finished_units"

**Files**:
- `src/services/coordinated_export_service.py`

**Parallel?**: Yes - can be done alongside T006/T007

---

### Subtask T009 – Implement `_export_finished_unit_snapshots()` Function

**Purpose**: Export all FinishedUnitSnapshot records to JSON.

**Steps**:
1. Add function after `_export_material_unit_snapshots()`:

```python
def _export_finished_unit_snapshots(output_dir: Path, session: Session) -> FileEntry:
    """Export all finished unit snapshots to JSON file with FK resolution.

    Feature 081: FinishedUnitSnapshot export for unit cost history.
    Exports in chronological order (oldest first) per FR-015.
    """
    snapshots = (
        session.query(FinishedUnitSnapshot)
        .options(joinedload(FinishedUnitSnapshot.finished_unit))
        .order_by(FinishedUnitSnapshot.snapshot_date)
        .all()
    )

    records = []
    for snap in snapshots:
        records.append(
            {
                "uuid": str(snap.uuid) if snap.uuid else None,
                # FK resolved by finished_unit slug
                "finished_unit_slug": snap.finished_unit.slug if snap.finished_unit else None,
                # Snapshot metadata
                "snapshot_date": snap.snapshot_date.isoformat() if snap.snapshot_date else None,
                "is_backfilled": snap.is_backfilled,
                # JSON data preserved exactly
                "definition_data": snap.definition_data,
            }
        )

    return _write_entity_file(output_dir, "finished_unit_snapshots", records)
```

**Files**:
- `src/services/coordinated_export_service.py`

**Parallel?**: Yes - can be implemented alongside T007

---

### Subtask T010 – Complete Export Orchestration and Verify Manifest

**Purpose**: Wire remaining export functions and verify complete manifest output.

**Steps**:
1. Add calls to `_export_complete_impl()` after WP01's additions:
   ```python
   # Feature 081: Remaining snapshot exports
   manifest.files.append(_export_material_unit_snapshots(output_dir, session))
   manifest.files.append(_export_finished_unit_snapshots(output_dir, session))
   ```

2. Verify manifest structure by examining output:
   - All 4 snapshot files should appear in manifest.json
   - Import order should be: recipe_snapshots(19), finished_good_snapshots(20), material_unit_snapshots(21), finished_unit_snapshots(22)

3. Run manual export test:
   ```bash
   # From project root with venv activated
   python -c "
   from src.services.coordinated_export_service import export_complete
   import tempfile
   import os
   with tempfile.TemporaryDirectory() as tmpdir:
       manifest = export_complete(tmpdir)
       print(f'Exported {len(manifest.files)} files')
       for f in manifest.files:
           if 'snapshot' in f.filename:
               print(f'  - {f.filename}: {f.record_count} records')
   "
   ```

**Files**:
- `src/services/coordinated_export_service.py` (modify `_export_complete_impl()`)

**Parallel?**: No - depends on T007 and T009

**Validation**:
- [ ] Export produces 4 snapshot JSON files
- [ ] Manifest lists all 4 with correct import_order
- [ ] Manual test runs without errors

---

## Definition of Done Checklist

- [ ] MaterialUnitSnapshot and FinishedUnitSnapshot models imported
- [ ] DEPENDENCY_ORDER includes all 4 snapshot types (orders 19-22)
- [ ] All 4 export functions implemented and follow same pattern
- [ ] Export orchestration calls all 4 snapshot export functions
- [ ] Manual export test produces 4 snapshot JSON files
- [ ] Manifest includes all 4 snapshot entries with correct order
- [ ] No lint errors

---

## Risks & Mitigations

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Merge conflict with WP01 | Medium | Use --base WP01 to branch from WP01's work |
| MaterialUnit/FinishedUnit have no snapshots in DB | Low | Export handles empty list gracefully |

---

## Review Guidance

**Reviewers should verify:**
1. All 4 snapshot types now have export functions
2. DEPENDENCY_ORDER entries 19-22 are sequential and have correct dependencies
3. Export functions are consistent in structure
4. `_export_complete_impl()` calls all 4 functions in order
5. Manual export produces correct file count

---

## Activity Log

- 2026-01-28T18:40:28Z – system – lane=planned – Prompt created.
- 2026-01-28T18:52:07Z – unknown – shell_pid=68803 – lane=for_review – Export functions implemented for MaterialUnitSnapshot and FinishedUnitSnapshot
- 2026-01-28T20:24:14Z – claude-lead – shell_pid=76436 – lane=doing – Started review via workflow command
