---
work_package_id: "WP04"
subtasks:
  - "T016"
  - "T017"
  - "T018"
title: "Version Bump and Function Rename"
phase: "Phase 1 - Core Schema Upgrade"
lane: "for_review"
assignee: ""
agent: "system"
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-06T12:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP04 - Version Bump and Function Rename

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

- Change schema version from "3.5" to "4.0" in all export functions
- Rename `import_all_from_json_v3()` to `import_all_from_json_v4()`
- Update version validation to require "4.0"
- Clear error message for v3.x file import attempts

**Success Criteria**:
- Exported files show version "4.0"
- v3.5 files are rejected with clear error message
- v4.0 files import successfully

## Context & Constraints

**Related Documents**:
- `kitty-specs/040-import-export-v4/spec.md` - FR-009 (reject v3.x with clear error)
- `docs/design/spec_import_export.md` - Updated spec (already at v4.0)

**Key Constraints**:
- Breaking change: v3.x files will no longer import
- Keep v3 function as deprecated alias with warning for code compatibility
- Error message must be user-friendly

**File to Modify**: `src/services/import_export_service.py`

**Dependencies**: WP01, WP02, WP03 must be complete first

## Subtasks & Detailed Guidance

### Subtask T016 - Change version from "3.5" to "4.0"

**Purpose**: Update exported file version to reflect new schema.

**Steps**:
1. Find all places where version is set in exports:
   - `export_all_to_json()` - main export
   - Any other export functions
2. Change version string:
   ```python
   data = {
       "version": "4.0",  # Changed from "3.5"
       "exported_at": datetime.now().isoformat() + "Z",
       "application": "bake-tracker",
       ...
   }
   ```
3. Search for "3.5" string to find all occurrences

**Files**: `src/services/import_export_service.py`
**Parallel?**: No - simple change

**Notes**:
- Use grep to find all version references: `grep -n '"3.5"' src/services/import_export_service.py`

### Subtask T017 - Rename import_all_from_json_v3 to v4

**Purpose**: Update function name to match version.

**Steps**:
1. Rename main import function:
   ```python
   def import_all_from_json_v4(file_path: str, mode: str = "merge") -> ImportResult:
       """Import all data from v4.0 JSON file."""
       ...
   ```
2. Keep old function as deprecated alias:
   ```python
   def import_all_from_json_v3(file_path: str, mode: str = "merge") -> ImportResult:
       """DEPRECATED: Use import_all_from_json_v4() instead."""
       import warnings
       warnings.warn(
           "import_all_from_json_v3 is deprecated, use import_all_from_json_v4",
           DeprecationWarning,
           stacklevel=2
       )
       return import_all_from_json_v4(file_path, mode)
   ```
3. Update all internal references to use v4 function name

**Files**: `src/services/import_export_service.py`
**Parallel?**: No - impacts function calls

**Notes**:
- Search for all callers of `import_all_from_json_v3` in codebase
- Update tests to use new function name

### Subtask T018 - Update version validation

**Purpose**: Reject v3.x files with clear error message.

**Steps**:
1. Locate version validation in import function (near start):
   ```python
   version = data.get("version")
   if version != "4.0":
       raise ValueError(
           f"Unsupported file version: {version}. "
           f"This application only supports v4.0 format. "
           f"Please export a new backup from a current version."
       )
   ```
2. Or if using ImportResult:
   ```python
   if version != "4.0":
       result.add_error("file", file_path,
           f"Unsupported file version: {version}. "
           f"This application only supports v4.0 format.")
       return result
   ```
3. Remove any backward compatibility handling for v3.x

**Files**: `src/services/import_export_service.py`
**Parallel?**: No - validation logic

**Notes**:
- Error message must match spec: include actual version, required version, and action to take

## Test Strategy

**Required Tests**:
```bash
pytest src/tests/services/test_import_export_service.py -v -k "version"
```

**Test Cases**:
- `test_export_produces_version_4`: Export file has version "4.0"
- `test_import_rejects_v3_file`: v3.5 file produces clear error
- `test_import_accepts_v4_file`: v4.0 file imports successfully
- `test_deprecated_v3_function_warns`: Calling v3 function shows deprecation warning

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Breaking existing user workflows | Clear error message explains migration path |
| Missing version references | Use grep to find all occurrences |
| Test failures from v3 references | Update all tests to use v4 |

## Definition of Done Checklist

- [ ] T016: All exports produce version "4.0"
- [ ] T017: Function renamed, deprecated alias exists
- [ ] T018: v3.x files rejected with clear message
- [ ] All tests updated and passing
- [ ] No remaining "3.5" references in code (except deprecation message)

## Review Guidance

- Grep for "3.5" to verify complete migration
- Test error message with actual v3.5 file
- Verify deprecation warning appears when using old function
- Check UI error display for version mismatch

## Activity Log

- 2026-01-06T12:00:00Z - system - lane=planned - Prompt created.
- 2026-01-07T03:18:26Z – system – shell_pid= – lane=doing – Moved to doing
- 2026-01-07T03:27:19Z – system – shell_pid= – lane=for_review – Moved to for_review
