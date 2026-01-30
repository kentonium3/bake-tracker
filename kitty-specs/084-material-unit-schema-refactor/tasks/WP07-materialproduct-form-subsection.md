---
work_package_id: WP07
title: MaterialProduct Form Sub-Section UI
lane: "doing"
dependencies: [WP03, WP04]
base_branch: 084-material-unit-schema-refactor-WP04
base_commit: 631b3b57cd9633165fb85cf9c6cd26afb95ad74b
created_at: '2026-01-30T18:19:26.373055+00:00'
subtasks:
- T032
- T033
- T034
- T035
- T036
phase: Wave 3 - Export/Import & UI
assignee: ''
agent: "claude-opus"
shell_pid: "45019"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-01-30T17:11:03Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP07 – MaterialProduct Form Sub-Section UI

## Implementation Command

```bash
spec-kitty implement WP07 --base WP04
```

Depends on WP03 (MaterialUnit service) and WP04 (auto-generation).

---

## Objectives & Success Criteria

**Goal**: Add MaterialUnits sub-section to MaterialProduct create/edit form.

**Success Criteria**:
- [ ] MaterialProduct form displays MaterialUnits list with columns: Name, Quantity per Unit
- [ ] "Add Unit" button visible only for linear/area products (not package_count)
- [ ] Auto-generated units appear in list immediately after product creation
- [ ] Edit/Delete functionality works from product form
- [ ] Deletion prevented for units referenced by Compositions
- [ ] UI patterns match Recipe→FinishedUnits sub-form

---

## Context & Constraints

**Reference Documents**:
- Spec: `kitty-specs/084-material-unit-schema-refactor/spec.md` (FR-009 to FR-011)
- Plan: `kitty-specs/084-material-unit-schema-refactor/plan.md`

**UI Pattern Reference**:
- Study: `src/ui/tabs/recipes_tab.py` - Recipe→FinishedUnits sub-form
- Pattern: CTkScrollableFrame with Treeview for listing, Add/Edit buttons, dialog forms

**Key Rules** (from spec):
- "Add Unit" button shown when: package_count is NULL (linear/area products)
- Auto-generated units are fully editable
- Name uniqueness enforced per product (service layer)

---

## Subtasks & Detailed Guidance

### Subtask T032 – Add MaterialUnits List Display

**Purpose**: Show MaterialUnits belonging to the current MaterialProduct.

**Files**: `src/ui/tabs/materials_tab.py`

**Steps**:
1. Locate the MaterialProduct edit/create form in materials_tab.py

2. Add a sub-section frame for MaterialUnits:
   ```python
   # MaterialUnits Sub-Section
   self.units_frame = ctk.CTkFrame(self.form_frame)
   self.units_frame.pack(fill="x", padx=10, pady=(10, 5))

   self.units_label = ctk.CTkLabel(
       self.units_frame,
       text="Material Units",
       font=ctk.CTkFont(size=14, weight="bold")
   )
   self.units_label.pack(anchor="w", padx=5, pady=5)
   ```

3. Add a Treeview to display units:
   ```python
   # Units list
   self.units_tree_frame = ctk.CTkFrame(self.units_frame)
   self.units_tree_frame.pack(fill="x", padx=5, pady=5)

   columns = ("name", "quantity_per_unit")
   self.units_tree = ttk.Treeview(
       self.units_tree_frame,
       columns=columns,
       show="headings",
       height=5,
   )
   self.units_tree.heading("name", text="Name")
   self.units_tree.heading("quantity_per_unit", text="Qty per Unit")
   self.units_tree.column("name", width=200)
   self.units_tree.column("quantity_per_unit", width=100)
   self.units_tree.pack(fill="x")
   ```

4. Add method to refresh the list:
   ```python
   def _refresh_units_list(self):
       """Refresh the MaterialUnits list for current product."""
       # Clear existing items
       for item in self.units_tree.get_children():
           self.units_tree.delete(item)

       if not self.current_product_id:
           return

       # Load units from service
       units = get_material_units_by_product(self.current_product_id)
       for unit in units:
           self.units_tree.insert("", "end", values=(
               unit.name,
               f"{unit.quantity_per_unit:.4f}",
           ), iid=str(unit.id))
   ```

