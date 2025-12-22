---
work_package_id: "WP04"
subtasks:
  - "T018"
  - "T019"
  - "T020"
  - "T021"
  - "T022"
  - "T023"
title: "Planning UI"
phase: "Phase 3 - UI Planning"
lane: "done"
assignee: ""
agent: "system"
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-21T12:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP04 - Planning UI

## Objectives & Success Criteria

- Add "Specific material" / "Generic product" toggle to composition editor
- Create generic product dropdown populated from packaging products
- Display inventory summary with total and breakdown by brand
- Show estimated cost with "Estimated" label
- Persist `is_generic=True` when saving generic compositions
- UI operations complete in <200ms

## Context & Constraints

**References**:
- `kitty-specs/026-deferred-packaging-decisions/plan.md` - Phase 3 details
- `kitty-specs/026-deferred-packaging-decisions/spec.md` - User Story 1
- Existing UI patterns in `src/ui/`

**Constraints**:
- Follow CustomTkinter patterns used in codebase
- Maintain existing UI structure
- Keep UI simple for non-technical user
- Performance: operations <200ms

## Subtasks & Detailed Guidance

### Subtask T018 - Add radio button toggle

- **Purpose**: Let user choose between specific product and generic product type
- **Steps**:
  1. Locate composition editing screen (likely in assembly/package editor)
  2. Add CTkRadioButton group: "Specific material" / "Generic product"
  3. Default to "Specific material" for backward compatibility
  4. Wire up selection to show/hide appropriate input widgets
- **Files**: `src/ui/composition_editor.py` or equivalent
- **Parallel?**: No
- **Notes**:
  - "Specific material" shows existing product dropdown
  - "Generic product" shows new generic product dropdown + summary

### Subtask T019 - Create generic product dropdown

- **Purpose**: Allow selection of generic product type from available options
- **Steps**:
  1. Create CTkComboBox for generic product selection
  2. Populate with `packaging_service.get_generic_products()`
  3. Show only when "Generic product" radio selected
  4. On selection change, update inventory summary and cost
- **Files**: `src/ui/composition_editor.py` or equivalent
- **Parallel?**: No
- **Notes**: Dropdown shows product_name values like "Cellophane Bags 6x10"

### Subtask T020 - Add inventory summary widget

- **Purpose**: Show total available and breakdown by brand/design
- **Steps**:
  1. Create summary widget (CTkFrame with labels)
  2. Call `packaging_service.get_generic_inventory_summary(product_name)`
  3. Display total: "Total available: 150"
  4. Display breakdown as expandable list:
     - "Snowflake design: 75"
     - "Holly pattern: 50"
     - "Plain: 25"
  5. Update when product selection changes
- **Files**: `src/ui/composition_editor.py` or new widget file
- **Parallel?**: No
- **Notes**: Consider collapsible section if breakdown is long

### Subtask T021 - Display estimated cost

- **Purpose**: Show estimated cost with clear "Estimated" label
- **Steps**:
  1. Calculate cost using `packaging_service.get_estimated_cost()`
  2. Display with prominent "Estimated" badge/label
  3. Update when product or quantity changes
  4. Format as currency: "Estimated: $12.50"
- **Files**: `src/ui/composition_editor.py` or equivalent
- **Parallel?**: No
- **Notes**: Visual distinction from actual costs (use different color/style)

### Subtask T022 - Persist is_generic flag

- **Purpose**: Save generic selection to database
- **Steps**:
  1. Capture radio button selection on save
  2. Pass `is_generic=True` to composition_service when saving
  3. For generic: set `packaging_product_id` to template product
  4. Verify composition saved correctly
- **Files**: `src/ui/composition_editor.py` or equivalent
- **Parallel?**: No
- **Notes**: Template product is any product with matching `product_name`

### Subtask T023 - Update UI validation

- **Purpose**: Validate input based on selected mode
- **Steps**:
  1. When "Specific material": require product selection (existing validation)
  2. When "Generic product": require generic product type selection
  3. Validate quantity is positive in both modes
  4. Show appropriate error messages
- **Files**: `src/ui/composition_editor.py` or equivalent
- **Parallel?**: No
- **Notes**: Validation should be consistent with existing patterns

## Test Strategy

Manual testing checklist:
1. Open composition editor
2. Verify radio buttons appear and default to "Specific material"
3. Select "Generic product" - verify dropdown appears
4. Select a generic product type - verify summary shows
5. Enter quantity - verify estimated cost updates
6. Save - verify composition saved with `is_generic=True`
7. Reopen - verify saved values load correctly

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| UI complexity confuses user | Clear visual separation; prominent labels |
| Performance with large inventory | Cache inventory summary; lazy load breakdown |
| Missing product types | Show helpful message if no generic products available |

## Definition of Done Checklist

- [x] Radio button toggle implemented
- [x] Generic product dropdown populated and working
- [x] Inventory summary displays correctly
- [x] Estimated cost shows with "Estimated" label
- [x] `is_generic` flag saved correctly
- [x] Validation works for both modes
- [ ] UI responds in <200ms
- [ ] Manual testing completed

## Review Guidance

- Test both modes (specific and generic)
- Verify saved data loads correctly on reopen
- Check visual distinction between estimated and actual costs
- Confirm inventory summary updates on product change

## Activity Log

- 2025-12-21T12:00:00Z - system - lane=planned - Prompt created.
- 2025-12-21T22:05:32Z - system - lane=doing - Moved to doing
- 2025-12-21T22:10:00Z - claude - lane=doing - Implemented PackagingRow with Specific/Generic toggle, inventory summary, estimated cost; updated packages_tab.py to pass is_generic; updated _populate_form to load is_generic on edit
- 2025-12-21T22:06:44Z – system – shell_pid= – lane=for_review – Moved to for_review
- 2025-12-22T02:27:39Z – system – shell_pid= – lane=done – Approved
