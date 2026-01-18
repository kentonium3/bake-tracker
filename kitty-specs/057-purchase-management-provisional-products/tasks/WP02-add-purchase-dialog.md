---
work_package_id: WP02
title: Add Purchase Dialog Enhancement
lane: "for_review"
dependencies: []
subtasks: [T007, T008, T009, T010, T011, T012]
agent: "claude"
history:
- date: '2026-01-17'
  action: created
  agent: claude
estimated_lines: 450
priority: P1
---

# WP02: Add Purchase Dialog Enhancement

**Feature**: F057 Purchase Management with Provisional Products
**Objective**: Enhance Add Purchase dialog with inline provisional product creation when product not found.

## Implementation Command

```bash
spec-kitty implement WP02 --base WP01
```

## Context

This work package implements the core user story: enabling purchase recording even when the product doesn't exist in the catalog. When a user searches for a product and it's not found, the dialog expands to show an inline form for creating a provisional product.

**Key Design Decisions** (from plan.md):
- Inline expansion (not modal) - keeps user in purchase context
- Prepopulate fields from search context to reduce data entry
- Minimal required fields: ingredient, brand, package_unit, package_unit_quantity

**Reference Files**:
- `src/ui/dialogs/add_purchase_dialog.py` - Current dialog (525 lines)
- `src/ui/products_tab.py` - Cascading ingredient filter pattern
- `src/services/product_service.py` - `create_provisional_product()` from WP01

## Subtasks

### T007: Add "Product not found" detection and inline expansion trigger

**Purpose**: Detect when user's search doesn't match any product and show expansion button.

**File**: `src/ui/dialogs/add_purchase_dialog.py`

**Steps**:

1. Add state variable for expansion:
```python
def __init__(self, parent, on_save=None):
    # ... existing code ...
    self._provisional_expanded = False
    self._provisional_frame = None
```

2. Modify product search handling to detect "not found":
```python
def _on_product_search(self, search_text: str) -> None:
    """Handle product search - show 'not found' when no matches."""
    search_text = search_text.strip()
    if not search_text:
        self._hide_not_found()
        return

    # Filter products matching search
    matches = [
        name for name in self.product_map.keys()
        if search_text.lower() in name.lower()
    ]

    if not matches and len(search_text) >= 3:
        # No matches found - show "create provisional" option
        self._show_not_found(search_text)
    else:
        self._hide_not_found()
```

3. Add "not found" UI with expansion button:
```python
def _show_not_found(self, search_text: str) -> None:
    """Show 'product not found' message with create option."""
    if not hasattr(self, 'not_found_frame'):
        self._create_not_found_widgets()

    self.not_found_label.configure(
        text=f'"{search_text}" not found in product catalog'
    )
    self.not_found_frame.pack(after=self.product_combo, fill="x", padx=10, pady=5)
    self._last_search_text = search_text

def _hide_not_found(self) -> None:
    """Hide the 'not found' message."""
    if hasattr(self, 'not_found_frame'):
        self.not_found_frame.pack_forget()
```

4. Create "not found" widgets:
```python
def _create_not_found_widgets(self) -> None:
    """Create the 'product not found' UI components."""
    self.not_found_frame = ctk.CTkFrame(self.form_frame, fg_color="transparent")

    self.not_found_label = ctk.CTkLabel(
        self.not_found_frame,
        text="",
        text_color="orange"
    )
    self.not_found_label.pack(side="left", padx=5)

    self.create_provisional_btn = ctk.CTkButton(
        self.not_found_frame,
        text="Create Provisional Product",
        command=self._toggle_provisional_form,
        width=180,
        fg_color="#2B7A0B",  # Green accent
    )
    self.create_provisional_btn.pack(side="right", padx=5)
```

**Validation**:
- [ ] "Not found" message appears when search has no matches
- [ ] Message only appears after 3+ characters typed
- [ ] "Create Provisional Product" button visible
- [ ] Clicking button triggers expansion

---

### T008: Create provisional product form section with ingredient selector

**Purpose**: Build the expandable form for entering provisional product details.

**File**: `src/ui/dialogs/add_purchase_dialog.py`

**Steps**:

