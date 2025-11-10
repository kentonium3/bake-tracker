# Implementation Plan: Phase 4 UI Completion

**Feature**: 003-phase4-ui-completion
**Created**: 2025-11-10
**Status**: Planning

---

## Overview

Complete Phase 4 of the Ingredient/Variant refactor by implementing UI components for My Ingredients and My Pantry tabs, executing data migration, and integrating with existing recipe/event functionality.

---

## Work Package Breakdown

### WP01: My Ingredients Tab - Ingredient Catalog CRUD ✅

**Goal**: Create My Ingredients tab with basic ingredient catalog management (list, add, edit, delete)

**Tasks**:
- [ ] Create `src/ui/ingredients_tab.py` with tab frame structure
- [ ] Implement ingredient list view (CTkScrollableFrame with table)
- [ ] Add search bar widget (filter by name)
- [ ] Add category filter dropdown
- [ ] Create "Add Ingredient" form dialog
  - [ ] Fields: Name, Category, Recipe Unit, Density (optional)
  - [ ] Validation: required fields, numeric constraints
  - [ ] Call ingredient_service.create_ingredient()
- [ ] Create "Edit Ingredient" form dialog
  - [ ] Pre-populate with current values
  - [ ] Call ingredient_service.update_ingredient()
- [ ] Implement delete with confirmation
  - [ ] Handle NotFound and ValidationError exceptions
  - [ ] Display dependency warnings
- [ ] Add to main_window.py tabbed interface
- [ ] Test CRUD operations through UI

**Dependencies**: None (service layer complete)

**Estimated Effort**: 12-15 hours

**Acceptance**:
- User can view list of ingredients
- User can add new ingredient
- User can edit existing ingredient
- User can delete ingredient (with dependency check)
- Search and filter work correctly

---

### WP02: My Ingredients Tab - Variant Management ✅

**Goal**: Add variant management interface within My Ingredients tab (view/add/edit/delete variants per ingredient)

**Tasks**:
- [ ] Add "View Variants" button to ingredient list rows
- [ ] Create variants panel/dialog that opens when ingredient selected
- [ ] Implement variant list view for selected ingredient
  - [ ] Display: brand, package size, preferred indicator, pantry total
  - [ ] Sort with preferred variant first
- [ ] Create "Add Variant" form dialog
  - [ ] Fields: Brand, Package Size, Purchase Unit, Purchase Quantity, UPC, Supplier
  - [ ] Call variant_service.create_variant()
- [ ] Create "Edit Variant" form dialog
  - [ ] Pre-populate with current values
  - [ ] Call variant_service.update_variant()
- [ ] Implement "Mark as Preferred" toggle button
  - [ ] Call variant_service.toggle_preferred_variant()
  - [ ] Update UI to show preferred indicator (star/check icon)
- [ ] Implement delete variant with confirmation
  - [ ] Handle pantry dependency errors
- [ ] Display total pantry quantity per variant
  - [ ] Call variant.get_total_pantry_quantity() or pantry_service
- [ ] Test variant CRUD through UI

**Dependencies**: WP01 (ingredient list must exist)

**Estimated Effort**: 10-12 hours

**Acceptance**:
- User can view variants for selected ingredient
- User can add new variant
- User can edit existing variant
- User can mark variant as preferred (toggle works atomically)
- User can delete variant (with pantry dependency check)
- Preferred indicator displays correctly
- Pantry totals display correctly

---

### WP03: My Pantry Tab - Inventory Display & Management ✅

**Goal**: Create My Pantry tab with inventory list view (aggregate and detail modes) and add/edit/delete pantry items

**Tasks**:
- [ ] Create `src/ui/pantry_tab.py` with tab frame structure
- [ ] Implement view mode toggle (Aggregate vs Detail)
  - [ ] Aggregate: group by ingredient, show total quantities
  - [ ] Detail: show individual pantry items (variant, lot, dates)
- [ ] Implement aggregate view
  - [ ] Call pantry_service to get quantities grouped by ingredient
  - [ ] Display: ingredient name, total quantity in recipe units
  - [ ] Expandable rows to show detail breakdown
- [ ] Implement detail view
  - [ ] Call pantry_service.get_pantry_items()
  - [ ] Display: variant name, quantity, purchase date, expiration, location
  - [ ] Sort by purchase date (oldest first - FIFO order)
- [ ] Add location filter dropdown
  - [ ] Filter pantry items by selected location
- [ ] Implement expiration alerts
  - [ ] Yellow highlight for items expiring within 14 days
  - [ ] Red highlight for expired items
  - [ ] Warning icons/badges
- [ ] Create "Add Pantry Item" form dialog
  - [ ] Fields: Ingredient (dropdown), Variant (filtered by ingredient), Quantity, Purchase Date, Expiration, Location, Notes
  - [ ] Call pantry_service.add_to_pantry()
