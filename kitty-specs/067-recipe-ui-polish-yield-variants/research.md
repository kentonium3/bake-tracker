# Research: F067 Recipe UI Polish - Yield Information and Variant Grouping

**Date**: 2026-01-25
**Feature**: 067-recipe-ui-polish-yield-variants

## Research Questions

### Q1: What grid technology is used for Recipe Catalog and Finished Units?

**Finding**: Both grids use a custom **CTkFrame-based DataTable** class, NOT CTkTreeview.

| Component | File | Class | Type |
|-----------|------|-------|------|
| Recipe Catalog | `src/ui/widgets/data_table.py:336` | `RecipeDataTable(DataTable)` | Flat CTkFrame table |
| Finished Units | `src/ui/widgets/data_table.py:396` | `FinishedGoodDataTable(DataTable)` | Flat CTkFrame table |

**Current Structure**:
- Base `DataTable` class creates rows as `CTkFrame` children in a `CTkScrollableFrame`
- No built-in hierarchy/tree support
- Variant relationships exist in database (`base_recipe_id`) but display as flat peers

### Q2: How should hierarchical variant grouping be implemented?

**Decision**: Add visual grouping within existing DataTable framework (no CTkTreeview migration).

**Rationale**:
- Converting to CTkTreeview would require significant refactoring of selection handling, callbacks, and styling
- The existing DataTable can support visual grouping via:
  1. Sorting recipes with variants immediately after their base
  2. Adding "↳ " prefix to variant names in the display
- This approach is simpler, maintains existing patterns, and achieves the spec requirements

**Alternatives Considered**:
1. **CTkTreeview migration** - Rejected: High effort, existing DataTable works well for other features
2. **Collapsible tree component** - Rejected: Overkill for simple parent-child display
3. **Visual indentation in flat list** - **Selected**: Low effort, meets requirements

### Q3: Current state of yield editor and variant dialog

**Recipe Form Dialog** (`src/ui/forms/recipe_form.py`):
- Yield section at lines 730-798
- Uses `YieldTypeRow` widget for each yield entry
- Already has F066 variant handling (readonly structure, inheritance note)
- **Gap**: No column labels above yield inputs
- **Gap**: Help text says "Description, Unit, Qty/batch" but spec wants specific labels

**Variant Creation Dialog** (`src/ui/forms/variant_creation_dialog.py`):
- Section header is "Variant Yields:" (spec wants "Finished Unit Name(s):")
- Each row has "Base: {name}" label (spec says remove "Base:" labels)
- Layout uses 2-column grid: label | entry

## Implementation Approach

### Recipe Catalog Grid Changes

1. **Modify `_load_data()` or data retrieval** to sort recipes:
   - Base recipes first (alphabetically)
   - Variants grouped under their base (sorted alphabetically within group)

2. **Modify `_get_row_values()`** to add "↳ " prefix for variants:
   ```python
   name = row_data.name
   if row_data.base_recipe_id:
       name = f"↳ {name}"
   ```

### Finished Units Grid Changes

1. **Modify data retrieval** to group by base recipe relationship
2. **Add visual indicator** for variant-sourced finished units

### Recipe Form Dialog Changes

1. **Add column labels** row above yield inputs:
   - "Finished Unit Name" | "Unit" | "Qty/Batch"

2. **Update help text** to match spec wording

3. **Reduce whitespace** after section title

### Variant Creation Dialog Changes

1. **Change section header** from "Variant Yields:" to "Finished Unit Name(s):"
2. **Remove "Base:" prefix** from row labels
3. **Adjust label placement** per layout requirements

### New Recipe Default Changes

1. **Set `production_ready=True`** as default in new recipe creation

## Files to Modify

| File | Changes |
|------|---------|
| `src/ui/widgets/data_table.py` | RecipeDataTable: sorting, variant prefix |
| `src/ui/widgets/data_table.py` | FinishedGoodDataTable: sorting, variant prefix |
| `src/ui/forms/recipe_form.py` | Column labels, help text, spacing |
| `src/ui/forms/variant_creation_dialog.py` | Section title, remove "Base:" labels |
| `src/ui/forms/recipe_form.py` | Default production_ready=True |

## Risk Assessment

**Low Risk**:
- All changes are UI-layer only
- No service or model modifications
- No database schema changes
- Existing tests should continue to pass
- Visual changes are additive (don't break existing functionality)

**Testing Considerations**:
- Manual UI testing required for visual verification
- Existing service tests unaffected
- May want snapshot tests for dialog layouts (future consideration)
