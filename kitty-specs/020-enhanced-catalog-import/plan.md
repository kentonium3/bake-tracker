# Implementation Plan: Enhanced Catalog Import

**Branch**: `020-enhanced-catalog-import` | **Date**: 2025-12-14 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/020-enhanced-catalog-import/spec.md`

## Summary

Create a separate catalog import pathway that safely adds/augments ingredient, product, and recipe reference data without affecting transactional user data. The feature provides:
- Service layer with entity-specific functions (`import_ingredients`, `import_products`, `import_recipes`) plus coordinator
- CLI command: `python -m src.utils.import_catalog`
- UI: "Import Catalog..." menu item with CatalogImportDialog
- Dry-run preview mode
- Partial success with actionable error messages

This preserves the existing unified import/export for development workflows (Constitution v1.2.0 compliance).

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: CustomTkinter (UI), SQLAlchemy 2.x (ORM), pytest (testing)
**Storage**: SQLite with WAL mode
**Testing**: pytest with >70% service layer coverage required
**Target Platform**: Desktop (macOS, Windows, Linux)
**Project Type**: Single desktop application
**Performance Goals**: Import 160 ingredients in under 30 seconds
**Constraints**: Must not affect existing transactional data; must preserve unified import/export
**Scale/Scope**: Single user, 160+ ingredient catalog, future recipe collections

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. User-Centric Design | PASS | Feature solves real problem: 160-ingredient catalog waiting for import |
| II. Data Integrity & FIFO | PASS | Import is additive only; no modification of existing transactional data |
| III. Future-Proof Schema | PASS | Uses existing schema; catalog format enables future web catalog sharing |
| IV. Test-Driven Development | REQUIRED | Service layer tests required before feature complete |
| V. Layered Architecture | PASS | CLI in utils, service in services, UI in ui - follows existing pattern |
| VI. Schema Change Strategy | N/A | No schema changes; uses existing models |
| VII. Pragmatic Aspiration | PASS | Enables web migration path (shared catalogs); clean service layer |

**Web Migration Cost**: LOW - Service layer is UI-independent, can become API endpoints

## Project Structure

### Documentation (this feature)

```
kitty-specs/020-enhanced-catalog-import/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0 output - architectural decisions
├── data-model.md        # Phase 1 output - data structures and contracts
├── quickstart.md        # Phase 1 output - usage guide
├── contracts/           # Phase 1 output - API contracts (if applicable)
├── checklists/          # Quality checklists
│   └── requirements.md  # Spec validation checklist
└── tasks.md             # Phase 2 output (created by /spec-kitty.tasks)
```

### Source Code (repository root)

```
src/
├── services/
│   ├── catalog_import_service.py    # NEW: Catalog import business logic
│   └── import_export_service.py     # EXISTING: Unified import/export (unchanged)
├── utils/
│   ├── import_catalog.py            # NEW: CLI entry point
│   └── import_export_cli.py         # EXISTING: Unified CLI (unchanged)
├── ui/
│   ├── catalog_import_dialog.py     # NEW: UI dialog for catalog import
│   ├── import_export_dialog.py      # EXISTING: Unified dialogs (unchanged)
│   └── main_window.py               # MODIFIED: Add "Import Catalog..." menu item
└── tests/
    └── test_catalog_import_service.py  # NEW: Service layer tests
```

**Structure Decision**: Single project structure (Option 1) - desktop application with existing layered architecture.

## Complexity Tracking

*No constitution violations to justify - feature follows all principles.*

---

## Phase 0: Research Summary

See [research.md](research.md) for full details.

### Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Service architecture | Module-level functions | Match existing `import_export_service.py` |
| File organization | Separate CLI + service | Match existing pattern |
| Validation location | Inline in service | Simpler; import-specific |
| Result pattern | Follow `ImportResult` | Proven pattern with per-entity tracking |
| Session management | Optional `session=None` | Enable transactional composition |
| Dry-run | Validate then rollback | Full preview accuracy |
| Partial success | Commit valid, report failures | User decision during discovery |

### Format Detection

```python
if "catalog_version" in data:
    # Catalog import format v1.0 -> catalog_import_service
elif "version" in data:
    # Unified format v3.x -> route to import_export_service
else:
    raise CatalogImportError("Unrecognized format")
