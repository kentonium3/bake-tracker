# Code Review Report: F054 - CLI Import/Export Parity

**Reviewer:** Cursor (Independent Review)
**Date:** 2026-01-15
**Feature Spec:** `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/054-cli-import-export-parity/kitty-specs/054-cli-import-export-parity/spec.md`

## Executive Summary
CLI commands are added, but several parity gaps remain: catalog export/import cannot round-trip (exports a directory, import/validate expect a single file and only add/augment modes), aug-export “all” produces extra non-spec files, and aug-import/validate rely on a service mapping that still cannot handle the new entity types (material-products/finished-units/finished-goods). Restore lacks mode/interactive options required by the spec and always performs replace. These break key user stories for aug/catalog workflows and restore safety.

## Review Scope

**Primary Files Modified:**
- `.worktrees/054-cli-import-export-parity/src/utils/import_export_cli.py`

**Additional Code Examined:**
- `src/services/coordinated_export_service.py` (call signatures)
- `src/services/denormalized_export_service.py` (export_all_context_rich behavior)
- `src/services/enhanced_import_service.py` (context-rich import/format detection mapping)
- `src/services/catalog_import_service.py` (import_catalog/validate_catalog_file expectations)

## Environment Verification

**Setup Process:**
```bash
cd /Users/kentgale/Vaults-repos/bake-tracker/.worktrees/054-cli-import-export-parity
/Users/kentgale/Vaults-repos/bake-tracker/venv/bin/python src/utils/import_export_cli.py --help 2>&1 | grep -E "backup|restore|aug-|catalog-"
/Users/kentgale/Vaults-repos/bake-tracker/venv/bin/python -c "
from src.utils.import_export_cli import (
    backup_cmd, restore_cmd, backup_list_cmd, backup_validate_cmd,
    aug_export_cmd, aug_import_cmd, aug_validate_cmd,
    catalog_export_cmd, catalog_import_cmd, catalog_validate_cmd,
); print('All CLI function imports successful')"
/Users/kentgale/Vaults-repos/bake-tracker/venv/bin/python -c "
from src.services.coordinated_export_service import export_complete, import_complete, validate_export
from src.services.denormalized_export_service import export_products_context_rich
from src.services.enhanced_import_service import import_context_rich_export, detect_format
from src.services.catalog_import_service import import_catalog, validate_catalog_file
print('All service imports successful')"
```

**Results:**
- All three verification commands succeeded; CLI help shows new commands.

---

## Findings

### Critical Issues

**Catalog CLI cannot round-trip and ignores replace/interactive modes**
- **Location:** `import_export_cli.py` (`catalog_export_cmd`, `catalog_import_cmd`, subparser args)
- **Problem:** `catalog-export` writes multiple files to a directory; `catalog-import`/`catalog-validate` expect a single JSON file path and only support modes add/augment (no replace), with no interactive FK resolution flag. This breaks the spec’s directory-based catalog flow (US3/FR-201–205) and omits replace/interactive options.
```1121:1144:src/utils/import_export_cli.py
elif entity == "suppliers":
    entry = _export_suppliers(output_path, session)  # writes files in dir
...
def catalog_import_cmd(input_file: str, mode: str = "add", dry_run: bool = False):
    input_path = Path(input_file)  # expects single file
    result = import_catalog(input_file, mode=mode, dry_run=dry_run)
```
- **Impact:** Catalog export cannot be imported back via CLI; required modes/flags missing.
- **Recommendation:** Make catalog import/validate operate on the export directory, support add/augment/replace and interactive FK resolution, and align entity list with spec. Update help text accordingly.

**Aug-export “all” produces non-spec files; aug-import/validate can’t handle new types**
- **Location:** `aug_export_cmd` uses `export_all_context_rich`; `enhanced_import_service` mapping (from F053) still lacks new types.
- **Problem:** `export_all_context_rich` emits 9 files (adds inventory/purchases) while CLI/UI spec lists 7 aug entities. Additionally, CLI exposes `material-products`, `finished-units`, `finished-goods`, but `import_context_rich_export`/`detect_format` do not map these export_type values, so CLI aug-import for those will fail.
```926:939:src/utils/import_export_cli.py
results = export_all_context_rich(output_dir)  # returns inventory/purchases too

1316:1334:src/services/enhanced_import_service.py  # mapping lacks material_products/finished_units/finished_goods
```
- **Impact:** `aug-export -t all` generates unexpected extra files; aug-import for newly added types is broken, defeating CLI parity for AI workflows.
- **Recommendation:** Align `export_all_context_rich` to 7 entities (or filter in CLI), and extend import/format detection mapping to support the new aug entity types.

