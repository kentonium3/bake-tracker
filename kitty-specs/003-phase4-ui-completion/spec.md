# Feature Specification: Phase 4 UI Completion - My Ingredients & My Pantry

**Feature Branch**: `003-phase4-ui-completion`
**Created**: 2025-11-10
**Status**: Draft
**Input**: Complete Phase 4 UI implementation for Ingredient/Variant/Pantry architecture with data migration execution

## User Scenarios & Testing *(mandatory)*

### User Story 1 - My Ingredients Tab: Ingredient Catalog Management (Priority: P1)

Users can view, search, filter, add, edit, and delete generic ingredients in the catalog. The interface displays ingredient name, category, recipe unit, and density. Users can search by name or filter by category. The system prevents deletion of ingredients referenced by variants or recipes.

**Why this priority**: Foundation UI for the new architecture. Without the ability to manage ingredients through the UI, users cannot interact with the refactored data model, blocking all downstream functionality (variants, pantry, recipes).

**Independent Test**: Can be tested by opening the My Ingredients tab, creating/editing/deleting ingredients through the UI, and verifying the interface correctly calls ingredient_service methods. Delivers immediate value by enabling users to manage their ingredient catalog.

**Acceptance Scenarios**:

1. **Given** user opens My Ingredients tab, **When** no ingredients exist, **Then** UI displays empty state message "No ingredients found. Click 'Add Ingredient' to get started"
2. **Given** user clicks "Add Ingredient" button, **When** form opens, **Then** UI displays fields: Name, Category, Recipe Unit, Density (g/ml), optional industry standard fields
3. **Given** user enters "All-Purpose Flour" in name field and "Flour" in category, **When** user clicks Save, **Then** system generates slug, creates ingredient, displays success message, and refreshes ingredient list
4. **Given** ingredient list contains "All-Purpose Flour", "Bread Flour", "Sugar", **When** user types "flour" in search box, **Then** UI filters list to show only "All-Purpose Flour" and "Bread Flour"
5. **Given** user selects "Flour" category filter, **When** filter is applied, **Then** UI displays only ingredients in "Flour" category
6. **Given** user selects "All-Purpose Flour" from list, **When** user clicks Edit, **Then** form opens with current values pre-populated
7. **Given** user edits ingredient density from 0.48 to 0.50 g/ml, **When** user saves, **Then** system updates ingredient and refreshes display
8. **Given** ingredient "All-Purpose Flour" has variants defined, **When** user attempts to delete ingredient, **Then** UI displays error "Cannot delete ingredient with existing variants. Delete variants first."
9. **Given** ingredient has no variants or recipes, **When** user deletes ingredient after confirmation, **Then** system removes ingredient and refreshes list

---

### User Story 2 - My Ingredients Tab: Variant Management (Priority: P2)

Users can view, add, edit, and delete brand-specific variants for each ingredient. The interface shows variant details (brand, package size, UPC, supplier) and allows marking a preferred variant. Users can see total pantry quantity for each variant.

**Why this priority**: Enables multi-brand tracking which is the key value proposition of the refactor. Users need to define which brands/packages they purchase before they can track inventory.

**Independent Test**: Can be tested by selecting an ingredient and managing its variants through the UI. Verifies UI correctly calls variant_service methods and displays variant properties. Delivers value by enabling brand/package definition.

**Acceptance Scenarios**:

1. **Given** user selects "All-Purpose Flour" in My Ingredients tab, **When** user clicks "View Variants" button, **Then** UI displays list of variants for that ingredient (or empty state if none exist)
2. **Given** variants list is displayed, **When** user clicks "Add Variant", **Then** form opens with fields: Brand, Package Size, Purchase Unit, Purchase Quantity, UPC/GTIN, Supplier
3. **Given** user enters "King Arthur" brand, "25" quantity, "lb" unit, **When** user saves, **Then** system creates variant, calculates display name "King Arthur - 25 lb", links to ingredient, and refreshes variant list
4. **Given** ingredient has 3 variants, **When** user clicks "Mark as Preferred" on one variant, **Then** UI shows checkmark/star indicator on preferred variant and removes it from others
5. **Given** variant list is displayed, **When** UI shows each variant, **Then** display includes: brand, package size, preferred indicator, total pantry quantity (aggregated from pantry items)
6. **Given** user selects variant, **When** user clicks Edit, **Then** form opens with current values
7. **Given** user edits variant brand from "King Arthur" to "King Arthur Baking Co.", **When** user saves, **Then** system updates variant and recalculates display name
8. **Given** variant has pantry items, **When** user attempts to delete variant, **Then** UI displays error "Cannot delete variant with existing pantry items. Remove inventory first."
9. **Given** variant has no pantry items, **When** user deletes variant after confirmation, **Then** system removes variant and refreshes list

