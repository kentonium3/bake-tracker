---
work_package_id: WP06
title: Edit Mode
lane: "done"
dependencies: [WP05]
base_branch: 097-finished-goods-builder-ui-WP05
base_commit: 0995392f6b9db5523c2fc8732fa0100c560713fb
created_at: '2026-02-07T00:43:55.428898+00:00'
subtasks:
- T027
- T028
- T029
- T030
- T031
phase: Phase C - Integration
assignee: ''
agent: "claude-opus"
shell_pid: "33322"
review_status: "approved"
reviewed_by: "Kent Gale"
history:
- timestamp: '2026-02-06T23:51:59Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP06 -- Edit Mode

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

- Builder dialog opens in edit mode when `finished_good` parameter is provided
- All steps pre-populated from existing FinishedGood component data
- Dialog opens directly to Step 3 (Review) with Steps 1-2 marked completed
- Current FinishedGood excluded from selectable items in Step 1 (prevents self-reference)
- Save in edit mode calls `update_finished_good()` (not create)
- Name uniqueness validation excludes the current item's slug
- Edit → modify → save round-trip works correctly

**Implementation command**: `spec-kitty implement WP06 --base WP05`

## Context & Constraints

- **Feature**: 097-finished-goods-builder-ui
- **Plan**: Design Decision D-005 (edit mode loading)
- **Research**: R-003 — service uses delete-and-replace for components on update
- **Service**: `FinishedGoodService.update_finished_good(finished_good_id, display_name, assembly_type, components, notes)`
  - Components list replaces ALL existing components atomically
  - Pass empty list `[]` to clear all components
- **Composition model**: `composition.py` — `component_type` property returns "finished_unit", "finished_good", "material_unit"
- **Session management**: Reload FinishedGood via service before populating to avoid detached ORM objects
- **Self-reference**: Database constraint `ck_composition_no_self_reference` and service validation

## Subtasks & Detailed Guidance

### Subtask T027 -- Implement edit mode initialization

- **Purpose**: Accept a FinishedGood parameter and set up the dialog for editing.

- **Steps**:
  1. Modify `__init__()` to handle edit mode:
     ```python
     def __init__(self, parent, finished_good=None):
         # ... existing setup ...
         self._finished_good = finished_good
         self._is_edit_mode = finished_good is not None
         self._finished_good_id = finished_good.id if finished_good else None

         if self._is_edit_mode:
             self.title(f"Edit: {finished_good.display_name}")
         else:
             self.title("Create Finished Good")
     ```
  2. After widget creation, if edit mode:
     - Call `self._load_existing_data(finished_good)`
  3. Implement `_load_existing_data(fg: FinishedGood)`:
     - Reload FinishedGood via service to ensure fresh data with eager-loaded components:
       ```python
       fg = FinishedGoodService.get_finished_good_by_id(fg.id)
       ```
     - Populate name entry: `self.name_entry.insert(0, fg.display_name)`
     - Populate notes: `self.notes_text.insert("1.0", fg.notes or "")`
     - Partition components by type (T028)

- **Files**: `src/ui/builders/finished_good_builder.py`

- **Notes**:
  - Reloading via service prevents detached ORM objects (see CLAUDE.md Session Management)
  - The `finished_good` parameter is the ORM object from the tab's selection

### Subtask T028 -- Pre-populate food and material selection states from existing components

- **Purpose**: Convert existing Composition records into the builder's internal selection state format.

- **Steps**:
  1. Implement `_populate_selections_from_components(fg: FinishedGood)`:
     ```python
     for comp in fg.components:
         if comp.component_type == "finished_unit":
             self._food_selections[comp.finished_unit_id] = {
                 "type": "finished_unit",
                 "id": comp.finished_unit_id,
                 "display_name": comp.component_name,
                 "quantity": int(comp.component_quantity),
             }
         elif comp.component_type == "finished_good":
             self._food_selections[comp.finished_good_id] = {
                 "type": "finished_good",
                 "id": comp.finished_good_id,
                 "display_name": comp.component_name,
                 "quantity": int(comp.component_quantity),
             }
         elif comp.component_type == "material_unit":
             self._material_selections[comp.material_unit_id] = {
                 "type": "material_unit",
                 "id": comp.material_unit_id,
                 "display_name": comp.component_name,
                 "quantity": int(comp.component_quantity),
             }
         # packaging_product type is not managed by builder (legacy)
     ```
  2. Handle edge case: component's source entity may have been deleted since the FG was created
     - If `comp.component_name` returns "Unknown Component", mark as unavailable
     - Show warning in review summary for unavailable components

- **Files**: `src/ui/builders/finished_good_builder.py`

