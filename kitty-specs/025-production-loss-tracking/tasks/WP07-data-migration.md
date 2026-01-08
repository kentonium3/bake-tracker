---
work_package_id: WP07
title: Data Migration & Documentation
lane: done
history:
- timestamp: '2025-12-21T16:55:08Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
agent: claude-reviewer
assignee: claude
phase: Phase 7 - Migration
shell_pid: '75646'
subtasks:
- T042
- T043
- T044
---

# Work Package Prompt: WP07 - Data Migration & Documentation

## Objectives & Success Criteria

- Migration transform script converts v1.0 exports to v1.1 format
- Export/transform/import cycle preserves all existing data
- Migration procedure documented with step-by-step instructions
- User can safely migrate existing database to new schema

## Context & Constraints

- **Spec**: `kitty-specs/025-production-loss-tracking/spec.md` - Edge Cases section
- **Plan**: `kitty-specs/025-production-loss-tracking/plan.md` - Phase 6
- **Data Model**: `kitty-specs/025-production-loss-tracking/data-model.md` - Migration Strategy
- **Constitution**: `.kittify/memory/constitution.md` - Principle VI: Schema Change Strategy

**Key Constraints**:
- Per Constitution Principle VI, use export/reset/import cycle (no Alembic)
- All existing data must be preserved
- Historical records set to COMPLETE status with 0 losses
- Transform must be idempotent (safe to run multiple times)

**Dependencies**:
- Requires WP05 complete (export/import must handle v1.1 format)

## Subtasks & Detailed Guidance

### Subtask T042 - Create migration transform script
- **Purpose**: Convert v1.0 exported data to v1.1 format
- **File**: `scripts/migrate_v1_0_to_v1_1.py` (new file)
- **Steps**:
  1. Create script with CLI interface:
     ```python
     #!/usr/bin/env python3
     """
     Migrate production history export from v1.0 to v1.1 format.

     Adds default loss tracking fields to existing production runs:
     - production_status: "complete"
     - loss_quantity: 0
     - losses: []

     Usage:
         python scripts/migrate_v1_0_to_v1_1.py input.json output.json
     """
     import json
     import sys
     from pathlib import Path

     def transform_v1_0_to_v1_1(data: dict) -> dict:
         """Transform v1.0 export to v1.1 format."""
         # Check version
         version = data.get("version", "1.0")
         if version != "1.0":
             print(f"Warning: Expected v1.0, got v{version}")

         # Transform each production run
         for run in data.get("production_runs", []):
             run.setdefault("production_status", "complete")
             run.setdefault("loss_quantity", 0)
             run.setdefault("losses", [])

         # Update version
         data["version"] = "1.1"
         return data

     def main():
         if len(sys.argv) != 3:
             print(__doc__)
             sys.exit(1)

         input_path = Path(sys.argv[1])
         output_path = Path(sys.argv[2])

         with open(input_path) as f:
             data = json.load(f)

         transformed = transform_v1_0_to_v1_1(data)

         with open(output_path, "w") as f:
             json.dump(transformed, f, indent=2)

         print(f"Transformed {len(data.get('production_runs', []))} production runs")
         print(f"Output written to {output_path}")

     if __name__ == "__main__":
         main()
     ```
  2. Make script executable: `chmod +x scripts/migrate_v1_0_to_v1_1.py`
- **Parallel?**: Yes, with T044
- **Notes**: Script is idempotent - safe to run on already-transformed data

### Subtask T043 - Test export/transform/import cycle
- **Purpose**: Verify no data loss during migration
- **File**: Manual testing with sample data
- **Steps**:
  1. Create test data:
     - Record some production runs in current database
     - Note expected values
  2. Export current data:
     ```bash
     # In Python or via app
     from src.services.batch_production_service import export_production_history
     import json
     data = export_production_history()
     with open("test_export_v1.0.json", "w") as f:
         json.dump(data, f, indent=2)
     ```
  3. Transform to v1.1:
     ```bash
     python scripts/migrate_v1_0_to_v1_1.py test_export_v1.0.json test_export_v1.1.json
     ```
  4. Verify transformed file:
     - Check version is "1.1"
     - Check each run has production_status, loss_quantity, losses
  5. Reset database (backup first!):
     - Delete database file
     - Run app to create fresh schema
  6. Import transformed data:
     ```python
     from src.services.batch_production_service import import_production_history
     import json
     with open("test_export_v1.1.json") as f:
         data = json.load(f)
     result = import_production_history(data)
     print(f"Imported: {result['imported']}, Skipped: {result['skipped']}, Errors: {result['errors']}")
     ```
  7. Verify data integrity:
     - All production runs present
     - All consumptions present
     - production_status = "complete" for all
     - loss_quantity = 0 for all
