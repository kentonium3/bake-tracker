# Implementation Plan: Product Name Differentiation

**Branch**: `023-product-name-differentiation` | **Date**: 2025-12-19 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/023-product-name-differentiation/spec.md`

## Summary

Add `product_name` field (VARCHAR 200, nullable) to the Product table to distinguish variants with identical packaging (e.g., "Lindt 70% Cacao" vs "Lindt 85% Cacao" both 3.5oz bars). Update unique constraint, display_name property, UI form, and import/export handling.

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: SQLAlchemy 2.x, CustomTkinter
**Storage**: SQLite with WAL mode
**Testing**: pytest
**Target Platform**: Desktop (macOS, Windows, Linux)
**Project Type**: Single project
**Performance Goals**: N/A (single-user desktop app)
**Constraints**: Export/reset/import migration per Constitution VI
**Scale/Scope**: Single user, ~15+ existing products

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| I. User-Centric Design | PASS | Optional field reduces user burden; solves real problem (variant tracking) |
| II. Data Integrity & FIFO Accuracy | PASS | Unique constraint prevents unintentional duplicates; migration preserves all data |
| III. Future-Proof Schema, Present-Simple Implementation | PASS | Single nullable field; no premature complexity |
| IV. Test-Driven Development | PASS | Tests required for model, service, import/export |
| V. Layered Architecture Discipline | PASS | Changes in Model, Service, UI layers with proper separation |
| VI. Schema Change Strategy | PASS | Using export/reset/import cycle per constitution |
| VII. Pragmatic Aspiration | PASS | Simple desktop change; does not block web migration |

**Violations**: None

## Project Structure

### Documentation (this feature)

```
kitty-specs/023-product-name-differentiation/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── research/
│   ├── evidence-log.csv # Research findings
│   └── source-register.csv # Source tracking
└── tasks.md             # Phase 2 output (/spec-kitty.tasks)
```

### Source Code (repository root)

```
src/
├── models/
│   └── product.py       # Add product_name column, update display_name, add constraint
├── services/
│   ├── product_service.py    # Update create/update to accept product_name
│   └── import_export_service.py # Add product_name to export/import
├── ui/
│   └── ingredients_tab.py    # Add Product Name field to ProductFormDialog
└── tests/
    ├── test_product_model.py     # New: test product_name behavior
    ├── test_product_service.py   # Update: test product_name CRUD
    └── test_import_export.py     # Update: test product_name export/import
```

**Structure Decision**: Single project structure matches existing codebase.

## Complexity Tracking

*No violations - no entries required.*

## Implementation Phases

### Phase 0: Research (COMPLETE)

- [x] Analyze existing Product model structure
- [x] Identify unique constraint requirements
- [x] Review import/export handling
- [x] Confirm display_name format with user
- [x] Document findings in research.md

**Output**: `research.md`, `data-model.md`, `research/*.csv`

### Phase 1: Design (COMPLETE)

- [x] Define product_name column specification
- [x] Document unique constraint change
- [x] Design display_name property update
- [x] Document export/import schema changes
- [x] Identify all files requiring modification

**Output**: `data-model.md` (complete)

### Phase 2: Tasks (PENDING - run /spec-kitty.tasks)

Work packages to be generated:

1. **Model Layer**: Add product_name column and unique constraint to Product model
2. **Model Layer**: Update display_name property to include product_name
3. **Service Layer**: Update product_service create/update methods
4. **Service Layer**: Update import_export_service for product_name
5. **UI Layer**: Add Product Name field to ProductFormDialog
6. **Testing**: Write/update tests for all changes
7. **Migration**: Execute export/reset/import cycle

## Next Steps

Run `/spec-kitty.tasks` to generate detailed task prompts for implementation.