```

---

## Phase 1: Design Summary

See [data-model.md](data-model.md) for full contracts.

### New Files

1. **`src/services/catalog_import_service.py`**
   - `import_catalog()` - coordinator
   - `import_ingredients()` - entity-specific
   - `import_products()` - entity-specific
   - `import_recipes()` - entity-specific
   - `validate_catalog_file()` - format detection
   - `CatalogImportResult` class

2. **`src/utils/import_catalog.py`**
   - CLI entry point with argparse
   - Options: `--mode`, `--entity`, `--dry-run`, `--verbose`

3. **`src/ui/catalog_import_dialog.py`**
   - `CatalogImportDialog` - modal dialog
   - File picker, mode radio, entity checkboxes, dry-run checkbox

4. **`src/tests/test_catalog_import_service.py`**
   - Unit tests for all service functions
   - Coverage: happy path, edge cases, error conditions

### Modified Files

1. **`src/ui/main_window.py`**
   - Add "Import Catalog..." menu item after separator in File menu
   - Wire to open `CatalogImportDialog`

### Entity Processing Order

Import must process in dependency order:
1. **Ingredients** (no dependencies)
2. **Products** (depends on ingredients via `ingredient_slug`)
3. **Recipes** (depends on ingredients via `ingredient_slug`, and on other recipes via `recipe_name` components)

---

## Implementation Strategy

### Work Packages (Preview)

Based on spec analysis, expect these work packages:

1. **WP01: Service Layer Foundation**
   - Create `CatalogImportResult` class
   - Create `import_ingredients()` function with ADD_ONLY mode
   - Unit tests for ingredient import

2. **WP02: Product Import**
   - Create `import_products()` function
   - FK validation for `ingredient_slug`
   - Unit tests

3. **WP03: Recipe Import**
   - Create `import_recipes()` function
   - FK validation for ingredients and components
   - Circular reference detection
   - Unit tests

4. **WP04: AUGMENT Mode**
   - Add AUGMENT mode to ingredients
   - Add AUGMENT mode to products
   - Reject AUGMENT for recipes with error
   - Unit tests

5. **WP05: Coordinator and Dry-Run**
   - Create `import_catalog()` coordinator
   - Implement dry-run mode
   - Create `validate_catalog_file()`
   - Unit tests

6. **WP06: CLI**
   - Create `src/utils/import_catalog.py`
   - Argparse setup with all options
   - Exit codes
   - Integration tests

7. **WP07: UI Dialog**
   - Create `CatalogImportDialog`
   - Wire to File menu
   - Results display
   - Manual testing

8. **WP08: Integration and Polish**
   - End-to-end testing
   - Error message refinement
   - Documentation updates

---

## Testing Strategy

### Unit Tests (Required)

- `test_import_ingredients_add_mode` - new ingredients created
- `test_import_ingredients_skip_existing` - existing slugs skipped
- `test_import_ingredients_augment_mode` - null fields updated
- `test_import_ingredients_augment_preserves_existing` - non-null fields unchanged
- `test_import_products_add_mode` - new products created
- `test_import_products_fk_validation` - missing ingredient fails
- `test_import_recipes_add_mode` - new recipes created
- `test_import_recipes_fk_validation` - missing ingredient fails
- `test_import_recipes_collision` - existing name rejected with detail
- `test_import_recipes_augment_rejected` - AUGMENT mode returns error
- `test_import_recipes_circular_detection` - circular refs detected
- `test_dry_run_no_commit` - database unchanged after dry-run
- `test_partial_success` - valid records committed, failures reported

### Integration Tests

- `test_cli_add_mode` - full CLI flow
- `test_cli_dry_run` - preview output
- `test_cli_verbose` - detailed output
- `test_format_detection` - catalog vs unified routing

---

## Dependencies

### Prerequisites

- Feature 009: File menu structure (exists)
- Feature 019: 4-field density format (complete)
- Existing `import_export_service.py` patterns (exists)

### Blocked By

None - all prerequisites met.

### Blocking

None - feature is standalone addition.

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Recipe `name` vs `slug` confusion | Medium | Medium | Use `name` consistently (matches model) |
| Large import performance | Low | Medium | Batch processing if >1000 records |
| Session detachment bugs | Medium | High | Follow `session=None` pattern per CLAUDE.md |
| Partial success data inconsistency | Low | Medium | Single transaction per entity type |

---

## References

- [Feature Specification](spec.md)
- [Research Decisions](research.md)
- [Data Model and Contracts](data-model.md)
- [Quickstart Guide](quickstart.md)
- [Enhanced Data Import Proposal](../../../docs/enhanced_data_import.md)
- [Constitution v1.2.0](../../../.kittify/memory/constitution.md)
