---
work_package_id: "WP03"
subtasks:
  - "T011"
  - "T012"
  - "T013"
  - "T014"
  - "T015"
  - "T016"
  - "T017"
title: "Purchase Form - Product Type Selector"
phase: "Phase 1 - Wave 1"
lane: "doing"
assignee: ""
agent: "claude-opus"
shell_pid: "66253"
review_status: ""
reviewed_by: ""
dependencies: ["WP01"]
history:
  - timestamp: "2026-01-18T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP03 - Purchase Form - Product Type Selector

## Important: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Implementation Command

```bash
# Depends on WP01 - branch from WP01 completion
spec-kitty implement WP03 --base WP01
```

---

## Objectives & Success Criteria

Extend AddPurchaseDialog with a product type selector that enables material purchases. Users should be able to:
- Switch between Food and Material purchase types
- See appropriate fields for each type
- Complete material purchases with calculated unit costs

**Success Criteria**:
- [ ] Product type radio buttons (Food/Material) visible at top of form
- [ ] Selecting Material shows material-specific fields, hides food fields
- [ ] Selecting Food shows food fields, hides material fields (existing behavior)
- [ ] Material purchase creates MaterialPurchase and MaterialInventoryItem records
- [ ] Real-time calculation of total units and unit cost
- [ ] Validation prevents incomplete submissions

---

## Context & Constraints

**Feature**: F059 - Materials Purchase Integration & Workflows
**Reference Documents**:
- Spec: `kitty-specs/059-materials-purchase-integration/spec.md` (FR-001 to FR-005)
- Research: `kitty-specs/059-materials-purchase-integration/research.md` (Section 1: Purchase Form Patterns)
- Plan: `kitty-specs/059-materials-purchase-integration/plan.md`

**Key Pattern from Research**:
```python
# Product Type Selection (always visible)
self.product_type_var = ctk.StringVar(value="food")
ctk.CTkRadioButton(form_frame, text="Food", variable=self.product_type_var,
                   value="food", command=self._on_product_type_change)
ctk.CTkRadioButton(form_frame, text="Material", variable=self.product_type_var,
                   value="material", command=self._on_product_type_change)
```

**Existing Form Structure** (from research.md):
```
CTkToplevel (500x600px, modal)
├── title_label
├── form_frame (grid layout)
│   ├── Product dropdown (CTkComboBox)
│   ├── Date entry
│   ├── Quantity entry
│   ├── Price entry
│   ├── Supplier dropdown
│   └── Notes (CTkTextbox)
├── preview_frame (live calculations)
├── error_label (validation feedback)
└── button_frame (Cancel | Save)
```

---

## Subtasks & Detailed Guidance

### Subtask T011 - Add Product Type Radio Buttons

**Purpose**: Add Food/Material selector at top of form (always visible).

**Steps**:
1. Open `src/ui/dialogs/add_purchase_dialog.py`
2. In `_create_form()` or equivalent, add at the TOP of the form (row 0):

```python
# Product Type Selection Frame
self.type_frame = ctk.CTkFrame(self.form_frame, fg_color="transparent")
self.type_frame.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))

ctk.CTkLabel(self.type_frame, text="Product Type:").pack(side="left", padx=(0, 10))

self.product_type_var = ctk.StringVar(value="food")
self.food_radio = ctk.CTkRadioButton(
    self.type_frame,
    text="Food",
    variable=self.product_type_var,
    value="food",
    command=self._on_product_type_change
)
self.food_radio.pack(side="left", padx=5)

self.material_radio = ctk.CTkRadioButton(
    self.type_frame,
    text="Material",
    variable=self.product_type_var,
    value="material",
    command=self._on_product_type_change
)
self.material_radio.pack(side="left", padx=5)
```

3. Shift all existing form elements down by 1 row in their grid positions

**Files**:
- `src/ui/dialogs/add_purchase_dialog.py` (modify)

**Validation**:
- [ ] Radio buttons visible at top of form
- [ ] Default selection is "Food" (existing behavior)
- [ ] Clicking a radio button triggers _on_product_type_change

---

