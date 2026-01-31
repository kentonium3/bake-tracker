---
work_package_id: "WP05"
title: "Form Dialog - Foods Component Section"
lane: "planned"
dependencies: ["WP04"]
subtasks: ["T028", "T029", "T030", "T031", "T032", "T033", "T034"]
priority: "P1"
estimated_lines: 480
history:
  - date: "2026-01-30"
    action: "created"
    agent: "claude"
---

# WP05: Form Dialog - Foods Component Section

## Objective

Implement the Foods section in the form dialog with category filter + search for adding FinishedUnits. Users can add foods to the form, see them in a list, and remove them. Component data is preserved on save.

## Context

- **Feature**: 088-finished-goods-catalog-ui
- **Priority**: P1 (MVP scope - basic creation with foods)
- **Dependencies**: WP04 (form shell exists)
- **Estimated Size**: ~480 lines

### Reference Files

- `src/ui/forms/finished_good_form.py` - Form to enhance (from WP04)
- `src/services/finished_unit_service.py` - Get FinishedUnits
- `src/models/finished_unit.py` - FinishedUnit model

### Component Data Structure

```python
# Stored in form's components list
{
    "type": "finished_unit",
    "id": fu.id,
    "quantity": qty,
    "display_name": fu.display_name,  # For UI display only
    "sort_order": index
}
```

## Implementation Command

```bash
spec-kitty implement WP05 --base WP04
```

---

## Subtasks

### T028: Create Foods section frame with section header and Add Food button

**Purpose**: Add the Foods section container to the form.

**Steps**:
1. In `_create_widgets()`, add call to create foods section:
   ```python
   self._create_foods_section()
   ```
2. Implement section creation:
   ```python
   def _create_foods_section(self):
       """Create the Foods (FinishedUnits) section."""
       # Section header with Add button
       self.foods_header_frame = ctk.CTkFrame(self.form_scroll)
       self.foods_header_frame.grid(row=7, column=0, columnspan=2, sticky="ew", pady=(15, 5))

       foods_label = ctk.CTkLabel(
           self.foods_header_frame,
           text="Foods (Finished Units)",
           font=ctk.CTkFont(size=14, weight="bold")
       )
       foods_label.pack(side="left")

       self.add_food_btn = ctk.CTkButton(
           self.foods_header_frame,
           text="+ Add Food",
           width=100,
           command=self._on_add_food
       )
       self.add_food_btn.pack(side="right")
   ```
3. Initialize foods list storage:
   ```python
   # In __init__
   self._foods_components: List[Dict] = []
   ```

**Files**:
- `src/ui/forms/finished_good_form.py` (~30 lines added)

**Validation**:
- [ ] Foods section header appears after Notes
- [ ] Add Food button is visible and clickable
- [ ] Section styling matches other sections

---

### T029: Create ComponentSelectionPopup for food selection (reusable base class)

**Purpose**: Create a popup dialog for selecting components with filtering.

**Steps**:
1. Create the popup class:
   ```python
   class ComponentSelectionPopup(ctk.CTkToplevel):
       """Popup for selecting a component with filter and search."""

       def __init__(
           self,
           parent,
           title: str,
           items: List[tuple],  # [(id, display_name, category), ...]
           categories: List[str],
           on_select: callable
       ):
           super().__init__(parent)

           self.items = items
           self.categories = categories
           self.on_select = on_select
           self.filtered_items = items.copy()

           self.title(title)
           self.geometry("400x500")
           self.transient(parent)
           self.grab_set()

           self._create_widgets()
   ```
2. Create filter/search controls:
   ```python
   def _create_widgets(self):
       # Filter frame
       filter_frame = ctk.CTkFrame(self)
       filter_frame.pack(fill="x", padx=10, pady=10)

       # Category filter
       ctk.CTkLabel(filter_frame, text="Category:").pack(side="left", padx=5)
       self.category_dropdown = ctk.CTkComboBox(
           filter_frame,
           values=["All"] + self.categories,
           command=self._on_filter_changed
       )
       self.category_dropdown.set("All")
       self.category_dropdown.pack(side="left", padx=5)

       # Search entry
       self.search_entry = ctk.CTkEntry(
           filter_frame,
           placeholder_text="Search..."
       )
       self.search_entry.pack(side="left", fill="x", expand=True, padx=5)
       self.search_entry.bind("<KeyRelease>", self._on_search_changed)

       # Items list
       self.items_frame = ctk.CTkScrollableFrame(self)
       self.items_frame.pack(fill="both", expand=True, padx=10, pady=5)

       self._refresh_items_list()

       # Cancel button
       cancel_btn = ctk.CTkButton(self, text="Cancel", command=self.destroy)
       cancel_btn.pack(pady=10)
   ```

