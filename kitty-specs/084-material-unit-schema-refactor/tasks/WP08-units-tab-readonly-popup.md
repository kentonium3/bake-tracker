---
work_package_id: WP08
title: Units Tab Read-Only + Detail Popup
lane: "for_review"
dependencies: [WP03]
base_branch: 084-material-unit-schema-refactor-WP03
base_commit: 8175cc9090e816bdaae4a24c51e036817c6199a0
created_at: '2026-01-30T18:30:25.245474+00:00'
subtasks:
- T037
- T038
- T039
- T040
phase: Wave 3 - Export/Import & UI
assignee: ''
agent: ''
shell_pid: "41099"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-01-30T17:11:03Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP08 – Units Tab Read-Only + Detail Popup

## Implementation Command

```bash
spec-kitty implement WP08 --base WP03
```

Depends on WP03 (MaterialUnit service for queries with product info).

---

## Objectives & Success Criteria

**Goal**: Update Materials→Units tab to read-only list with detail popup.

**Success Criteria**:
- [ ] Units tab has NO "Add Unit" button (read-only view)
- [ ] Units tab displays columns: Name, Material, Product, Quantity per Unit
- [ ] Clicking a row opens popup showing parent MaterialProduct details
- [ ] Popup is informational only (not edit form)
- [ ] Tab serves as reference overview for all units

---

## Context & Constraints

**Reference Documents**:
- Spec: `kitty-specs/084-material-unit-schema-refactor/spec.md` (FR-012 to FR-014)
- Plan: `kitty-specs/084-material-unit-schema-refactor/plan.md`

**Planning Decision**:
- Changed from accordion expansion to modal/popup (simpler, avoids new UI component)
- Popup shows MaterialProduct details inline (read-only)

**Key Changes**:
- Remove "Add Unit" button from tab
- Add "Product" column to show parent product name
- Add click handler to show popup

---

## Subtasks & Detailed Guidance

### Subtask T037 – Update Units Tab to Read-Only

**Purpose**: Remove creation functionality from Units tab.

**Files**: `src/ui/tabs/materials_tab.py`

**Steps**:
1. Locate the Units sub-tab in materials_tab.py (may be a separate tab or section)

2. Remove or hide the "Add Unit" button:
   ```python
   # Find and remove/comment out:
   # self.add_unit_btn = ctk.CTkButton(
   #     self.units_toolbar,
   #     text="Add Unit",
   #     command=self._on_add_unit_click,
   # )
   # self.add_unit_btn.pack(side="left", padx=5)
   ```

3. Remove the Add Unit click handler if no longer needed:
   ```python
   # Remove or keep for reference (may be used in product form)
   # def _on_add_unit_click(self):
   #     ...
   ```

4. Optionally add a label explaining the read-only nature:
   ```python
   self.units_info_label = ctk.CTkLabel(
       self.units_toolbar,
       text="View all units. To add units, edit the MaterialProduct.",
       font=ctk.CTkFont(size=11, slant="italic"),
       text_color="gray",
   )
   self.units_info_label.pack(side="left", padx=10)
   ```

5. Remove Edit/Delete buttons if present (creation/editing now on product form)

**Validation**:
- [ ] No "Add Unit" button visible in Units tab
- [ ] No "Edit" or "Delete" buttons visible
- [ ] Optional: Info label explains where to manage units
- [ ] List still displays and updates correctly

---

### Subtask T038 – Update Units Tab Columns

**Purpose**: Add Material and Product columns for context.

**Files**: `src/ui/tabs/materials_tab.py`

**Steps**:
1. Locate the Units Treeview configuration:
   ```python
   # Find existing columns
   columns = ("name", "quantity_per_unit")
   ```

2. Update columns to include Material and Product:
   ```python
   columns = ("name", "material", "product", "quantity_per_unit")
   self.units_tree = ttk.Treeview(
       self.units_frame,
       columns=columns,
       show="headings",
       height=15,  # Larger for overview
   )
   self.units_tree.heading("name", text="Name")
   self.units_tree.heading("material", text="Material")
   self.units_tree.heading("product", text="Product")
   self.units_tree.heading("quantity_per_unit", text="Qty per Unit")

   self.units_tree.column("name", width=150)
   self.units_tree.column("material", width=150)
   self.units_tree.column("product", width=180)
   self.units_tree.column("quantity_per_unit", width=100)
   self.units_tree.pack(fill="both", expand=True)
   ```

