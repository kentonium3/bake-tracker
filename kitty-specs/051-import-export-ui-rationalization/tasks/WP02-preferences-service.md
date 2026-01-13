---
work_package_id: "WP02"
subtasks:
  - "T008"
  - "T009"
  - "T010"
  - "T011"
  - "T012"
  - "T013"
  - "T014"
title: "Preferences Service"
phase: "Phase 0 - Foundational"
lane: "done"
assignee: ""
agent: "codex"
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-13T12:55:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP02 - Preferences Service

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

Create a service for managing directory preferences stored in the app_config table.

**Success Criteria**:
- `preferences_service.py` exists with get/set/reset functions for all directories
- Preferences persist to `app_config` table (survive app restart)
- Missing/invalid directories fall back gracefully to defaults
- Unit tests cover CRUD operations and edge cases

## Context & Constraints

**Related Documents**:
- Spec: `kitty-specs/051-import-export-ui-rationalization/spec.md` (US6 - Configurable Directories)
- Plan: `kitty-specs/051-import-export-ui-rationalization/plan.md`
- Data Model: `kitty-specs/051-import-export-ui-rationalization/data-model.md`

**Architecture Constraints**:
- Use existing `app_config` table (key-value pattern)
- Service layer only (no UI imports)
- Handle filesystem operations gracefully (permission errors, missing dirs)

**Existing Patterns**:
- `src/models/app_config.py` - AppConfig model
- `src/services/database.py` - session_scope pattern

## Subtasks & Detailed Guidance

### Subtask T008 - Create preferences_service.py with base structure
- **Purpose**: Establish service file with helper functions
- **Steps**:
  1. Create `src/services/preferences_service.py`
  2. Add imports: `logging`, `pathlib.Path`, `os`
  3. Import `session_scope` from `src/services/database`
  4. Import `AppConfig` model if exists, or use raw queries
  5. Define constants for preference keys and defaults:
     ```python
     PREF_IMPORT_DIR = "import_directory"
     PREF_EXPORT_DIR = "export_directory"
     PREF_LOGS_DIR = "logs_directory"
     DEFAULT_IMPORT_DIR = Path.home() / "Documents"
     DEFAULT_EXPORT_DIR = Path.home() / "Documents"
     DEFAULT_LOGS_DIR = Path(__file__).parent.parent.parent / "docs" / "user_testing"
     ```
  6. Add private helpers `_get_preference()` and `_set_preference()`
- **Files**: `src/services/preferences_service.py`
- **Parallel?**: Yes
- **Notes**: Check if AppConfig model exists; if not, use direct SQL

### Subtask T009 - Implement get/set_import_directory()
- **Purpose**: CRUD for import directory preference
- **Steps**:
  1. `get_import_directory()` - retrieve from app_config, validate exists, return path or default
  2. `set_import_directory(path: str)` - validate path is directory, store in app_config
  3. Handle case where stored path no longer exists (warn and return default)
- **Files**: `src/services/preferences_service.py`
- **Parallel?**: No (establishes pattern for T010-T011)
- **Notes**: Return `Path` objects for consistency

### Subtask T010 - Implement get/set_export_directory()
- **Purpose**: CRUD for export directory preference
- **Steps**:
  1. Follow same pattern as T009
  2. `get_export_directory()` - retrieve, validate, return path or default
  3. `set_export_directory(path: str)` - validate, store
- **Files**: `src/services/preferences_service.py`
- **Parallel?**: Yes (once T009 pattern exists)
- **Notes**: Can copy/adapt T009 implementation

### Subtask T011 - Implement get/set_logs_directory()
- **Purpose**: CRUD for logs directory preference
- **Steps**:
  1. Follow same pattern as T009
  2. `get_logs_directory()` - retrieve, validate, return path or default
  3. `set_logs_directory(path: str)` - validate, store
  4. Note: logs directory should also validate write permission
- **Files**: `src/services/preferences_service.py`
- **Parallel?**: Yes (once T009 pattern exists)
- **Notes**: Consider validating write permission for logs dir

### Subtask T012 - Implement reset_all_preferences()
- **Purpose**: Restore all directory preferences to system defaults
- **Steps**:
  1. Delete all preference keys from app_config (or set to None/empty)
  2. Next get_*() call will return default
  3. Alternative: explicitly set to default values
  4. Return success indicator
- **Files**: `src/services/preferences_service.py`
- **Parallel?**: No (depends on T009-T011)
- **Notes**: Used by Preferences dialog "Restore Defaults" button

### Subtask T013 - Implement directory existence validation with fallback
- **Purpose**: Gracefully handle missing/invalid directories
- **Steps**:
  1. Create `_validate_directory(path: str) -> bool` helper
  2. Check path exists and is a directory
  3. For logs directory, also check write permission
  4. Log warning when falling back to default
  5. Ensure all get_*() functions use this validation
- **Files**: `src/services/preferences_service.py`
- **Parallel?**: No (integrate into get functions)
- **Notes**: Don't raise exceptions; log and return default

### Subtask T014 - Create test_preferences_service.py
- **Purpose**: Unit test coverage for preferences service
- **Steps**:
  1. Create `src/tests/test_preferences_service.py`
  2. Test set then get returns same path
  3. Test get with no preference returns default
  4. Test invalid path falls back to default with warning
  5. Test reset clears all preferences
  6. Test permission handling (mock filesystem if needed)
- **Files**: `src/tests/test_preferences_service.py`
- **Parallel?**: Yes (once core functions exist)
- **Notes**: May need to mock filesystem operations; use tmp_path fixture

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| app_config table doesn't exist | Verify with existing code; may need to create or use existing config pattern |
| Cross-platform path issues | Use `pathlib.Path` throughout; avoid hardcoded separators |
| Permission errors | Catch OSError, log warning, return default |

## Definition of Done Checklist

- [ ] `src/services/preferences_service.py` created
- [ ] get/set functions for import, export, and logs directories
- [ ] `reset_all_preferences()` implemented
- [ ] Directory validation with graceful fallback
- [ ] `src/tests/test_preferences_service.py` exists with tests
- [ ] All tests pass: `./run-tests.sh src/tests/test_preferences_service.py -v`
- [ ] No UI imports in service

## Review Guidance

**Key checkpoints**:
1. Verify app_config integration works correctly
2. Verify missing directory falls back to default (check logs)
3. Verify preferences persist (set, restart conceptually, get returns value)
4. Verify reset clears all preferences
5. Run `./run-tests.sh src/tests/test_preferences_service.py -v`

## Activity Log

- 2026-01-13T12:55:00Z - system - lane=planned - Prompt created.
- 2026-01-13T18:26:50Z – codex – lane=doing – Started implementation
- 2026-01-13T18:30:42Z – codex – lane=for_review – Ready for review
- 2026-01-13T20:57:02Z – codex – lane=done – Code review APPROVED by claude - All tests pass (27 preferences tests), JSON persistence works correctly, survives DB resets
