# F101: Type-Ahead Search Component

**Version**: 1.0  
**Priority**: MEDIUM  
**Type**: UI Component (Reusable)  

**Created**: 2026-02-08  
**Status**: Draft  

---

## Executive Summary

Current gaps:
- ❌ No type-ahead/autocomplete capability in ingredient selection
- ❌ Dropdown shows hundreds of arbitrarily ordered items (unusable)
- ❌ Tree view requires "too many clicks" per user feedback
- ❌ Ingredient entry takes 2-3x longer than necessary
- ❌ Pattern will be needed in multiple contexts (ingredients, materials, products)

This spec implements a reusable type-ahead search component that filters results as user types, reducing selection time from minutes to seconds and providing consistent search UX across the application.

---

## Problem Statement

**Current State (NO TYPE-AHEAD):**
```
Recipe Ingredient Entry
├─ Dropdown: Shows 200+ ingredients in arbitrary order
│  └─ ❌ Unusable - requires scrolling through entire list
├─ Tree View: Hierarchical navigation
│  └─ ❌ "Too many clicks" - user must expand categories, find item
└─ No Search: User cannot type to filter

Time Impact
├─ ❌ 2-3 minutes per ingredient with current methods
├─ ❌ 10+ ingredients per recipe = 20-30 minutes just selecting
└─ ❌ Doubled or tripled input time per user testing

User Expectation
├─ User repeatedly attempts to type in dropdown
├─ Expects modern type-ahead behavior
└─ Frustrated when typing doesn't filter results
```

**Target State (TYPE-AHEAD ENABLED):**
```
Recipe Ingredient Entry
├─ Type-Ahead Field: User types "choc"
│  ├─ After 3 characters, shows filtered matches
│  ├─ "Chocolate Chips"
│  ├─ "Chocolate (baking)"
│  └─ "Cocoa Powder"
├─ Continued Typing: "chocol"
│  ├─ List narrows further
│  ├─ "Chocolate Chips"
│  └─ "Chocolate (baking)"
└─ Selection: Click item or press Enter

Time Impact
├─ ✅ 5-10 seconds per ingredient (type + select)
├─ ✅ 10+ ingredients = 1-2 minutes total
└─ ✅ 2-3x speed improvement validated in testing

Reusability
├─ ✅ Ingredient selection (immediate need)
├─ ✅ Material selection (future)
├─ ✅ Product search (future)
├─ ✅ Any large-list selection scenario
└─ ✅ Consistent search UX across app
```

---

## User Testing Validation

**Discovery from Applied Testing (2026-02-08):**

**Finding 1:** User repeatedly attempted to type in dropdown
- Expected modern type-ahead behavior (like Google search)
- Frustrated when dropdown didn't filter on typing
- "I kept trying to type but nothing happened"

**Finding 2:** Dropdown unusable with hundreds of items
- Scrolling through 200+ arbitrarily ordered items impractical
- No way to jump to letter or filter
- User gave up and switched to tree view

**Finding 3:** Tree view "too many clicks"
- Must expand category → find subcategory → select item
- 3-5 clicks per ingredient vs 1 click with type-ahead
- Acceptable for browsing, not for rapid data entry

**Finding 4:** Ingredient entry bottleneck
- Doubled or tripled recipe input time
- User spent more time selecting ingredients than entering quantities
- Clear opportunity for 2-3x speed improvement

**Conclusion:** Type-ahead search is high-value, reusable component worth building properly.

---

## CRITICAL: Study These Files FIRST

**Before implementation, spec-kitty planning phase MUST read and understand:**

1. **Existing Search/Filter Patterns**
   - Find any existing search implementations in codebase
   - Study text input handling and event binding patterns
   - Note debouncing patterns if any exist
   - Understand service layer query methods with search parameters

2. **CustomTkinter Entry and Frame Widgets**
   - Study CTkEntry widget capabilities
   - Note event binding patterns for key events
   - Understand CTkScrollableFrame for dropdown list
   - Note positioning and layering patterns

3. **Ingredient Service Query Methods**
   - `src/services/ingredient_service.py` - search methods
   - Note: How to query ingredients by partial name match
   - Study: Return format (list of IngredientProducts)
   - Understand: Performance characteristics with large datasets

4. **Recipe UI Integration Point**
   - `src/ui/recipes/` - Find ingredient entry implementation
   - Study: Current dropdown and tree view patterns
   - Note: Where ingredient selection triggers save
   - Understand: How selected ingredient passed to parent form

5. **Similar Reusable Components**
   - Find other reusable UI components in codebase
   - Study initialization patterns and parameter passing
   - Note callback/event handling patterns
   - Understand how components integrated into forms

---

## Requirements Reference

