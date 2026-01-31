# Feature Specification: Catalog Tab Layout Standardization

**Feature Branch**: `087-catalog-tab-layout-standardization`
**Created**: 2026-01-30
**Status**: Draft
**Input**: Standardize all catalog tabs to use consistent 3-row layout, remove unnecessary title labels, convert RecipeDataTable to ttk.Treeview for trackpad scrolling, reduce padding. Pure UI refactoring.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Consistent Catalog Navigation (Priority: P1)

As a user navigating between Catalog tabs (Ingredients, Materials, Recipes), I experience a consistent layout pattern with search/filters at top, action buttons below, and data grid filling remaining space, so that I develop muscle memory and can work efficiently across all tabs.

**Why this priority**: Layout consistency is the core value proposition - without it, the other changes (trackpad scrolling, space optimization) have less impact.

**Independent Test**: Navigate between all Catalog tabs and verify identical 3-row layout pattern (controls, actions, grid) with no title labels.

**Acceptance Scenarios**:

1. **Given** I am in the Ingredients tab, **When** I observe the layout, **Then** I see search/filters at row 0, action buttons at row 1, data grid filling remaining space at row 2, and no title label.
2. **Given** I am in the Recipes tab, **When** I observe the layout, **Then** I see the same 3-row pattern as Ingredients tab.
3. **Given** I am in any Materials sub-tab, **When** I observe the layout, **Then** I see the same 3-row pattern.
4. **Given** I switch between any two Catalog tabs, **When** I compare layouts, **Then** control positions are identical.

---

### User Story 2 - Trackpad Scrolling in Recipes Tab (Priority: P1)

As a user viewing recipes on a trackpad-equipped device, I can scroll the recipe list using two-finger swipe gestures, so that I have the same scrolling experience as other tabs.

**Why this priority**: This is the primary usability fix - the current RecipeDataTable doesn't support native trackpad scrolling.

**Independent Test**: Open Recipes tab with enough recipes to require scrolling, use two-finger swipe on trackpad to scroll up and down.

**Acceptance Scenarios**:

1. **Given** the Recipes tab contains more recipes than visible, **When** I two-finger swipe down on trackpad, **Then** the recipe list scrolls down smoothly.
2. **Given** I have scrolled down in the Recipes list, **When** I two-finger swipe up, **Then** the list scrolls back up.
3. **Given** the Recipes tab is displayed, **When** I use scrollbar or mousewheel, **Then** scrolling works as expected.

---

### User Story 3 - Maximized Data Display Space (Priority: P2)

As a user viewing catalog data, I see more data rows without scrolling because unnecessary title labels and excessive padding have been removed, maximizing the vertical space for actual data.

**Why this priority**: More visible data improves efficiency but is secondary to layout consistency and scrolling fixes.

**Independent Test**: Compare visible row count before and after changes - more rows should be visible.

**Acceptance Scenarios**:

1. **Given** the Ingredients tab is displayed, **When** I count visible rows, **Then** more rows are visible than before (no "My Ingredients" title consuming space).
2. **Given** the Products tab is displayed, **When** I observe the layout, **Then** controls are consolidated into fewer rows than before.
3. **Given** any Catalog tab is displayed, **When** I resize the window vertically, **Then** the data grid expands/contracts while controls remain fixed height.

---

### User Story 4 - Preserved Functionality (Priority: P1)

As a user performing catalog operations (search, filter, add, edit, delete), all existing functionality works exactly as before the layout changes.

**Why this priority**: Zero regression is mandatory - this is a refactoring feature.

**Independent Test**: Execute all CRUD operations and search/filter in each tab.

**Acceptance Scenarios**:

1. **Given** any Catalog tab, **When** I type in the search field, **Then** results filter in real-time as before.
2. **Given** any Catalog tab, **When** I click Add button, **Then** the add dialog opens as before.
3. **Given** any Catalog tab with data, **When** I double-click a row, **Then** the edit dialog opens as before.
4. **Given** the Recipes tab, **When** I click a column header, **Then** the data sorts by that column.
5. **Given** any filter dropdown, **When** I select a filter value, **Then** data filters correctly.

---

### Edge Cases

- Window resized to minimum height - controls should remain visible, grid may show zero rows
- Empty data state - layout should remain consistent even with no data rows
- Very long text in grid cells - should truncate or wrap consistently across tabs
- Rapid tab switching - no visual artifacts or layout glitches

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST remove "My Ingredients" title label from IngredientsTab and shift rows up
- **FR-002**: System MUST remove "Product Catalog" title label from ProductsTab and consolidate control rows
- **FR-003**: System MUST remove "Materials Catalog" title label from MaterialsTab outer container
- **FR-004**: System MUST replace RecipeDataTable with ttk.Treeview in RecipesTab while preserving all column definitions, sorting, selection, and double-click behavior
- **FR-005**: System MUST configure all Catalog tabs with weight=0 for control rows and weight=1 for data grid row
- **FR-006**: System MUST use PADDING_MEDIUM consistently for vertical spacing between sections
- **FR-007**: System MUST apply the 3-row layout pattern to all Materials sub-tabs (Catalog, Products, Units)
- **FR-008**: System MUST preserve all existing search, filter, sort, selection, and CRUD functionality in all affected tabs

### Key Entities

- **No data model changes** - this is a pure UI refactoring feature
- Affected UI components: IngredientsTab, ProductsTab, RecipesTab, MaterialsTab, MaterialsCatalogTab, MaterialProductsTab, MaterialUnitsTab

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All Catalog tabs display NO title labels (0 title labels across all tabs)
- **SC-002**: All Catalog tabs use identical 3-row layout (controls, actions, grid)
- **SC-003**: Recipes tab supports trackpad two-finger scrolling (verified on macOS)
- **SC-004**: Products tab uses 3 grid rows (down from 5)
- **SC-005**: More data rows visible in each tab compared to current layout (at least 1 additional row per tab at standard window size)
- **SC-006**: Zero functionality regressions - all existing operations work identically
- **SC-007**: All ttk.Treeview grids expand vertically when window is resized (weight=1 verified)
- **SC-008**: Padding between sections uses PADDING_MEDIUM consistently

## Assumptions

- The func-spec at `docs/func-spec/F087_catalog_tab_layout_standardization.md` contains authoritative requirements
- IngredientsTab ttk.Treeview implementation is the reference pattern for the Recipes tab conversion
- RecipesTab currently uses RecipeDataTable which lacks native trackpad scrolling
- Existing test coverage for tab functionality is sufficient to detect regressions

## Out of Scope

- Adding new functionality to any tab
- Changing filter logic or search algorithms
- Modifying service layer or data models
- Adding new columns to any grid
- Changing color schemes or themes
- Refactoring Materials tab architecture (sub-tabs remain)
- Performance optimization beyond layout changes
