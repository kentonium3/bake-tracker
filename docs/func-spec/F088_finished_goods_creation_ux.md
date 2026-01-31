# F088: FinishedGoods Creation UX

**Version**: 1.0
**Date**: 2026-01-30
**Priority**: HIGH
**Type**: Full Stack (UI + Service Layer)

---

## Executive Summary

FinishedGoods currently exist in the data model but have no creation or management UI, which blocks the ability to define assembled products for event planning and prevents validation of the planning module with real user workflows.

Current gaps:
- ❌ No UI for creating FinishedGoods
- ❌ Cannot assemble foods (FinishedUnits) with materials (MaterialUnits) into deliverable products
- ❌ Cannot nest assemblies (FinishedGoods containing other FinishedGoods)
- ❌ Planning module blocked - cannot create deliverable products for events
- ❌ Real user testing blocked - Marianne cannot define her actual product catalog

This spec adds a new Finished Goods tab to Catalog mode following the F087 standardized layout pattern, and implements single-form creation/edit UI with filtered component selection for foods, materials, and nested assemblies.

---

## Problem Statement

**Current State (NO UI):**
```
Catalog Mode Tabs
├─ ✅ Ingredients (Ingredient Catalog, Food Products)
├─ ✅ Materials (Categories, Products, Units)
├─ ✅ Recipes (Recipes Catalog, Finished Units)
└─ ❌ No Finished Goods tab

FinishedGood Model
├─ ✅ Exists in schema
├─ ✅ Composition relationships defined
└─ ❌ NO creation UI anywhere

Composition Model
├─ ✅ Supports FinishedUnit components
├─ ✅ Supports FinishedGood components (nesting)
├─ ✅ Supports MaterialUnit components (F085)
└─ ❌ NO UI to create these relationships

User Pain
├─ Cannot define "Biscotti Variety Bag" (2 almond + 2 hazelnut + 1 bag + 1 ribbon)
├─ Cannot define "Gift Box" (1 cake + 1 variety bag + 1 jumble pack)
└─ Planning module unusable without deliverable products
```

**Target State (FULL UI):**
```
Catalog Mode Tabs
├─ ✅ Ingredients (Ingredient Catalog, Food Products)
├─ ✅ Materials (Categories, Products, Units)
├─ ✅ Recipes (Recipes Catalog, Finished Units)
└─ ✅ Finished Goods (NEW - single view, F087 standardized layout)
    ├─ Row 0: Search/Filter controls
    ├─ Row 1: Action buttons
    └─ Row 2: List/Form view (ttk.Treeview + edit form)

Finished Goods Tab (F087 Pattern)
├─ List View (ttk.Treeview for trackpad scrolling)
│   ├─ Name, Assembly Type, Component Count
│   ├─ Actions: Create New, Edit, Delete
│   └─ Filter/Search capabilities
└─ Create/Edit Form
    ├─ Basic Info (Name, Assembly Type, Notes)
    ├─ Foods Section (add FinishedUnits with quantity)
    ├─ Materials Section (add MaterialUnits with quantity)
    └─ Components Section (add nested FinishedGoods with quantity)

Component Selection
├─ Category filter dropdown (narrows list)
├─ Type-ahead search (finds specific items)
├─ Clear quantity input
└─ Add/Remove functionality

User Workflow
├─ Create "Biscotti Variety Bag"
│   ├─ Add Foods: 2× Almond Biscotti, 2× Hazelnut Biscotti, 2× Choc-Dipped Biscotti
│   └─ Add Materials: 1× 12" ribbon, 1× 8" clear bag
├─ Create "Gift Box"
│   ├─ Add Foods: 1× Medium Chocolate Cake
│   ├─ Add Components: 1× Biscotti Variety Bag, 1× Jumble Cookie Pack
│   └─ Assembly nesting works correctly
└─ Planning module can now reference deliverable products
```

---

## CRITICAL: Study These Files FIRST

**Before implementation, spec-kitty planning phase MUST read and understand:**

1. **F087 Standardized Tab Layout Pattern**
   - Find: `docs/func-spec/F087_catalog_tab_layout_standardization.md` - THE PATTERN TO FOLLOW
   - Study: 3-row layout (controls, actions, grid)
   - Note: No title labels, ttk.Treeview for data, trackpad scrolling support
   - **CRITICAL:** FinishedGoods tab MUST follow F087 pattern exactly