**Files**:
- `src/ui/forms/finished_good_form.py` (~70 lines added)

**Validation**:
- [ ] Popup opens modally
- [ ] Category dropdown populated
- [ ] Search field accepts input
- [ ] Items display in scrollable list

---

### T030: Add category filter dropdown (populated from Recipe categories)

**Purpose**: Filter FinishedUnits by their recipe category.

**Steps**:
1. Load categories from database:
   ```python
   def _get_food_categories(self) -> List[str]:
       """Get unique categories from FinishedUnits."""
       from src.services import finished_unit_service
       units = finished_unit_service.get_all_finished_units()
       categories = set()
       for unit in units:
           if unit.category:
               categories.add(unit.category)
       return sorted(list(categories))
   ```
2. Implement filter logic in popup:
   ```python
   def _on_filter_changed(self, category: str):
       self._apply_filters()

   def _apply_filters(self):
       category = self.category_dropdown.get()
       search = self.search_entry.get().lower().strip()

       self.filtered_items = []
       for item_id, display_name, item_category in self.items:
           # Category filter
           if category != "All" and item_category != category:
               continue
           # Search filter
           if search and search not in display_name.lower():
               continue
           self.filtered_items.append((item_id, display_name, item_category))

       self._refresh_items_list()
   ```

**Files**:
- `src/ui/forms/finished_good_form.py` (~30 lines added)

**Validation**:
- [ ] Category dropdown shows all unique categories
- [ ] Selecting a category filters the list
- [ ] "All" shows all items

---

### T031: Add type-ahead search CTkComboBox for FinishedUnits

**Purpose**: Allow searching for FinishedUnits by name.

**Steps**:
1. Implement search handling:
   ```python
   def _on_search_changed(self, event):
       self._apply_filters()
   ```
2. Highlight matching text in display (optional enhancement):
   ```python
   def _refresh_items_list(self):
       # Clear existing items
       for widget in self.items_frame.winfo_children():
           widget.destroy()

       if not self.filtered_items:
           no_items = ctk.CTkLabel(
               self.items_frame,
               text="No items match your search",
               text_color="gray"
           )
           no_items.pack(pady=20)
           return

       for item_id, display_name, category in self.filtered_items:
           item_frame = ctk.CTkFrame(self.items_frame)
           item_frame.pack(fill="x", pady=2)

           label = ctk.CTkLabel(
               item_frame,
               text=f"{display_name} ({category})" if category else display_name
           )
           label.pack(side="left", padx=5)

           select_btn = ctk.CTkButton(
               item_frame,
               text="Select",
               width=60,
               command=lambda id=item_id, name=display_name: self._select_item(id, name)
           )
           select_btn.pack(side="right", padx=5)
   ```
3. Handle selection:
   ```python
   def _select_item(self, item_id: int, display_name: str):
       self.on_select(item_id, display_name)
       self.destroy()
   ```

**Files**:
- `src/ui/forms/finished_good_form.py` (~45 lines added)

**Validation**:
- [ ] Search filters list as user types
- [ ] Empty results show message
- [ ] Items show name and category

---

### T032: Add quantity input entry with integer validation

**Purpose**: Allow specifying quantity when adding a food.

**Steps**:
1. Modify selection flow to include quantity:
   ```python
   def _on_add_food(self):
       """Open food selection popup."""
       from src.services import finished_unit_service
       units = finished_unit_service.get_all_finished_units()

       # Build items list: (id, display_name, category)
       items = [(u.id, u.display_name, u.category or "") for u in units]
       categories = self._get_food_categories()

       popup = ComponentSelectionPopup(
           self,
           title="Select Food",
           items=items,
           categories=categories,
           on_select=self._show_quantity_dialog
       )
   ```
2. Create quantity dialog:
   ```python
   def _show_quantity_dialog(self, item_id: int, display_name: str):
       """Show quantity input dialog after selecting food."""
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
               self._add_food_component(item_id, display_name, quantity)
           except ValueError:
               # Show error or just ignore invalid input
               pass
   ```

**Files**:
- `src/ui/forms/finished_good_form.py` (~35 lines added)

**Validation**:
- [ ] Quantity dialog appears after selection
- [ ] Only positive integers accepted
- [ ] Invalid input handled gracefully

---

### T033: Implement added foods list display (CTkScrollableFrame with rows) [P]

**Purpose**: Display the list of added food components.

**Steps**:
1. Create foods list container:
   ```python
   def _create_foods_section(self):
       # ... header code from T028 ...

       # Foods list container
       self.foods_list_frame = ctk.CTkScrollableFrame(
           self.form_scroll,
           height=150
       )
       self.foods_list_frame.grid(row=8, column=0, columnspan=2, sticky="ew", pady=5)
   ```
