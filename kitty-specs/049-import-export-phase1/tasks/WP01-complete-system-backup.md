---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
  - "T003"
  - "T004"
  - "T005"
  - "T006"
  - "T007"
  - "T008"
title: "Complete System Backup (16 Entities)"
phase: "Phase 1 - Foundation"
lane: "done"
assignee: "claude"
agent: "claude"
shell_pid: "13882"
review_status: "approved"
reviewed_by: "claude"
history:
  - timestamp: "2026-01-12T16:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 - Complete System Backup (16 Entities)

## IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

**Objective**: Extend `coordinated_export_service.py` to export all 16 entity types (currently exports 12) with accurate manifest.

**Success Criteria**:
- SC-001: Full backup export includes all 16 entity types with accurate manifest counts
- SC-002: Complete system state can be restored from backup (round-trip test passes)
- SC-012: All exports use slug references (zero database IDs in export files)
- FR-001: System MUST export all 16 entity types
- FR-002: System MUST include manifest.json with entity counts
- FR-003: System MUST export empty entities as empty arrays (not omit them)
- FR-004: System MUST use slug-based references in all exports

## Context & Constraints

**Reference Documents**:
- Constitution: `.kittify/memory/constitution.md` (Principles II, V)
- Spec: `kitty-specs/049-import-export-phase1/spec.md` (User Story 1)
- Plan: `kitty-specs/049-import-export-phase1/plan.md`
- Existing spec: `docs/design/spec_import_export.md` (Appendix D)

**Current State**: The coordinated export service exports 12 entities:
1. suppliers
2. ingredients
3. products
4. recipes (with recipe_ingredients, recipe_components)
5. purchases
6. inventory_items
7. material_categories
8. material_subcategories
9. materials
10. material_products
11. material_units
12. material_purchases

**Entities to Add** (4 new):
13. finished_goods
14. events
15. production_runs
16. inventory_depletions

**Architectural Constraints**:
- Follow existing exporter pattern exactly
- Use slug-based FK references (not database IDs)
- Each entity exports to numbered file (e.g., `07_materials.json`)
- Manifest includes sha256 hash and record count per entity

---

## Subtasks & Detailed Guidance

### Subtask T001 - Add finished_goods exporter

**Purpose**: Export FinishedGood records with composition references.

**Steps**:
1. Open `src/services/coordinated_export_service.py`
2. Study existing exporters as pattern
3. Create `export_finished_goods()` function:
   - Query all FinishedGood records
   - Include: id, uuid, slug, display_name, category, description
   - Note: Compositions are separate entity
4. Register in `DEPENDENCY_ORDER` constant

**Files**: `src/services/coordinated_export_service.py`

**Pattern to Follow**:
```python
def export_finished_goods(session: Session, output_dir: Path) -> FileEntry:
    """Export finished goods to JSON file."""
    goods = session.query(FinishedGood).all()

    records = []
    for g in goods:
        record = {
            "id": g.id,
            "uuid": str(g.uuid) if g.uuid else None,
            "slug": g.slug,
            "display_name": g.display_name,
            # ... include all relevant fields
        }
        records.append(record)

    # Write to file, calculate hash
    return write_entity_file("finished_goods", records, output_dir, import_order=13)
```

### Subtask T002 - Add events exporter

**Purpose**: Export Event records with output_mode and targets.

**Steps**:
1. Create `export_events()` function
2. Include: id, uuid, slug, name, event_date, year, output_mode, notes
3. Include nested: event_production_targets, event_assembly_targets

**Files**: `src/services/coordinated_export_service.py`
**Parallel?**: Yes, can proceed after T001 establishes pattern

### Subtask T003 - Add production_runs exporter

**Purpose**: Export ProductionRun records with recipe and event references.

**Steps**:
1. Create `export_production_runs()` function
2. Include: id, uuid, recipe_id, recipe_slug, event_id, event_slug (nullable), batches_produced, units_produced, produced_at, actual_cost, notes
3. Resolve recipe and event FKs

