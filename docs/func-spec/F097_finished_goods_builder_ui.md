# F097: Finished Goods Builder UI

**Version**: 1.0  
**Priority**: HIGH  
**Type**: Full Stack Feature  

**Created**: 2026-02-06  
**Status**: Draft  

---

## Executive Summary

Current gaps:
- ❌ No UI for creating composite FinishedGoods (bundles, multi-item packages)
- ❌ Cannot create mixed bundles (e.g., assorted biscotti bag with 6 almond + 4 hazelnut + 2 chocolate-dipped)
- ❌ Cannot specify quantities per component in finished good assembly
- ❌ Manual FinishedGood creation is nearly impossible with current grid-based UI

This spec implements a guided 3-step accordion builder for creating FinishedGoods with multi-select component selection and per-component quantity specification, validated through paper prototype user testing.

---

## Problem Statement

**Current State:**
```
FinishedGoods Creation
├─ ❌ No dedicated builder UI
├─ ❌ Grid-based forms don't scale for multi-component assemblies
├─ ❌ Cannot create mixed bundles (different FinishedUnits/FinishedGoods)
├─ ❌ No quantity specification per component
└─ ❌ Filtering/navigation impractical with long component lists

Example Use Cases Blocked:
├─ ❌ Assorted biscotti bag (6 almond + 4 hazelnut + 2 chocolate-dipped)
├─ ❌ Cookie variety box (3 types, different quantities each)
├─ ❌ Gift basket (multiple cakes + brownies + box + tissue + ribbon)
└─ ❌ Tray of mixed cupcakes (2 vanilla + 4 chocolate + 3 red velvet)
```

**Target State (PAPER PROTOTYPE VALIDATED):**
```
FinishedGoods Builder
├─ ✅ 3-step accordion workflow (food → materials → review)
├─ ✅ Multi-select with per-component quantities
├─ ✅ Category filtering for long lists
├─ ✅ "Bare items only" filter for initial bundle creation
├─ ✅ Materials consolidated (no separate "decorations" step)
└─ ✅ Review screen with component summary before save

User Can Now Build:
├─ ✅ Assorted biscotti bag with specified quantities per type
├─ ✅ Mixed cookie boxes with different counts
├─ ✅ Gift baskets with multiple components
└─ ✅ Any combination of FinishedUnits/FinishedGoods + Materials
```

---

## User Testing Validation

**Tabletop Exercise Results (2026-02-06):**

✅ **Pattern B (Accordion Builder) validated as effective approach**
- 3-step flow matches user mental model
- Progressive disclosure reduces cognitive load
- Step-by-step guidance prevents errors

✅ **Category filtering works well for long lists**
- Existing ProductCategory system sufficient (F095/F096)
- No need for separate FinishedGoodCategory

✅ **Multi-select + quantity workflow needed**
- Single-select insufficient for mixed bundles
- Quantity must be specifiable per component
- Inline quantity entry preferred over separate dialog

✅ **Materials consolidation appropriate**
- No distinction needed between "packaging" and "decorations"
- All non-food components treated as Materials
- Single Materials step simpler than separate steps

✅ **"Bare items only" filter essential**
- Critical for creating initial bundles from FinishedUnits
- Prevents overwhelming lists when building first-level assemblies
- "Include assemblies" filter useful for nested FinishedGoods

❌ **"Include pre-packaged" filter rejected**
- No clear distinction from "Include assemblies"
- Removed as redundant

---

## CRITICAL: Study These Files FIRST

**Before implementation, spec-kitty planning phase MUST read and understand:**

1. **Data Model Foundation**
   - `src/models/finished_good.py` - FinishedGood model with components relationship
   - `src/models/finished_good_component.py` - FinishedGoodComponent junction table
   - Study: component_type enum, quantity field, foreign keys

2. **Service Layer**
   - `src/services/finished_good_service.py` - CRUD operations
   - `src/services/finished_unit_service.py` - For querying available FinishedUnits
   - `src/services/material_product_service.py` - For querying Materials
   - Note: Component creation, validation, save patterns

3. **Existing UI Patterns**
   - `src/ui/catalog/catalog_tab.py` - Tab shell pattern (F087)
   - `src/ui/finished_goods/finished_unit_form.py` - Category filtering pattern
   - `src/ui/materials/material_categories_dialog.py` - Multi-select pattern reference
   - Study: Layout patterns, filter controls, selection handling