2. **Existing Catalog Tab Patterns**
   - Find: `src/ui/modes/catalog_mode.py` - Current 3 tab structure
   - Find: `src/ui/tabs/recipes_group_tab.py` - Pattern for group tab structure
   - Note: How tabs are added to CatalogMode, grid configuration, refresh patterns

3. **List View + Form Patterns**
   - Find: `src/ui/finished_units_tab.py` - List + create/edit form pattern
   - Find: `src/ui/recipes_tab.py` - Another list + form example (will be F087 compliant)
   - Study: How list displays data, how create/edit forms are structured
   - Note: Action buttons (Create, Edit, Delete), refresh logic

4. **Component Selection UI Patterns**
   - Find: Recipe ingredient selection UI - How ingredients are added to recipes
   - Find: Any existing dropdown + search filter combinations
   - Study: How to populate filtered dropdowns, how type-ahead search works
   - Note: CustomTkinter dropdown widgets, filter event handlers

5. **FinishedGood Service Layer**
   - Find: `src/services/finished_good_service.py` - Existing CRUD operations
   - Study: How to create FinishedGood with Compositions
   - Note: Circular reference validation, component validation

6. **Composition Service Patterns**
   - Find: `src/models/composition.py` - Factory methods for creating compositions
   - Study: `create_unit_composition()`, `create_assembly_composition()`, `create_material_unit_composition()`
   - Note: How to build Composition records with correct foreign keys

---

## Requirements Reference

This specification implements the final piece of the MaterialUnit/FinishedGoods refactor identified in planning discussions:
- F085 provides product-specific MaterialUnits (schema foundation)
- F087 establishes standardized catalog tab layout pattern
- F088 provides UI to assemble FinishedGoods using F087 pattern and MaterialUnits
- Together they unblock planning module user testing

---

## Functional Requirements

### FR-1: Add Finished Goods Tab Following F087 Pattern

**What it must do:**
- Add "Finished Goods" top-level tab to CatalogMode (4th tab)
- Create new FinishedGoodsTab widget following F087 standardized layout:
  - Row 0: Search/Filter controls (weight=0)
  - Row 1: Action buttons (weight=0)
  - Row 2: ttk.Treeview list view (weight=1)
  - Row 3: Status bar if needed (weight=0)
- NO title label (per F087 standard)
- Use ttk.Treeview for data display (trackpad scrolling)
- Position after Recipes tab in tab order
- Implement lazy data loading on first activation
- Add to CatalogMode.refresh_all_tabs() method

**Pattern reference:** Study F087 spec + post-F087 Recipes/Ingredients/Products tabs

**Success criteria:**
- [ ] Finished Goods tab appears in Catalog mode after Recipes
- [ ] Tab follows F087 3-row layout exactly
- [ ] No title label present
- [ ] ttk.Treeview used for list display
- [ ] Trackpad scrolling works
- [ ] Lazy loading prevents data fetch until first view
- [ ] Refresh works correctly

---

### FR-2: Implement FinishedGoods List View (ttk.Treeview)

**What it must do:**
- Display ttk.Treeview of all FinishedGoods
- Show columns: Name, Assembly Type, Component Count, Notes (truncated)
- Add "Create New" button in row 1 (action buttons row)
- Add "Edit" and "Delete" buttons in row 1
- Implement search entry in row 0 (filter controls row)
- Implement filter by assembly type dropdown in row 0
- Handle empty state with helpful message
- Refresh list after create/edit/delete operations
- Support row selection
- Support double-click to edit

**Pattern reference:** Study post-F087 RecipesTab ttk.Treeview implementation

**Success criteria:**
- [ ] ttk.Treeview displays all FinishedGoods with correct columns
- [ ] Trackpad scrolling works (two-finger swipe)
- [ ] "Create New" button opens create form
- [ ] "Edit" button opens edit form with selected FinishedGood
- [ ] Double-click opens edit form
- [ ] "Delete" button prompts for confirmation, then deletes
- [ ] Search filters list as user types
- [ ] Assembly type filter works correctly
- [ ] Empty state displays helpful message
- [ ] List refreshes after data changes