5. Call refresh when product is loaded/saved

**Validation**:
- [ ] Units list displays in product form
- [ ] Columns show Name and Quantity per Unit
- [ ] List refreshes when product changes
- [ ] Empty list shown for new products

---

### Subtask T033 – Add Conditional "Add Unit" Button

**Purpose**: Show "Add Unit" button only for linear/area products.

**Files**: `src/ui/tabs/materials_tab.py`

**Steps**:
1. Add button frame with Add/Edit/Delete buttons:
   ```python
   self.units_button_frame = ctk.CTkFrame(self.units_frame)
   self.units_button_frame.pack(fill="x", padx=5, pady=5)

   self.add_unit_btn = ctk.CTkButton(
       self.units_button_frame,
       text="Add Unit",
       command=self._on_add_unit_click,
       width=100,
   )
   self.add_unit_btn.pack(side="left", padx=5)
   ```

2. Add method to update button visibility:
   ```python
   def _update_add_unit_button_visibility(self):
       """Show Add Unit button only for linear/area products."""
       if not self.current_product_id:
           # New product - hide until saved
           self.add_unit_btn.pack_forget()
           return

       product = get_material_product(self.current_product_id)
       if product:
           # Show Add button only if NOT a package_count product
           # (i.e., linear or area products need manual unit creation)
           if product.package_count is not None:
               # Package count products have auto-generated units
               self.add_unit_btn.pack_forget()
           else:
               # Linear/area products need manual unit creation
               self.add_unit_btn.pack(side="left", padx=5)
   ```

3. Call visibility update when:
   - Product is loaded
   - Product type (package_count/length/area) changes
   - After product save

**Validation**:
- [ ] Button hidden for products with package_count
- [ ] Button visible for products with package_length_m
- [ ] Button visible for products with package_sq_m
- [ ] Button hidden for unsaved new products

---

### Subtask T034 – Add Edit/Delete Functionality

**Purpose**: Allow editing and deleting MaterialUnits from the product form.

**Files**: `src/ui/tabs/materials_tab.py`

**Steps**:
1. Add Edit and Delete buttons:
   ```python
   self.edit_unit_btn = ctk.CTkButton(
       self.units_button_frame,
       text="Edit",
       command=self._on_edit_unit_click,
       width=80,
   )
   self.edit_unit_btn.pack(side="left", padx=5)

   self.delete_unit_btn = ctk.CTkButton(
       self.units_button_frame,
       text="Delete",
       command=self._on_delete_unit_click,
       width=80,
       fg_color="darkred",
   )
   self.delete_unit_btn.pack(side="left", padx=5)
   ```

2. Implement edit handler:
   ```python
   def _on_edit_unit_click(self):
       """Open edit dialog for selected unit."""
       selection = self.units_tree.selection()
       if not selection:
           messagebox.showwarning("No Selection", "Please select a unit to edit.")
           return

       unit_id = int(selection[0])
       unit = get_material_unit(unit_id)
       if unit:
           dialog = MaterialUnitDialog(self, unit=unit, product_id=self.current_product_id)
           if dialog.result:
               self._refresh_units_list()
   ```

3. Implement delete handler with validation:
   ```python
   def _on_delete_unit_click(self):
       """Delete selected unit with confirmation."""
       selection = self.units_tree.selection()
       if not selection:
           messagebox.showwarning("No Selection", "Please select a unit to delete.")
           return

       unit_id = int(selection[0])
       unit = get_material_unit(unit_id)
       if not unit:
           return

       # Confirm deletion
       if not messagebox.askyesno(
           "Confirm Delete",
           f"Delete unit '{unit.name}'?\n\nThis cannot be undone."
       ):
           return

       try:
           delete_material_unit(unit_id)
           self._refresh_units_list()
       except ValidationError as e:
           # Unit is referenced by Compositions
           messagebox.showerror(
               "Cannot Delete",
               str(e.messages[0]) if e.messages else str(e)
           )
   ```

