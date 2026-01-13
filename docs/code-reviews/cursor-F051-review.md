# Code Review Report: F051 - Import/Export UI Rationalization

**Reviewer:** Cursor (Independent Review)
**Date:** 2026-01-13
**Feature Spec:** `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/051-import-export-ui-rationalization/kitty-specs/051-import-export-ui-rationalization/spec.md`

## Executive Summary
The unified Import dialog and new schema/preferences services are wired in, but several critical implementation gaps break catalog import flows (augment mode crashes), supplier merge logic (missing method), and context-rich preprocessing/validation. Preferences storage and catalog export/import UX diverge from spec (directory persistence in app_config, no catalog auto-detect, suppliers checkbox ordering). Schema validation is both incomplete and applied only to context-rich paths, not the required catalog/backup imports.

## Review Scope

**Primary Files Modified:**
- `.worktrees/051-import-export-ui-rationalization/src/ui/import_export_dialog.py`
- `.worktrees/051-import-export-ui-rationalization/src/ui/main_window.py`
- `.worktrees/051-import-export-ui-rationalization/src/ui/preferences_dialog.py`
- `.worktrees/051-import-export-ui-rationalization/src/services/import_export_service.py`
- `.worktrees/051-import-export-ui-rationalization/src/services/catalog_import_service.py`
- `.worktrees/051-import-export-ui-rationalization/src/services/schema_validation_service.py`
- `.worktrees/051-import-export-ui-rationalization/src/services/preferences_service.py`
- `.worktrees/051-import-export-ui-rationalization/src/tests/test_schema_validation_service.py`
- `.worktrees/051-import-export-ui-rationalization/src/tests/test_preferences_service.py`

**Additional Code Examined:**
- Preferences defaults and logging in `import_export_dialog`
- Entity detection logic in `enhanced_import_service` (referenced by UI)

## Environment Verification

**Setup Process:**
```bash
cd /Users/kentgale/Vaults-repos/bake-tracker/.worktrees/051-import-export-ui-rationalization
/Users/kentgale/Vaults-repos/bake-tracker/venv/bin/python -c "from src.services.schema_validation_service import validate_import_file; print('Import OK')"
/Users/kentgale/Vaults-repos/bake-tracker/venv/bin/python -m pytest src/tests/test_schema_validation_service.py -v --tb=short -q 2>&1 | head -20
```

**Results:**
- Import smoke: OK.
- Targeted pytest: 51 tests passed (schema_validation_service).

---

## Findings

### Critical Issues

**Catalog import “Augment” mode always crashes (invalid mode)**
- **Location:** `ImportDialog._do_catalog_import`
- **Problem:** Mode radio offers “Add”/“Augment”, but call maps `"add"`→`"merge"` and passes `"augment"` directly to `import_all_from_json_v4`, which only accepts `merge|replace`, so selecting Augment raises `ValueError` and aborts.
- **Impact:** Acceptance scenarios for catalog import/update fail; users cannot run augment mode.
- **Recommendation:** Map UI modes to supported backend modes (e.g., add→`skip_existing`, augment→`merge`/`augment` with backend support), or extend backend to honor augment; update validation/tests.
```925:929:.worktrees/051-import-export-ui-rationalization/src/ui/import_export_dialog.py
                result = import_export_service.import_all_from_json_v4(
                    self.file_path,
                    mode="merge" if mode == "add" else mode,
                )
```

**Supplier merge path raises AttributeError and lacks counts**
- **Location:** `catalog_import_service.py` supplier import loop
- **Problem:** When an existing supplier is found, code calls `result.add_update(...)` but `CatalogImportResult` defines no such method; entity_counts also omit `suppliers`. Any merge/skip path hits AttributeError before finishing.
- **Impact:** Catalog imports with existing suppliers fail; supplier stats/logging are missing, violating supplier round-trip and dependency ordering scenarios.
- **Recommendation:** Add supplier to `entity_counts`; implement a supplier update/augment helper (or use `add_skip`/`add_augment`), and cover with tests.
```2831:2866:.worktrees/051-import-export-ui-rationalization/src/services/import_export_service.py
                                if updated_fields:
                                    result.add_update("supplier", ... )  # method does not exist
                                else:
                                    result.add_skip("supplier", ... )
```