4. **UX Mockups (This Spec)**
   - Section "Detailed UI Mockups" below - ASCII wireframes for each step
   - Paper prototype validation results (above)
   - User workflow sequences

5. **Constitution References**
   - `.kittify/memory/constitution.md` - Principle I: User-Centric Design
   - Paper prototype validation fulfills "user testing MUST validate major features"

---

## Requirements Reference

This specification implements:
- **Constitution Principle I**: User-Centric Design & Workflow Validation
  - Features MUST solve actual user problems (mixed bundles)
  - UI MUST be intuitive (validated via paper prototype)
  - Workflows MUST match natural baking planning (food → materials → review)
  - User testing with primary user MUST validate major features (✓ completed 2026-02-06)

From: `.kittify/memory/constitution.md` (v1.4.0)

---

## Functional Requirements

### FR-1: Create FinishedGoods Builder Dialog

**What it must do:**
- Create dedicated modal dialog for building FinishedGoods
- Launch from Catalog > Finished Goods tab via "+ Create Finished Good" button
- Implement 3-step workflow: Food Selection → Materials → Review
- Support multi-select component selection
- Allow per-component quantity specification
- Include category filtering and bare/assembly toggles

**Dialog requirements:**
- Header with name field and auto-generate option
- Step 1: Food selection with category filter, bare/assembly toggles, search, multi-select list with quantities
- Step 2: Materials selection with category filter, search, multi-select list with quantities (optional step)
- Step 3: Review screen showing component summary, tags, notes field
- Save and cancel actions available
- State management between steps (preserve selections when navigating)

**Success criteria:**
- [ ] Dialog launches from Finished Goods tab
- [ ] 3 accordion sections expand/collapse properly
- [ ] Only one section expanded at a time
- [ ] Completed sections show checkmark + summary
- [ ] Can navigate back to previous steps via "Change" button

---

### FR-2: Food Selection Step (Step 1)

**Display requirements:**
- Display all available FinishedUnits and FinishedGoods for selection
- Filter by ProductCategory (using existing category system)
- Toggle between "Bare items only" (auto-created from recipes) and "Include assemblies" (manually created FinishedGoods)
- Support multi-select capability
- Allow quantity specification per selected item
- Validate minimum 1 food item selected before continuing to next step

**Filtering requirements:**
- "Bare items only" filter: Show only auto-created FinishedGoods (from recipes with EA yield)
- "Include assemblies" toggle: Show manually created composite FinishedGoods
- Category filter: Limit results to selected ProductCategory
- Both filters can be combined (category + bare/assemblies)

**Required UI elements:**
- Category selection (all categories from ProductCategory)
- "Bare items only" and "Include assemblies" filters
- Search field for filtering by name
- List of available items showing: name, source recipe, yield
- Selection mechanism for multiple items
- Quantity input for each selected item (range 1-999)
- Validation feedback if no items selected
- Continue button to proceed to next step

**Validation rules:**
- Minimum 1 food item must be checked
- Checked items must have quantity > 0
- Display error if Continue clicked without valid selections

**Success criteria:**
- [ ] Category filter populates from ProductCategory table
- [ ] "Bare items only" shows only auto-created FinishedGoods (from EA recipes)
- [ ] "Include assemblies" shows manually created FinishedGoods
- [ ] Search filters by FinishedGood name (case-insensitive)
- [ ] Multi-select checkboxes work properly
- [ ] Quantity fields accept integers 1-999
- [ ] Validation prevents continuing without selections
- [ ] Selected items persist when navigating back from Step 2

---

### FR-3: Materials Selection Step (Step 2)

**Display requirements:**
- Display all available MaterialProducts for selection
- Filter by MaterialCategory
- Support multi-select capability
- Allow quantity specification per selected item
- Allow skipping step entirely (materials are optional)
- Materials step can be skipped if building food-only bundle

**Materials query requirements:**
- Query all available MaterialProducts
- Filter by MaterialCategory if selected
- Exclude discontinued materials

**Required UI elements:**
- Material category selection (from MaterialCategory)
- Search field for filtering by name
- List of available materials showing: name, specifications
- Selection mechanism for multiple materials
- Quantity input for each selected material (range 1-999)
- Skip option to bypass materials entirely
- Continue button to proceed to review step

