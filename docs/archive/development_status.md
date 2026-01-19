# Seasonal Baking Tracker - Development Status

**Last Updated:** 2025-12-14
**Current Phase:** User Testing (Features 001-019 Complete)
**Application Version:** 0.6.0
**Active Branch:** `main`

---

## Quick Reference

| Resource | Purpose |
|----------|---------|
| [feature_roadmap.md](./feature_roadmap.md) | Feature sequencing, current status, key decisions |
| [requirements.md](./requirements.md) | Functional and non-functional requirements |
| [architecture.md](./architecture.md) | System architecture and design decisions |
| [import_export_specification.md](./import_export_specification.md) | Data portability (v3.3 format) |
| [packaging_options.md](./packaging_options.md) | Windows distribution strategies |
| [constitution.md](../.kittify/memory/constitution.md) | Core principles and governance (v1.2.0) |

### Quick Commands

```bash
# Run all tests
pytest src/tests -v

# Run with coverage
pytest src/tests -v --cov=src

# Run application
python src/main.py

# Export data (before schema changes)
python -m src.utils.import_export_cli export my_backup.json

# Import data (after schema changes)
python -m src.utils.import_export_cli import my_backup.json
```

---

## Project Overview

The Seasonal Baking Tracker is a desktop application for managing holiday baking inventory, recipes, finished goods, and gift package planning. Built with Python 3.12, SQLite, and CustomTkinter.

**Technology Stack:**
- Python 3.12.10
- SQLite 3.49.1 with SQLAlchemy ORM
- CustomTkinter 5.2.2 for UI
- Pytest for testing

**Architecture:**
- **Models Layer**: SQLAlchemy models for data persistence
- **Services Layer**: Business logic and database operations
- **UI Layer**: CustomTkinter-based interface
- **Utils Layer**: Validation, constants, configuration

---

## Current Status Summary

### Completed Features (001-019)

| Feature | Name | Status |
|---------|------|--------|
| 001-010 | Foundation, Ingredient/Product Architecture, Density Model | ✅ Complete |
| 011 | Packaging Materials & BOM Foundation | ✅ Complete |
| 012 | Nested Recipes (RecipeComponent) | ✅ Complete |
| 013 | Production & Assembly Services | ✅ Complete |
| 014 | Production UI | ✅ Complete |
| 016 | Event-Centric Production Model | ✅ Complete |
| 017 | Reporting & Event Planning | ✅ Complete |
| 018 | Event Production Dashboard | ✅ Complete |
| 019 | Unit Conversion Simplification | ✅ Complete |

**Note:** Feature 015 was skipped (aborted prior attempt).

### Current Focus

**User Testing Phase** - Real-world testing of complete feature set with primary user.

### Next Planned

| Feature | Name | Priority | Status |
|---------|------|----------|--------|
| 020 | Packaging & Distribution | LOW | Blocked on user testing |

---

## Development Phases

### Phase 1: Foundation (MVP) ✅ COMPLETED

**Completion Date:** 2025-11-03

- SQLite database with WAL mode and foreign key enforcement
- Ingredient model with purchase/recipe unit conversion
- Recipe model with many-to-many ingredient relationships
- Full CRUD operations for ingredients and recipes
- Real-time cost calculation based on ingredient costs
- Main window with tabbed navigation (CustomTkinter)
- Unit tests with >70% coverage on services layer

### Phase 2: Finished Goods & Bundles ✅ COMPLETED

**Completion Date:** 2025-11-04

- FinishedGood model with two yield modes (discrete count, batch portion)
- Bundle model for grouping finished goods
- Cost calculation at all levels (recipe → finished good → bundle)
- Batch planning calculations
- Eager loading strategy to prevent DetachedInstanceError

### Phase 3: Event Planning ✅ COMPLETED

**Completion Date:** 2025-11-04

- Event, Recipient, Package models
- EventRecipientPackage junction for assignments
- Recipe needs calculation (batches needed per recipe)
- Shopping list generation (needs vs inventory)
- Recipient history tracking
- EventDetailWindow with 4 planning tabs

### Phase 4: Ingredient/Product Architecture ✅ COMPLETED

**Completion Date:** 2025-12-05

- Separated Ingredient (generic) from Product (brand-specific)
- InventoryItem with FIFO tracking
- Purchase history for price trending
- 4-field density model for unit conversions
- Industry standard fields (FoodOn, GTIN, etc.) as nullable
- Import/export v3.x format

### Phase 5: Production Tracking ✅ COMPLETED

**Completion Date:** 2025-12-12

**Feature 011: Packaging Materials (2025-12-08)**
- `is_packaging` flag on Ingredient
- Packaging materials in Composition
- BOM patterns established

**Feature 012: Nested Recipes (2025-12-09)**
- RecipeComponent junction table
- Recursive cost calculation
- Recursive ingredient aggregation
- Maximum 3 levels of nesting

**Feature 013: Production Services (2025-12-09)**
- BatchProductionService with FIFO consumption
- AssemblyService with component consumption
- 51 tests, 91% coverage

**Feature 014: Production UI (2025-12-10)**
- Record Production dialog with availability checking
- Record Assembly dialog with component availability
- Integration with FinishedUnits and FinishedGoods tabs

