# Research: CLI Import/Export Parity

**Feature**: 054-cli-import-export-parity
**Date**: 2026-01-15
**Status**: Complete

## Research Questions

### Q1: What is the current CLI command structure?

**Decision**: Follow existing argparse subparsers pattern in `src/utils/import_export_cli.py`

**Findings**:
- CLI uses argparse with subparsers for command organization
- Each command is a separate subparser with its own arguments
- Commands follow naming pattern: `export-[entity]`, `import-[type]`
- Exit codes: 0 for success, 1 for failure

**Existing Commands**:
| Command | Service Called | Purpose |
|---------|---------------|---------|
| export | export_all_to_json() | Legacy v3.2 format export |
| export-[entity] | export_*_to_json() | Entity-specific exports |
| import | import_all_from_json_v4() | Legacy v3.2 format import |
| export-complete | coordinated_export_service.export_complete() | 16-entity backup |
| export-view | denormalized_export_service.export_*_view() | Context-rich exports |
| validate-export | coordinated_export_service.validate_export() | Checksum validation |
| import-view | enhanced_import_service.import_view() | Context-rich imports |

**Rationale**: Reuse existing patterns ensures consistency and reduces learning curve.

---

### Q2: What service functions exist for backup/restore?

**Decision**: Use `coordinated_export_service` for backup operations

**Findings**:

**Export Function**:
```python
def export_complete(
    output_path: str,
    create_zip: bool = False,
    session: Optional[Session] = None,
) -> ExportManifest
```

**Import Function**:
```python
def import_complete(
    import_path: str,
    session: Optional[Session] = None,
) -> Dict  # {successful, files_imported, entity_counts, errors}
```

**Validation Function**:
```python
def validate_export(backup_dir: str) -> Dict  # Checksum validation results
```

**16 Entities in Dependency Order**:
1. suppliers (order 1)
2. ingredients (order 2)
3. products (order 3)
4. recipes (order 4)
5. purchases (order 5)
6. inventory_items (order 6)
7. material_categories (order 7)
8. material_subcategories (order 8)
9. materials (order 9)
10. material_products (order 10)
11. material_units (order 11)
12. material_purchases (order 12)
13. finished_goods (order 13)
14. events (order 14)
15. production_runs (order 15)
16. inventory_depletions (order 16)

**Manifest Structure**:
- version: "1.0"
- export_date: ISO timestamp
- source: app name/version
- files: array of {filename, entity_type, record_count, sha256, dependencies, import_order}

---

### Q3: What service functions exist for context-rich (aug) exports?

**Decision**: Use `denormalized_export_service` for aug operations

**Findings**:

**File Naming**: `aug_` prefix (confirmed F053)

**Export Functions**:
```python
def export_products_context_rich(output_path, session) -> ExportResult
def export_inventory_context_rich(output_path, session) -> ExportResult
def export_purchases_context_rich(output_path, session) -> ExportResult
def export_ingredients_context_rich(output_path, session) -> ExportResult
def export_materials_context_rich(output_path, session) -> ExportResult
def export_recipes_context_rich(output_path, session) -> ExportResult
def export_material_products_context_rich(output_path, session) -> ExportResult
def export_finished_units_context_rich(output_path, session) -> ExportResult
def export_finished_goods_context_rich(output_path, session) -> ExportResult
```

**Convenience Function**:
```python
def export_all_context_rich(output_dir, session) -> Dict[str, ExportResult]
```

**Aug File Structure**:
```json
{
  "version": "1.0",
  "export_type": "entity_type",
  "export_date": "ISO timestamp",
  "_meta": {
    "editable_fields": ["field1", "field2"],
    "readonly_fields": ["id", "slug", "computed_field"]
  },
  "records": [...]
}
```

---

### Q4: What service functions exist for catalog operations?

**Decision**: Use `catalog_import_service` for catalog operations

**Findings**:

**Main Import Function**:
```python
def import_catalog(
    file_path: str,
    mode: str = "add",  # "add" or "augment"
    entities: Optional[List[str]] = None,
    dry_run: bool = False,
    session: Optional[Session] = None,
) -> CatalogImportResult
```

**Catalog Entity Types** (7):
1. ingredients
2. products
3. recipes
4. materials
5. material_products
6. suppliers (F050)
7. finished_goods

**Import Modes**:
- ADD_ONLY ("add"): Create new, skip existing
- AUGMENT ("augment"): Update null fields on existing, add new

**No existing catalog-export function** - need to aggregate from entity-specific exports

---

### Q5: What is the CLIFKResolver pattern?