3. Update the data loading to include Material and Product:
   ```python
   def _load_all_units(self):
       """Load all MaterialUnits with parent info."""
       # Clear existing items
       for item in self.units_tree.get_children():
           self.units_tree.delete(item)

       # Query all units with eager loading
       units = get_all_material_units_with_context()  # New service method
       for unit in units:
           material_name = ""
           product_name = ""
           if unit.material_product:
               product_name = unit.material_product.name
               if unit.material_product.material:
                   material_name = unit.material_product.material.name

           self.units_tree.insert("", "end", values=(
               unit.name,
               material_name,
               product_name,
               f"{unit.quantity_per_unit:.4f}",
           ), iid=str(unit.id))
   ```

4. Add service method if needed:
   ```python
   # In material_unit_service.py
   def get_all_material_units_with_context(
       session: Optional[Session] = None,
   ) -> List[MaterialUnit]:
       """Get all MaterialUnits with MaterialProduct and Material loaded."""
       def _impl(sess: Session) -> List[MaterialUnit]:
           return sess.query(MaterialUnit).options(
               joinedload(MaterialUnit.material_product).joinedload(MaterialProduct.material)
           ).all()
       ...
   ```

**Validation**:
- [ ] Columns show Name, Material, Product, Qty per Unit
- [ ] Material column shows parent Material name
- [ ] Product column shows parent MaterialProduct name
- [ ] Data loads correctly with joins

---

### Subtask T039 – Create MaterialProduct Detail Popup Dialog

**Purpose**: Read-only popup showing MaterialProduct details.

**Files**: `src/ui/dialogs/material_product_popup.py` (new file)

**Steps**:
1. Create new popup dialog file:
   ```python
   import customtkinter as ctk
   from typing import Optional

   from src.models.material_product import MaterialProduct
   from src.services.material_product_service import get_material_product


   class MaterialProductPopup(ctk.CTkToplevel):
       """Read-only popup showing MaterialProduct details."""

       def __init__(self, parent, product_id: int):
           super().__init__(parent)

           self.product = get_material_product(product_id)
           if not self.product:
               self.destroy()
               return

           # Window setup
           self.title(f"Product: {self.product.name}")
           self.geometry("450x400")
           self.resizable(False, False)

           self._create_widgets()

       def _create_widgets(self):
           """Create read-only display widgets."""
           # Header
           header = ctk.CTkLabel(
               self,
               text=self.product.name,
               font=ctk.CTkFont(size=18, weight="bold"),
           )
           header.pack(pady=(20, 10))

           # Details frame
           details_frame = ctk.CTkFrame(self)
           details_frame.pack(fill="x", padx=20, pady=10)

           # Material
           self._add_field(details_frame, "Material:",
               self.product.material.name if self.product.material else "N/A")

           # Brand
           self._add_field(details_frame, "Brand:",
               self.product.brand or "N/A")

           # Package info
           if self.product.package_count:
               self._add_field(details_frame, "Package Count:",
                   str(self.product.package_count))
           if self.product.package_length_m:
               self._add_field(details_frame, "Package Length:",
                   f"{self.product.package_length_m} m")
           if self.product.package_sq_m:
               self._add_field(details_frame, "Package Area:",
                   f"{self.product.package_sq_m} sq m")

           # Supplier
           self._add_field(details_frame, "Supplier:",
               self.product.supplier.name if self.product.supplier else "N/A")

           # SKU
           if self.product.sku:
               self._add_field(details_frame, "SKU:", self.product.sku)

           # Units section
           units_label = ctk.CTkLabel(
               self,
               text="Material Units",
               font=ctk.CTkFont(size=14, weight="bold"),
           )
           units_label.pack(anchor="w", padx=25, pady=(15, 5))

           # List units
           units_frame = ctk.CTkScrollableFrame(self, height=100)
           units_frame.pack(fill="x", padx=20, pady=5)

           if self.product.material_units:
               for unit in self.product.material_units:
                   unit_text = f"• {unit.name} ({unit.quantity_per_unit:.4f})"
                   ctk.CTkLabel(units_frame, text=unit_text).pack(anchor="w", padx=5)
           else:
               ctk.CTkLabel(units_frame, text="No units defined",
                   text_color="gray").pack(anchor="w", padx=5)

           # Close button
           ctk.CTkButton(
               self,
               text="Close",
               command=self.destroy,
               width=100,
           ).pack(pady=20)

       def _add_field(self, parent, label: str, value: str):
           """Add a label-value pair."""
           frame = ctk.CTkFrame(parent, fg_color="transparent")
           frame.pack(fill="x", pady=2)
           ctk.CTkLabel(frame, text=label, width=120, anchor="e").pack(side="left", padx=5)
           ctk.CTkLabel(frame, text=value, anchor="w").pack(side="left", padx=5)
   ```

