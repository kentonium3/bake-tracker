---
title: My Ingredients Tab - Variant Management
lane: done
priority: P2
tags:
- ui
- variants
- customtkinter
history:
- timestamp: '2025-11-10T18:01:00Z'
  lane: planned
  agent: Claude Code
  shell_pid: '1'
  action: Work package created
- timestamp: '2025-11-10T17:51:41Z'
  lane: done
  agent: Claude Code
  shell_pid: '1'
  action: Work package completed - all variant management features implemented and committed
agent: Claude Code
assignee: Claude Code
dependencies:
- WP01
estimate: 10-12 hours
feature: 003-phase4-ui-completion
id: WP02
shell_pid: '1'
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

- [x] Add "View Variants" button to each ingredient row in list
- [x] Create variants panel/dialog component
  - [x] Opens when ingredient selected
  - [x] Shows variants for that ingredient only
  - [x] Empty state: "No variants. Click 'Add Variant' to create one."
- [x] Implement variant list view
  - [x] Columns: Brand, Package Size, UPC, Supplier, Preferred (indicator), Pantry Total, Actions
  - [x] Sort: preferred first, then alphabetically
- [x] Create "Add Variant" form dialog
  - [x] Fields: Brand (required), Package Size (display), Purchase Unit (required), Purchase Quantity (required), UPC/GTIN (optional), Supplier (optional)
  - [x] Validation: non-empty brand, quantity > 0
  - [x] Call variant_service.create_variant(ingredient_id, data)
  - [x] Handle exceptions
- [x] Create "Edit Variant" form dialog
  - [x] Pre-populate with current values
  - [x] Call variant_service.update_variant(variant_id, data)
- [x] Implement "Mark as Preferred" toggle
  - [x] Star/check icon button
  - [x] Call variant_service.toggle_preferred_variant(variant_id)
  - [x] Refresh list to show new preferred at top
- [x] Display total pantry quantity for each variant
  - [x] Call variant.get_total_pantry_quantity() or pantry_service
  - [x] Show in "Pantry Total" column
  - [x] Unit: variant's purchase_unit
- [x] Implement delete variant
  - [x] Confirmation dialog
  - [x] Call variant_service.delete_variant(variant_id)
  - [x] Handle dependency error (pantry items exist)
- [x] Test variant CRUD through UI

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

- [x] User can view variants for selected ingredient
- [x] User can add new variant
- [x] User can edit existing variant
- [x] User can toggle preferred variant (one preferred per ingredient)
- [x] User can delete variant without pantry items
- [x] Deletion blocked when variant has pantry items
- [x] Pantry totals display correctly
- [x] Preferred indicator shows correctly
- [x] Variants sorted with preferred first

## Testing Checklist

- [x] Add variant to ingredient → success
- [x] Add multiple variants to same ingredient → all appear
- [x] Mark variant as preferred → indicator shows, others cleared
- [x] Toggle preferred between variants → works correctly
- [x] Edit variant brand → saves correctly
- [x] Delete variant with no pantry items → succeeds
- [x] Delete variant with pantry items → error message
- [x] Pantry total displays correct quantity

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
- 2025-11-10T17:51:41Z – Claude Code – lane=done – Work package completed. All variant management features implemented, tested, and committed.