1. Add toggle function for expansion:
```python
def _toggle_provisional_form(self) -> None:
    """Toggle the provisional product form visibility."""
    if self._provisional_expanded:
        self._collapse_provisional_form()
    else:
        self._expand_provisional_form()

def _expand_provisional_form(self) -> None:
    """Show the provisional product creation form."""
    if self._provisional_frame is None:
        self._create_provisional_form()

    self._provisional_frame.pack(after=self.not_found_frame, fill="x", padx=10, pady=10)
    self._provisional_expanded = True
    self.create_provisional_btn.configure(text="Cancel")

    # Resize dialog to accommodate form
    self.geometry("500x850")

def _collapse_provisional_form(self) -> None:
    """Hide the provisional product creation form."""
    if self._provisional_frame:
        self._provisional_frame.pack_forget()
    self._provisional_expanded = False
    self.create_provisional_btn.configure(text="Create Provisional Product")
    self.geometry("500x600")
```

2. Create the form widgets with cascading ingredient selector:
```python
def _create_provisional_form(self) -> None:
    """Create the provisional product form widgets."""
    self._provisional_frame = ctk.CTkFrame(self.form_frame)

    # Header
    header = ctk.CTkLabel(
        self._provisional_frame,
        text="Create Provisional Product",
        font=ctk.CTkFont(size=14, weight="bold"),
    )
    header.pack(pady=(10, 5))

    info_label = ctk.CTkLabel(
        self._provisional_frame,
        text="Fill in what you know. Missing details can be added later.",
        font=ctk.CTkFont(size=10),
        text_color="gray",
    )
    info_label.pack(pady=(0, 10))

    # Ingredient selection (cascading L0 -> L1 -> L2)
    ing_frame = ctk.CTkFrame(self._provisional_frame)
    ing_frame.pack(fill="x", padx=10, pady=5)

    ctk.CTkLabel(ing_frame, text="Ingredient *", anchor="w").pack(anchor="w")

    # L0 (Category) dropdown
    self._prov_l0_var = ctk.StringVar(value="Select Category")
    self._prov_l0_dropdown = ctk.CTkOptionMenu(
        ing_frame,
        variable=self._prov_l0_var,
        values=["Select Category"],
        command=self._on_prov_l0_change,
        width=200,
    )
    self._prov_l0_dropdown.pack(anchor="w", pady=2)

    # L1 (Subcategory) dropdown
    self._prov_l1_var = ctk.StringVar(value="Select Subcategory")
    self._prov_l1_dropdown = ctk.CTkOptionMenu(
        ing_frame,
        variable=self._prov_l1_var,
        values=["Select Subcategory"],
        command=self._on_prov_l1_change,
        width=200,
        state="disabled",
    )
    self._prov_l1_dropdown.pack(anchor="w", pady=2)

    # L2 (Leaf ingredient) dropdown
    self._prov_l2_var = ctk.StringVar(value="Select Ingredient")
    self._prov_l2_dropdown = ctk.CTkOptionMenu(
        ing_frame,
        variable=self._prov_l2_var,
        values=["Select Ingredient"],
        width=200,
        state="disabled",
    )
    self._prov_l2_dropdown.pack(anchor="w", pady=2)

    # Brand entry
    brand_frame = ctk.CTkFrame(self._provisional_frame)
    brand_frame.pack(fill="x", padx=10, pady=5)
    ctk.CTkLabel(brand_frame, text="Brand *", anchor="w").pack(anchor="w")
    self._prov_brand_var = ctk.StringVar()
    self._prov_brand_entry = ctk.CTkEntry(
        brand_frame,
        textvariable=self._prov_brand_var,
        width=200,
        placeholder_text="e.g., King Arthur",
    )
    self._prov_brand_entry.pack(anchor="w", pady=2)

    # Product name entry (optional)
    name_frame = ctk.CTkFrame(self._provisional_frame)
    name_frame.pack(fill="x", padx=10, pady=5)
    ctk.CTkLabel(name_frame, text="Product Name (optional)", anchor="w").pack(anchor="w")
    self._prov_name_var = ctk.StringVar()
    self._prov_name_entry = ctk.CTkEntry(
        name_frame,
        textvariable=self._prov_name_var,
        width=200,
        placeholder_text="e.g., Organic",
    )
    self._prov_name_entry.pack(anchor="w", pady=2)

    # Package details
    pkg_frame = ctk.CTkFrame(self._provisional_frame)
    pkg_frame.pack(fill="x", padx=10, pady=5)
    ctk.CTkLabel(pkg_frame, text="Package *", anchor="w").pack(anchor="w")

    pkg_inner = ctk.CTkFrame(pkg_frame, fg_color="transparent")
    pkg_inner.pack(anchor="w", pady=2)

    self._prov_pkg_qty_var = ctk.StringVar(value="1")
    self._prov_pkg_qty_entry = ctk.CTkEntry(
        pkg_inner,
        textvariable=self._prov_pkg_qty_var,
        width=60,
        placeholder_text="1",
    )
    self._prov_pkg_qty_entry.pack(side="left", padx=(0, 5))

    self._prov_pkg_unit_var = ctk.StringVar()
    self._prov_pkg_unit_entry = ctk.CTkEntry(
        pkg_inner,
        textvariable=self._prov_pkg_unit_var,
        width=80,
        placeholder_text="lb, oz, each",
    )
    self._prov_pkg_unit_entry.pack(side="left")

    # Create button
    self._prov_create_btn = ctk.CTkButton(
        self._provisional_frame,
        text="Create & Use Product",
        command=self._on_create_provisional,
        width=180,
    )
    self._prov_create_btn.pack(pady=15)

    # Error label for provisional form
    self._prov_error_label = ctk.CTkLabel(
        self._provisional_frame,
        text="",
        text_color="red",
    )
    self._prov_error_label.pack()

    # Load ingredient hierarchy data
    self._load_ingredient_hierarchy()
```