---

### FR-3: Implement FinishedGood Create/Edit Form - Basic Info

**What it must do:**
- Create form with fields: Name, Assembly Type (dropdown), Packaging Instructions (text area), Notes (text area)
- Assembly Type options: Custom Order, Gift Box, Variety Pack, Seasonal Box, Event Package
- Validate Name is required and non-empty
- Auto-generate slug from name (following existing slug patterns)
- Display form in modal or dedicated area (pattern match existing forms)
- Save/Cancel buttons with proper event handling

**Pattern reference:** Study how Recipe create/edit form handles basic fields

**Business rules:**
- Name is required
- Assembly Type defaults to Custom Order
- Slug auto-generated, cannot be manually edited
- Packaging Instructions and Notes are optional

**Success criteria:**
- [ ] Form displays correctly for create and edit modes
- [ ] All fields populated correctly in edit mode
- [ ] Name validation prevents empty values
- [ ] Assembly Type dropdown shows all options
- [ ] Slug auto-generated on save
- [ ] Save creates/updates FinishedGood record
- [ ] Cancel discards changes

---

### FR-4: Implement Foods Component Section (FinishedUnits)

**What it must do:**
- Display "Foods" section in create/edit form
- Show list of currently added FinishedUnits with columns: Name, Quantity, Actions (Remove)
- Add "Add Food" button that opens food selection UI
- Food selection UI has:
  - Category filter dropdown (populated from Recipe categories)
  - Type-ahead search field (filters by FinishedUnit name)
  - Quantity input field
  - Add button
- Selected foods appear in Foods list
- Support removing foods from list
- Pass FinishedUnit component data to service layer on save

**Pattern reference:** Study how Recipe form adds ingredients with quantities

**UI Requirements:**
- Category filter must narrow dropdown options effectively
- Type-ahead search must filter as user types
- Quantity input must validate positive integers
- Clear visual separation between section header and component list

**Success criteria:**
- [ ] Foods section displays in form
- [ ] "Add Food" opens selection UI
- [ ] Category filter works correctly
- [ ] Type-ahead search filters FinishedUnits list
- [ ] Quantity validation prevents invalid values
- [ ] Added foods appear in list with quantity
- [ ] Remove button deletes food from list
- [ ] Component data saved correctly via service layer

---

### FR-5: Implement Materials Component Section (MaterialUnits)

**What it must do:**
- Display "Materials" section in create/edit form
- Show list of currently added MaterialUnits with columns: Name, Product, Quantity, Actions (Remove)
- Add "Add Material" button that opens material selection UI
- Material selection UI has:
  - Category filter dropdown (populated from Material hierarchy: Category → Subcategory)
  - Type-ahead search field (filters by MaterialUnit name or product name)
  - Quantity input field
  - Add button
- Selected materials appear in Materials list
- Support removing materials from list
- Pass MaterialUnit component data to service layer on save

**Pattern reference:** Copy Foods section pattern, adjust for MaterialUnit data structure

**UI Requirements:**
- Category filter should show Material categories and subcategories
- Search must work on both MaterialUnit name and parent product name
- Product column helps disambiguate identical MaterialUnits from different products
- Quantity supports decimals for materials (some materials use fractional quantities)

**Success criteria:**
- [ ] Materials section displays in form
- [ ] "Add Material" opens selection UI
- [ ] Category filter uses Material hierarchy
- [ ] Type-ahead search works on name and product
- [ ] Quantity validation allows decimals
- [ ] Added materials appear in list with product info
- [ ] Remove button deletes material from list
- [ ] Component data saved correctly via service layer

---

### FR-6: Implement Components Section (Nested FinishedGoods)

**What it must do:**
- Display "Components" section in create/edit form
- Show list of currently added FinishedGoods with columns: Name, Assembly Type, Quantity, Actions (Remove)
- Add "Add Component" button that opens component selection UI
- Component selection UI has:
  - Assembly Type filter dropdown
  - Type-ahead search field (filters by FinishedGood name)
  - Quantity input field
  - Add button
