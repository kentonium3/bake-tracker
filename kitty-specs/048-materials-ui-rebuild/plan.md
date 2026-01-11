# Implementation Plan: Materials UI Rebuild - Match Ingredients Pattern

**Branch**: `048-materials-ui-rebuild` | **Date**: 2026-01-11 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/kitty-specs/048-materials-ui-rebuild/spec.md`

## Summary

Rebuild the Materials UI to exactly match the Ingredients tab pattern. The current Materials UI uses a single collapsible tree view with mixed listings. The target is a 3-tab structure (Materials Catalog | Material Products | Material Units) with grid views, filters, and consistent dialog patterns. No tree view toggle - flat grid views only.

**Key Constraint**: Copy patterns from `src/ui/ingredients_tab.py` exactly, not invent new approaches.

## Technical Context

**Language/Version**: Python 3.10+ (minimum for type hints)
**Primary Dependencies**: CustomTkinter, tkinter.ttk, SQLAlchemy 2.x
**Storage**: SQLite with WAL mode (existing)
**Testing**: pytest
**Target Platform**: Desktop (Windows, macOS, Linux)
**Project Type**: Single desktop application
**Performance Goals**: Responsive UI (<100ms for filter operations)
**Constraints**: Must match Ingredients tab layout exactly (FR-025, FR-026, FR-027)
**Scale/Scope**: ~100-500 materials/products expected; single-user desktop app

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| Layered Architecture | PASS | UI-only changes, no service/model modifications |
| User-Centric Design | PASS | Matching established Ingredients pattern for consistency |
| Test-Driven Development | PASS | UI components will have unit tests for callbacks |
| FIFO Accuracy | N/A | Not applicable to Materials (no FIFO consumption model) |
| Future-Proof Schema | PASS | No schema changes required |

## Project Structure

### Documentation (this feature)

```
kitty-specs/048-materials-ui-rebuild/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0 output - decisions and rationale
├── data-model.md        # Phase 1 output - UI component structure
├── quickstart.md        # Phase 1 output - implementation guidance
├── tasks.md             # Phase 2 output (created by /spec-kitty.tasks)
└── tasks/               # Work package prompts
```

### Source Code (repository root)

```
src/
├── ui/
│   ├── materials_tab.py          # REPLACE: New 3-tab implementation (~2000 lines)
│   ├── ingredients_tab.py        # REFERENCE: Pattern to copy (1741 lines)
│   └── widgets/
│       └── ingredient_tree_widget.py  # REFERENCE: Not needed for materials
├── services/
│   ├── material_catalog_service.py    # USE: Existing, no changes
│   ├── material_product_service.py    # USE: Existing, no changes
│   ├── material_unit_service.py       # USE: Existing, no changes
│   └── material_purchase_service.py   # USE: Existing, no changes
└── models/
    └── material.py                    # USE: Existing, no changes

src/tests/
└── ui/
    └── test_materials_tab.py     # NEW: UI tests
