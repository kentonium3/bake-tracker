---
work_package_id: "WP03"
subtasks:
  - "T016"
  - "T017"
  - "T018"
  - "T019"
  - "T020"
  - "T021"
  - "T022"
  - "T023"
  - "T024"
  - "T025"
title: "UI - Record Production Dialog"
phase: "Phase 3 - UI Record Dialog"
lane: "done"
assignee: "claude"
agent: "claude-reviewer"
shell_pid: "74330"
history:
  - timestamp: "2025-12-21T16:55:08Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP03 - UI - Record Production Dialog

## Objectives & Success Criteria

- Loss quantity auto-calculated and displayed when actual_yield < expected_yield
- Expandable loss details section (collapsed by default)
- Loss details section auto-expands when loss detected
- Loss category dropdown with all LossCategory enum values
- Loss notes textbox for optional details
- Cost breakdown display: good units vs lost units with dollar amounts
- Real-time updates as actual_yield changes
- Validation prevents actual_yield > expected_yield
- Confirmation dialog shows loss information

## Context & Constraints

- **Spec**: `kitty-specs/025-production-loss-tracking/spec.md` - User Stories 1, 3, 4, 5
- **Plan**: `kitty-specs/025-production-loss-tracking/plan.md` - Phase 3
- **Existing UI**: `src/ui/forms/record_production_dialog.py` (read this first!)
- **Constitution**: `.kittify/memory/constitution.md` - User-Centric Design

**Key Constraints**:
- UI must NOT contain business logic (per Layered Architecture)
- Expandable section keeps default view clean
- Loss recording adds <30s to workflow (SC-001)
- Use CustomTkinter widgets consistently with existing dialog

**Dependencies**:
- Requires WP02 complete (service must accept loss parameters)

## Subtasks & Detailed Guidance

### Subtask T016 - Add loss_quantity calculation on yield change
- **Purpose**: Auto-calculate losses to reduce user burden (FR-002)
- **File**: `src/ui/forms/record_production_dialog.py`
- **Steps**:
  1. Add method `_calculate_loss_quantity()`:
     ```python
     def _calculate_loss_quantity(self) -> int:
         """Calculate loss quantity from expected vs actual yield."""
         batch_count = self._get_batch_count()
         expected = self._calculate_expected_yield(batch_count)
         actual = self._get_actual_yield()
         return max(0, expected - actual)
     ```
  2. Call this in `_on_batch_changed()` and when actual yield changes
  3. Add binding to yield_entry for KeyRelease event
- **Parallel?**: Yes, with T017
- **Notes**: max(0, ...) prevents negative loss if validation fails

### Subtask T017 - Add read-only loss_quantity display
- **Purpose**: Show user the calculated loss quantity
- **File**: `src/ui/forms/record_production_dialog.py`
- **Steps**:
  1. Add label after actual yield row:
     ```python
     ctk.CTkLabel(self, text="Loss Quantity:").grid(
         row=row, column=0, sticky="e", padx=PADDING_MEDIUM
     )
     self.loss_quantity_label = ctk.CTkLabel(self, text="0")
     self.loss_quantity_label.grid(
         row=row, column=1, sticky="w", padx=PADDING_MEDIUM
     )
     ```
  2. Add method `_update_loss_quantity_display()` to update label
  3. Call this from yield change handlers
- **Parallel?**: Yes, with T016
- **Notes**: Show "0" when no loss, actual number when loss exists

### Subtask T018 - Create expandable loss details frame
- **Purpose**: Optional loss details without cluttering default view
- **File**: `src/ui/forms/record_production_dialog.py`
- **Steps**:
  1. Create collapsible frame after loss quantity display:
     ```python
     self.loss_details_frame = ctk.CTkFrame(self)
     self.loss_details_visible = False
     ```
  2. Add toggle method:
     ```python
     def _toggle_loss_details(self, show: bool):
         if show and not self.loss_details_visible:
             self.loss_details_frame.grid(row=loss_row, column=0, columnspan=2, ...)
             self.loss_details_visible = True
         elif not show and self.loss_details_visible:
             self.loss_details_frame.grid_remove()
             self.loss_details_visible = False
     ```
  3. Initially hide the frame using grid_remove()
- **Parallel?**: Yes
- **Notes**: Use grid/grid_remove for show/hide (not pack)