3. Load ingredient hierarchy data:
```python
def _load_ingredient_hierarchy(self) -> None:
    """Load ingredient hierarchy for dropdowns."""
    from src.services import ingredient_hierarchy_service

    try:
        roots = ingredient_hierarchy_service.get_root_ingredients()
        self._prov_l0_map = {
            ing.get("display_name", ing.get("name", "?")): ing
            for ing in roots
        }
        values = ["Select Category"] + sorted(self._prov_l0_map.keys())
        self._prov_l0_dropdown.configure(values=values)
        self._prov_l1_map = {}
        self._prov_l2_map = {}
    except Exception as e:
        print(f"Warning: Failed to load ingredient hierarchy: {e}")
```

**Validation**:
- [ ] Form expands when button clicked
- [ ] Form collapses when Cancel clicked
- [ ] All required fields have labels with asterisks
- [ ] Ingredient selector has 3 cascading dropdowns

---

### T009: Implement brand/product name prepopulation from search context

**Purpose**: Parse search text to prepopulate brand field, reducing data entry.

**File**: `src/ui/dialogs/add_purchase_dialog.py`

**Steps**:

1. Add prepopulation logic when expanding form:
```python
def _expand_provisional_form(self) -> None:
    """Show the provisional product creation form."""
    # ... existing expansion code ...

    # Prepopulate brand from search text
    self._prepopulate_from_search()

def _prepopulate_from_search(self) -> None:
    """Attempt to prepopulate fields from the search text."""
    search_text = getattr(self, '_last_search_text', '').strip()
    if not search_text:
        return

    # Common brand patterns (capitalized words at start)
    # E.g., "King Arthur flour" -> Brand: "King Arthur"
    words = search_text.split()
    if not words:
        return

    # Check if first word(s) look like a brand (capitalized)
    brand_words = []
    remaining_words = []
    found_lowercase = False

    for word in words:
        # Stop collecting brand words when we hit a lowercase word
        if word[0].islower() and not found_lowercase:
            found_lowercase = True
        if not found_lowercase and word[0].isupper():
            brand_words.append(word)
        else:
            remaining_words.append(word)

    if brand_words:
        self._prov_brand_var.set(" ".join(brand_words))

    if remaining_words:
        self._prov_name_var.set(" ".join(remaining_words))
```

**Validation**:
- [ ] Search "King Arthur flour" prepopulates brand "King Arthur"
- [ ] Search "organic butter" doesn't prepopulate brand (no capitals)
- [ ] Search "ALDI eggs" prepopulates brand "ALDI"
- [ ] User can modify prepopulated values

---

