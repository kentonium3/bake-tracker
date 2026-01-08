---
work_package_id: WP08
title: Inline Product Creation
lane: done
history:
- timestamp: '2025-12-24T23:15:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
agent: claude
assignee: claude
phase: Phase 3 - Advanced Features
review_status: ''
reviewed_by: ''
shell_pid: '33920'
subtasks:
- T048
- T049
- T050
- T051
- T052
- T053
- T054
- T055
- T056
- T057
- T058
- T059
---

# Work Package Prompt: WP08 – Inline Product Creation

## Objectives & Success Criteria

**Goal**: Add collapsible accordion form for creating new products without leaving the dialog.

**Success Criteria**:
- [ ] [+ New] button expands inline form
- [ ] Form pre-fills ingredient (read-only), supplier (from session), unit (from defaults)
- [ ] Create button adds product and selects it in dropdown
- [ ] Cancel button collapses form without changes
- [ ] Zero-products case shows prominent create button
- [ ] Error handling keeps form expanded
- [ ] Integration tests pass

## Context & Constraints

**References**:
- Spec: `kitty-specs/029-streamlined-inventory-entry/spec.md` (User Story 4 - Inline Product Creation)
- Design: `docs/design/F029_streamlined_inventory_entry.md` (Inline Product Creation section)

**Constraints**:
- Depends on WP02 (category defaults for unit pre-fill)
- Depends on WP06 (type-ahead integration for dropdown updates)
- Depends on WP07 (session memory for supplier pre-fill)
- Form expands within dialog (no separate modal)
- Main product dropdown disabled while form expanded

## Subtasks & Detailed Guidance

### Subtask T048 – Create inline creation frame

**Purpose**: Container for product creation form.

**Steps**:
1. Create CTkFrame for inline form
2. Add border to visually distinguish
3. Initially not packed/gridded (hidden)

**Code**:
```python
# In dialog __init__:
self.inline_create_frame = ctk.CTkFrame(
    self,
    border_width=1,
    corner_radius=5
)
# Do NOT grid initially - hidden until expanded
```

### Subtask T049 – Implement accordion toggle

**Purpose**: Expand/collapse behavior.

**Steps**:
1. Implement `_toggle_inline_create()` method
2. Toggle visibility with grid/grid_forget
3. Disable/enable product dropdown based on state

**Code**:
```python
def _toggle_inline_create(self):
    """Toggle inline product creation form (accordion)."""
    if self.inline_create_expanded:
        # Collapse
        self.inline_create_frame.grid_forget()
        self.inline_create_expanded = False
        self.product_combo.configure(state="normal")
    else:
        # Expand
        self.inline_create_frame.grid(
            row=3, column=0, columnspan=2,
            sticky="ew", padx=10, pady=5
        )
        self.inline_create_expanded = True
        self.product_combo.configure(state="disabled")
        self._prefill_inline_form()
        self.inline_name_entry.focus_set()
```

### Subtask T050 – Pre-fill ingredient (read-only)

**Purpose**: Show current ingredient selection.

**Steps**:
1. Add CTkLabel for ingredient display
2. Set text from selected ingredient
3. Gray text color to indicate read-only

**Code**:
```python
# In form setup:
self.inline_ingredient_label = ctk.CTkLabel(
    form_frame,
    text="",
    text_color="gray"
)

# In _prefill_inline_form:
if self.selected_ingredient:
    self.inline_ingredient_label.configure(
        text=self.selected_ingredient.display_name
    )
```

### Subtask T051 – Pre-fill supplier from session

**Purpose**: Default to last-used supplier.

**Steps**:
1. Add CTkComboBox for preferred supplier
2. Pre-select from session state
3. Add ⭐ prefix if from session

**Code**:
```python
# In _prefill_inline_form:
last_supplier_id = self.session_state.get_last_supplier_id()
if last_supplier_id:
    for display_name, supplier in self.supplier_map.items():
        if supplier.id == last_supplier_id:
            self.inline_supplier_combo.set(f"⭐ {display_name}")
            break
```

### Subtask T052 – Pre-fill unit from defaults

**Purpose**: Smart default based on ingredient category.

**Steps**:
1. Import get_default_unit_for_ingredient from category_defaults
2. Set unit dropdown to default value

**Code**:
```python
from src.utils.category_defaults import get_default_unit_for_ingredient

# In _prefill_inline_form:
if self.selected_ingredient:
    default_unit = get_default_unit_for_ingredient(self.selected_ingredient)
    self.inline_unit_combo.set(default_unit)
```

### Subtask T053 – Add form fields

**Purpose**: Input fields for new product.