### Subtask T019 - Add loss category dropdown
- **Purpose**: Categorize losses for trend analysis (FR-008)
- **File**: `src/ui/forms/record_production_dialog.py`
- **Steps**:
  1. Add import: `from src.models import LossCategory`
  2. Inside loss_details_frame, add dropdown:
     ```python
     category_options = [cat.value.replace("_", " ").title() for cat in LossCategory]
     self.loss_category_var = ctk.StringVar(value="Other")
     ctk.CTkLabel(self.loss_details_frame, text="Loss Category:").grid(...)
     self.loss_category_dropdown = ctk.CTkOptionMenu(
         self.loss_details_frame,
         variable=self.loss_category_var,
         values=category_options,
         width=200,
     )
     ```
  3. Add helper to get selected category as enum:
     ```python
     def _get_loss_category(self) -> LossCategory:
         selected = self.loss_category_var.get().lower().replace(" ", "_")
         return LossCategory(selected)
     ```
- **Parallel?**: Yes
- **Notes**: Display as "Burnt", "Wrong Ingredients" etc., map back to enum

### Subtask T020 - Add loss notes textbox
- **Purpose**: Capture optional details about the loss (FR-009)
- **File**: `src/ui/forms/record_production_dialog.py`
- **Steps**:
  1. Inside loss_details_frame, add textbox:
     ```python
     ctk.CTkLabel(self.loss_details_frame, text="Notes:").grid(...)
     self.loss_notes_textbox = ctk.CTkTextbox(
         self.loss_details_frame, height=60, width=300
     )
     self.loss_notes_textbox.grid(...)
     ```
  2. Add helper to get notes:
     ```python
     def _get_loss_notes(self) -> Optional[str]:
         notes = self.loss_notes_textbox.get("1.0", "end-1c").strip()
         return notes if notes else None
     ```
- **Parallel?**: Yes
- **Notes**: Same style as existing notes textbox

### Subtask T021 - Implement auto-expand on loss detection
- **Purpose**: Guide user to loss details when loss exists
- **File**: `src/ui/forms/record_production_dialog.py`
- **Steps**:
  1. In `_update_loss_quantity_display()`, add auto-expand logic:
     ```python
     def _update_loss_quantity_display(self):
         loss_qty = self._calculate_loss_quantity()
         self.loss_quantity_label.configure(text=str(loss_qty))
         # Auto-expand/collapse loss details
         self._toggle_loss_details(loss_qty > 0)
     ```
  2. Ensure this is called whenever batch count or actual yield changes
- **Parallel?**: Yes
- **Notes**: Collapse when loss becomes 0, expand when loss detected

### Subtask T022 - Add cost breakdown display
- **Purpose**: Show financial impact of losses (FR-012, US5)
- **File**: `src/ui/forms/record_production_dialog.py`
- **Steps**:
  1. Add cost breakdown section (visible when loss exists):
     ```python
     self.cost_breakdown_frame = ctk.CTkFrame(self.loss_details_frame)
     self.good_units_cost_label = ctk.CTkLabel(self.cost_breakdown_frame, text="")
     self.lost_units_cost_label = ctk.CTkLabel(self.cost_breakdown_frame, text="")
     self.total_cost_label = ctk.CTkLabel(self.cost_breakdown_frame, text="")
     ```
  2. Add update method:
     ```python
     def _update_cost_breakdown(self, per_unit_cost: Decimal):
         actual = self._get_actual_yield()
         loss = self._calculate_loss_quantity()
         good_cost = actual * per_unit_cost
         lost_cost = loss * per_unit_cost
         total_cost = good_cost + lost_cost
         self.good_units_cost_label.configure(
             text=f"Good units ({actual}): ${good_cost:.2f}"
         )
         self.lost_units_cost_label.configure(
             text=f"Lost units ({loss}): ${lost_cost:.2f}"
         )
         self.total_cost_label.configure(
             text=f"Total batch cost: ${total_cost:.2f}"
         )
     ```
- **Parallel?**: Yes
- **Notes**: Need per_unit_cost from somewhere - may need to calculate or estimate

### Subtask T023 - Update real-time cost calculation
- **Purpose**: Immediate feedback as user adjusts yield
- **File**: `src/ui/forms/record_production_dialog.py`
- **Steps**:
  1. Track per_unit_cost after availability check or estimate from recipe
  2. Call `_update_cost_breakdown()` from `_update_loss_quantity_display()`
  3. Store estimated per_unit_cost as instance variable when availability checked
