---
work_package_id: "WP06"
subtasks:
  - "T049"
  - "T050"
  - "T051"
  - "T052"
  - "T053"
  - "T054"
  - "T055"
  - "T056"
title: "Add Product Dialog"
phase: "Phase 3 - UI Layer"
lane: "doing"
assignee: ""
agent: "system"
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-22T14:35:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP06 – Add Product Dialog

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

**Goal**: Create dialog for adding and editing products.

**Success Criteria**:
- [ ] Dialog opens from Products tab (US-2 Scenario 1)
- [ ] All required fields present (US-2 Scenario 1)
- [ ] Save creates product in database (US-2 Scenario 2)
- [ ] Ingredient selection works (US-2 Scenario 3)
- [ ] Validation prevents incomplete saves (US-2 Scenario 4)
- [ ] Edit mode pre-populates fields (US-5)

## Context & Constraints

**Reference Documents**:
- User Story 2 & 5: `kitty-specs/027-product-catalog-management/spec.md`
- Existing dialogs: `src/ui/forms/add_inventory_dialog.py`

**Parallel Opportunity**: Can develop alongside WP07.

## Subtasks & Detailed Guidance

### T049 – Create add_product_dialog.py

**Purpose**: Establish dialog following project conventions.

**Steps**:
1. Create `src/ui/forms/add_product_dialog.py`
2. Import required modules:
```python
import customtkinter as ctk
from typing import Optional
from src.services import product_catalog_service, supplier_service, ingredient_service
```
3. Create class:
```python
class AddProductDialog(ctk.CTkToplevel):
    def __init__(self, parent, product_id: Optional[int] = None, **kwargs):
        super().__init__(parent, **kwargs)
        self.product_id = product_id  # None for add, ID for edit
        self.result = None
        self._setup_ui()
        if product_id:
            self._load_product()
```

**Files**: `src/ui/forms/add_product_dialog.py` (NEW)

### T050 – Add form fields

**Purpose**: Create input fields for product attributes.

**Steps**:
```python
def _setup_ui(self):
    self.title("Add Product" if not self.product_id else "Edit Product")
    self.geometry("500x400")

    # Product Name
    ctk.CTkLabel(self, text="Product Name *").pack(pady=(10, 0))
    self.name_var = ctk.StringVar()
    self.name_entry = ctk.CTkEntry(self, textvariable=self.name_var, width=300)
    self.name_entry.pack(pady=5)

    # Brand (optional)
    ctk.CTkLabel(self, text="Brand").pack(pady=(10, 0))
    self.brand_var = ctk.StringVar()
    self.brand_entry = ctk.CTkEntry(self, textvariable=self.brand_var, width=300)
    self.brand_entry.pack(pady=5)

    # Package Unit
    ctk.CTkLabel(self, text="Package Unit *").pack(pady=(10, 0))
    self.unit_var = ctk.StringVar()
    self.unit_entry = ctk.CTkEntry(
        self,
        textvariable=self.unit_var,
        width=300,
        placeholder_text="e.g., lb, oz, each, bag"
    )
    self.unit_entry.pack(pady=5)

    # Package Quantity
    ctk.CTkLabel(self, text="Package Quantity *").pack(pady=(10, 0))
    self.quantity_var = ctk.StringVar()
    self.quantity_entry = ctk.CTkEntry(
        self,
        textvariable=self.quantity_var,
        width=300,
        placeholder_text="e.g., 5 (for 5 lb bag)"
    )
    self.quantity_entry.pack(pady=5)
```

### T051 – Add ingredient and supplier dropdowns

**Purpose**: Enable ingredient selection and optional supplier.

**Steps**:
```python
def _setup_ui(self):
    ...
    # Ingredient dropdown (required)
    ctk.CTkLabel(self, text="Ingredient *").pack(pady=(10, 0))
    self.ingredient_var = ctk.StringVar()
    ingredients = ingredient_service.get_all_ingredients()
    self.ingredients_map = {i["name"]: i for i in ingredients}
    self.ingredient_dropdown = ctk.CTkComboBox(
        self,
        variable=self.ingredient_var,
        values=list(self.ingredients_map.keys()),
        command=self._on_ingredient_change,
        width=300
    )
    self.ingredient_dropdown.pack(pady=5)

    # Category display (read-only, auto-populated)
    ctk.CTkLabel(self, text="Category").pack(pady=(10, 0))
    self.category_var = ctk.StringVar()
    self.category_label = ctk.CTkLabel(self, textvariable=self.category_var)
    self.category_label.pack(pady=5)

    # Preferred Supplier dropdown (optional)
    ctk.CTkLabel(self, text="Preferred Supplier").pack(pady=(10, 0))
    self.supplier_var = ctk.StringVar(value="None")
    suppliers = supplier_service.get_active_suppliers()
    self.suppliers_map = {s["name"]: s for s in suppliers}
    self.supplier_dropdown = ctk.CTkComboBox(
        self,
        variable=self.supplier_var,
        values=["None"] + list(self.suppliers_map.keys()),
        width=300
    )
    self.supplier_dropdown.pack(pady=5)
```

### T052 – Implement ingredient category auto-population

**Purpose**: Show category when ingredient selected (US-2 Scenario 3).

**Steps**:
```python
def _on_ingredient_change(self, choice):
    if choice in self.ingredients_map:
        ingredient = self.ingredients_map[choice]
        self.category_var.set(ingredient.get("category", "Unknown"))
```