- Prevent circular references (cannot add self or ancestors)
- Selected components appear in Components list
- Support removing components from list
- Pass nested FinishedGood component data to service layer on save

**Pattern reference:** Copy Foods section pattern, adjust for FinishedGood nesting

**Business rules:**
- Cannot add the FinishedGood being edited to its own components (self-reference)
- Cannot add any FinishedGood that contains the current one (circular reference)
- Service layer must validate circular references before save

**Success criteria:**
- [ ] Components section displays in form
- [ ] "Add Component" opens selection UI
- [ ] Assembly Type filter works correctly
- [ ] Type-ahead search filters FinishedGoods list
- [ ] Circular reference validation prevents invalid selections
- [ ] Added components appear in list with quantity
- [ ] Remove button deletes component from list
- [ ] Component data saved correctly via service layer
- [ ] Service layer rejects circular references with clear error

---

### FR-7: Implement Service Layer for FinishedGood Creation with Components

**What it must do:**
- Enhance FinishedGoodService.create() to accept component data
- Component data structure: list of dicts with {type, id, quantity, notes, sort_order}
- Create FinishedGood record first
- Create Composition records for each component using factory methods
- Validate at least one component exists (FinishedGood must contain something)
- Validate circular references for nested FinishedGoods
- Transaction management: rollback all if any step fails
- Return created FinishedGood with loaded relationships

**Pattern reference:** Study how Recipe creation handles multiple RecipeIngredient records

**Business rules:**
- FinishedGood must have at least one component (food, material, or component)
- Circular references are invalid (A contains B, B contains A)
- All component IDs must resolve to existing records
- Transaction ensures atomicity (all-or-nothing)

**Success criteria:**
- [ ] create() accepts component data parameter
- [ ] FinishedGood and all Compositions created atomically
- [ ] Validation prevents FinishedGoods with zero components
- [ ] Validation prevents circular references
- [ ] Invalid component IDs raise clear errors
- [ ] Transaction rollback on any failure
- [ ] Service tests cover success and error cases

---

### FR-8: Implement Service Layer for FinishedGood Update with Components

**What it must do:**
- Enhance FinishedGoodService.update() to accept component data
- Delete all existing Compositions for the FinishedGood
- Recreate Compositions from provided component data
- Validate at least one component exists
- Validate circular references
- Transaction management: rollback all if any step fails
- Return updated FinishedGood with loaded relationships

**Pattern reference:** Study how Recipe update handles RecipeIngredient changes

**Business rules:**
- Same validation as create (at least one component, no circular references)
- Delete-and-recreate simpler than diff-and-patch for components
- Maintain sort_order from UI for consistent component display

**Success criteria:**
- [ ] update() accepts component data parameter
- [ ] Old Compositions deleted, new ones created atomically
- [ ] Validation prevents removing all components
- [ ] Validation prevents circular references
- [ ] Transaction rollback on any failure
- [ ] Service tests cover component updates

---

### FR-9: Implement FinishedGood Deletion with Safety Checks

**What it must do:**
- Check if FinishedGood is referenced by other FinishedGoods (as component)
- Check if FinishedGood is referenced by Events (planning module)
- Prevent deletion with clear error message if in use
- Allow deletion if no references exist
- Cascade delete all Compositions when FinishedGood deleted
- Confirmation dialog in UI before deletion

**Pattern reference:** Study how Recipe deletion handles references

**Success criteria:**
- [ ] Deletion prevented if FinishedGood is component of another
- [ ] Deletion prevented if FinishedGood is in event planning
- [ ] Error message clearly explains why deletion blocked
- [ ] Deletion succeeds if no references exist
- [ ] Compositions cascade deleted correctly
- [ ] UI shows confirmation dialog before deletion

---

## Out of Scope

**Explicitly NOT included in this feature:**
- ❌ Inventory awareness during creation (separate concern - user defines catalog, inventory calculated separately)
- ❌ Cost display/calculation in UI (costs calculated dynamically, not shown in catalog)
- ❌ Assembly instructions or production workflow (F014 assembly recording handles this)
- ❌ Packaging product selection (generic packaging deferred to separate feature)
- ❌ Batch/quantity goals (planning module handles this via events)
- ❌ Image upload or product photos (future enhancement)
- ❌ Nutritional information or allergen tracking (future enhancement)
- ❌ Duplicate/clone FinishedGood functionality (manual recreation acceptable for now)