**Success criteria:**
- [ ] Material category filter populates from MaterialCategory table
- [ ] Search filters by MaterialProduct name
- [ ] Can skip step entirely (materials optional)
- [ ] Selected materials persist when navigating back from Step 3
- [ ] Quantity fields validate 1-999

---

### FR-4: Review & Save Step (Step 3)

**Display requirements:**
- Summary of all selected components (food and materials)
- Per-component quantities clearly displayed
- Editable FinishedGood name field
- Auto-generated suggested tags from component names
- Notes field for additional context
- Save action creates all records atomically
- Start Over action clears all selections and returns to Step 1

**Save requirements:**
- Create FinishedGood record with user-entered name and notes
- Create all FinishedGoodComponent records atomically
- Each component must reference correct entity (FinishedGood or MaterialProduct)
- Each component must store specified quantity
- Transaction must be atomic (all or nothing)

**Required UI elements:**
- Component summary section showing:
  - Food items with quantities
  - Materials with quantities
  - Metadata (yield, nesting level, usage contexts)
- Tag management (display auto-suggested tags, allow adding more)
- Notes text field
- Save button (creates FinishedGood)
- Start Over button (resets wizard)

**Success criteria:**
- [ ] Summary accurately reflects all selections
- [ ] Quantities displayed correctly per component
- [ ] Tags auto-generated from component names
- [ ] Save creates FinishedGood + all FinishedGoodComponents atomically
- [ ] Success message displayed on save
- [ ] Dialog closes and refreshes Finished Goods tab list
- [ ] "Start Over" clears all selections and returns to Step 1

---

### FR-5: Accordion State Management

**What it must do:**
- Only one accordion section expanded at a time
- Completed steps show collapsed with checkmark + summary
- Can click "Change" on completed step to re-expand and edit
- Incomplete steps show greyed out until previous steps complete
- State persists during session (can navigate back/forward)

**State management requirements:**
- Only one step visible/active at a time
- Completed steps show summary with ability to return and edit
- Incomplete steps unavailable until prerequisites met
- Selection state preserved when navigating between steps
- User can navigate back to previous steps to modify selections

**Success criteria:**
- [ ] Only one section expanded at a time
- [ ] Checkmarks appear on completed steps
- [ ] Summary line shows selections count
- [ ] "Change" button re-expands step
- [ ] All steps navigable forward and backward

---

### FR-6: Integration with Finished Goods Tab

**What it must do:**
- Add "+ Create Finished Good" button to Finished Goods tab (Catalog mode)
- Launch FinishedGoodsBuilderDialog on button click
- Refresh Finished Goods list on successful save
- Display newly created FinishedGood in grid

**Success criteria:**
- [ ] Button added to Finished Goods tab toolbar
- [ ] Dialog launches on click
- [ ] List refreshes after save
- [ ] New FinishedGood appears in grid

---

## Edge Cases

### Edge Case 1: Empty Category Lists
**Scenario:** User selects category with no items
**Behavior:** Display "No items in this category" message
**Validation:** Prevent continuing if no items available

### Edge Case 2: All Items Already Selected
**Scenario:** User checks all items in a category
**Behavior:** Allow continuing normally, no special handling needed

### Edge Case 3: Very Long Names
**Scenario:** FinishedGood or Material name exceeds display width
**Behavior:** Truncate with ellipsis, show full name on hover tooltip

### Edge Case 4: Duplicate Named FinishedGoods
**Scenario:** User tries to save FinishedGood with name that already exists
**Behavior:** Show error: "A Finished Good with this name already exists. Please choose a different name."
**Validation:** Check name uniqueness before save

### Edge Case 5: Cancel with Unsaved Changes
**Scenario:** User clicks Cancel after making selections
**Behavior:** Show confirmation dialog: "Discard unsaved changes?"
**Options:** "Discard" (close dialog) / "Keep Editing" (stay in dialog)

### Edge Case 6: Zero Quantity Entered
**Scenario:** User checks item but leaves quantity blank or enters 0
**Behavior:** Treat as unchecked (do not include in save)
**Validation:** Only save components with quantity >= 1

### Edge Case 7: Navigation During Edit
**Scenario:** User clicks "Change" on Step 1 while on Step 3
**Behavior:** Collapse Step 3, expand Step 1, preserve all selections