### Subtask T012 - Implement Field Group Show/Hide Logic

**Purpose**: Show appropriate fields based on product type selection.

**Steps**:
1. Create `_on_product_type_change()` method:

```python
def _on_product_type_change(self):
    """Handle product type change - show/hide appropriate fields."""
    product_type = self.product_type_var.get()

    if product_type == "material":
        self._show_material_fields()
        self._hide_food_fields()
        self._clear_food_fields()
    else:
        self._show_food_fields()
        self._hide_material_fields()
        self._clear_material_fields()

    # Reset preview
    self._update_preview()

def _show_material_fields(self):
    """Show material-specific form fields."""
    # Show: material_product_frame, package_qty_frame, etc.
    self.material_product_frame.grid()
    self.package_qty_frame.grid()
    # etc.

def _hide_material_fields(self):
    """Hide material-specific form fields."""
    self.material_product_frame.grid_remove()
    self.package_qty_frame.grid_remove()
    # etc.

def _show_food_fields(self):
    """Show food-specific form fields (existing)."""
    self.product_frame.grid()
    # etc.

def _hide_food_fields(self):
    """Hide food-specific form fields."""
    self.product_frame.grid_remove()
    # etc.
```

2. Use `grid_remove()` to hide (preserves layout) and `grid()` to show

**Files**:
- `src/ui/dialogs/add_purchase_dialog.py` (add methods)

**Validation**:
- [ ] Switching to Material hides food fields
- [ ] Switching to Food hides material fields
- [ ] Fields can be toggled back and forth

---

### Subtask T013 - Create Material-Specific Field Widgets

**Purpose**: Add widgets for MaterialProduct selection and package quantity.

**Steps**:
1. Add material fields (create in `__init__` or `_create_form`, initially hidden):

```python
# Material Product Selection Frame
self.material_product_frame = ctk.CTkFrame(self.form_frame, fg_color="transparent")
# grid() position - will be shown/hidden

ctk.CTkLabel(self.material_product_frame, text="Material Product:").grid(row=0, column=0, sticky="w")

# Load material products
self.material_products = material_catalog_service.list_products(include_hidden=False)
self.material_product_map = {p["name"]: p for p in self.material_products}
material_names = sorted(self.material_product_map.keys())

self.material_product_var = ctk.StringVar()
self.material_product_combo = ctk.CTkComboBox(
    self.material_product_frame,
    variable=self.material_product_var,
    values=material_names if material_names else ["(No products)"],
    width=300,
    command=self._on_material_product_selected
)
self.material_product_combo.grid(row=0, column=1, padx=5)

# Package Quantity Frame
self.package_qty_frame = ctk.CTkFrame(self.form_frame, fg_color="transparent")

ctk.CTkLabel(self.package_qty_frame, text="Packages:").grid(row=0, column=0, sticky="w")
self.packages_var = ctk.StringVar(value="1")
self.packages_entry = ctk.CTkEntry(
    self.package_qty_frame, textvariable=self.packages_var, width=80
)
self.packages_entry.grid(row=0, column=1, padx=5)

ctk.CTkLabel(self.package_qty_frame, text="x").grid(row=0, column=2)

self.package_unit_qty_var = ctk.StringVar()
self.package_unit_qty_entry = ctk.CTkEntry(
    self.package_qty_frame, textvariable=self.package_unit_qty_var, width=80
)
self.package_unit_qty_entry.grid(row=0, column=3, padx=5)

self.package_unit_label = ctk.CTkLabel(self.package_qty_frame, text="units each")
self.package_unit_label.grid(row=0, column=4, padx=5)

# Total Cost for Material
self.material_cost_frame = ctk.CTkFrame(self.form_frame, fg_color="transparent")
ctk.CTkLabel(self.material_cost_frame, text="Total Cost: $").grid(row=0, column=0)
self.material_cost_var = ctk.StringVar()
self.material_cost_entry = ctk.CTkEntry(
    self.material_cost_frame, textvariable=self.material_cost_var, width=100
)
self.material_cost_entry.grid(row=0, column=1)
```

2. Initially hide material frames: `self.material_product_frame.grid_remove()`

