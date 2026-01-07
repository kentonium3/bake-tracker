# Research: Import/Export v4.0 Upgrade

**Feature**: 040-import-export-v4
**Date**: 2026-01-06
**Status**: Complete

## Executive Summary

Research confirms the import/export upgrade is feasible using existing model structures. Key finding: the design document referenced `yield_mode` on Recipe, but it actually exists on `FinishedUnit`. The v4.0 schema will export/import the Recipe's F037 fields (base_recipe_id, variant_name, is_production_ready) plus linked FinishedUnits with their yield_mode.

## Key Decisions

### D1: Recipe Schema Export Structure

**Decision**: Export Recipe with F037 fields plus embedded FinishedUnits (which contain yield_mode)

**Rationale**:
- Recipe model has: `base_recipe_id`, `variant_name`, `is_production_ready` (F037)
- FinishedUnit model has: `yield_mode` (DISCRETE_COUNT, BATCH_PORTION, WEIGHT_BASED)
- A Recipe can have multiple FinishedUnits, each with its own yield_mode
- Exporting FinishedUnits as part of Recipe maintains relationship integrity

**Alternatives Considered**:
- Add yield_mode directly to Recipe: Rejected - would duplicate FinishedUnit data
- Export FinishedUnits separately: Acceptable but less intuitive for restore

### D2: Event output_mode Integration

**Decision**: Add `output_mode` to Event export with conditional target validation

**Rationale**:
- Event.output_mode is nullable in current model (src/models/event.py:83)
- Values: bulk_count, bundled, packaged (OutputMode enum)
- EventAssemblyTarget and EventProductionTarget already exist in v3.6 exports
- Only change: add output_mode field to event JSON, validate mode matches targets

**Alternatives Considered**: None - straightforward addition

### D3: BT Mobile Import - Separate Entry Points

**Decision**: Create two distinct import functions, not a unified one

**Rationale**:
- `import_purchases_from_bt_mobile()` - creates Purchase + InventoryItem
- `import_inventory_updates_from_bt_mobile()` - modifies existing InventoryItem
- Different validation, different side effects, different error handling
- `import_type` field in JSON distinguishes them for auto-detection

**Alternatives Considered**:
- Single function with mode parameter: Rejected - too many conditionals, harder to test

### D4: UPC Matching Strategy

**Decision**: Query Product.upc_code with exact match, collect unmatched for UI resolution

**Rationale**:
- Product.upc_code exists (src/models/product.py:67), indexed (idx_product_upc)
- Simple equality match is sufficient (UPCs are standardized)
- UI resolution deferred to separate UI component (not part of service layer)

**Alternatives Considered**:
- GTIN fallback: Could add, but UPC is primary use case
- Fuzzy matching: Rejected - UPCs are exact or not

### D5: Percentage Calculation Algorithm

**Decision**: Use linked Purchase.quantity_purchased as original quantity baseline

**Rationale**:
- InventoryItem has purchase_id FK
- Purchase has quantity_purchased (the original amount)
- Formula: target = original * (percentage/100); adjustment = target - current
- FIFO: Query oldest active inventory item first

**Alternatives Considered**:
- Store original quantity on InventoryItem: Would require model change, unnecessary

### D6: Parallelization Strategy

**Decision**: Staged parallel - Part 1 first, then Parts 2+3 in parallel

**Rationale**:
- Part 1 (core schema): Modifies existing export/import functions
- Part 2 (purchase import): New function, no overlap with Part 3
- Part 3 (inventory updates): New function, no overlap with Part 2
- File boundaries:
  - Part 1: `import_export_service.py` existing functions
  - Part 2: New function + new UI dialog file
  - Part 3: New function only (no UI)
- Safe for Claude (Part 2) + Gemini (Part 3) parallel after Part 1 complete

**Alternatives Considered**:
- Full parallel: Risky due to Part 1 shared foundation
- Sequential: Slower, unnecessary given clear boundaries

## Model Analysis

### Current State (v3.6)

| Model | F037/F039 Fields | Export Status |
|-------|------------------|---------------|
| Recipe | base_recipe_id, variant_name, is_production_ready | NOT EXPORTED |
| FinishedUnit | yield_mode | EXPORTED (partial) |
| Event | output_mode | NOT EXPORTED |
| Product | upc_code, gtin | EXPORTED |
| InventoryItem | purchase_id | EXPORTED |
| Purchase | quantity_purchased | EXPORTED |

### Required Changes for v4.0

1. **Recipe export**: Add base_recipe_id, variant_name, is_production_ready
2. **Recipe import**: Handle self-referential base_recipe_id (import base recipes first)
3. **Event export**: Add output_mode field
4. **Event import**: Validate output_mode matches target types
5. **Version bump**: "3.5" -> "4.0" in header

## Integration Points

### Existing Services Used

- `session_scope()` from database.py
- Existing `export_*` and `import_*` helpers
- `ImportResult` and `ExportResult` classes

### New UI Components Needed

- UPC resolution dialog (Part 2 only)
- No UI for Part 3 (fully automated)

## Open Questions

None - all critical questions resolved during research.

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Recipe circular reference on import | Low | High | Import in dependency order: base recipes before variants |
| UPC not found in DB | Medium | Low | Resolution UI handles gracefully |
| Percentage calc precision errors | Low | Low | Use Decimal throughout |
| Parallel development conflicts | Low | Medium | Clear file boundaries documented |

## References

- `docs/design/_F040_import_export_upgrade.md` - Design specification
- `docs/design/spec_import_export.md` - Current import/export spec (v4.0 updated)
- `src/models/recipe.py` - Recipe model with F037 fields
- `src/models/event.py` - Event model with output_mode
- `src/models/product.py` - Product model with upc_code