This specification implements:
- **Constitution Principle I**: User-Centric Design & Workflow Validation
  - Features MUST solve actual user problems (ingredient entry bottleneck)
  - UI MUST be intuitive (standard type-ahead behavior)
  - User testing MUST validate major features (✓ completed 2026-02-08)

- **Constitution Principle VI.C**: Reusable Component Patterns
  - Components MUST be reusable across contexts
  - Consistent UX patterns across application
  - Reduce duplication through shared components

- **Constitution Principle VI.F**: Performance & Scalability
  - Search MUST be fast and responsive
  - Debouncing prevents excessive queries
  - Efficient filtering with large datasets

From: `.kittify/memory/constitution.md` (v1.4.0)

---

## Functional Requirements

### FR-1: Type-Ahead Entry Widget

**What it must do:**
- Provide text entry field that accepts keyboard input
- Monitor text changes and trigger search after minimum characters entered
- Display filtered results in dropdown below entry field
- Allow selection of item from results via click or keyboard
- Hide dropdown when item selected or focus lost
- Clear entry field after selection (or populate with selected item name)

**Trigger threshold:**
- Minimum 3 characters before search executes
- Show placeholder text: "Type at least 3 characters to search..."
- Display character count or hint if user types 1-2 characters

**Input handling:**
- Accept all alphanumeric characters and common punctuation
- Case-insensitive search
- Trim whitespace from query
- Validate input before executing search

**Success criteria:**
- [ ] Entry field accepts keyboard input
- [ ] Search triggered after 3+ characters typed
- [ ] No search executed with <3 characters
- [ ] Placeholder guides user on minimum length
- [ ] Input validation prevents invalid queries

---

### FR-2: Debounced Search Execution

**What it must do:**
- Wait for user to stop typing before executing search
- Debounce delay: 150-300ms after last keystroke
- Cancel pending search if user continues typing
- Show loading indicator during search execution
- Handle rapid typing without excessive queries

**Debouncing behavior:**
- User types "c" → wait
- User types "h" (150ms later) → reset timer
- User types "o" (150ms later) → reset timer
- User stops typing → wait 150ms → execute search for "cho"

