# Research: Context-Rich Export Fixes

**Feature**: 053-context-rich-export-fixes
**Date**: 2026-01-15

## Research Questions

### Q1: How are context-rich exports currently implemented?

**Decision**: Context-rich exports are handled by `src/services/denormalized_export_service.py`

**Findings**:
- Service has `export_*_view()` methods for each entity type
- Currently supports: ingredients, materials, recipes, products (partially), inventory, purchases
- File prefix hardcoded as `view_` in each method
- Each export creates JSON with `_meta` section defining editable vs readonly fields
- Returns `ExportResult` dataclass with record count and path

**Key Methods**:
- `export_ingredients_view()` - lines ~200-280
- `export_materials_view()` - lines ~280-360
- `export_recipes_view()` - lines ~360-440
- `export_products_view()` - exists but not exposed in UI
- `export_all_views()` - bulk export function (not used in UI)

**Rationale**: Existing patterns are well-established and can be followed for new entity types.

---

### Q2: How is the UI export dialog structured?

**Decision**: Export dialog is in `src/ui/import_export_dialog.py`, class `ExportDialog`

**Findings**:
- Tabbed interface with 3 tabs: "Full Backup", "Catalog", "Context-Rich"
- Context-Rich tab (lines 1633-1691) uses **radio buttons** for single selection
- Only 3 entities exposed: ingredients, materials, recipes
- Variable `self.view_var` holds selection
- Button text: "Export Context-Rich View..."
- Handler `_export_context_rich()` (lines 1798-1850) handles single selection export

**Current UI Code Pattern**:
```python
self.view_var = ctk.StringVar(value="ingredients")
views = [
    ("ingredients", "Ingredients (with products, inventory totals, costs)"),
    ("materials", "Materials (with hierarchy paths, products)"),
    ("recipes", "Recipes (with ingredients, computed costs)"),
]
for value, label in views:
    rb = ctk.CTkRadioButton(...)
```

**Rationale**: Clear refactoring path - replace radio buttons with checkboxes, add "All" logic.

---

### Q3: What entity types need to be added?

**Decision**: Add Products, Material Products, Finished Units, Finished Goods

**Findings**:
- `export_products_view()` already exists in service - just needs UI exposure
- Need to create: `export_material_products_context_rich()`, `export_finished_units_context_rich()`, `export_finished_goods_context_rich()`
- Reference file `test_data/old_view_products.json` shows expected structure:
  - `_meta.editable_fields`: brand, product_name, package_size, etc.
  - `_meta.readonly_fields`: id, uuid, ingredient_id, ingredient_slug, etc.
  - `records[]`: denormalized product data with context

**Entity Models**:
- `Product` - src/models/product.py
- `MaterialProduct` - src/models/material_product.py
- `FinishedUnit` - src/models/finished_unit.py (yields from recipes)
- `FinishedGood` - src/models/finished_good.py (assembled bundles)

**Rationale**: Follow existing export patterns; all models exist with relationships defined.

---

### Q4: What terminology changes are needed?

**Decision**: Deprecate "view" terminology entirely, use "context-rich" or "aug"

**Changes Required**:
| Location | Current | New |
|----------|---------|-----|
| File prefix | `view_` | `aug_` |
| Method names | `export_*_view()` | `export_*_context_rich()` |
| Variables | `view_var`, `view_type` | `context_rich_var`, etc. |
| UI text | "Context-Rich View" | "Context-Rich File" |
| Constants | `*_VIEW_EDITABLE` | `*_CONTEXT_RICH_EDITABLE` |

**Rationale**: User requested deprecation of "view" due to ambiguity; "context-rich" is clearer.

---

### Q5: How should multi-select export work?

**Decision**: Sequential export with "All" checkbox

**Approach**:
1. Replace radio buttons with checkboxes (one per entity type)
2. Add "All" checkbox at top with separator
3. "All" checked → check all entities; "All" unchecked → uncheck all
4. Individual checkbox changes update "All" state
5. Export button iterates selected entities sequentially
6. Validation: require at least one selection

**Performance**: User confirmed sequential export is acceptable; no parallelism needed.

**Rationale**: Simple implementation, matches user expectations, no performance concerns.

---

## Alternatives Considered

### Multi-select Implementation
- **Option A (Chosen)**: Checkboxes with "All" toggle - standard UI pattern, intuitive
- **Option B**: Listbox with multi-select - more complex, less discoverable
- **Option C**: Dropdown with checkboxes - unconventional for CustomTkinter

### Prefix Change
- **Option A (Chosen)**: `aug_` - short, indicates "augmentation" purpose
- **Option B**: `context_` - longer, more descriptive but verbose
- **Option C**: `enriched_` - accurate but even longer

---

## Dependencies

- CustomTkinter `CTkCheckBox` widget (already available in framework)
- Existing export service patterns (well-established)
- No new external dependencies required
