---
work_package_id: WP01
title: Recipe & FinishedGood Snapshot Export
lane: "doing"
dependencies: []
base_branch: main
base_commit: 2ad59dfb928e8e8071e55871259216e9f5ff27a4
created_at: '2026-01-28T18:48:39.759119+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
phase: Phase 1 - Export Functions
assignee: ''
agent: ''
shell_pid: "68763"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-01-28T18:40:28Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP01 – Recipe & FinishedGood Snapshot Export

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
spec-kitty implement WP01
```

No dependencies - this is the starting work package.

---

## Objectives & Success Criteria

Add export functions for RecipeSnapshot and FinishedGoodSnapshot entities to `coordinated_export_service.py`.

**Success Criteria:**
- [ ] `recipe_snapshots.json` exported with correct structure (uuid, recipe_slug, snapshot_date, recipe_data, ingredients_data)
- [ ] `finished_good_snapshots.json` exported with correct structure (uuid, finished_good_slug, snapshot_date, definition_data)
- [ ] Snapshots exported in chronological order (oldest first) per FR-015
- [ ] UUIDs and JSON data preserved exactly per FR-010, FR-012
- [ ] DEPENDENCY_ORDER includes both new entity types

---

## Context & Constraints

**Reference Documents:**
- Feature spec: `kitty-specs/081-snapshot-export-coverage/spec.md`
- Implementation plan: `kitty-specs/081-snapshot-export-coverage/plan.md`
- Data model: `kitty-specs/081-snapshot-export-coverage/data-model.md`
- Research: `kitty-specs/081-snapshot-export-coverage/research.md`

**Key Files to Modify:**
- `src/services/coordinated_export_service.py` - Add export functions

**Pattern Reference:**
Follow the existing `_export_finished_units()` pattern at line 728-759 of coordinated_export_service.py.

**Constraints:**
- Must use slug-based FK resolution (recipe_slug, finished_good_slug)
- Must preserve exact UUID (no regeneration)
- Must preserve exact timestamp (no modification)
- Must preserve JSON data exactly (recipe_data, ingredients_data, definition_data)

---

## Subtasks & Detailed Guidance

### Subtask T001 – Add RecipeSnapshot Model Import and DEPENDENCY_ORDER Entry

**Purpose**: Register RecipeSnapshot in the export system so it can be exported and imported in the correct order.

**Steps**:
1. Add import at top of `coordinated_export_service.py`:
   ```python
   from src.models.recipe_snapshot import RecipeSnapshot
   ```

2. Add entry to DEPENDENCY_ORDER dict (after line ~128):
   ```python
   "recipe_snapshots": (19, ["recipes"]),
   ```
   - Import order 19 places it after all parent entities
   - Dependency on "recipes" ensures recipes import first

**Files**:
- `src/services/coordinated_export_service.py` (modify ~lines 33-51 for import, ~lines 106-128 for DEPENDENCY_ORDER)

**Parallel?**: No - must complete before T002

**Notes**:
- Import order numbers 1-18 are already used by existing entities
- Recipe snapshots depend only on recipes (not production_runs for export purposes)

---

### Subtask T002 – Implement `_export_recipe_snapshots()` Function

**Purpose**: Export all RecipeSnapshot records to JSON with slug-based FK resolution.

**Steps**:
1. Add function after `_export_production_runs()` (around line 860):

```python
def _export_recipe_snapshots(output_dir: Path, session: Session) -> FileEntry:
    """Export all recipe snapshots to JSON file with FK resolution.

    Feature 081: RecipeSnapshot export for cost history preservation.
    Exports in chronological order (oldest first) per FR-015.
    """
    snapshots = (
        session.query(RecipeSnapshot)
        .options(joinedload(RecipeSnapshot.recipe))
        .order_by(RecipeSnapshot.snapshot_date)
        .all()
    )

    records = []
    for snap in snapshots:
        records.append(
            {
                "uuid": str(snap.uuid) if snap.uuid else None,
                # FK resolved by recipe slug
                "recipe_slug": snap.recipe.slug if snap.recipe else None,
                # Snapshot metadata
                "snapshot_date": snap.snapshot_date.isoformat() if snap.snapshot_date else None,
                "scale_factor": snap.scale_factor,
                "is_backfilled": snap.is_backfilled,
                # JSON data preserved exactly
                "recipe_data": snap.recipe_data,
                "ingredients_data": snap.ingredients_data,
            }
        )

    return _write_entity_file(output_dir, "recipe_snapshots", records)
