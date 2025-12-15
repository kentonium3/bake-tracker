# Implementation Plan: Field Naming Consistency Refactor

**Branch**: `021-field-naming-consistency` | **Date**: 2025-12-15 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/kitty-specs/021-field-naming-consistency/spec.md`

## Summary

Two terminology consistency refactors:

1. **Package fields**: Rename `purchase_unit`/`purchase_quantity` to `package_unit`/`package_unit_quantity` on Product model across all layers (model, services, tests, UI, import/export).

2. **Inventory terminology**: Rename remaining `pantry` references to `inventory` in test files. Note: Model layer (`InventoryItem`) and service layer (`inventory_item_service.py`) are already correctly named; only test function names, variables, and docstrings remain.

This is a cosmetic refactor with no functional changes. User-facing "Pantry" labels in UI are preserved.

**Scope**:
- ~35 files affected by `purchase_unit`/`purchase_quantity` rename
- ~5 test files with `pantry` references needing rename (~40+ occurrences)
- Import/export spec update to v3.4
- ~10 sample JSON files to update

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: SQLAlchemy 2.x, CustomTkinter, pytest
**Storage**: SQLite with WAL mode
**Testing**: pytest with >70% service layer coverage requirement
**Target Platform**: Desktop (macOS, Windows)
**Project Type**: Single desktop application
**Performance Goals**: N/A (cosmetic refactor)
**Constraints**: No SQL migration scripts (Constitution v1.2.0)
**Scale/Scope**: Single user, ~35 files to modify

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. User-Centric Design | PASS | UI labels unchanged; refactor invisible to user |
| II. Data Integrity & FIFO | PASS | Export/import cycle preserves all data with validation |
| III. Future-Proof Schema | PASS | `package_unit` better describes the field's purpose |
| IV. Test-Driven Development | PASS | All existing tests updated and must pass |
| V. Layered Architecture | PASS | Changes follow UI -> Services -> Models flow |
| VI. Schema Change Strategy | PASS | Using export/reset/import workflow per Constitution |
| VII. Pragmatic Aspiration | PASS | Aligns internal code with documented import/export format |

**Post-Phase 1 Re-check**: All gates pass. No complexity violations.

## Project Structure

### Documentation (this feature)

```
kitty-specs/021-field-naming-consistency/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0 research findings
├── data-model.md        # Entity change documentation
├── quickstart.md        # Verification checklist
├── research/            # Evidence audit trail
│   ├── evidence-log.csv
│   └── source-register.csv
└── tasks.md             # Phase 2 output (/spec-kitty.tasks)
```

### Source Code (repository root)

```
src/
├── models/
│   └── product.py           # PRIMARY: Rename fields here
├── services/
│   ├── product_service.py   # Update field references
│   ├── import_export_service.py  # Update import/export logic
│   ├── recipe_service.py    # Update field references
│   └── ...                  # Other services as needed
├── ui/
│   ├── inventory_tab.py     # Update variable names (not labels)
│   ├── ingredients_tab.py   # Update variable names (not labels)
│   └── forms/               # Update field references
└── tests/                   # Update all test references

docs/
└── design/
    └── import_export_specification.md  # Update to v3.4

examples/
└── import/                  # Update sample JSON files

test_data/
└── *.json                   # Update sample JSON files
```

**Structure Decision**: Existing single-project structure maintained. Changes span models, services, UI, tests, and documentation.

## Complexity Tracking

*No Constitution violations requiring justification.*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| (none) | - | - |

## Implementation Strategy

### Phase 1: Preparation

1. **Export existing data** - Backup current database via export
2. **Document affected files** - Generate comprehensive list

### Phase 2: Model Layer

1. **Rename columns in Product model** - `purchase_unit` -> `package_unit`, `purchase_quantity` -> `package_unit_quantity`
2. **Update model docstrings** - Reflect new field names

### Phase 3: Service Layer

1. **Update product_service.py** - All field references
2. **Update import_export_service.py** - Export/import field mapping
3. **Update other services** - Any remaining references

### Phase 4: UI Layer

1. **Update variable names** - Internal code only
2. **Preserve UI labels** - Keep "Pantry" user-facing strings

### Phase 5: Tests

1. **Update test fixtures** - conftest.py, sample data for `purchase_*` -> `package_*`
2. **Update test assertions** - All `purchase_unit`/`purchase_quantity` references
3. **Rename pantry references** - Function names, variables, docstrings (`pantry` -> `inventory`)
4. **Preserve skip reason context** - Historical references to `PantryItem` in skip reasons are acceptable
5. **Run full test suite** - Verify all pass

### Phase 6: Documentation & Data

1. **Update import/export spec** - Bump to v3.4
2. **Update sample JSON files** - New field names
3. **Validate data integrity** - Export/import cycle test

## Verification Checklist

See [quickstart.md](./quickstart.md) for the complete verification checklist.

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Missed references | Comprehensive grep validation before/after |
| Data loss | Full export before changes; validation after import |
| Test failures | Expected; update all test files systematically |
| UI regression | Manual verification of "Pantry" labels preserved |

## Dependencies

- Export functionality must be working (prerequisite)
- No external service dependencies

## Estimated Work Packages

1. **WP-001**: Model layer changes (~1 file)
2. **WP-002**: Service layer changes (~7 files)
3. **WP-003**: UI layer changes (~4 files)
4. **WP-004**: Test updates (~18 files)
5. **WP-005**: Documentation updates (~2 files)
6. **WP-006**: Sample data updates (~10 files)
7. **WP-007**: Verification & validation
