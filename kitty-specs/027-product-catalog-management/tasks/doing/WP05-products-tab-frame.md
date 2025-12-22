---
work_package_id: "WP05"
subtasks:
  - "T039"
  - "T040"
  - "T041"
  - "T042"
  - "T043"
  - "T044"
  - "T045"
  - "T046"
  - "T047"
  - "T048"
title: "Products Tab Frame"
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

# Work Package Prompt: WP05 – Products Tab Frame

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

**Goal**: Create main Products tab with grid, filters, and search.

**Success Criteria**:
- [ ] Products tab appears in main window
- [ ] Grid displays products with all columns (US-1 Scenario 1)
- [ ] Search filters products in real-time (US-1 Scenario 2)
- [ ] Category filter works (US-1 Scenario 3)
- [ ] Show Hidden checkbox works (US-1 Scenario 4)
- [ ] Double-click opens product detail

## Context & Constraints

**Reference Documents**:
- User Story 1: `kitty-specs/027-product-catalog-management/spec.md`
- Existing tabs: `src/ui/inventory_tab.py`, `src/ui/recipes_tab.py`

**UI Framework**: CustomTkinter

**Pattern Reference**: Follow existing tab structure from inventory_tab.py

## Subtasks & Detailed Guidance

### T039 – Create products_tab.py

**Purpose**: Establish Products tab frame following project conventions.

**Steps**:
1. Create `src/ui/products_tab.py`
2. Import required modules:
```python
import customtkinter as ctk
from src.services import product_catalog_service, supplier_service, ingredient_service
```
3. Create class:
```python
class ProductsTab(ctk.CTkFrame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._setup_ui()
        self._load_products()
```

**Files**: `src/ui/products_tab.py` (NEW)

### T040 – Add toolbar with buttons

**Purpose**: Provide Add Product and Manage Suppliers actions.

**Steps**:
```python
def _setup_toolbar(self):
    toolbar = ctk.CTkFrame(self)
    toolbar.pack(fill="x", padx=10, pady=5)

    self.add_btn = ctk.CTkButton(
        toolbar,
        text="Add Product",
        command=self._on_add_product
    )
    self.add_btn.pack(side="left", padx=5)

    self.suppliers_btn = ctk.CTkButton(
        toolbar,
        text="Manage Suppliers",
        command=self._on_manage_suppliers
    )
    self.suppliers_btn.pack(side="left", padx=5)
```

### T041 – Add filter controls

**Purpose**: Enable filtering by Ingredient, Category, and Supplier (FR-014, FR-015, FR-016).

**Steps**:
```python
def _setup_filters(self):
    filter_frame = ctk.CTkFrame(self)
    filter_frame.pack(fill="x", padx=10, pady=5)

    # Ingredient filter
    ctk.CTkLabel(filter_frame, text="Ingredient:").pack(side="left", padx=5)
    self.ingredient_var = ctk.StringVar(value="All")
    self.ingredient_dropdown = ctk.CTkComboBox(
        filter_frame,
        variable=self.ingredient_var,
        values=["All"] + self._get_ingredient_names(),
        command=self._on_filter_change
    )
    self.ingredient_dropdown.pack(side="left", padx=5)

    # Category filter
    ctk.CTkLabel(filter_frame, text="Category:").pack(side="left", padx=5)
    self.category_var = ctk.StringVar(value="All")
    self.category_dropdown = ctk.CTkComboBox(
        filter_frame,
        variable=self.category_var,
        values=["All"] + self._get_categories(),
        command=self._on_filter_change
    )
    self.category_dropdown.pack(side="left", padx=5)

    # Supplier filter
    ctk.CTkLabel(filter_frame, text="Supplier:").pack(side="left", padx=5)
    self.supplier_var = ctk.StringVar(value="All")
    self.supplier_dropdown = ctk.CTkComboBox(
        filter_frame,
        variable=self.supplier_var,
        values=["All"] + self._get_supplier_names(),
        command=self._on_filter_change
    )
    self.supplier_dropdown.pack(side="left", padx=5)
```

### T042 – Add search box

**Purpose**: Enable real-time text search (FR-017).

**Steps**:
```python
def _setup_search(self):
    search_frame = ctk.CTkFrame(self)
    search_frame.pack(fill="x", padx=10, pady=5)

    ctk.CTkLabel(search_frame, text="Search:").pack(side="left", padx=5)
    self.search_var = ctk.StringVar()
    self.search_var.trace_add("write", self._on_search_change)
    self.search_entry = ctk.CTkEntry(
        search_frame,
        textvariable=self.search_var,
        width=200,
        placeholder_text="Search products..."
    )
    self.search_entry.pack(side="left", padx=5)
```

**Notes**:
- Use trace_add to trigger filter on keystroke
- Consider debouncing for performance (optional for small catalogs)

### T043 – Add Show Hidden checkbox

**Purpose**: Toggle visibility of hidden products (FR-018).

**Steps**:
```python
# Add to filter_frame or search_frame
self.show_hidden_var = ctk.BooleanVar(value=False)
self.show_hidden_cb = ctk.CTkCheckBox(
    search_frame,
    text="Show Hidden",
    variable=self.show_hidden_var,
    command=self._on_filter_change
)
self.show_hidden_cb.pack(side="left", padx=20)
```

### T044 – Create product grid

**Purpose**: Display products in tabular format.