---

### User Story 3 - My Pantry Tab: Inventory Display & Management (Priority: P3)

Users can view current pantry inventory aggregated by ingredient or detailed by variant/lot. The interface allows adding new pantry items with purchase date, expiration, and location. Users can filter by location and see expiration alerts.

**Why this priority**: Provides visibility into actual inventory using the new architecture. Users need to see what they have in stock before they can plan recipes or events.

**Independent Test**: Can be tested by opening My Pantry tab, adding pantry items for different variants, and verifying display modes (aggregated vs detailed). Tests pantry_service integration. Delivers value by showing current inventory.

**Acceptance Scenarios**:

1. **Given** user opens My Pantry tab, **When** no pantry items exist, **Then** UI displays empty state message "No pantry inventory. Click 'Add Pantry Item' to record purchases"
2. **Given** user clicks "Add Pantry Item", **When** form opens, **Then** UI displays fields: Ingredient (dropdown), Variant (dropdown filtered by ingredient), Quantity, Purchase Date, Expiration Date, Location, Notes
3. **Given** user selects "All-Purpose Flour" ingredient and "King Arthur - 25 lb" variant, enters quantity "25", purchase date "2025-11-01", **When** user saves, **Then** system creates pantry item and refreshes display
4. **Given** pantry contains multiple items, **When** view mode is "Aggregate by Ingredient", **Then** UI displays list grouped by ingredient showing total quantity in recipe units
5. **Given** pantry view is aggregated, **When** user clicks on "All-Purpose Flour" row, **Then** UI expands to show detail view with all lots/variants for that ingredient
6. **Given** view mode is "Detail by Variant", **When** UI displays pantry items, **Then** each row shows: variant name, quantity, purchase date, expiration date, location, actions
7. **Given** user filters by location "Main Pantry", **When** filter is applied, **Then** UI shows only pantry items in that location
8. **Given** pantry item has expiration date within 14 days, **When** UI displays item, **Then** row is highlighted in yellow/orange with warning icon
9. **Given** pantry item is expired, **When** UI displays item, **Then** row is highlighted in red with "EXPIRED" badge
10. **Given** user selects pantry item, **When** user clicks Edit, **Then** form opens with current values
11. **Given** user updates quantity from 25 to 20, **When** user saves, **Then** system updates pantry item and refreshes display
12. **Given** user selects pantry item, **When** user clicks Delete after confirmation, **Then** system removes pantry item and refreshes inventory

---

### User Story 4 - My Pantry Tab: FIFO Consumption Interface (Priority: P4)

Users can consume ingredients from pantry using FIFO logic through the UI. The interface shows consumption history and allows manual consumption recording. Users can see which lots will be consumed first based on purchase dates.

**Why this priority**: Enables testing and using FIFO consumption from the UI, validating the core algorithm works correctly. Required for accurate cost tracking when recipes use ingredients.

**Independent Test**: Can be tested by creating multiple pantry items with different purchase dates, then consuming a quantity and verifying oldest lots are consumed first. Tests pantry_service.consume_fifo() integration.

**Acceptance Scenarios**:

1. **Given** My Pantry tab is open with ingredient "All-Purpose Flour" having 3 lots, **When** user clicks "Consume Ingredient", **Then** dialog opens with ingredient selector and quantity input
2. **Given** consume dialog is open, **When** user selects "All-Purpose Flour" and enters quantity "10 cups", **Then** UI shows preview: "Will consume from 2 lots: Lot 1 (8 cups), Lot 2 (2 cups)"
3. **Given** user confirms consumption, **When** system processes request, **Then** pantry_service.consume_fifo() is called, quantities are updated, and UI displays success message with breakdown
4. **Given** ingredient has insufficient inventory, **When** user attempts to consume more than available, **Then** UI displays warning "Insufficient inventory. Available: 15 cups, Requested: 20 cups. Shortfall: 5 cups"
5. **Given** user expands ingredient in pantry view, **When** multiple lots exist, **Then** UI displays lots ordered by purchase date (oldest first) with visual indicator of FIFO order
6. **Given** My Pantry tab is open, **When** user clicks "Consumption History" tab, **Then** UI displays log of past consumptions with date, ingredient, quantity, and breakdown by lot
7. **Given** consumption history is displayed, **When** user filters by date range "Last 30 days", **Then** UI shows only consumptions within that period

