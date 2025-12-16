# Implementation Plan: Unit Reference Table & UI Dropdowns

**Branch**: `022-unit-reference-table` | **Date**: 2025-12-16 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/kitty-specs/022-unit-reference-table/spec.md`

## Summary

Create a database-backed unit reference table to replace free-form unit entry with constrained dropdown selection in the UI. The reference table stores all 27 valid measurement units with metadata (code, display name, symbol, category, optional UN/CEFACT code). UI forms will use CTkComboBox with category headers as separators for grouped selection. The approach is simple: seed data on startup, replace text entries with dropdowns in existing forms, and validate at the UI layer.

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: SQLAlchemy 2.x (ORM), CustomTkinter (UI)
**Storage**: SQLite with WAL mode
**Testing**: pytest
**Target Platform**: Desktop (Windows/macOS/Linux)
**Project Type**: Single desktop application
**Performance Goals**: Dropdown selection in <3 seconds (per SC-001)
**Constraints**: Must preserve all existing data, no breaking changes to import/export
**Scale/Scope**: Single user, 27 units total (4 weight, 9 volume, 4 count, 10 package)

### Planning Decisions

1. **UI Component**: CTkComboBox with category headers as non-selectable separators (e.g., "-- Weight --", "oz", "lb"). Simple approach, can revisit based on user testing.

2. **Seed Data Strategy**: Seed units table in `init_database()` function using existing `constants.py` definitions. Idempotent seeding (check if table empty before inserting).

3. **Dropdown Context Filtering**:
   - Product package_unit: ALL_UNITS
   - Ingredient density_volume_unit: VOLUME_UNITS only
   - Ingredient density_weight_unit: WEIGHT_UNITS only
   - RecipeIngredient unit: WEIGHT + VOLUME + COUNT (no PACKAGE)

4. **Schema Compatibility**: Import/export continues using constants.py validation (TD-002 already standardized). Database table is for UI dropdowns only.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. User-Centric Design | PASS | Dropdowns prevent typos, faster than typing |
| II. Data Integrity & FIFO | PASS | No changes to FIFO logic, units unchanged |
| III. Future-Proof Schema | PASS | UN/CEFACT code field is nullable for future |
| IV. Test-Driven Development | PASS | Will add tests for Unit model and seeding |
| V. Layered Architecture | PASS | Model in models/, UI changes in ui/forms/ |
| VI. Schema Change Strategy | PASS | New table, no migration needed |
| VII. Pragmatic Aspiration | PASS | Simple approach, web-compatible (reference data) |

**Desktop Phase Gates:**
- Does this design block web deployment? **NO** - Reference table pattern is standard
- Is the service layer UI-independent? **YES** - Unit model has no UI dependencies
- Are business rules in services, not UI? **YES** - Validation uses constants.py
- Web migration cost: **LOW** - Reference data migrates trivially

## Project Structure

### Documentation (this feature)

```
kitty-specs/022-unit-reference-table/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
└── tasks.md             # Phase 2 output (from /spec-kitty.tasks)
```

### Source Code (repository root)

```
src/
├── models/
│   ├── unit.py                    # NEW: Unit reference model
│   └── __init__.py                # Update to export Unit
├── services/
│   ├── database.py                # Modify: Add unit seeding to init_database()
│   └── unit_service.py            # NEW: Helper to get units by category
├── ui/
│   ├── ingredients_tab.py         # Modify: Product package_unit dropdown (line ~1412)
│   └── forms/
│       ├── ingredient_form.py     # Modify: Ingredient density unit dropdowns
│       └── recipe_form.py         # Modify: RecipeIngredient unit dropdown
└── utils/
    └── constants.py               # Reference: Use existing unit definitions for seeding

src/tests/
├── test_unit_model.py             # NEW: Unit model tests
└── test_unit_seeding.py           # NEW: Seeding tests
```

**Structure Decision**: Single project structure (existing). New Unit model in `src/models/unit.py`, minimal service layer (just query helpers), UI modifications to existing forms.

## Complexity Tracking

*No constitution violations - simple feature following established patterns.*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| (none) | - | - |
