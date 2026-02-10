# Feature Specification: Type-Ahead Search Component

**Feature Branch**: `101-type-ahead-search-component`
**Created**: 2026-02-10
**Status**: Draft
**Input**: See docs/func-spec/F101_type_ahead_search_component.md

## User Scenarios & Testing

### User Story 1 - Fast Ingredient Search (Priority: P1)

Baker creating a recipe types partial ingredient name and immediately sees filtered matches, selects one with a click or Enter key. This eliminates the current bottleneck of scrolling through 200+ items in a dropdown or navigating a multi-click tree view.

**Why this priority**: Core value proposition. User testing (2026-02-08) confirmed ingredient entry takes 2-3x longer than necessary. User repeatedly attempted to type in the dropdown expecting filter behavior. This is the immediate pain point.

**Independent Test**: Can be fully tested by typing partial ingredient names into the type-ahead field and verifying filtered results appear, are selectable, and integrate into the recipe form.

**Acceptance Scenarios**:

1. **Given** a recipe ingredient entry field with type-ahead, **When** user types "cho" (3 characters), **Then** a dropdown appears showing matching ingredients (e.g., Chocolate Chips, Chocolate (baking), Cocoa Powder)

2. **Given** a dropdown showing chocolate items, **When** user continues typing "colate", **Then** list narrows to only Chocolate-prefixed items

3. **Given** filtered results showing, **When** user clicks "Chocolate Chips", **Then** the ingredient is selected, callback fires with the selected item, dropdown closes, and entry field clears for next search

4. **Given** entry field cleared after selection, **When** user types next ingredient "van", **Then** dropdown shows vanilla items (independent of previous search)

5. **Given** user types fewer than 3 characters, **When** looking at the entry field, **Then** no dropdown appears and placeholder text guides user: "Type at least 3 characters to search..."

---

### User Story 2 - Keyboard-Only Workflow (Priority: P1)

Baker enters ingredients using only the keyboard for rapid data entry. Arrow keys navigate the results, Enter selects, Escape dismisses.

**Why this priority**: Power users (and the primary user Marianne) prefer keyboard-only data entry for speed. Keyboard navigation is essential for the 2-3x speed improvement goal.

**Independent Test**: Can be tested by completing full ingredient selection using only keyboard (type, arrow, Enter) without touching the mouse.

**Acceptance Scenarios**:

1. **Given** user tabs to the type-ahead field and types "sugar", **When** dropdown appears, **Then** no item is initially highlighted

2. **Given** dropdown with items, **When** user presses Down Arrow twice, **Then** second item is highlighted with a visually distinct background

3. **Given** desired item highlighted, **When** user presses Enter, **Then** item is selected and callback fires

4. **Given** dropdown open, **When** user presses Escape, **Then** dropdown closes without any selection

5. **Given** highlight is on the last item, **When** user presses Down Arrow, **Then** highlight stays on the last item (no wrap)

6. **Given** highlight is on the first item, **When** user presses Up Arrow, **Then** highlight stays on the first item (no wrap)

7. **Given** dropdown open with no item highlighted, **When** user presses Enter, **Then** nothing happens (no selection made)

---

### User Story 3 - Reuse for Material Selection (Priority: P2)

The same type-ahead component is used for material product selection in the Finished Goods builder, demonstrating reusability with a different data source but identical UX behavior.

**Why this priority**: Validates the reusable design. Important for long-term consistency but not the immediate user pain point.

**Independent Test**: Can be tested by integrating the component into a materials form with a material service callback and verifying identical behavior.

**Acceptance Scenarios**:

1. **Given** a materials entry form using TypeAheadEntry with a material service callback, **When** user types "box", **Then** dropdown shows matching materials (cake boxes, gift boxes, etc.)

2. **Given** material type-ahead and ingredient type-ahead side by side, **When** comparing behavior, **Then** keyboard shortcuts, visual design, debounce timing, and interaction patterns are identical

---

### User Story 4 - Large Result Sets (Priority: P3)

User searches a common term that matches many items. The component shows a bounded result set with guidance to refine the search.

**Why this priority**: Important for data quality with growing datasets but less common than typical targeted searches.

**Independent Test**: Can be tested by searching a broad term (e.g., "chocolate") that matches 50+ items.

**Acceptance Scenarios**:

1. **Given** a search query matching 50+ items, **When** results load, **Then** shows first 10 items with a message: "Showing 10 of 50+ results. Refine search for more."

2. **Given** a large result set displayed, **When** user adds more characters to narrow the search, **Then** result count decreases and the desired item appears within the top 10

---

### Edge Cases

- **Exact match typed**: When user types a full item name (e.g., "Chocolate Chips"), the dropdown still shows matching results for user confirmation (no auto-select)
- **Special characters**: Queries containing "&", "/", "-", or parentheses are handled correctly (e.g., "salt & pepper" returns matching items)
- **Rapid typing**: Debouncing ensures only 1 search fires per pause, even if user types 10 characters in quick succession
- **Focus loss**: Dropdown closes when user clicks outside it or tabs to another field
- **Rapid tab-through**: If user tabs past the field without typing, no dropdown appears
- **Multiple instances**: If two type-ahead fields exist on the same form, each maintains independent state and dropdown
- **Empty results**: When no items match the query, dropdown shows "No items match '[query]'" with a suggestion to try different terms

## Requirements

### Functional Requirements

- **FR-001**: System MUST provide a text entry field that accepts keyboard input and triggers filtered search after a configurable minimum character threshold (default: 3 characters)
- **FR-002**: System MUST debounce search execution with a configurable delay (default: 150ms) after the last keystroke, cancelling any pending search when the user continues typing
- **FR-003**: System MUST display filtered results in a dropdown positioned directly below the entry field, showing a configurable maximum number of results (default: 10) with scrolling if more exist
- **FR-004**: System MUST support full keyboard navigation: Down/Up arrows to highlight items, Enter to select the highlighted item, Escape to close without selection
- **FR-005**: System MUST execute a configurable callback when an item is selected, passing the full selected item data to the parent form
- **FR-006**: System MUST be a reusable component accepting configuration parameters: items_callback, on_select_callback, min_chars, debounce_ms, max_results, placeholder_text, clear_on_select
- **FR-007**: System MUST show a "No items match" message when a search returns zero results
- **FR-008**: System MUST close the dropdown when the user clicks outside it, tabs away, or presses Escape
- **FR-009**: Arrow keys at list boundaries MUST stop (not wrap around); Enter with no item highlighted MUST do nothing
- **FR-010**: System MUST perform case-insensitive search with trimmed whitespace

### Key Entities

- **TypeAheadEntry**: Reusable UI widget combining a text entry field with a filtered dropdown. Configured via callbacks and parameters. No business logic -- delegates search and selection handling to the parent form.
- **SearchResult item**: Generic dictionary/object returned by the items_callback. Must include at minimum a display name and an identifier. Structure is defined by the caller, not the component.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Ingredient selection time reduced from 2-3 minutes per ingredient to under 10 seconds per ingredient (2-3x speed improvement confirmed in user testing)
- **SC-002**: Recipe with 10 ingredients can be entered in under 2 minutes using type-ahead (vs 20-30 minutes with current dropdown/tree)
- **SC-003**: Primary user (Marianne) rates type-ahead as "much easier" than dropdown/tree in post-testing feedback
- **SC-004**: 100% of search and selection functionality is accessible via keyboard alone (no mouse required)
- **SC-005**: Component is successfully reused in at least 2 different contexts (ingredient selection + one additional) with the same codebase and consistent UX
