---
work_package_id: WP06
title: Form Dialog - Materials and Components Sections
lane: "doing"
dependencies:
- WP03
- WP05
base_branch: 088-finished-goods-catalog-ui-WP06-merge-base
base_commit: 5a70a3df344ddb77e8ccb91024698c2a890c767e
created_at: '2026-01-31T04:54:18.803113+00:00'
subtasks: [T035, T036, T037, T038, T039, T040, T041, T042]
shell_pid: "29214"
history:
- date: '2026-01-30'
  action: created
  agent: claude
estimated_lines: 520
priority: P2
---

# WP06: Form Dialog - Materials and Components Sections

## Objective

Add Materials section (MaterialUnits) and Components section (nested FinishedGoods) to the form dialog. All three component types should work together seamlessly.

## Context

- **Feature**: 088-finished-goods-catalog-ui
- **Priority**: P2 (extends MVP with materials and nesting)
- **Dependencies**: WP05 (reuse ComponentSelectionPopup pattern), WP03 (circular reference validation)
- **Estimated Size**: ~520 lines

### Reference Files

- `src/ui/forms/finished_good_form.py` - Form to enhance (from WP05)
- `src/services/material_unit_service.py` - Get MaterialUnits (or equivalent)
- `src/models/material_unit.py` - MaterialUnit model
- `src/services/finished_good_service.py` - Circular reference validation (from WP03)

### Material Display Format

"Unit Name (Product Name)" - e.g., "Gift Box Medium (Kraft Paper Box)"

### Component Types Summary

| Type | Model | Quantity | Notes |
|------|-------|----------|-------|
| Foods | FinishedUnit | Integer | Category filter |
| Materials | MaterialUnit | Decimal | Category + Product filter |
| Components | FinishedGood | Integer | Assembly Type filter |

## Implementation Command

```bash
spec-kitty implement WP06 --base WP05
```

---

## Subtasks

### T035: Create Materials section with Add Material button [P]

**Purpose**: Add the Materials section container to the form.

**Steps**:
1. In `_create_widgets()`, add call after foods section:
   ```python
   self._create_materials_section()
   ```
2. Implement section creation (similar to foods):
   ```python
   def _create_materials_section(self):
       """Create the Materials (MaterialUnits) section."""
       # Section header with Add button
       self.materials_header_frame = ctk.CTkFrame(self.form_scroll)
       self.materials_header_frame.grid(row=9, column=0, columnspan=2, sticky="ew", pady=(15, 5))

       materials_label = ctk.CTkLabel(
           self.materials_header_frame,
           text="Materials",
           font=ctk.CTkFont(size=14, weight="bold")
       )
       materials_label.pack(side="left")

       self.add_material_btn = ctk.CTkButton(
           self.materials_header_frame,
           text="+ Add Material",
           width=120,
           command=self._on_add_material
       )
       self.add_material_btn.pack(side="right")

       # Materials list container
       self.materials_list_frame = ctk.CTkScrollableFrame(
           self.form_scroll,
           height=120
       )
       self.materials_list_frame.grid(row=10, column=0, columnspan=2, sticky="ew", pady=5)
   ```
3. Initialize materials list storage:
   ```python
   # In __init__
   self._materials_components: List[Dict] = []
   ```

**Files**:
- `src/ui/forms/finished_good_form.py` (~35 lines added)

**Validation**:
- [ ] Materials section appears after Foods
- [ ] Add Material button is visible and clickable
- [ ] Section styling matches Foods section

---

### T036: Implement material selection with Material category/subcategory filter [P]

**Purpose**: Allow filtering MaterialUnits by category.

**Steps**:
1. Get material categories:
   ```python
   def _get_material_categories(self) -> List[str]:
       """Get unique categories from MaterialUnits."""
       from src.services import material_unit_service
       # Assuming a service exists; adjust based on actual implementation
       units = material_unit_service.get_all_material_units()
       categories = set()
       for unit in units:
           if unit.product and unit.product.category:
               categories.add(unit.product.category)
       return sorted(list(categories))
   ```
