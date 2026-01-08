---
work_package_id: WP05
title: Assignment Dialog
lane: done
history:
- timestamp: '2025-12-21T12:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
agent: claude
assignee: claude
phase: Phase 4 - UI Assignment
review_status: ''
reviewed_by: ''
shell_pid: '94728'
subtasks:
- T024
- T025
- T026
- T027
- T028
- T029
---

# Work Package Prompt: WP05 - Assignment Dialog

## Objectives & Success Criteria

- Create new PackagingAssignmentDialog class
- Show available specific products with checkbox + quantity input
- Display running total: "Assigned: X / Y needed"
- Validate before save (sum must equal requirement)
- Integrate dialog trigger into assembly screen
- Update cost display after assignment (estimated -> actual)

## Context & Constraints

**References**:
- `kitty-specs/026-deferred-packaging-decisions/plan.md` - Phase 4 details
- `kitty-specs/026-deferred-packaging-decisions/spec.md` - User Story 2
- `kitty-specs/026-deferred-packaging-decisions/data-model.md` - Assignment structure
- Existing dialog patterns in `src/ui/`

**Constraints**:
- Follow CustomTkinter patterns used in codebase
- Modal dialog behavior
- Clear visual feedback for validation state
- Performance: respond in <200ms

## Subtasks & Detailed Guidance

### Subtask T024 - Create PackagingAssignmentDialog class

- **Purpose**: New dialog for material assignment workflow
- **Steps**:
  1. Create `src/ui/packaging_assignment_dialog.py`
  2. Extend appropriate CustomTkinter dialog base
  3. Accept `composition_id` as parameter
  4. Load composition and available inventory on init
  5. Set up dialog layout with header, content, and action buttons
- **Files**: `src/ui/packaging_assignment_dialog.py` (new)
- **Parallel?**: No
- **Notes**:
  - Header shows: "Assign Materials for: [generic product name]"
  - Required quantity from `composition.component_quantity`

### Subtask T025 - Implement products list with quantities

- **Purpose**: Show available specific products for selection
- **Steps**:
  1. Query inventory items matching the generic `product_name`
  2. For each product with inventory:
     - Checkbox for selection
     - Product name and brand display
     - Available quantity label
     - CTkEntry for quantity to assign
  3. Disable quantity input when checkbox unchecked
  4. Bound quantity input to available amount
- **Files**: `src/ui/packaging_assignment_dialog.py`
- **Parallel?**: No
- **Notes**:
  - Use `packaging_service.get_generic_inventory_summary()` for data
  - Group by brand for clarity

### Subtask T026 - Add running total display

- **Purpose**: Real-time feedback on assignment progress
- **Steps**:
  1. Add prominent total display at bottom of list
  2. Format: "Assigned: 30 / 50 needed"
  3. Update on any quantity change
  4. Color code:
     - Red if over requirement
     - Orange if under
     - Green if exact match
- **Files**: `src/ui/packaging_assignment_dialog.py`
- **Parallel?**: No
- **Notes**: Use trace/callback on entry widgets for real-time update

### Subtask T027 - Implement save validation

- **Purpose**: Prevent invalid assignments
- **Steps**:
  1. On save button click, validate:
     - Total assigned equals requirement
     - Each quantity <= available inventory
     - At least one product selected
  2. If invalid, show error message and prevent save
  3. If valid, call `packaging_service.assign_materials()`
  4. Close dialog on success
- **Files**: `src/ui/packaging_assignment_dialog.py`
- **Parallel?**: No
- **Notes**: Disable save button until validation passes

### Subtask T028 - Integrate dialog into assembly screen

- **Purpose**: Allow triggering assignment from assembly view
- **Steps**:
  1. Add "Assign Materials" button/link to compositions list
  2. Only show for compositions where `is_generic=True`
  3. Button opens PackagingAssignmentDialog
  4. Refresh display after dialog closes
- **Files**: `src/ui/assembly_screen.py` or equivalent
- **Parallel?**: No
- **Notes**: Consider showing pending indicator for unassigned items

### Subtask T029 - Update cost display after assignment

- **Purpose**: Switch from estimated to actual cost after assignment
- **Steps**:
  1. After successful assignment, recalculate costs
  2. Call `packaging_service.get_actual_cost(composition_id)`
  3. Update cost display in parent screen
  4. Remove "Estimated" label, show actual cost
- **Files**: `src/ui/packaging_assignment_dialog.py`, parent screen
- **Parallel?**: No
- **Notes**: Refresh parent screen's cost totals

## Test Strategy

Manual testing checklist:
1. Open assembly with generic packaging requirement
2. Click "Assign Materials" - dialog opens
3. Verify available products listed with correct quantities
4. Select products and enter quantities
5. Verify running total updates correctly
6. Try to save with wrong total - verify error
7. Correct quantities and save - verify success
8. Verify cost display updated from estimated to actual

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Quantity validation UX confusing | Clear color coding; instant feedback |
| Inventory changes during dialog | Refresh on focus; validate on save |
| Large product list overwhelming | Group by brand; consider scrollable list |

## Definition of Done Checklist

- [ ] PackagingAssignmentDialog class created
- [ ] Products list with checkboxes and quantities working
- [ ] Running total updates in real-time
- [ ] Validation prevents invalid saves
- [ ] Dialog integrated into assembly screen
- [ ] Cost display updates after assignment
- [ ] Manual testing completed

## Review Guidance

- Test with various quantities (under, over, exact)
- Verify validation error messages are clear
- Check that dialog closes cleanly on cancel
- Confirm parent screen updates after assignment

## Activity Log

- 2025-12-21T12:00:00Z - system - lane=planned - Prompt created.
- 2025-12-21T22:07:18Z – system – shell_pid= – lane=doing – Moved to doing
- 2025-12-21T22:15:38Z – system – shell_pid= – lane=for_review – Moved to for_review
- 2025-12-22T02:27:53Z – system – shell_pid= – lane=done – Approved
