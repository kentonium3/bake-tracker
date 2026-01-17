---
work_package_id: "WP05"
subtasks:
  - "T016"
  - "T017"
  - "T018"
  - "T019"
  - "T020"
title: "UI Updates"
phase: "Phase 4 - UI Updates"
lane: "done"
assignee: "claude"
agent: "claude"
shell_pid: "N/A"
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-16T22:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP05 – UI Updates 🎯 MVP

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you understand the feedback and begin addressing it, update `review_status: acknowledged`.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

**Objective**: Unify yield editing in the recipe form with 3-field yield type rows; remove legacy yield fields from the form.

**Success Criteria**:
1. Recipe form shows yield type rows with: Description (display_name), Unit (item_unit), Quantity (items_per_batch)
2. Legacy `yield_quantity` and `yield_unit` fields removed from top of form
3. At least one complete yield type required to save
4. Remove button disabled when only one row exists
5. Finished Units tab correctly displays `item_unit` for all records

## Context & Constraints

**Related Documents**:
- Spec: `kitty-specs/056-unified-yield-management/spec.md`
- Plan: `kitty-specs/056-unified-yield-management/plan.md`
- Data Model: `kitty-specs/056-unified-yield-management/data-model.md`
- Research: `kitty-specs/056-unified-yield-management/research.md`

**Architectural Constraints**:
- UI layer must NOT contain business logic (validation in services)
- CustomTkinter framework
- Follow existing patterns in `recipe_form.py`

**Key Design Decision**: UI enforces "at least one yield type" via validation. Service layer is authoritative, but UI provides immediate feedback.

## Subtasks & Detailed Guidance

### Subtask T016 – Add item_unit field to YieldTypeRow widget

**Purpose**: Extend the YieldTypeRow widget to include the item_unit field.

**Steps**:
1. Open `src/ui/forms/recipe_form.py`
2. Locate the `YieldTypeRow` class (around line 390)
3. Update `__init__()` to accept `item_unit` parameter:
   ```python
   def __init__(
       self,
       master,
       finished_unit_id: int = None,
       display_name: str = "",
       items_per_batch: int = None,
       item_unit: str = "",  # NEW
       on_remove=None,
       **kwargs
   ):
       super().__init__(master, **kwargs)
       self.finished_unit_id = finished_unit_id

       # ... existing setup

       # Add Unit entry (between Description and Quantity)
       self.unit_entry = ctk.CTkEntry(
           self,
           placeholder_text="Unit (e.g., cookie, piece)",
           width=150
       )
       self.unit_entry.pack(side="left", padx=(5, 0))
       if item_unit:
           self.unit_entry.insert(0, item_unit)
   ```
4. Update `get_data()` to include item_unit:
   ```python
   def get_data(self) -> dict:
       """Return the data for this yield type row."""
       return {
           "id": self.finished_unit_id,
           "display_name": self.name_entry.get().strip(),
           "items_per_batch": self._parse_quantity(),
           "item_unit": self.unit_entry.get().strip()  # NEW
       }
   ```
5. Reorder the fields for intuitive layout: Description → Unit → Quantity → Remove button

**Files**: `src/ui/forms/recipe_form.py`
**Parallel?**: No (blocking change)
**Notes**: The existing widget has name_entry and quantity_entry; add unit_entry between them.

### Subtask T017 – Remove legacy yield_quantity and yield_unit fields from recipe form

**Purpose**: Eliminate the redundant top-level yield fields from the form layout.

**Steps**:
1. Open `src/ui/forms/recipe_form.py`
2. Locate the "Yield Information" section (search for `yield_quantity_entry` or similar)
3. Remove or comment out:
   - `yield_quantity_entry` (CTkEntry for yield quantity)
   - `yield_unit_combo` (CTkComboBox or CTkEntry for yield unit)
   - Any labels associated with these fields
4. Locate the code that reads these fields on save and remove it
5. Locate the code that populates these fields on load and remove it
6. The "Yield Information" section should now ONLY contain the yield type rows

**Files**: `src/ui/forms/recipe_form.py`
**Parallel?**: No (depends on T016)
**Notes**: Be careful not to remove the yield_description field if it's used for something else. Check usage before removing.

### Subtask T018 – Add validation requiring at least one complete yield type

**Purpose**: Prevent saving recipes without complete yield information.

**Steps**:
1. Open `src/ui/forms/recipe_form.py`
2. Locate the form validation method (likely `_validate()` or `_on_save()`)
3. Add validation logic:
   ```python
   def _validate_yield_types(self) -> list[str]:
       """Validate that at least one complete yield type exists."""
       errors = []

       # Get all yield type data
       yield_types = [row.get_data() for row in self.yield_type_rows]

       # Filter to complete rows (has all required fields)
       complete_rows = [
           yt for yt in yield_types
           if yt.get('display_name') and yt.get('item_unit') and yt.get('items_per_batch')
       ]

       if not complete_rows:
           errors.append("At least one complete yield type is required (Description, Unit, and Quantity)")

       # Check for partial rows (some fields but not all)
       for yt in yield_types:
           has_name = bool(yt.get('display_name'))
           has_unit = bool(yt.get('item_unit'))
           has_qty = bool(yt.get('items_per_batch'))

           if any([has_name, has_unit, has_qty]) and not all([has_name, has_unit, has_qty]):
               errors.append(f"Yield type '{yt.get('display_name') or 'unnamed'}' is incomplete")

       return errors
   ```