2. Open selection popup:
   ```python
   def _on_add_material(self):
       """Open material selection popup."""
       from src.services import material_unit_service

       units = material_unit_service.get_all_material_units()

       # Build items list: (id, display_name, category)
       items = []
       for u in units:
           product_name = u.product.name if u.product else ""
           display = f"{u.name} ({product_name})" if product_name else u.name
           category = u.product.category if u.product else ""
           items.append((u.id, display, category))

       categories = self._get_material_categories()

       popup = ComponentSelectionPopup(
           self,
           title="Select Material",
           items=items,
           categories=categories,
           on_select=self._show_material_quantity_dialog
       )
   ```

**Files**:
- `src/ui/forms/finished_good_form.py` (~40 lines added)

**Validation**:
- [ ] Material popup shows all materials
- [ ] Category filter works
- [ ] Display shows "Unit Name (Product Name)"

---

### T037: Add type-ahead search for MaterialUnits (search by name and product name) [P]

**Purpose**: Search materials by unit name or product name.

**Steps**:
1. The `ComponentSelectionPopup` from WP05 already supports search
2. Ensure the display_name includes product name for searchability:
   ```python
   # In _on_add_material, the display already includes product name:
   display = f"{u.name} ({product_name})" if product_name else u.name
   # This allows searching for either "Gift Box" or "Kraft Paper"
   ```
3. Search already filters on display_name in `_apply_filters()`:
   ```python
   if search and search not in display_name.lower():
       continue
   ```

**Files**:
- No additional code needed - reuses existing popup functionality

**Validation**:
- [ ] Can search by material unit name
- [ ] Can search by product name
- [ ] Combined search works (partial matches)

---

### T038: Add quantity input with decimal validation (materials support fractional) [P]

**Purpose**: Allow decimal quantities for materials (e.g., 0.5 for half a roll of ribbon).

**Steps**:
1. Create decimal quantity dialog:
   ```python
   def _show_material_quantity_dialog(self, item_id: int, display_name: str):
       """Show quantity input dialog for material (accepts decimals)."""
       dialog = ctk.CTkInputDialog(
           text=f"Quantity for {display_name}:",
           title="Enter Quantity"
       )
       quantity_str = dialog.get_input()

       if quantity_str:
           try:
               quantity = float(quantity_str)
               if quantity <= 0:
                   raise ValueError("Must be positive")
               self._add_material_component(item_id, display_name, quantity)
           except ValueError:
               pass  # Invalid input ignored
   ```
2. Add material component:
   ```python
   def _add_material_component(self, material_id: int, display_name: str, quantity: float):
       """Add a material component and update display."""
       # Check for duplicates
       for comp in self._materials_components:
           if comp["id"] == material_id:
               comp["quantity"] += quantity
               self._refresh_materials_list()
               return

       self._materials_components.append({
           "type": "material_unit",
           "id": material_id,
           "quantity": quantity,
           "display_name": display_name,
           "sort_order": len(self._materials_components)
       })
       self._refresh_materials_list()
   ```

**Files**:
- `src/ui/forms/finished_good_form.py` (~35 lines added)

**Validation**:
- [ ] Accepts decimal values (e.g., 0.5, 1.5)
- [ ] Rejects zero and negative values
- [ ] Quantity displayed correctly

---

### T039: Display added materials list with Product column [P]

**Purpose**: Display materials list similar to foods list.

**Steps**:
1. Implement refresh:
   ```python
   def _refresh_materials_list(self):
       """Refresh the materials list display."""
       for widget in self.materials_list_frame.winfo_children():
           widget.destroy()

       if not self._materials_components:
           empty_label = ctk.CTkLabel(
               self.materials_list_frame,
               text="No materials added yet",
               text_color="gray"
           )
           empty_label.pack(pady=10)
           return

       for i, comp in enumerate(self._materials_components):
           row_frame = ctk.CTkFrame(self.materials_list_frame)
           row_frame.pack(fill="x", pady=2)

           # Name and quantity (format decimal nicely)
           qty_str = f"{comp['quantity']:.1f}" if comp['quantity'] % 1 else str(int(comp['quantity']))
           name_label = ctk.CTkLabel(
               row_frame,
               text=f"{comp['display_name']} x {qty_str}"
           )
           name_label.pack(side="left", padx=5)

           remove_btn = ctk.CTkButton(
               row_frame,
               text="Remove",
               width=70,
               fg_color="red",
               hover_color="darkred",
               command=lambda idx=i: self._remove_material_component(idx)
           )
           remove_btn.pack(side="right", padx=5)

   def _remove_material_component(self, index: int):
       """Remove a material component by index."""
       if 0 <= index < len(self._materials_components):
           del self._materials_components[index]
           for i, comp in enumerate(self._materials_components):
               comp["sort_order"] = i
           self._refresh_materials_list()
   ```

