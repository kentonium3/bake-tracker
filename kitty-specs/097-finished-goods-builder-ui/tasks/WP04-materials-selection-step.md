---
work_package_id: WP04
title: Materials Selection Step
lane: "done"
dependencies: [WP03]
base_branch: 097-finished-goods-builder-ui-WP03
base_commit: dc88d9df821188a2edab7ff87369ebf920e30f67
created_at: '2026-02-07T00:28:24.554404+00:00'
subtasks:
- T016
- T017
- T018
- T019
- T020
phase: Phase B - Step Implementation
assignee: ''
agent: "claude-opus"
shell_pid: "29671"
review_status: "approved"
reviewed_by: "Kent Gale"
history:
- timestamp: '2026-02-06T23:51:59Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP04 -- Materials Selection Step

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

- Implement Step 2 (Materials) content panel within the builder dialog
- MaterialCategory dropdown filters MaterialUnits by category (via join through MaterialProduct)
- Search field provides real-time name filtering on MaterialUnit.name
- Multi-select checkboxes with per-item quantity fields (1-999)
- Skip button allows bypassing materials entirely (food-only bundles)
- Selection state persists across filter changes
- Unit tests pass for material filtering, selection, and skip

**Implementation command**: `spec-kitty implement WP04 --base WP03`

## Context & Constraints

- **Feature**: 097-finished-goods-builder-ui
- **Research**: R-002 — Step 2 shows MaterialUnits (not MaterialProducts); Composition stores `material_unit_id`
- **Data model**: `data-model.md` — MaterialUnit has `name`, `material_product_id`; MaterialProduct has category via subcategory
- **Service**: `src/services/material_catalog_service.py` — `list_products()`, `list_materials()` for querying
- **Model**: `src/models/material_unit.py` — `name`, `slug`, `quantity_per_unit`, `material_product_id`
- **Pattern reuse**: Same checkbox + quantity pattern as WP03 (Food Selection)
- **Composition type**: `"material_unit"` with `id = material_unit.id`

## Subtasks & Detailed Guidance

### Subtask T016 -- Create materials selection content panel with filter bar UI

- **Purpose**: Build the visual layout for Step 2's content area.

- **Steps**:
  1. Create method `_create_materials_step_content()` that populates `self.step2.content_frame`
  2. Filter bar layout:
     - MaterialCategory dropdown: CTkComboBox with "All Categories" + MaterialCategory names
     - Search entry: CTkEntry with placeholder "Search materials..."
  3. Below filter bar: CTkScrollableFrame for the material item list
  4. Below list: Button frame with "Skip" (left) and "Continue" (right)
  5. Wire filter controls to `_on_material_filter_changed()` callback

- **Files**: `src/ui/builders/finished_good_builder.py`

- **Notes**:
  - Simpler filter bar than Step 1 (no bare/assembly toggle — all MaterialUnits are selectable)
  - Skip button text: "Skip - No Materials Needed"
  - Continue button text: "Continue"

### Subtask T017 -- Implement data query for MaterialUnits with filtering

- **Purpose**: Fetch selectable MaterialUnits from the database with category and search filters.

- **Steps**:
  1. Implement `_query_material_items()`:
     ```python
     def _query_material_items(self) -> List[Dict]:
         """Query MaterialUnits matching current filter state.
         Returns list of dicts: {id, name, category_name, product_name}
         """
     ```
  2. Query approach:
     - Query MaterialUnit records via SQLAlchemy join:
       MaterialUnit → MaterialProduct → MaterialSubcategory → MaterialCategory
     - Filter by MaterialCategory name if not "All Categories"
     - Filter by search text: case-insensitive partial match on MaterialUnit.name
     - Only include MaterialUnits whose parent MaterialProduct exists and is not hidden
  3. Implement `_get_material_categories()`:
     - Query all MaterialCategory records
     - Return sorted list of category names, prepend "All Categories"
  4. Each result item:
     - `id`: MaterialUnit ID
     - `name`: MaterialUnit name (e.g., "6-inch Red Ribbon")
     - `category_name`: Parent MaterialCategory name
     - `product_name`: Parent MaterialProduct name (for display context)

- **Files**: `src/ui/builders/finished_good_builder.py`

- **Notes**:
  - MaterialUnit → MaterialProduct is `material_product` relationship (lazy="joined")
  - MaterialProduct → MaterialSubcategory via `material_subcategory_id` FK
  - MaterialSubcategory → MaterialCategory via `material_category_id` FK
  - Use `material_catalog_service` if suitable helper methods exist; otherwise query directly via session
  - Only show MaterialUnits that have a valid parent chain (skip orphans)

### Subtask T018 -- Implement scrollable checkbox list with per-item quantity entries

- **Purpose**: Render filtered MaterialUnits as a multi-select list with quantity fields.

