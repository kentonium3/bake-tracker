# Research: Enhanced Export/Import System

**Feature**: 030-enhanced-export-import
**Date**: 2025-12-25

## Executive Summary

Research into the existing codebase reveals well-established patterns for import/export operations that the enhanced system should build upon. The codebase has two distinct import services with different philosophies that inform our architecture.

## Key Findings

### 1. Existing Service Architecture

**`src/services/import_export_service.py`** (~1100+ lines)
- Monolithic service with per-entity export functions
- `export_all_to_json()` creates single unified file
- `import_all_from_json_v3()` handles unified import
- `ImportResult` / `ExportResult` classes for tracking
- No FK resolution - relies on exact ID matching

**`src/services/catalog_import_service.py`** (~1200 lines)
- Cleaner, newer design with structured patterns
- `ImportMode` enum: `ADD_ONLY` and `AUGMENT`
- `CatalogImportResult` with structured `ImportError` objects
- **FK resolution via slug**: Uses `ingredient_slug` field to resolve FKs
- **Dependency ordering**: Imports in order (ingredients → products → recipes)
- **Session pattern**: `session=None` with internal `_impl` functions

**Decision**: Use `catalog_import_service.py` patterns as foundation for new services.

### 2. Existing UI Patterns

**`src/ui/import_export_dialog.py`**
- `ImportDialog`: Modal file chooser with mode selection
- `ImportResultsDialog`: Scrollable results with copy/log functionality
- Modal behavior via `transient()` and `grab_set()`
- Logging to `docs/user_testing/import_{timestamp}.log`

**Decision**: Follow existing dialog patterns for FK resolution wizard.

### 3. Existing CLI Patterns

**`src/utils/import_export_cli.py`**
- Uses `argparse` (not click/typer)
- Per-entity export commands via subcommands
- `--mode` flag for merge/replace modes
- Initializes database before operations
- Returns exit codes (0 success, 1 failure)

**Decision**: Extend existing CLI with new commands and flags.

### 4. Session Management (CRITICAL)

Per CLAUDE.md, nested `session_scope()` calls cause detached object issues.

**The Pattern**:
```python
def service_function(..., session=None):
    if session is not None:
        return _service_function_impl(..., session)
    with session_scope() as sess:
        return _service_function_impl(..., sess)
```

**Decision**: All new services MUST use this pattern.

### 5. Entity Relationships

From `src/models/`:
- **Supplier**: `id`, `name`, `city`, `state`, `zip` (unique: name)
- **Ingredient**: `id`, `slug`, `display_name`, `category` (unique: slug)
- **Product**: `id`, `ingredient_id` (FK), `brand`, `package_unit`, etc. (no single unique key)
- **Purchase**: `id`, `product_id` (FK), `supplier_id` (FK), `purchase_date`, `quantity`, `unit_cost`
- **InventoryItem**: `id`, `product_id` (FK), `quantity`, etc.

**FK Resolution Strategy**:
| Entity | Resolution Key | Unique? |
|--------|---------------|---------|
| Supplier | name | Yes |
| Ingredient | slug | Yes |
| Product | ingredient_slug + brand + package_unit + package_unit_quantity | Composite |

## Architecture Decisions

### Export Services (Gemini Work)

**New File: `src/services/coordinated_export_service.py`**
- `export_complete(output_dir, zip=False)` → Creates entity files + manifest
- `ExportManifest` dataclass with checksums, record counts, dependencies
- Per-entity export with FK resolution fields (both id and slug/name)

**New File: `src/services/denormalized_export_service.py`**
- `export_products_view(output_path)` → Products with ingredient/supplier context
- `export_inventory_view(output_path)` → Inventory with product/purchase context
- `export_purchases_view(output_path)` → Purchases with product/supplier context
- Include `_editable_fields` and `_readonly_fields` metadata in output

### Import Services (Claude Work)

**New File: `src/services/enhanced_import_service.py`**
- `import_view(file_path, mode, resolver=None)` → Core import logic
- Modes: `merge` (update+add), `skip_existing` (add only)
- Integrates with FK resolver for missing references
- `dry_run` support via session rollback
- `skip_on_error` mode with logging

**New File: `src/services/fk_resolver_service.py`**
- `FKResolver` class with pluggable resolution strategies
- `ResolutionChoice`: CREATE, MAP, SKIP enum
- `MissingFK` dataclass: entity_type, missing_value, affected_records
- `resolve_missing_fks(missing_list, resolver_callback)` → Core logic
- Shared by CLI (interactive prompt) and UI (dialog)

### CLI Changes

**Extend `src/utils/import_export_cli.py`**:
- New commands: `export-complete`, `export-view`, `import-view`, `validate-export`
- New flags: `--interactive`, `--skip-on-error`, `--dry-run`, `--output`, `--zip`

### UI Changes

**New File: `src/ui/fk_resolution_dialog.py`**
- `FKResolutionDialog`: Shows missing FK, options (create/map/skip)
- Fuzzy search for "map to existing" option
- Entity creation form for "create new" option

**Modify `src/ui/main_window.py`**:
- Add File > Import > Import View menu item
- Wire to new import dialog flow

## Parallel Work Split

| Component | Owner | Files |
|-----------|-------|-------|
| Coordinated Export Service | Gemini | `src/services/coordinated_export_service.py` |
| Denormalized Export Service | Gemini | `src/services/denormalized_export_service.py` |
| Export CLI Commands | Gemini | `src/utils/import_export_cli.py` (export parts) |
| Export Tests | Gemini | `src/tests/services/test_coordinated_export.py`, `test_denormalized_export.py` |
| Enhanced Import Service | Claude | `src/services/enhanced_import_service.py` |
| FK Resolver Service | Claude | `src/services/fk_resolver_service.py` |
| Import CLI Commands | Claude | `src/utils/import_export_cli.py` (import parts) |
| FK Resolution Dialog | Claude | `src/ui/fk_resolution_dialog.py` |
| Import UI Integration | Claude | `src/ui/main_window.py`, `src/ui/import_export_dialog.py` |
| Import Tests | Claude | `src/tests/services/test_enhanced_import.py`, `test_fk_resolver.py` |

## Open Questions / Risks

1. **Product uniqueness**: Products lack a single unique key. The composite key (ingredient_slug + brand + package_unit + package_unit_quantity) may have edge cases. Mitigation: Warn on ambiguous matches.

2. **Large file performance**: No streaming JSON support in existing code. For >10,000 records, may need `ijson` or chunked processing. Mitigation: Defer to post-MVP optimization.

3. **Transaction scope**: Interactive FK resolution across many entities needs careful session management. Each resolution cycle should be atomic. Mitigation: Batch resolutions within single session.

## References

- `src/services/catalog_import_service.py`: Best patterns for import
- `src/services/import_export_service.py`: Entity relationships and export structure
- `src/ui/import_export_dialog.py`: Dialog patterns
- `src/utils/import_export_cli.py`: CLI patterns
- `docs/design/F030_enhanced_export_import.md`: Original design document (reference only)
