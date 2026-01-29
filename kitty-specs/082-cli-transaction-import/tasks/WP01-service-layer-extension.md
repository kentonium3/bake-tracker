---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
  - "T003"
title: "Service Layer Extension"
phase: "Phase 1 - Foundation"
lane: "doing"
assignee: ""
agent: "claude"
shell_pid: "30076"
review_status: ""
reviewed_by: ""
dependencies: []
history:
  - timestamp: "2026-01-29T04:45:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 – Service Layer Extension

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Implementation Command

```bash
spec-kitty implement WP01
```

No dependencies - this is the foundation WP.

---

## Objectives & Success Criteria

**Goal**: Add `strict_mode` parameter to transaction import services and create JSON output helper.

**Success Criteria**:
- [ ] `import_purchases()` accepts `strict_mode: bool = False` parameter
- [ ] `import_adjustments()` accepts `strict_mode: bool = False` parameter
- [ ] In strict mode, functions return early on first FK resolution failure
- [ ] `result_to_json()` helper converts ImportResult to structured dict
- [ ] Existing behavior unchanged when strict_mode=False (backward compatible)
- [ ] All existing tests pass

## Context & Constraints

**Files to Modify**:
- `src/services/transaction_import_service.py` - Add strict_mode parameter
- `src/utils/import_export_cli.py` - Add result_to_json() helper (near other helpers)

**Research Reference**: See `kitty-specs/082-cli-transaction-import/research/fk-resolution-analysis.md`

**Key Constraint**: Must maintain backward compatibility - default behavior unchanged.

**Pattern Reference**: The existing `dry_run` parameter shows how to add optional flags to these functions.

---

## Subtasks & Detailed Guidance

### Subtask T001 – Add strict_mode to import_purchases()

**Purpose**: Enable strict FK resolution mode that fails fast on first unresolved product.

**Steps**:

1. Open `src/services/transaction_import_service.py`

2. Modify function signature at line ~363:
   ```python
   def import_purchases(
       file_path: str,
       dry_run: bool = False,
       strict_mode: bool = False,  # ADD THIS
       session: Optional[Session] = None,
   ) -> ImportResult:
   ```

3. Pass `strict_mode` to internal implementation:
   ```python
   if session is not None:
       return _import_purchases_impl(file_path, dry_run, strict_mode, session)

   with session_scope() as sess:
       result = _import_purchases_impl(file_path, dry_run, strict_mode, sess)
   ```

4. Modify `_import_purchases_impl()` signature:
   ```python
   def _import_purchases_impl(
       file_path: str,
       dry_run: bool,
       strict_mode: bool,  # ADD THIS
       session: Session,
   ) -> ImportResult:
   ```

5. Add early exit logic after product resolution failure (around line ~529-537):
   ```python
   product, error = _resolve_product_by_slug(product_slug, session)
   if not product:
       product = _try_create_provisional_from_slug(product_slug, session, result)
   if not product:
       result.add_error(
           "purchase",
           product_slug,
           f"Product '{product_slug}' not found: {error}",
           suggestion="..."
       )
       # ADD THIS: Early exit in strict mode
       if strict_mode:
           return result
       continue  # Existing behavior for auto mode
   ```

**Files**: `src/services/transaction_import_service.py`

**Parallel?**: Yes - can be done alongside T002

**Validation**:
- Existing tests still pass
- `import_purchases("file.json")` works unchanged (backward compatible)
- `import_purchases("file.json", strict_mode=True)` stops on first failure

---

### Subtask T002 – Add strict_mode to import_adjustments()

**Purpose**: Enable strict FK resolution mode for adjustment imports.

**Steps**:

1. Modify function signature at line ~614:
   ```python
   def import_adjustments(
       file_path: str,
       dry_run: bool = False,
       strict_mode: bool = False,  # ADD THIS
       session: Optional[Session] = None,
   ) -> ImportResult:
   ```

2. Pass to internal implementation (same pattern as T001)

3. Modify `_import_adjustments_impl()` signature

4. Add early exit logic after product resolution failure (around line ~831-836):
   ```python
   product, error = _resolve_product_by_slug(product_slug, session)
   if not product:
       result.add_error(...)
       # ADD THIS: Early exit in strict mode
       if strict_mode:
           return result
       continue
   ```

**Files**: `src/services/transaction_import_service.py`

**Parallel?**: Yes - can be done alongside T001

**Validation**:
- Existing tests still pass
- Backward compatible when strict_mode not provided

---

### Subtask T003 – Add result_to_json() helper function

**Purpose**: Convert ImportResult to structured dict for CLI --json output.

**Steps**:

1. Open `src/utils/import_export_cli.py`

2. Add helper function near other helpers (around line ~200-250):
   ```python
   def result_to_json(result: ImportResult) -> dict:
       """Convert ImportResult to structured dict for JSON output.

       Args:
           result: ImportResult from import operation

       Returns:
           dict suitable for json.dumps() with:
           - success: bool (True if no failures)
           - imported: int (successful count)
           - skipped: int (skipped count)
           - failed: int (error count)
           - errors: list[dict] (error details with field paths)
           - warnings: list[dict] (warning details)
           - entity_counts: dict (per-entity breakdown)
       """
       return {
           "success": result.failed == 0,
           "imported": result.successful,
           "skipped": result.skipped,
           "failed": result.failed,
           "errors": result.errors,
           "warnings": result.warnings,
           "entity_counts": result.entity_counts,
       }
   ```

3. Add import at top if needed:
   ```python
   from src.services.import_export_service import ImportResult
   ```
   (Check if already imported)

**Files**: `src/utils/import_export_cli.py`

**Parallel?**: No - should be done after T001/T002

**Validation**:
- Function can be called with any ImportResult
- Output is valid JSON-serializable dict
- Includes all required fields per spec

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Breaking existing imports | Keep strict_mode=False as default |
| Missing early exit points | Review all error paths in both functions |
| ImportResult import collision | Check existing imports before adding |

---

## Definition of Done Checklist

- [ ] T001: strict_mode parameter added to import_purchases()
- [ ] T002: strict_mode parameter added to import_adjustments()
- [ ] T003: result_to_json() helper function added
- [ ] All existing tests pass
- [ ] No linting errors
- [ ] Backward compatibility verified (default behavior unchanged)

---

## Review Guidance

**Reviewers should verify**:
1. Function signatures match the spec exactly
2. Early exit logic is in the correct location (after resolution failure, before continue)
3. Default behavior is unchanged (strict_mode=False)
4. result_to_json() output matches spec JSON format
5. No duplicate imports added

---

## Activity Log

- 2026-01-29T04:45:00Z – system – lane=planned – Prompt created.
- 2026-01-29T04:55:42Z – claude – shell_pid=24063 – lane=doing – Started implementation via workflow command
- 2026-01-29T05:06:48Z – claude – shell_pid=24063 – lane=for_review – Ready for review: Added strict_mode to import_purchases/import_adjustments and result_to_json helper. All 3191 tests pass.
- 2026-01-29T05:20:10Z – claude – shell_pid=30076 – lane=doing – Started review via workflow command