4. Enable/disable buttons based on selection:
   ```python
   def _on_units_tree_select(self, event):
       """Update button states based on selection."""
       selection = self.units_tree.selection()
       state = "normal" if selection else "disabled"
       self.edit_unit_btn.configure(state=state)
       self.delete_unit_btn.configure(state=state)

   # Bind selection event
   self.units_tree.bind("<<TreeviewSelect>>", self._on_units_tree_select)
   ```

**Validation**:
- [ ] Edit button opens dialog with unit data
- [ ] Delete button shows confirmation
- [ ] Delete blocked for referenced units (shows error)
- [ ] Buttons disabled when no selection

---

### Subtask T035 – Add MaterialUnit Create/Edit Dialog

**Purpose**: Dialog form for creating/editing MaterialUnits.

**Files**: `src/ui/dialogs/material_unit_dialog.py` (new file)

**Steps**:
1. Create new dialog file:
   ```python
   import customtkinter as ctk
   from tkinter import messagebox
   from typing import Optional

   from src.models.material_unit import MaterialUnit
   from src.services.material_unit_service import (
       create_material_unit,
       update_material_unit,
       get_material_unit,
   )
   from src.utils.validation import ValidationError


   class MaterialUnitDialog(ctk.CTkToplevel):
       """Dialog for creating/editing a MaterialUnit."""

       def __init__(
           self,
           parent,
           unit: Optional[MaterialUnit] = None,
           product_id: Optional[int] = None,
       ):
           super().__init__(parent)

           self.unit = unit
           self.product_id = product_id or (unit.material_product_id if unit else None)
           self.result = None

           # Window setup
           self.title("Edit Unit" if unit else "Add Unit")
           self.geometry("400x250")
           self.resizable(False, False)
           self.grab_set()  # Modal

           self._create_widgets()
           if unit:
               self._load_unit_data()

       def _create_widgets(self):
           """Create form widgets."""
           # Name field
           ctk.CTkLabel(self, text="Name:").pack(anchor="w", padx=20, pady=(20, 5))
           self.name_entry = ctk.CTkEntry(self, width=300)
           self.name_entry.pack(padx=20)

           # Quantity per unit field
           ctk.CTkLabel(self, text="Quantity per Unit:").pack(anchor="w", padx=20, pady=(10, 5))
           self.qty_entry = ctk.CTkEntry(self, width=300)
           self.qty_entry.pack(padx=20)

           # Description field
           ctk.CTkLabel(self, text="Description (optional):").pack(anchor="w", padx=20, pady=(10, 5))
           self.desc_entry = ctk.CTkEntry(self, width=300)
           self.desc_entry.pack(padx=20)

           # Buttons
           btn_frame = ctk.CTkFrame(self, fg_color="transparent")
           btn_frame.pack(pady=20)

           ctk.CTkButton(btn_frame, text="Save", command=self._on_save).pack(side="left", padx=10)
           ctk.CTkButton(btn_frame, text="Cancel", command=self.destroy).pack(side="left", padx=10)

       def _load_unit_data(self):
           """Load existing unit data into form."""
           if self.unit:
               self.name_entry.insert(0, self.unit.name)
               self.qty_entry.insert(0, str(self.unit.quantity_per_unit))
               if self.unit.description:
                   self.desc_entry.insert(0, self.unit.description)

       def _on_save(self):
           """Save unit data."""
           name = self.name_entry.get().strip()
           qty_str = self.qty_entry.get().strip()
           description = self.desc_entry.get().strip() or None

           # Validate
           if not name:
               messagebox.showerror("Validation Error", "Name is required.")
               return

           try:
               qty = float(qty_str)
               if qty <= 0:
                   raise ValueError("Must be positive")
           except ValueError:
               messagebox.showerror("Validation Error", "Quantity must be a positive number.")
               return

           try:
               if self.unit:
                   # Update existing
                   update_material_unit(
                       self.unit.id,
                       name=name,
                       quantity_per_unit=qty,
                       description=description,
                   )
               else:
                   # Create new
                   create_material_unit(
                       material_product_id=self.product_id,
                       name=name,
                       quantity_per_unit=qty,
                       description=description,
                   )
               self.result = True
               self.destroy()
           except ValidationError as e:
               messagebox.showerror("Validation Error", str(e.messages[0]) if e.messages else str(e))
   ```

