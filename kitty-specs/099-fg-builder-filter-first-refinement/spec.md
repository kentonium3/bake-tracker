# Feature Specification: FG Builder Filter-First Refinement

**Feature Branch**: `099-fg-builder-filter-first-refinement`
**Created**: 2026-02-08
**Status**: Draft
**Input**: See docs/func-spec/F099_finished_goods_builder_refinement.md

## User Scenarios & Testing

### User Story 1 - Instant Dialog Open with Filter Prompts (Priority: P1)

Baker opens the Create Finished Good dialog and immediately sees filter prompts instead of waiting for hundreds of items to load. The dialog starts blank with clear guidance on what to select first.

**Why this priority**: Core UX improvement. Eliminates the slow auto-load that currently forces the user to wait before they can act, and removes confusion about where to start.

**Independent Test**: Click "Create Finished Good" button, verify dialog opens instantly with no items loaded and filter prompts visible.

**Acceptance Scenarios**:

1. **Given** the Finished Goods tab is open, **When** user clicks "Create Finished Good", **Then** dialog opens in <200ms with a blank item list and filter prompts visible
2. **Given** the dialog is open with no filters selected, **When** user views Step 1, **Then** placeholder text says "Select item type and category to see available items"
3. **Given** the catalog has 500+ FinishedUnits, **When** dialog opens, **Then** there is no performance delay because items have not been loaded

---

### User Story 2 - Clear Terminology for Item Types (Priority: P1)

Baker selects "Finished Units" and understands these are the atomic recipe outputs to build assemblies with. The old "Bare items only" toggle is replaced with clear, model-aligned terminology.

**Why this priority**: Eliminates terminology confusion identified in user testing session (2026-02-08). Users must understand the distinction between atomic units and assembled bundles.

**Independent Test**: Select each filter option and verify correct item types load with clear descriptions.

**Acceptance Scenarios**:

1. **Given** Step 1 is open with no selection, **When** user sees filter options, **Then** choices are "Finished Units" / "Existing Assemblies" / "Both" with descriptive text
2. **Given** user selects "Finished Units", **When** items load, **Then** only atomic items from recipes display (FinishedGoods where is_assembled=False, or FinishedUnits directly)
3. **Given** user selects "Existing Assemblies", **When** items load, **Then** only assembled FinishedGoods (is_assembled=True) display
4. **Given** user selects "Both", **When** items load, **Then** both types display with clear visual distinction between them

---

### User Story 3 - Filter-Driven Item Loading (Priority: P1)

Baker selects item type and category, then sees only the relevant subset of items load. Changing filters reloads items. Search further narrows results.

**Why this priority**: Performance and UX -- user controls when data loads and sees only relevant items.

**Independent Test**: Select different filter combinations and verify correct subsets load each time.

**Acceptance Scenarios**:

1. **Given** "Finished Units" is selected, **When** user selects "Cookies" category, **Then** query executes and only cookie Finished Units display
2. **Given** items are loaded for "Cookies", **When** user changes to "Cakes", **Then** new query executes and cake items replace cookie items
3. **Given** user types "chocolate" in search, **When** typing stops for 300ms, **Then** results filter to show only items matching "chocolate"
4. **Given** no items match the selected filters, **When** results are empty, **Then** display message: "No items match filters. Try different filters or create new recipes."

---

### User Story 4 - Edit Protection for Atomic Items (Priority: P2)

Baker accidentally tries to edit an auto-generated FinishedGood and receives a clear message explaining why editing is blocked and what to do instead.

**Why this priority**: Important for data integrity but less common than the creation workflow.

**Independent Test**: Click Edit on an atomic FG, verify block message shown. Click Edit on an assembled FG, verify builder opens normally.

**Acceptance Scenarios**:

1. **Given** an atomic FinishedGood (is_assembled=False) in the list, **When** user clicks Edit, **Then** message displays: "This item is auto-created from a recipe. Edit the recipe to change it."
2. **Given** an assembled FinishedGood (is_assembled=True) in the list, **When** user clicks Edit, **Then** builder opens with existing components loaded for modification
3. **Given** user sees the block message, **When** user reads it, **Then** they understand to edit the source recipe instead

---

### User Story 5 - Progressive Filter Workflow (Priority: P2)

Baker follows a natural progression: type -> category -> search -> select. Each step narrows the context for the next.