**Steps**:
1. Add Product Name entry (required)
2. Add Package Unit dropdown (required)
3. Add Package Quantity entry (required)
4. Add Preferred Supplier dropdown (optional)

**Code**:
```python
def _setup_inline_create_form(self):
    """Setup inline product creation form."""
    form_frame = ctk.CTkFrame(self.inline_create_frame)
    form_frame.pack(fill="both", expand=True, padx=10, pady=5)

    # Ingredient (read-only)
    ctk.CTkLabel(form_frame, text="Ingredient:").grid(row=0, column=0, sticky="w")
    self.inline_ingredient_label = ctk.CTkLabel(form_frame, text="", text_color="gray")
    self.inline_ingredient_label.grid(row=0, column=1, sticky="w")

    # Product Name (required)
    ctk.CTkLabel(form_frame, text="Product Name:*").grid(row=1, column=0, sticky="w")
    self.inline_name_entry = ctk.CTkEntry(form_frame)
    self.inline_name_entry.grid(row=1, column=1, sticky="ew")

    # Package Unit + Quantity
    ctk.CTkLabel(form_frame, text="Package Unit:*").grid(row=2, column=0, sticky="w")
    unit_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
    unit_frame.grid(row=2, column=1, sticky="ew")

    self.inline_unit_combo = ctk.CTkComboBox(
        unit_frame,
        values=["lb", "oz", "kg", "g", "fl oz", "ml", "L", "count"],
        state="readonly"
    )
    self.inline_unit_combo.pack(side="left", padx=(0, 10))

    ctk.CTkLabel(unit_frame, text="Qty:").pack(side="left")
    self.inline_qty_entry = ctk.CTkEntry(unit_frame, width=80)
    self.inline_qty_entry.pack(side="left", padx=(5, 0))

    # Preferred Supplier
    ctk.CTkLabel(form_frame, text="Preferred Supplier:").grid(row=3, column=0, sticky="w")
    self.inline_supplier_combo = ctk.CTkComboBox(
        form_frame,
        values=[],  # Populated from main supplier list
        state="readonly"
    )
    self.inline_supplier_combo.grid(row=3, column=1, sticky="ew")

    # Buttons
    btn_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
    btn_frame.grid(row=4, column=0, columnspan=2, pady=10)

    ctk.CTkButton(btn_frame, text="Cancel", command=self._cancel_inline_create).pack(side="left", padx=5)
    ctk.CTkButton(btn_frame, text="Create Product", command=self._create_product_inline).pack(side="left", padx=5)
```

### Subtask T054 – Implement Create button

**Purpose**: Create product and add to dropdown.

**Steps**:
1. Validate required fields
2. Call product service to create
3. On success: update dropdown, select new product, collapse
4. On error: show message, keep expanded

**Code**:
```python
def _create_product_inline(self):
    """Create product from inline form."""
    # Validate
    name = self.inline_name_entry.get().strip()
    if not name:
        self._show_error("Product name is required")
        return

    unit = self.inline_unit_combo.get()
    if not unit:
        self._show_error("Package unit is required")
        return

    try:
        qty = Decimal(self.inline_qty_entry.get())
        if qty <= 0:
            raise ValueError()
    except:
        self._show_error("Package quantity must be a positive number")
        return

    # Get preferred supplier
    supplier_display = self.inline_supplier_combo.get().replace("⭐ ", "").strip()
    preferred_supplier_id = None
    if supplier_display and supplier_display in self.supplier_map:
        preferred_supplier_id = self.supplier_map[supplier_display].id

    # Create product
    try:
        product = self.product_service.create_product(
            name=name,
            ingredient_id=self.selected_ingredient.id,
            package_unit=unit,
            package_unit_quantity=qty,
            preferred_supplier_id=preferred_supplier_id
        )

        # Success - update dropdown and select
        with session_scope() as session:
            product_values = build_product_dropdown_values(
                self.selected_ingredient.id, session
            )
            self.product_combo.reset_values(product_values)
            self.product_combo.set(f"⭐ {name}")  # New product is "recent"
            self.selected_product = product

        # Collapse form
        self._cancel_inline_create()

    except Exception as e:
        self._show_error(f"Failed to create product: {e}")
        # Keep form expanded for correction
```

### Subtask T055 – Implement Cancel button

**Purpose**: Close form without changes.

**Steps**:
1. Clear form fields
2. Collapse accordion
3. Re-enable product dropdown
4. Return focus to product dropdown