- **Parallel?**: Yes
- **Notes**: May need to estimate from availability check result or recipe data

### Subtask T024 - Add yield validation in UI
- **Purpose**: Prevent invalid input before service call (FR-003)
- **File**: `src/ui/forms/record_production_dialog.py`
- **Steps**:
  1. Update `_validate()` method to check:
     ```python
     expected = self._calculate_expected_yield(batch_count)
     if actual_yield > expected:
         show_error(
             "Validation Error",
             f"Actual yield ({actual_yield}) cannot exceed expected yield ({expected}).",
             parent=self,
         )
         return False
     ```
  2. Also add visual feedback in real-time (optional): highlight yield entry red if invalid
- **Parallel?**: Yes
- **Notes**: Prevent submission; service has same validation as backup

### Subtask T025 - Update confirmation dialog with loss info
- **Purpose**: User confirms loss details before recording
- **File**: `src/ui/forms/record_production_dialog.py`
- **Steps**:
  1. Update `_on_confirm()` message to include loss info:
     ```python
     loss_qty = self._calculate_loss_quantity()
     loss_info = ""
     if loss_qty > 0:
         category = self._get_loss_category()
         loss_info = f"\nLoss: {loss_qty} units ({category.value})\n"

     message = (
         f"Record {batch_count} batch(es) of {self.finished_unit.display_name}?\n\n"
         f"{event_info}"
         f"Expected yield: {expected}\n"
         f"Actual yield: {actual_yield}\n"
         f"{loss_info}"
         f"This will consume ingredients from inventory.\n"
         f"This action cannot be undone."
     )
     ```
  2. Pass loss_category and loss_notes to service call:
     ```python
     result = self.service_integrator.execute_service_operation(
         # ... existing params ...
         service_function=lambda: batch_production_service.record_batch_production(
             # ... existing params ...
             loss_category=self._get_loss_category() if loss_qty > 0 else None,
             loss_notes=self._get_loss_notes() if loss_qty > 0 else None,
         ),
     )
     ```
- **Parallel?**: Yes
- **Notes**: Only pass loss params when loss exists

## Test Strategy

Manual testing (no automated UI tests required):
1. Open dialog for a finished unit with recipe
2. Enter batch count, verify expected yield updates
3. Enter actual yield < expected, verify:
   - Loss quantity displays correctly
   - Loss details section auto-expands
   - Category dropdown visible with all options
   - Notes textbox visible
   - Cost breakdown shows correct values
4. Enter actual yield > expected, verify error prevents confirm
5. Confirm with loss, verify loss info shown in confirmation
6. Record production with loss, verify success message

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| UI clutter | Expandable section keeps default clean |
| User confusion | Auto-expand guides to loss details |
| Cost estimate inaccuracy | Use actual per_unit_cost when available |
| Performance | Calculations are simple, no performance concern |

## Definition of Done Checklist

- [ ] Loss quantity auto-calculated and displayed
- [ ] Expandable loss details section created
- [ ] Loss details section auto-expands on loss detection
- [ ] Loss category dropdown with all enum values
- [ ] Loss notes textbox for optional details
- [ ] Cost breakdown shows good vs lost with $ amounts
- [ ] Real-time updates as yield changes
- [ ] Validation prevents actual > expected
- [ ] Confirmation dialog includes loss information
- [ ] Service called with loss_category and loss_notes
- [ ] Manual testing passes all scenarios
- [ ] `tasks.md` updated with completion status

## Review Guidance

- Verify UI follows existing dialog patterns
- Check that loss section collapses when loss is 0
- Confirm category dropdown maps correctly to enum
- Test edge cases: 0 actual yield, exact expected yield
- Verify no business logic in UI layer

## Activity Log

- 2025-12-21T16:55:08Z - system - lane=planned - Prompt created.
- 2025-12-21T18:08:58Z – claude – shell_pid=65790 – lane=doing – Starting UI implementation - Record Production Dialog
- 2025-12-21T18:16:24Z – claude – shell_pid=66601 – lane=for_review – T016-T025 complete. Loss tracking UI implemented. Ready for review.
- 2025-12-21T19:10:50Z – claude-reviewer – shell_pid=74330 – lane=done – Code review APPROVED: All Definition of Done items verified. UI correctly delegates to service, auto-expand works, validation correct.
