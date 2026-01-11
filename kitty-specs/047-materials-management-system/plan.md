# Implementation Plan: Materials Management System

**Branch**: `047-materials-management-system` | **Date**: 2026-01-10 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/kitty-specs/047-materials-management-system/spec.md`

## Summary

Implement a comprehensive materials management system that parallels the existing ingredient management system, enabling proper handling of non-edible materials (ribbon, boxes, bags, tissue, etc.) used in baking assemblies. The system uses a 3-level mandatory hierarchy (Category > Subcategory > Material > Product), weighted average costing (not FIFO since materials are non-perishable), and full denormalized snapshots for historical accuracy.

## Technical Context

**Language/Version**: Python 3.10+ (matches existing codebase)
**Primary Dependencies**: SQLAlchemy 2.x, CustomTkinter (desktop UI)
**Storage**: SQLite with WAL mode (existing database)
**Testing**: pytest with >70% service layer coverage requirement
**Target Platform**: Desktop (Windows, macOS, Linux)
**Project Type**: Single desktop application
**Performance Goals**: N/A (single-user desktop app)
**Constraints**: Must integrate with existing Composition model for FinishedGoods
**Scale/Scope**: Single user, ~100s of materials, ~1000s of purchases over time

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. User-Centric Design | PASS | Mirrors familiar Ingredients tab pattern |
| II. Data Integrity & FIFO Accuracy | PASS | Weighted average (not FIFO) appropriate for non-perishable materials; full snapshot for history |
| III. Future-Proof Schema | PASS | Uses existing patterns (BaseModel, UUID, slug-based FKs) |
| IV. Test-Driven Development | PASS | Service layer will have >70% coverage |
| V. Layered Architecture | PASS | UI -> Services -> Models separation maintained |
| VI. Schema Change Strategy | PASS | New tables only; no migration needed |
| VII. Pragmatic Aspiration | PASS | Supports AI-assisted JSON import; web-ready service layer |

**Desktop Phase Checks:**
- Does this design block web deployment? NO - stateless services
- Is the service layer UI-independent? YES - all business logic in services
- Does this support AI-assisted JSON import? YES - import/export included
- What's the web migration cost? LOW - services become API endpoints

## Project Structure

### Documentation (this feature)

```
kitty-specs/047-materials-management-system/
├── spec.md              # Feature specification (complete)
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (internal service contracts)
└── tasks.md             # Phase 2 output (created by /spec-kitty.tasks)
```

### Source Code (repository root)

```
src/
├── models/
│   ├── material_category.py      # NEW: MaterialCategory model
│   ├── material_subcategory.py   # NEW: MaterialSubcategory model
│   ├── material.py               # NEW: Material model
│   ├── material_product.py       # NEW: MaterialProduct model
│   ├── material_unit.py          # NEW: MaterialUnit model
│   ├── material_purchase.py      # NEW: MaterialPurchase model
│   ├── material_consumption.py   # NEW: MaterialConsumption model
│   └── __init__.py               # UPDATE: Export new models
├── services/
│   ├── material_catalog_service.py   # NEW: CRUD for hierarchy
│   ├── material_purchase_service.py  # NEW: Purchase & inventory
│   ├── material_unit_service.py      # NEW: Unit calculations
│   ├── material_consumption_service.py # NEW: Assembly consumption
│   └── __init__.py                   # UPDATE: Export new services
├── ui/
│   └── materials_tab.py          # NEW: Materials tab UI
└── tests/
    ├── test_material_catalog_service.py
    ├── test_material_purchase_service.py
    ├── test_material_unit_service.py
    └── test_material_consumption_service.py
```

**Structure Decision**: Single project structure (Option 1) - matches existing codebase. New models follow existing patterns (BaseModel inheritance, slug-based references). New services follow existing patterns (session parameter support, session_scope usage).

## Complexity Tracking

*No constitution violations requiring justification.*

## Parallelization Strategy (Gemini CLI)

The following work packages can be safely parallelized:

**Safe for Gemini (Independent work):**
1. **Models** - All 7 models can be built together (no cross-dependencies within the new model set)
2. **Service Tests** - Test scaffolding can be written while models are being created
3. **Import/Export Extensions** - Can be delegated entirely after core models exist
4. **UI Tab** - Can be built after services are defined (mirrors Ingredients tab)

**Requires Claude Lead (Integration points):**
1. Composition model integration (adding material_unit_id, material_id columns)
2. AssemblyRun integration (MaterialConsumption creation during assembly)
3. Final acceptance testing

## Phase 0: Research Findings

See [research.md](research.md) for detailed analysis.

**Key Decisions:**
1. **Unit Conversion**: Products store native purchase units; system converts to base units (inches for linear, square inches for area) for storage and aggregation
2. **Inventory Enforcement**: No "Record Anyway" bypass - assembly blocked when inventory insufficient
3. **Historical Snapshots**: Full denormalized MaterialConsumption (product_name, material_name, category_name, quantity, unit_cost, supplier_name)
4. **Material Resolution**: Inline during assembly - dropdown per pending material
5. **Hierarchy**: Mandatory 3-level (Category > Subcategory > Material)

## Phase 1: Design Artifacts

See:
- [data-model.md](data-model.md) - Entity definitions and relationships
- [contracts/](contracts/) - Service interface contracts
- [quickstart.md](quickstart.md) - Developer onboarding guide