**Code**:
```python
def _cancel_inline_create(self):
    """Cancel inline product creation."""
    # Clear form
    self.inline_name_entry.delete(0, 'end')
    self.inline_qty_entry.delete(0, 'end')
    self.inline_unit_combo.set("")
    self.inline_supplier_combo.set("")

    # Collapse
    self.inline_create_frame.grid_forget()
    self.inline_create_expanded = False

    # Re-enable product dropdown
    self.product_combo.configure(state="normal")
    self.product_combo.focus_set()
```

### Subtask T056 – Success: select and collapse

**Purpose**: Smooth transition after product creation.

**Steps**:
1. Rebuild product dropdown with new product
2. Select new product (with ⭐ as it's new/recent)
3. Collapse inline form
4. Continue workflow (supplier/price next)

**Notes**: Already covered in T054 implementation.

### Subtask T057 – Error: show message

**Purpose**: Clear error display for user correction.

**Steps**:
1. Show error message (dialog or inline label)
2. Keep form expanded
3. Focus on relevant field if known

**Code**:
```python
def _show_error(self, message: str):
    """Display error message."""
    from tkinter import messagebox
    messagebox.showerror("Error", message, parent=self)
```

### Subtask T058 – Handle zero-products case

**Purpose**: Prominent create option when no products exist.

**Steps**:
1. In ingredient selection, check product count
2. If zero, show prominent button or auto-expand
3. Orange/highlight color for emphasis

**Code**:
```python
# In _on_ingredient_selected:
product_count = session.query(Product).filter_by(
    ingredient_id=ingredient.id,
    is_hidden=False
).count()

if product_count == 0:
    # Highlight the New button
    self.new_product_btn.configure(
        text="+ Create First Product",
        fg_color="orange"
    )
else:
    self.new_product_btn.configure(
        text="+ New",
        fg_color=None  # Default color
    )
```

### Subtask T059 – Integration tests [P]

**Purpose**: Verify inline creation workflow.

**Test Cases**:
```python
def test_inline_form_expands_on_button(mock_dialog):
    """Form should expand when + New clicked."""
    dialog = create_dialog()
    dialog._on_ingredient_selected('All-Purpose Flour')
    dialog.new_product_btn.invoke()

    assert dialog.inline_create_expanded
    assert dialog.inline_create_frame.winfo_viewable()

def test_inline_form_prefills_ingredient(mock_dialog):
    """Ingredient should be pre-filled and read-only."""
    dialog = create_dialog()
    dialog._on_ingredient_selected('All-Purpose Flour')
    dialog._toggle_inline_create()

    assert 'All-Purpose Flour' in dialog.inline_ingredient_label.cget('text')

def test_inline_creation_adds_to_dropdown(mock_dialog, mock_product_service):
    """New product should appear in dropdown."""
    dialog = create_dialog()
    # Setup and create product...
    dialog._create_product_inline()

    values = dialog.product_combo.cget('values')
    assert any('New Product Name' in v for v in values)
```

**Parallel?**: Yes, can be written alongside implementation

## Test Strategy

Manual testing:
1. Select ingredient with no products - verify prominent create button
2. Click + New - verify form expands
3. Verify pre-fills: ingredient, supplier, unit
4. Create product - verify appears in dropdown, selected, form collapses
5. Cancel - verify form collapses, no product created
6. Create with error - verify form stays open with error message

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Dialog layout breaks on expand | Test layout stability |
| Product creation fails | Clear error handling |
| Focus management | Test focus after expand/collapse |

## Definition of Done Checklist

- [ ] Inline form frame created
- [ ] Accordion expand/collapse works
- [ ] Ingredient pre-filled (read-only)
- [ ] Supplier pre-filled from session
- [ ] Unit pre-filled from category defaults
- [ ] Create button creates product and updates dropdown
- [ ] Cancel button collapses without changes
- [ ] Zero-products case shows prominent button
- [ ] Error handling keeps form expanded
- [ ] Integration tests pass

## Review Guidance

**Reviewers should verify**:
1. Form expands/collapses smoothly
2. Pre-fills are correct (ingredient, supplier, unit)
3. Product creation works and updates dropdown
4. New product is selected after creation
5. Cancel properly cleans up
6. Zero-products case is visually prominent

## Activity Log

- 2025-12-24T23:15:00Z – system – lane=planned – Prompt created.
- 2025-12-25T05:31:46Z – claude – shell_pid=33920 – lane=doing – Starting inline product creation implementation
- 2025-12-25T05:39:48Z – claude – shell_pid=33920 – lane=for_review – Inline product creation implemented with prefill and accordion UI
- 2025-12-25T15:19:40Z – claude – shell_pid=33920 – lane=done – Moved to done
