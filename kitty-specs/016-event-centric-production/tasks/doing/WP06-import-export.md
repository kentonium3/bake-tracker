---
work_package_id: "WP06"
subtasks:
  - "T028"
  - "T029"
  - "T030"
  - "T031"
  - "T032"
  - "T033"
  - "T034"
  - "T035"
title: "Import/Export"
phase: "Phase 4 - Import/Export"
lane: "doing"
assignee: ""
agent: "system"
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-10T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP06 - Import/Export

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

**Objective**: Extend import/export to handle new entities and modified fields.

**Success Criteria**:
- Export includes EventProductionTarget and EventAssemblyTarget
- Export includes event_name in ProductionRun and AssemblyRun
- Export includes fulfillment_status in EventRecipientPackage
- Import resolves event_name to event_id
- Import handles null event_name (standalone production)
- Round-trip preserves all data

## Context & Constraints

**Reference Documents**:
- `kitty-specs/016-event-centric-production/spec.md` - FR-029 through FR-033
- `kitty-specs/016-event-centric-production/data-model.md` - Section 5: Import/Export Schema

**Existing Code**:
- `src/services/import_export_service.py`

**Export Order** (entities with dependencies must be exported/imported in order):
1. Events (already exists)
2. EventProductionTarget (new)
3. EventAssemblyTarget (new)
4. ProductionRun (modified - add event_name)
5. AssemblyRun (modified - add event_name)
6. EventRecipientPackage (modified - add fulfillment_status)

**Dependencies**: WP01-WP05 (all models and services)

---

## Subtasks & Detailed Guidance

### Subtask T028 - Add EventProductionTarget to export

**Purpose**: Include production targets in export data.

**Steps**:
1. Open `src/services/import_export_service.py`
2. Find export function (likely `export_all()` or similar)
3. Add export logic:
   ```python
   def export_event_production_targets(self, session) -> List[dict]:
       targets = session.query(EventProductionTarget).options(
           joinedload(EventProductionTarget.event),
           joinedload(EventProductionTarget.recipe)
       ).all()
       return [
           {
               "event_name": t.event.name,
               "recipe_name": t.recipe.name,
               "target_batches": t.target_batches,
               "notes": t.notes
           }
           for t in targets
       ]
   ```
4. Add to export_all data structure

**Files**: `src/services/import_export_service.py`
**Parallel?**: No
**Notes**: Use event.name and recipe.name for human-readable export.

---

### Subtask T029 - Add EventAssemblyTarget to export

**Purpose**: Include assembly targets in export data.

**Steps**:
1. Add export logic following same pattern:
   ```python
   def export_event_assembly_targets(self, session) -> List[dict]:
       targets = session.query(EventAssemblyTarget).options(
           joinedload(EventAssemblyTarget.event),
           joinedload(EventAssemblyTarget.finished_good)
       ).all()
       return [
           {
               "event_name": t.event.name,
               "finished_good_name": t.finished_good.name,
               "target_quantity": t.target_quantity,
               "notes": t.notes
           }
           for t in targets
       ]
   ```

**Files**: `src/services/import_export_service.py`
**Parallel?**: Yes (can proceed with T028)
**Notes**: Same pattern as production targets.

---

### Subtask T030 - Add event_name field to ProductionRun export

**Purpose**: Include event attribution in production run export.

**Steps**:
1. Find ProductionRun export function
2. Add event_name to exported fields:
   ```python
   {
       # ... existing fields ...
       "event_name": run.event.name if run.event else None,
       # ... rest of fields ...
   }
   ```
3. Ensure Event relationship is eager-loaded in query

**Files**: `src/services/import_export_service.py`
**Parallel?**: No
**Notes**: Handle null event (standalone production) with None.

---

### Subtask T031 - Add event_name field to AssemblyRun export

**Purpose**: Include event attribution in assembly run export.

**Steps**:
1. Find AssemblyRun export function
2. Add event_name following same pattern as T030
3. Ensure Event relationship is eager-loaded

**Files**: `src/services/import_export_service.py`
**Parallel?**: Yes (can proceed with T030)
**Notes**: Same pattern as ProductionRun.

---

### Subtask T032 - Add fulfillment_status to EventRecipientPackage export

**Purpose**: Include package workflow status in export.

**Steps**:
1. Find EventRecipientPackage export function
2. Add fulfillment_status to exported fields:
   ```python
   {
       # ... existing fields ...
       "fulfillment_status": erp.fulfillment_status,
       # ... rest of fields ...
   }
   ```

