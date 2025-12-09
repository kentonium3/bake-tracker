---
work_package_id: "WP06"
subtasks:
  - "T034"
  - "T035"
  - "T036"
  - "T037"
  - "T038"
  - "T039"
  - "T040"
  - "T041"
  - "T042"
title: "UI - Recipe Form"
phase: "Phase 3 - UI Integration"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-09T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP06 – UI - Recipe Form

## Objectives & Success Criteria

- Add "Sub-Recipes" section to recipe form (below Ingredients)
- Add recipe selection dropdown, quantity input, add button
- Display existing sub-recipes with remove capability
- Show cost summary including component costs
- Wire UI to service layer for save/load
- Handle validation errors with user-friendly messages

**Definition of Done**: User can add, view, edit, and remove sub-recipes in the recipe form; changes persist correctly.

## Context & Constraints

**Reference Documents**:
- `kitty-specs/012-nested-recipes/quickstart.md` - UI mockups and workflows
- `src/ui/` - Existing UI patterns to follow
- Constitution Principle V: UI must NOT contain business logic

**Architecture Constraints**:
- All business logic in recipe_service.py (UI only calls services)
- Use CustomTkinter (CTk) widgets
- Follow existing UI patterns in codebase
- Single scrollable form layout (user confirmed)

**UI Layout** (from quickstart.md):
```
┌─────────────────────────────────────────────────────────┐
│ INGREDIENTS                                             │
│ [existing ingredients section]                          │
│                                                         │
│ ═══════════════════════════════════════════════════════ │
│ SUB-RECIPES                                             │
│ ─────────────────────────────────────────────────────── │
│ [Recipe dropdown   ▼] [qty] batches [Add]               │
│                                                         │
│   • Chocolate Cake Layers (1x)      $5.00      [Remove] │
│   • Buttercream Frosting (2x)       $6.00      [Remove] │
│                                                         │
│ ═══════════════════════════════════════════════════════ │
│ COST SUMMARY                                            │
│   Direct ingredients:              $8.00                │
│   Sub-recipes:                    $11.00                │
│   Total:                          $19.00                │
└─────────────────────────────────────────────────────────┘
```

## Subtasks & Detailed Guidance

### Subtask T034 – Add "Sub-Recipes" section label and frame

**Purpose**: Create visual section for sub-recipe management.

**Steps**:
1. Find recipe form file (likely `src/ui/recipe_form.py` or similar)
2. After Ingredients section, add separator and "SUB-RECIPES" label
3. Create container frame for sub-recipe controls

**Files**: `src/ui/recipe_form.py` (or appropriate UI file)

**Code Pattern**:
```python
# After ingredients section

# Sub-Recipes Section
self.subrecipes_separator = ctk.CTkLabel(
    self.form_frame,
    text="═" * 40,
    font=("", 12)
)
self.subrecipes_separator.pack(pady=(20, 5))

self.subrecipes_label = ctk.CTkLabel(
    self.form_frame,
    text="SUB-RECIPES",
    font=("", 14, "bold")
)
self.subrecipes_label.pack(pady=(5, 10))

self.subrecipes_frame = ctk.CTkFrame(self.form_frame)
self.subrecipes_frame.pack(fill="x", padx=10, pady=5)
```

---

### Subtask T035 – Add recipe selection dropdown

**Purpose**: Allow user to select which recipe to add as component.