4. Call this validation in the save flow:
   ```python
   def _on_save(self):
       errors = self._validate_yield_types()
       if errors:
           self._show_validation_errors(errors)
           return
       # ... proceed with save
   ```

**Files**: `src/ui/forms/recipe_form.py`
**Parallel?**: No (depends on T016)
**Notes**: UI validation is for user feedback; service layer is authoritative.

### Subtask T019 – Disable Remove button when only one row exists

**Purpose**: Prevent users from removing all yield type rows.

**Steps**:
1. Open `src/ui/forms/recipe_form.py`
2. Locate where yield type rows are managed
3. Add method to update Remove button states:
   ```python
   def _update_remove_buttons(self):
       """Enable/disable Remove buttons based on row count."""
       row_count = len(self.yield_type_rows)
       for row in self.yield_type_rows:
           if row_count <= 1:
               row.remove_button.configure(state="disabled")
           else:
               row.remove_button.configure(state="normal")
   ```
4. Call this method after:
   - Adding a row
   - Removing a row
   - Initial form load

**Files**: `src/ui/forms/recipe_form.py`
**Parallel?**: No (depends on T016)
**Notes**: The YieldTypeRow class needs to expose `remove_button` or have a method to set its state.

### Subtask T020 – Verify Finished Units tab displays item_unit correctly

**Purpose**: Confirm the Finished Units tab shows the unit field for all records.

**Steps**:
1. Open `src/ui/finished_units_tab.py` (or `src/ui/widgets/data_table.py`)
2. Locate where the "Yield Info" column is formatted
3. Verify the format includes item_unit:
   ```python
   # Expected format: "12 cookie/batch" for DISCRETE_COUNT
   yield_info = f"{fu.items_per_batch} {fu.item_unit}/batch"
   ```
4. If item_unit is missing from display, add it
5. Test by viewing the Finished Units tab with test data

**Files**: `src/ui/finished_units_tab.py` or `src/ui/widgets/data_table.py`
**Parallel?**: Yes (independent of T016-T019)
**Notes**: Per research.md, the tab already displays item_unit. This is a verification task.

## Test Strategy

**Required Tests**:
1. YieldTypeRow `get_data()` includes item_unit
2. Form validation fails with no yield types
3. Form validation fails with incomplete yield types
4. Form validation passes with one complete yield type
5. Remove button disabled when one row
6. Remove button enabled when multiple rows
7. Legacy yield fields no longer appear in form

**Commands**:
```bash
# Run recipe form tests if they exist
./run-tests.sh src/tests/ui/ -v -k "recipe"

# Manual testing (visual verification)
python src/main.py
# Then: Create new recipe, verify form layout
# Then: Open existing recipe, verify yield types display
```

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| User confusion | Add clear placeholder text and validation messages |
| Data loss on save | Preserve existing FinishedUnits when editing |
| Breaking existing recipes | Service layer validation is soft until fully migrated |

## Definition of Done Checklist

- [ ] T016: YieldTypeRow has item_unit field that returns data correctly
- [ ] T017: Legacy yield_quantity and yield_unit fields removed from form
- [ ] T018: Validation requires at least one complete yield type
- [ ] T019: Remove button disabled when only one row exists
- [ ] T020: Finished Units tab displays item_unit correctly
- [ ] Manual testing verifies form layout and behavior
- [ ] `tasks.md` updated with completion status

## Review Guidance

**Key Checkpoints**:
1. Verify YieldTypeRow layout is intuitive (Description → Unit → Quantity)
2. Verify validation messages are clear and helpful
3. Verify Remove button state updates correctly
4. Verify existing FinishedUnit data loads correctly into form
5. Verify form submission creates/updates FinishedUnits correctly

## Activity Log

- 2026-01-16T22:00:00Z – system – lane=planned – Prompt created.
- 2026-01-17T03:44:45Z – claude – lane=doing – Starting UI updates for unified yield management
- 2026-01-17T03:57:03Z – claude – lane=for_review – All subtasks complete: T016-T020. YieldTypeRow updated with item_unit, legacy yield fields removed, validation updated, remove button logic added.
- 2026-01-17T18:01:19Z – claude – lane=doing – Starting review
- 2026-01-17T18:02:09Z – claude – lane=done – Review passed: YieldTypeRow has 3 fields (name/unit/qty). Legacy fields removed. Validation requires complete rows. Remove button disabled with one row. item_unit persisted in both tabs (Cursor fix verified).