**Files**:
- `src/ui/dialogs/add_purchase_dialog.py` (add widgets)

**Validation**:
- [ ] MaterialProduct dropdown populated with products
- [ ] Package quantity fields accept numeric input
- [ ] Total cost field visible for materials

---

### Subtask T014 - Implement Real-Time Calculation

**Purpose**: Calculate and display total units and unit cost as user types.

**Steps**:
1. Add trace handlers for material fields:

```python
# In __init__ or after creating widgets
self.packages_var.trace_add("write", lambda *args: self._update_material_preview())
self.package_unit_qty_var.trace_add("write", lambda *args: self._update_material_preview())
self.material_cost_var.trace_add("write", lambda *args: self._update_material_preview())
```

2. Create `_update_material_preview()`:

```python
def _update_material_preview(self):
    """Update preview with calculated total units and unit cost."""
    try:
        packages = Decimal(self.packages_var.get() or "0")
        units_per_package = Decimal(self.package_unit_qty_var.get() or "0")
        total_cost = Decimal(self.material_cost_var.get() or "0")

        total_units = packages * units_per_package

        if total_units > 0:
            unit_cost = total_cost / total_units

            # Get unit name from selected product
            product = self.material_product_map.get(self.material_product_var.get())
            unit_name = product["package_unit"] if product else "units"

            self.preview_label.configure(
                text=f"Total: {total_units} {unit_name}\nUnit cost: ${unit_cost:.4f}/{unit_name}",
                text_color=("#00AA00" if total_units > 0 and total_cost >= 0 else "orange")
            )
        else:
            self.preview_label.configure(
                text="Enter package quantities...",
                text_color="gray"
            )
    except (InvalidOperation, ValueError):
        self.preview_label.configure(
            text="Invalid input",
            text_color="orange"
        )
```

**Files**:
- `src/ui/dialogs/add_purchase_dialog.py` (add calculation logic)

**Parallel?**: Yes - can be developed alongside T013

**Validation**:
- [ ] Preview updates as user types
- [ ] Total units calculated correctly (packages x units_per_package)
- [ ] Unit cost calculated correctly (total_cost / total_units)
- [ ] Invalid input shows appropriate feedback

---

### Subtask T015 - Wire Up Validation for Material Fields

**Purpose**: Validate material purchase fields before submission.

**Steps**:
1. Extend `_validate()` method for material validation:

```python
def _validate(self) -> Tuple[bool, str]:
    """Validate form fields based on product type."""
    product_type = self.product_type_var.get()

    if product_type == "material":
        return self._validate_material_purchase()
    else:
        return self._validate_food_purchase()  # Existing logic

def _validate_material_purchase(self) -> Tuple[bool, str]:
    """Validate material-specific fields."""
    # Product selected?
    product_name = self.material_product_var.get()
    if not product_name or product_name not in self.material_product_map:
        return (False, "Please select a material product")

    # Packages > 0?
    try:
        packages = Decimal(self.packages_var.get())
        if packages <= 0:
            return (False, "Packages must be greater than 0")
    except (InvalidOperation, ValueError):
        return (False, "Invalid package quantity")

    # Units per package > 0?
    try:
        units = Decimal(self.package_unit_qty_var.get())
        if units <= 0:
            return (False, "Units per package must be greater than 0")
    except (InvalidOperation, ValueError):
        return (False, "Invalid units per package")

    # Cost >= 0?
    try:
        cost = Decimal(self.material_cost_var.get())
        if cost < 0:
            return (False, "Cost cannot be negative")
    except (InvalidOperation, ValueError):
        return (False, "Invalid cost")

    # Date valid? (reuse existing date validation)
    # ...

    return (True, "")
```

**Files**:
- `src/ui/dialogs/add_purchase_dialog.py` (extend validation)

**Validation**:
- [ ] Missing product selection shows error
- [ ] Zero/negative packages shows error
- [ ] Zero/negative units shows error
- [ ] Negative cost shows error
- [ ] All valid inputs pass validation

---

### Subtask T016 - Connect to MaterialPurchaseService on Save

