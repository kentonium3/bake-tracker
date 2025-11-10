---
id: WP02
title: My Ingredients Tab - Variant Management
feature: 003-phase4-ui-completion
lane: planned
priority: P2
estimate: 10-12 hours
assignee: ""
agent: ""
shell_pid: ""
tags:
  - ui
  - variants
  - customtkinter
dependencies:
  - WP01
history:
  - timestamp: "2025-11-10T18:01:00Z"
    lane: "planned"
    agent: ""
    shell_pid: ""
    action: "Work package created"
---

# WP02: My Ingredients Tab - Variant Management

## Objective

Add variant management interface to My Ingredients tab. Users can view, add, edit, and delete brand-specific variants for each ingredient, mark preferred variants, and see pantry totals.

## Scope

- Add variant panel/dialog to ingredients_tab.py
- Implement variant list for selected ingredient
- Create variant CRUD forms
- Implement preferred variant toggle
- Display pantry totals per variant

## Tasks

- [ ] Add "View Variants" button to each ingredient row in list
- [ ] Create variants panel/dialog component
  - [ ] Opens when ingredient selected
  - [ ] Shows variants for that ingredient only
  - [ ] Empty state: "No variants. Click 'Add Variant' to create one."
- [ ] Implement variant list view
  - [ ] Columns: Brand, Package Size, UPC, Supplier, Preferred (indicator), Pantry Total, Actions
  - [ ] Sort: preferred first, then alphabetically
- [ ] Create "Add Variant" form dialog
  - [ ] Fields: Brand (required), Package Size (display), Purchase Unit (required), Purchase Quantity (required), UPC/GTIN (optional), Supplier (optional)
  - [ ] Validation: non-empty brand, quantity > 0
  - [ ] Call variant_service.create_variant(ingredient_id, data)
  - [ ] Handle exceptions
- [ ] Create "Edit Variant" form dialog
  - [ ] Pre-populate with current values
  - [ ] Call variant_service.update_variant(variant_id, data)
- [ ] Implement "Mark as Preferred" toggle
  - [ ] Star/check icon button
  - [ ] Call variant_service.toggle_preferred_variant(variant_id)
  - [ ] Refresh list to show new preferred at top
- [ ] Display total pantry quantity for each variant
  - [ ] Call variant.get_total_pantry_quantity() or pantry_service
  - [ ] Show in "Pantry Total" column
  - [ ] Unit: variant's purchase_unit
- [ ] Implement delete variant
  - [ ] Confirmation dialog
  - [ ] Call variant_service.delete_variant(variant_id)
  - [ ] Handle dependency error (pantry items exist)
- [ ] Test variant CRUD through UI

## Technical Notes

**Service Methods:**
- `variant_service.get_variants_by_ingredient(ingredient_id)` - list
- `variant_service.create_variant(ingredient_id, data)` - create
- `variant_service.get_variant(variant_id)` - read for edit
- `variant_service.update_variant(variant_id, data)` - update
- `variant_service.toggle_preferred_variant(variant_id)` - preferred toggle
- `variant_service.delete_variant(variant_id)` - delete

**Preferred Variant Logic:**
- Only one variant per ingredient can be preferred
- Toggle is atomic (service handles un-setting others)
- UI shows preferred indicator (star/check icon)

## Acceptance Criteria

- [ ] User can view variants for selected ingredient
- [ ] User can add new variant
- [ ] User can edit existing variant
- [ ] User can toggle preferred variant (one preferred per ingredient)
- [ ] User can delete variant without pantry items
- [ ] Deletion blocked when variant has pantry items
- [ ] Pantry totals display correctly
- [ ] Preferred indicator shows correctly
- [ ] Variants sorted with preferred first

## Testing Checklist

- [ ] Add variant to ingredient → success
- [ ] Add multiple variants to same ingredient → all appear
- [ ] Mark variant as preferred → indicator shows, others cleared
- [ ] Toggle preferred between variants → works correctly
- [ ] Edit variant brand → saves correctly
- [ ] Delete variant with no pantry items → succeeds
- [ ] Delete variant with pantry items → error message
- [ ] Pantry total displays correct quantity

## Files to Modify

- `src/ui/ingredients_tab.py` (add variant management)

## Dependencies

**Requires:**
- ✅ WP01 (ingredient list must exist)
- ✅ variant_service.py (complete)

**Blocks:**
- WP03 (Pantry tab needs variants)

## Estimated Effort

10-12 hours

## Activity Log

- 2025-11-10 – Claude Code – lane=planned – Work package created
