# F100: Planning FG Selection Refinement

**Version**: 1.0  
**Priority**: HIGH  
**Type**: UI Enhancement  

**Created**: 2026-02-09  
**Status**: Draft  

---

## Executive Summary

Current gaps:
- ❌ Recipe selection auto-loads all recipes (slow, doesn't match F099 UX pattern)
- ❌ FG selection shows all available items without progressive filtering
- ❌ User must scroll through potentially hundreds of items to find desired FGs
- ❌ No clear buttons ("Clear All" or "Clear Finished Goods") or "Show All Selected" workflow support
- ❌ Filter changes lose selection state
- ❌ No dedicated quantity specification step after selections made

This spec refines Planning FG selection workflow to match F099 (Finished Goods Builder) UX patterns: start blank with filter prompts (progressive disclosure), independent combinatorial filters, selection persistence across filter changes, and clear selection management.

---

## Problem Statement

**Current State (AUTO-LOAD ALL):**
```
Recipe Selection (F069)
├─ ❌ Auto-loads all recipes on event selection
├─ ❌ User must scroll to find recipes before filtering
└─ ❌ Doesn't match F099 "blank start" pattern

FG Selection (F070/F071)
├─ ✅ Filtered by selected recipes (F070)
├─ ✅ Quantity inputs per FG (F071)
├─ ❌ Shows all available FGs immediately (no progressive filters)
├─ ❌ User must scroll through long lists
├─ ❌ Changing filters loses selections
├─ ❌ No clear buttons ("Clear All" / "Clear Finished Goods")
└─ ❌ No "Show All Selected" view

Quantity Specification
└─ ❌ Inline with selection (no dedicated review step)
```

**Target State (FILTER-FIRST WITH INDEPENDENT FILTERS):**
```
Recipe Selection (F069 Enhanced)
├─ ✅ Starts blank with filter prompts
├─ ✅ Recipe category filter applied FIRST
├─ ✅ Recipes load only after category selected
└─ ✅ Matches F099 progressive disclosure pattern

FG Selection (F070/F071 Enhanced)
├─ ✅ Starts blank with filter prompts
├─ ✅ Three independent filters visible: recipe category, item type, yield type
├─ ✅ User sets filters in any order (combinatorial AND logic)
├─ ✅ FGs load only after filters applied
├─ ✅ Selections persist when filters change
├─ ✅ "Clear All" button (full reset: recipes + FGs + quantities)
├─ ✅ "Clear Finished Goods" button (reset FGs + quantities, keep recipes)
└─ ✅ "Show All Selected" shows only selected items (temporary filter override)

Quantity Specification Step
├─ ✅ Dedicated section after selections finalized
├─ ✅ Shows only selected FGs with quantity inputs
└─ ✅ Clear review before saving to database
```

---

## CRITICAL: Study These Files FIRST

**Before implementation, spec-kitty planning phase MUST read and understand:**

1. **F099 (Finished Goods Builder Refinement)**
   - Find: `docs/func-spec/F099_finished_goods_builder_refinement.md`
   - Study: "Blank start with filter prompts" pattern (FR-1, lines 125-189)
   - Study: Progressive filter workflow (FR-4, lines 263-297)
   - Note: Why this pattern works (user testing validation, lines 79-98)
   - **KEY**: Apply exact same UX pattern to Planning workflow

2. **Current Planning Tab Implementation**
   - Find: `src/ui/planning_tab.py`
   - Study: How recipe selection frame shown (lines 549-583)
   - Study: How FG selection frame shown (lines 652-691)
   - Note: Session management and refresh patterns
   - Understand: Multi-section planning workflow structure

3. **Recipe Selection Frame (F069)**
   - Find: `src/ui/components/recipe_selection_frame.py`
   - Study: Current checkbox list implementation
   - Note: Selection tracking with `_recipe_vars` dict
   - Understand: Save/Cancel pattern

4. **FG Selection Frame (F070/F071)**
   - Find: `src/ui/components/fg_selection_frame.py`
   - Study: Current FG list with quantity inputs
   - Note: Grid layout (checkbox, quantity entry, feedback label)
   - Understand: Quantity validation pattern (lines 311-339)

5. **Recipe and FG Data Models**
   - Find: Recipe categories (ProductCategory enum)
   - Find: `FinishedGood.is_assembly` field (F098 dependency)
   - Find: `FinishedGood.yield_unit_type` field
   - Understand: How to query by these fields

---

## Requirements Reference

This specification implements:
- **REQ-UX-001**: Progressive disclosure reduces cognitive load (established in F099)
- **REQ-UX-002**: Filter-first workflow matches user mental model (established in F099)
- **REQ-PLAN-022**: Recipe selection must support category filtering before display
- **REQ-PLAN-023**: FG selection must support independent combinatorial filtering (category, type, yield with AND logic)
- **REQ-PLAN-024**: Selection state must persist across filter changes
- **REQ-PLAN-025**: User must be able to clear selections (two-level: all vs FGs-only) and show only selected items
- **REQ-PLAN-026**: Quantity validation must reject zero, decimals, and negative numbers
- **REQ-PLAN-027**: Quantities must persist in UI state when navigating between planning steps
- **REQ-EDIT-001**: Initial plan creation (this spec) is separate from edit mode (F077/F078)

From: `docs/func-spec/F099_finished_goods_builder_refinement.md` (UX patterns)  
From: F077/F078 (Plan State Management & Amendments)

---

## Functional Requirements

### FR-1: Recipe Selection with Category Filter First

**What it must do:**
- Recipe selection frame starts blank (no recipes loaded)
- Display recipe category filter dropdown prominently
- Load and display recipes only after user selects category
- Support "All Categories" option to show all recipes
- Filter changes reload recipe list while preserving selection state

**UI Requirements:**
- Blank state shows filter prompt: "Select recipe category to see available recipes"
- Category filter dropdown visible immediately
- Recipe list area shows placeholder until filter applied
- Selection checkboxes and counts update when list loads

**Pattern reference:** Study F099 FR-1 (lines 154-189) - exact same "blank start with filter prompts" pattern

**Success criteria:**
- [ ] Recipe frame opens with no recipes displayed
- [ ] Category filter dropdown shown prominently
- [ ] Recipes load only after category selected
- [ ] "All Categories" option available
- [ ] Selection state preserved when category changed

---

### FR-2: FG Selection Independent Combinatorial Filtering

**What it must do:**
- FG selection frame starts blank (no FGs loaded)
- Display three independent filter dropdowns, all visible at once:
  - **Recipe category**: Filters by recipe category (Cookies, Brownies, Cakes, etc.) or "All Categories"
  - **Item type**: Filters by Finished Units / Assemblies / Both
  - **Yield type**: Filters by EA / SERVING / Both
- User can set filters in any order (no dependencies between filters)
- Filters combine with AND logic to narrow the displayed FG list
- Load and display FGs only after at least one filter applied
- Changing any filter reloads FG list with combined filter criteria

**UI Requirements:**
- Blank state shows filter prompt: "Select filters to see available finished goods"
- All three filter dropdowns visible simultaneously
- No wizard/sequential flow - user controls which filters to apply
- FG list area shows placeholder until at least one filter applied
- FG list updates immediately when any filter changes

**Filter behavior (independent, combinatorial):**
- Recipe category filter: Shows FGs whose recipes match category (or all if "All Categories")
- Item type filter: Shows Finished Units (`is_assembly=False`), Assemblies (`is_assembly=True`), or Both
- Yield type filter: Shows FGs with `yield_unit_type` of EA, SERVING, or Both
- **All active filters use AND logic**: An item must match ALL selected criteria to display
- Example: If user selects "Cookies" + "Finished Units" + "EA", show only Finished Units from cookie recipes with EA yield type

**Pattern reference:** Study F099 FR-1 (blank start) and FR-4 (filter combinations)

**Success criteria:**
- [ ] FG frame opens with no FGs displayed
- [ ] Three filter dropdowns shown simultaneously
- [ ] User can set filters in any order
- [ ] FGs load after any filter applied
- [ ] Recipe category filter narrows by recipe
- [ ] Item type filter works (Finished Units / Assemblies / Both)
- [ ] Yield type filter works (EA / SERVING / Both)
- [ ] Filters combine correctly (AND logic)
- [ ] Changing any filter reloads list immediately

---

### FR-3: Selection Persistence Across Filter Changes

**What it must do:**
- When user checks FG checkbox, store selection state
- When filters change and FG disappears from view, keep checkbox checked
- When filters change and FG reappears, show previous checked state
- User can toggle filters to explore different FGs while building selection list

**Business rules:**
- Selected FG stays selected even when filtered out of view
- Unchecking FG removes from selection regardless of current filters
- Filter changes are for browsing, not for clearing selections

**Pattern reference:** Study how F099 manages selection state during filter changes

**Success criteria:**
- [ ] Checking FG checkbox stores selection
- [ ] Changing filters doesn't uncheck selected FGs
- [ ] Selected FG reappears checked when filters show it again
- [ ] User can freely change filters without losing selections

---

### FR-4: Clear Selections Buttons (Two-Level Clear)

**What it must do:**
- Display TWO clear buttons at planning tab level:
  - **"Clear All"**: Clears recipes + FGs + quantities (full reset to blank state)
  - **"Clear Finished Goods"**: Clears only FG checkboxes + quantities, retains recipe selections
- When clicked, show confirmation dialog appropriate to scope
- Update selection counts after clearing

**UI Requirements:**
- Both buttons visible and clearly labeled
- Button placement at tab level (near Edit/Delete event buttons, outside recipe/FG selection frames)
- Distinct confirmation dialogs:
  - "Clear All" confirmation: "Clear all recipes and finished goods? This resets the entire plan to blank."
  - "Clear Finished Goods" confirmation: "Clear all finished good selections? Recipe selections will remain."

**Placement rationale:**
- Buttons affect multiple sections (recipes + FGs), so belong at tab level not within individual frames
- Near Edit/Delete buttons provides consistent action grouping
- Planning phase determines exact layout

**Business rules:**
- "Clear All" returns planning workflow to initial blank state (Step 1 blank, Step 2 blank)
- "Clear Finished Goods" only affects FG selections, preserves recipe selections for re-filtering
- Both operations require user confirmation before executing
- Canceling confirmation leaves current state unchanged

**Pattern reference:** Standard confirmation pattern used throughout app

**Success criteria:**
- [ ] "Clear All" button visible at tab level (near Edit/Delete buttons)
- [ ] "Clear Finished Goods" button visible at tab level (near Edit/Delete buttons)
- [ ] "Clear All" confirmation shows appropriate warning
- [ ] "Clear All" clears recipes, FGs, and quantities from UI state
- [ ] "Clear Finished Goods" confirmation shows appropriate warning
- [ ] "Clear Finished Goods" clears only FGs and quantities from UI state (recipes remain)
- [ ] Selection counts update correctly after clear
- [ ] Canceling either confirmation leaves selections unchanged

---

### FR-5: Show All Selected Button

**What it must do:**
- Display "Show All Selected" button in FG selection frame
- When clicked, temporarily replace current filter state with "selected items only" view
- Show ONLY selected FGs (all selected items visible regardless of what filters were active)
- Clear indication that view mode is active ("Showing X selected items")
- Button toggles to "Show Filtered View" to return to normal filtering
- Changing any filter while in "selected items only" view returns to normal filter-based display

**UI Requirements:**
- Button visible near filter controls
- Button label changes based on state: "Show All Selected" ↔ "Show Filtered View"
- Visual indicator when "show selected" mode active
- Selection count remains accurate

**Business rules:**
- "Show All Selected" temporarily replaces filter state (does not modify filter settings)
- Toggling back to filtered view restores previous filter settings exactly
- Changing any filter dropdown while in "selected" view exits that view and applies new filter
- Quantities remain editable in "show selected" mode

**Success criteria:**
- [ ] "Show All Selected" button visible
- [ ] Clicking shows only selected FGs (ignores filters)
- [ ] Visual indicator shows "selected only" mode active
- [ ] Button toggles to "Show Filtered View"
- [ ] Clicking "Show Filtered View" restores filters
- [ ] Previous filter settings preserved during toggle

---

### FR-6: Quantity Specification and State Persistence

**What it must do:**
- After FG selections finalized (Save clicked), show quantity specification section
- Display only selected FGs with quantity inputs
- User specifies quantity for each selected FG
- Validate quantities: **positive integers only (no decimals, no zero)**
- Quantity entries persist to UI state only (in-memory) on blur/change
- User can navigate back to Step 2 (FG selection) without losing Step 3 (quantity) data
- All selections (recipes, FGs, quantities) persist in UI state until explicit clear, event close, or final save
- **Database write is atomic**: When user clicks final Save button, write all FG + quantity pairs to `event_finished_goods` table in single transaction

**UI Requirements:**
- Clear section heading: "Specify Quantities for Selected Items"
- List shows FG name and quantity input per selected item
- Quantity validation feedback inline
- Save button disabled if validation errors exist

**Quantity Validation:**
- **Accept**: Positive integers (1, 2, 100, etc.)
- **Reject**: Zero, negative numbers, decimals (0.5, -1, etc.), non-numeric text
- **Error messages**:
  - Empty field when checkbox checked: "Quantity required"
  - Zero entered: "Quantity must be greater than zero"
  - Decimal entered: "Whole numbers only"
  - Negative entered: "Quantity must be positive"
  - Non-numeric: "Enter a valid number"

**State Persistence Behavior (UI State Only):**
- Quantity changes persist to **UI state only** (in-memory, not database) on blur or change event
- Provides semi-persistent state as user navigates between sections
- User can click back to "Select Finished Goods" step to modify selections
- Returning to quantity step shows previously entered quantities (from UI state)
- Quantities remain in UI state until user clicks "Clear Finished Goods", "Clear All", or closes event
- **Database write occurs only on final Save button** - all selections and quantities written atomically to `event_finished_goods` table

**Why UI state only:**
- Transient working state as user builds plan
- Avoids partial database writes during exploration
- Final Save action persists complete plan atomically

**Pattern reference:** Study existing quantity input pattern in `fg_selection_frame.py` (lines 168-191)

**Note:** This may already exist inline with selection (F071). Determine during planning phase whether to enhance existing implementation or create dedicated section.

**Success criteria:**
- [ ] Quantity section shows after FG selections saved
- [ ] Only selected FGs displayed
- [ ] Quantity inputs validate correctly (reject zero, decimals, negatives)
- [ ] Appropriate error messages shown for invalid input
- [ ] Validation prevents saving with errors
- [ ] Quantities persist in UI state when navigating between steps
- [ ] Quantities save to database only on final save
- [ ] User can return to FG selection without losing quantities

---

## Out of Scope

**Explicitly NOT included in this feature:**
- ❌ Recipe search/filtering by name (future enhancement)
- ❌ FG search/filtering by name (future enhancement)
- ❌ Bulk quantity entry (paste from spreadsheet)
- ❌ Historical quantity suggestions (future enhancement)
- ❌ Assembly component breakdown display (future enhancement)
- ❌ Recipe category management (separate feature)
- ❌ Batch calculation (F073 - separate feature)
- ❌ **Edit Mode for saved event plans** (see "Edit Mode Constraints" section below)

---

## Edit Mode Constraints

**Scope Boundary:**
This specification covers **initial plan creation only** (creating a new event plan from blank state). 

**Edit Mode is OUT OF SCOPE - Separate Future Feature:**
- Modifying saved event plans requires separate Edit Plan mode feature
- Edit mode must incorporate plan amendments workflow (F078 - future work)
- Edit mode must enforce state-based constraints (DRAFT/LOCKED/IN_PRODUCTION/COMPLETED)

**Future Work References:**
- **F077 (Plan State Management)**: Defines plan states and transitions
- **F078 (Plan Snapshots & Amendments)**: Defines amendment workflow and audit trail

**Why Edit Mode is Separate:**
- Initial plan creation (this spec): Optimized for blank-start exploratory browsing with filter-first UX
- Edit mode (future): Must enforce state validation, create amendment records, maintain audit trail
- Different user workflows: Create = exploratory, Edit = constrained modifications
- Separating concerns keeps this spec focused on validated UX patterns from F099

**Current Scope Only:**
- User creates new event plan from blank state
- No existing recipe/FG selections to modify
- No state validation constraints
- No amendment records needed
- Optimized for discovery and selection building

---

## Success Criteria

**Complete when:**

### Recipe Selection Enhancement
- [ ] Recipe frame starts blank with category filter
- [ ] Recipes load only after category selected
- [ ] "All Categories" option works
- [ ] Selection state persists across category changes
- [ ] Pattern matches F099 progressive disclosure

### FG Selection Enhancement
- [ ] FG frame starts blank with filter prompts
- [ ] Three independent filters visible simultaneously (recipe category, item type, yield type)
- [ ] User can set filters in any order
- [ ] Filters combine with AND logic correctly
- [ ] FGs load only after at least one filter applied
- [ ] Changing any filter reloads FG list immediately
- [ ] Pattern matches F099 blank-start approach

### Selection Management
- [ ] Selections persist when filters change
- [ ] Selected FGs stay checked when filtered out of view
- [ ] "Clear All" button clears recipes + FGs + quantities with confirmation
- [ ] "Clear Finished Goods" button clears only FGs + quantities (keeps recipes) with confirmation
- [ ] "Show All Selected" button shows only selected items (temporary filter override)
- [ ] Changing any filter while in "selected items" view returns to normal filtering
- [ ] Toggle between filtered and selected views works

### Quantity Specification
- [ ] Quantity inputs work for all selected FGs
- [ ] Validation rejects zero, decimals, negative numbers, non-numeric input
- [ ] Appropriate error messages shown for each validation failure type
- [ ] Quantities persist to UI state only (in-memory) on blur/change
- [ ] User can navigate back to FG selection without losing quantities from UI state
- [ ] Quantities remain in UI state until explicit clear, event close, or final save
- [ ] Database write occurs only on final Save button click (atomic write of all selections + quantities)
- [ ] Saved quantities load correctly when event reopened

### User Experience
- [ ] No auto-loading of long lists (fast dialog open)
- [ ] User understands filter workflow without instruction
- [ ] Selection workflow feels natural and efficient
- [ ] User testing confirms improved UX vs current state

### Quality
- [ ] Code follows established UI component patterns
- [ ] Session management correct (uses provided session)
- [ ] Error handling consistent with project
- [ ] Performance acceptable with large catalogs

---

## Architecture Principles

### Progressive Disclosure Pattern (F099 Reference)

**Blank-Start Filter-First Workflow:**
- Frame opens blank (no items loaded yet)
- User specifies WHAT they're looking for (applies filters in any order)
- System shows relevant items (filtered list combining all active filters)
- User makes selections (checkboxes)
- System persists choices (database)

**Why this matters:**
- Reduces cognitive load (starts simple, user controls complexity)
- Matches user mental model (think → filter → browse → select)
- Improves performance (loads filtered subset, not all items)
- Validated through user testing (F099, lines 79-98)

### Selection State Management

**Persistence Strategy:**
- Selection state independent from display state
- Filters control WHAT IS SHOWN, not WHAT IS SELECTED
- User builds selection list while exploring via filters
- "Show All Selected" provides selection review

**UI State vs Database:**
- **Working state (UI only)**: Recipes, FG selections, quantities persist in-memory as user builds plan
- **Transient storage**: Survives navigation between planning sections, lost on event close
- **Atomic save**: Final Save button writes complete plan (recipes + FGs + quantities) to database in single transaction
- **Why UI state only**: Avoids partial writes during exploration, enables atomic rollback on cancel

**Why this matters:**
- User can freely change filters without losing work
- Enables exploratory browsing while building list
- Reduces frustration from accidental filter changes
- Clean separation between working state and committed state

### Independent Combinatorial Filtering

**Filter Composition:**
- Three independent filter dimensions (recipe category, item type, yield type)
- All filters visible simultaneously (no sequential/wizard flow)
- User can set filters in any order they choose
- Filters combine with AND logic to narrow results
- "All" or "Both" options disable that filter dimension

**Why this matters:**
- User browses naturally - add/remove filters as they think
- No forced workflow - user decides which filters matter
- Supports exploratory discovery (try different combinations)
- Reduces scrolling through irrelevant items

### Create vs Edit Separation

**This Spec: Initial Plan Creation Only:**
- User starts with blank event (no existing recipe/FG selections)
- Exploratory browsing workflow with filter-first approach
- No state validation constraints (no LOCKED/IN_PRODUCTION checks)
- Optimized for discovery and selection building

**Edit Mode (F077/F078 - Separate Concern):**
- User modifies existing saved plan
- Must respect plan state (DRAFT editable, LOCKED/IN_PRODUCTION requires amendments, COMPLETED read-only)
- Audit trail requirements (snapshot + amendment records)
- State transition validation

**Why this separation matters:**
- Create workflow optimized for UX without state machinery overhead
- Edit workflow enforces business rules and audit requirements
- Clear boundary prevents feature creep in this spec
- Services can share selection persistence logic but wrap with appropriate state checks

---

## Constitutional Compliance

✅ **Principle I: User-Centric Design & Workflow Validation**
- Applies validated UX pattern from F099 user testing
- Filter-first workflow matches baker's mental model
- Progressive disclosure reduces cognitive load
- Selection persistence prevents frustration

✅ **Principle VI.F: Performance & Scalability**
- No auto-loading prevents slow dialog open
- Filtered queries more efficient than loading all items
- UI remains responsive with large catalogs

✅ **Principle V: Layered Architecture Discipline**
- UI layer handles filter controls and display
- Service layer handles filtered queries
- Clear separation maintained

✅ **Principle III: Pattern Consistency**
- Recipe selection matches FG builder pattern (F099)
- FG selection matches FG builder pattern (F099)
- Consistent UX across Planning and Production workflows

---

## Risk Considerations

**Risk: User confused by blank start**
- **Context:** Current implementation auto-loads all items; change to blank start might confuse users
- **Mitigation:** Clear placeholder text explains next action: "Select filters to see available items." F099 user testing validated this approach.

**Risk: Selection state complexity**
- **Context:** Tracking selections while filters change requires careful state management
- **Mitigation:** Planning phase should study existing checkbox state management patterns. Consider using Set data structure for selected IDs.

**Risk: Filter interaction complexity**
- **Context:** Three filter stages (recipe category, item type, yield type) could confuse users
- **Mitigation:** Planning phase determines UI approach (all visible vs progressive reveal). Test with user to validate.

**Risk: Performance with large FG catalogs**
- **Context:** Even with filtering, some categories might have hundreds of FGs
- **Mitigation:** Planning phase should consider pagination or limit patterns if needed. Load performance testing required.

**Risk: Quantity specification step integration**
- **Context:** F071 already implements inline quantity inputs; this spec suggests dedicated step
- **Mitigation:** Planning phase determines whether to enhance existing inline pattern or create separate section. Review F071 implementation first.

**Risk: Transient UI state data loss**
- **Context:** Quantities and selections stored in UI state only; closing event or browser crash loses work
- **Mitigation:** Acceptable for initial plan creation workflow. User completes planning session, then clicks Save to persist. Consider auto-save draft feature in future enhancement if user feedback indicates need.

**Risk: Clear button placement**
- **Context:** "Clear All" affects multiple sections (recipes + FGs); placement at tab level might not be obvious
- **Mitigation:** Planning phase determines exact button positioning near Edit/Delete buttons. Consider visual grouping or section header to clarify scope.

---

## Notes for Implementation

**Pattern Discovery (Planning Phase):**
- Study F099 FR-1 (blank start pattern) → apply to recipe selection and FG selection
- Study F099 FR-4 (progressive filtering) → apply to FG multi-stage filters
- Study `RecipeSelectionFrame` → understand checkbox list structure
- Study `FGSelectionFrame` → understand grid layout with quantity inputs
- Study filter dropdown patterns used elsewhere in app

**Key Patterns to Copy:**
- F099 blank start UI pattern → Recipe/FG selection frames (exact parallel)
- F099 filter-first workflow → Planning filter workflow (exact parallel)
- Checkbox state management → Selection persistence across filter changes
- Quantity validation pattern (F071) → Quantity specification step

**Focus Areas:**
- **UX consistency:** Recipe and FG selection must feel like same workflow (both use F099 pattern)
- **State management:** Selection state must survive filter changes without data loss
- **Performance:** Filtered queries must be fast enough for real-time filtering
- **User feedback:** Clear indication of what filters are active and what selections exist

**Integration Points:**
- Recipe selection affects FG availability (F070 dependency)
- FG selection quantities affect batch calculations (F073 dependency)
- Planning state management affects downstream workflows

**Discovery Questions for Planning Phase:**
- How are recipe categories currently stored and queried?
- What is the data structure for `yield_unit_type` enum?
- What is optimal layout for three independent filter dropdowns (horizontal row, vertical stack, etc.)?
- Should "Show All Selected" be a toggle button or separate view?
- Should quantity specification be inline (F071 current) or dedicated section?
- How to efficiently query with combined filters (three WHERE clauses with AND)?
- Where exactly should "Clear All" and "Clear Finished Goods" buttons be positioned at tab level (near Edit/Delete buttons)?
- How to implement UI state persistence for quantities during navigation (component state, service layer cache, etc.)?

---

## User Scenarios

### Scenario 1: User Plans Holiday Event
1. Opens Planning tab, selects event
2. Recipe selection frame opens blank with category filter
3. Selects "Cookies" category → sees cookie recipes only
4. Checks desired cookie recipes, clicks Save
5. FG selection frame opens blank with three filter dropdowns visible
6. Selects "Cookies" category first → sees cookie FGs (all types and yields)
7. Too many results, adds "Finished Units" filter → list narrows to cookie finished units only
8. Still browsing, adds "EA" filter → sees only EA cookie finished units
9. Checks desired FGs, then changes recipe category to "Brownies" to explore
10. Previous cookie selections remain checked (not lost), now sees brownie FGs with same type/yield filters
11. Checks brownie FGs, clicks "Show All Selected" to review complete list
12. Sees only checked FGs (all cookies + brownies, ignoring current filters), specifies quantities (stored in UI state)
13. Reviews all quantities, clicks final Save button → all recipes, FG selections, and quantities write to database atomically

### Scenario 2: User Explores with Different Filter Combinations
1. User starts with "All Categories" + "Assemblies" + "SERVING" to see serving-size bundles
2. Selects several bundles, then wants to see individual cookies too
3. Changes item type filter to "Both" (assemblies + finished units)
4. Assembly selections remain checked, now also sees finished units
5. Narrows to "Cookies" category to focus search
6. Previous non-cookie selections remain checked (not lost)
7. Adds cookie finished units to existing selection list
8. Clicks "Show All Selected" to review: sees assemblies + cookies mixed
9. Specifies quantities and saves

### Scenario 3: User Wants Fresh Start (Two Clear Options)

**Option A - Full Reset:**
1. User has recipes + FGs + quantities entered
2. Realizes entire plan is wrong for this event
3. Clicks "Clear All" button
4. Confirms: "Clear all recipes and finished goods?"
5. Recipe selections cleared, FG selections cleared, quantities cleared
6. Returns to blank state (can start over from recipe selection)

**Option B - Keep Recipes, Reset FGs:**
1. User has recipes selected and 15 FGs checked with quantities
2. Realizes FG selections are wrong but recipes are correct
3. Clicks "Clear Finished Goods" button
4. Confirms: "Clear all finished good selections? Recipe selections will remain."
5. FG checkboxes unchecked, quantities cleared, recipes remain selected
6. Can re-filter and select different FGs without re-selecting recipes

### Scenario 4: User Navigates Between Steps with UI State Persistence
1. User selects recipes, then FGs, enters quantities for 10 items (stored in UI state)
2. Realizes they forgot to add one more FG
3. Clicks back to "Select Finished Goods" step
4. Adds forgotten FG to selection list
5. Returns to quantity specification step
6. Sees all 11 FGs: 10 with previously entered quantities (preserved in UI state), 1 new with empty quantity
7. Enters quantity for new FG, all quantities persist to UI state on blur
8. Can freely navigate between steps without losing data (all in UI state)
9. Clicks final "Save" button → all recipes, FG selections, and quantities write to database atomically
10. Reopening event shows all saved data loaded from database

---

**END OF SPECIFICATION**