---

## Success Criteria

### Measurable Outcomes

**SC-001: Core Workflow Completion**
- User can build mixed bundle (e.g., assorted biscotti) in under 3 minutes
- All components selected correctly with proper quantities
- FinishedGood saves successfully with all relationships intact

**SC-002: Filtering Effectiveness**
- Category filter reduces visible items to relevant subset
- "Bare items only" toggle shows only FinishedUnits
- Search narrows list to matching items within 2 keystrokes

**SC-003: Multi-Select Usability**
- User can select 5+ items without confusion
- Quantities editable inline without separate dialog
- Checkboxes clearly indicate selected state

**SC-004: User Testing Validation**
- Primary user (Marianne) completes 3 test scenarios successfully:
  1. Assorted biscotti bag (6 almond + 4 hazelnut + 2 chocolate)
  2. Cookie variety box (3 types, different quantities)
  3. Gift basket (cake + brownies + box + ribbon)
- Zero critical issues during testing
- User rates workflow as "intuitive" or better

**SC-005: Data Integrity**
- All FinishedGoodComponents save with correct quantities
- Foreign keys properly reference FinishedGoods and MaterialProducts
- No orphaned components or missing relationships

---

## User Scenarios & Testing

### User Story 1 - Create Simple Bundle (Priority: P1)

**Scenario:** Baker creates an assorted biscotti bag with multiple types and quantities.

**Why this priority:** Core value proposition - enables mixed bundles which are currently impossible to create. Directly addresses validated user need from paper prototype testing.

**Independent Test:** Can be fully tested by creating a 3-item biscotti bundle and verifying all components save correctly with proper quantities.

**Acceptance Scenarios:**

1. **Given** Catalog > Finished Goods tab is open, **When** user clicks "+ Create Finished Good", **Then** builder dialog opens with Step 1 expanded

2. **Given** Step 1 is expanded, **When** user selects "Cookies" category and checks "Bare items only", **Then** only bare cookie FinishedUnits display

3. **Given** bare items displayed, **When** user selects "Almond Biscotti" (qty 6), "Hazelnut Biscotti" (qty 4), "Chocolate-Dipped Biscotti" (qty 2) and clicks Continue, **Then** Step 1 collapses with checkmark, Step 2 expands

4. **Given** Step 2 is expanded, **When** user selects "Cellophane Bag (6x9)" (qty 1), "Ribbon (red, 24")" (qty 1) and clicks Continue, **Then** Step 2 collapses with checkmark, Step 3 expands

5. **Given** Step 3 shows summary, **When** user enters name "Assorted Biscotti Gift Bag" and clicks Save, **Then** FinishedGood saves with 5 components (3 food + 2 materials), dialog closes, tab refreshes

---

### User Story 2 - Filter and Search (Priority: P1)

**Scenario:** Baker finds specific items quickly using category filters and search when lists are long.

**Why this priority:** Essential for usability with large catalogs. Paper prototype identified this as critical pain point.

**Independent Test:** Can be tested by creating catalog with 50+ items and verifying filtering reduces list to <10 items.

**Acceptance Scenarios:**

1. **Given** 100+ FinishedUnits exist across categories, **When** user selects "Cakes" category in Step 1, **Then** only cake items display (not cookies, brownies, etc.)

2. **Given** "Cakes" category selected with 20 items, **When** user types "choc" in search box, **Then** only chocolate-related cakes display

3. **Given** "Bare items only" unchecked, **When** user checks "Include assemblies", **Then** pre-built FinishedGoods appear in list alongside bare items

4. **Given** many items visible, **When** user checks items and scrolls, **Then** checked items remain checked and quantities preserved

---

### User Story 3 - Edit Existing Selections (Priority: P2)

**Scenario:** Baker realizes they need to change quantities or add items after progressing to later step.

**Why this priority:** Important for workflow flexibility but not core functionality. Can be omitted from MVP.

**Independent Test:** Can be tested by completing Step 1, proceeding to Step 2, clicking "Change" on Step 1, and verifying selections are editable.

**Acceptance Scenarios:**

1. **Given** Step 3 is displayed with review, **When** user clicks "Change" on Step 1 summary, **Then** Step 1 expands with previous selections visible and editable

