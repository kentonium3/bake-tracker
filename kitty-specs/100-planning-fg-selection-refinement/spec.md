# Feature Specification: Planning FG Selection Refinement

**Feature Branch**: `100-planning-fg-selection-refinement`
**Created**: 2026-02-09
**Status**: Draft
**Input**: See docs/func-spec/F100_planning_fg_selection_refinement.md

## User Scenarios & Testing

### User Story 1 - Recipe Category Filter-First Selection (Priority: P1)

Baker opens the Planning tab, selects an event, and sees the recipe selection frame start blank with a category filter dropdown. Recipes load only after selecting a category. This replaces the current auto-load-all behavior.

**Why this priority**: Foundation for the entire filter-first pattern. Without blank-start recipe selection, the downstream FG filtering has no consistent UX precedent within Planning. Directly mirrors F099 pattern validated in user testing.

**Independent Test**: Select an event, verify recipe frame opens blank with category filter, select a category, verify only matching recipes appear.

**Acceptance Scenarios**:

1. **Given** the Planning tab is open and an event is selected, **When** user views recipe selection, **Then** the frame starts blank with placeholder text "Select recipe category to see available recipes"
2. **Given** recipe frame is blank, **When** user selects "Cookies" from category dropdown, **Then** only cookie recipes load and display with checkboxes
3. **Given** recipes are loaded for "Cookies", **When** user changes to "All Categories", **Then** all recipes load and display
4. **Given** user has checked 3 cookie recipes, **When** user changes category to "Brownies", **Then** the 3 cookie selections persist and brownie recipes now display
5. **Given** no recipes exist for selected category, **When** results are empty, **Then** message displays "No recipes found for this category"

---

### User Story 2 - FG Independent Combinatorial Filtering (Priority: P1)

Baker reaches the FG selection step and sees three independent filter dropdowns (recipe category, item type, yield type) all visible at once. FGs load only after at least one filter is applied. Filters combine with AND logic and can be set in any order.

**Why this priority**: Core UX improvement. Replaces "show all FGs" approach with structured filtering that scales to large catalogs and matches F099 progressive disclosure pattern.

**Independent Test**: Open FG selection, verify blank start, apply filters in different orders, verify AND logic produces correct subsets.

**Acceptance Scenarios**:

1. **Given** FG selection step is active, **When** user views the frame, **Then** it starts blank with placeholder "Select filters to see available finished goods" and three filter dropdowns visible
2. **Given** no filters applied, **When** user selects "Cookies" recipe category, **Then** all FGs from cookie recipes display (item type and yield type not yet filtered)
3. **Given** "Cookies" category selected, **When** user also selects "Finished Units" item type, **Then** only cookie Finished Units display (AND logic)
4. **Given** "Cookies" + "Finished Units" selected, **When** user also selects "EA" yield type, **Then** only EA cookie Finished Units display (three-way AND)
5. **Given** three filters active, **When** user changes recipe category to "All Categories", **Then** FGs update to show all Finished Units with EA yield (two remaining filters still active)
6. **Given** user sets item type to "Assemblies", **When** no assemblies match other filters, **Then** message displays "No items match current filters"

---

### User Story 3 - Selection Persistence Across Filter Changes (Priority: P1)

Baker checks FGs, then changes filters to explore other categories. Previously checked FGs remain selected even when filtered out of view. Returning to the original filter restores the visible checked state.

**Why this priority**: Without persistence, filter changes destroy user's work-in-progress selections, causing frustration. This is the key differentiator from the current implementation.

**Independent Test**: Check FGs, change filters to hide them, change filters back, verify checkboxes are still checked.

**Acceptance Scenarios**:

1. **Given** user checks 3 cookie FGs, **When** user changes recipe category to "Brownies", **Then** cookie FGs disappear from view but remain selected internally
2. **Given** cookie FGs are selected but hidden, **When** user changes back to "Cookies", **Then** the 3 cookie FGs reappear with checkboxes checked
3. **Given** user has 5 FGs selected across multiple categories, **When** user changes item type filter, **Then** all 5 selections persist regardless of which are currently visible
4. **Given** a selected FG is visible, **When** user unchecks it, **Then** it is removed from the selection set regardless of current filters

