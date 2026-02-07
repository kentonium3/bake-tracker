---
work_package_id: WP03
title: Food Selection Step
lane: "doing"
dependencies: [WP02]
base_branch: 097-finished-goods-builder-ui-WP02
base_commit: 2ee0f735330f610e0e5a20f50351289422a882a6
created_at: '2026-02-07T00:19:41.778791+00:00'
subtasks:
- T010
- T011
- T012
- T013
- T014
- T015
phase: Phase B - Step Implementation
assignee: ''
agent: "claude-opus"
shell_pid: "27248"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-02-06T23:51:59Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP03 -- Food Selection Step

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

- Implement Step 1 (Food Selection) content panel within the builder dialog
- Category dropdown filters FinishedGoods by ProductCategory (string field on FinishedUnit)
- "Bare items only" and "Include assemblies" toggles filter by AssemblyType
- Search field provides real-time name filtering
- Multi-select checkboxes with per-item quantity fields (1-999)
- Selection state persists across filter changes (global, not per-filter-view)
- Validation: minimum 1 food item selected with quantity >= 1 before Continue
- Unit tests pass for filtering logic and validation

**Implementation command**: `spec-kitty implement WP03 --base WP02`

## Context & Constraints

- **Feature**: 097-finished-goods-builder-ui
- **Plan**: Design Decisions D-003 (inline checkboxes), D-004 (state management)
- **Research**: R-004 (bare items = AssemblyType.BARE), R-005 (category = string field on FinishedUnit)
- **Data model**: `data-model.md` — FinishedGood has `assembly_type`, FinishedUnit has `category`
- **Existing patterns**:
  - `src/ui/forms/finished_good_form.py` lines 21-186: ComponentSelectionPopup (filter + search pattern)
  - `src/services/finished_good_service.py`: `get_all_finished_goods()` returns all FGs
  - `src/services/finished_unit_service.py`: `get_all_finished_units(category=..., name_search=...)`
- **Composition types for food**: `"finished_unit"` and `"finished_good"` (two separate component types)
- **Constitution**: Principle V — no business logic in UI; queries go through service layer

## Subtasks & Detailed Guidance

### Subtask T010 -- Create food selection content panel with filter bar UI

- **Purpose**: Build the visual layout for Step 1's content area.

- **Steps**:
  1. In the builder dialog, create a method `_create_food_step_content()` that populates `self.step1.content_frame`
  2. Filter bar layout (top of content frame):
     - Category dropdown: CTkComboBox with "All Categories" + distinct category values
     - Bare/Assembly toggle: Two CTkSegmentedButton options: "Bare Items Only" | "Include Assemblies"
     - Search entry: CTkEntry with placeholder "Search by name..."
  3. Below filter bar: CTkScrollableFrame for the item list
  4. Below list: "Continue" button (right-aligned)
  5. Wire filter controls to `_on_food_filter_changed()` callback

- **Files**: `src/ui/builders/finished_good_builder.py`

- **Notes**:
  - Use `ctk.CTkSegmentedButton` for the bare/assembly toggle if available, otherwise two CTkButtons with active state
  - Filter bar should be compact (one row) to maximize list space
  - Category values populated at dialog open time from service queries

### Subtask T011 -- Implement data query for available FinishedGoods with filtering

- **Purpose**: Fetch selectable food items from the database with category, type, and search filters applied.

- **Steps**:
  1. Implement `_query_food_items()` method that returns filtered list of selectable items:
     ```python
     def _query_food_items(self) -> List[Dict]:
         """Query FinishedGoods matching current filter state.
         Returns list of dicts: {id, display_name, category, assembly_type, type}
         """
     ```
  2. Query approach:
     - Get all FinishedGoods via `FinishedGoodService.get_all_finished_goods()`
     - Filter by bare/assembly toggle:
       - "Bare Items Only": `fg.assembly_type == AssemblyType.BARE`
       - "Include Assemblies": Include all types (both bare and non-bare)
     - Filter by category (if not "All Categories"): Match category from the FG's components or source recipe
     - Filter by search text: case-insensitive partial match on `display_name`
  3. Implement `_get_distinct_categories()`:
     - Query all FinishedUnits, collect distinct non-null `category` values
     - Sort alphabetically, prepend "All Categories"
  4. For each result item, include:
     - `id`: FinishedGood ID
     - `display_name`: FinishedGood display name
     - `type`: `"finished_unit"` if BARE (wraps a single FinishedUnit), `"finished_good"` if assembly
     - `component_id`: For BARE items, the underlying FinishedUnit ID; for assemblies, the FinishedGood ID itself

- **Files**: `src/ui/builders/finished_good_builder.py`

- **Notes**:
  - BARE FinishedGoods wrap a single FinishedUnit. When selected, the Composition should reference the FinishedUnit (type="finished_unit", id=finished_unit_id), not the FinishedGood
  - For non-BARE FinishedGoods (assemblies), the Composition references the FinishedGood itself (type="finished_good", id=finished_good_id)
  - Category for BARE items comes from the wrapped FinishedUnit's `category` field
  - Category for assembly items: derive from the most common category of their components, or show in "Assemblies" group

### Subtask T012 -- Implement scrollable checkbox list with per-item quantity entries

- **Purpose**: Render the filtered food items as a multi-select list with quantity fields.