---

## Success Criteria

**Complete when:**

### F087 Pattern Compliance
- [ ] Finished Goods tab follows F087 3-row layout exactly
- [ ] No title label present
- [ ] Row 0: Search/Filter controls (weight=0)
- [ ] Row 1: Action buttons (weight=0)
- [ ] Row 2: ttk.Treeview grid (weight=1)
- [ ] Trackpad scrolling works (two-finger swipe)
- [ ] Compact vertical layout maximizes data display

### Tab Structure
- [ ] Finished Goods tab appears as 4th tab in Catalog
- [ ] Tab activates and displays correctly
- [ ] Lazy loading works on first activation
- [ ] Tab refreshes correctly with other catalog tabs

### List View
- [ ] All FinishedGoods display in ttk.Treeview
- [ ] Columns show correct data (Name, Type, Component Count, Notes)
- [ ] "Create New" button opens create form
- [ ] "Edit" button opens edit form with correct data
- [ ] Double-click opens edit form
- [ ] "Delete" button confirms and deletes (if allowed)
- [ ] Search and filters work correctly
- [ ] Empty state displays helpful message

### Create/Edit Form
- [ ] Form displays with all sections (Basic Info, Foods, Materials, Components)
- [ ] Basic info fields work correctly (Name, Assembly Type, etc.)
- [ ] Slug auto-generated from name
- [ ] Save/Cancel buttons function correctly
- [ ] Form validates required fields

### Component Selection
- [ ] Foods section adds/removes FinishedUnits correctly
- [ ] Materials section adds/removes MaterialUnits correctly
- [ ] Components section adds/removes nested FinishedGoods correctly
- [ ] Category filters narrow options effectively
- [ ] Type-ahead search filters as user types
- [ ] Quantity inputs validate correctly
- [ ] All component data appears in respective lists

### Service Layer
- [ ] FinishedGood created with all components atomically
- [ ] FinishedGood updated with component changes atomically
- [ ] Validation prevents FinishedGoods with zero components
- [ ] Validation prevents circular references
- [ ] Deletion prevented when FinishedGood in use
- [ ] Service tests achieve >80% coverage

### Integration
- [ ] Created FinishedGoods appear in planning module dropdowns
- [ ] User can create "Biscotti Variety Bag" example successfully
- [ ] User can create "Gift Box" with nested components successfully
- [ ] Round-trip: create → edit → save preserves all data
- [ ] Real user (Marianne) can define actual product catalog

### Quality
- [ ] Zero failing tests after implementation
- [ ] UI responsive and intuitive
- [ ] Error messages clear and actionable
- [ ] Component lists display in consistent order (sort_order preserved)
- [ ] No UI lag when adding/removing components
- [ ] Visual consistency with other F087-compliant tabs

---

## Architecture Principles

### F087 Layout Standard Compliance

**Follow established catalog tab pattern:**
- No title label (tab name already identifies content)
- 3-row structure (controls, actions, grid)
- ttk.Treeview for data display (trackpad scrolling)
- Fixed controls at top, expandable grid below
- Matches Recipes, Ingredients, Products, Materials tabs post-F087

### Single-Form Component Assembly

**All three component types in one form:**
- Foods, Materials, Components sections all visible simultaneously
- User sees complete assembly at a glance
- Simpler than multi-step wizard or separate tabs
- Matches mental model: "I'm assembling a package with these things"

### Category Filters + Type-Ahead Search

**Two-level filtering for usability:**
- Category filter narrows options quickly (broad categorization)
- Type-ahead search finds specific items (precise selection)
- Prevents scrolling through 200+ items in dropdowns
- Familiar pattern from e-commerce product filters

### Service Layer Atomicity

**All-or-nothing saves:**
- FinishedGood + all Compositions created in single transaction
- Validation before any database writes
- Rollback on any failure preserves data integrity
- Follows existing Recipe + RecipeIngredient pattern

### Circular Reference Prevention

