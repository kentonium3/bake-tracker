# Cursor Code Review: Feature 030 - Enhanced Export/Import System

**Date:** 2025-12-25
**Reviewer:** Cursor (AI Code Review)
**Feature:** 030-enhanced-export-import
**Branch:** 030-enhanced-export-import

## Summary

Feature 030 delivers a solid **export foundation** (coordinated manifest + checksums, denormalized “AI-friendly” view exports, CLI wiring, and UI entrypoints). The **import side is not feature-complete** relative to the prompt/spec: `enhanced_import_service.import_view()` appears to only support **products** (not inventory/purchases), and its FK resolution field expectations don’t line up with what the view exporters actually emit.

Additionally, the F030 test suite run shows two distinct categories of failures:
- **Known/expected**: decimal string formatting differences in denormalized exports (`"12.9900"` vs `"12.99"`)
- **Blocking**: many FK/import tests accidentally target the **production database path** (`~/Documents/BakeTracker/bake_tracker.db`) because they do not consistently use the `test_db` fixture → causing `sqlite3.OperationalError: attempt to write a readonly database` in sandboxed/CI-style environments.

## Verification Results

### Module Import Validation
- coordinated_export_service.py: **PASS**
- denormalized_export_service.py: **PASS**
- fk_resolver_service.py: **PASS**
- enhanced_import_service.py: **PASS**
- import_export_cli.py (CLI extensions): **PASS**
- fk_resolution_dialog.py: **PASS**
- import_export_dialog.py (ImportViewDialog): **PASS**
- main_window.py (menu integration): **PASS**

**Evidence:** `python3 -c "from src.services...; from src.ui...; print('All modules import successfully')"` succeeded.

### Test Results

- Full test suite: **NOT RUN** (only F030-focused subset executed)
- F030-focused subset (`src/tests/services/test_coordinated_export.py`, `test_denormalized_export.py`, `test_fk_resolver.py`, `test_enhanced_import.py`, `src/tests/utils/test_import_export_cli.py`):
  - **122 passed, 8 failed, 29 errors** (31.60s)

**Most important details:**
- **3 failures** are decimal formatting mismatches in denormalized exports:
  - `last_purchase_price` exported as `"12.9900"` but tests expect `"12.99"`
  - `unit_price` exported as `"12.9900"` but tests expect `"12.99"`
  - `total_cost` exported as `"25.9800"` but tests expect `"25.98"`
- **Most errors + several failures** are due to writes against a production DB URL:
  - `sqlite:////Users/kentgale/Documents/BakeTracker/bake_tracker.db`
  - resulting in `attempt to write a readonly database`

### Code Pattern Validation

- FKResolverCallback protocol: **correct** (`FKResolverCallback.resolve(missing) -> Resolution`)
- Session parameter pattern: **present** in:
  - `src/services/coordinated_export_service.py` (uses `session: Optional[Session] = None`)
  - `src/services/denormalized_export_service.py` (uses `session: Optional[Session] = None`)
  - `src/services/fk_resolver_service.py` (**uses `session: Session = None`**, should be `Optional[Session]`)
  - `src/services/enhanced_import_service.py` (**uses `session: Session = None`**, should be `Optional[Session]`)
- EnhancedImportResult delegation: **correct** (wraps/delegates to `ImportResult`, adds FK stats + summary)
- Modal dialog behavior: **present** (`transient()`, `grab_set()` in FK resolution dialogs and import dialogs)

## Findings

### Critical Issues

1. **Enhanced import only supports products view (inventory/purchases imports missing)**
   - `enhanced_import_service._view_type_to_entity_type()` only maps products/ingredients/suppliers; it does **not** map `"inventory"`/`"purchases"` view types produced by `denormalized_export_service`.
   - `_collect_missing_fks_for_view()` and `_check_record_fk()` only implement logic for `entity_type == "product"`.
   - **Impact:** The headline WP05/WP06 requirement (“import denormalized views for products/inventory/purchases”) is not met; UI “Import View…” can import products only, and silently cannot support other view files.

