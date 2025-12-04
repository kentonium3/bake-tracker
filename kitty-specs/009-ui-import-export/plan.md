# Implementation Plan: UI Import/Export with v3.0 Schema

**Branch**: `009-ui-import-export` | **Date**: 2025-12-04 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/kitty-specs/009-ui-import-export/spec.md`

## Summary

Add a graphical File menu with Import/Export functionality backed by a v3.0 specification that reflects the current schema (Features 001-008). The service layer will support both Merge and Replace modes to accommodate current use cases (DB population, test data capture) and future needs (programmatic imports, API foundation).

**Key deliverables**:
1. v3.0 import/export specification document (archive v2.0)
2. Refactored import_export_service.py with mode parameter and new entities
3. File menu UI with Import/Export dialogs
4. Updated sample_data.json in v3.0 format

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: CustomTkinter, SQLAlchemy 2.x, tkinter (Menu, filedialog)
**Storage**: SQLite with WAL mode
**Testing**: pytest with >70% service layer coverage
**Target Platform**: Desktop (macOS, Windows, Linux)
**Project Type**: Single desktop application
**Performance Goals**: Export <30s, Import <60s for typical dataset (<1000 records)
**Constraints**: Must use SQLAlchemy transactions for atomic import rollback
**Scale/Scope**: Single user, ~16 exportable entity types, ~1000 records typical

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| **I. Layered Architecture** | PASS | Service layer handles all import/export logic; UI only calls service methods and displays results |
| **II. Build for Today** | PASS | Designing for current desktop use with clean service contracts for future API |
| **III. FIFO Accuracy** | PASS | Import preserves PantryItem acquisition dates for FIFO ordering |
| **IV. User-Centric Design** | PASS | File menu with standard dialogs; user-friendly error messages |
| **V. Test-Driven Development** | PASS | Service methods will have unit tests for both modes |
| **VI. Migration Safety** | PASS | v2.0 compatibility with warnings; no schema changes required |

**Post-Design Re-check**: Required after Phase 1 completes.

## Project Structure

### Documentation (this feature)

```
kitty-specs/009-ui-import-export/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0 research findings
├── data-model.md        # v3.0 entity documentation
├── quickstart.md        # Implementation guide
├── checklists/          # Quality checklists
│   └── requirements.md  # Spec quality checklist
└── tasks/               # Work packages (created by /spec-kitty.tasks)
```

### Source Code (repository root)

```
src/
├── models/              # No changes required (schema stable)
├── services/
│   └── import_export_service.py  # Refactor for v3.0 + mode parameter
├── ui/
│   ├── main_window.py            # Add proper menu bar
│   └── import_export_dialog.py   # NEW: Import/Export dialogs
└── utils/
    └── import_export_cli.py      # Update for v3.0 compatibility

docs/
├── design/
│   └── import_export_specification.md  # Update to v3.0
└── archive/
    └── import_export_specification_v2.md  # Archive current spec

test_data/
└── sample_data.json     # Update to v3.0 format
```

**Structure Decision**: Single project layout; changes span services, UI, and docs layers.

## Complexity Tracking

*No constitution violations requiring justification.*

## Research Summary

### Key Findings

1. **Existing Service**: `import_export_service.py` (1961 lines) has robust export/import with 8 entity-specific functions plus master functions. Returns `ImportResult`/`ExportResult` objects with `get_summary()` methods.

2. **v2.0 to v3.0 Changes Required**:
   - **Deprecated**: `bundles` array (v2.0) -> `compositions` (v3.0)
   - **Added**: `finished_units`, `compositions`, `production_records`
   - **Modified**: `packages` now uses `PackageFinishedGood` not bundles
   - **Modified**: `events` assignments include `status` and `delivered_to` fields

3. **Current Models** (20 total, 16 exportable):
   - Core: Ingredient, Variant, Purchase, PantryItem, UnitConversion
   - Recipe: Recipe, RecipeIngredient, FinishedUnit, FinishedGood, Composition
   - Gift: Package, PackageFinishedGood, Recipient, Event, EventRecipientPackage
   - Production: ProductionRecord (PackageStatus is enum, not separate entity)

4. **UI Pattern**: Main window uses CTkFrame menu bar with buttons. For proper File menu, can use tkinter Menu widget with CTkToplevel dialogs.

5. **File Dialogs**: tkinter provides `filedialog.askopenfilename()` and `filedialog.asksaveasfilename()` which work with CustomTkinter.

### Import Mode Decision

| Mode | Behavior | Use Case |
|------|----------|----------|
| **Merge** | Add new records, skip duplicates by primary key | Adding ingredients/variants from external sources |
| **Replace** | Clear all data, then import | Fresh start, restore from backup |

User selects mode at import time via dialog.

### Entity Dependency Order (v3.0)

Import must follow this order for referential integrity:

1. `unit_conversions` - No dependencies
2. `ingredients` - No dependencies
3. `variants` - Requires: ingredients (via ingredient_slug)
4. `purchases` - Requires: variants
5. `pantry_items` - Requires: variants
6. `recipes` - No direct dependency (recipe_ingredients embedded)
7. `finished_units` - Requires: recipes (via recipe_id)
8. `finished_goods` - Requires: recipes (via recipe_id)
9. `compositions` - Requires: finished_units, finished_goods
10. `packages` - No direct dependency
11. `package_finished_goods` - Requires: packages, finished_goods
12. `recipients` - No dependencies
13. `events` - No direct dependency
14. `event_recipient_packages` - Requires: events, recipients, packages
15. `production_records` - Requires: events, recipes

## Implementation Phases

### Phase 1: Documentation & Specification (P1)
- Archive v2.0 spec to `docs/archive/`
- Create v3.0 spec with all 15 entities
- Document JSON examples for each entity
- Document validation rules and constraints

### Phase 2: Service Layer Refactoring (P1)
- Add `mode` parameter to `import_all_from_json()`: `"merge"` or `"replace"`
- Add export/import for new entities: `finished_units`, `compositions`, `production_records`
- Update `packages` export/import for `PackageFinishedGood` relationship
- Update `events` export/import for status fields
- Add v2.0 compatibility layer with warnings
- Unit tests for both modes

### Phase 3: UI Implementation (P1)
- Add proper tkinter Menu bar to main_window.py
- Create `ImportExportDialog` class (CTkToplevel)
- Export dialog: file save picker, progress, confirmation
- Import dialog: file open picker, mode selection (Merge/Replace), progress, summary
- Error handling with user-friendly messages

### Phase 4: Sample Data & Testing (P2)
- Update `test_data/sample_data.json` to v3.0 format
- Include all entity types with realistic test data
- Round-trip test: export -> clear -> import -> verify
- Manual testing of UI workflows

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Large import fails mid-way | SQLAlchemy transaction rollback on any error |
| v2.0 files silently fail | Detect version, show warnings, best-effort mapping |
| User confusion about modes | Clear dialog labels with descriptions |
| Performance with large datasets | Progress indication, consider chunked commits |

## Open Questions

None - all planning questions resolved during discovery.

## Next Steps

Run `/spec-kitty.tasks` to generate work packages from this plan.
