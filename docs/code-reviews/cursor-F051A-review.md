# Code Review Report: F051A - Import/Export UI Rationalization (Re-review)

**Reviewer:** Cursor (Independent Review)
**Date:** 2026-01-13
**Feature Spec:** `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/051-import-export-ui-rationalization/kitty-specs/051-import-export-ui-rationalization/spec.md`

## Executive Summary
Re-review after fixes: core blockers are resolved (catalog augment mode now works via `import_catalog`; supplier import/merge no longer crashes; context-rich preprocessing/validation added; schema validation runs before catalog imports). Remaining gaps are around directory preference storage/usage and catalog schema validation coverage for non-core entities. No test updates were required; targeted suites pass.

## Review Scope

**Primary Files Re-reviewed:**
- `.worktrees/051-import-export-ui-rationalization/src/ui/import_export_dialog.py`
- `.worktrees/051-import-export-ui-rationalization/src/services/catalog_import_service.py`
- `.worktrees/051-import-export-ui-rationalization/src/services/schema_validation_service.py`
- `.worktrees/051-import-export-ui-rationalization/src/services/preferences_service.py`
- `.worktrees/051-import-export-ui-rationalization/src/ui/main_window.py`

**Tests executed:**
- `python -c "from src.services.schema_validation_service import validate_import_file; print('Import OK')"`
- `pytest src/tests/test_schema_validation_service.py -v --tb=short -q`
- `pytest src/tests/test_preferences_service.py -v --tb=short -q`

## Environment Verification

**Commands (outside sandbox):**
```bash
cd /Users/kentgale/Vaults-repos/bake-tracker/.worktrees/051-import-export-ui-rationalization
/Users/kentgale/Vaults-repos/bake-tracker/venv/bin/python -c "from src.services.schema_validation_service import validate_import_file; print('Import OK')"
/Users/kentgale/Vaults-repos/bake-tracker/venv/bin/python -m pytest src/tests/test_schema_validation_service.py -v --tb=short -q 2>&1 | head -20
/Users/kentgale/Vaults-repos/bake-tracker/venv/bin/python -m pytest src/tests/test_preferences_service.py -v --tb=short -q 2>&1 | head -40
```

**Results:** All commands succeeded; schema validation tests (51) and preferences tests (27) passed.

---

## Findings

### Major Concerns

**Directory preferences still not persisted/applied per spec**
- **Location:** `preferences_service.py`, `import_export_dialog.py`
- **Problem:** Preferences are stored in a JSON file under `~/Library/Application Support/BakeTracker` instead of the spec-required `app_config` table, and Import/Export file pickers don’t use the configured directories as initial locations. User Story 6 acceptance (file dialogs start in configured dirs; persistence via app_config) is not met.
- **Recommendation:** Persist import/export/logs directories in `app_config`; seed file dialogs (`askopenfilename`/`asksaveasfilename`/`askdirectory`) with those preferences; keep JSON fallback only if explicitly accepted.
```1:88:.worktrees/051-import-export-ui-rationalization/src/services/preferences_service.py
# JSON-backed prefs; not stored in app_config as spec requires
```

**Schema validation coverage still limited to suppliers/ingredients/products/recipes**
- **Location:** `schema_validation_service.py`
- **Problem:** Catalog/backup files that include materials/material_products/material_units (supported by catalog import) bypass schema validation or yield only “unexpected field” warnings. FR-012 expects pre-import structural validation for all catalog entities.
- **Recommendation:** Add validators for materials/material_products/material_units (and any other catalog entities) with required/optional fields and type checks; ensure catalog/backup validation paths include them.
```135:243:.worktrees/051-import-export-ui-rationalization/src/services/schema_validation_service.py
# Validators exist only for suppliers/ingredients/products/recipes
```

### Minor Issues

- Catalog export entity list is manually ordered; although Suppliers are present, the ordering isn’t clearly alphabetical, which may drift from the “alphabetical with Suppliers” acceptance nuance.
- Preferences logs default remains `docs/user_testing`; if directory prefs are meant to control logs, align defaults with user-configurable location.

### Positive Observations
- Catalog import now routes through `import_catalog`, so “Add” and “Augment” modes work without backend mode errors, and schema validation runs before import.
- Supplier import/merge in `catalog_import_service` now tracks suppliers in `entity_counts` and uses `add_augment`/`add_skip`, removing the previous crash.
- Context-rich import flow now preprocesses `aug_*.json`, strips to editable fields, validates normalized data, and blocks on missing slugs before import—meeting FR-010/011 intent.

## Recommendations Priority

**Must Fix Before Merge:**
1. Persist and apply directory preferences per spec (app_config + dialog initial dirs).
2. Expand schema validation to cover materials/material_products/material_units (and any other catalog entities) to honor FR-012 for full catalog/backup files.

**Should Fix Soon:**
1. Align catalog export entity ordering to an explicit alphabetical list including Suppliers; clarify UX expectation.
2. Consider using the configured logs directory as default rather than repo `docs/user_testing`.

**Consider for Future:**
1. Add tests for context-rich preprocessing/validation with missing FKs and for catalog imports that include materials to guard the expanded schemas.

## Overall Assessment
Improvements landed: prior critical blockers resolved, and core flows run without crashes. Remaining work centers on spec alignment for directory preferences and broader schema validation. Address those before shipping to meet User Story 6 and FR-012/014 coverage expectations.