- [ ] Create "Edit Pantry Item" form dialog
  - [ ] Pre-populate current values
  - [ ] Call pantry_service.update_pantry_item()
- [ ] Implement delete with confirmation
  - [ ] Call pantry_service.delete_pantry_item()
- [ ] Test pantry CRUD through UI

**Dependencies**: WP02 (needs variants to reference)

**Estimated Effort**: 12-15 hours

**Acceptance**:
- User can view pantry in aggregate mode
- User can view pantry in detail mode
- User can filter by location
- Expiration alerts display correctly (yellow/red highlighting)
- User can add pantry item
- User can edit pantry item
- User can delete pantry item
- FIFO ordering visible (oldest first)

---

### WP04: My Pantry Tab - FIFO Consumption Interface ✅

**Goal**: Add FIFO consumption interface and consumption history display

**Tasks**:
- [ ] Add "Consume Ingredient" button to My Pantry tab
- [ ] Create consumption dialog
  - [ ] Ingredient selector dropdown
  - [ ] Quantity input with unit display (ingredient's recipe unit)
  - [ ] Preview panel showing which lots will be consumed
- [ ] Implement consumption preview
  - [ ] Call pantry_service to preview FIFO consumption
  - [ ] Display breakdown: lot date, quantity from each lot
- [ ] Implement consumption execution
  - [ ] Call pantry_service.consume_fifo()
  - [ ] Display success message with consumption breakdown
  - [ ] Refresh pantry display
- [ ] Handle insufficient inventory scenario
  - [ ] Display warning with shortfall amount
  - [ ] Option to proceed with partial consumption or cancel
- [ ] Create "Consumption History" sub-tab or panel
  - [ ] Display log of past consumptions
  - [ ] Show: date, ingredient, quantity, breakdown by lot
  - [ ] Date range filter (e.g., "Last 30 days")
- [ ] Visual FIFO ordering indicator
  - [ ] Number or icon showing FIFO order in detailed view
  - [ ] Tooltip explaining "Oldest inventory will be used first"
- [ ] Test FIFO consumption through UI with multiple lots

**Dependencies**: WP03 (pantry display must exist)

**Estimated Effort**: 8-10 hours

**Acceptance**:
- User can consume ingredients via UI
- FIFO preview shows correct lots and quantities
- Consumption updates pantry correctly
- Insufficient inventory warning works
- Consumption history displays correctly
- FIFO visual indicators help users understand ordering

---

### WP05: Migration Execution & Wizard ✅

**Goal**: Create migration wizard UI for executing v0.3.0 → v0.4.0 data migration with dry-run, progress tracking, and validation

**Tasks**:
- [ ] Create migration wizard window/dialog
  - [ ] Welcome screen explaining migration
  - [ ] Warnings about backing up database
- [ ] Implement "Dry Run" button
  - [ ] Call migration script with dry_run=True
  - [ ] Display preview report
  - [ ] Show: ingredients to create, variants to create, pantry items, recipes to update
- [ ] Implement "Execute Migration" button
  - [ ] Confirmation dialog with backup warning
  - [ ] Call migration script with dry_run=False
- [ ] Add progress indicator
  - [ ] Progress bar showing current phase
  - [ ] Status text (e.g., "Creating ingredients... 45/83")
  - [ ] Update UI as migration progresses
- [ ] Display migration results
  - [ ] Summary: ingredients created, variants created, pantry items created, recipes updated
  - [ ] Validation results (data integrity checks)
  - [ ] Cost comparison table (old vs new costs for sample recipes)
- [ ] Handle migration errors
  - [ ] Display error messages clearly
  - [ ] Advise user to restore from backup
  - [ ] Log detailed error information
- [ ] Add migration to Settings/Tools menu
  - [ ] Only show if v0.3.0 schema detected
  - [ ] Hide after successful migration
- [ ] Test migration on sample database copy

**Dependencies**: WP01-WP04 (UI should be ready before migrating data)

**Estimated Effort**: 10-12 hours

**Acceptance**:
- Dry run generates accurate preview
- Migration wizard is accessible from Settings/Tools
- Progress indicator updates during migration
- Migration completes successfully on test database
- Validation report shows data integrity maintained
- Cost comparison shows minimal differences
- Error handling works (displays clear messages)
- Users are prompted to backup before migration

---

### WP06: Integration & Cross-Tab Functionality ✅

**Goal**: Integrate new tabs with existing Recipe and Events tabs, ensuring seamless workflow

**Tasks**:
- [ ] Update Recipe tab ingredient selector
  - [ ] Replace old ingredient selector with new one
  - [ ] Show generic ingredients (not variants)
  - [ ] Link recipes to ingredient via ingredient_id
- [ ] Update recipe cost calculation
  - [ ] Integrate with pantry_service.consume_fifo() for cost calculation
  - [ ] Fallback to preferred variant pricing if pantry empty
  - [ ] Display cost breakdown showing source (FIFO vs preferred)
- [ ] Update Events tab shopping list
  - [ ] Show preferred variant recommendations
  - [ ] Display: ingredient name + "Recommended: [Preferred Variant]"
  - [ ] Link to variant in My Ingredients tab
- [ ] Add "Used in Recipes" functionality to My Pantry
  - [ ] Button/link on ingredient shows which recipes use it
  - [ ] Navigate to Recipe tab with filter applied
- [ ] Add navigation between tabs
  - [ ] Click variant in shopping list → opens My Ingredients with that variant highlighted
  - [ ] Click ingredient in recipe → opens My Ingredients with that ingredient selected
- [ ] Update main_window.py tab ordering
  - [ ] Order: Dashboard, My Ingredients, My Pantry, Recipes, Finished Goods, Bundles, Packages, Recipients, Events, Reports
- [ ] Deprecate/remove old inventory_tab.py
  - [ ] Ensure no references to old tab remain
  - [ ] Update any existing bookmarks/shortcuts
- [ ] End-to-end workflow testing
  - [ ] Create ingredient → add variant → add pantry item → create recipe → generate shopping list
  - [ ] Verify cost calculations match expected values

**Dependencies**: WP01-WP05 (all new UI must be complete)

**Estimated Effort**: 8-10 hours

**Acceptance**:
- Recipe tab uses new ingredient selector (generic ingredients)
- Recipe costs calculated using FIFO or preferred variant
- Shopping lists show preferred variant recommendations
- Navigation between tabs works seamlessly
- "Used in Recipes" links work
- Old inventory_tab.py removed
- Full workflow test passes

---

## Implementation Order

1. **WP01** → My Ingredients basics (foundation)
2. **WP02** → Variant management (extends WP01)
3. **WP03** → My Pantry display (uses variants from WP02)
4. **WP04** → FIFO consumption (extends WP03)
5. **WP05** → Migration wizard (uses all new UI for validation)
6. **WP06** → Integration (ties everything together)

---

## Testing Strategy

### Unit Testing
- Form validation logic
- Error message formatting
- Widget state management

### Integration Testing
- UI → Service layer calls
- Service error handling in UI
- Data refresh after operations

### Manual Testing
- Execute all user scenarios from spec.md
- Test error conditions (network issues, validation failures)
- Test with large datasets (performance)
- Test migration on sample database

### User Acceptance Testing
- Complete workflow: ingredient → variant → pantry → recipe → event
- Verify costs match expectations
- Confirm UI is intuitive and clear
- Check error messages are helpful

---

## Success Criteria Summary

Phase 4 UI Complete when:
- ✅ All 6 work packages marked complete
- ✅ All user scenarios from spec.md pass
- ✅ Migration executes successfully on test database
- ✅ No regressions in existing functionality
- ✅ Cost calculations accurate (FIFO vs preferred variant)
- ✅ User can complete full workflow end-to-end
- ✅ Documentation updated (user guide + architecture docs)

---

## Risks & Mitigation

**Risk**: Migration causes data loss
- **Mitigation**: Mandatory dry-run before execution, backup prompts, validation checks

**Risk**: UI performance issues with large datasets
- **Mitigation**: Pagination, lazy loading, query optimization with eager loading

**Risk**: User confusion between ingredient vs variant
- **Mitigation**: Clear labels, tooltips, help documentation, onboarding guide

**Risk**: Cost discrepancies between old and new architecture
- **Mitigation**: Side-by-side comparison in migration report, detailed cost breakdown in UI

---

## Dependencies & Prerequisites

**External Dependencies**: None

**Internal Dependencies**:
- ✅ Ingredient, Variant, PantryItem, Purchase models (complete)
- ✅ ingredient_service, variant_service, pantry_service, purchase_service (complete)
- ✅ Migration script (complete)
- ✅ CustomTkinter UI framework (available)

**Blockers**: None

---

## Timeline

**Estimated Total**: 60-90 hours (2-3 weeks for single developer)

**Week 1**: WP01 + WP02 (ingredient catalog + variants)
**Week 2**: WP03 + WP04 (pantry display + FIFO)
**Week 3**: WP05 + WP06 (migration + integration)

**Buffer**: +20% for bug fixes, testing, documentation

---

## Next Steps

1. Create work package files in `tasks/doing/`
2. Start with WP01 (My Ingredients Tab - Basic CRUD)
3. Commit frequently with descriptive messages
4. Move WP to `tasks/done/` when complete
5. Update this plan.md as work progresses