2. **FK field-name mismatch between view exports and import/FK resolution**
   - Products view exporter emits `preferred_supplier_name` / `preferred_supplier_id`, but import FK scanning looks for `supplier_name`.
   - **Impact:** supplier FK resolution is likely never triggered for product view imports; mapping/creation UI paths won’t fire when expected.

3. **UI cancel/rollback semantics are not implemented end-to-end**
   - `FKResolutionDialog._on_cancel()` returns special pseudo-entity types `__cancel_keep__` / `__cancel_rollback__`.
   - Neither `fk_resolver_service.resolve_missing_fks()` nor `enhanced_import_service.import_view()` interprets these sentinel values to keep partial results or rollback transactions.
   - **Impact:** UI presents “Cancel Import / keep vs rollback” but behavior is not enforced → user trust issue + potential partial imports.

4. **Test harness is inconsistent: many tests do not use the in-memory test DB fixture**
   - `src/tests/conftest.py::test_db` provides an in-memory DB by monkey-patching `src.services.database.get_session_factory`.
   - Several FK resolver and enhanced import tests (and fixtures) do **not** depend on `test_db`, so they use the default config environment, which is **production**, pointing at `~/Documents/BakeTracker/bake_tracker.db`.
   - **Impact:** tests error in sandboxes/CI (readonly home path), and in real dev environments could mutate a user’s production DB during tests.

### Warnings

1. **Spec drift in coordinated export dataclasses / manifest shape**
   - Prompt expects `ExportedFile` dataclass and a manifest with an explicit `import_order` list; implementation uses `FileEntry` and `ExportManifest.files[*].import_order`, no top-level `import_order` list.
   - Not inherently wrong, but it’s a divergence from the stated review prompt.

2. **Decimal formatting in denormalized export**
   - Export uses `str(Decimal)` which preserves trailing zeros (e.g., `"12.9900"`).
   - If the intended interface is “human/AI editable”, consistent formatting (likely 2dp for currency) is better and is currently failing tests.

3. **`datetime.utcnow()` deprecation warnings**
   - Both export services use `datetime.utcnow()`; Python 3.13 warns it will be removed in future versions.
   - Prefer `datetime.now(datetime.UTC)` and emit RFC3339/ISO8601 consistently.

4. **`collect_missing_fks()` does not implement product missing detection**
   - For `target_type == "product"`, missing detection is hardcoded to `False`.
   - This leaves a gap if/when inventory/purchases imports rely on product mapping via composite keys.

5. **Checksum calculation loads entire file into memory**
   - `_calculate_checksum()` reads the whole file at once; for large exports it should stream in chunks.

### Observations

- Protocol-based FK resolution is a good architectural choice: it keeps core logic in services while letting CLI/UI provide different UX.
- The denormalized view `_meta` (editable vs readonly fields) is a strong foundation for “AI augmentation” workflows.
- UI integration is minimally invasive: a single File menu item plus dialogs, keeping most behavior in services.

## Files Reviewed

