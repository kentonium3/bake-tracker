---
work_package_id: WP07
title: Tab Integration and CRUD Wiring
lane: "doing"
dependencies:
- WP01
- WP02
- WP03
- WP04
- WP05
subtasks: [T043, T044, T045, T046, T047, T048, T049, T050, T051]
history:
- date: '2026-01-30'
  action: created
  agent: claude
estimated_lines: 420
priority: P1
---

# WP07: Tab Integration and CRUD Wiring

## Objective

Wire up all CRUD operations in the tab to complete the user flow. Connect Create, Edit, and Delete buttons to the form dialog and service layer. Implement search and filter functionality.

## Context

- **Feature**: 088-finished-goods-catalog-ui
- **Priority**: P1 (final integration)
- **Dependencies**: WP01 (tab), WP02-03 (service), WP04-06 (form)
- **Estimated Size**: ~420 lines

### Reference Files

- `src/ui/finished_goods_tab.py` - Tab to complete (from WP01)
- `src/ui/forms/finished_good_form.py` - Form dialog (from WP04-06)
- `src/services/finished_good_service.py` - Service layer (from WP02-03)

## Implementation Command

```bash
spec-kitty implement WP07 --base WP06
```

---

## Subtasks

### T043: Wire Create New button to open form dialog (create mode)

**Purpose**: Connect Create New button to form dialog.

**Steps**:
1. Implement `_on_create_new()`:
   ```python
   def _on_create_new(self):
       """Open form dialog in create mode."""
       from src.ui.forms.finished_good_form import FinishedGoodFormDialog

       dialog = FinishedGoodFormDialog(self, finished_good=None)
       self.wait_window(dialog)

       if dialog.result:
           self._handle_create_result(dialog.result)
   ```
2. The form dialog handles its own modal behavior via `grab_set()` and `transient()`

**Files**:
- `src/ui/finished_goods_tab.py` (~15 lines added)