### T010: Add validation for provisional product minimum fields

**Purpose**: Ensure required fields are filled before attempting creation.

**File**: `src/ui/dialogs/add_purchase_dialog.py`

**Steps**:

1. Add validation function:
```python
def _validate_provisional_form(self) -> tuple:
    """Validate provisional product form fields.

    Returns:
        Tuple of (is_valid: bool, error_message: str)
    """
    # Check ingredient selected
    l2_selection = self._prov_l2_var.get()
    if l2_selection == "Select Ingredient" or l2_selection not in self._prov_l2_map:
        return False, "Please select an ingredient"

    # Check brand
    brand = self._prov_brand_var.get().strip()
    if not brand:
        return False, "Brand is required (use 'Unknown' if not known)"

    # Check package unit
    pkg_unit = self._prov_pkg_unit_var.get().strip()
    if not pkg_unit:
        return False, "Package unit is required (e.g., lb, oz, each)"

    # Check package quantity
    try:
        pkg_qty = float(self._prov_pkg_qty_var.get().strip())
        if pkg_qty <= 0:
            return False, "Package quantity must be greater than 0"
    except ValueError:
        return False, "Package quantity must be a number"

    return True, ""
```

**Validation**:
- [ ] Returns error if no ingredient selected
- [ ] Returns error if brand empty
- [ ] Returns error if package unit empty
- [ ] Returns error if package quantity invalid
- [ ] Returns success when all required fields filled

---

### T011: Wire form to `create_provisional_product()` service method

**Purpose**: Create the provisional product when user submits the form.

**File**: `src/ui/dialogs/add_purchase_dialog.py`

**Steps**:

1. Implement create handler:
```python
def _on_create_provisional(self) -> None:
    """Handle provisional product creation."""
    # Clear previous errors
    self._prov_error_label.configure(text="")

    # Validate
    is_valid, error = self._validate_provisional_form()
    if not is_valid:
        self._prov_error_label.configure(text=error)
        return

    # Get values
    ingredient = self._prov_l2_map[self._prov_l2_var.get()]
    ingredient_id = ingredient.get("id")
    brand = self._prov_brand_var.get().strip()
    product_name = self._prov_name_var.get().strip() or None
    pkg_unit = self._prov_pkg_unit_var.get().strip()
    pkg_qty = float(self._prov_pkg_qty_var.get().strip())

    try:
        from src.services.product_service import create_provisional_product

        product = create_provisional_product(
            ingredient_id=ingredient_id,
            brand=brand,
            package_unit=pkg_unit,
            package_unit_quantity=pkg_qty,
            product_name=product_name,
        )

        # Success - use the new product
        self._on_provisional_product_created(product)

    except Exception as e:
        self._prov_error_label.configure(text=f"Failed: {str(e)}")
```

**Validation**:
- [ ] Calls `create_provisional_product()` with correct parameters
- [ ] Shows error message on failure
- [ ] Proceeds to success handler on success

---

### T012: Update dialog to continue purchase flow with newly created product

**Purpose**: After creating provisional product, select it and continue with purchase entry.

**File**: `src/ui/dialogs/add_purchase_dialog.py`

**Steps**:

1. Add success handler:
```python
def _on_provisional_product_created(self, product) -> None:
    """Handle successful provisional product creation.

    Collapses the form, selects the new product, and continues purchase flow.
    """
    # Reload products to include new one
    self._load_products()

    # Find and select the new product
    display_name = product.display_name
    if display_name in self.product_map:
        self.product_var.set(display_name)
        self._on_product_selected(display_name)

    # Collapse provisional form
    self._collapse_provisional_form()
    self._hide_not_found()

    # Show success message briefly
    self.error_label.configure(
        text=f"Created provisional product: {display_name}",
        text_color="green"
    )

    # Focus on quantity field to continue
    self.qty_entry.focus_set()
```

2. Update `_load_products()` to be callable for refresh:
```python
def _load_products(self) -> None:
    """Load products from service."""
    try:
        self.products = get_products(include_hidden=False)
        self.product_map = {}
        for p in self.products:
            display_name = p.get("display_name", p.get("product_name", "Unknown"))
            self.product_map[display_name] = p

        # Update dropdown values
        product_names = sorted(self.product_map.keys())
        self.product_combo.configure(values=product_names)
    except Exception:
        self.products = []
        self.product_map = {}
```