- **Parallel?**: No (sequential verification steps)
- **Notes**: Document any issues encountered

### Subtask T044 - Document migration procedure
- **Purpose**: Enable users to safely migrate their data
- **File**: `docs/migrations/v0.6_to_v0.7_production_loss.md` (new file)
- **Steps**:
  1. Create migration guide:
     ```markdown
     # Migration Guide: v0.6 to v0.7 (Production Loss Tracking)

     This guide explains how to migrate your database to support the new
     production loss tracking feature (Feature 025).

     ## Overview

     The migration adds loss tracking fields to production runs. All existing
     production runs will be marked as "complete" with zero losses.

     ## Prerequisites

     - Backup your current database file
     - Python environment with project dependencies installed

     ## Step 1: Export Current Data

     1. Open the application
     2. Go to Settings > Data Management > Export All
     3. Save as `backup_before_loss_tracking.json`

     Alternative via Python:
     ```python
     from src.services.batch_production_service import export_production_history
     import json
     data = export_production_history()
     with open("backup_before_loss_tracking.json", "w") as f:
         json.dump(data, f, indent=2)
     ```

     ## Step 2: Transform Data

     Run the migration transform script:
     ```bash
     python scripts/migrate_v1_0_to_v1_1.py backup_before_loss_tracking.json migrated_data.json
     ```

     ## Step 3: Reset Database

     1. Close the application
     2. Delete the database file (`data/bake_tracker.db`)
     3. Open the application to create fresh schema with new fields

     ## Step 4: Import Transformed Data

     1. Go to Settings > Data Management > Import
     2. Select `migrated_data.json`
     3. Verify import report shows no errors

     Alternative via Python:
     ```python
     from src.services.batch_production_service import import_production_history
     import json
     with open("migrated_data.json") as f:
         data = json.load(f)
     result = import_production_history(data)
     print(result)
     ```

     ## Verification

     After import, verify:
     - [ ] All recipes present
     - [ ] All production runs present
     - [ ] Production history shows "Complete" status for all existing runs
     - [ ] Application functions normally

     ## Rollback

     If issues occur:
     1. Close application
     2. Delete database file
     3. Open application (fresh schema)
     4. Import original backup (`backup_before_loss_tracking.json`)

     Note: Original backup uses v1.0 format which the new import function
     handles with automatic transform.
     ```
- **Parallel?**: Yes, with T042
- **Notes**: Keep instructions simple for non-technical user

## Test Strategy

1. Complete manual test cycle (T043)
2. Verify documentation steps work as written
3. Test rollback procedure

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Data loss | Mandatory backup before migration |
| Transform errors | Idempotent script, version checking |
| Import failures | Error reporting, rollback procedure |

## Definition of Done Checklist

- [ ] Migration transform script created
- [ ] Script is idempotent and handles edge cases
- [ ] Export/transform/import cycle tested successfully
- [ ] All data preserved after migration
- [ ] Migration documentation complete
- [ ] Rollback procedure documented
- [ ] `tasks.md` updated with completion status

## Review Guidance

- Verify script handles missing fields gracefully
- Test with actual v1.0 export if available
- Confirm documentation is clear for non-technical user
- Check rollback procedure works

## Activity Log

- 2025-12-21T16:55:08Z - system - lane=planned - Prompt created.
- 2025-12-21T18:42:38Z – claude – shell_pid=69086 – lane=doing – Starting data migration implementation
- 2025-12-21T18:45:23Z – claude – shell_pid=69086 – lane=for_review – T042-T044 complete. Migration script and documentation ready.
- 2025-12-21T19:20:38Z – claude-reviewer – shell_pid=75646 – lane=done – Code review APPROVED: Migration script idempotent, documentation comprehensive with rollback procedure.