```

2. Key implementation details:
   - Use `order_by(RecipeSnapshot.snapshot_date)` for chronological order
   - Use `joinedload(RecipeSnapshot.recipe)` to eagerly load parent
   - Export `recipe_slug` from parent Recipe entity
   - Preserve `recipe_data` and `ingredients_data` as-is (they're already JSON strings)

**Files**:
- `src/services/coordinated_export_service.py` (add function ~line 860)

**Parallel?**: Yes - can be implemented alongside T003/T004 after T001

**Validation**:
- [ ] Function returns FileEntry with correct record_count
- [ ] JSON includes all required fields
- [ ] Records ordered by snapshot_date ascending

---

### Subtask T003 – Add FinishedGoodSnapshot Model Import and DEPENDENCY_ORDER Entry

**Purpose**: Register FinishedGoodSnapshot in the export system.

**Steps**:
1. Add import at top of file:
   ```python
   from src.models.finished_good_snapshot import FinishedGoodSnapshot
   ```

2. Add entry to DEPENDENCY_ORDER:
   ```python
   "finished_good_snapshots": (20, ["finished_goods"]),
   ```
   - Import order 20 (after recipe_snapshots)
   - Dependency on "finished_goods"

**Files**:
- `src/services/coordinated_export_service.py` (modify imports and DEPENDENCY_ORDER)

**Parallel?**: Yes - can be done alongside T001/T002

**Notes**: Import order 20 chosen to group all snapshots together (19-22)

---

### Subtask T004 – Implement `_export_finished_good_snapshots()` Function

**Purpose**: Export all FinishedGoodSnapshot records to JSON.

**Steps**:
1. Add function after `_export_recipe_snapshots()`:

```python
def _export_finished_good_snapshots(output_dir: Path, session: Session) -> FileEntry:
    """Export all finished good snapshots to JSON file with FK resolution.

    Feature 081: FinishedGoodSnapshot export for assembly cost history.
    Exports in chronological order (oldest first) per FR-015.
    """
    snapshots = (
        session.query(FinishedGoodSnapshot)
        .options(joinedload(FinishedGoodSnapshot.finished_good))
        .order_by(FinishedGoodSnapshot.snapshot_date)
        .all()
    )

    records = []
    for snap in snapshots:
        records.append(
            {
                "uuid": str(snap.uuid) if snap.uuid else None,
                # FK resolved by finished_good slug
                "finished_good_slug": snap.finished_good.slug if snap.finished_good else None,
                # Snapshot metadata
                "snapshot_date": snap.snapshot_date.isoformat() if snap.snapshot_date else None,
                "is_backfilled": snap.is_backfilled,
                # JSON data preserved exactly
                "definition_data": snap.definition_data,
            }
        )

    return _write_entity_file(output_dir, "finished_good_snapshots", records)
```

**Files**:
- `src/services/coordinated_export_service.py`

**Parallel?**: Yes - can be implemented alongside T002

**Validation**:
- [ ] Function returns FileEntry with correct record_count
- [ ] JSON includes uuid, finished_good_slug, snapshot_date, definition_data, is_backfilled

---

### Subtask T005 – Update `_export_complete_impl()` to Call Export Functions

**Purpose**: Wire the new export functions into the export orchestration.

**Steps**:
1. Locate `_export_complete_impl()` function (around line 938)

2. Add calls after existing snapshot-adjacent exports (after `_export_inventory_depletions`):
   ```python
   # Feature 081: Snapshot exports for cost history preservation
   manifest.files.append(_export_recipe_snapshots(output_dir, session))
   manifest.files.append(_export_finished_good_snapshots(output_dir, session))
   ```

3. Place these calls AFTER the parent entity exports:
   - `_export_recipes()` must come before `_export_recipe_snapshots()`
   - `_export_finished_goods()` must come before `_export_finished_good_snapshots()`

**Files**:
- `src/services/coordinated_export_service.py` (modify `_export_complete_impl()` ~line 950-980)

**Parallel?**: No - depends on T002 and T004

**Validation**:
- [ ] Export with snapshots produces 2 new JSON files
- [ ] Manifest includes recipe_snapshots and finished_good_snapshots entries
- [ ] Files appear in correct import_order in manifest

---

## Definition of Done Checklist

- [ ] All 5 subtasks completed and validated
- [ ] RecipeSnapshot and FinishedGoodSnapshot models imported
- [ ] DEPENDENCY_ORDER includes both entity types with correct order/dependencies
- [ ] Export functions produce valid JSON with all required fields
- [ ] Snapshots exported in chronological order
- [ ] Export orchestration calls both new functions
- [ ] Manual test: run export, verify new JSON files created
- [ ] No lint errors (black, flake8)

---

## Risks & Mitigations

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Parent recipe/finished_good has no slug | Low | All parents have slugs (F080 ensures recipes have slugs) |
| Large number of snapshots slows export | Low | Simple query pattern, no N+1 issues with joinedload |
| JSON data malformed | Low | Preserve as-is, no transformation |

---

## Review Guidance

**Reviewers should verify:**
1. Import statements added correctly at top of file
2. DEPENDENCY_ORDER entries have correct import_order and dependencies
3. Export functions follow existing patterns exactly
4. Chronological ordering via `order_by(snapshot_date)`
5. UUID converted to string, timestamp to ISO format
6. JSON data fields preserved as-is (not parsed/re-serialized)
7. Export orchestration places calls after parent entity exports

---

## Activity Log

- 2026-01-28T18:40:28Z – system – lane=planned – Prompt created.