**Steps**:
```python
def _setup_grid(self):
    # Use ttk.Treeview for grid (CustomTkinter doesn't have native table)
    from tkinter import ttk

    columns = ("name", "ingredient", "category", "supplier", "last_price", "last_purchase")
    self.tree = ttk.Treeview(self, columns=columns, show="headings")

    self.tree.heading("name", text="Product Name")
    self.tree.heading("ingredient", text="Ingredient")
    self.tree.heading("category", text="Category")
    self.tree.heading("supplier", text="Preferred Supplier")
    self.tree.heading("last_price", text="Last Price")
    self.tree.heading("last_purchase", text="Last Purchase")

    # Set column widths
    self.tree.column("name", width=200)
    self.tree.column("ingredient", width=150)
    self.tree.column("category", width=100)
    self.tree.column("supplier", width=150)
    self.tree.column("last_price", width=80)
    self.tree.column("last_purchase", width=100)

    # Scrollbar
    scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
    self.tree.configure(yscrollcommand=scrollbar.set)

    self.tree.pack(fill="both", expand=True, padx=10, pady=5)
    scrollbar.pack(side="right", fill="y")
```

**Notes**:
- Hidden products should display grayed out (use tag)
- Format last_price as currency

### T045 – Implement grid refresh

**Purpose**: Populate grid from service with current filters.

**Steps**:
```python
def _load_products(self):
    # Clear existing items
    for item in self.tree.get_children():
        self.tree.delete(item)

    # Build filter params
    params = {
        "include_hidden": self.show_hidden_var.get(),
    }

    # Add ingredient filter
    if self.ingredient_var.get() != "All":
        ingredient = self._get_ingredient_by_name(self.ingredient_var.get())
        if ingredient:
            params["ingredient_id"] = ingredient["id"]

    # Add category filter
    if self.category_var.get() != "All":
        params["category"] = self.category_var.get()

    # Add supplier filter
    if self.supplier_var.get() != "All":
        supplier = self._get_supplier_by_name(self.supplier_var.get())
        if supplier:
            params["supplier_id"] = supplier["id"]

    # Add search
    search = self.search_var.get().strip()
    if search:
        params["search"] = search

    # Fetch products
    products = product_catalog_service.get_products(**params)

    # Populate grid
    for p in products:
        values = (
            p["product_name"],
            p.get("ingredient_name", ""),
            p.get("category", ""),
            p.get("preferred_supplier_name", ""),
            f"${p['last_price']:.2f}" if p.get("last_price") else "N/A",
            p.get("last_purchase_date", "N/A")
        )
        tags = ("hidden",) if p.get("is_hidden") else ()
        self.tree.insert("", "end", iid=p["id"], values=values, tags=tags)

    # Style hidden rows
    self.tree.tag_configure("hidden", foreground="gray")
```

### T046 – Add double-click handler

**Purpose**: Open product detail on row double-click.

**Steps**:
```python
def _setup_grid(self):
    ...
    self.tree.bind("<Double-1>", self._on_product_double_click)

def _on_product_double_click(self, event):
    selection = self.tree.selection()
    if selection:
        product_id = int(selection[0])
        self._open_product_detail(product_id)

def _open_product_detail(self, product_id):
    from src.ui.forms.product_detail_dialog import ProductDetailDialog
    dialog = ProductDetailDialog(self, product_id)
    dialog.wait_window()
    self._load_products()  # Refresh after dialog closes
```

### T047 – Add context menu

**Purpose**: Provide Edit, Hide/Unhide, Delete actions.

**Steps**:
```python
def _setup_grid(self):
    ...
    self.tree.bind("<Button-3>", self._on_right_click)  # Right-click

def _on_right_click(self, event):
    item = self.tree.identify_row(event.y)
    if item:
        self.tree.selection_set(item)
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Edit", command=self._on_edit_product)
        menu.add_command(label="Hide" if not self._is_hidden(item) else "Unhide",
                         command=self._on_toggle_hidden)
        menu.add_separator()
        menu.add_command(label="Delete", command=self._on_delete_product)
        menu.post(event.x_root, event.y_root)
```

### T048 – Add Products tab to main window

**Purpose**: Integrate tab into application.

**Steps**:
1. Open `src/ui/main_window.py`
2. Import ProductsTab:
```python
from src.ui.products_tab import ProductsTab
```
3. Add tab in tab creation section:
```python
# In _setup_tabs or similar method
self.products_tab = ProductsTab(self.tabview.tab("Products"))
self.products_tab.pack(fill="both", expand=True)
```

**Files**: `src/ui/main_window.py` (MODIFY)

**Notes**:
- Add tab after existing tabs or in logical order
- Tab name should be "Products"

## Test Strategy

**Manual Testing** (UI components):
- Launch app, verify Products tab appears
- Add sample products via dialog
- Test each filter independently
- Test filter combinations
- Verify search is case-insensitive
- Verify Show Hidden displays grayed rows
- Verify double-click opens detail

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Grid performance with many products | Start with all products; add pagination if needed |
| Filter dropdowns slow to populate | Cache ingredient/category lists |
| Treeview styling limited | Use tags for hidden row styling |

## Definition of Done Checklist

- [ ] Products tab visible in main window
- [ ] Grid displays products with all columns
- [ ] Ingredient filter works
- [ ] Category filter works
- [ ] Supplier filter works
- [ ] Search filters in real-time
- [ ] Show Hidden checkbox toggles visibility
- [ ] Hidden products display grayed
- [ ] Double-click opens product detail (placeholder OK)
- [ ] Context menu provides Edit/Hide/Delete

## Review Guidance

**Key Checkpoints**:
1. Tab appears in main window
2. All filters work independently
3. Filters work in combination
4. Search is case-insensitive
5. Hidden products shown grayed when checkbox checked
6. Double-click handler connected

## Activity Log

- 2025-12-22T14:35:00Z – system – lane=planned – Prompt created via /spec-kitty.tasks
- 2025-12-22T23:10:12Z – system – shell_pid= – lane=doing – Starting implementation