2. Add import to materials_tab.py:
   ```python
   from src.ui.dialogs.material_unit_dialog import MaterialUnitDialog
   ```

**Validation**:
- [ ] Dialog opens for create (empty form)
- [ ] Dialog opens for edit (pre-filled form)
- [ ] Validation errors shown in dialog
- [ ] Save returns result flag
- [ ] Cancel closes without saving

---

### Subtask T036 – Integrate with MaterialProduct Save Workflow

**Purpose**: Ensure units refresh after product save and auto-generation.

**Files**: `src/ui/tabs/materials_tab.py`

**Steps**:
1. Update product save handler to refresh units:
   ```python
   def _on_save_product(self):
       """Save the current product."""
       # ... existing save logic ...

       try:
           if self.current_product_id:
               # Update existing product
               update_material_product(self.current_product_id, ...)
           else:
               # Create new product (may auto-generate unit)
               product = create_material_product(...)
               self.current_product_id = product.id

           # Refresh units list (shows auto-generated unit)
           self._refresh_units_list()

           # Update Add button visibility based on product type
           self._update_add_unit_button_visibility()

           messagebox.showinfo("Success", "Product saved successfully.")
       except ValidationError as e:
           messagebox.showerror("Error", str(e))
   ```

2. Ensure Add Unit handler has product_id:
   ```python
   def _on_add_unit_click(self):
       """Open dialog to add new unit."""
       if not self.current_product_id:
           messagebox.showwarning("Save First", "Please save the product before adding units.")
           return

       dialog = MaterialUnitDialog(self, product_id=self.current_product_id)
       if dialog.result:
           self._refresh_units_list()
   ```

3. Update form load to refresh units:
   ```python
   def _load_product_form(self, product_id: int):
       """Load product data into form."""
       self.current_product_id = product_id
       product = get_material_product(product_id)

       # ... load other fields ...

       # Refresh units list
       self._refresh_units_list()

       # Update button visibility
       self._update_add_unit_button_visibility()
   ```

**Validation**:
- [ ] Units list refreshes after product save
- [ ] Auto-generated unit appears immediately
- [ ] Add button visibility updates after save
- [ ] Add Unit blocked until product is saved

---

## Test Strategy

**Manual Testing** (UI tests):
1. Create product with package_count → Verify unit auto-generated, "Add Unit" hidden
2. Create product with package_length_m → Verify no auto-generation, "Add Unit" visible
3. Click "Add Unit" → Verify dialog opens, unit created after save
4. Select unit, click "Edit" → Verify dialog opens with data, changes saved
5. Select unit, click "Delete" → Verify confirmation, unit deleted
6. Try to delete referenced unit → Verify error message shown

**Test Commands**:
```bash
# Run application for manual testing
python src/main.py
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| UI pattern mismatch with Recipe→FinishedUnits | Study existing pattern before implementing |
| Dialog not modal | Use grab_set() for modal behavior |
| List not updating | Call refresh after every CRUD operation |

---

## Definition of Done Checklist

- [ ] MaterialUnits list displays in product form
- [ ] "Add Unit" button conditional on product type
- [ ] Edit/Delete functionality works
- [ ] MaterialUnit dialog created
- [ ] Units refresh after product save
- [ ] Auto-generated units visible immediately
- [ ] Manual testing passes all scenarios

---

## Review Guidance

**Key Checkpoints**:
1. Compare to Recipe→FinishedUnits pattern for consistency
2. Verify "Add Unit" button logic matches FR-010
3. Test delete validation with referenced units
4. Verify form state management (current_product_id)

---

## Activity Log

- 2026-01-30T17:11:03Z – system – lane=planned – Prompt generated via /spec-kitty.tasks
- 2026-01-30T18:30:05Z – unknown – shell_pid=38722 – lane=for_review – Implementation complete: MaterialUnits sub-section added to MaterialProduct form
- 2026-01-30T18:43:00Z – claude-opus – shell_pid=45019 – lane=doing – Started review via workflow command