**Restore lacks mode/interactive options and always replaces data**
- **Location:** `restore_cmd` and subparser
- **Problem:** Restore subparser has no `--mode`/`--interactive`; restore_cmd calls `import_complete(backup_dir)` with no mode and warns “replace” unconditionally. Spec requires add/augment/replace and interactive FK resolution.
```1754:1762:src/utils/import_export_cli.py  # parser has only backup_dir
728:779:src/utils/import_export_cli.py       # restore_cmd calls import_complete without mode
```
- **Impact:** Users cannot perform safer add/augment restores or interactive resolution; behavior diverges from FR-106/FR-107.
- **Recommendation:** Add mode/interactive flags, pass through to service (or document limitation and adjust spec/CLI help).

### Major Concerns

**Catalog-validate is file-based, not directory-based**
- **Location:** `catalog_validate_cmd`
- **Problem:** Validates a single file via `validate_catalog_file`, not the directory of per-entity files produced by catalog-export. Does not check required files per spec.
- **Impact:** False sense of validation; directory exports cannot be validated via CLI.
- **Recommendation:** Validate the export directory contents (expected files/entity counts) or adjust catalog-export to emit the same single-file format expected by validator.

**Aug-export “all” summary hides extra entities**
- **Location:** `aug_export_cmd`
- **Problem:** CLI prints counts for whatever export_all_context_rich returns; since that includes inventory/purchases, users may assume 7 when 9 files are produced; filenames/prefixes not surfaced in help.
- **Impact:** Confusing UX; downstream scripts may mis-handle unexpected files.
- **Recommendation:** Filter to spec entity set or update help/docs to list all produced files explicitly.

### Minor Issues

**Catalog import help text and parameter names suggest file, not directory**
- Parser argument is `input_file`, help “Input catalog JSON file” while export writes a directory. Mismatch invites user error.
- Recommendation: Rename to `input_dir` and describe expected layout.

**Mode coverage gaps**
- Catalog import only supports add/augment; spec calls for replace as well. Restore lacks mode; aug-import lacks explicit mode (merge/skip) though service may default—document or expose.

## Positive Observations
- New commands are registered and appear in `--help`; docstring/epilog include examples for new groups.
- Backup commands honor `--zip` and list/validate helpers reuse checksum validation.
- Aug commands reuse existing CLIFKResolver for interactive FK prompts; add warnings for missing files.

## Spec Compliance Analysis
- **Backup/Restore (FR-101–107):** Backup/list/validate present; restore missing mode/interactive flags (FR-106/FR-107).
- **Aug (FR-301–306):** Commands present; “all” exports wrong set (9 vs 7). Import/validate cannot handle new entity types, breaking round-trip.
- **Catalog (FR-201–205):** Catalog-export writes directory of files; catalog-import/validate expect single file and only add/augment modes—non-compliant.
- **Entity exports (FR-401–504):** Commands registered; not deeply validated here, but dependent on import_export_service functions.
- **Documentation (FR-601–603):** Help text/examples largely present; misalignment around catalog path semantics and aug “all” outputs.

## Code Quality Assessment
- Follows existing argparse patterns; command wiring centralized in main().
- Coupling to service behavior (export_all_context_rich, import_context_rich_export, import_catalog) is implicit and currently inconsistent with CLI surface, causing parity gaps.
- Limited input validation (e.g., no entity filter for aug “all”, catalog path type).

## Recommendations Priority

**Must Fix Before Merge:**
1. Align catalog export/import/validate: use the same format (directory vs single file), support add/augment/replace (and interactive if applicable), and update help text.
2. Fix aug “all” to export exactly the 7 spec entities, or document and filter; extend enhanced_import_service mapping so aug-import/validate support `material-products`, `finished-units`, `finished-goods`.
3. Add restore mode/interactive flags and pass through to the restore implementation (or clearly constrain behavior).

**Should Fix Soon:**
1. Update catalog-validate to check the actual export format (directory contents) and required files.
2. Improve help/arg names to reflect expected inputs (catalog directory, restore modes).

**Consider for Future:**
1. Add tests for new CLI commands (especially aug “all” and catalog export/import).
2. Consider a shared entity-set constant for aug/catalog to avoid drift from service implementations.

## Overall Assessment
Needs revision. Commands surface is present, but aug/catalog flows are not spec-compliant and restore lacks required safety/options. Address the format/mapping/mode gaps above before shipping.