2. Implement add and display:
   ```python
   def _add_food_component(self, food_id: int, display_name: str, quantity: int):
       """Add a food component and update display."""
       # Check for duplicates
       for comp in self._foods_components:
           if comp["id"] == food_id:
               # Update quantity instead of adding duplicate
               comp["quantity"] += quantity
               self._refresh_foods_list()
               return

       # Add new component
       self._foods_components.append({
           "type": "finished_unit",
           "id": food_id,
           "quantity": quantity,
           "display_name": display_name,
           "sort_order": len(self._foods_components)
       })
       self._refresh_foods_list()

   def _refresh_foods_list(self):
       """Refresh the foods list display."""
       # Clear existing
       for widget in self.foods_list_frame.winfo_children():
           widget.destroy()

       if not self._foods_components:
           empty_label = ctk.CTkLabel(
               self.foods_list_frame,
               text="No foods added yet",
               text_color="gray"
           )
           empty_label.pack(pady=10)
           return

       for i, comp in enumerate(self._foods_components):
           row_frame = ctk.CTkFrame(self.foods_list_frame)
           row_frame.pack(fill="x", pady=2)

           # Name and quantity
           name_label = ctk.CTkLabel(
               row_frame,
               text=f"{comp['display_name']} x {comp['quantity']}"
           )
           name_label.pack(side="left", padx=5)

           # Remove button (T034)
           # ...
   ```

**Files**:
- `src/ui/forms/finished_good_form.py` (~55 lines added)

**Validation**:
- [ ] Added foods appear in list
- [ ] Format shows "Name x Quantity"
- [ ] Empty state message shows when no foods
- [ ] Duplicate adds increase quantity

---

### T034: Add Remove button per row with callback [P]

**Purpose**: Allow removing foods from the list.

**Steps**:
1. Add remove button in `_refresh_foods_list()`:
   ```python
   # In the row_frame creation loop
   remove_btn = ctk.CTkButton(
       row_frame,
       text="Remove",
       width=70,
       fg_color="red",
       hover_color="darkred",
       command=lambda idx=i: self._remove_food_component(idx)
   )
   remove_btn.pack(side="right", padx=5)
   ```
2. Implement remove handler:
   ```python
   def _remove_food_component(self, index: int):
       """Remove a food component by index."""
       if 0 <= index < len(self._foods_components):
           del self._foods_components[index]
           # Update sort_order for remaining items
           for i, comp in enumerate(self._foods_components):
               comp["sort_order"] = i
           self._refresh_foods_list()
   ```
3. Update save handler to include foods:
   ```python
   def _on_save(self):
       # ... validation ...

       self.result = {
           "display_name": name,
           "assembly_type": self._get_assembly_type(),
           "packaging_instructions": self.packaging_text.get("1.0", "end-1c").strip(),
           "notes": self.notes_text.get("1.0", "end-1c").strip(),
           "components": self._foods_components.copy()  # Include foods
       }
       self.destroy()
   ```

**Files**:
- `src/ui/forms/finished_good_form.py` (~30 lines added)

**Validation**:
- [ ] Remove button appears on each row
- [ ] Clicking Remove deletes the component
- [ ] sort_order updates after removal
- [ ] Save includes foods in result

---

## Edit Mode Integration

When editing an existing FinishedGood, populate the foods list:

```python
def _populate_form(self):
    # ... other fields ...

    # Populate foods from existing components
    if self.finished_good and self.finished_good.components:
        for comp in self.finished_good.components:
            if comp.finished_unit_id is not None:
                self._foods_components.append({
                    "type": "finished_unit",
                    "id": comp.finished_unit_id,
                    "quantity": comp.component_quantity,
                    "display_name": comp.finished_unit_component.display_name,
                    "sort_order": comp.sort_order
                })
        self._refresh_foods_list()
```

---

## Definition of Done

- [ ] All 7 subtasks completed
- [ ] Foods section added to form
- [ ] Can add foods with category filter + search
- [ ] Can specify quantity for each food
- [ ] Added foods display in list
- [ ] Can remove foods from list
- [ ] Save includes foods in result dict
- [ ] Edit mode populates existing foods

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Large FinishedUnit list | Category filter + search reduces visible options |
| CTkInputDialog limitations | Keep simple; can enhance with custom dialog later |
| Edit mode data loading | Eagerly load relationships or handle lazy loading |

## Reviewer Guidance

1. Test adding multiple foods with different quantities
2. Verify duplicate detection works (adds to quantity)
3. Test remove functionality at various positions
4. Verify edit mode correctly loads existing components
5. Check that result dict has correct format for service layer
