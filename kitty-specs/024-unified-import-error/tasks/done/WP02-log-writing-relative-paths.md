---
work_package_id: "WP02"
subtasks:
  - "T002"
  - "T003"
title: "Log Writing - Relative Path Support"
phase: "Phase 2 - Log Writing Generalization"
lane: "done"
assignee: ""
agent: "claude-reviewer"
shell_pid: "77765"
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-19T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP02 - Log Writing - Relative Path Support

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

**Objective**: Update `_write_import_log()` to return relative paths for UI display instead of absolute paths.

**Success Criteria**:
- Function returns relative path (e.g., `docs/user_testing/import_2025-12-19_143022.log`)
- Falls back to absolute path gracefully if relative conversion fails
- Works with both `ImportResult` and `CatalogImportResult` (already does via `getattr`)
- Docstring updated to document return type

## Context & Constraints

**Reference Documents**:
- Feature Spec: `kitty-specs/024-unified-import-error/spec.md` (FR-007, User Story 3)
- Implementation Plan: `kitty-specs/024-unified-import-error/plan.md` (Phase 2)

**Architectural Constraints**:
- Function is in UI layer (`src/ui/import_export_dialog.py`)
- Return value change is backward-compatible (string path)
- Must handle Windows edge case where paths may be on different drives

**Current State**:
`_write_import_log()` currently returns an absolute path string. The function already uses `getattr(result, 'mode', 'unknown')` so it works with any result type.

## Subtasks & Detailed Guidance

### Subtask T002 - Update _write_import_log() Return Value

**Purpose**: Change the return value from absolute path to relative path for user-friendly display.

**File**: `src/ui/import_export_dialog.py`

**Steps**:

1. **Locate the function**: Find `_write_import_log()` (around line 29-49).

2. **Find the return statement**: Currently returns `str(log_file)` which is absolute.

3. **Update to return relative path**:
   ```python
   def _write_import_log(file_path: str, result, summary_text: str) -> str:
       """Write import results to a log file.

       Args:
           file_path: Source file that was imported
           result: ImportResult or CatalogImportResult
           summary_text: Formatted summary text

       Returns:
           Relative path to the created log file (for display in UI)
       """
       logs_dir = _get_logs_dir()
       timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
       log_file = logs_dir / f"import_{timestamp}.log"

       with open(log_file, "w", encoding="utf-8") as f:
           f.write(f"Import Log - {datetime.now().isoformat()}\n")
           f.write("=" * 60 + "\n\n")
           f.write(f"Source file: {file_path}\n")
           f.write(f"Import mode: {getattr(result, 'mode', 'unknown')}\n\n")
           f.write("Results:\n")
           f.write("-" * 40 + "\n")
           f.write(summary_text)
           f.write("\n")

       # Return relative path for display
       try:
           return str(log_file.relative_to(Path.cwd()))
       except ValueError:
           return str(log_file)  # Fallback to absolute if not relative
   ```

**Parallel?**: No - this is the main change.

### Subtask T003 - Add Try/Except Fallback for Path Conversion

**Purpose**: Handle edge cases where relative path conversion might fail (e.g., different drives on Windows).

**File**: `src/ui/import_export_dialog.py`

**Steps**:

1. **Wrap path conversion in try/except** (included in T002 code above):
   ```python
   try:
       return str(log_file.relative_to(Path.cwd()))
   except ValueError:
       return str(log_file)  # Fallback to absolute if not relative
   ```

2. **Why this is needed**:
   - `Path.relative_to()` raises `ValueError` if paths don't share a common base
   - On Windows, `C:\logs\file.log` cannot be relative to `D:\project\`
   - Fallback ensures function never crashes

**Parallel?**: Yes - can be implemented alongside T002 (same function).

**Notes**:
- The `Path.cwd()` approach works because the app runs from the project root
- If the app is ever run from a different directory, paths will still work (just absolute)

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Path conversion fails on Windows | Low | Low | Try/except with fallback to absolute |
| cwd changes during execution | Very Low | Low | Path is computed at write time, displayed immediately |

## Definition of Done Checklist

- [ ] T002: `_write_import_log()` returns relative path
- [ ] T003: Try/except fallback handles edge cases
- [ ] Docstring updated to document return type
- [ ] Unified import still works (receives relative path now)
- [ ] `tasks.md` updated with status change

## Review Guidance

**Key Checkpoints**:
1. Verify return value is relative (e.g., `docs/user_testing/import_...` not `/Users/.../docs/...`)
2. Verify try/except handles the ValueError case
3. Verify docstring documents the return type

**Test Approach**:
```python
# After changes, in the app:
# 1. Do a unified import (File > Import Data)
# 2. Check the log path in the dialog - should be relative
# 3. Verify log file was actually written to the expected location
```

## Activity Log

- 2025-12-19T00:00:00Z - system - lane=planned - Prompt created.
- 2025-12-20T04:47:55Z – claude – shell_pid=75369 – lane=doing – Started implementation
- 2025-12-20T04:50:14Z – claude – shell_pid=75874 – lane=for_review – Ready for review - T002, T003 complete
- 2025-12-20T05:00:52Z – claude-reviewer – shell_pid=77765 – lane=done – Approved: Relative path return with fallback implemented correctly