---

### User Story 5 - Data Migration Execution (Priority: P5)

Users can execute the data migration from v0.3.0 schema to v0.4.0 Ingredient/Variant architecture through a migration wizard. The interface provides dry-run preview, progress tracking, and validation reporting.

**Why this priority**: Critical for transitioning existing users to the new architecture. Must be executed after UI is ready and tested. Includes rollback capability for safety.

**Independent Test**: Can be tested with backup database copy. Verify dry-run shows accurate preview, actual migration succeeds, and validation confirms data integrity. Tests migration script integration.

**Acceptance Scenarios**:

1. **Given** user opens Settings/Tools menu, **When** user selects "Migration Wizard", **Then** UI displays migration welcome screen explaining v0.3.0 → v0.4.0 changes
2. **Given** migration wizard is open, **When** user clicks "Run Dry Run", **Then** system executes migration script with dry_run=True and displays preview report
3. **Given** dry run report is displayed, **When** report shows summary, **Then** UI displays: ingredients to create, variants to create, pantry items to create, recipe references to update
4. **Given** dry run completed successfully, **When** user clicks "Execute Migration", **Then** UI displays confirmation dialog warning "This will modify your database. Backup recommended."
5. **Given** user confirms migration, **When** migration executes, **Then** UI displays progress bar with current step (e.g., "Creating ingredients... 45/83")
6. **Given** migration is running, **When** each phase completes, **Then** UI updates progress indicator and shows phase results
7. **Given** migration completes successfully, **When** final report displays, **Then** UI shows: total ingredients created, variants created, pantry items created, recipes updated, and validation results
8. **Given** migration report shows validation passed, **When** report includes cost comparison, **Then** UI displays side-by-side: old costs vs new costs for sample recipes
9. **Given** migration encounters error, **When** error occurs, **Then** UI displays error message, migration halts, and user is advised to restore from backup
10. **Given** migration completed, **When** user returns to My Ingredients tab, **Then** UI displays migrated ingredients and variants

---

### User Story 6 - Integration with Existing Tabs (Priority: P6)

Users can navigate seamlessly between new tabs (My Ingredients, My Pantry) and existing tabs (Recipes, Events). Recipe creation uses new ingredient selector. Shopping lists show preferred variants.

**Why this priority**: Ensures end-to-end integration of Phase 4 UI with existing functionality. Users need to see the new architecture working within their complete workflow.

**Independent Test**: Can be tested by creating a recipe using the ingredient selector, then viewing shopping list to verify preferred variants are shown. Tests cross-tab integration.

**Acceptance Scenarios**:

1. **Given** user is in Recipe tab adding ingredients, **When** user clicks "Add Ingredient", **Then** selector shows list of generic ingredients (not variants)
2. **Given** ingredient selector is open, **When** user selects "All-Purpose Flour", **Then** recipe links to generic ingredient (not specific brand)
3. **Given** recipe is saved with "All-Purpose Flour", **When** recipe cost is calculated, **Then** system uses FIFO from pantry or preferred variant pricing
4. **Given** user is viewing recipe cost, **When** cost breakdown is displayed, **Then** UI shows: ingredient name, quantity needed, unit cost source (FIFO or preferred variant), total cost
5. **Given** user is in Events tab planning an event, **When** shopping list is generated, **Then** UI displays ingredients with preferred variant recommendations
6. **Given** shopping list shows "All-Purpose Flour" needed, **When** user views details, **Then** UI displays: "Recommended: King Arthur - 25 lb bag ($X.XX/unit)" with link to variant
7. **Given** user clicks variant link in shopping list, **When** link is followed, **Then** My Ingredients tab opens with selected ingredient and variant highlighted
8. **Given** user is in My Pantry tab, **When** user clicks "Used in Recipes" on ingredient, **Then** UI displays list of recipes using that ingredient with links

---

## Technical Requirements

### UI Framework
- Use existing CustomTkinter framework
- Follow existing UI patterns from other tabs
- Reuse widgets from src/ui/widgets/ where applicable