**Validate before save, not after:**
- Check circular references during component selection (UI)
- Double-check in service layer validation (safety)
- Clear error messages explain why component cannot be added
- Prevents user from creating invalid assemblies

---

## Constitutional Compliance

✅ **Principle I: User-Centric Design**
- Single form shows complete assembly at once
- Category filters reduce cognitive load
- Real user (Marianne) can define actual product catalog
- Unblocks user testing of planning module
- F087 pattern provides consistent, familiar experience

✅ **Principle II: Data Integrity**
- Validation prevents invalid assemblies (zero components, circular refs)
- Transaction atomicity ensures consistent state
- Deletion safety checks prevent orphaned references

✅ **Principle III: Future-Proof Schema**
- FinishedGood model already supports this UI (no schema changes)
- Component structure ready for web deployment
- Slug-based references enable multi-tenant future

✅ **Principle V: Layered Architecture**
- UI layer uses service layer for all data operations
- Service layer validates business rules
- No business logic in UI widgets

✅ **Principle VII: Pragmatic Aspiration**
- Build for desktop today (F087 pattern, trackpad scrolling)
- Establish pattern for tomorrow (consistent catalog management)
- Pattern matches existing catalog tabs (Recipes, Products, Materials)

---

## Risk Considerations

**Risk: Component selection UI becomes unwieldy with 100+ FinishedUnits**
- Context: Large catalogs make dropdown selection difficult
- Mitigation: Category filter + type-ahead search narrows options; tested with realistic catalog size

**Risk: Circular reference validation misses edge cases**
- Context: Complex nesting (A→B→C→A) might not be caught
- Mitigation: Service layer validation uses graph traversal; comprehensive test cases for multi-level nesting

**Risk: Users accidentally create FinishedGoods with wrong components**
- Context: Component lists might be long, easy to mis-select
- Mitigation: Component list shows all added items clearly; Remove button allows correction before save

**Risk: Delete prevention too aggressive (blocks legitimate deletions)**
- Context: User wants to delete old FinishedGood but system prevents it
- Mitigation: Error message clearly explains which records reference it; user can remove references first

**Risk: F087 pattern not followed exactly (inconsistent with other tabs)**
- Context: Deviating from F087 pattern breaks user expectations
- Mitigation: Explicit requirement to follow F087 spec; planning phase must verify pattern match

---

## Notes for Implementation

**Pattern Discovery (Planning Phase):**
- Study F087 spec FIRST - this is the mandatory layout pattern
- Study post-F087 RecipesTab → apply ttk.Treeview + 3-row layout
- Study FinishedUnitsTab → apply list view pattern (but with F087 layout)
- Study Recipe create/edit form → apply component section pattern
- Study how Recipe handles RecipeIngredient → apply to Composition handling
- Study Materials tab structure → understand non-group tab in Catalog mode

**Key Patterns to Copy:**
- F087 layout: 3-row structure → FinishedGoods tab MUST follow exactly
- Tab structure: Materials tab → FinishedGoods tab (single view, not group)
- List view: Post-F087 RecipesTab ttk.Treeview → FinishedGoods list
- Component selection: Recipe ingredients → FinishedGood components
- Service transactions: Recipe creation → FinishedGood creation

**Focus Areas:**
- F087 pattern compliance (mandatory, non-negotiable)
- Component selection UI usability (filters, search, clarity)
- Circular reference validation (graph traversal, clear errors)
- Transaction management (atomic saves, rollback on failure)
- Real user testing (Marianne can define actual products)
- Trackpad scrolling verification (two-finger swipe works)

**UI Component Selection Approach:**
- Investigate existing dropdown + search patterns in codebase
- Consider ComboBox or filtered list widgets for component selection
- Ensure type-ahead search provides immediate visual feedback
- Test with realistic catalog sizes (50+ FinishedUnits, 30+ MaterialUnits)

**Implementation Order:**
1. Create FinishedGoodsTab shell following F087 pattern exactly
2. Implement ttk.Treeview list view with trackpad scrolling
3. Implement create/edit form with basic info
4. Add Foods component section
5. Add Materials component section
6. Add Components section with circular reference prevention
7. Implement service layer enhancements
8. Test complete workflow end-to-end
9. User testing with Marianne

---

**END OF SPECIFICATION**
