# Research: Finished Goods Catalog UI

**Feature**: 088-finished-goods-catalog-ui
**Date**: 2026-01-30

## Codebase Pattern Research

### 1. Tab Creation Pattern

**Decision**: Add FinishedGoodsTab as 4th tab in CatalogMode
**Rationale**: Follows existing pattern for non-group tabs (like MaterialsTab)
**Alternatives Considered**:
- Group tab with sub-tabs → Rejected: FinishedGoods is single view, no sub-tabs needed

**Key Files**:
- `src/ui/modes/catalog_mode.py` - Where to add tab (lines 59-87)
- `src/ui/materials_tab.py` - Pattern for single view tab

### 2. F087 Layout Pattern

**Decision**: Follow F087 exactly (3-row layout, ttk.Treeview)
**Rationale**: Required by spec; ensures consistency with other catalog tabs
**Alternatives Considered**: None - F087 compliance is mandatory

**Key Files**:
- `src/ui/recipes_tab.py` - Reference implementation with ttk.Treeview
- `src/ui/finished_units_tab.py` - Recently converted to ttk.Treeview

**Pattern Details**:
```python
self.grid_rowconfigure(0, weight=0)  # Search/filters (fixed)
self.grid_rowconfigure(1, weight=0)  # Action buttons (fixed)
self.grid_rowconfigure(2, weight=1)  # ttk.Treeview (expandable)
self.grid_rowconfigure(3, weight=0)  # Status bar (fixed)
```

### 3. FinishedGood Model

**Decision**: Use existing model without changes
**Rationale**: Model already supports all required fields and relationships
**Alternatives Considered**: None - model is complete

**Key Fields**:
- `display_name` (required)
- `assembly_type` (enum: CUSTOM_ORDER, GIFT_BOX, VARIETY_PACK, SEASONAL_BOX, EVENT_PACKAGE)
- `packaging_instructions` (optional)
- `notes` (optional)
- `components` relationship → List[Composition]

**Key File**: `src/models/finished_good.py`

### 4. Composition Factory Methods

**Decision**: Use existing factory methods for component creation
**Rationale**: Factory methods handle polymorphic FK correctly
**Alternatives Considered**: Direct Composition creation → Rejected: Error-prone, violates XOR constraint

**Factory Methods**:
```python
Composition.create_unit_composition(assembly_id, finished_unit_id, quantity)
Composition.create_assembly_composition(assembly_id, finished_good_id, quantity)
Composition.create_material_unit_composition(assembly_id, material_unit_id, quantity)
```

**Key File**: `src/models/composition.py`

### 5. Service Layer Pattern

**Decision**: Enhance existing finished_good_service.py with atomic component handling
**Rationale**: Follows existing session management patterns; maintains layered architecture
**Alternatives Considered**:
- New service file → Rejected: Existing service provides foundation
- UI-level transaction management → Rejected: Violates layered architecture

**Enhancements Needed**:
1. `create_finished_good()` accepts `components` list
2. `update_finished_good()` with component replacement
3. `validate_no_circular_references()` for nested FinishedGoods
4. Delete safety checks (referenced by other FinishedGoods or events)

**Key File**: `src/services/finished_good_service.py`

### 6. Form Dialog Pattern

**Decision**: Create FinishedGoodFormDialog following RecipeFormDialog pattern
**Rationale**: Established pattern for complex create/edit forms
**Alternatives Considered**:
- Inline form in tab → Rejected: Too complex, breaks tab layout pattern
- Separate page → Rejected: Overcomplicates navigation

**Pattern Elements**:
- CTkToplevel modal dialog
- Scrollable form with sections
- Category filter + type-ahead search for component selection
- Save/Cancel buttons

**Key Files**:
- `src/ui/forms/recipe_form.py` - Reference for form structure
- `src/ui/widgets/search_bar.py` - Reusable search widget

### 7. Component Selection UI

**Decision**: Category filter dropdown + type-ahead search for each component type
**Rationale**: Handles large catalogs efficiently; familiar pattern from recipes
**Alternatives Considered**:
- Tree browser only → Rejected: Slower for known items
- Dropdown only → Rejected: Unwieldy with 50+ items

**Pattern**:
1. Category filter narrows options
2. Type-ahead search finds specific items
3. Quantity input with validation
4. Add/Remove buttons

## Technical Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Tab type | Single view (not group) | FinishedGoods has no sub-tabs |
| Grid widget | ttk.Treeview | F087 compliance, trackpad scrolling |
| Form dialog | Modal CTkToplevel | Follows RecipeFormDialog pattern |
| Component selection | Filter + Search | Handles large catalogs |
| Service transactions | session_scope() | Atomic saves with rollback |
| Circular reference check | Graph traversal | Catches all cycle types |

## Files to Create

1. `src/ui/finished_goods_tab.py` - Main tab widget
2. `src/ui/forms/finished_good_form.py` - Create/edit dialog
3. `src/tests/test_finished_good_service.py` - Service layer tests (enhance existing)

## Files to Modify

1. `src/ui/modes/catalog_mode.py` - Add Finished Goods tab
2. `src/services/finished_good_service.py` - Enhance with component handling
