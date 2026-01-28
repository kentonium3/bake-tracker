---
work_package_id: WP03
title: Recipe & FinishedGood Snapshot Import
lane: "for_review"
dependencies: [WP01]
base_branch: 081-snapshot-export-coverage-WP01
base_commit: 58d09833a9ae87691cf419f8adfaeca5c2ed1ed1
created_at: '2026-01-28T20:25:51.473325+00:00'
subtasks:
- T011
- T012
- T013
- T014
phase: Phase 2 - Import Functions
assignee: ''
agent: ''
shell_pid: "76733"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-01-28T18:40:28Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP03 – Recipe & FinishedGood Snapshot Import

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
spec-kitty implement WP03 --base WP01
```

Depends on WP01 - export functions must exist for testing imports.

---

## Objectives & Success Criteria

Add import handlers for RecipeSnapshot and FinishedGoodSnapshot entities to `coordinated_export_service.py`.

**Success Criteria:**
- [ ] RecipeSnapshot records import with correct recipe_id FK resolution
- [ ] FinishedGoodSnapshot records import with correct finished_good_id FK resolution
- [ ] Missing parent entities result in warning log, not failure (FR-013)
- [ ] Original UUIDs preserved exactly (FR-010)
- [ ] Original timestamps preserved exactly (FR-011)
- [ ] JSON data preserved exactly (FR-012)

---

## Context & Constraints

**Reference Documents:**
- Feature spec: `kitty-specs/081-snapshot-export-coverage/spec.md` (FR-005, FR-006, FR-009, FR-010, FR-011, FR-012, FR-013)
- Data model: `kitty-specs/081-snapshot-export-coverage/data-model.md`

**Key Files to Modify:**
- `src/services/coordinated_export_service.py` - Add import handlers

**Pattern Reference:**
Follow the existing `finished_units` import handler pattern at lines 1448-1492 of coordinated_export_service.py.

**Critical Constraints:**
- Snapshots must import AFTER parent entities (recipes, finished_goods)
- Snapshots must be DELETED BEFORE parent entities in delete cascade
- Missing parent = skip snapshot + warning (don't fail entire import)

---

## Subtasks & Detailed Guidance

### Subtask T011 – Add Snapshot Model Imports and Update Delete Order

**Purpose**: Prepare the import infrastructure for snapshot entities.

**Steps**:

1. **Add model imports** in the import section of `_import_entity_records()` (around line 1242):
   ```python
   from src.models.recipe_snapshot import RecipeSnapshot
   from src.models.finished_good_snapshot import FinishedGoodSnapshot
   ```

2. **Update delete order** in `_import_complete_impl()` (around line 1153-1172):

   Add snapshot deletions BEFORE their parent entities:
   ```python
   # Delete snapshots before their parents (FK constraints)
   session.query(RecipeSnapshot).delete()
   session.query(FinishedGoodSnapshot).delete()
   # Then existing parent deletions...
   session.query(ProductionRun).delete()  # etc.
   ```

   **Delete order must be**:
   1. RecipeSnapshot (before Recipe)
   2. FinishedGoodSnapshot (before FinishedGood)
   3. ... existing deletions ...

**Files**:
- `src/services/coordinated_export_service.py` (lines ~1135-1175)

**Parallel?**: No - must complete before T012/T013

**Notes**:
- Import order is controlled by DEPENDENCY_ORDER (already set in WP01/WP02)
- Delete order is separate and must be explicit in code

---

### Subtask T012 – Implement `recipe_snapshots` Import Handler

**Purpose**: Import RecipeSnapshot records with FK resolution.

**Steps**:

1. Add handler in `_import_entity_records()` function (around line 1850, after existing handlers):

```python
elif entity_type == "recipe_snapshots":
    # Feature 081: RecipeSnapshot import with slug-based FK resolution
    from src.models.recipe_snapshot import RecipeSnapshot
    from uuid import UUID

    recipe_slug = record.get("recipe_slug")
    if not recipe_slug:
        logger.warning(f"RecipeSnapshot skipped: no recipe_slug provided")
        continue

    # Resolve recipe FK by slug
    recipe = session.query(Recipe).filter(Recipe.slug == recipe_slug).first()
    if not recipe:
        logger.warning(
            f"RecipeSnapshot skipped: recipe '{recipe_slug}' not found"
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
            # Handle ISO format with or without timezone
            if snapshot_date_str.endswith('Z'):
                snapshot_date_str = snapshot_date_str[:-1] + '+00:00'
            snapshot_date = datetime.fromisoformat(snapshot_date_str)
        except ValueError:
            logger.warning(f"RecipeSnapshot: invalid snapshot_date '{snapshot_date_str}'")

    obj = RecipeSnapshot(
        uuid=uuid_val,
        recipe_id=recipe.id,
        snapshot_date=snapshot_date,
        scale_factor=record.get("scale_factor", 1.0),
        is_backfilled=record.get("is_backfilled", False),
        # JSON data preserved exactly
        recipe_data=record.get("recipe_data", "{}"),
        ingredients_data=record.get("ingredients_data", "[]"),
    )
    session.add(obj)
    imported_count += 1
```

**Files**:
- `src/services/coordinated_export_service.py` (add handler ~line 1850)

**Parallel?**: Yes - can be implemented alongside T013 after T011

**Validation**:
- [ ] FK resolved via recipe_slug
- [ ] Missing recipe results in warning + skip (not error)
- [ ] UUID preserved exactly
- [ ] snapshot_date preserved exactly
- [ ] recipe_data and ingredients_data preserved as-is

---

### Subtask T013 – Implement `finished_good_snapshots` Import Handler

**Purpose**: Import FinishedGoodSnapshot records with FK resolution.

**Steps**:

1. Add handler after `recipe_snapshots` handler:

```python
elif entity_type == "finished_good_snapshots":
    # Feature 081: FinishedGoodSnapshot import with slug-based FK resolution
    from src.models.finished_good_snapshot import FinishedGoodSnapshot
    from src.models.finished_good import FinishedGood
    from uuid import UUID

    fg_slug = record.get("finished_good_slug")
    if not fg_slug:
        logger.warning(f"FinishedGoodSnapshot skipped: no finished_good_slug provided")
        continue

    # Resolve finished_good FK by slug
    finished_good = (
        session.query(FinishedGood)
        .filter(FinishedGood.slug == fg_slug)
        .first()
    )
    if not finished_good:
        logger.warning(
            f"FinishedGoodSnapshot skipped: finished_good '{fg_slug}' not found"
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
            logger.warning(f"FinishedGoodSnapshot: invalid snapshot_date '{snapshot_date_str}'")

    obj = FinishedGoodSnapshot(
        uuid=uuid_val,
        finished_good_id=finished_good.id,
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

**Parallel?**: Yes - can be implemented alongside T012

**Validation**:
- [ ] FK resolved via finished_good_slug
- [ ] Missing finished_good results in warning + skip
- [ ] UUID, timestamp, definition_data preserved exactly

---

### Subtask T014 – Add Warning Logging for Missing Parent Entities

**Purpose**: Ensure missing parent handling is consistent and logged appropriately (FR-013).

**Steps**:

1. **Verify logging level** - warnings should use `logger.warning()`, not `logger.error()`

2. **Test warning output** - run import with a snapshot referencing non-existent parent:
   - Should see: `WARNING - RecipeSnapshot skipped: recipe 'nonexistent-slug' not found`
   - Should NOT see: `ERROR` or exception

3. **Verify import continues** - other records should still import successfully

4. **Add docstring note** to import handlers documenting the skip behavior:
   ```python
   # Note: Missing parent entities are skipped with warning (FR-013)
   # Import continues with remaining records
   ```

**Files**:
- `src/services/coordinated_export_service.py` (verify handlers from T012/T013)

**Parallel?**: No - must verify after T012/T013

**Validation**:
- [ ] Missing parent produces WARNING level log
- [ ] Import continues after skip
- [ ] Imported count reflects actual successful imports

---

## Definition of Done Checklist

- [ ] RecipeSnapshot and FinishedGoodSnapshot model imports added
- [ ] Delete order updated (snapshots before parents)
- [ ] recipe_snapshots import handler implemented
- [ ] finished_good_snapshots import handler implemented
- [ ] Missing parent handling: skip + warning (not error)
- [ ] UUID preserved exactly from export
- [ ] Timestamp preserved exactly from export
- [ ] JSON data preserved exactly from export
- [ ] No lint errors

---

## Risks & Mitigations

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Delete order wrong | Medium | Explicitly verify in code review |
| UUID parsing fails | Low | Use uuid.UUID() with error handling |
| Timestamp parsing fails | Low | Handle ISO format variations |

---

## Review Guidance

**Reviewers should verify:**
1. Delete order: snapshots deleted BEFORE their parent entities
2. FK resolution uses slug-based lookup
3. Missing parent: skip + warning (NOT error/exception)
4. UUID preserved via uuid.UUID() conversion
5. Timestamp parsed correctly from ISO format
6. JSON data assigned directly (no transformation)
7. Import handlers follow consistent pattern

---

## Activity Log

- 2026-01-28T18:40:28Z – system – lane=planned – Prompt created.
- 2026-01-28T20:29:04Z – unknown – shell_pid=76733 – lane=for_review – RecipeSnapshot and FinishedGoodSnapshot import handlers with delete order fixes