- **Notes**:
  - `component_quantity` is Float in the model but quantities should be int for the builder
  - `component_name` property on Composition handles null relationships gracefully
  - `packaging_product` type compositions are NOT loaded into the builder (legacy; builder doesn't manage these)

### Subtask T029 -- Open builder to Step 3 in edit mode with Steps 1-2 marked completed

- **Purpose**: In edit mode, user sees the Review step first so they can assess current state before making changes.

- **Steps**:
  1. After loading data, set step states:
     ```python
     food_count = len(self._food_selections)
     material_count = len(self._material_selections)

     self.step1.mark_completed(f"{food_count} item(s) selected")
     self._step_completed[1] = True

     if material_count > 0:
         self.step2.mark_completed(f"{material_count} material(s) selected")
     else:
         self.step2.mark_completed("No materials")
     self._step_completed[2] = True

     self.step3.set_state("active")
     self.step3.expand()
     ```
  2. Refresh review summary to show existing components
  3. Set `self._has_changes = False` (no changes yet in edit mode)

- **Files**: `src/ui/builders/finished_good_builder.py`

### Subtask T030 -- Implement self-reference prevention

- **Purpose**: Prevent the user from adding the FinishedGood being edited as a component of itself.

- **Steps**:
  1. In `_query_food_items()`, when "Include assemblies" is active:
     - Exclude the current FinishedGood from results:
       ```python
       if self._is_edit_mode:
           items = [item for item in items if item["id"] != self._finished_good_id
                    or item["type"] != "finished_good"]
       ```
  2. This filtering happens at query/display time — the user simply never sees the current FG in the list
  3. The service also validates circular references as a safety net

- **Files**: `src/ui/builders/finished_good_builder.py`

- **Notes**:
  - Only filter when `_is_edit_mode` is True — in create mode there's no self to exclude
  - Only filter FinishedGood items (type="finished_good"), not FinishedUnits

### Subtask T031 -- Implement Save in edit mode with update service

- **Purpose**: Use `update_finished_good()` instead of `create_finished_good()` when in edit mode.

- **Steps**:
  1. Modify `_on_save()` to branch on edit mode:
     ```python
     def _on_save(self):
         name = self.name_entry.get().strip()
         if not name:
             self._show_save_error("Name is required")
             return

         components = self._build_component_list()
         if not components:
             self._show_save_error("At least one food item is required")
             return

         try:
             if self._is_edit_mode:
                 fg = FinishedGoodService.update_finished_good(
                     self._finished_good_id,
                     display_name=name,
                     components=components,
                     notes=self.notes_text.get("1.0", "end-1c").strip() or None,
                 )
             else:
                 fg = FinishedGoodService.create_finished_good(
                     display_name=name,
                     assembly_type=AssemblyType.CUSTOM_ORDER,
                     components=components,
                     notes=self.notes_text.get("1.0", "end-1c").strip() or None,
                 )
             self.result = {"finished_good_id": fg.id, "display_name": fg.display_name}
             self.destroy()
         except (ValidationError, ServiceError) as e:
             self._show_save_error(str(e))
     ```
  2. Modify `_validate_name_uniqueness()` to exclude current item:
     - When checking slug collision, skip the current `self._finished_good_id`
  3. Note: `update_finished_good()` uses delete-and-replace for components — the full list is sent, not a diff

- **Files**: `src/ui/builders/finished_good_builder.py`

- **Notes**:
  - In edit mode, `assembly_type` is NOT changed (preserve existing type)
  - Only `display_name`, `components`, and `notes` are updated
  - The service handles slug regeneration if name changes

## Risks & Mitigations

- **Risk**: Detached ORM objects from the parent tab's selection. **Mitigation**: Reload via service with fresh session.
- **Risk**: Deleted component source entities. **Mitigation**: Show "(unavailable)" warning and exclude from save.
- **Risk**: Concurrent edits (another process modifies the FG). **Mitigation**: Single-user desktop; not a concern.

## Definition of Done Checklist

- [ ] Edit mode opens when `finished_good` parameter provided
- [ ] All existing components pre-populated in food/material selections
- [ ] Dialog opens to Step 3 (Review) with Steps 1-2 marked completed
- [ ] Current FinishedGood excluded from Step 1 selectable items
- [ ] Save calls `update_finished_good()` with correct arguments
- [ ] Name uniqueness validation excludes current item
- [ ] Edit → modify quantity → save persists correctly
- [ ] Edit → add component → save persists correctly
- [ ] Edit → remove component → save removes correctly
- [ ] No linting errors

## Review Guidance

- Create a FG with 3 food items + 1 material, close, reopen in edit mode — verify all 4 components shown
- In edit mode, change a quantity and save — verify the change persists (reload and check)
- In edit mode, remove a food item and save — verify the component is deleted
- In edit mode, add a new food item and save — verify the new component appears
- Verify the current FG doesn't appear in its own selectable items list

## Activity Log

- 2026-02-06T23:51:59Z -- system -- lane=planned -- Prompt created.
- 2026-02-07T00:43:55Z – claude-opus – shell_pid=33322 – lane=doing – Assigned agent via workflow command
- 2026-02-07T00:47:47Z – claude-opus – shell_pid=33322 – lane=for_review – Ready for review: Edit mode with selection population, self-reference prevention, update service call. 58 tests pass, lint clean.
- 2026-02-07T00:54:16Z – claude-opus – shell_pid=33322 – lane=done – Review passed: all 10 checklist items verified. 58/58 tests pass, 0 lint errors.