**Context-Rich import skips required preprocessing/FK validation and validates at wrong stage**
- **Location:** `ImportDialog._do_context_rich_import`
- **Problem:** It validates the raw aug file with `schema_validation_service` (whose schema doesn’t match aug format) and then calls `import_context_rich_view` directly—no preprocessing to normalized form, no FK validation, no blocking on missing refs. Spec requires preprocessing then schema validation on normalized output and FK blocking errors.
- **Impact:** Missing-FK files won’t surface actionable errors; valid aug files may fail schema validation due to schema mismatch; spec FR-010/010a/010b/011 not met.
- **Recommendation:** Preprocess aug_*.json to normalized data (strip readonly fields, resolve FK), then run schema validation on the normalized data, abort on FK errors, and pass normalized data to the importer. Adjust UI messaging/logging accordingly.
```957:1010:.worktrees/051-import-export-ui-rationalization/src/ui/import_export_dialog.py
            raw_data = json.load(f)
            validation_result = schema_validation_service.validate_import_file(raw_data)
            ...
            result = import_context_rich_view(self.file_path)  # no preprocessing/FK validation
```

**Schema validation misaligned and not applied to catalog/backup imports**
- **Location:** `schema_validation_service.py`; `ImportDialog._do_catalog_import` / `_do_backup_restore`
- **Problem:** Validator only knows limited fields (e.g., products require `display_name`, suppliers only `name/slug/contact/notes`), so real catalog exports (brand/product_name/city/state/slug) would fail validation. Moreover, validation is only invoked for context-rich, not for catalog/backup despite FR-012.
- **Impact:** Either false positives (if enabled) or no protection against malformed catalog/backup files (current behavior).
- **Recommendation:** Expand schemas to match actual catalog/backup payloads (suppliers: slug/supplier_type/city/state/zip..., products: brand/product_name/preferred_supplier_slug/etc., materials if present); run validation before catalog/backup imports; treat unexpected fields as warnings per spec. Cover with multi-entity fixtures.
```135:231:.worktrees/051-import-export-ui-rationalization/src/services/schema_validation_service.py
supplier_fields = {"name","slug","contact_info","notes"}  # misses city/state/slug rules
```

### Major Concerns

**Catalog export still uses entity checkboxes and supplier ordering is non-alphabetic**
- **Location:** `ExportDialog._setup_catalog_tab`
- **Problem:** UI presents manual entity checkboxes (including suppliers) and ordering is not alphabetical (`suppliers` last). Spec FR-009 expects no entity checkboxes for Catalog import (auto-detect) and FR-003 wants Suppliers checkbox present alphabetically in export.
- **Impact:** UX diverges from rationalized flow; supplier checkbox appears but ordering and auto-detect expectations aren’t met.
- **Recommendation:** For export, sort entities alphabetically and ensure suppliers included; for import, hide entity selection for Catalog purpose and rely on detection display instead.

**Preferences storage and usage diverge from spec**
- **Location:** `preferences_service.py`, `import_export_dialog.py`, `preferences_dialog.py`
- **Problem:** Preferences are stored in a JSON file under `~/Library/Application Support/BakeTracker`, not in `app_config` (spec FR-016). Import/export file pickers ignore preferences for initial directories; logs default to repo `docs/user_testing`.
- **Impact:** Preferences may not follow app_config persistence requirement; users don’t get preferred directories in dialogs; logs may still land in repo.
- **Recommendation:** Persist directories in `app_config`, preload file dialogs with stored prefs, and use prefs for logs directory consistently.

### Minor Issues

- Context-rich schema validation uses the same path as catalog but without tailoring to aug formats; warnings/errors shown may be confusing.
- Supplier schema ignores slug format from F050 (underscores allowed) vs hyphen regex; consider aligning patterns.