2. **Given** Step 1 re-expanded, **When** user changes quantity from 6 to 8 and clicks Continue, **Then** Step 3 summary reflects new quantity

3. **Given** Step 2 complete, **When** user clicks "Change" and adds another material, **Then** Step 3 summary includes new material

---

### User Story 4 - Skip Optional Materials (Priority: P2)

**Scenario:** Baker creates food-only bundle without any packaging materials.

**Why this priority:** Valid use case but less common. Good to have for flexibility.

**Independent Test:** Can be tested by creating FinishedGood with only food items and no materials.

**Acceptance Scenarios:**

1. **Given** Step 2 is expanded, **When** user clicks "Skip Step" without selecting materials, **Then** Step 2 collapses with "No materials" summary, Step 3 expands

2. **Given** Step 3 displays, **When** review summary shown, **Then** only food items listed under "Components", no materials section

3. **Given** food-only bundle, **When** user clicks Save, **Then** FinishedGood saves with only food components (no material components)

---

### User Story 5 - Start Over (Priority: P3)

**Scenario:** Baker realizes they're building wrong bundle and wants to start fresh.

**Why this priority:** Nice to have for user convenience but can work around by Cancel + relaunch.

**Independent Test:** Can be tested by making selections, clicking "Start Over", and verifying all state clears.

**Acceptance Scenarios:**

1. **Given** Step 3 with selections made, **When** user clicks "Start Over", **Then** all steps reset, Step 1 expands, all selections cleared

2. **Given** fresh start after "Start Over", **When** user makes new selections, **Then** previous selections do not reappear

---

## UI Workflow Overview

The builder dialog follows a 3-step progressive workflow validated through paper prototype testing with the primary user (2026-02-06):

**Step 1: Food Selection**
- Shows category filter, bare/assembly toggles, search
- Displays list of available FinishedGoods matching filters
- User selects items and specifies quantities
- Validates minimum 1 item before proceeding

**Step 2: Materials (Optional)**  
- Shows material category filter, search
- Displays list of available MaterialProducts
- User selects materials and specifies quantities
- Can be skipped entirely

**Step 3: Review**
- Shows complete component summary
- Allows name editing and tag management
- Provides save action to create FinishedGood

**Navigation:**
- Steps progress forward sequentially
- Completed steps can be revisited to modify selections
- Selections preserved when navigating between steps
- Cancel available at any point

---

## Dependencies

**Required Features (Must be Complete):**
- F095: Enum Display Pattern Standardization (for category dropdowns)
- F096: Recipe Category Management v2 (for ProductCategory filtering)
- F047: Materials Management System (for MaterialProduct availability)
- F087: Catalog Tab Layout Standardization (for Finished Goods tab shell)

**Related Features (Reference but not blocking):**
- F088: Finished Goods Creation UX (original spec, now superseded by F097)
- F046: Finished Goods Bundles Assembly (data model foundation)

**Future Features (Depend on F097):**
- Event Planning Module (F068-F079) - will use created FinishedGoods
- Finished Goods Inventory (F061) - will track assembled bundles

---

## Testing Strategy

### Unit Tests
- FinishedGood creation with multiple components
- Component validation (quantities, types)
- Category filtering logic
- Search filtering

### Integration Tests
- Full workflow: select items → select materials → save
- Navigation between steps with state preservation
- Edit previous step and re-save
- Skip materials step

### User Acceptance Tests
With primary user (Marianne):
1. Create assorted biscotti bag (3 types, different quantities)
2. Create cookie variety box (multiple cookies + box + tissue)
3. Create gift basket (cake + brownies + multiple materials)
4. Attempt to find specific item using category + search
5. Edit selections after progressing to later step

**Success Criteria:** All 5 scenarios completed without confusion or errors

---

## Constitutional Compliance

**Principle I: User-Centric Design & Workflow Validation** ✓
- Paper prototype user testing completed and validated
- Workflow matches natural planning process (food → materials → review)
- UI intuitive for non-technical user (primary user feedback)

**Principle V: Layered Architecture Discipline** ✓
- UI layer calls service methods only
- No business logic in dialog code
- Service layer handles all data operations

**Principle IV: Test-Driven Development** ✓
- Unit tests required for all save operations
- Integration tests for full workflow
- User acceptance testing mandatory before completion

---

## Version History

- v1.0 (2026-02-06): Initial specification based on paper prototype validation