---

### User Story 4 - Clear Buttons (Two-Level Reset) (Priority: P2)

Baker has recipes and FGs selected with quantities entered. They can use "Clear All" to reset the entire plan or "Clear Finished Goods" to reset just FGs while keeping recipe selections.

**Why this priority**: Enables efficient course corrections. Without clear buttons, user must manually uncheck every item. Two-level clear provides targeted reset options.

**Independent Test**: Build a plan with recipes + FGs + quantities, click each clear button, verify correct scope is cleared.

**Acceptance Scenarios**:

1. **Given** user has recipes selected + FGs checked + quantities entered, **When** user clicks "Clear All", **Then** confirmation dialog shows "Clear all recipes and finished goods? This resets the entire plan to blank."
2. **Given** user confirms "Clear All", **Then** recipe selections cleared, FG selections cleared, quantities cleared, both frames return to blank state
3. **Given** user cancels "Clear All", **Then** all selections and quantities remain unchanged
4. **Given** user has recipes + FGs + quantities, **When** user clicks "Clear Finished Goods", **Then** confirmation shows "Clear all finished good selections? Recipe selections will remain."
5. **Given** user confirms "Clear Finished Goods", **Then** FG checkboxes unchecked and quantities cleared, but recipe selections remain intact
6. **Given** user cancels "Clear Finished Goods", **Then** all selections remain unchanged

---

### User Story 5 - Show All Selected Toggle (Priority: P2)

Baker has selected FGs across multiple filter combinations and wants to review all selections in one view. "Show All Selected" temporarily shows only checked items regardless of active filters.

**Why this priority**: Enables selection review across filter boundaries. Without this, user cannot see their complete selection list when filters hide some items.

**Independent Test**: Select FGs across different filter settings, click "Show All Selected", verify all selected items visible, toggle back, verify filters restored.

**Acceptance Scenarios**:

1. **Given** user has 8 FGs selected across different categories, **When** user clicks "Show All Selected", **Then** only the 8 selected FGs display regardless of current filter settings
2. **Given** "Show All Selected" mode is active, **Then** visual indicator shows "Showing 8 selected items" and button label changes to "Show Filtered View"
3. **Given** "Show All Selected" mode is active, **When** user clicks "Show Filtered View", **Then** display returns to filter-based view with previous filter settings restored exactly
4. **Given** "Show All Selected" mode is active, **When** user changes any filter dropdown, **Then** "selected only" mode exits and the new filter applies normally
5. **Given** no FGs are selected, **When** user clicks "Show All Selected", **Then** message displays "No items selected"

---

### User Story 6 - Quantity Specification with UI State Persistence (Priority: P2)

Baker finishes FG selection and proceeds to quantity specification. Only selected FGs appear with quantity inputs. Quantities persist in UI state across step navigation and are saved atomically to the database on final Save.

**Why this priority**: Completes the workflow from selection to committed plan. UI-state persistence enables back-and-forth navigation without data loss. Atomic save prevents partial database writes.

**Independent Test**: Select FGs, enter quantities, navigate back to FG selection, return, verify quantities preserved, click Save, verify database write.

**Acceptance Scenarios**:

1. **Given** user has selected 5 FGs, **When** user proceeds to quantity step, **Then** only the 5 selected FGs display with quantity input fields
2. **Given** quantity step is active, **When** user enters "12" for a cookie FG, **Then** value persists in UI state on blur/change
3. **Given** user enters "0", **Then** validation error "Quantity must be greater than zero" shown inline
4. **Given** user enters "2.5", **Then** validation error "Whole numbers only" shown inline
5. **Given** user enters "-3", **Then** validation error "Quantity must be positive" shown inline
6. **Given** user enters "abc", **Then** validation error "Enter a valid number" shown inline
7. **Given** user leaves quantity empty, **Then** validation error "Quantity required" shown inline
8. **Given** quantities entered for 5 FGs, **When** user navigates back to FG selection step, **Then** quantities are preserved in UI state
9. **Given** user returns to quantity step after adding a 6th FG, **Then** 5 FGs show previous quantities and 6th FG shows empty quantity input
10. **Given** all quantities valid, **When** user clicks Save, **Then** all recipes + FG selections + quantities write to `event_finished_goods` table atomically
11. **Given** validation errors exist, **When** user tries to Save, **Then** Save button is disabled with indication of errors