2. Add to dialogs __init__.py if needed:
   ```python
   from src.ui.dialogs.material_product_popup import MaterialProductPopup
   ```

**Validation**:
- [ ] Popup displays product name as title
- [ ] Shows Material, Brand, Package info
- [ ] Shows Supplier and SKU if present
- [ ] Lists MaterialUnits belonging to product
- [ ] Close button works

---

### Subtask T040 – Add Row Click Handler to Show Popup

**Purpose**: Open popup when user clicks a row in Units tab.

**Files**: `src/ui/tabs/materials_tab.py`

**Steps**:
1. Import the popup dialog:
   ```python
   from src.ui.dialogs.material_product_popup import MaterialProductPopup
   ```

2. Add double-click handler for the Units Treeview:
   ```python
   def _on_unit_row_double_click(self, event):
       """Show MaterialProduct popup when unit row is double-clicked."""
       selection = self.units_tree.selection()
       if not selection:
           return

       unit_id = int(selection[0])
       unit = get_material_unit(unit_id)
       if unit and unit.material_product_id:
           MaterialProductPopup(self, product_id=unit.material_product_id)

   # Bind double-click event
   self.units_tree.bind("<Double-1>", self._on_unit_row_double_click)
   ```

3. Alternative: Add single-click handler with small delay (avoids accidental opens):
   ```python
   def _on_unit_row_click(self, event):
       """Show MaterialProduct popup when unit row is clicked."""
       # Use after() to avoid triggering on selection changes
       self.after(100, self._show_unit_popup)

   def _show_unit_popup(self):
       """Actually show the popup if selection still exists."""
       selection = self.units_tree.selection()
       if not selection:
           return

       unit_id = int(selection[0])
       unit = get_material_unit(unit_id)
       if unit and unit.material_product_id:
           MaterialProductPopup(self, product_id=unit.material_product_id)

   # Bind click event
   self.units_tree.bind("<<TreeviewSelect>>", self._on_unit_row_click)
   ```

4. Add visual hint that rows are clickable:
   ```python
   # Add tooltip or label
   self.click_hint = ctk.CTkLabel(
       self.units_toolbar,
       text="Double-click a row to view product details",
       font=ctk.CTkFont(size=11),
       text_color="gray",
   )
   self.click_hint.pack(side="right", padx=10)
   ```

**Validation**:
- [ ] Double-clicking row opens popup
- [ ] Popup shows correct product for clicked unit
- [ ] Visual hint indicates rows are clickable
- [ ] Multiple clicks don't open multiple popups

---

## Test Strategy

**Manual Testing** (UI tests):
1. Navigate to Materials → Units tab
2. Verify "Add Unit" button is NOT present
3. Verify columns show Name, Material, Product, Qty per Unit
4. Double-click a row → Verify popup opens with correct product
5. Verify popup shows product details and units
6. Click Close → Verify popup closes

**Test Commands**:
```bash
# Run application for manual testing
python src/main.py
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Users expect to edit from Units tab | Info label explains where to manage units |
| Popup not loading product | Eager load with joinedload in query |
| Double-click feels slow | Consider single-click with delay |

---

## Definition of Done Checklist

- [ ] "Add Unit" button removed from Units tab
- [ ] Columns updated: Name, Material, Product, Qty per Unit
- [ ] MaterialProductPopup dialog created
- [ ] Row click opens popup with product details
- [ ] Visual hint for clickable rows
- [ ] Manual testing passes all scenarios

---

## Review Guidance

**Key Checkpoints**:
1. Verify no CRUD buttons remain in Units tab
2. Verify all columns display correct data
3. Test popup with products that have units and without
4. Verify popup is read-only (no edit functionality)

---

## Activity Log

- 2026-01-30T17:11:03Z – system – lane=planned – Prompt generated via /spec-kitty.tasks
- 2026-01-30T18:34:00Z – unknown – shell_pid=41099 – lane=for_review – Implementation complete: Units tab now read-only with product popup