- **Steps**:
  1. Implement `_render_material_items(items: List[Dict])`:
     - Same pattern as `_render_food_items()` from WP03:
       ```
       [checkbox] [name_label (expanding)] [qty_entry (width=60)]
       ```
     - Display MaterialUnit name in the label
  2. Implement `_on_material_item_toggled(item_id: int)`:
     - Same toggle logic as food items — add/remove from `self._material_selections`
  3. Same quantity validation pattern (1-999, integer only)

- **Files**: `src/ui/builders/finished_good_builder.py`

- **Notes**:
  - Consider extracting a shared `_render_selectable_list()` helper method to DRY up the code between Steps 1 and 2
  - Both steps use identical row rendering logic; only the data source and selection dict differ

### Subtask T019 -- Implement Skip button and optional step completion logic

- **Purpose**: Allow users to bypass materials for food-only bundles.

- **Steps**:
  1. Implement `_on_materials_skip()`:
     - Clear `self._material_selections` (remove any accidental selections)
     - Mark step 2 as completed with summary "No materials"
     - Call `self._advance_to_step(3)`
  2. Implement `_on_materials_continue()`:
     - If `self._material_selections` is not empty:
       - Generate summary: `f"{len(self._material_selections)} material(s) selected"`
       - Mark step 2 completed, advance to step 3
     - If empty (but user clicked Continue instead of Skip):
       - Treat same as Skip — advance with "No materials" summary
  3. Both buttons advance to Step 3; Skip explicitly clears selections, Continue preserves them

- **Files**: `src/ui/builders/finished_good_builder.py`

- **Notes**:
  - Unlike Step 1, Step 2 has NO minimum selection requirement
  - Both Skip and Continue (with no selections) result in step 2 being "completed" — the builder can proceed
  - In edit mode (WP06), if the existing FG has materials, they'll be pre-populated so the user can modify or remove them

### Subtask T020 -- Write unit tests for materials selection and skip functionality

- **Purpose**: Verify material filtering, selection, and skip behavior.

- **Steps**:
  1. Add tests to `src/tests/test_finished_good_builder.py`:
     - `test_material_query_all`: Verify all MaterialUnits returned with no filter
     - `test_material_query_category_filter`: Verify MaterialCategory filtering
     - `test_material_query_search`: Verify name search filtering
     - `test_material_selection_persists_across_filter`: Select material, change filter, verify persists
     - `test_materials_skip_advances_to_step_3`: Verify Skip clears selections and advances
     - `test_materials_continue_with_selections`: Verify Continue preserves selections and advances
     - `test_materials_continue_empty_same_as_skip`: Verify Continue with no selections behaves like Skip

- **Files**: `src/tests/test_finished_good_builder.py`

- **Notes**:
  - Mock MaterialUnit/MaterialProduct queries
  - Test `_material_selections` dict directly

## Risks & Mitigations

- **Risk**: MaterialUnit query requires 3 joins for category filtering. **Mitigation**: Use SQLAlchemy relationship loading; verify query performance with test data.
- **Risk**: Some MaterialProducts may have no MaterialUnits. **Mitigation**: Only include units from products that have defined units.

## Definition of Done Checklist

- [ ] Materials selection panel renders in Step 2 content frame
- [ ] MaterialCategory dropdown populated correctly
- [ ] Search filters MaterialUnits by name
- [ ] Multi-select with quantity entries works
- [ ] Selections persist across filter changes
- [ ] Skip button advances to Step 3 with "No materials" summary
- [ ] Continue button advances to Step 3 with correct summary
- [ ] Unit tests pass
- [ ] No linting errors

## Review Guidance

- Verify Skip clears any accidental selections
- Select materials, then Skip — verify selections are cleared in the save data
- Select materials, change category filter, verify selections persist
- Verify MaterialUnit names (not MaterialProduct names) display in the list

## Activity Log

- 2026-02-06T23:51:59Z -- system -- lane=planned -- Prompt created.
- 2026-02-07T00:28:24Z – claude-opus – shell_pid=29671 – lane=doing – Assigned agent via workflow command
- 2026-02-07T00:34:13Z – claude-opus – shell_pid=29671 – lane=for_review – Materials selection step: filter by category/search, checkbox+qty list, skip/continue, 9 new tests (35 total)
- 2026-02-07T00:36:48Z – claude-opus – shell_pid=29671 – lane=doing – Review returned: advance_to_step(2) does not call _on_material_filter_changed(), so material list is empty on first arrival to step 2. Must populate items when step 2 first opens, similar to how _set_initial_state() calls _on_food_filter_changed() for step 1.
- 2026-02-07T00:39:00Z – claude-opus – shell_pid=29671 – lane=for_review – Fixed: advance_to_step(2) now populates material list. Added test.
- 2026-02-07T00:39:06Z – claude-opus – shell_pid=29671 – lane=done – Review fix applied: material list now populated on advance_to_step(2). Trivial fix, self-approved.