**Files**:
- `src/ui/forms/finished_good_form.py` (~45 lines added)

**Validation**:
- [ ] Materials display in list
- [ ] Decimal quantities show cleanly (1 vs 1.5)
- [ ] Remove button works

---

### T040: Create Components section with Add Component button [P]

**Purpose**: Add the nested FinishedGoods section.

**Steps**:
1. Add section creation:
   ```python
   def _create_components_section(self):
       """Create the Components (nested FinishedGoods) section."""
       self.components_header_frame = ctk.CTkFrame(self.form_scroll)
       self.components_header_frame.grid(row=11, column=0, columnspan=2, sticky="ew", pady=(15, 5))

       components_label = ctk.CTkLabel(
           self.components_header_frame,
           text="Components (Finished Goods)",
           font=ctk.CTkFont(size=14, weight="bold")
       )
       components_label.pack(side="left")

       self.add_component_btn = ctk.CTkButton(
           self.components_header_frame,
           text="+ Add Component",
           width=130,
           command=self._on_add_component
       )
       self.add_component_btn.pack(side="right")

       # Components list container
       self.components_list_frame = ctk.CTkScrollableFrame(
           self.form_scroll,
           height=120
       )
       self.components_list_frame.grid(row=12, column=0, columnspan=2, sticky="ew", pady=5)
   ```
2. Initialize components list:
   ```python
   self._nested_components: List[Dict] = []
   ```

**Files**:
- `src/ui/forms/finished_good_form.py` (~35 lines added)

**Validation**:
- [ ] Components section appears after Materials
- [ ] Add Component button visible
- [ ] Section has scrollable list container

---

### T041: Implement component selection with Assembly Type filter [P]

**Purpose**: Allow filtering FinishedGoods by assembly type.

**Steps**:
1. Get assembly types for filter:
   ```python
   def _get_assembly_type_options(self) -> List[str]:
       return ["Custom Order", "Gift Box", "Variety Pack", "Seasonal Box", "Event Package"]
   ```
2. Open selection popup:
   ```python
   def _on_add_component(self):
       """Open component selection popup."""
       from src.services import finished_good_service

       goods = finished_good_service.get_all_finished_goods()

       # Filter out self if editing
       current_id = self.finished_good.id if self.finished_good else None

       items = []
       for fg in goods:
           if fg.id == current_id:
               continue  # Can't add self
           type_display = self._enum_to_type.get(fg.assembly_type, "Custom Order")
           items.append((fg.id, fg.display_name, type_display))

       popup = ComponentSelectionPopup(
           self,
           title="Select Component",
           items=items,
           categories=self._get_assembly_type_options(),
           on_select=self._on_component_selected
       )
   ```

**Files**:
- `src/ui/forms/finished_good_form.py` (~35 lines added)

**Validation**:
- [ ] Component popup shows other FinishedGoods
- [ ] Self is excluded in edit mode
- [ ] Assembly type filter works

---

### T042: Add circular reference check on selection (filter out invalid choices) [P]

**Purpose**: Prevent selecting FinishedGoods that would create cycles.

**Steps**:
1. Check for circular reference before adding:
   ```python
   def _on_component_selected(self, item_id: int, display_name: str):
       """Handle component selection with circular reference check."""
       # In create mode, no circular check needed (no existing ID)
       if self.finished_good:
           # Check if this would create a cycle
           try:
               from src.services import finished_good_service
               # Build tentative components list
               tentative = [{"type": "finished_good", "id": item_id, "quantity": 1}]
               finished_good_service._validate_no_circular_references(
                   self.finished_good.id, tentative, session=None
               )
           except ValueError as e:
               self._show_circular_reference_error(display_name, str(e))
               return

       # Show quantity dialog
       self._show_component_quantity_dialog(item_id, display_name)

   def _show_circular_reference_error(self, name: str, message: str):
       """Show error when circular reference detected."""
       from tkinter import messagebox
       messagebox.showerror(
           "Invalid Selection",
           f"Cannot add '{name}':\n{message}"
       )
   ```