**Performance considerations:**
- Prevent query spam (typing fast shouldn't trigger 10 queries)
- Balance responsiveness vs server load
- Loading indicator provides feedback during delay

**Success criteria:**
- [ ] Search executes only after typing stops
- [ ] Debounce delay configurable (default 150ms)
- [ ] Rapid typing doesn't trigger multiple searches
- [ ] Loading indicator shown during search
- [ ] User perceives responsive (not laggy) behavior

---

### FR-3: Filtered Results Dropdown

**What it must do:**
- Display search results in dropdown list below entry field
- Position dropdown directly under entry field
- Show maximum 10 results (configurable)
- Truncate or scroll if more results available
- Display "No results found" if query returns empty
- Close dropdown when item selected or focus lost

**Dropdown behavior:**
- Appears below entry field (not overlapping)
- Scrollable if more than maximum results
- Click on item selects it and closes dropdown
- Click outside dropdown closes without selection
- Escape key closes dropdown without selection

**Result display:**
- Show item name prominently
- Optional: Show category or additional context
- Highlight matching text (optional enhancement)
- Clear visual separation between items

**Empty state:**
- If 0 results: "No items match 'query'"
- Suggest: "Try different search terms"
- Don't show dropdown if fewer than minimum characters typed

**Success criteria:**
- [ ] Dropdown positioned below entry field
- [ ] Results display clearly and readably
- [ ] Maximum result count respected
- [ ] Scrollable if needed
- [ ] Empty state shown when no matches
- [ ] Dropdown closes on selection or focus loss

---

### FR-4: Keyboard Navigation

**What it must do:**
- Support arrow keys to navigate dropdown results
- Highlight current selection
- Enter key selects highlighted item
- Escape key closes dropdown without selection
- Tab key moves focus (standard behavior)

**Keyboard interactions:**
- **Down Arrow:** Highlight next item in list
- **Up Arrow:** Highlight previous item in list
- **Enter:** Select highlighted item and close dropdown
- **Escape:** Close dropdown without selecting
- **Tab:** Move focus to next field (close dropdown if open)

**Visual feedback:**
- Highlighted item has distinct background color
- Mouse hover also highlights (keyboard and mouse work together)
- Clear indication which item is selected

**Edge cases:**
- Down arrow at bottom of list - behavior to be determined
- Up arrow at top of list - behavior to be determined  
- Enter with no item highlighted - behavior to be determined

**Success criteria:**
- [ ] Arrow keys navigate results
- [ ] Highlighted item visually distinct
- [ ] Enter selects highlighted item
- [ ] Escape closes dropdown
- [ ] Keyboard and mouse navigation work together

---

### FR-5: Item Selection and Callback

**What it must do:**
- When item selected (click or Enter), execute callback function
- Pass selected item data to callback
- Clear or populate entry field based on configuration
- Close dropdown after selection
- Return focus to appropriate next field

**Selection callback:**
- Callback receives selected item (full object or just ID)
- Parent form handles what to do with selection
- Component remains decoupled from business logic

**Post-selection behavior:**
- Option A: Clear entry field (ready for next search)
- Option B: Populate with selected item name (show what was selected)
- Configurable based on use case

**Focus management:**
- After selection, focus next input field (if specified)
- Or return focus to entry field for next search
- Or blur entirely (depends on form workflow)

**Success criteria:**
- [ ] Callback executed on selection
- [ ] Selected item data passed to callback
- [ ] Entry field cleared or populated as configured
- [ ] Dropdown closes after selection
- [ ] Focus moved appropriately

---

### FR-6: Reusable Component Interface

**What it must do:**
- Accept configuration parameters at initialization
- Support any data source (ingredients, materials, products, etc.)
- Callback function for fetching filtered items
- Configurable minimum characters, debounce delay, max results
- Consistent API across different use cases

**Component initialization parameters:**
- `items_callback`: Function that accepts query string, returns filtered items
- `on_select_callback`: Function called when item selected
- `min_chars`: Minimum characters before search (default: 3)
- `debounce_ms`: Debounce delay in milliseconds (default: 150)
- `max_results`: Maximum results to display (default: 10)
- `placeholder_text`: Text shown in empty entry field
- `clear_on_select`: Boolean - clear entry after selection (default: True)

**Usage examples (conceptual - not implementation code):**
- Ingredient selection with ingredient service callback
- Material selection with material service callback
- Product search with product service callback

**Success criteria:**
- [ ] Component accepts configuration parameters
- [ ] Works with any data source via callback
- [ ] Consistent behavior across different contexts
- [ ] Easy to integrate into existing forms
- [ ] Documentation shows usage examples

---

## Edge Cases

### Edge Case 1: Very Long Result List
**Scenario:** Query returns 100+ matching items
**Behavior:** Show first 10 (or max_results), display "Showing 10 of 100 results. Refine search for more."
**Validation:** Encourage more specific search terms rather than overwhelming user

### Edge Case 2: Network/Query Delay
**Scenario:** Search query takes more than 2 seconds to return results
**Behavior:** Show loading indicator, allow user to continue typing (cancel previous query)
**Validation:** User sees feedback, understands system is working

### Edge Case 3: Special Characters in Query
**Scenario:** User types "salt & pepper" or "chocolate/cocoa"
**Behavior:** Handle special characters appropriately (escape or allow in query)
**Validation:** Search works correctly with special characters

### Edge Case 4: Exact Match Found
**Scenario:** User types full item name "Chocolate Chips"
**Behavior:** Show single result, possibly auto-select if exact match
**Validation:** Decision needed - auto-select or let user confirm

### Edge Case 5: Dropdown Off-Screen
**Scenario:** Entry field near bottom of window, dropdown would go off-screen
**Behavior:** Position dropdown above entry field instead of below
**Validation:** Dropdown always fully visible

### Edge Case 6: Rapid Tab Through Form
**Scenario:** User tabs through form quickly, lands on type-ahead field briefly
**Behavior:** Don't show dropdown unless user actually types
**Validation:** Dropdown only appears when actively searching

### Edge Case 7: Concurrent Searches
**Scenario:** User searches in multiple type-ahead fields simultaneously
**Behavior:** Each field maintains independent state and dropdown
**Validation:** No cross-contamination between search instances

---

## Success Criteria

### Measurable Outcomes

**SC-001: Speed Improvement**
- Ingredient selection time reduced from 2-3 minutes to 5-10 seconds
- Recipe with 10 ingredients: Entry time under 2 minutes (vs 20-30 minutes currently)
- User testing confirms 2-3x speed improvement

**SC-002: User Satisfaction**
- Primary user (Marianne) rates type-ahead as "much easier" vs dropdown/tree
- Zero instances of user attempting to type in old dropdown (new behavior clear)
- User completes recipe entry without assistance using type-ahead

**SC-003: Reusability**
- Component used in at least 2 different contexts (ingredients + materials minimum)
- Same component code, different data sources
- Consistent UX across all instances

**SC-004: Performance**
- Search executes in under 500ms for typical query
- Debouncing prevents query spam (max 1 query per 150ms typing)
- Dropdown rendering instantaneous (under 100ms)

**SC-005: Keyboard Accessibility**
- 100% of dropdown functionality available via keyboard
- No mouse required for search and selection
- Keyboard navigation feels natural and responsive

---

## User Scenarios & Testing

### User Story 1 - Fast Ingredient Search (Priority: P1)

**Scenario:** Baker creating recipe types "choc" and immediately sees chocolate ingredients.

**Why this priority:** Core value proposition - eliminates ingredient entry bottleneck.

**Independent Test:** Can be fully tested by typing partial ingredient name, verifying filtered results appear.

**Acceptance Scenarios:**

1. **Given** recipe ingredient entry field, **When** user types "cho", **Then** dropdown appears showing Chocolate Chips, Chocolate (baking), Cocoa Powder

2. **Given** dropdown showing chocolate items, **When** user continues typing "colate", **Then** list narrows to Chocolate Chips and Chocolate (baking)

3. **Given** 2 chocolate items showing, **When** user clicks "Chocolate Chips", **Then** item selected, ingredient added to recipe, dropdown closes, entry field clears

4. **Given** entry field cleared, **When** user types next ingredient "van", **Then** dropdown shows vanilla items

---

### User Story 2 - Keyboard-Only Workflow (Priority: P1)

**Scenario:** Baker enters ingredients without using mouse.

**Why this priority:** Power users prefer keyboard-only data entry (faster).

**Independent Test:** Can be tested by completing ingredient selection using only keyboard.

**Acceptance Scenarios:**

1. **Given** recipe entry form, **When** user tabs to ingredient field and types "sugar", **Then** dropdown shows sugar items, first item highlighted

2. **Given** dropdown with highlighted item, **When** user presses Down Arrow twice, **Then** third item highlighted

3. **Given** desired item highlighted, **When** user presses Enter, **Then** item selected and added to recipe

4. **Given** dropdown open, **When** user presses Escape, **Then** dropdown closes without selection

---

### User Story 3 - Reuse for Material Selection (Priority: P2)

**Scenario:** Same type-ahead component used for material product selection.

**Why this priority:** Validates reusability design, important for consistency but not immediate need.

**Independent Test:** Can be tested by integrating component into materials form with different data source.

**Acceptance Scenarios:**

1. **Given** materials entry form, **When** developer integrates TypeAheadEntry with material_service callback, **Then** component works identically to ingredient version

2. **Given** material search field, **When** user types "box", **Then** dropdown shows cake boxes, gift boxes, etc.

3. **Given** material search UX, **When** compared to ingredient search, **Then** behavior consistent (same keyboard shortcuts, same visual design)

---

### User Story 4 - Handle Large Result Sets (Priority: P3)

**Scenario:** User searches "chocolate" which matches 50+ items.

**Why this priority:** Important for data quality but less common than typical searches.

**Independent Test:** Can be tested by searching common term with many matches.

**Acceptance Scenarios:**

1. **Given** search query with 50+ matches, **When** results load, **Then** shows first 10 items with message "Showing 10 of 50+ results. Refine search for more."

2. **Given** large result set, **When** user adds more characters to narrow search, **Then** result count decreases and more specific items shown

3. **Given** user sees "refine search" message, **When** user narrows query, **Then** finds desired item within top 10 results

---

## Dependencies

**Required Features (Must be Complete):**
- CustomTkinter UI framework (existing)
- Service layer search methods (ingredient_service, material_service with name search)

**Blocks These Features:**
- None immediately
- Future: Any feature requiring large-list selection benefits from this pattern

**Related Features (Will Benefit):**
- Recipe ingredient entry (immediate integration)
- Materials selection forms (future integration)
- Product search (future integration)
- Any search/filter UI across app

---

## Testing Strategy

### Unit Tests
- Debounce logic (typing fast doesn't spam queries)
- Minimum character validation
- Dropdown positioning calculation
- Keyboard navigation state machine
- Selection callback execution

### Integration Tests
- Component with ingredient service
- Component with material service
- Multiple instances on same form
- Keyboard-only workflow
- Mouse-only workflow

### User Acceptance Tests
With primary user (Marianne):
1. Enter recipe with 10 ingredients using type-ahead
2. Measure time vs old dropdown/tree method
3. Verify 2-3x speed improvement
4. Confirm "much easier" subjective rating
5. Test keyboard-only workflow

**Success Criteria:** All scenarios completed successfully, time improvement confirmed

---

## Constitutional Compliance

**Principle I: User-Centric Design & Workflow Validation** ✓
- Addresses major pain point identified in user testing
- 2-3x speed improvement is measurable user benefit
- Validated through applied testing (ingredient entry bottleneck)

**Principle VI.C: Reusable Component Patterns** ✓
- Component designed for reuse across contexts
- Consistent UX through shared implementation
- Reduces code duplication

**Principle VI.F: Performance & Scalability** ✓
- Debouncing prevents excessive queries
- Efficient search with large datasets
- Responsive UI with proper loading indicators

---

## Version History

- v1.0 (2026-02-08): Initial specification based on user testing insights
