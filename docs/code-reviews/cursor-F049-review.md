# Code Review Report: F049 - Import/Export System Phase 1

**Reviewer:** Cursor (Independent Review)
**Date:** 2026-01-12
**Feature Spec:** /Users/kentgale/Vaults-repos/bake-tracker/.worktrees/049-import-export-phase1/kitty-specs/049-import-export-phase1/spec.md

## Executive Summary
Phase 1 extends backup/restore, catalog imports (incl. materials), context-rich exports/imports, and transaction imports. Verification commands passed, but two spec-critical gaps remain: the UI “Backup Restore” flow cannot restore the new coordinated backup format, and the context-rich importer updates fields marked readonly/computed. Adjustment imports also reject a required reason code and are case-sensitive. Needs revision before release.

## Review Scope

**Primary Files Modified:**
- `src/services/coordinated_export_service.py`
- `src/services/denormalized_export_service.py`
- `src/services/enhanced_import_service.py`
- `src/services/transaction_import_service.py`
- `src/ui/import_export_dialog.py`
- Tests under `src/tests/services/` and `src/tests/integration/test_import_export_roundtrip.py`

**Additional Code Examined:**
- `src/services/catalog_import_service.py` (materials catalog path)
- Spec/docs: `docs/design/spec_import_export.md`

## Environment Verification

**Setup Process:**
```bash
cd /Users/kentgale/Vaults-repos/bake-tracker/.worktrees/049-import-export-phase1
/Users/kentgale/Vaults-repos/bake-tracker/venv/bin/python -c "from src.services.coordinated_export_service import export_complete; from src.services.denormalized_export_service import export_ingredients_view; from src.services.enhanced_import_service import detect_format; from src.services.transaction_import_service import import_purchases, import_adjustments; from src.ui.import_export_dialog import ImportDialog, ExportDialog; print('All imports successful')"
/Users/kentgale/Vaults-repos/bake-tracker/venv/bin/pytest src/tests/services/test_transaction_import_service.py -v --tb=short -q 2>&1 | tail -20
```

**Results:**
- Imports: `All imports successful`
- Tests: `44 passed, 40 warnings` (SAWarning on drop_all cycles, SQLAlchemy legacy Query.get warning)

---

## Findings

### Critical Issues

**Backup restore flow cannot restore coordinated backup exports**
- **Location:** `src/ui/import_export_dialog.py` (`ImportDialog._do_backup_restore`)
- **Problem:** Export dialog writes multi-file coordinated backups (`export_complete` + `manifest.json`), but the Backup Restore path calls `import_export_service.import_all_from_json_v4` expecting a single normalized JSON file. There is no import path for the coordinated backup set.
- **Impact:** Users cannot restore the backups created by the new Full Backup export; User Story 1/FR-001/002 acceptance (“backup → reset → restore all 16 entities via manifest”) fails.
- **Recommendation:** Add an import path for coordinated exports (read `manifest.json`, ingest the 16 entity files in dependency order) and wire Backup Restore to it; alternatively, export and restore must use the same format (either both coordinated or both normalized) with clear UX.

**Context-rich import writes readonly/computed fields**
- **Location:** `src/services/enhanced_import_service.py` (`_import_record_merge`)
- **Problem:** For purchases and inventory items, the importer unconditionally adds `unit_price`, `quantity_purchased`, and `unit_cost` to `fields_to_update`, overriding the `_meta.editable_fields` contract.
- **Impact:** Computed/readonly fields from context-rich exports can be imported back and overwrite canonical data (violates FR-014, risks cost corruption).
- **Recommendation:** Honor `_meta.editable_fields` strictly; remove the special-casing that updates price/quantity fields for purchases/inventory items during context-rich imports.

