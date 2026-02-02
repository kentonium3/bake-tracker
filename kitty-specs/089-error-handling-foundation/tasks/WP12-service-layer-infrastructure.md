---
work_package_id: "WP12"
subtasks:
  - "T063"
  - "T064"
  - "T065"
  - "T066"
  - "T067"
  - "T068"
  - "T069"
title: "Service Layer & Infrastructure"
phase: "Phase 2 - UI Migration"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
dependencies: ["WP03"]
history:
  - timestamp: "2026-02-02T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP12 – Service Layer & Infrastructure

## Implementation Command

```bash
spec-kitty implement WP12 --base WP03
```

**Depends on**: WP03

---

## Objectives & Success Criteria

**Objective**: Update exception handling in service layer and infrastructure code.

**Success Criteria**:
- [ ] `import_export_service.py` updated (35 occurrences - largest file)
- [ ] `import_export_dialog.py` updated (11 occurrences)
- [ ] `utils/import_export_cli.py` updated (25 occurrences)
- [ ] `utils/backup_validator.py` updated (6 occurrences)
- [ ] Remaining files updated
- [ ] CLI tools use text output (not GUI dialogs)

---

## Context & Constraints

**Special Handling for CLI Tools**:
CLI tools should NOT show GUI dialogs. Pattern:
```python
# For CLI
try:
    result = operation()
except ServiceError as e:
    # Log but don't show dialog
    logger.error(f"Operation failed: {e}")
    print(f"Error: {_get_friendly_message(e)}")
    sys.exit(1)
except Exception as e:
    logger.exception("Unexpected error")
    print("Error: An unexpected error occurred")
    sys.exit(1)
```

**For import_export_service.py**:
Many catches may be legitimate for handling file I/O - distinguish between:
- Recoverable errors (invalid file format) → wrap in ServiceError
- Expected failures (file not found) → specific exception
- Unexpected errors → log and re-raise

---

## Subtasks & Detailed Guidance

### Subtask T063 – Update import_export_service.py

**Files**: `src/services/import_export_service.py`
**Occurrences**: 35 (largest - handle carefully)
**Operations**: "Import data", "Export data", "Validate file", "Parse JSON"

**Approach**:
1. Review each catch block
2. For catches that transform to domain exception: keep pattern
3. For catches that just log/return: add structured logging
4. For bare exception catches: convert to ServiceError wrapping

### Subtask T064 – Update import_export_dialog.py

**Files**: `src/ui/import_export_dialog.py`
**Occurrences**: 11
**Operations**: "Import file", "Export file", "Validate import"

Use `handle_error()` with GUI dialogs.

### Subtask T065 – Update utils/import_export_cli.py

**Files**: `src/utils/import_export_cli.py`
**Occurrences**: 25

**Note**: CLI tool - use text output, not GUI. Pattern above.

### Subtask T066 – Update utils/backup_validator.py

**Files**: `src/utils/backup_validator.py`
**Occurrences**: 6
**Operations**: "Validate backup", "Check integrity"

### Subtask T067 – Update catalog_import_dialog.py

**Files**: `src/ui/catalog_import_dialog.py`
**Occurrences**: 1
**Operations**: "Import catalog"

### Subtask T068 – Update main.py

**Files**: `src/main.py`
**Occurrences**: 3
**Operations**: "Start application", "Initialize database"

**Note**: Startup errors should show dialog and exit gracefully.

### Subtask T069 – Update remaining services

**Files**: Various service files with remaining generic catches
- Check: `src/services/database.py`
- Check: `src/migrations/migration_orchestrator.py`
- Check: Any other services found via grep

---

## Definition of Done Checklist

- [ ] import_export_service.py fully updated (35 occurrences)
- [ ] CLI tools use text output, not GUI dialogs
- [ ] GUI dialogs use handle_error()
- [ ] Test: Import invalid file → shows friendly error message
- [ ] Test: CLI import error → prints message and exits with code 1

---

## Activity Log

- 2026-02-02T00:00:00Z – system – lane=planned – Prompt created.