---

### Edge Cases

- What happens when user selects a recipe, then that recipe's FGs are all filtered out by item type/yield type? Selection count still shows the recipe as selected; FGs simply don't appear in current filter view.
- What happens when user clears recipes that have associated FG selections? FG selections for those recipes should also be cleared (cascading clear).
- What happens when event has no recipes in the database? Recipe selection shows "No recipes available" after any category selected.
- What happens when user rapidly changes filters? Each filter change triggers a reload; debounce if needed for performance.
- What happens when user clicks Save with no FGs selected? Save should be disabled or show "Select at least one finished good."

## Requirements

### Functional Requirements

- **FR-001**: Recipe selection frame MUST start blank with category filter visible and placeholder text
- **FR-002**: Recipes MUST load only after user selects a category from the dropdown
- **FR-003**: Recipe selection state MUST persist when category filter changes
- **FR-004**: FG selection frame MUST start blank with three filter dropdowns visible simultaneously
- **FR-005**: FG filters MUST be independent (no dependencies between them; user sets in any order)
- **FR-006**: FG filters MUST combine with AND logic to narrow displayed items
- **FR-007**: FGs MUST load only after at least one filter is applied
- **FR-008**: FG selection state MUST persist when any filter changes (checked items stay checked even when filtered out)
- **FR-009**: "Clear All" button MUST clear recipes + FGs + quantities with confirmation dialog
- **FR-010**: "Clear Finished Goods" button MUST clear only FGs + quantities while preserving recipe selections, with confirmation dialog
- **FR-011**: "Show All Selected" button MUST display only selected FGs regardless of active filters
- **FR-012**: "Show All Selected" mode MUST exit when any filter dropdown changes
- **FR-013**: Quantity inputs MUST accept only positive integers (reject zero, decimals, negatives, non-numeric)
- **FR-014**: Quantities MUST persist in UI state (in-memory) across step navigation
- **FR-015**: Database write MUST occur only on final Save button click, writing all selections and quantities atomically

### Key Entities

- **Recipe**: Belongs to a recipe category. Users select recipes to determine which FGs are available for planning.
- **RecipeCategory**: Groups recipes (Cookies, Brownies, Cakes, etc.). Primary filter dimension for recipe selection.
- **FinishedGood**: An assembled item or bare unit. Has assembly_type (BARE/BUNDLE) and is linked to recipes.
- **FinishedUnit**: Atomic recipe output (single item). Has yield_type (EA/SERVING).
- **EventFinishedGood**: Junction table linking an Event to FinishedGoods with quantity. Target for atomic save.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Planning recipe/FG selection frames open instantly with no item loading delay (blank start)
- **SC-002**: User can find and select desired FGs using filter combinations in under 30 seconds (vs scrolling through full list)
- **SC-003**: Zero selections lost when changing filters during a planning session
- **SC-004**: User can reset FG selections without losing recipe selections (targeted clear)
- **SC-005**: User can review all selected items across filter boundaries in a single view
- **SC-006**: All quantity validation errors produce clear, specific messages matching the input type
- **SC-007**: Quantities entered during planning persist across step navigation until explicit clear or final save
- **SC-008**: Final save writes complete plan (recipes + FGs + quantities) to database in single atomic transaction
- **SC-009**: Existing test suite continues to pass with no regressions

## Assumptions

- Recipe categories are already stored and queryable (RecipeCategory model from F096)
- FinishedUnit.yield_type field exists and is queryable (from F083)
- FinishedGood.assembly_type field distinguishes BARE from BUNDLE items
- The Planning tab's multi-step accordion/section structure can accommodate the new filter-first pattern
- This spec covers initial plan creation only; edit mode for saved plans is deferred to F077/F078

## Out of Scope

- Recipe search/filtering by name (future enhancement)
- FG search/filtering by name (future enhancement)
- Bulk quantity entry (paste from spreadsheet)
- Historical quantity suggestions
- Assembly component breakdown display
- Edit mode for saved event plans (F077/F078)
- Batch calculation integration (F073)