**Files**: `src/services/coordinated_export_service.py`
**Parallel?**: Yes

### Subtask T004 - Add inventory_depletions exporter

**Purpose**: Export inventory depletion records for audit trail.

**Steps**:
1. Create `export_inventory_depletions()` function
2. Include all fields needed for audit reconstruction
3. Resolve inventory_item and related FKs

**Files**: `src/services/coordinated_export_service.py`
**Parallel?**: Yes

### Subtask T005 - Update DEPENDENCY_ORDER constant

**Purpose**: Register all 4 new entities with correct import order and dependencies.

**Steps**:
1. Update `DEPENDENCY_ORDER` dict in coordinated_export_service.py to add:
```python
# Add to existing DEPENDENCY_ORDER:
"finished_goods": (13, []),
"events": (14, []),
"production_runs": (15, ["recipes", "events"]),
"inventory_depletions": (16, ["inventory_items"]),
```

**Files**: `src/services/coordinated_export_service.py`

### Subtask T006 - Update manifest generation

**Purpose**: Ensure manifest includes all 16 entities with accurate counts.

**Steps**:
1. Update `export_complete()` to call all 4 new exporters
2. Verify manifest.json includes all 16 FileEntry records
3. Verify import_order is sequential 1-16

**Files**: `src/services/coordinated_export_service.py`

### Subtask T007 - Add unit tests for new exporters

**Purpose**: Test each new exporter function.

**Steps**:
1. Open `src/tests/services/test_coordinated_export_service.py`
2. Add test for each new entity:
   - `test_export_finished_goods()`
   - `test_export_events()`
   - `test_export_production_runs()`
   - `test_export_inventory_depletions()`
3. Test FK resolution is correct (slugs not IDs)
4. Test manifest counts match exported records

**Files**: `src/tests/services/test_coordinated_export_service.py`

### Subtask T008 - Verify empty arrays for zero-record entities

**Purpose**: Ensure entities with no data export as `[]` not omitted.

**Steps**:
1. Add test case with empty database
2. Export full backup
3. Verify all 16 entity files exist
4. Verify each contains `"records": []`
5. Verify manifest shows `record_count: 0` for each

**Files**: `src/tests/services/test_coordinated_export_service.py`

---

## Test Strategy

**Unit Tests** (required per constitution):
- Test each exporter with sample data
- Test FK resolution produces slugs not IDs
- Test empty entity handling
- Test manifest accuracy

**Run Tests**:
```bash
./run-tests.sh src/tests/services/test_coordinated_export_service.py -v
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| FK resolution missing relationship | Check model definitions for all FKs |
| Import order incorrect | Verify dependencies match FK relationships |
| Hash calculation inconsistent | Use same algorithm as existing exporters |

---

## Definition of Done Checklist

- [ ] All 4 new entity exporters implemented (finished_goods, events, production_runs, inventory_depletions)
- [ ] DEPENDENCY_ORDER updated with all 16 entities
- [ ] Manifest includes all 16 entities
- [ ] Empty entities export as empty arrays
- [ ] All FK references use slugs (no IDs)
- [ ] Unit tests pass for all new exporters
- [ ] Export folder contains 16 numbered JSON files + manifest.json

## Review Guidance

**Reviewers should verify**:
1. All 16 entity types present in export
2. Manifest counts match file contents
3. FK fields use slugs, not numeric IDs
4. Empty entities have `[]` not omitted
5. Import order matches dependency requirements

---

## Activity Log

- 2026-01-12T16:00:00Z - system - lane=planned - Prompt created via /spec-kitty.tasks
- 2026-01-12T17:00:22Z – claude – lane=doing – Started implementation
- 2026-01-12T17:15:00Z – claude – lane=for_review – All 8 subtasks complete. 4 new exporters implemented, 40 tests passing.
- 2026-01-12T21:45:00Z – claude – shell_pid=13882 – lane=done – Approved: All 40 tests pass. DEPENDENCY_ORDER has all 16 entities. Empty arrays verified. Slug-based FK references confirmed.