**Steps**:
1. Create CTkComboBox populated with available recipes
2. Filter out: current recipe (can't add self), recipes that would create cycle
3. Refresh options when form loads and after changes

**Files**: `src/ui/recipe_form.py`

**Code Pattern**:
```python
# In subrecipes_frame
self.recipe_select_frame = ctk.CTkFrame(self.subrecipes_frame)
self.recipe_select_frame.pack(fill="x", pady=5)

# Dropdown
self.subrecipe_dropdown = ctk.CTkComboBox(
    self.recipe_select_frame,
    values=self._get_available_recipes(),
    width=250,
    state="readonly"
)
self.subrecipe_dropdown.pack(side="left", padx=5)

def _get_available_recipes(self):
    """Get recipes that can be added as components."""
    from src.services import recipe_service

    all_recipes = recipe_service.get_all_recipes()

    # Filter out current recipe and existing components
    current_id = getattr(self, 'recipe_id', None)
    existing_component_ids = {c.component_recipe_id for c in self.current_components}

    available = []
    for recipe in all_recipes:
        if recipe.id == current_id:
            continue
        if recipe.id in existing_component_ids:
            continue
        available.append(recipe.name)

    return sorted(available)
```

---

### Subtask T036 – Add quantity input field

**Purpose**: Allow user to specify batch multiplier.

**Steps**:
1. Add CTkEntry for quantity input
2. Default to 1.0
3. Add "batches" label after input

**Files**: `src/ui/recipe_form.py`

**Code Pattern**:
```python
# Quantity input
self.subrecipe_qty_entry = ctk.CTkEntry(
    self.recipe_select_frame,
    width=60,
    placeholder_text="1.0"
)
self.subrecipe_qty_entry.pack(side="left", padx=5)
self.subrecipe_qty_entry.insert(0, "1.0")

# Label
self.qty_label = ctk.CTkLabel(
    self.recipe_select_frame,
    text="batches"
)
self.qty_label.pack(side="left", padx=(0, 10))
```

---

### Subtask T037 – Add "Add Sub-Recipe" button with click handler

**Purpose**: Allow user to add selected recipe as component.

**Steps**:
1. Add "Add" button
2. Implement click handler that:
   - Gets selected recipe and quantity
   - Calls service to add component (or adds to pending list if new recipe)
   - Handles validation errors
   - Refreshes display

**Files**: `src/ui/recipe_form.py`

**Code Pattern**:
```python
# Add button
self.add_subrecipe_btn = ctk.CTkButton(
    self.recipe_select_frame,
    text="Add",
    width=60,
    command=self._on_add_subrecipe
)
self.add_subrecipe_btn.pack(side="left", padx=5)

def _on_add_subrecipe(self):
    """Handle adding a sub-recipe."""
    recipe_name = self.subrecipe_dropdown.get()
    if not recipe_name:
        self._show_error("Please select a recipe")
        return

    try:
        quantity = float(self.subrecipe_qty_entry.get())
    except ValueError:
        self._show_error("Quantity must be a number")
        return

    if quantity <= 0:
        self._show_error("Quantity must be greater than 0")
        return

    # Find recipe by name
    from src.services import recipe_service
    recipes = recipe_service.get_all_recipes(name_search=recipe_name)
    component_recipe = next((r for r in recipes if r.name == recipe_name), None)

    if not component_recipe:
        self._show_error(f"Recipe '{recipe_name}' not found")
        return

    # If editing existing recipe, add via service
    if self.recipe_id:
        try:
            recipe_service.add_recipe_component(
                self.recipe_id,
                component_recipe.id,
                quantity=quantity
            )
        except Exception as e:
            self._show_error(str(e))
            return
    else:
        # For new recipe, add to pending list
        self.pending_components.append({
            "recipe_id": component_recipe.id,
            "recipe_name": recipe_name,
            "quantity": quantity,
        })

    # Refresh display
    self._refresh_subrecipes_display()
    self._update_cost_summary()

    # Reset inputs
    self.subrecipe_dropdown.set("")
    self.subrecipe_qty_entry.delete(0, "end")
    self.subrecipe_qty_entry.insert(0, "1.0")
```

---

### Subtask T038 – Display existing sub-recipes in list format

**Purpose**: Show current sub-recipes with their quantities and costs.

**Steps**:
1. Create scrollable frame for sub-recipe list
2. For each component, show: name, quantity (Nx), cost
3. Refresh when components change

**Files**: `src/ui/recipe_form.py`

**Code Pattern**:
```python
# Components list frame
self.components_list_frame = ctk.CTkScrollableFrame(
    self.subrecipes_frame,
    height=150
)
self.components_list_frame.pack(fill="x", pady=10)

def _refresh_subrecipes_display(self):
    """Refresh the sub-recipes display."""
    # Clear existing
    for widget in self.components_list_frame.winfo_children():
        widget.destroy()

    components = []
    if self.recipe_id:
        from src.services import recipe_service
        components = recipe_service.get_recipe_components(self.recipe_id)
    else:
        components = self.pending_components

    for comp in components:
        self._add_component_row(comp)

    # Update dropdown options
    self.subrecipe_dropdown.configure(values=self._get_available_recipes())

def _add_component_row(self, component):
    """Add a row for a component."""
    row = ctk.CTkFrame(self.components_list_frame)
    row.pack(fill="x", pady=2)

    # Get display info
    if isinstance(component, dict):
        # Pending component
        name = component["recipe_name"]
        qty = component["quantity"]
        cost = 0.0  # Can't calculate until saved
        comp_id = component["recipe_id"]
    else:
        # RecipeComponent model
        name = component.component_recipe.name
        qty = component.quantity
        from src.services import recipe_service
        cost_info = recipe_service.calculate_total_cost_with_components(
            component.component_recipe_id
        )
        cost = cost_info["total_cost"] * qty
        comp_id = component.component_recipe_id

    # Name and quantity
    name_label = ctk.CTkLabel(
        row,
        text=f"• {name} ({qty}x)",
        anchor="w"
    )
    name_label.pack(side="left", fill="x", expand=True, padx=5)

    # Cost
    cost_label = ctk.CTkLabel(
        row,
        text=f"${cost:.2f}",
        width=70
    )
    cost_label.pack(side="left", padx=5)

    # Remove button
    remove_btn = ctk.CTkButton(
        row,
        text="Remove",
        width=60,
        fg_color="red",
        hover_color="darkred",
        command=lambda: self._on_remove_component(comp_id)
    )
    remove_btn.pack(side="right", padx=5)
```

---

### Subtask T039 – Add remove button for each sub-recipe row

**Purpose**: Allow user to remove components.

**Steps**:
1. Add remove button in T038 (already included above)
2. Implement remove handler

**Files**: `src/ui/recipe_form.py`

**Code Pattern**:
```python
def _on_remove_component(self, component_recipe_id):
    """Handle removing a sub-recipe."""
    if self.recipe_id:
        from src.services import recipe_service
        recipe_service.remove_recipe_component(self.recipe_id, component_recipe_id)
    else:
        # Remove from pending
        self.pending_components = [
            c for c in self.pending_components
            if c["recipe_id"] != component_recipe_id
        ]

    # Refresh
    self._refresh_subrecipes_display()
    self._update_cost_summary()
```

---

### Subtask T040 – Add cost summary section

**Purpose**: Show total cost breakdown including components.

**Steps**:
1. Add cost summary section below sub-recipes
2. Show: Direct ingredients cost, Sub-recipes cost, Total, Per unit
3. Update when components change

**Files**: `src/ui/recipe_form.py`

**Code Pattern**:
```python
# Cost summary section
self.cost_separator = ctk.CTkLabel(
    self.form_frame,
    text="═" * 40,
    font=("", 12)
)
self.cost_separator.pack(pady=(20, 5))

self.cost_label = ctk.CTkLabel(
    self.form_frame,
    text="COST SUMMARY",
    font=("", 14, "bold")
)
self.cost_label.pack(pady=(5, 10))

self.cost_frame = ctk.CTkFrame(self.form_frame)
self.cost_frame.pack(fill="x", padx=10, pady=5)

# Labels for costs
self.direct_cost_label = ctk.CTkLabel(self.cost_frame, text="Direct ingredients: $0.00")
self.direct_cost_label.pack(anchor="w", padx=10)

self.component_cost_label = ctk.CTkLabel(self.cost_frame, text="Sub-recipes: $0.00")
self.component_cost_label.pack(anchor="w", padx=10)

self.total_cost_label = ctk.CTkLabel(
    self.cost_frame,
    text="Total: $0.00",
    font=("", 12, "bold")
)
self.total_cost_label.pack(anchor="w", padx=10, pady=(5, 0))

self.per_unit_cost_label = ctk.CTkLabel(self.cost_frame, text="Per unit: $0.00")
self.per_unit_cost_label.pack(anchor="w", padx=10)

def _update_cost_summary(self):
    """Update cost summary display."""
    if not self.recipe_id:
        return

    from src.services import recipe_service
    try:
        cost_info = recipe_service.calculate_total_cost_with_components(self.recipe_id)

        self.direct_cost_label.configure(
            text=f"Direct ingredients: ${cost_info['direct_ingredient_cost']:.2f}"
        )
        self.component_cost_label.configure(
            text=f"Sub-recipes: ${cost_info['total_component_cost']:.2f}"
        )
        self.total_cost_label.configure(
            text=f"Total: ${cost_info['total_cost']:.2f}"
        )
        self.per_unit_cost_label.configure(
            text=f"Per unit: ${cost_info['cost_per_unit']:.2f}"
        )
    except Exception:
        pass  # Silently handle cost calculation errors
```

---

### Subtask T041 – Wire form to service layer for save/load

**Purpose**: Ensure components are saved/loaded with recipe.

**Steps**:
1. On form load, fetch existing components
2. On save, save pending components for new recipes
3. Handle component updates as part of recipe save

**Files**: `src/ui/recipe_form.py`

**Code Pattern**:
```python
def _load_recipe(self, recipe_id):
    """Load recipe data into form."""
    # ... existing load logic ...

    # Load components
    from src.services import recipe_service
    self.current_components = recipe_service.get_recipe_components(recipe_id)
    self._refresh_subrecipes_display()
    self._update_cost_summary()

def _save_recipe(self):
    """Save recipe data."""
    # ... existing save logic ...

    # If new recipe, save pending components
    if not self.recipe_id and self.pending_components:
        from src.services import recipe_service
        for comp in self.pending_components:
            try:
                recipe_service.add_recipe_component(
                    new_recipe.id,  # ID from just-created recipe
                    comp["recipe_id"],
                    quantity=comp["quantity"]
                )
            except Exception as e:
                self._show_warning(f"Failed to add component: {e}")
```

---

### Subtask T042 – Handle validation errors with user-friendly messages

**Purpose**: Display clear error messages when validation fails.

**Steps**:
1. Catch ValidationError from service calls
2. Display appropriate message dialog
3. Map error codes to user-friendly messages

**Files**: `src/ui/recipe_form.py`

**Code Pattern**:
```python
def _show_error(self, message):
    """Show error dialog."""
    from CTkMessagebox import CTkMessagebox
    CTkMessagebox(
        title="Error",
        message=message,
        icon="cancel"
    )

def _show_warning(self, message):
    """Show warning dialog."""
    from CTkMessagebox import CTkMessagebox
    CTkMessagebox(
        title="Warning",
        message=message,
        icon="warning"
    )

def _on_add_subrecipe(self):
    """Handle adding a sub-recipe with validation."""
    # ... selection and validation ...

    try:
        recipe_service.add_recipe_component(...)
    except ValidationError as e:
        error_msg = str(e)

        # User-friendly messages
        if "circular reference" in error_msg.lower():
            self._show_error(
                f"Cannot add '{recipe_name}'.\n\n"
                "This would create a circular reference "
                "(recipes cannot contain each other)."
            )
        elif "depth" in error_msg.lower():
            self._show_error(
                f"Cannot add '{recipe_name}'.\n\n"
                "This would exceed the maximum nesting depth of 3 levels."
            )
        elif "already a component" in error_msg.lower():
            self._show_error(f"'{recipe_name}' is already added to this recipe.")
        else:
            self._show_error(error_msg)
        return
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| UI slow with many recipes | Lazy load dropdown, limit to 100 recipes |
| Cost calculation errors | Silently handle, show $0.00 rather than crash |
| Widget reference errors | Use lambda with closure for remove buttons |

## Definition of Done Checklist

- [ ] Sub-Recipes section visible in recipe form
- [ ] Recipe dropdown shows available recipes
- [ ] Quantity input accepts valid numbers
- [ ] Add button creates component relationship
- [ ] Existing components display correctly
- [ ] Remove button removes components
- [ ] Cost summary shows correct totals
- [ ] Form save persists components
- [ ] Validation errors show clear messages
- [ ] Manual testing confirms all workflows

## Review Guidance

- Test with new recipe (pending components)
- Test with existing recipe (immediate save)
- Verify dropdown filters correctly
- Test all validation error scenarios
- Check cost summary updates in real-time

## Activity Log

- 2025-12-09T00:00:00Z – system – lane=planned – Prompt created.