**Adjustment import rejects required reason code and is case-sensitive**
- **Location:** `src/services/transaction_import_service.py` (`ALLOWED_REASON_CODES`, `_process_single_adjustment`)
- **Problem:** Allowed set is `{"spoilage","waste","correction","other"}` (missing `DAMAGED`), and comparison is case-sensitive.
- **Impact:** Valid files using spec codes (`DAMAGED`, upper-case) are rejected (fails User Story 5 / FR-021 acceptance).
- **Recommendation:** Include `damaged` in the allowed set and normalize reason_code case-insensitively before validation.

### Major Concerns

- **Slug-first requirement vs. ID-heavy coordinated exports**
  - **Location:** `src/services/coordinated_export_service.py` (entity files include ids and foreign key ids).
  - **Problem:** FR-004 calls for slug-based references in exports; coordinated exports emit IDs alongside slugs (and some refs only as IDs).
  - **Impact:** Restoring on a clean database or different instance risks FK mismatch if IDs differ; undercuts “slug-based” portability goal.
  - **Recommendation:** Ensure all FK references in export files are slug-based (ids optional at most); include composite product/material slugs consistently.

### Minor Issues

- **Reason codes in UI copy differ from validator**
  - Import dialog text lists uppercase codes; service expects lowercase. Fix once service is made case-insensitive to avoid UX confusion.

### Positive Observations

- Coordinated export now covers all 16 entities with manifest and checksums.
- Context-rich exports for ingredients/materials/recipes include hierarchy paths, nested relationships, and computed values with `_meta` editable/readonly annotations.
- Transaction import tests cover duplicate detection, negative-only adjustments, FIFO depletion, and invalid quantity cases.
- Import dialog clearly separates four purposes and auto-detects context/purchase/adjustment formats for user confirmation.

## Spec Compliance Analysis
- **User Story 1 (Complete backup/restore):** Export side meets 16-entity requirement, but restore path does not consume the exported format, so round-trip acceptance fails. IDs in exports also dilute slug-based portability.
- **User Story 2 (Materials catalog import):** Catalog import service includes materials/material_products/material_units paths; not fully exercised here, but structure follows ingredient pattern.
- **User Story 3 (Context-rich export):** Views exist for ingredients/materials/recipes with hierarchy and computed fields; good alignment.
- **User Story 4/5 (Purchase/Adjustment imports):** Core flows implemented; positive quantity validation and duplicate checks for purchases, negative-only validation for adjustments. However, reason code handling violates spec (missing DAMAGED, case sensitivity).
- **User Story 6 (Context-rich import auto-detect):** detect_format surfaces context-rich and auto-selects catalog flow; but importer violates editable/readonly contract.
- **User Story 7 (UI redesign):** Import dialog distinguishes four purposes and shows detected format; export dialog separates full backup, catalog, and context-rich.

## Code Quality Assessment

**Consistency with Codebase:** Largely follows existing service/UI patterns; coordinated export mirrors earlier entity exports.
**Maintainability:** Clear separation of service concerns; however, mixing readonly overrides in context-rich import increases surprise and risk.
**Test Coverage:** Transaction import has focused tests; coordinated export/restore parity and context-rich import field protection lack coverage.
**Dependencies & Integration:** Backup export/import mismatch indicates integration gap; slug-vs-id tension remains for portability.

## Recommendations Priority

**Must Fix Before Merge:**
1. Add coordinated backup restore path and wire Import “Backup Restore” to it (or align export format with restore format).
2. Honor `_meta.editable_fields` in context-rich imports; stop writing readonly/computed fields.
3. Make adjustment reason_code validation case-insensitive and include `DAMAGED`.

**Should Fix Soon:**
1. Ensure coordinated exports use slug-based references for all FKs (IDs optional only).
2. Align UI messaging with reason code validation once fixed.

**Consider for Future:**
1. Persist weighted-average cost on purchase import once product cost field exists.
2. Add integration test for full backup round-trip (manifest-based).

## Overall Assessment
Needs revision. Backup restore cannot load the produced backup format, context-rich import writes readonly fields, and adjustment reason-code validation is incomplete. Address these before shipping to ensure backup/restore viability and protect data integrity.៥