### Positive Observations
- Unified File menu now exposes a single Import entry and removes the prior Catalog/Context-Rich items, matching the consolidated entry-point goal.
```94:104:.worktrees/051-import-export-ui-rationalization/src/ui/main_window.py
file_menu.add_command(label="Import Data...", command=self._show_import_dialog)
# removed separate Import Catalog / Import View entries
```
- Logging function in `import_export_dialog` adds structured sections (SOURCE, OPERATION, VALIDATION, RESULTS, ERRORS, WARNINGS, SUMMARY, METADATA) with truncation safeguards, aligning with the spec’s comprehensive logging intent.
```114:299:.worktrees/051-import-export-ui-rationalization/src/ui/import_export_dialog.py
_write_import_log(... MAX_LOG_ENTRIES ...)
```

## Spec Compliance Analysis
- FR-001/002: Single Import Data menu present; old menu entries removed.
- FR-003/004 (supplier export): Suppliers checkbox present but not alphabetical; supplier export is available.
- FR-005/007/020: Auto-detection shown in UI, but catalog import still allows/needs manual entity selection; dependency-order import exists but supplier merge path broken.
- FR-008/009: Catalog import still exposes entity selection via export tab, and augment mode fails; no add-only vs update-only clarity.
- FR-010/010a/010b/011: Context-rich preprocessing and FK blocking not implemented; validation order incorrect.
- FR-012/013/014: Schema validation not applied to catalog/backup and schemas are incomplete; unexpected fields handled as warnings, consistent where used.
- FR-015/016/017/018/019: Preferences stored outside app_config and not used to seed dialogs; logs written with sections but directory pref/spec persistence gaps remain.
- FR-021/022: Existing backup/purchases/adjustments flows untouched but not validated; risk of regressions from shared dialog logic.

## Code Quality Assessment
**Consistency:** UI patterns match prior dialogs; logging helper is structured. Supplier import logic diverges from established result API (missing add_update).
**Maintainability:** Preferences service is self-contained but diverges from DB persistence; schema validator needs broader coverage to avoid drift.
**Test Coverage:** New tests cover schema validator and preferences service in isolation; no UI/flow tests, no supplier import merge coverage, no catalog augment path coverage, and no context-rich preprocessing tests.
**Dependencies & Integration:** Supplier import relies on enhanced generate_slug; merge path currently broken; preferences not integrated with app_config as required.

## Recommendations Priority

**Must Fix Before Merge:**
1. Fix catalog import mode mapping: support augment/update mode without passing invalid `"augment"` to `import_all_from_json_v4`; ensure add-only maps to skip-existing. Add tests.
2. Repair supplier merge handling in catalog import: add supplier entity counts, replace `add_update` with a valid update/augment recording method, and test merge/augment paths.
3. Implement context-rich preprocessing + FK validation workflow; run schema validation after preprocessing on normalized data; block on missing FKs with actionable errors.
4. Extend schema validation to actual catalog/backup schemas (suppliers/products/materials) and apply it to catalog/backup imports per FR-012 with warning semantics for unexpected fields.

**Should Fix Soon:**
1. Align Catalog UI with rationalized flow: remove entity checkboxes for import, rely on auto-detection display; ensure suppliers checkbox ordering is alphabetical in export.
2. Persist directory preferences in `app_config` and seed Import/Export dialogs (and log directory) from stored preferences.

**Consider for Future:**
1. Expand tests to cover end-to-end import flows (catalog add/augment, supplier merge, context-rich with FK errors, multi-entity detection).
2. Revisit slug validation patterns to align with F050 (allow underscores) across schema validation and UI messages.

## Overall Assessment
Needs revision. The unified dialog and logging scaffolding are present, but core workflows (catalog augment, supplier merge, context-rich preprocessing/validation, schema validation coverage, preferences integration) are incomplete or broken. Address the critical issues before shipping to ensure imports function as specified and produce the promised validation/logging experience.