**Validation**:
- [ ] Clicking Create New opens form dialog
- [ ] Dialog is modal (can't click tab behind it)
- [ ] Cancel returns without changes

---

### T044: Wire Edit button and double-click to open form dialog (edit mode)

**Purpose**: Enable editing existing FinishedGoods.

**Steps**:
1. Implement `_on_edit()`:
   ```python
   def _on_edit(self):
       """Open form dialog in edit mode for selected item."""
       if not self._selected_id:
           return

       # Get the FinishedGood from current list
       finished_good = self._get_selected_finished_good()
       if not finished_good:
           self._set_status("Could not load selected item")
           return

       from src.ui.forms.finished_good_form import FinishedGoodFormDialog

       dialog = FinishedGoodFormDialog(self, finished_good=finished_good)
       self.wait_window(dialog)

       if dialog.result:
           self._handle_update_result(finished_good.id, dialog.result)
   ```
2. Implement helper:
   ```python
   def _get_selected_finished_good(self) -> Optional[FinishedGood]:
       """Get FinishedGood object for selected row."""
       for fg in self._current_finished_goods:
           if fg.id == self._selected_id:
               return fg
       return None
   ```
3. Implement double-click handler (from WP01):
   ```python
   def _on_double_click(self, event):
       """Handle double-click on row to edit."""
       if self._selected_id:
           self._on_edit()
   ```

**Files**:
- `src/ui/finished_goods_tab.py` (~30 lines added)

**Validation**:
- [ ] Edit button opens form with existing data
- [ ] Double-click opens form with existing data
- [ ] Cancel returns without changes

---

### T045: Implement form result handling and service layer calls

**Purpose**: Process form results and call service layer.

**Steps**:
1. Implement create handler:
   ```python
   def _handle_create_result(self, result: dict):
       """Handle result from create form."""
       try:
           from src.services import finished_good_service
           from src.models.assembly_type import AssemblyType

           # Convert assembly_type string to enum
           assembly_type = AssemblyType(result["assembly_type"])

           # Create via service
           fg = finished_good_service.create_finished_good(
               display_name=result["display_name"],
               assembly_type=assembly_type,
               packaging_instructions=result.get("packaging_instructions"),
               notes=result.get("notes"),
               components=result.get("components", [])
           )

           self._set_status(f"Created: {fg.display_name}")
           self._refresh_list()

       except Exception as e:
           self._set_status(f"Error creating: {str(e)}")
   ```
2. Implement update handler:
   ```python
   def _handle_update_result(self, finished_good_id: int, result: dict):
       """Handle result from edit form."""
       try:
           from src.services import finished_good_service
           from src.models.assembly_type import AssemblyType

           assembly_type = AssemblyType(result["assembly_type"])

           fg = finished_good_service.update_finished_good(
               finished_good_id=finished_good_id,
               display_name=result["display_name"],
               assembly_type=assembly_type,
               packaging_instructions=result.get("packaging_instructions"),
               notes=result.get("notes"),
               components=result.get("components", [])
           )

           self._set_status(f"Updated: {fg.display_name}")
           self._refresh_list()

       except Exception as e:
           self._set_status(f"Error updating: {str(e)}")
   ```

**Files**:
- `src/ui/finished_goods_tab.py` (~45 lines added)

**Validation**:
- [ ] Create calls service and shows success status
- [ ] Update calls service and shows success status
- [ ] Errors display in status bar
- [ ] List refreshes after operations

---

### T046: Implement list refresh after create/edit operations

**Purpose**: Refresh the treeview after data changes.

**Steps**:
1. Enhance `_refresh_list()`:
   ```python
   def _refresh_list(self):
       """Refresh the finished goods list from database."""
       # Clear selection
       self._selected_id = None
       self._update_button_states()

       # Clear existing items
       for item in self.tree.get_children():
           self.tree.delete(item)

       # Reload from service
       from src.services import finished_good_service
       self._current_finished_goods = finished_good_service.get_all_finished_goods()

       # Apply current filters
       self._apply_filters()
   ```
2. Call `_refresh_list()` at end of create/update handlers (already done in T045)
3. Preserve selection if still valid after refresh:
   ```python
   def _refresh_list(self, preserve_selection: bool = False):
       previous_id = self._selected_id if preserve_selection else None

       # ... refresh logic ...

       # Restore selection if item still exists
       if previous_id:
           for fg in self._current_finished_goods:
               if fg.id == previous_id:
                   self.tree.selection_set(str(previous_id))
                   self._selected_id = previous_id
                   break
   ```

**Files**:
- `src/ui/finished_goods_tab.py` (~20 lines enhanced)

**Validation**:
- [ ] List updates after create
- [ ] List updates after edit
- [ ] Selection cleared by default
- [ ] Selection can be preserved if needed

---

### T047: Wire Delete button with confirmation dialog

**Purpose**: Implement delete with user confirmation.

**Steps**:
1. Implement `_on_delete()`:
   ```python
   def _on_delete(self):
       """Handle delete button click with confirmation."""
       if not self._selected_id:
           return

       finished_good = self._get_selected_finished_good()
       if not finished_good:
           return

       # Confirmation dialog
       from tkinter import messagebox
       confirmed = messagebox.askyesno(
           "Confirm Delete",
           f"Are you sure you want to delete '{finished_good.display_name}'?\n\n"
           "This action cannot be undone."
       )

       if confirmed:
           self._perform_delete(finished_good.id, finished_good.display_name)
   ```

**Files**:
- `src/ui/finished_goods_tab.py` (~20 lines added)

**Validation**:
- [ ] Delete shows confirmation dialog
- [ ] Cancel keeps item in list
- [ ] Confirm proceeds to deletion

---

### T048: Implement delete with error handling (show blocked reason)

**Purpose**: Handle delete errors gracefully.

**Steps**:
1. Implement `_perform_delete()`:
   ```python
   def _perform_delete(self, finished_good_id: int, display_name: str):
       """Perform deletion with error handling."""
       try:
           from src.services import finished_good_service

           result = finished_good_service.delete_finished_good(finished_good_id)

           if result:
               self._set_status(f"Deleted: {display_name}")
               self._refresh_list()
           else:
               self._set_status(f"Could not delete: {display_name}")

       except ValueError as e:
           # Show error dialog for blocked deletions
           from tkinter import messagebox
           messagebox.showerror(
               "Cannot Delete",
               str(e)
           )
           self._set_status("Delete blocked - see error message")

       except Exception as e:
           self._set_status(f"Error deleting: {str(e)}")
   ```

**Files**:
- `src/ui/finished_goods_tab.py` (~25 lines added)

**Validation**:
- [ ] Successful delete shows status message
- [ ] Blocked delete shows error dialog with reason
- [ ] Other errors display in status bar
- [ ] List refreshes after successful delete

---

### T049: Implement search functionality (filter tree by name) [P]

**Purpose**: Enable searching FinishedGoods by name.

**Steps**:
1. Implement search handler (stub from WP01):
   ```python
   def _on_search(self, search_text: str):
       """Handle search input changes."""
       self._current_search = search_text.lower().strip()
       self._apply_filters()
   ```
2. Store search state:
   ```python
   # In __init__
   self._current_search = ""
   self._current_type_filter = "All"
   ```
3. Implement filter application:
   ```python
   def _apply_filters(self):
       """Apply search and type filters to the list."""
       # Clear tree
       for item in self.tree.get_children():
           self.tree.delete(item)

       # Filter items
       filtered = []
       for fg in self._current_finished_goods:
           # Search filter
           if self._current_search:
               if self._current_search not in fg.display_name.lower():
                   continue

           # Type filter
           if self._current_type_filter != "All":
               type_display = self._enum_to_display.get(fg.assembly_type, "")
               if type_display != self._current_type_filter:
                   continue

           filtered.append(fg)

       # Populate tree
       self._populate_tree(filtered)

       # Update status
       total = len(self._current_finished_goods)
       showing = len(filtered)
       if showing < total:
           self._set_status(f"Showing {showing} of {total} finished goods")
       elif total == 0:
           self._set_status("No finished goods defined. Click 'Create New' to add one.")
       else:
           self._clear_status()
   ```

**Files**:
- `src/ui/finished_goods_tab.py` (~40 lines added)

**Validation**:
- [ ] Typing in search filters list
- [ ] Partial matches work
- [ ] Case insensitive
- [ ] Status shows filter count

---

### T050: Implement assembly type filter functionality [P]

**Purpose**: Enable filtering by assembly type.

**Steps**:
1. Implement type filter handler (stub from WP01):
   ```python
   def _on_type_filter_changed(self, selected_type: str):
       """Handle type filter dropdown changes."""
       self._current_type_filter = selected_type
       self._apply_filters()
   ```
2. Add enum to display mapping:
   ```python
   self._enum_to_display = {
       AssemblyType.CUSTOM_ORDER: "Custom Order",
       AssemblyType.GIFT_BOX: "Gift Box",
       AssemblyType.VARIETY_PACK: "Variety Pack",
       AssemblyType.SEASONAL_BOX: "Seasonal Box",
       AssemblyType.EVENT_PACKAGE: "Event Package",
   }
   ```
3. Filter is already applied in `_apply_filters()` (T049)

**Files**:
- `src/ui/finished_goods_tab.py` (~15 lines added)

**Validation**:
- [ ] Dropdown selection filters list
- [ ] "All" shows all items
- [ ] Works combined with search
- [ ] Status updates correctly

---

### T051: Implement row selection state and button enable/disable

**Purpose**: Enable Edit/Delete buttons when a row is selected.

**Steps**:
1. Implement selection handler:
   ```python
   def _on_selection_changed(self, event):
       """Handle tree selection changes."""
       selected = self.tree.selection()
       if selected:
           self._selected_id = int(selected[0])
       else:
           self._selected_id = None
       self._update_button_states()
   ```
2. Implement button state update:
   ```python
   def _update_button_states(self):
       """Update Edit/Delete button enabled states."""
       if self._selected_id:
           self.edit_btn.configure(state="normal")
           self.delete_btn.configure(state="normal")
       else:
           self.edit_btn.configure(state="disabled")
           self.delete_btn.configure(state="disabled")
   ```
3. Initialize selection state:
   ```python
   # In __init__
   self._selected_id: Optional[int] = None
   ```
4. Call `_update_button_states()` after refresh to reset buttons

**Files**:
- `src/ui/finished_goods_tab.py` (~20 lines added)

**Validation**:
- [ ] No selection: Edit/Delete disabled
- [ ] Row selected: Edit/Delete enabled
- [ ] Clicking empty space deselects
- [ ] Selection cleared after refresh

---

## End-to-End Test Scenarios

### Scenario 1: Create New
1. Click "Create New" → Form opens
2. Enter name, select type, add foods/materials
3. Click Save → List refreshes, new item visible
4. Status shows "Created: [name]"

### Scenario 2: Edit Existing
1. Select item in list
2. Click "Edit" or double-click → Form opens with data
3. Modify fields, change components
4. Click Save → List refreshes with changes
5. Status shows "Updated: [name]"

### Scenario 3: Delete
1. Select item in list
2. Click "Delete" → Confirmation dialog
3. Confirm → Item removed from list
4. Status shows "Deleted: [name]"

### Scenario 4: Delete Blocked
1. Select item that is referenced by another
2. Click "Delete" → Confirmation dialog
3. Confirm → Error dialog explains why blocked
4. Item remains in list

### Scenario 5: Search and Filter
1. Type in search → List filters by name
2. Select assembly type → List filters by type
3. Combine search and type filter
4. Status shows "Showing X of Y"

---

## Definition of Done

- [ ] All 9 subtasks completed
- [ ] Full create/edit/delete workflow works
- [ ] Search filters by name
- [ ] Type filter filters by assembly type
- [ ] Selection enables/disables buttons
- [ ] Error messages display correctly
- [ ] End-to-end scenarios pass

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| State sync issues | Refresh list after every operation |
| Service errors not handled | Wrap all service calls in try/except |
| Selection state bugs | Clear selection on refresh, test edge cases |

## Reviewer Guidance

1. Test complete create → edit → delete workflow
2. Verify delete blocking works with referenced items
3. Test search and filter combinations
4. Check button states during all operations
5. Verify status bar messages are helpful
6. Test with empty database state

## Activity Log

- 2026-01-31T05:05:04Z – unknown – lane=doing – CRUD integration already complete from merged WPs