2. Alternative: Filter out invalid options in popup:
   ```python
   def _on_add_component(self):
       # ... previous code ...

       # Filter out items that would create cycles
       if self.finished_good:
           valid_items = []
           for item_id, display_name, category in items:
               try:
                   tentative = [{"type": "finished_good", "id": item_id, "quantity": 1}]
                   finished_good_service._validate_no_circular_references(
                       self.finished_good.id, tentative, session=None
                   )
                   valid_items.append((item_id, display_name, category))
               except ValueError:
                   pass  # Skip invalid options
           items = valid_items
   ```
3. Add component after validation:
   ```python
   def _show_component_quantity_dialog(self, item_id: int, display_name: str):
       dialog = ctk.CTkInputDialog(
           text=f"Quantity for {display_name}:",
           title="Enter Quantity"
       )
       quantity_str = dialog.get_input()

       if quantity_str:
           try:
               quantity = int(quantity_str)
               if quantity <= 0:
                   raise ValueError("Must be positive")
               self._add_nested_component(item_id, display_name, quantity)
           except ValueError:
               pass

   def _add_nested_component(self, component_id: int, display_name: str, quantity: int):
       for comp in self._nested_components:
           if comp["id"] == component_id:
               comp["quantity"] += quantity
               self._refresh_components_list()
               return

       self._nested_components.append({
           "type": "finished_good",
           "id": component_id,
           "quantity": quantity,
           "display_name": display_name,
           "sort_order": len(self._nested_components)
       })
       self._refresh_components_list()
   ```

**Files**:
- `src/ui/forms/finished_good_form.py` (~60 lines added)

**Validation**:
- [ ] Circular references detected in edit mode
- [ ] Error message shown to user
- [ ] Invalid options filtered from list OR error on select
- [ ] Valid components can be added

---

## Update Save Handler

Combine all component types:

```python
def _on_save(self):
    # ... validation ...

    # Combine all components
    all_components = (
        self._foods_components +
        self._materials_components +
        self._nested_components
    )

    # Re-assign sort_order across all types
    for i, comp in enumerate(all_components):
        comp["sort_order"] = i

    self.result = {
        "display_name": name,
        "assembly_type": self._get_assembly_type(),
        "packaging_instructions": self.packaging_text.get("1.0", "end-1c").strip(),
        "notes": self.notes_text.get("1.0", "end-1c").strip(),
        "components": all_components
    }
    self.destroy()
```

---

## Edit Mode Integration

Load all component types from existing FinishedGood:

```python
def _populate_form(self):
    # ... other fields ...

    if self.finished_good and self.finished_good.components:
        for comp in self.finished_good.components:
            if comp.finished_unit_id is not None:
                self._foods_components.append({...})
            elif comp.material_unit_id is not None:
                mu = comp.material_unit_component
                product_name = mu.product.name if mu.product else ""
                display = f"{mu.name} ({product_name})" if product_name else mu.name
                self._materials_components.append({
                    "type": "material_unit",
                    "id": comp.material_unit_id,
                    "quantity": comp.component_quantity,
                    "display_name": display,
                    "sort_order": comp.sort_order
                })
            elif comp.finished_good_id is not None:
                fg = comp.finished_good_component
                self._nested_components.append({
                    "type": "finished_good",
                    "id": comp.finished_good_id,
                    "quantity": comp.component_quantity,
                    "display_name": fg.display_name,
                    "sort_order": comp.sort_order
                })

        self._refresh_foods_list()
        self._refresh_materials_list()
        self._refresh_components_list()
```

---

## Definition of Done

- [ ] All 8 subtasks completed
- [ ] Materials section with category filter works
- [ ] Materials support decimal quantities
- [ ] Components section with assembly type filter works
- [ ] Circular reference validation prevents invalid nesting
- [ ] All three component types combine in save result
- [ ] Edit mode loads all component types

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Complex material hierarchy | Use Material category + product structure |
| Circular reference missed in UI | Service layer validates again on save (defense in depth) |
| Session issues with validation | Accept session=None for UI-side check, or use separate session |

## Reviewer Guidance

1. Test adding all three component types to one FinishedGood
2. Verify materials accept decimal quantities
3. Test circular reference detection in edit mode
4. Verify self is excluded from component selection
5. Check that edit mode loads all component types correctly