**Feature 016: Event-Centric Production Model (2025-12-11)**
- `event_id` FK on ProductionRun and AssemblyRun
- EventProductionTarget and EventAssemblyTarget tables
- `fulfillment_status` on EventRecipientPackage
- Progress calculation methods
- 10 work packages, 65+ service tests

### Phase 6: Reporting & Polish ✅ COMPLETED

**Completion Date:** 2025-12-14

**Feature 017: Reporting & Event Planning (2025-12-12)**
- Shopping list CSV export
- Event summary reports (planned vs actual)
- Cost analysis views
- Recipient history reports
- Dashboard enhancements

**Feature 018: Event Production Dashboard (2025-12-12)**
- "Mission control" view for events
- Progress bars per recipe/finished good
- Fulfillment status tracking

**Feature 019: Unit Conversion Simplification (2025-12-14)**
- Removed redundant `Ingredient.recipe_unit` column
- Deleted `UnitConversion` model and table
- 4-field density model is canonical conversion source
- Import/export updated to v3.3

---

## Schema Evolution

| Version | Date | Key Changes |
|---------|------|-------------|
| v0.3 | 2025-11-04 | Event planning, packages, recipients |
| v0.4 | 2025-11-09 | Ingredient/Product separation, FIFO inventory |
| v0.5 | 2025-12-09 | Production tracking, nested recipes |
| v0.6 | 2025-12-14 | Event-centric production, unit simplification |

**Schema Change Strategy (Constitution v1.2.0):** For desktop phase, use export → reset → import cycle rather than migration scripts.

---

## Import/Export

**Current Version:** v3.3

**Supported Entity Types:**
1. Ingredients (with 4-field density)
2. Products (brand-specific)
3. Inventory Items
4. Purchases
5. Recipes (with nested RecipeComponents)
6. Finished Goods
7. Bundles
8. Packages
9. Recipients
10. Events (with assignments and targets)

**Removed in v3.3:**
- `unit_conversions` array (density model makes it redundant)
- `recipe_unit` field on ingredients

---

## Technical Achievements

### Cost Calculation Hierarchy

```
Ingredient (via Product purchase)
  ↓ [density conversion: volume ↔ weight]
RecipeIngredient (quantity in any unit)
  ↓ [FIFO consumption from inventory]
Recipe (total_cost = sum of ingredient costs)
  ↓ [cost per item = recipe_cost / yield_quantity]
FinishedGood (cost_per_item)
  ↓ [bundle cost = sum(fg_cost × quantity)]
Bundle (total_cost)
  ↓ [package cost = sum(bundle_cost × quantity)]
Package (total_cost)
  ↓ [event cost = sum(package_cost × recipients)]
Event (total_estimated_cost)
```

### Unit Conversion System (v0.6+)

**Canonical Source:** 4-field density on Ingredient
- `density_volume_value` / `density_volume_unit`
- `density_weight_value` / `density_weight_unit`

**Conversion Flow:**
- Volume ↔ Weight via `get_density_g_per_ml()`
- Standard conversions within type (cups ↔ ml, lb ↔ g)
- `convert_any_units()` handles cross-type via density

### FIFO Inventory

- InventoryItem tracks purchase dates
- `consume_fifo()` depletes oldest items first
- Accurate cost tracking when prices fluctuate
- Supports lot/batch tracking

---

## Known Limitations

- No undo functionality
- Search is case-sensitive
- No image attachments for recipes
- Single user only (no authentication)
- Windows primary target (cross-platform code but untested on Mac/Linux)

---

## Development Guidelines

### Spec-Kitty Workflow

All features follow the spec-kitty process:
1. `/spec-kitty.specify` - Create specification
2. `/spec-kitty.plan` - Technical planning
3. `/spec-kitty.tasks` - Generate task prompts
4. `/spec-kitty.implement` - Execute with TDD
5. `/spec-kitty.review` - Validate against acceptance criteria
6. `/spec-kitty.accept` - Full acceptance checks
7. `/spec-kitty.merge` - Merge and cleanup

### Testing Strategy

- Unit tests for all services (>70% coverage)
- Integration tests for database operations
- Manual UI testing with real data
- Test edge cases and error conditions

### Code Organization

```
src/
├── models/        # SQLAlchemy models
├── services/      # Business logic
├── ui/            # CustomTkinter interface
│   ├── forms/     # Dialog forms
│   └── widgets/   # Reusable components
├── utils/         # Helpers, validators
└── tests/         # pytest tests
```

---

## Document History

- **v1.0** (2025-11-02) - Initial Phase 1 plan
- **v2.0** (2025-11-04) - Phase 1-2 complete
- **v3.0** (2025-11-04) - Phase 3b complete (Event Planning)
- **v4.0** (2025-11-09) - Phase 4 service layer complete
- **v5.0** (2025-12-14) - Consolidated from current_priorities.md. Features 001-019 complete. User testing phase.

---

**Document Status:** Living document, updated with each major milestone
**Authoritative Feature Status:** See [feature_roadmap.md](./feature_roadmap.md)
