# Implementation Plan: Packaging & BOM Foundation

**Branch**: `011-packaging-bom-foundation` | **Date**: 2025-12-08 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/kitty-specs/011-packaging-bom-foundation/spec.md`

## Summary

Add support for packaging materials (bags, boxes, ribbon, labels) as trackable inventory items that can be associated with FinishedGood assemblies and Packages. Extend the Composition model to support packaging products as components with variable quantities. Update shopping list calculations to aggregate and display packaging needs alongside food ingredients.

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: SQLAlchemy 2.x, CustomTkinter
**Storage**: SQLite with WAL mode (auto-created tables)
**Testing**: pytest with >70% service layer coverage
**Target Platform**: Desktop (Windows/macOS)
**Project Type**: Single application

**Performance Goals**: N/A (single user, small dataset)
**Constraints**: No Alembic migrations - direct SQLAlchemy model updates with auto-create
**Scale/Scope**: Single user, hundreds of ingredients/products

## Planning Decisions

The following decisions were confirmed during the planning phase:

### Q1: Shopping List Display
**Decision**: Separate sections - "Ingredients" followed by "Packaging"
**Rationale**: Clear visual separation helps user distinguish between food items needing recipe-based shopping and packaging supplies. Keeps shopping list organized.

### Q2: Schema Changes
**Decision**: Direct SQLAlchemy model updates with auto-create (no Alembic)
**Rationale**: Matches existing project pattern. SQLite database can be recreated from export/import if needed. User already has established backup workflow.

### Q3: Packaging UI
**Decision**: Simple inline forms within existing FinishedGood/Package dialogs
**Rationale**: Minimizes UI changes. Adds a "Packaging" section to existing assembly dialogs. Reuses existing component editing patterns.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. User-Centric Design | PASS | Feature solves real problem (tracking packaging supplies). UI reuses existing patterns. |
| II. Data Integrity & FIFO | PASS | Packaging inventory uses same InventoryItem model with FIFO support. |
| III. Future-Proof Schema | PASS | Adds `is_packaging` flag to Ingredient (nullable for existing data). Product model unchanged. |
| IV. Test-Driven Development | PASS | Will add service layer tests for packaging compositions and shopping list calculations. |
| V. Layered Architecture | PASS | Services handle packaging logic. UI only displays data. |
| VI. Migration Safety | PASS | No migrations - auto-create with backward compatible nullable columns. |
| VII. Pragmatic Aspiration | PASS | Minimal schema changes. Web migration cost: LOW (services are UI-independent). |

## Project Structure

### Documentation (this feature)

```
kitty-specs/011-packaging-bom-foundation/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output (/spec-kitty.tasks)
```

### Source Code (repository root)

```
src/
├── models/
│   ├── ingredient.py       # Add is_packaging boolean
│   └── composition.py      # Add packaging_product_id FK
├── services/
│   ├── ingredient_service.py      # Update for packaging categories
│   ├── composition_service.py     # Support packaging compositions
│   ├── event_service.py           # Shopping list aggregation
│   └── import_export_service.py   # Include is_packaging flag
└── ui/
    └── [existing dialogs]         # Add packaging sections

tests/
├── integration/
│   └── test_packaging_flow.py     # End-to-end packaging tests
└── unit/
    ├── test_composition_service.py # Packaging composition tests
    └── test_event_service.py       # Shopping list tests
```

**Structure Decision**: Single project layout. Extends existing models/services in place. No new files except test additions.

## Schema Changes Summary

### Ingredient Model Changes
```python
# Add to Ingredient model
is_packaging = Column(Boolean, nullable=False, default=False)
```

**New Packaging Categories**: Bags, Boxes, Ribbon, Labels, Tissue Paper, Wrapping, Other Packaging

### Composition Model Changes
```python
# Add to Composition model
packaging_product_id = Column(
    Integer, ForeignKey("products.id", ondelete="RESTRICT"), nullable=True, index=True
)

# Update XOR constraint to include packaging
CheckConstraint(
    "(finished_unit_id IS NOT NULL AND finished_good_id IS NULL AND packaging_product_id IS NULL) OR "
    "(finished_unit_id IS NULL AND finished_good_id IS NOT NULL AND packaging_product_id IS NULL) OR "
    "(finished_unit_id IS NULL AND finished_good_id IS NULL AND packaging_product_id IS NOT NULL)",
    name="ck_composition_exactly_one_component",
)
```

### Package Model
Add back-reference to packaging compositions.

```python
# Add to Package model
packaging_compositions = relationship(
    "Composition",
    foreign_keys="Composition.package_id",
    back_populates="package",
    cascade="all, delete-orphan",
    lazy="selectin",
)
```

### Composition Model (Full Update)
Extend to support both FinishedGood and Package parents, plus packaging products.

```python
# Add package_id FK
package_id = Column(Integer, ForeignKey("packages.id", ondelete="CASCADE"), nullable=True, index=True)

# Add packaging_product_id FK
packaging_product_id = Column(Integer, ForeignKey("products.id", ondelete="RESTRICT"), nullable=True, index=True)

# Change quantity type
component_quantity = Column(Float, nullable=False, default=1.0)  # Was Integer

# Parent constraint: exactly one of assembly_id or package_id
CheckConstraint(
    "(assembly_id IS NOT NULL AND package_id IS NULL) OR "
    "(assembly_id IS NULL AND package_id IS NOT NULL)",
    name="ck_composition_exactly_one_parent",
)

# Component constraint: exactly one of three options
CheckConstraint(
    "(finished_unit_id IS NOT NULL AND finished_good_id IS NULL AND packaging_product_id IS NULL) OR "
    "(finished_unit_id IS NULL AND finished_good_id IS NOT NULL AND packaging_product_id IS NULL) OR "
    "(finished_unit_id IS NULL AND finished_good_id IS NULL AND packaging_product_id IS NOT NULL)",
    name="ck_composition_exactly_one_component",
)
```

## Complexity Tracking

*No constitution violations requiring justification.*

| Aspect | Complexity | Justification |
|--------|------------|---------------|
| Composition XOR extension | Low | Natural extension of existing pattern |
| Ingredient flag | Low | Single boolean column |
| Package parent support | Low | Mirrors existing assembly_id pattern |
| Shopping list aggregation | Medium | New service logic but follows existing patterns |

## Research Answers (Phase 0)

### Q1: Package Packaging Association
**Decision**: Extend Composition with `package_id` FK
**Rationale**: Consistent with spec FR-004 wording. Reuses existing Composition model pattern. Avoids code duplication of separate PackageComposition table.

### Q2: Composition Quantity Type
**Decision**: Change `component_quantity` from Integer to Float
**Rationale**: FR-006 requires decimal support ("0.5 yards ribbon"). SQLite handles type change seamlessly. No migration needed.

### Q3: Deletion Handling
**Decision**: Use `ondelete="RESTRICT"` on `packaging_product_id` FK
**Rationale**: SQLite supports RESTRICT with `PRAGMA foreign_keys=ON` (enabled by default in SQLAlchemy 2.x). Service layer catches IntegrityError and raises user-friendly validation error.

## Phase 1 Artifacts

- **research.md**: Complete - Research questions answered
- **data-model.md**: Complete - Detailed schema design
- **quickstart.md**: Complete - Developer setup guide
- **contracts/**: Complete - Service method contracts
  - composition_service.md
  - event_service.md
  - ingredient_service.md
  - import_export_service.md

## Ready for Phase 2

Plan is complete and ready for `/spec-kitty.tasks` to generate work packages.