### Service Integration
- **ingredient_service.py**: All ingredient CRUD operations
- **variant_service.py**: All variant CRUD operations
- **pantry_service.py**: Pantry CRUD, FIFO consumption, aggregation
- **purchase_service.py**: Price history display

### State Management
- Handle service exceptions gracefully (NotFound, ValidationError, DatabaseError)
- Display user-friendly error messages
- Confirm destructive operations (delete)
- Show loading indicators for long operations

### Data Validation
- Required fields: ingredient name, variant brand, pantry quantity
- Numeric validation: quantity > 0, density >= 0
- Date validation: expiration_date >= purchase_date (if provided)
- Prevent deletion of referenced entities

---

## Success Criteria

**Phase 4 Complete When:**
1. ✅ My Ingredients tab fully functional (CRUD + variants)
2. ✅ My Pantry tab fully functional (display + FIFO)
3. ✅ Migration executed successfully on test database
4. ✅ Recipe tab integrated with new ingredient selector
5. ✅ Shopping lists show preferred variants
6. ✅ All costs calculated using FIFO or preferred variant
7. ✅ No regressions in existing functionality
8. ✅ User can complete full workflow: ingredient → variant → pantry → recipe → event

---

## Non-Goals (Out of Scope)

- Recipe service refactoring (deferred to later)
- Event service refactoring (deferred to later)
- Materials tracking (Phase 5)
- Production tracking enhancements (Phase 5)
- PDF export features
- Mobile companion app
- Barcode scanning UI

---

## Dependencies

**Required (Must be complete):**
- ✅ Ingredient, Variant, PantryItem, Purchase models (v0.4.0)
- ✅ ingredient_service, variant_service, pantry_service, purchase_service
- ✅ Migration script (migrate_to_ingredient_variant.py)
- ✅ CustomTkinter UI framework

**Optional (Nice to have):**
- Unit converter updates for density-based conversions
- Import/export for new schema format
- Bulk operations (e.g., add multiple pantry items)

---

## Risks & Mitigations

**Risk 1: Migration Data Loss**
- Mitigation: Dry-run preview, backup recommendation, validation checks
- Mitigation: Test migration on copy of production database first

**Risk 2: UI Performance with Large Datasets**
- Mitigation: Pagination for ingredient/pantry lists
- Mitigation: Lazy loading of variants
- Mitigation: Optimize queries with eager loading

**Risk 3: User Confusion with New Architecture**
- Mitigation: Onboarding tooltips explaining ingredient vs variant
- Mitigation: Help documentation updated
- Mitigation: Migration wizard with explanatory text

**Risk 4: Cost Calculation Discrepancies**
- Mitigation: Side-by-side comparison in migration report
- Mitigation: Detailed cost breakdown in UI
- Mitigation: Allow users to verify costs before finalizing migration

---

## Testing Strategy

**Unit Tests:**
- UI widget validation logic
- Form field validators
- Error message formatting

**Integration Tests:**
- UI → Service layer calls
- Service error handling in UI
- Cross-tab navigation

**Manual Testing:**
- Full user workflows (Scenarios 1-6)
- Edge cases (empty states, large datasets)
- Error conditions (network issues, validation failures)

**Migration Testing:**
- Test on sample database
- Test on copy of production database
- Verify cost calculations match v0.3.0

---

## Documentation Updates

**User Guide:**
- New section: "Managing Ingredients (Generic Catalog)"
- New section: "Managing Variants (Brands & Packages)"
- New section: "Tracking Pantry Inventory"
- New section: "FIFO Consumption Explained"
- New section: "Migration Guide (v0.3.0 → v0.4.0)"

**Architecture Documentation:**
- Update diagrams to show UI layer
- Document ingredient/variant UI patterns
- Document migration process

---

## Timeline Estimate

**Total Effort: 2-3 weeks (60-90 hours)**

- WP01: My Ingredients Tab - Basic CRUD (12-15 hours)
- WP02: My Ingredients Tab - Variant Management (10-12 hours)
- WP03: My Pantry Tab - Display & Management (12-15 hours)
- WP04: My Pantry Tab - FIFO & Consumption (8-10 hours)
- WP05: Migration Execution & Wizard (10-12 hours)
- WP06: Integration & Testing (8-10 hours)

**Assumptions:**
- Developer familiar with CustomTkinter
- Service layer APIs are stable
- No major refactoring of existing tabs required