**Purpose**: Save material purchases through the service layer.

**Steps**:
1. Extend `_on_save()` to handle material purchases:

```python
def _on_save(self):
    """Save the purchase based on product type."""
    self._clear_error()

    is_valid, error_msg = self._validate()
    if not is_valid:
        self._show_error(error_msg)
        return

    product_type = self.product_type_var.get()

    try:
        if product_type == "material":
            self._save_material_purchase()
        else:
            self._save_food_purchase()  # Existing logic

        if self.on_save:
            self.on_save()
        self.destroy()
    except Exception as e:
        self._show_error(f"Failed to save: {str(e)}")

def _save_material_purchase(self):
    """Record a material purchase."""
    from src.services.material_purchase_service import record_purchase

    product = self.material_product_map[self.material_product_var.get()]
    packages = Decimal(self.packages_var.get())
    units_per_package = Decimal(self.package_unit_qty_var.get())
    total_cost = Decimal(self.material_cost_var.get())
    purchase_date = datetime.strptime(self.date_var.get(), "%Y-%m-%d").date()

    # Calculate total units in base units
    total_units = packages * units_per_package

    # Get supplier if selected (may need to add supplier dropdown for materials)
    supplier_id = None  # Or get from self.supplier_map if added

    record_purchase(
        product_id=product["id"],
        quantity=packages,  # Number of packages
        total_cost=total_cost,
        purchase_date=purchase_date,
        supplier_id=supplier_id,
        notes=self.notes_text.get("1.0", "end-1c").strip() or None,
    )
```

**Files**:
- `src/ui/dialogs/add_purchase_dialog.py` (add save logic)

**Validation**:
- [ ] Material purchases create MaterialPurchase record
- [ ] Material purchases create MaterialInventoryItem record
- [ ] Purchase data (product, quantity, cost, date) saved correctly

---

### Subtask T017 - Add Field Clearing on Type Switch

**Purpose**: Clear type-specific fields when switching to prevent data leakage.

**Steps**:
1. Add clearing methods:

```python
def _clear_food_fields(self):
    """Clear food-specific field values."""
    self.product_var.set("")
    self.qty_var.set("1")
    self.price_var.set("")
    # Clear any other food-specific fields

def _clear_material_fields(self):
    """Clear material-specific field values."""
    self.material_product_var.set("")
    self.packages_var.set("1")
    self.package_unit_qty_var.set("")
    self.material_cost_var.set("")
```

2. Call these in `_on_product_type_change()` (already added in T012)

**Files**:
- `src/ui/dialogs/add_purchase_dialog.py` (add clearing methods)

**Validation**:
- [ ] Switching from Food to Material clears food fields
- [ ] Switching from Material to Food clears material fields
- [ ] No stale data from previous type selection

---

## Test Strategy

Manual testing scenarios:
1. Open Add Purchase, switch to Material, enter valid data, save
2. Open Add Purchase, enter food data, switch to Material, verify fields cleared
3. Try to save with missing material product - verify error
4. Enter quantities, verify preview calculation is correct

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Form complexity | Clear visual separation; complete hide of irrelevant fields |
| User confusion on switch | Clear fields on type change |
| Grid layout disruption | Use grid_remove() instead of grid_forget() to preserve positions |

---

## Definition of Done Checklist

- [ ] T011: Product type radio buttons added
- [ ] T012: Field show/hide logic implemented
- [ ] T013: Material-specific widgets created
- [ ] T014: Real-time calculation working
- [ ] T015: Validation working for material fields
- [ ] T016: MaterialPurchaseService integration complete
- [ ] T017: Field clearing on type switch working
- [ ] Material purchases create correct database records
- [ ] tasks.md updated with status change

---

## Review Guidance

- Test type switching multiple times to ensure no state leakage
- Verify preview calculations match expected values
- Check that existing food purchase functionality still works
- Ensure form remains usable on smaller screens

---

## Activity Log

- 2026-01-18T00:00:00Z - system - lane=planned - Prompt created.
- 2026-01-19T00:23:32Z – claude-opus – shell_pid=66253 – lane=doing – Started implementation via workflow command
