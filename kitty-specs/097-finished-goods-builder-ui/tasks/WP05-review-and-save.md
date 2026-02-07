---
work_package_id: WP05
title: Review & Save (Create Mode)
lane: "doing"
dependencies: [WP04]
base_branch: 097-finished-goods-builder-ui-WP04
base_commit: f8941c4e075f34fceb85767f384ed7789063c40a
created_at: '2026-02-07T00:35:16.697975+00:00'
subtasks:
- T021
- T022
- T023
- T024
- T025
- T026
phase: Phase C - Integration
assignee: ''
agent: ''
shell_pid: "31568"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-02-06T23:51:59Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP05 -- Review & Save (Create Mode)

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

- Implement Step 3 (Review & Save) content panel
- Component summary displays all food items and materials with quantities
- Editable name field with slug-based uniqueness pre-validation
- Notes text field and auto-suggested tags from component names
- Save button creates FinishedGood via `create_finished_good()` atomically
- Error handling displays validation errors, duplicate names, and service errors inline
- On success, dialog closes and returns result to parent
- Unit tests pass for review display, save operation, and error handling

**Implementation command**: `spec-kitty implement WP05 --base WP04`

## Context & Constraints

- **Feature**: 097-finished-goods-builder-ui
- **Plan**: Design Decision D-006 (save operation)
- **Research**: R-003 — service component format: `[{"type": str, "id": int, "quantity": int, "sort_order": int}]`
- **Service**: `FinishedGoodService.create_finished_good(display_name, assembly_type, components, **kwargs)`
  - `assembly_type` default: `AssemblyType.CUSTOM_ORDER` for builder-created items
  - Components format: `[{"type": "finished_unit"|"material_unit"|"finished_good", "id": int, "quantity": int, "sort_order": int}]`
  - Atomic: All-or-nothing transaction
  - Raises: `ValidationError`, `InvalidComponentError`, `CircularReferenceError`
- **Research**: R-009 — Name uniqueness via slug generation; service catches IntegrityError

## Subtasks & Detailed Guidance

### Subtask T021 -- Create review panel with component summary display

- **Purpose**: Show a clear, organized summary of all selected components before save.

- **Steps**:
  1. Create method `_create_review_step_content()` that populates `self.step3.content_frame`
  2. Layout:
     - "Food Items" section header (bold)
     - Scrollable list of food items: `"{display_name} x {quantity}"` per row
     - Separator
     - "Materials" section header (bold) — only if materials selected
     - Scrollable list of materials: `"{name} x {quantity}"` per row
     - If no materials: Show "No materials" label
     - Summary line: "Total: {N} food items, {M} materials"
  3. Implement `_refresh_review_summary()`:
     - Called when Step 3 is expanded (either by advancing or "Change" click)
     - Reads from `self._food_selections` and `self._material_selections`
     - Rebuilds the summary display
  4. Below summary: Notes text field, Tags display, Save button

- **Files**: `src/ui/builders/finished_good_builder.py`

