# Bug Fix: Import/Export Backward-Compatibility Importer Must Not Exist

**Branch**: `040-import-export-v4`
**Priority**: HIGH (policy violation + ongoing maintenance risk)
**Estimated Effort**: 30–60 minutes
**Status**: ✅ Fixed

## Context

Bake Tracker’s import/export strategy is:

- **No backward compatibility import functions**
- **No programmatic transforms between schema versions**
- **No version-based branching/gating** (version is informational; schema compliance is what matters)

If an import file does not comply with the current spec/schema, it should **fail** and the file should be **manually adjusted** (often via instructions to Claude / a spec update).

## Problem

During Feature 040 (Import/Export v4) work, a legacy full-database importer entrypoint (`import_all_from_json_v3`) existed and was used by UI/CLI/tests. This introduced two problems:

1. **Backward-compat import behavior existed**, which violates policy.
2. A **version-gating check** existed in the v4 importer (`version == "4.0"`), which violates policy.

This created confusion, made it easy for “old-format import” logic to creep in, and caused test breakages when the legacy importer was removed.

## Root Cause

- Legacy importer (`import_all_from_json_v3`) remained as a public API and was still referenced by:
  - UI import dialog
  - CLI import command
  - multiple integration/unit test suites
- `import_all_from_json_v4` enforced `data["version"] == "4.0"` rather than relying purely on current-schema validation.

## Solution (What Changed)

### 1) Remove backward-compat import API

- **Removed** `import_all_from_json_v3` entirely.
- **Removed** any “upgrade header / transform” logic used to make older files import.

### 2) Remove version gating

- **Removed** the explicit `version == "4.0"` rejection in `import_all_from_json_v4`.
- Import success/failure is now determined by schema/field validity + FK resolution + model validation.

### 3) Rewire all entrypoints to current importer only

- UI import dialog now calls **`import_all_from_json_v4`**
- CLI import command now calls **`import_all_from_json_v4`**

### 4) Update tests to enforce policy

- Tests that referenced the legacy importer were updated to call the current importer.
- Tests asserting version rejection were updated/removed to align with “version is informational only.”

## Files Changed (high level)

**Core:**
- `.worktrees/040-import-export-v4/src/services/import_export_service.py`

**Entry points:**
- `.worktrees/040-import-export-v4/src/ui/import_export_dialog.py`
- `.worktrees/040-import-export-v4/src/utils/import_export_cli.py`

**Tests:**
- `.worktrees/040-import-export-v4/src/tests/services/test_import_export_service.py`
- `.worktrees/040-import-export-v4/src/tests/integration/test_import_export_027.py`
- `.worktrees/040-import-export-v4/src/tests/integration/test_nested_recipes_flow.py`
- `.worktrees/040-import-export-v4/src/tests/integration/test_packaging_flow.py`

## Verification

**Required checks (examples):**

- `PYTHONPATH=. python3 -m pytest src/tests/services/test_import_export_service.py -q`
- `PYTHONPATH=. python3 -m pytest src/tests -q`

**Expected result:** full suite passes.

## Acceptance Criteria

- [x] No `import_all_from_json_v3` symbol exists in runtime code
- [x] UI/CLI import flows use only the current importer (`import_all_from_json_v4`)
- [x] Current importer does not reject/branch on `version`
- [x] Full test suite passes

## Notes / Rationale

This approach intentionally pushes format adjustments into:

- spec updates, and/or
- manual JSON edits / Claude-assisted transformations in `test_data/`

…instead of growing the application’s runtime complexity with compatibility layers that are expensive to maintain and easy to get subtly wrong.