**Why this priority**: Good UX flow that guides the user naturally, but the individual filters (Stories 1-3) already deliver the core value.

**Independent Test**: Observe user completing the full filter chain without guidance.

**Acceptance Scenarios**:

1. **Given** dialog is open, **When** user's first action, **Then** they naturally select item type (filter prompts guide them)
2. **Given** type is selected, **When** user looks for next step, **Then** category filter is prominent and the obvious next action
3. **Given** category is selected with many items, **When** user wants a specific item, **Then** search narrows results effectively

---

### User Story 6 - Filter Change Clears Selections with Warning (Priority: P2)

Baker has selected items but then changes the type or category filter. Selections are cleared and the user is warned before losing them.

**Why this priority**: Prevents confusion about stale selections that no longer match the active filters.

**Independent Test**: Select items, change filter, verify warning shown and selections cleared.

**Acceptance Scenarios**:

1. **Given** user has selected 3 items, **When** user changes the item type filter, **Then** a warning appears: "Changing filters will clear your current selections. Continue?"
2. **Given** warning is shown, **When** user confirms, **Then** selections are cleared and new filter results load
3. **Given** warning is shown, **When** user cancels, **Then** selections are preserved and filter reverts to previous value

---

### Edge Cases

- **No items match filters**: Display empty state with suggestion to adjust filters or create new recipes
- **Very large category (500+ items)**: Limit display to 100 items with message: "Showing first 100 items. Use search to narrow results."
- **"Both" filter with many items**: Clearly distinguish Finished Units from Assemblies visually (labels, grouping, or icons)
- **Category deleted with items**: Items with deleted/null category appear in "Uncategorized" filter option
- **Edit atomic FG**: Block action with clear message directing user to edit recipe
- **Slow query (>2 seconds)**: Show loading indicator so dialog does not appear frozen

## Requirements

### Functional Requirements

- **FR-001**: Dialog MUST open with no items loaded and display filter prompts guiding the user to select item type and category
- **FR-002**: Item type filter MUST offer three options: "Finished Units" (atomic items from recipes), "Existing Assemblies" (is_assembled=True), and "Both"
- **FR-003**: Items MUST load only after the user selects an item type filter; no query executes on dialog open
- **FR-004**: Category filter MUST appear after item type selection, offering categories appropriate to the selected type plus an "All Categories" option
- **FR-005**: Search input MUST further narrow results within the selected type and category, with 300ms debounce
- **FR-006**: All FinishedGoods created via the builder MUST have is_assembled=True; the builder MUST NOT create atomic FinishedGoods
- **FR-007**: Builder MUST enforce a minimum of 1 component (food or material) for any created assembly
- **FR-008**: Edit action on an atomic FinishedGood (is_assembled=False) MUST be blocked with a message directing the user to edit the source recipe
- **FR-009**: Edit action on an assembled FinishedGood (is_assembled=True) MUST open the builder with existing components pre-loaded
- **FR-010**: Changing item type or category filters after items have been selected MUST warn the user and clear selections upon confirmation
- **FR-011**: Loading states MUST be displayed during queries: placeholder before filters, spinner during load, results after load, empty state when no matches
- **FR-012**: The "Bare items only" toggle terminology MUST be removed and replaced with the new filter options

### Key Entities

- **FinishedUnit**: Atomic item created from a recipe. Represents a single recipe output (e.g., "Chocolate Cake - Whole"). These are building blocks for assemblies.
- **FinishedGood**: Can be atomic (is_assembled=False, auto-generated from FinishedUnit) or assembled (is_assembled=True, user-built bundle of components). The builder only creates assembled FinishedGoods.
- **Composition**: Junction entity linking a FinishedGood to its component FinishedGoods/FinishedUnits with quantities.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Dialog opens in <200ms regardless of catalog size (no auto-query on open)
- **SC-002**: Filtered item load completes in <1 second for typical filter combinations
- **SC-003**: Primary user (Marianne) correctly identifies "Finished Units" as recipe outputs without prompting
- **SC-004**: Zero instances of "what is bare?" confusion (old terminology eliminated)
- **SC-005**: 100% of builder-created FinishedGoods have is_assembled=True
- **SC-006**: User completes filter -> select -> build workflow without assistance in user testing
- **SC-007**: Primary user confirms builder feels "faster and clearer" compared to previous version
