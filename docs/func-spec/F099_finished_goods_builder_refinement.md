# F099: FinishedGoods Builder Refinement

**Version**: 1.0  
**Priority**: HIGH  
**Type**: UI Enhancement  

**Created**: 2026-02-08  
**Status**: Draft  

---

## Executive Summary

Current gaps:
- ❌ Builder auto-loads all FinishedGoods on open (slow, doesn't match mental model)
- ❌ No distinction between atomic building blocks and user-built assemblies
- ❌ User forced to see hundreds of items before making filter selections
- ❌ "Bare items only" terminology doesn't align with FinishedUnit concept
- ❌ Builder allows editing atomic FinishedGoods (unnecessary complexity)

This spec refines the builder to start blank, prompt for filter selections first, distinguish between FinishedUnits (building blocks) and assembled FinishedGoods, and only allow creation/editing of assembled bundles.

---

## Problem Statement

**Current State (AUTO-LOAD ALL):**
```
Create Finished Good Button Clicked
├─ ❌ Immediately loads ALL FinishedGoods (hundreds of items)
├─ ❌ Slow performance (loads before user makes choices)
├─ ❌ Shows atomic + assembled mixed together
└─ ❌ User must scroll through long list to find items

Step 1: Food Selection
├─ ❌ "Bare items only" toggle unclear (what is "bare"?)
├─ ❌ Shows atomic FinishedGoods created from recipes
└─ ❌ Mental model: user thinks "show building blocks" not "show bare"

Edit Atomic FinishedGood
├─ ❌ Opens full builder with multi-select components
├─ ❌ Unnecessary - atomic items have single component
└─ ❌ Should edit recipe instead, not FinishedGood

Mental Model Misalignment
├─ ❌ Builder treats all FinishedGoods same way
├─ ❌ Doesn't distinguish building blocks from compositions
└─ ❌ User confused about what they're building
```

**Target State (BLANK START WITH PROMPTS):**
```
Create Finished Good Button Clicked
├─ ✅ Dialog opens BLANK (no items loaded yet)
├─ ✅ Step 1 shows filter prompts: "What are you building?"
└─ ✅ Items load only after user makes filter selections

Step 1: Filter Selection First
├─ ✅ "Building blocks" = FinishedUnits (atomic, from recipes)
├─ ✅ "Existing assemblies" = FinishedGoods where is_assembled=True
├─ ✅ "Both" = show both types
├─ ✅ Category filter appears after type selection
└─ ✅ Load items only after filters applied

Mental Model Alignment
├─ ✅ FinishedUnits = building blocks (terminology clear)
├─ ✅ Assemblies = user-built bundles (what builder creates)
├─ ✅ Builder only creates assembled FinishedGoods (is_assembled=True)
└─ ✅ Atomic FinishedGoods not editable via builder

Performance Improvement
├─ ✅ No auto-load on open (instant dialog display)
├─ ✅ Load only filtered subset (faster queries)
└─ ✅ User in control of what loads when
```

---

## User Testing Validation

**Discovery from Applied Testing (2026-02-08):**

**Finding 1:** Auto-loading all items is slow and doesn't match workflow
- Baker wants to specify what they're building BEFORE seeing options
- Current model: "Here are 500 items, now filter them"
- Desired model: "What type of thing? What category? Now show me relevant items"

**Finding 2:** "Bare items only" terminology confusing
- Baker thinks in terms of "building blocks" not "bare vs packaged"
- FinishedUnits are the atomic units from recipes
- These are what you BUILD WITH, not "bare finished goods"

**Finding 3:** Builder showing all FinishedGoods together causes confusion
- Atomic items (auto-created from recipes) mixed with user-built assemblies
- No visual distinction between "what I can build with" vs "what I already built"
- User wants: "Show me my building blocks (FinishedUnits)" as primary selection

**Conclusion:** Start blank, prompt for filters first, load only relevant items, align terminology with mental model (FinishedUnits = building blocks).

---

## CRITICAL: Study These Files FIRST

**Before implementation, spec-kitty planning phase MUST read and understand:**

1. **Current Builder Implementation**
   - Find FinishedGoods builder dialog UI file
   - Study: Current Step 1 implementation (item loading, filters)
   - Note: Where items loaded (on dialog open? on step expand?)
   - Understand: Current filter toggle implementation ("Bare items only")

2. **Query Methods for FinishedUnits vs FinishedGoods**
   - `src/services/finished_unit_service.py` - list methods
   - `src/services/finished_good_service.py` - list methods with is_assembled filter
   - Study: How to query atomic vs assembled separately
   - Note: Category filtering patterns

3. **is_assembled Field (F098 Dependency)**
   - Understand: is_assembled=False means auto-created atomic FG
   - Understand: is_assembled=True means user-built assembly
   - Query pattern: filter FinishedGoods by is_assembled value

4. **Filter Control Patterns**
   - Study existing category filter implementations
   - Note multi-stage filter patterns (type → category → search)
   - Understand progressive disclosure UI patterns

5. **Performance Optimization Patterns**
   - Find lazy loading implementations
   - Study deferred query patterns (load on demand)
   - Note pagination or limit patterns if applicable

---

## Requirements Reference

This specification implements:
- **Constitution Principle I**: User-Centric Design & Workflow Validation
  - Features MUST solve actual user problems (slow load, confusing terminology)
  - UI MUST be intuitive (filters before results)
  - Workflows MUST match natural baking planning (select type → category → items)
  - User testing MUST validate major features (✓ completed 2026-02-08)

- **Constitution Principle VI.F**: Performance & Scalability
  - UI MUST remain responsive with large datasets (lazy loading)
  - Queries MUST be optimized (load filtered subset, not all items)
  - User interactions MUST feel instant (no unnecessary delays)

From: `.kittify/memory/constitution.md` (v1.4.0)

---

## Functional Requirements

### FR-1: Blank Start with Filter Prompts

**What it must do:**
- Dialog opens with Step 1 expanded showing NO items loaded
- Display filter selection prompts before showing any item list
- Prompt: "What are you building?" with options: "From building blocks" / "From existing assemblies" / "Both"
- Load items only after user selects item type filter
- Provide clear instructions: "Select item type and category to see available items"

**Initial state requirements:**
- No FinishedUnits or FinishedGoods loaded on dialog open
- Item list area shows placeholder: "Select filters above to see available items"
- Filter controls visible and enabled
- Category filter visible but secondary (shown after type selection)

**User interaction flow:**
1. Dialog opens → blank state with filter prompts
2. User selects "From building blocks" (FinishedUnits)
3. Category filter becomes prominent
4. User selects category (or "All")
5. Items load and display in list
6. User can change filters to reload different items

**Performance benefit:**
- Dialog opens instantly (no query executed)
- Only filtered subset loaded (not entire catalog)
- User controls when data loads

**Success criteria:**
- [ ] Dialog opens with no items loaded
- [ ] Filter prompts clearly visible
- [ ] Items load only after filters selected
- [ ] Dialog opens in <200ms regardless of catalog size
- [ ] Placeholder text guides user to select filters

---

### FR-2: Replace "Bare Items" with "Building Blocks" (FinishedUnits)

**What it must do:**
- Remove "Bare items only" / "Include pre-packaged" toggle terminology
- Replace with clear options: "Building Blocks (FinishedUnits)" / "Existing Assemblies" / "Both"
- Query FinishedUnits when "Building Blocks" selected
- Query assembled FinishedGoods (is_assembled=True) when "Existing Assemblies" selected
- Query both when "Both" selected

**Filter options:**
- **"Building Blocks"** - Shows FinishedUnits (atomic items from recipes)
  - Description: "Items created from recipes - use these to build bundles"
  - Queries: FinishedUnit table directly OR FinishedGoods where is_assembled=False
  
- **"Existing Assemblies"** - Shows assembled FinishedGoods
  - Description: "Bundles you've already created - reuse in larger assemblies"
  - Queries: FinishedGoods where is_assembled=True
  
- **"Both"** - Shows all available items
  - Description: "All building blocks and assemblies"
  - Queries: Both FinishedUnits and assembled FinishedGoods

**Terminology alignment:**
- "Building Blocks" clearer than "bare items"
- "Existing Assemblies" clearer than "include assemblies"
- "FinishedUnits" shown in parentheses (educate user on data model)

**Success criteria:**
- [ ] "Bare items only" toggle removed
- [ ] New filter options use clear terminology
- [ ] Queries return correct item types
- [ ] Description text helps user understand distinction
- [ ] User testing confirms terminology is clearer

---

### FR-3: Defer Item Loading Until Filters Applied

**What it must do:**
- Execute query only after user selects item type and optionally category
- Show loading indicator while query executes
- Display results in item list once loaded
- Allow filter changes to reload different items
- Cache results to avoid re-querying on filter toggle (optional optimization)

**Loading states:**
- **Initial state:** "Select filters to see items"
- **Loading state:** "Loading items..." with spinner
- **Loaded state:** "Showing X items" with list
- **Empty state:** "No items match filters" with suggestion to adjust

**Query trigger:**
- User selects item type → query executes
- User changes category → query re-executes with new filters
- User types in search → query re-executes with search term
- Debounce search input (wait 300ms after typing stops)

**Performance considerations:**
- Limit query to 100 items max per filter (add pagination if needed)
- Index on is_assembled field for fast filtering
- Category filter narrows results efficiently

**Success criteria:**
- [ ] No query executed on dialog open
- [ ] Query triggered only after filters selected
- [ ] Loading indicator shown during query
- [ ] Results display after query completes
- [ ] Filter changes reload items correctly

---

### FR-4: Category Filter Appears After Type Selection

**What it must do:**
- Show category filter prominently after item type selected
- Filter categories appropriate to selected type (ProductCategory for building blocks)
- Support "All Categories" option to show unfiltered results
- Combine type filter + category filter for precise results

**Filter interaction:**
- Type filter primary (must select first)
- Category filter secondary (becomes available after type selected)
- Search tertiary (further narrows type + category results)

**Category filtering rules:**
- If "Building Blocks" selected → show ProductCategories (Cakes, Cookies, etc.)
- If "Existing Assemblies" selected → show ProductCategories (bundles inherit from components)
- If "Both" selected → show ProductCategories (applies to both types)

**UI progression:**
```
1. Select Type: [Building Blocks ▼]
   ↓
2. Select Category: [All ▾] [Cakes] [Cookies] [Brownies]...
   ↓
3. Search: [_____________] 🔍
   ↓
4. Results: [List of matching items]
```

**Success criteria:**
- [ ] Category filter visible after type selection
- [ ] Category options appropriate to item type
- [ ] "All Categories" option available
- [ ] Combined filters return precise results
- [ ] UI progression feels natural and guided

---

### FR-5: Builder Only Creates Assembled FinishedGoods

**What it must do:**
- Set is_assembled=True on all FinishedGoods created via builder
- Never create FinishedGoods with is_assembled=False (those are auto-generated from FinishedUnits)
- Validate that builder never used to create atomic items
- Enforce minimum 1 component requirement (can't build assembly with zero items)

**Creation logic:**
- User completes Step 1 (food selection) + Step 2 (materials) + Step 3 (review)
- On Save: Create FinishedGood with is_assembled=True
- Create FinishedGoodComponents for all selected items
- Result: New assembled bundle available for future use

**Validation rules:**
- Minimum 1 food item (building block or existing assembly)
- Materials optional (can be food-only bundle)
- Name must be unique among FinishedGoods
- At least 1 component total (food or material)

**Success criteria:**
- [ ] All builder-created FGs have is_assembled=True
- [ ] No atomic FGs (is_assembled=False) created via builder
- [ ] Validation enforces minimum components
- [ ] Created assemblies appear in "Existing Assemblies" filter

---

### FR-6: Remove Edit Capability for Atomic FinishedGoods

**What it must do:**
- Detect if FinishedGood being edited is atomic (is_assembled=False)
- Block edit action with message: "This item is auto-created from a recipe. Edit the recipe to change it."
- Provide link/button to open recipe for editing (optional enhancement)
- Only allow builder to edit assembled FinishedGoods (is_assembled=True)

**Detection logic:**
- User clicks Edit on FinishedGood in list
- Check is_assembled field
- If False → show message, block builder open
- If True → open builder with pre-populated selections

**User guidance:**
- Clear message explaining why edit blocked
- Suggestion: "To change this item, edit its source recipe"
- Optional: Direct link to recipe edit form

**Edit flow for assembled FGs:**
- User clicks Edit on assembled FinishedGood
- Builder opens with existing components loaded
- User modifies selections, saves updates
- Updated FinishedGood remains is_assembled=True

**Success criteria:**
- [ ] Edit action detects is_assembled field
- [ ] Atomic FGs cannot be edited via builder
- [ ] Clear message explains why edit blocked
- [ ] Assembled FGs open for editing normally
- [ ] User testing confirms no confusion

---

## Edge Cases

### Edge Case 1: No Items Match Filters
**Scenario:** User selects type + category with zero matching items
**Behavior:** Display empty state: "No items in this category. Try different filters or create new recipes."
**Validation:** Suggest adjusting filters or creating new source content

### Edge Case 2: Very Large Category
**Scenario:** Category has 500+ items after filtering
**Behavior:** Limit display to 100 items, show message: "Showing first 100 items. Use search to narrow results."
**Validation:** Search becomes required for large result sets

### Edge Case 3: Filter Changes with Selections Made
**Scenario:** User selects items, then changes type/category filter
**Behavior:** Decision needed - clear selections OR preserve if still valid?
**Validation:** Warn user if filter change will clear selections

### Edge Case 4: Both Filter with Many Items
**Scenario:** "Both" selected showing FinishedUnits + Assemblies together
**Behavior:** Clearly distinguish types visually (icons, labels, grouping)
**Validation:** User can tell building blocks from assemblies in mixed list

### Edge Case 5: Edit Atomic FG Accidentally
**Scenario:** User clicks Edit on auto-generated FinishedGood
**Behavior:** Block action, show message with guidance
**Validation:** User understands why blocked and what to do instead

### Edge Case 6: Category Deleted with Items
**Scenario:** Category deleted but items still exist with that category
**Behavior:** Items appear in "Uncategorized" or null category filter
**Validation:** User can still find and use items

### Edge Case 7: Slow Query on Large Catalog
**Scenario:** Query takes >2 seconds on large dataset
**Behavior:** Show loading indicator, consider pagination or limit
**Validation:** User sees feedback, doesn't think dialog frozen

---

## Success Criteria

### Measurable Outcomes

**SC-001: Performance Improvement**
- Dialog opens in <200ms regardless of catalog size (no auto-query)
- Filtered item load completes in <1 second for typical filters
- User perceives instant dialog open (subjective but measurable)

**SC-002: Terminology Clarity**
- User testing: 100% of users understand "Building Blocks" vs "Existing Assemblies"
- Zero questions about "what is bare?" (old terminology eliminated)
- User correctly identifies FinishedUnits as recipe outputs without prompting

**SC-003: Workflow Naturalness**
- User completes filter selection → item load → selection workflow without confusion
- Zero instances of "why is the list empty?" (because prompts explain)
- Filter-first workflow feels intuitive in user testing

**SC-004: Data Integrity**
- 100% of builder-created FinishedGoods have is_assembled=True
- Zero atomic FinishedGoods (is_assembled=False) created via builder post-F099
- Edit protection prevents modification of atomic FGs

**SC-005: User Experience Validation**
- Primary user (Marianne) confirms: "Builder feels faster and clearer"
- User can build mixed bundle with new workflow without assistance
- Zero confusion about what items are building blocks vs assemblies

---

## User Scenarios & Testing

### User Story 1 - Fast Dialog Open with Guided Workflow (Priority: P1)

**Scenario:** Baker opens Create Finished Good dialog and immediately sees what to do next.

**Why this priority:** Core UX improvement - eliminates slow auto-load and confusion about starting point.

**Independent Test:** Can be fully tested by clicking Create button, measuring load time, verifying filters shown before items.

**Acceptance Scenarios:**

1. **Given** Finished Goods tab open, **When** user clicks "Create Finished Good", **Then** dialog opens in <200ms with blank item list and filter prompts visible

2. **Given** dialog open with no filters selected, **When** user looks at Step 1, **Then** placeholder text says "Select item type and category to see available items"

3. **Given** catalog has 500 FinishedUnits, **When** dialog opens, **Then** no performance delay (items not loaded yet)

---

### User Story 2 - Clear Terminology for Item Types (Priority: P1)

**Scenario:** Baker selects "Building Blocks" and understands these are recipe outputs to build with.

**Why this priority:** Eliminates terminology confusion identified in user testing.

**Independent Test:** Can be tested by user selecting filters and verifying correct items load.

**Acceptance Scenarios:**

1. **Given** Step 1 open with no selection, **When** user sees filter options, **Then** choices are "Building Blocks (FinishedUnits)" / "Existing Assemblies" / "Both" with descriptions

2. **Given** user selects "Building Blocks", **When** items load, **Then** only FinishedUnits (atomic items from recipes) display

3. **Given** user selects "Existing Assemblies", **When** items load, **Then** only assembled FinishedGoods (is_assembled=True) display

4. **Given** user testing session, **When** asked "What are building blocks?", **Then** user correctly explains "items from recipes I build with"

---

### User Story 3 - Filter-Driven Item Loading (Priority: P1)

**Scenario:** Baker selects type and category, sees only relevant items load.

**Why this priority:** Performance and UX - user controls what loads when.

**Independent Test:** Can be tested by selecting different filter combinations and verifying correct subsets load.

**Acceptance Scenarios:**

1. **Given** "Building Blocks" selected, **When** user selects "Cookies" category, **Then** query executes and only cookie FinishedUnits display

2. **Given** items loaded for "Cookies", **When** user changes to "Cakes", **Then** new query executes and cake items replace cookie items

3. **Given** user types "chocolate" in search, **When** typing stops for 300ms, **Then** results filter to show only items matching "chocolate"

---

### User Story 4 - Edit Protection for Atomic Items (Priority: P2)

**Scenario:** Baker accidentally tries to edit auto-generated FinishedGood, receives clear guidance.

**Why this priority:** Important for data integrity but less common than creation workflow.

**Independent Test:** Can be tested by clicking Edit on atomic FG, verifying block message shown.

**Acceptance Scenarios:**

1. **Given** atomic FinishedGood (is_assembled=False) in list, **When** user clicks Edit, **Then** message displays: "This item is auto-created from a recipe. Edit the recipe to change it."

2. **Given** assembled FinishedGood (is_assembled=True) in list, **When** user clicks Edit, **Then** builder opens with components loaded for modification

3. **Given** user sees block message, **When** user reads message, **Then** understands to edit recipe instead (verified in user testing)

---

### User Story 5 - Progressive Filter Workflow (Priority: P2)

**Scenario:** Baker follows natural progression: type → category → search → select.

**Why this priority:** Nice UX flow but not critical for core functionality.

**Independent Test:** Can be tested by observing user's natural workflow without guidance.

**Acceptance Scenarios:**

1. **Given** dialog open, **When** user first action, **Then** naturally selects item type (not searching or scrolling blank list)

2. **Given** type selected, **When** user looks for next step, **Then** category filter is prominent and obvious next action

3. **Given** category selected with many items, **When** user wants specific item, **Then** search narrows results effectively

---

## Dependencies

**Required Features (Must be Complete):**
- F098: Auto-Generation of FinishedGoods from FinishedUnits (provides is_assembled field)
- FinishedUnit service with list methods (existing)
- FinishedGood service with is_assembled filtering (F098 adds this)

**Blocks These Features:**
- F100: FinishedGoods Management UI Split (depends on builder only showing assembled FGs)

**Related Features (Reference but not blocking):**
- F097: FinishedGoods Builder UI (original implementation, now refined)

---

## Testing Strategy

### Unit Tests
- Filter query logic (type + category combinations)
- is_assembled validation on save
- Edit protection for atomic FGs
- Search filter debouncing
- Empty state handling

### Integration Tests
- Complete workflow: open dialog → select filters → load items → create assembly
- Filter changes reload correct items
- Edit assembled FG pre-populates builder
- Edit atomic FG shows block message
- Performance: dialog open <200ms

### User Acceptance Tests
With primary user (Marianne):
1. Open Create Finished Good dialog, verify feels fast and clear what to do
2. Select "Building Blocks" + "Cookies", verify correct items load
3. Build mixed cookie bundle using workflow
4. Try to edit auto-generated FinishedGood, verify block message clear
5. Edit existing assembled bundle, verify works normally

**Success Criteria:** All 5 scenarios completed without confusion, user confirms "faster and clearer"

---

## Constitutional Compliance

**Principle I: User-Centric Design & Workflow Validation** ✓
- Addresses user testing pain points (slow load, confusing terminology)
- Filter-first workflow matches natural planning process
- Validated through applied user testing (2026-02-08)

**Principle VI.F: Performance & Scalability** ✓
- Lazy loading eliminates slow dialog open
- Filtered queries more efficient than loading all items
- Responsive UI with large catalogs

**Principle V: Layered Architecture Discipline** ✓
- UI layer handles filter controls and display
- Service layer handles filtered queries
- Clear separation between FinishedUnit and FinishedGood queries

---

## Version History

- v1.0 (2026-02-08): Initial specification based on user testing insights