- **Steps**:
  1. Implement `_render_food_items(items: List[Dict])`:
     - Clear existing children from the scrollable frame
     - For each item, create a row frame containing:
       ```
       [checkbox] [name_label (expanding)] [qty_entry (width=60)]
       ```
     - CTkCheckBox: Variable linked to selection state; command triggers `_on_food_item_toggled(item_id)`
     - Name label: Display name, truncated with ellipsis for long names
     - Quantity entry: CTkEntry, initially disabled; enabled when checkbox checked; default value "1"
  2. Implement `_on_food_item_toggled(item_id: int)`:
     - If now checked: enable quantity entry, set default "1", add to `self._food_selections`
     - If now unchecked: disable quantity entry, clear value, remove from `self._food_selections`
     - Set `self._has_changes = True`
  3. Quantity validation on entry:
     - Bind `<FocusOut>` or `<KeyRelease>` to validate integer 1-999
     - If invalid, reset to "1"
     - Update quantity in `self._food_selections[item_id]`

- **Files**: `src/ui/builders/finished_good_builder.py`

- **Notes**:
  - Each row should have consistent height (~35px)
  - Use `pack(fill="x")` for rows, `side="left"` for checkbox, name; `side="right"` for quantity
  - Quantity entry: Restrict to digits only (validate command or KeyRelease handler)

### Subtask T013 -- Implement selection state management

- **Purpose**: Maintain global selection state that persists across filter changes.

- **Steps**:
  1. Initialize selection store:
     ```python
     self._food_selections: Dict[int, Dict] = {}
     # Key: component ID, Value: {"type": str, "id": int, "display_name": str, "quantity": int}
     ```
  2. When rendering items after filter change, restore check/quantity state:
     - For each rendered item, check if its ID is in `self._food_selections`
     - If yes: set checkbox checked, set quantity entry to stored value
     - If no: leave unchecked, quantity entry disabled
  3. When filter changes (category, bare/assembly, search):
     - Call `_query_food_items()` with new filters
     - Call `_render_food_items(items)` — this rebuilds the list but restores states from dict
  4. Selections are NOT cleared when filters change — only when user explicitly unchecks or clicks Start Over

- **Files**: `src/ui/builders/finished_good_builder.py`

- **Notes**:
  - This is the core UX innovation: selections are global, filter is just a "view" into available items
  - A user can select items from "Cookies" category, switch to "Cakes", select more, and all selections persist
  - When going back to Step 1 via "Change" button, the list re-renders with selections restored

### Subtask T014 -- Implement validation and Continue button

- **Purpose**: Enforce minimum-1-item rule and transition to Step 2 on Continue.

- **Steps**:
  1. Implement `_on_food_continue()` (bound to Continue button):
     - Validate: `len(self._food_selections) >= 1`
     - Validate: All selected items have `quantity >= 1`
     - If invalid: Show inline error message below the list (e.g., "Select at least one food item")
     - If valid:
       - Count selected items for summary: `f"{len(self._food_selections)} item(s) selected"`
       - Call `self._advance_to_step(2)` which marks step 1 completed and expands step 2
  2. Show validation error as a CTkLabel with red text below the list/above Continue button
  3. Clear error when user makes a selection change

- **Files**: `src/ui/builders/finished_good_builder.py`

- **Notes**:
  - Items with quantity 0 or blank are treated as unchecked per spec edge case 6
  - Before advancing, clean up: remove any items where quantity is 0 from `self._food_selections`

### Subtask T015 -- Write unit tests for food selection filtering and validation

- **Purpose**: Verify filtering logic, selection persistence, and validation rules.

- **Steps**:
  1. Add tests to `src/tests/test_finished_good_builder.py`:
     - `test_food_query_bare_only`: Mock service, verify only BARE items returned
     - `test_food_query_include_assemblies`: Verify all types returned
     - `test_food_query_category_filter`: Verify category filtering works
     - `test_food_query_search_filter`: Verify name search filtering
     - `test_food_selection_persists_across_filter`: Select item, change filter, verify selection preserved
     - `test_food_validation_requires_one_item`: Verify Continue blocked with no selections
     - `test_food_validation_requires_positive_quantity`: Verify quantity 0 treated as unchecked
     - `test_food_continue_advances_to_step_2`: Verify valid selection advances dialog

- **Files**: `src/tests/test_finished_good_builder.py`

- **Notes**:
  - Mock `FinishedGoodService.get_all_finished_goods()` and `finished_unit_service.get_all_finished_units()` to return controlled test data
  - Test the internal `_query_food_items()` and `_food_selections` dict directly for unit tests

## Risks & Mitigations

- **Risk**: Large number of items (200+) may cause slow rendering. **Mitigation**: CTkScrollableFrame handles this via viewport; consider batch rendering if needed.
- **Risk**: Category values may be inconsistent (None, empty, mixed case). **Mitigation**: Normalize to title case; skip None/empty.
- **Risk**: BARE FinishedGood may not have a clean link to its FinishedUnit. **Mitigation**: Query the FG's components to find the wrapped FinishedUnit ID.

## Definition of Done Checklist

- [ ] Food selection panel renders in Step 1 content frame
- [ ] Category dropdown populated from distinct categories
- [ ] Bare/Assembly toggle filters correctly
- [ ] Search filters by name (case-insensitive)
- [ ] Multi-select checkboxes with quantity entries work
- [ ] Selections persist across filter changes
- [ ] Validation blocks Continue without valid selections
- [ ] Continue advances to Step 2 with summary
- [ ] Unit tests pass
- [ ] No linting errors

## Review Guidance

- Select items in "Cookies" category, switch to "Cakes", then back — verify Cookies selections preserved
- Try entering quantity 0 or blank — verify treated as unchecked
- Try continuing with no selections — verify error message appears
- Verify BARE items map to FinishedUnit component type, assemblies to FinishedGood type

## Activity Log

- 2026-02-06T23:51:59Z -- system -- lane=planned -- Prompt created.
- 2026-02-07T00:19:42Z – claude-opus – shell_pid=27248 – lane=doing – Assigned agent via workflow command