| File | Status | Notes |
|------|--------|-------|
| src/services/coordinated_export_service.py | Reviewed | Works; minor spec drift (dataclass naming, return value for zip); checksum could stream; dependencies list may be incomplete (products may depend on suppliers). |
| src/services/denormalized_export_service.py | Reviewed | Works; decimal formatting mismatch with tests; consider robust recent purchase selection; `utcnow()` deprecation. |
| src/services/fk_resolver_service.py | Reviewed | Good protocol and create/map/skip flows; product missing detection in `collect_missing_fks()` not implemented; session typing should be Optional. |
| src/services/enhanced_import_service.py | Reviewed | **Major gaps**: view types other than products not supported; FK scanning mismatches exported field names; cancel/rollback not handled. |
| src/utils/import_export_cli.py | Reviewed | CLI routing present; interactive resolver is implemented; note prompt’s grep expects `add_parser` but implementation uses `subparsers.add_parser(...)` which is fine. |
| src/ui/fk_resolution_dialog.py | Reviewed | Modal behavior correct; cancel UX exists but backend doesn’t enforce keep/rollback semantics. |
| src/ui/import_export_dialog.py | Reviewed | `ImportViewDialog` exists and collects file/mode; import logging path is “user_testing” (temporary). |
| src/ui/main_window.py | Reviewed | “Import View…” menu item present; calls `enhanced_import_service.import_view()` with `UIFKResolver`; refreshes tabs. |
| src/tests/services/test_coordinated_export.py | Reviewed | Strong test coverage; correctly uses `test_db`. |
| src/tests/services/test_denormalized_export.py | Reviewed | Mostly solid; 3 known failures due to decimal formatting expectations. |
| src/tests/services/test_fk_resolver.py | Reviewed | **Broken test isolation**: many tests do not use `test_db`, hitting production DB path. |
| src/tests/services/test_enhanced_import.py | Reviewed | **Broken test isolation** similarly; only covers product view imports. |
| src/tests/utils/test_import_export_cli.py | Reviewed | Covers CLI wiring; appears to use `test_db` appropriately. |

## Architecture Assessment

### Layered Architecture
**Mostly good**: UI calls service APIs, services operate on models/DB. However, `main_window.py` directly orchestrates import execution and logging; consider a small UI service layer wrapper for the “wizard” flow to keep UI thinner.

### Session Management
**Partially compliant** with the `session=None` pattern:
- Export services: good, explicitly accept optional sessions.
- FK resolver / enhanced import: accept `session=None`, but type annotations should be `Optional[Session]` and flows need to ensure consistent transactional behavior, especially for cancel/rollback from UI.

### Protocol-Based Design
**Strong**: `FKResolverCallback` enables CLI and UI to share core resolution logic.

### Separation of Concerns
Exports are cleanly separated (coordinated vs denormalized). Import is currently too narrow (products-only), which is a separation issue from the functional standpoint: it doesn’t yet “own” inventory/purchases import.

## Functional Requirements Verification

| Requirement | Status | Evidence |
|-------------|--------|----------|
| FR-001: Export manifest with checksums | **PASS** | `coordinated_export_service.export_complete()` writes `manifest.json` with per-file `sha256`. |
| FR-002: Entity dependency ordering | **PASS (partial)** | Ordering exists; dependency list may miss product→supplier and recipe self-deps. |
| FR-003: ZIP archive creation | **PASS** | ZIP created; tests validate zip exists. |
| FR-004: Checksum validation | **PASS** | `validate_export()` checks file checksums; supports validating `.zip`. |
| FR-005: Products view export | **PASS** | `export_products_view()` includes context + `_meta`. |
| FR-006: Inventory view export | **PASS** | `export_inventory_view()` emits context + `_meta`. |
| FR-007: Purchases view export | **PASS** | `export_purchases_view()` emits context + `_meta`. |
| FR-008: Context fields for AI | **PASS** | Supplier/ingredient/purchase context fields present in views. |
| FR-009: Editable fields metadata | **PASS** | `_meta.editable_fields` and `_meta.readonly_fields` present. |
| FR-010: export-complete CLI | **PASS** | `import_export_cli.py` routes `export-complete`. |
| FR-011: export-view CLI | **PASS** | `import_export_cli.py` routes `export-view`. |
| FR-012: validate-export CLI | **PASS** | `import_export_cli.py` routes `validate-export`. |
| FR-013: FK resolution CREATE | **PASS** | `fk_resolver_service` supports CREATE; UI/CLI build `Resolution(created_entity=...)`. |
| FR-014: FK resolution MAP | **PASS** | `find_similar_entities()` + MAP wiring exists. |
| FR-015: FK resolution SKIP | **PASS** | SKIP supported; import tracks `skipped_due_to_fk`. |
| FR-016: Fuzzy entity matching | **PASS** | `find_similar_entities()` implemented for supplier/ingredient/product. |
| FR-017: import-view CLI | **PASS (products-only)** | Command exists; import service supports products view. |
| FR-018: --interactive flag | **PASS** | CLI resolver is used when `--interactive` is set. |
| FR-019: --dry-run flag | **PASS (products-only)** | Dry-run implemented by rolling back session after import. |
| FR-020: --skip-on-error flag | **PASS (products-only)** | Skips invalid/missing-FK records and writes skipped log. |
| FR-021: Merge mode | **PASS (products-only)** | Updates editable fields or creates new entities. |
| FR-022: Skip existing mode | **PASS (products-only)** | Adds only when no existing match. |
| FR-023: FK resolution dialog | **PASS (UI) / FAIL (end-to-end)** | UI exists; cancel semantics not honored in services. |
| FR-024: Create entity forms | **PASS** | Supplier/ingredient/product forms exist. |
| FR-025: Map entity search | **PASS** | UI search uses `find_similar_entities()`. |
| FR-026: Import View menu item | **PASS** | `main_window.py` adds “Import View…”. |
| FR-027: Import results dialog | **PASS** | Uses `ImportResultsDialog` with log writing. |