```

**Structure Decision**: Single project structure. Only `src/ui/materials_tab.py` is modified/replaced. All other files are used as-is.

## Design Decisions

### D1: Tab Structure

**Decision**: 3 sub-tabs within Materials using `CTkTabview`
- Tab 1: "Materials Catalog" - Material definitions (L0/L1/L2 hierarchy display)
- Tab 2: "Material Products" - Specific purchasable products
- Tab 3: "Material Units" - Packaging units that consume material

**Rationale**: User confirmed third tab for MaterialUnits. Matches logical separation in Ingredients (Catalog vs Products) plus Materials-specific unit tracking.

### D2: View Mode

**Decision**: Flat grid views only, no tree/flat toggle

**Rationale**: User confirmed no tree view needed for materials. Simplifies implementation and UI. Hierarchy is displayed via L0/L1 columns in grid (same as Ingredients flat view).

### D3: Grid Columns

| Tab | Columns |
|-----|---------|
| Materials Catalog | Category (L0), Subcategory (L1), Material Name, Default Unit |
| Material Products | Material, Product Name, Inventory, Unit Cost, Supplier |
| Material Units | Material, Unit Name, Qty/Unit, Available, Cost/Unit |

### D4: Filter Controls

**Materials Catalog Tab** (matching Ingredients):
- Search box (filters by name)
- L0 Category dropdown (cascading)
- L1 Subcategory dropdown (cascading, depends on L0)
- Level filter dropdown (All Levels, Categories L0, Subcategories L1, Materials L2)
- Clear button

**Material Products Tab**:
- Search box (filters by product name)
- Material dropdown (filter by linked material)
- Clear button

**Material Units Tab**:
- Search box (filters by unit name)
- Material dropdown (filter by linked material)
- Clear button

### D5: Dialog Patterns

All dialogs follow `IngredientFormDialog` pattern:
- Modal with `transient()` and `grab_set()`
- Label column ~120px, input flexible
- Cascading dropdowns where applicable
- Delete button (left) when editing, Save/Cancel (right)
- Validation before save

### D6: Button States

- Edit button enabled only when item selected
- Record Purchase / Adjust Inventory enabled only when product selected
- Add buttons always enabled

## Mapping: Ingredients -> Materials

| Ingredients Component | Materials Equivalent |
|-----------------------|---------------------|
| `IngredientsTab` | `MaterialsCatalogTab` (inner class) |
| `IngredientFormDialog` | `MaterialFormDialog` |
| Products tab (separate file) | `MaterialProductsTab` (inner class) |
| `ProductFormDialog` | `MaterialProductFormDialog` |
| N/A | `MaterialUnitsTab` (inner class) |
| N/A | `MaterialUnitFormDialog` |
| `ingredient_service` | `material_catalog_service` |
| `product_service` | `material_product_service` |
| N/A | `material_unit_service` |
| `ingredient_hierarchy_service` | `material_catalog_service` (has hierarchy methods) |

## Implementation Phases

### Phase 1: Core Tab Structure
- Create `MaterialsTab` with `CTkTabview` containing 3 tabs
- Implement basic grid views for each tab
- Wire up refresh and lazy loading

### Phase 2: Materials Catalog Tab
- Implement grid with L0/L1/Name/Unit columns
- Implement cascading L0/L1 filters
- Implement level filter
- Implement search
- Implement `MaterialFormDialog` with cascading dropdowns
- Wire up CRUD operations

### Phase 3: Material Products Tab
- Implement grid with Material/Name/Inventory/Cost/Supplier columns
- Implement material filter dropdown
- Implement search
- Implement `MaterialProductFormDialog`
- Implement `RecordPurchaseDialog`
- Implement `AdjustInventoryDialog`
- Wire up CRUD and inventory operations

### Phase 4: Material Units Tab
- Implement grid with Material/Name/Qty/Available/Cost columns
- Implement material filter dropdown
- Implement search
- Implement `MaterialUnitFormDialog`
- Wire up CRUD operations

### Phase 5: Polish and Testing
- Status bar updates
- Selection state management
- Button enable/disable logic
- Unit tests for callbacks
- Manual acceptance testing

## Complexity Tracking

*No constitution violations - no complexity justification needed*

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Service API mismatch | Low | Medium | Services already exist and work with current UI |
| Missing hierarchy methods | Low | Low | material_catalog_service has list_categories/subcategories/materials |
| Performance with large datasets | Low | Low | ttk.Treeview handles large datasets well; same as Ingredients |

## Dependencies

- Existing services: `material_catalog_service`, `material_product_service`, `material_unit_service`, `material_purchase_service`, `supplier_service`
- Reference implementation: `src/ui/ingredients_tab.py`
- No external dependencies to add

## Success Metrics

From spec:
- SC-002: Materials tab layout visually indistinguishable from Ingredients tab layout
- SC-003: All CRUD operations complete without errors on valid input
- SC-006: 100% of acceptance scenarios pass manual testing
- SC-007: No regression in existing materials functionality