**Validation**:
- [ ] New product appears in dropdown after creation
- [ ] New product is automatically selected
- [ ] Product price auto-fill is triggered (may show "No price history")
- [ ] Form collapses and "not found" message hidden
- [ ] Focus moves to quantity field
- [ ] Success message displayed

---

## Supporting Code

### Cascading Dropdown Handlers

Add these handlers for the ingredient hierarchy dropdowns:

```python
def _on_prov_l0_change(self, value: str) -> None:
    """Handle L0 category selection."""
    from src.services import ingredient_hierarchy_service

    if value == "Select Category":
        self._prov_l1_dropdown.configure(values=["Select Subcategory"], state="disabled")
        self._prov_l2_dropdown.configure(values=["Select Ingredient"], state="disabled")
        self._prov_l1_var.set("Select Subcategory")
        self._prov_l2_var.set("Select Ingredient")
        return

    if value not in self._prov_l0_map:
        return

    l0_id = self._prov_l0_map[value].get("id")
    try:
        children = ingredient_hierarchy_service.get_children(l0_id)
        self._prov_l1_map = {
            child.get("display_name", "?"): child for child in children
        }
        values = ["Select Subcategory"] + sorted(self._prov_l1_map.keys())
        self._prov_l1_dropdown.configure(values=values, state="normal")
        self._prov_l1_var.set("Select Subcategory")

        # Reset L2
        self._prov_l2_map = {}
        self._prov_l2_dropdown.configure(values=["Select Ingredient"], state="disabled")
        self._prov_l2_var.set("Select Ingredient")
    except Exception as e:
        print(f"Warning: Failed to load subcategories: {e}")

def _on_prov_l1_change(self, value: str) -> None:
    """Handle L1 subcategory selection."""
    from src.services import ingredient_hierarchy_service

    if value == "Select Subcategory":
        self._prov_l2_dropdown.configure(values=["Select Ingredient"], state="disabled")
        self._prov_l2_var.set("Select Ingredient")
        return

    if value not in self._prov_l1_map:
        return

    l1_id = self._prov_l1_map[value].get("id")
    try:
        children = ingredient_hierarchy_service.get_children(l1_id)
        self._prov_l2_map = {
            child.get("display_name", "?"): child for child in children
        }
        values = ["Select Ingredient"] + sorted(self._prov_l2_map.keys())
        self._prov_l2_dropdown.configure(values=values, state="normal")
        self._prov_l2_var.set("Select Ingredient")
    except Exception as e:
        print(f"Warning: Failed to load ingredients: {e}")
```

---

## Definition of Done

- [ ] All 6 subtasks completed
- [ ] "Product not found" message appears for unknown search
- [ ] Provisional product form expands inline
- [ ] Cascading ingredient dropdowns work (L0 -> L1 -> L2)
- [ ] Brand prepopulated from search context when possible
- [ ] Validation prevents creation with missing required fields
- [ ] Product created successfully via `create_provisional_product()`
- [ ] New product automatically selected after creation
- [ ] Purchase flow continues seamlessly
- [ ] Manual test: Full workflow from search to purchase complete

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Dialog too tall for screen | Make form scrollable or limit visible fields |
| Ingredient hierarchy slow to load | Cache hierarchy data after first load |
| Brand parsing too aggressive | Keep it simple - only obvious patterns |
| User confusion about required fields | Clear asterisks and helpful placeholder text |

## Reviewer Notes

When reviewing this WP:
1. Test full workflow: search -> not found -> expand -> create -> select -> complete purchase
2. Verify form collapses cleanly on cancel
3. Check that provisional product appears in dropdown immediately
4. Verify ingredient cascade works correctly
5. Test with edge cases: long brand names, special characters

## Activity Log

- 2026-01-18T02:12:23Z – claude – lane=doing – Starting implementation of Purchase Service Integration
- 2026-01-18T02:16:14Z – claude – lane=for_review – Ready for review: Enhanced Add Purchase dialog with inline provisional product creation. Added product search detection, not-found message, cascading ingredient selector, brand prepopulation from search context, form validation, and seamless flow continuation after product creation.
