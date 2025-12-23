# Implementation Plan: Product Catalog Management

**Branch**: `027-product-catalog-management` | **Date**: 2025-12-22 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/027-product-catalog-management/spec.md`

## Summary

Enable standalone product catalog management with supplier tracking and purchase history. This is the foundation feature (027 of 3) that introduces:
- New Products tab with CRUD operations, filtering, and search
- New Supplier and Purchase entities for price tracking
- Schema modifications to Product and InventoryAddition
- Migration via export/reset/import cycle per Constitution VI

**Development Approach**: Sequential with review gates - complete each layer before starting next to minimize merge conflicts and ensure solid foundations.

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: SQLAlchemy 2.x, CustomTkinter, pytest
**Storage**: SQLite with WAL mode
**Testing**: pytest with >70% coverage target for services
**Target Platform**: Desktop (macOS/Windows)
**Project Type**: Single desktop application
**Performance Goals**: Product search <5 seconds, add product <30 seconds (per SC-001, SC-002)
**Constraints**: Single-user, offline-capable, no network dependencies
**Scale/Scope**: ~500 products, ~50 suppliers, ~2000 purchases (holiday baking scale)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| I. User-Centric Design | PASS | Products tab addresses real user need (40+ min data entry pain point) |
| II. Data Integrity & FIFO | PASS | Purchase.unit_price replaces InventoryAddition.price_paid; RESTRICT deletes preserve history |
| III. Future-Proof Schema | PASS | UUID support, industry-standard fields preserved |
| IV. Test-Driven Development | PASS | >70% coverage target, test files defined in research.md |
| V. Layered Architecture | PASS | UI → Services → Models flow maintained |
| VI. Schema Change Strategy | PASS | Export/reset/import cycle for migration |
| VII. Pragmatic Aspiration | PASS | Desktop-focused, web migration path preserved |

**Post-Design Re-Check**: All gates pass. No violations requiring justification.

## Project Structure

### Documentation (this feature)

```
kitty-specs/027-product-catalog-management/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0 research decisions
├── data-model.md        # Entity definitions
├── quickstart.md        # Developer onboarding
├── checklists/          # Quality checklists
│   └── requirements.md
├── research/            # Evidence tracking
│   ├── evidence-log.csv
│   └── source-register.csv
└── tasks.md             # Task tracking (created by /spec-kitty.tasks)
```

### Source Code (repository root)

```
src/
├── models/
│   ├── __init__.py          # Export Supplier, Purchase (MODIFY)
│   ├── supplier.py          # NEW: Supplier model
│   ├── purchase.py          # NEW: Purchase model
│   ├── product.py           # MODIFY: Add preferred_supplier_id, is_hidden
│   └── inventory_addition.py # MODIFY: Add purchase_id
├── services/
│   ├── __init__.py          # Export new services (MODIFY)
│   ├── supplier_service.py  # NEW: Supplier CRUD
│   ├── product_catalog_service.py # NEW: Product CRUD with purchase history
│   └── import_export_service.py   # MODIFY: Handle new entities
├── ui/
│   ├── main_window.py       # MODIFY: Add Products tab
│   ├── products_tab.py      # NEW: Products tab frame
│   └── forms/
│       ├── add_product_dialog.py    # NEW: Add/Edit product
│       └── product_detail_dialog.py # NEW: Product detail with history
└── tests/
    ├── services/
    │   ├── test_supplier_service.py        # NEW
    │   └── test_product_catalog_service.py # NEW
    └── integration/
        └── test_product_catalog.py         # NEW
```

**Structure Decision**: Single project structure following existing codebase patterns.

## Work Package Overview

Development proceeds in sequential phases with review gates:

### Phase 1: Schema & Models (WP01-WP02)
Foundation layer - must complete before services.

| WP | Name | Description | Dependencies |
|----|------|-------------|--------------|
| WP01 | Supplier Model | Create Supplier SQLAlchemy model | None |
| WP02 | Purchase Model & Product Updates | Create Purchase model, modify Product and InventoryAddition | WP01 |

**Review Gate**: All models import correctly, relationships valid.

### Phase 2: Service Layer (WP03-WP04)
Business logic - must complete before UI.

| WP | Name | Description | Dependencies |
|----|------|-------------|--------------|
| WP03 | Supplier Service | CRUD operations with session pattern | WP01 |
| WP04 | Product Catalog Service | Product CRUD, purchase history, filtering | WP02, WP03 |

**Review Gate**: >70% test coverage, all service tests pass.

### Phase 3: UI Layer (WP05-WP07)
User interface - depends on services.

| WP | Name | Description | Dependencies |
|----|------|-------------|--------------|
| WP05 | Products Tab Frame | Main Products tab with grid and filters | WP04 |
| WP06 | Add Product Dialog | Create/edit product form | WP04 |
| WP07 | Product Detail Dialog | View product with purchase history | WP04 |

**Review Gate**: UI renders correctly, all user stories testable.

### Phase 4: Integration & Migration (WP08-WP09)
Bringing it all together.

| WP | Name | Description | Dependencies |
|----|------|-------------|--------------|
| WP08 | Import/Export Updates | Update export/import for new entities | WP02, WP04 |
| WP09 | Migration Transformation | Transform existing data for new schema | WP08 |

**Review Gate**: Full integration tests pass, migration preserves all data.

## Parallelization Notes

Within each phase, some tasks can run in parallel:
- **Phase 2**: WP03 and WP04 can start simultaneously (WP04 depends on WP03 for supplier lookups but can stub initially)
- **Phase 3**: WP06 and WP07 can develop in parallel once WP05 establishes the tab frame

Cross-phase parallelization is intentionally avoided per the chosen "Sequential with review gates" approach.

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Migration data loss | Backup production DB before migration; comprehensive transformation tests |
| Existing test breakage | Update test fixtures in WP02 before running full suite |
| Service session issues | Follow CLAUDE.md session pattern strictly; review in WP03/WP04 |

## Success Criteria Mapping

| Criterion | Work Package | Validation |
|-----------|--------------|------------|
| SC-001: Add product <30s | WP06 | Manual timing test |
| SC-002: Search <5s | WP05 | Manual timing test |
| SC-003: 2 clicks to history | WP05, WP07 | UI flow verification |
| SC-004: 100% inventory→purchase | WP08 | Integration test |
| SC-005: Hidden products excluded | WP04, WP05 | Unit + integration tests |
| SC-006: >70% service coverage | WP03, WP04 | pytest --cov |
| SC-007: Existing tests pass | WP02 | pytest full suite |
| SC-008: Migration success | WP09 | Migration validation script |

## Next Steps

1. Run `/spec-kitty.tasks` to generate detailed task prompts
2. Execute WP01-WP02 (Schema & Models)
3. Review gate: verify models
4. Execute WP03-WP04 (Services)
5. Review gate: verify test coverage
6. Execute WP05-WP07 (UI)
7. Review gate: verify user stories
8. Execute WP08-WP09 (Integration & Migration)
9. Run `/spec-kitty.accept` for final validation
