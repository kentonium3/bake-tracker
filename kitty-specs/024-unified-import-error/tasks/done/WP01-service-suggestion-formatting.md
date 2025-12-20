---
work_package_id: "WP01"
subtasks:
  - "T001"
title: "Service Layer - Suggestion Formatting"
phase: "Phase 1 - Service Layer Enhancement"
lane: "done"
assignee: ""
agent: "claude-reviewer"
shell_pid: "77654"
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-19T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 - Service Layer - Suggestion Formatting

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

**Objective**: Update `CatalogImportResult.get_detailed_report()` to include suggestion text in error output, enabling the UI to display actionable fix guidance.

**Success Criteria**:
- `get_detailed_report()` includes suggestions when present
- Suggestions are visually distinct (indented, prefixed with "Suggestion:")
- Empty suggestions produce no extra lines in output
- Existing callers are not broken

## Context & Constraints

**Reference Documents**:
- Feature Spec: `kitty-specs/024-unified-import-error/spec.md` (User Story 4)
- Implementation Plan: `kitty-specs/024-unified-import-error/plan.md` (Phase 1)
- Data Model: `kitty-specs/024-unified-import-error/data-model.md`

**Architectural Constraints**:
- Layered architecture: Services layer must not import UI components
- Method signature must remain unchanged for backward compatibility
- Output format enhancement only - no logic changes

**Current State**:
The `ImportError` dataclass already has a `suggestion` field (line 114 of `catalog_import_service.py`), but `get_detailed_report()` does not include it in the output.

## Subtasks & Detailed Guidance

### Subtask T001 - Update get_detailed_report() Error Formatting

**Purpose**: Add suggestion text to the error output so users can see actionable fix guidance.

**File**: `src/services/catalog_import_service.py`

**Steps**:

1. **Locate the method**: Find `get_detailed_report()` in the `CatalogImportResult` class (around line 200+).

2. **Find the error loop**: Look for where errors are formatted, typically:
   ```python
   for err in self.errors:
       lines.append(f"  - {err.entity_type}: {err.identifier}")
       lines.append(f"    {err.message}")
   ```

3. **Add suggestion formatting**: After the message line, add conditional suggestion:
   ```python
   for err in self.errors:
       lines.append(f"  - {err.entity_type}: {err.identifier}")
       lines.append(f"    {err.message}")
       if err.suggestion:  # Only add if suggestion is non-empty
           lines.append(f"    Suggestion: {err.suggestion}")
   ```

4. **Verify empty suggestions are handled**: The `if err.suggestion:` check ensures:
   - Empty string `""` produces no line
   - `None` (if ever passed) produces no line
   - Whitespace-only strings are treated as truthy in Python, which is acceptable

**Expected Output Format**:
```
Errors:
  - recipe: Almond Biscotti
    Invalid unit 'whole' for ingredient 'eggs_whole'.
    Suggestion: Valid units: count, cup, dozen, each, fl oz, g, gal, kg, l, lb, ml, oz, piece, pt, qt, tbsp, tsp
```

**Parallel?**: No - single subtask in this work package.

**Notes**:
- The suggestion field contains actionable guidance like valid units list
- Formatting must match the existing indentation style (2-space indent for entity, 4-space for details)

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking existing callers | Low | Medium | Method signature unchanged; only output format enhanced |
| Suggestions too long | Low | Low | Let them wrap naturally; CTkTextbox handles long lines |

## Definition of Done Checklist

- [ ] T001: `get_detailed_report()` updated with suggestion formatting
- [ ] Empty suggestions produce no extra output lines
- [ ] Output format matches expected format above
- [ ] No import changes required (services layer stays independent)
- [ ] `tasks.md` updated with status change

## Review Guidance

**Key Checkpoints**:
1. Verify the suggestion line only appears when `err.suggestion` is truthy
2. Verify indentation matches existing error format (4 spaces for details)
3. Verify no UI imports were added to the service file

**Test Approach**:
```python
# Quick validation in Python REPL or test
result = CatalogImportResult()
result.add_error("recipe", "Test Recipe", "validation", "Test message", "Test suggestion")
result.add_error("recipe", "No Suggestion", "validation", "Another message", "")
print(result.get_detailed_report())
# Should show suggestion for first error, no suggestion line for second
```

## Activity Log

- 2025-12-19T00:00:00Z - system - lane=planned - Prompt created.
- 2025-12-20T04:42:33Z – claude – shell_pid=74676 – lane=doing – Started implementation
- 2025-12-20T04:47:39Z – claude – shell_pid=75268 – lane=for_review – Ready for review - T001 complete
- 2025-12-20T05:00:24Z – claude-reviewer – shell_pid=77654 – lane=done – Approved: All success criteria met