**Decision**: Reuse CLIFKResolver for interactive FK resolution in new import commands

**Findings**:

**Location**: Lines 344-537 in `import_export_cli.py`

**Pattern**:
```python
class CLIFKResolver:
    def resolve(self, missing: MissingFK) -> Resolution:
        # Display options: [C] Create, [M] Map, [S] Skip
        # User input loop
        # Returns Resolution with choice and data
```

**Resolution Choices**:
- CREATE: Create missing entity with provided data
- MAP: Map to existing entity by fuzzy search
- SKIP: Skip records referencing this missing FK

**Service Integration**:
- `find_similar_entities(entity_type, missing_value, limit=5)` - Fuzzy search
- `resolve_missing_fks(missing_fks, resolver, session)` - Apply resolutions

---

### Q6: What result classes are used?

**Decision**: All CLI commands should return appropriate result objects with `.get_summary()` method

**Findings**:

**ExportResult** (basic exports):
- file_path, record_count, success, error, entity_counts
- `.get_summary()` returns formatted summary

**ImportResult** (basic imports):
- total_records, successful, skipped, failed, errors, warnings, entity_counts
- `.get_summary()` returns formatted summary with per-entity breakdown

**EnhancedImportResult** (context-rich imports):
- base_result: ImportResult
- resolutions: List[Resolution]
- created_entities, mapped_entities, skipped_due_to_fk
- `.get_summary()` includes FK resolution summary

**CatalogImportResult** (catalog imports):
- entity_counts: Dict[str, EntityImportCounts]
- errors, warnings, dry_run, mode
- `.get_summary()`, `.get_detailed_report()`

**ExportManifest** (coordinated backup):
- version, export_date, source, files: List[FileEntry]
- `.to_dict()` for JSON serialization

---

## Implementation Approach

### Command Organization

**New Command Groups**:

1. **Backup/Restore** (wraps coordinated_export_service):
   - `backup` -> export_complete()
   - `restore` -> import_complete()
   - `backup-list` -> list directories with manifest.json
   - `backup-validate` -> validate_export()

2. **Catalog** (wraps catalog_import_service + aggregated exports):
   - `catalog-export` -> aggregate entity exports
   - `catalog-import` -> import_catalog()
   - `catalog-validate` -> schema validation

3. **Aug** (wraps denormalized_export_service + enhanced_import_service):
   - `aug-export` -> export_*_context_rich()
   - `aug-import` -> import_context_rich_export()
   - `aug-validate` -> format detection + schema check

4. **Entity-Specific** (wraps individual service functions):
   - `export-materials` -> export_materials_to_json()
   - `export-material-products` -> export_material_products_to_json()
   - `export-material-categories` -> export_material_categories_to_json()
   - `export-material-subcategories` -> export_material_subcategories_to_json()
   - `export-suppliers` -> export_suppliers_to_json()
   - `export-purchases` -> export_purchases_to_json()

### Service Function Mapping

| CLI Command | Service Function | Result Type |
|-------------|------------------|-------------|
| backup | coordinated_export_service.export_complete() | ExportManifest |
| restore | coordinated_export_service.import_complete() | Dict |
| backup-validate | coordinated_export_service.validate_export() | Dict |
| catalog-import | catalog_import_service.import_catalog() | CatalogImportResult |
| aug-export | denormalized_export_service.export_*_context_rich() | ExportResult |
| aug-import | enhanced_import_service.import_context_rich_export() | EnhancedImportResult |

### Argument Patterns

**Standard patterns to follow**:
- `-o, --output`: Output directory/file
- `-m, --mode`: Import mode (add/augment/replace)
- `-t, --type`: Entity type selection
- `-i, --interactive`: Enable FK resolution prompts
- `-s, --skip-on-error`: Continue on validation errors
- `-d, --dry-run`: Preview mode
- `-z, --zip`: Create ZIP archive
- `--entities`: Comma-separated entity list

---

## Alternatives Considered

### Alt 1: Create new CLI module vs extend existing

**Rejected**: Extend existing `import_export_cli.py`

**Rationale**: Keep all import/export commands in one place for discoverability. The module is already ~800 lines; adding ~400 more is manageable.

### Alt 2: JSON output mode for all commands

**Rejected**: Keep human-readable output as default

**Rationale**: Existing commands output human-readable summaries. Add `--json` flag only where explicitly needed (backup, aug commands for AI workflows).

### Alt 3: Separate backup-list from main CLI

**Rejected**: Keep as subparser command

**Rationale**: Users expect `python -m src.utils.import_export_cli backup-list` pattern. Separate script breaks discoverability.