**Files**: `src/services/import_export_service.py`
**Parallel?**: No
**Notes**: Simple field addition.

---

### Subtask T033 - Implement import for new entities

**Purpose**: Import targets and resolve name references to IDs.

**Steps**:
1. Add import function for production targets:
   ```python
   def import_event_production_targets(self, data: List[dict], session) -> int:
       count = 0
       for item in data:
           event = session.query(Event).filter_by(name=item["event_name"]).first()
           recipe = session.query(Recipe).filter_by(name=item["recipe_name"]).first()

           if not event:
               raise ValueError(f"Event not found: {item['event_name']}")
           if not recipe:
               raise ValueError(f"Recipe not found: {item['recipe_name']}")

           target = EventProductionTarget(
               event_id=event.id,
               recipe_id=recipe.id,
               target_batches=item["target_batches"],
               notes=item.get("notes")
           )
           session.add(target)
           count += 1
       return count
   ```
2. Add similar function for assembly targets
3. Ensure import order: events first, then targets

**Files**: `src/services/import_export_service.py`
**Parallel?**: No
**Notes**: Validate referenced entities exist before creating.

---

### Subtask T034 - Handle null event_name in import

**Purpose**: Support standalone production/assembly in import.

**Steps**:
1. Update ProductionRun import:
   ```python
   event_id = None
   if item.get("event_name"):
       event = session.query(Event).filter_by(name=item["event_name"]).first()
       if not event:
           raise ValueError(f"Event not found: {item['event_name']}")
       event_id = event.id

   run = ProductionRun(
       # ... other fields ...
       event_id=event_id,
   )
   ```
2. Apply same pattern to AssemblyRun import

**Files**: `src/services/import_export_service.py`
**Parallel?**: No
**Notes**: None/empty string in event_name means standalone (no event).

---

### Subtask T035 - Write import/export tests

**Purpose**: Verify round-trip preserves all data.

**Steps**:
1. Create `src/tests/integration/test_import_export_016.py`
2. Add test cases:
   ```python
   class TestImportExport016:
       def test_export_includes_production_targets(self, db_session):
           """Export contains event_production_targets section."""

       def test_export_includes_assembly_targets(self, db_session):
           """Export contains event_assembly_targets section."""

       def test_export_production_run_has_event_name(self, db_session):
           """ProductionRun export includes event_name field."""

       def test_export_production_run_null_event(self, db_session):
           """ProductionRun export handles null event_name."""

       def test_export_erp_has_fulfillment_status(self, db_session):
           """EventRecipientPackage export includes fulfillment_status."""

       def test_import_production_targets(self, db_session):
           """Import creates EventProductionTarget records."""

       def test_import_resolves_event_name(self, db_session):
           """Import resolves event_name to event_id."""

       def test_import_null_event_name(self, db_session):
           """Import handles null event_name as standalone."""

       def test_round_trip_preserves_data(self, db_session):
           """Full export/import cycle preserves all data."""
           # Export
           # Clear database
           # Import
           # Verify all records match
   ```

**Files**: `src/tests/integration/test_import_export_016.py`
**Parallel?**: No
**Notes**: Round-trip test is the most critical.

---

## Test Strategy

**Run Tests**:
```bash
pytest src/tests/integration/test_import_export_016.py -v
```

**Coverage Requirements**:
- Export includes all new fields
- Import creates correct records
- Name-to-ID resolution works
- Null event handling works
- Round-trip preserves all data

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Import order | Events must exist before targets/runs |
| Missing references | Validate and fail fast with clear error |
| Data integrity | Round-trip test ensures no data loss |

---

## Definition of Done Checklist

- [ ] EventProductionTarget in export
- [ ] EventAssemblyTarget in export
- [ ] ProductionRun has event_name
- [ ] AssemblyRun has event_name
- [ ] EventRecipientPackage has fulfillment_status
- [ ] Import resolves event_name to event_id
- [ ] Import handles null event_name
- [ ] Round-trip test passes
- [ ] All tests pass
- [ ] `tasks.md` updated with status change

---

## Review Guidance

**Reviewers should verify**:
1. Export includes all new entities/fields
2. Import validates references exist
3. Null event handling is consistent
4. Import order is correct (events before targets)
5. Round-trip test is comprehensive

---

## Activity Log

- 2025-12-10T00:00:00Z - system - lane=planned - Prompt created.
- 2025-12-11T04:11:39Z – system – shell_pid= – lane=doing – Moved to doing