### T053 – Add validation

**Purpose**: Ensure required fields are filled (US-2 Scenario 4).

**Steps**:
```python
def _validate(self) -> bool:
    errors = []

    if not self.name_var.get().strip():
        errors.append("Product name is required")

    if not self.unit_var.get().strip():
        errors.append("Package unit is required")

    qty_str = self.quantity_var.get().strip()
    if not qty_str:
        errors.append("Package quantity is required")
    else:
        try:
            qty = float(qty_str)
            if qty <= 0:
                errors.append("Package quantity must be positive")
        except ValueError:
            errors.append("Package quantity must be a number")

    if not self.ingredient_var.get() or self.ingredient_var.get() not in self.ingredients_map:
        errors.append("Ingredient must be selected")

    if errors:
        self._show_errors(errors)
        return False
    return True

def _show_errors(self, errors):
    from tkinter import messagebox
    messagebox.showerror("Validation Error", "\n".join(errors))
```

### T054 – Implement Save button

**Purpose**: Create/update product via service.

**Steps**:
```python
def _setup_buttons(self):
    button_frame = ctk.CTkFrame(self)
    button_frame.pack(pady=20)

    self.save_btn = ctk.CTkButton(
        button_frame,
        text="Save",
        command=self._on_save
    )
    self.save_btn.pack(side="left", padx=10)

    self.cancel_btn = ctk.CTkButton(
        button_frame,
        text="Cancel",
        command=self._on_cancel
    )
    self.cancel_btn.pack(side="left", padx=10)

def _on_save(self):
    if not self._validate():
        return

    ingredient = self.ingredients_map[self.ingredient_var.get()]
    supplier_id = None
    if self.supplier_var.get() != "None":
        supplier = self.suppliers_map.get(self.supplier_var.get())
        supplier_id = supplier["id"] if supplier else None

    try:
        if self.product_id:
            # Edit mode
            product_catalog_service.update_product(
                self.product_id,
                product_name=self.name_var.get().strip(),
                brand=self.brand_var.get().strip() or None,
                package_unit=self.unit_var.get().strip(),
                package_quantity=float(self.quantity_var.get()),
                ingredient_id=ingredient["id"],
                preferred_supplier_id=supplier_id
            )
        else:
            # Add mode
            product_catalog_service.create_product(
                product_name=self.name_var.get().strip(),
                ingredient_id=ingredient["id"],
                package_unit=self.unit_var.get().strip(),
                package_quantity=float(self.quantity_var.get()),
                preferred_supplier_id=supplier_id,
                brand=self.brand_var.get().strip() or None
            )

        self.result = True
        self.destroy()

    except Exception as e:
        from tkinter import messagebox
        messagebox.showerror("Error", str(e))
```

### T055 – Implement Cancel button

**Purpose**: Close dialog without saving.

**Steps**:
```python
def _on_cancel(self):
    self.result = None
    self.destroy()
```

### T056 – Support edit mode

**Purpose**: Pre-populate fields for existing product (US-5).

**Steps**:
```python
def _load_product(self):
    """Load existing product for edit mode."""
    product = product_catalog_service.get_product_with_last_price(self.product_id)
    if not product:
        from tkinter import messagebox
        messagebox.showerror("Error", "Product not found")
        self.destroy()
        return

    self.name_var.set(product.get("product_name", ""))
    self.brand_var.set(product.get("brand", "") or "")
    self.unit_var.set(product.get("package_unit", ""))
    self.quantity_var.set(str(product.get("package_quantity", "")))

    # Find and set ingredient
    ingredient_id = product.get("ingredient_id")
    for name, ing in self.ingredients_map.items():
        if ing["id"] == ingredient_id:
            self.ingredient_var.set(name)
            self._on_ingredient_change(name)
            break

    # Find and set supplier
    supplier_id = product.get("preferred_supplier_id")
    if supplier_id:
        for name, sup in self.suppliers_map.items():
            if sup["id"] == supplier_id:
                self.supplier_var.set(name)
                break
```

## Test Strategy

**Manual Testing**:
- Open dialog in add mode
- Verify all fields present
- Test validation (empty required fields)
- Test successful save
- Open dialog in edit mode
- Verify fields pre-populated
- Test edit save

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Ingredient list too long | Could add search; acceptable for baking scale |
| Supplier dropdown stale | Refresh on dialog open |
| Concurrent edit | Single-user app, not a concern |

## Definition of Done Checklist

- [ ] Dialog file created
- [ ] All form fields present with labels
- [ ] Ingredient dropdown populated
- [ ] Supplier dropdown shows active only
- [ ] Category auto-populates on ingredient selection
- [ ] Validation prevents empty required fields
- [ ] Validation prevents invalid quantity
- [ ] Save creates product (add mode)
- [ ] Save updates product (edit mode)
- [ ] Cancel closes without saving
- [ ] Edit mode pre-populates all fields

## Review Guidance

**Key Checkpoints**:
1. Required fields marked with *
2. Ingredient selection triggers category display
3. Supplier dropdown shows only active suppliers
4. Validation error messages are clear
5. Edit mode loads existing data correctly

## Activity Log

- 2025-12-22T14:35:00Z – system – lane=planned – Prompt created via /spec-kitty.tasks
- 2025-12-22T23:17:46Z – system – shell_pid= – lane=doing – Starting implementation of Add Product Dialog
