---
work_package_id: WP05
title: Service Layer - Export/Import
lane: done
history:
- timestamp: '2025-12-21T16:55:08Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
agent: claude-reviewer
assignee: claude
phase: Phase 5 - Export/Import
shell_pid: '74814'
subtasks:
- T030
- T031
- T032
- T033
---

# Work Package Prompt: WP05 - Service Layer - Export/Import

## Objectives & Success Criteria

- Export function produces v1.1 schema with production_status and loss_quantity
- Export includes losses array with ProductionLoss records
- Import function handles v1.1 data with loss records
- Import function handles v1.0 data with transform to add defaults
- Version detection works correctly for both schemas

## Context & Constraints

- **Spec**: `kitty-specs/025-production-loss-tracking/spec.md`
- **Plan**: `kitty-specs/025-production-loss-tracking/plan.md` - Phase 6
- **Data Model**: `kitty-specs/025-production-loss-tracking/data-model.md` - Import/Export Schema
- **Existing Code**: `src/services/batch_production_service.py` - export_production_history(), import_production_history()

**Key Constraints**:
- Backward compatibility with v1.0 exports
- No data loss on import
- Session management pattern for database operations

**Dependencies**:
- Requires WP01 (models) and WP02 (service layer)

## Subtasks & Detailed Guidance

### Subtask T030 - Update export for v1.1 schema
- **Purpose**: Include new loss tracking fields in exports
- **File**: `src/services/batch_production_service.py`
- **Steps**:
  1. Update `export_production_history()` version to "1.1":
     ```python
     return {
         "version": "1.1",  # Changed from "1.0"
         "exported_at": datetime.utcnow().isoformat(),
         "production_runs": exported_runs,
     }
     ```
  2. Add new fields to each exported run:
     ```python
     exported_run = {
         # ... existing fields ...
         "production_status": run.get("production_status", "complete"),
         "loss_quantity": run.get("loss_quantity", 0),
     }
     ```
- **Parallel?**: Yes, with T031
- **Notes**: Default values handle old data during export

### Subtask T031 - Add losses array to export
- **Purpose**: Export detailed loss records for each production run
- **File**: `src/services/batch_production_service.py`
- **Steps**:
  1. Update `get_production_history()` call to include_losses=True:
     ```python
     runs = get_production_history(
         # ... existing params ...
         include_losses=True,
         limit=10000,
     )
     ```
  2. Add losses array to each exported run:
     ```python
     exported_run["losses"] = [
         {
             "uuid": loss.get("uuid"),
             "loss_category": loss["loss_category"],
             "loss_quantity": loss["loss_quantity"],
             "per_unit_cost": loss["per_unit_cost"],
             "total_loss_cost": loss["total_loss_cost"],
             "notes": loss.get("notes"),
         }
         for loss in run.get("losses", [])
     ]
     ```
- **Parallel?**: Yes, with T030
- **Notes**: Handle missing losses gracefully with empty list

### Subtask T032 - Update import to handle loss records
- **Purpose**: Import ProductionLoss records from v1.1 exports
- **File**: `src/services/batch_production_service.py`
- **Steps**:
  1. In `import_production_history()`, after ProductionRun creation:
     ```python
     # Set new fields on ProductionRun
     run = ProductionRun(
         # ... existing fields ...
         production_status=run_data.get("production_status", "complete"),
         loss_quantity=run_data.get("loss_quantity", 0),
     )
     session.add(run)
     session.flush()

     # Import losses
     for loss_data in run_data.get("losses", []):
         loss = ProductionLoss(
             uuid=loss_data.get("uuid"),
             production_run_id=run.id,
             finished_unit_id=finished_unit.id,
             loss_category=loss_data["loss_category"],
             loss_quantity=loss_data["loss_quantity"],
             per_unit_cost=Decimal(loss_data["per_unit_cost"]),
             total_loss_cost=Decimal(loss_data["total_loss_cost"]),
             notes=loss_data.get("notes"),
         )
         session.add(loss)
     ```
  2. Add ProductionLoss import to imports at top
- **Parallel?**: Yes, with T033
- **Notes**: All in same session for atomicity

### Subtask T033 - Add v1.0 import transform
- **Purpose**: Handle old exports without loss data
- **File**: `src/services/batch_production_service.py`
- **Steps**:
  1. At start of import_production_history(), detect version:
     ```python
     version = data.get("version", "1.0")
     ```
  2. Transform v1.0 runs to v1.1 format:
     ```python
     if version == "1.0":
         for run_data in data.get("production_runs", []):
             # Add default loss fields
             run_data.setdefault("production_status", "complete")
             run_data.setdefault("loss_quantity", 0)
             run_data.setdefault("losses", [])
     ```
  3. Rest of import proceeds normally with transformed data
- **Parallel?**: Yes, with T032
- **Notes**: Mutates data in place; could copy if immutability needed

## Test Strategy

```bash
pytest src/tests/services/test_batch_production_service.py -v -k "export or import"
```

Manual verification:
1. Export production data, verify v1.1 format with loss fields
2. Import v1.1 data, verify ProductionLoss records created
3. Create v1.0 format data, import, verify defaults applied
4. Round-trip: export -> import -> export, compare

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| v1.0 import fails | Version detection with sensible defaults |
| Loss data not matched to runs | Use production_run_id FK correctly |
| Decimal precision loss | Use string representation in JSON |

## Definition of Done Checklist

- [ ] Export produces v1.1 version tag
- [ ] Export includes production_status and loss_quantity
- [ ] Export includes losses array for each run
- [ ] Import creates ProductionLoss records from losses array
- [ ] Import handles v1.0 data with default values
- [ ] Version detection works correctly
- [ ] Round-trip preserves all data
- [ ] `tasks.md` updated with completion status

## Review Guidance

- Verify version field correctly updated to "1.1"
- Check default values match schema defaults
- Confirm all loss fields included in export
- Test backward compatibility with v1.0 data

## Activity Log

- 2025-12-21T16:55:08Z - system - lane=planned - Prompt created.
- 2025-12-21T18:22:06Z – claude – shell_pid=67679 – lane=doing – Starting export/import implementation
- 2025-12-21T18:36:19Z – claude – shell_pid=69086 – lane=for_review – T030-T033 complete. Export/import updated for v1.1 schema with loss tracking.
- 2025-12-21T19:14:25Z – claude-reviewer – shell_pid=74814 – lane=done – Code review APPROVED: v1.1 export schema correct, v1.0 backward compatibility via transform, ProductionLoss import correct.