## Work Package Verification

| Work Package | Status | Notes |
|--------------|--------|-------|
| WP01: Coordinated Export Service | **PASS** | Functionality covered by tests; minor spec drift / performance nit. |
| WP02: Denormalized Export Service | **PASS with warnings** | Decimal formatting mismatches; otherwise sound. |
| WP03: Export CLI Commands | **PASS** | Commands exist and are tested. |
| WP04: FK Resolver Service | **PASS with warnings** | Product missing detection in `collect_missing_fks()` incomplete; session typing; UI cancel semantics not supported. |
| WP05: Enhanced Import Service | **FAIL** | Appears products-only; FK field mismatch; no inventory/purchases import. |
| WP06: Import CLI Commands | **PASS (products-only)** | Flags exist; behavior limited by WP05. |
| WP07: FK Resolution Dialog | **PASS (UI) / FAIL (transaction semantics)** | UX present; keep/rollback not enforced. |
| WP08: UI Integration | **PASS (products-only)** | Menu + wizard exist; behavior limited by WP05. |

## Test Coverage Assessment

| Test File | Tests | Coverage | Notes |
|-----------|-------|----------|-------|
| test_coordinated_export.py | N/A | N/A | Passed in batch; good functional coverage. |
| test_denormalized_export.py | N/A | N/A | 3 deterministic failures due to Decimal formatting. |
| test_fk_resolver.py | N/A | N/A | Many tests error due to not using `test_db` fixture (writes production DB path). |
| test_enhanced_import.py | N/A | N/A | Many tests error due to not using `test_db` fixture; coverage is products-only. |
| test_import_export_cli.py | N/A | N/A | Passed in batch; covers routing/flags. |

## Multi-Agent Coordination Assessment

| Agent | Work Packages | Status | Notes |
|-------|---------------|--------|-------|
| Gemini | WP01, WP02, WP03 | **Mostly good** | Export surfaces are coherent; decimal formatting needs alignment. |
| Claude | WP04, WP05, WP06, WP07, WP08 | **Needs follow-up** | Import needs inventory/purchases support and end-to-end cancel semantics. |

## Conclusion

**NEEDS REVISION**

**Recommended next fixes (highest impact):**
1. Extend `enhanced_import_service` to support `inventory` and `purchases` view types (view mapping + record import + FK resolution fields aligned to exporter outputs).
2. Align FK resolution field names between exporters and importers (e.g., `preferred_supplier_name` vs `supplier_name`; product key strategy).
3. Implement UI cancel keep/rollback semantics end-to-end (transaction boundaries + sentinel handling).
4. Fix test isolation: ensure all DB-mutating tests/fixtures use `test_db` (or explicitly set `BAKING_TRACKER_ENV=development` + `reset_config()`), to prevent tests from touching production DB paths.
5. Normalize currency/decimal formatting for exports (`unit_price`, `total_cost`, `last_purchase_price`) to meet the intended contract (likely 2dp).