- **Notes**:
  - Summary should be read-only (user can't change quantities here — must go back via "Change")
  - Use a CTkScrollableFrame if component list is long (>10 items)
  - Each row could include a small icon indicating component type (food vs material)

### Subtask T022 -- Implement editable name field with uniqueness pre-validation

- **Purpose**: Let user set or modify the FinishedGood name with early uniqueness feedback.

- **Steps**:
  1. The name entry is already in the dialog header (from WP02 T006)
  2. Implement `_validate_name_uniqueness()`:
     - Get current name from `self.name_entry.get().strip()`
     - Generate slug using same logic as service: lowercase, replace spaces with hyphens, strip special chars
     - Query: Check if a FinishedGood with that slug already exists
     - If exists (and not the current FG in edit mode): Show red border on name entry + error label
     - If unique: Show green border or clear error
  3. Bind validation to `<FocusOut>` event on name entry (don't validate on every keystroke — too noisy)
  4. Also validate on Save button click (before service call)

- **Files**: `src/ui/builders/finished_good_builder.py`

- **Notes**:
  - Slug generation: Use `re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')` to match service logic
  - In edit mode (WP06), exclude the current FG's ID from the uniqueness check
  - Pre-validation is advisory — the service also validates and catches IntegrityError as a fallback

### Subtask T023 -- Implement notes text field and auto-suggested tags

- **Purpose**: Allow user to add notes and see auto-generated tags from component names.

- **Steps**:
  1. Add notes section below component summary:
     ```python
     notes_label = ctk.CTkLabel(content, text="Notes:", font=ctk.CTkFont(weight="bold"))
     self.notes_text = ctk.CTkTextbox(content, height=80)
     ```
  2. Add tags section:
     - Auto-generate tags from component display names: extract key words
     - Display as comma-separated string in a CTkEntry (editable)
     - Example: Components "Almond Biscotti", "Hazelnut Biscotti" → tags: "almond, hazelnut, biscotti"
  3. Implement `_generate_tags()`:
     - Collect all display names from food and material selections
     - Extract unique significant words (skip common words like "the", "and", "x")
     - Join with ", "

- **Files**: `src/ui/builders/finished_good_builder.py`

- **Notes**:
  - Tags are a convenience — the FinishedGood model may or may not have a tags field
  - Check if FinishedGood model has a `tags` or similar field; if not, store in `notes` or skip tags
  - If no tags field exists on the model, the auto-generated tags can be prepended to notes

### Subtask T024 -- Implement Save button with create_finished_good() service call

- **Purpose**: Convert builder state to service format and create the FinishedGood atomically.

- **Steps**:
  1. Implement `_on_save()`:
     ```python
     def _on_save(self):
         name = self.name_entry.get().strip()
         if not name:
             self._show_save_error("Name is required")
             return

         # Build component list
         components = self._build_component_list()

         if not components:
             self._show_save_error("At least one food item is required")
             return

         try:
             fg = FinishedGoodService.create_finished_good(
                 display_name=name,
                 assembly_type=AssemblyType.CUSTOM_ORDER,
                 components=components,
                 notes=self.notes_text.get("1.0", "end-1c").strip() or None,
             )
             self.result = {"finished_good_id": fg.id, "display_name": fg.display_name}
             self.destroy()
         except ValidationError as e:
             self._show_save_error(str(e))
         except ServiceError as e:
             self._show_save_error(f"Save failed: {e}")
     ```
  2. Implement `_build_component_list()`:
     ```python
     def _build_component_list(self) -> List[Dict]:
         components = []
         sort_order = 0
         for item_id, sel in self._food_selections.items():
             components.append({
                 "type": sel["type"],  # "finished_unit" or "finished_good"
                 "id": sel["id"],
                 "quantity": sel["quantity"],
                 "sort_order": sort_order,
             })
             sort_order += 1
         for item_id, sel in self._material_selections.items():
             components.append({
                 "type": "material_unit",
                 "id": sel["id"],
                 "quantity": sel["quantity"],
                 "sort_order": sort_order,
             })
             sort_order += 1
         return components
     ```

- **Files**: `src/ui/builders/finished_good_builder.py`

- **Notes**:
  - `assembly_type` defaults to `CUSTOM_ORDER` for all builder-created items
  - Sort order: food items first (in selection order), then materials
  - The service handles slug generation, validation, and atomicity
  - `self.result` is set BEFORE `self.destroy()` so the parent can access it

### Subtask T025 -- Implement error handling and user feedback

- **Purpose**: Display errors inline and show success feedback.

- **Steps**:
  1. Implement `_show_save_error(message: str)`:
     - Display error as a CTkLabel with red text above the Save button
     - Clear any previous error first
  2. Implement `_clear_save_error()`:
     - Remove error label if present
  3. Handle specific error types:
     - `ValidationError`: Show validation message (e.g., "Display name is required")
     - `InvalidComponentError`: "One or more components are no longer available"
     - `CircularReferenceError`: "Cannot create circular reference"
     - Generic `ServiceError`: "Save failed: {message}"
  4. Success path: `self.destroy()` closes dialog; parent tab shows success message and refreshes

- **Files**: `src/ui/builders/finished_good_builder.py`

- **Notes**:
  - Error display should not require scrolling — show at bottom of review panel near Save button
  - Clear errors when user makes any change (modifies name, goes back to change selections)

### Subtask T026 -- Write unit tests for review display, save operation, and error handling

- **Purpose**: Verify review panel rendering, component list building, and save error handling.

- **Steps**:
  1. Add tests to `src/tests/test_finished_good_builder.py`:
     - `test_review_summary_shows_all_components`: Set up selections, advance to step 3, verify summary
     - `test_review_summary_no_materials`: Skip materials, verify "No materials" shown
     - `test_build_component_list_format`: Verify `_build_component_list()` output matches service format
     - `test_build_component_list_sort_order`: Verify food items come before materials
     - `test_save_calls_create_service`: Mock service, verify correct arguments passed
     - `test_save_validation_error_shows_message`: Mock service to raise ValidationError, verify error displayed
     - `test_save_empty_name_shows_error`: Try save with empty name, verify error
     - `test_save_success_sets_result_and_closes`: Verify result set and dialog destroyed

- **Files**: `src/tests/test_finished_good_builder.py`

## Risks & Mitigations

- **Risk**: Slug collision not caught by pre-validation. **Mitigation**: Service has IntegrityError fallback.
- **Risk**: Component IDs may have changed between selection and save. **Mitigation**: Service validates all component IDs exist.

## Definition of Done Checklist

- [ ] Review panel shows food items and materials with quantities
- [ ] Name field validates uniqueness (pre-validation)
- [ ] Notes text field captures input
- [ ] Tags auto-generated from component names
- [ ] Save creates FinishedGood with correct components via service
- [ ] Error messages display inline for validation/service errors
- [ ] Dialog closes and returns result on successful save
- [ ] Unit tests pass
- [ ] No linting errors

## Review Guidance

- Verify component summary matches selections from Steps 1 and 2
- Verify Save produces correct component format (check types, IDs, quantities, sort_order)
- Try saving with duplicate name — verify error message appears
- Try saving with empty name — verify validation prevents save
- Verify dialog closes on success and `result` is set

## Activity Log

- 2026-02-06T23:51:59Z -- system -- lane=planned -- Prompt created.
