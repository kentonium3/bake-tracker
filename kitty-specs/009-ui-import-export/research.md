# Research: UI Import/Export with v3.0 Schema

**Feature**: 009-ui-import-export
**Date**: 2025-12-04

## Research Questions Addressed

### 1. What is the current state of import/export functionality?

**Decision**: Existing service is robust and extensible
**Rationale**: `import_export_service.py` (1961 lines) already provides:
- `ImportResult` and `ExportResult` classes with `get_summary()` methods
- Entity-specific export/import functions (8 each)
- Master functions `export_all_to_json()` and `import_all_from_json()`
- Duplicate detection and skip logic
- Foreign key validation

**Alternatives Considered**:
- Rewrite from scratch: Rejected - existing code is well-structured
- Use external library: Rejected - custom format requirements

### 2. What schema changes occurred since v2.0?

**Decision**: Update to v3.0 format with backward compatibility
**Rationale**: Schema changes from Features 006-008 require format updates:

| v2.0 Entity | v3.0 Entity | Change Type |
|-------------|-------------|-------------|
| `bundles` | `compositions` | Renamed/restructured |
| - | `finished_units` | New entity |
| - | `production_records` | New entity (Feature 008) |
| `packages.bundles[]` | `package_finished_goods` | Relationship changed |
| `events.assignments[]` | `event_recipient_packages` | Added status fields |

**Alternatives Considered**:
- Breaking change (no v2.0 support): Rejected - user has existing backups
- Automatic migration service: Rejected - out of scope per spec

### 3. How should import modes work?

**Decision**: User choice at import time: Merge or Replace
**Rationale**: Multiple use cases require flexibility:
- **Merge**: Add new ingredients from external sources without clearing existing data
- **Replace**: Full restore from backup, testing fresh database states

**Implementation**:
```python
def import_all_from_json(file_path: str, mode: str = "merge") -> ImportResult:
    """
    mode: "merge" - skip duplicates, preserve existing data
    mode: "replace" - clear all tables, then import
    """
```

**Alternatives Considered**:
- Merge only: Rejected - restore from backup is a primary use case
- Replace only: Rejected - adding data incrementally is needed for testing

### 4. How should the UI menu be implemented?

**Decision**: Use tkinter Menu widget with CTkToplevel dialogs
**Rationale**:
- tkinter Menu provides standard OS menu bar appearance
- Works seamlessly with CustomTkinter
- File dialogs (`filedialog.askopenfilename`, `filedialog.asksaveasfilename`) are battle-tested

**Pattern**:
```python
# In main_window.py
self.menu_bar = tk.Menu(self)
self.config(menu=self.menu_bar)

file_menu = tk.Menu(self.menu_bar, tearoff=0)
file_menu.add_command(label="Import Data...", command=self._show_import_dialog)
file_menu.add_command(label="Export Data...", command=self._show_export_dialog)
file_menu.add_separator()
file_menu.add_command(label="Exit", command=self._on_exit)
self.menu_bar.add_cascade(label="File", menu=file_menu)
```

**Alternatives Considered**:
- CTkFrame button menu (current): Rejected - not standard UX for File operations
- Custom dropdown: Rejected - unnecessary complexity

### 5. What entities should be exportable in v3.0?

**Decision**: 15 entity types in dependency order
**Rationale**: All user data should be exportable. Supporting models (aliases, crosswalks) are internal.

**Exportable Entities**:
1. `unit_conversions` - Unit conversion factors
2. `ingredients` - Generic ingredient definitions
3. `variants` - Brand-specific variants
4. `purchases` - Purchase history
5. `pantry_items` - Current inventory with FIFO lots
6. `recipes` - Recipe definitions (includes `recipe_ingredients` embedded)
7. `finished_units` - Yield definitions for recipes
8. `finished_goods` - Composite finished products
9. `compositions` - FinishedUnit -> FinishedGood relationships
10. `packages` - Gift package definitions
11. `package_finished_goods` - Package contents (embedded or separate)
12. `recipients` - Gift recipients
13. `events` - Holiday/occasion events
14. `event_recipient_packages` - Package assignments with status
15. `production_records` - Batch production with FIFO cost capture

**Not Exported**:
- `IngredientAlias` - Internal supporting model
- `IngredientCrosswalk` - Internal migration model
- `VariantPackaging` - Internal supporting model
- `IngredientLegacy` - Migration compatibility only
- `InventorySnapshot` - Historical snapshots (future consideration)

## Existing Code References

### Service Layer
- `src/services/import_export_service.py:552-890` - `export_all_to_json()`
- `src/services/import_export_service.py:1796-1960` - `import_all_from_json()`
- Result classes: `ImportResult`, `ExportResult` with `get_summary()`

### Models
- `src/models/__init__.py` - Canonical export list
- `src/models/production_record.py` - New Feature 008 model
- `src/models/package_status.py` - PackageStatus enum

### UI
- `src/ui/main_window.py` - Current menu bar implementation
- `src/ui/migration_wizard_dialog.py` - Dialog pattern to follow

### Documentation
- `docs/design/import_export_specification.md` - Current v2.0 spec
- `test_data/sample_data.json` - Current v2.0 format test data

## Test Strategy

### Unit Tests
- `test_export_all_to_json()` - Verify all entities exported
- `test_import_merge_mode()` - Verify duplicates skipped
- `test_import_replace_mode()` - Verify data cleared then imported
- `test_import_v2_compatibility()` - Verify warnings and best-effort mapping
- `test_round_trip()` - Export -> Import -> Verify data integrity

### Integration Tests
- Full workflow: Export from populated DB -> Clear -> Import -> Verify
- v2.0 file import with deprecation warnings
- Large dataset performance (<60s for 1000 records)

### Manual Tests
- File menu appears and functions
- Export creates valid JSON file
- Import shows mode selection
- Progress indication during operations
- Error messages are user-friendly
