---
work_package_id: "WP07"
subtasks:
  - "T057"
  - "T058"
  - "T059"
  - "T060"
  - "T061"
  - "T062"
  - "T063"
  - "T064"
title: "Product Detail Dialog"
phase: "Phase 3 - UI Layer"
lane: "planned"
assignee: ""
agent: ""
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

# Work Package Prompt: WP07 – Product Detail Dialog

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

**Goal**: Create dialog showing product details and purchase history.

**Success Criteria**:
- [ ] Dialog opens from grid double-click (US-4 Scenario 1)
- [ ] Purchase history displays sorted by date (US-4 Scenario 2)
- [ ] Empty history shows appropriate message (US-4 Scenario 3)
- [ ] Edit button opens edit dialog (US-5 Scenario 1)
- [ ] Hide/Unhide button toggles visibility (US-6)
- [ ] Delete checks dependencies (US-6 Scenarios 3-4)

## Context & Constraints

**Reference Documents**:
- User Stories 4, 5, 6: `kitty-specs/027-product-catalog-management/spec.md`
- Success Criteria SC-003: 2 clicks to history

**Parallel Opportunity**: Can develop alongside WP06.

## Subtasks & Detailed Guidance

### T057 – Create product_detail_dialog.py

**Purpose**: Establish detail view dialog.

**Steps**:
1. Create `src/ui/forms/product_detail_dialog.py`
2. Import required modules:
```python
import customtkinter as ctk
from tkinter import ttk, messagebox
from src.services import product_catalog_service
```
3. Create class:
```python
class ProductDetailDialog(ctk.CTkToplevel):
    def __init__(self, parent, product_id: int, **kwargs):
        super().__init__(parent, **kwargs)
        self.product_id = product_id
        self.product = None
        self._setup_ui()
        self._load_product()
```

**Files**: `src/ui/forms/product_detail_dialog.py` (NEW)

### T058 – Add product info section

**Purpose**: Display product attributes.

**Steps**:
```python
def _setup_ui(self):
    self.title("Product Details")
    self.geometry("600x500")

    # Info frame
    info_frame = ctk.CTkFrame(self)
    info_frame.pack(fill="x", padx=10, pady=10)

    # Product name (large)
    self.name_label = ctk.CTkLabel(
        info_frame,
        text="",
        font=ctk.CTkFont(size=18, weight="bold")
    )
    self.name_label.pack(pady=5)

    # Details grid
    details_frame = ctk.CTkFrame(info_frame)
    details_frame.pack(fill="x", pady=10)

    # Row 1: Brand, Ingredient
    ctk.CTkLabel(details_frame, text="Brand:").grid(row=0, column=0, sticky="e", padx=5)
    self.brand_label = ctk.CTkLabel(details_frame, text="")
    self.brand_label.grid(row=0, column=1, sticky="w", padx=5)

    ctk.CTkLabel(details_frame, text="Ingredient:").grid(row=0, column=2, sticky="e", padx=5)
    self.ingredient_label = ctk.CTkLabel(details_frame, text="")
    self.ingredient_label.grid(row=0, column=3, sticky="w", padx=5)

    # Row 2: Category, Package
    ctk.CTkLabel(details_frame, text="Category:").grid(row=1, column=0, sticky="e", padx=5)
    self.category_label = ctk.CTkLabel(details_frame, text="")
    self.category_label.grid(row=1, column=1, sticky="w", padx=5)

    ctk.CTkLabel(details_frame, text="Package:").grid(row=1, column=2, sticky="e", padx=5)
    self.package_label = ctk.CTkLabel(details_frame, text="")
    self.package_label.grid(row=1, column=3, sticky="w", padx=5)

    # Row 3: Supplier, Last Price
    ctk.CTkLabel(details_frame, text="Preferred Supplier:").grid(row=2, column=0, sticky="e", padx=5)
    self.supplier_label = ctk.CTkLabel(details_frame, text="")
    self.supplier_label.grid(row=2, column=1, sticky="w", padx=5)

    ctk.CTkLabel(details_frame, text="Last Price:").grid(row=2, column=2, sticky="e", padx=5)
    self.price_label = ctk.CTkLabel(details_frame, text="")
    self.price_label.grid(row=2, column=3, sticky="w", padx=5)
```

### T059 – Add Edit button

**Purpose**: Open AddProductDialog in edit mode.

**Steps**:
```python
def _setup_buttons(self):
    button_frame = ctk.CTkFrame(self)
    button_frame.pack(fill="x", padx=10, pady=5)

    self.edit_btn = ctk.CTkButton(
        button_frame,
        text="Edit",
        command=self._on_edit
    )
    self.edit_btn.pack(side="left", padx=5)

def _on_edit(self):
    from src.ui.forms.add_product_dialog import AddProductDialog
    dialog = AddProductDialog(self, product_id=self.product_id)
    dialog.wait_window()
    if dialog.result:
        self._load_product()  # Refresh after edit
```

### T060 – Add Hide/Unhide button

**Purpose**: Toggle product visibility.

**Steps**:
```python
def _setup_buttons(self):
    ...
    self.hide_btn = ctk.CTkButton(
        button_frame,
        text="Hide",  # Updated dynamically
        command=self._on_toggle_hidden
    )
    self.hide_btn.pack(side="left", padx=5)

def _on_toggle_hidden(self):
    if self.product.get("is_hidden"):
        product_catalog_service.unhide_product(self.product_id)
    else:
        product_catalog_service.hide_product(self.product_id)
    self._load_product()  # Refresh

def _update_hide_button(self):
    if self.product.get("is_hidden"):
        self.hide_btn.configure(text="Unhide")
    else:
        self.hide_btn.configure(text="Hide")
```

### T061 – Add Delete button with confirmation

**Purpose**: Delete product after dependency check.

**Steps**:
```python
def _setup_buttons(self):
    ...
    self.delete_btn = ctk.CTkButton(
        button_frame,
        text="Delete",
        fg_color="red",
        command=self._on_delete
    )
    self.delete_btn.pack(side="left", padx=5)

def _on_delete(self):
    # Confirm
    if not messagebox.askyesno(
        "Confirm Delete",
        f"Are you sure you want to delete '{self.product['product_name']}'?\n\n"
        "This cannot be undone."
    ):
        return

    try:
        product_catalog_service.delete_product(self.product_id)
        messagebox.showinfo("Deleted", "Product deleted successfully.")
        self.destroy()
    except ValueError as e:
        # Has dependencies - suggest hide
        messagebox.showerror(
            "Cannot Delete",
            f"{str(e)}\n\nWould you like to hide it instead?"
        )
```

### T062 – Create purchase history grid

**Purpose**: Display purchase transactions (FR-012).

**Steps**:
```python
def _setup_history(self):
    # Section header
    ctk.CTkLabel(
        self,
        text="Purchase History",
        font=ctk.CTkFont(size=14, weight="bold")
    ).pack(pady=(10, 5))

    # Treeview for history
    columns = ("date", "supplier", "price", "quantity")
    self.history_tree = ttk.Treeview(self, columns=columns, show="headings", height=8)

    self.history_tree.heading("date", text="Date")
    self.history_tree.heading("supplier", text="Supplier")
    self.history_tree.heading("price", text="Unit Price")
    self.history_tree.heading("quantity", text="Qty")

    self.history_tree.column("date", width=100)
    self.history_tree.column("supplier", width=200)
    self.history_tree.column("price", width=80)
    self.history_tree.column("quantity", width=50)

    scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.history_tree.yview)
    self.history_tree.configure(yscrollcommand=scrollbar.set)

    self.history_tree.pack(fill="both", expand=True, padx=10, pady=5)
    scrollbar.pack(side="right", fill="y")

    # Empty state label
    self.empty_label = ctk.CTkLabel(
        self,
        text="No purchase history for this product.",
        text_color="gray"
    )
```

### T063 – Show empty history message

**Purpose**: Display message when no purchases exist (US-4 Scenario 3).

**Steps**:
```python
def _load_history(self):
    # Clear existing
    for item in self.history_tree.get_children():
        self.history_tree.delete(item)

    # Load history
    history = product_catalog_service.get_purchase_history(self.product_id)

    if not history:
        self.history_tree.pack_forget()
        self.empty_label.pack(pady=20)
    else:
        self.empty_label.pack_forget()
        self.history_tree.pack(fill="both", expand=True, padx=10, pady=5)

        for purchase in history:
            values = (
                purchase.get("purchase_date", ""),
                purchase.get("supplier_name", "Unknown"),
                f"${purchase.get('unit_price', 0):.2f}",
                purchase.get("quantity_purchased", "")
            )
            self.history_tree.insert("", "end", values=values)
```

### T064 – Sort purchase history by date

**Purpose**: Ensure newest purchases appear first (FR-012).

**Steps**:
The sorting is handled by the service layer (`get_purchase_history` returns sorted by date DESC).

Verify in `_load_history`:
```python
# History comes pre-sorted from service (newest first)
# No additional sorting needed here
```

## Test Strategy

**Manual Testing**:
- Double-click product in grid → dialog opens
- Verify all product info displayed correctly
- With purchases: verify history grid shows entries
- Without purchases: verify "No purchase history" message
- Click Edit → AddProductDialog opens in edit mode
- Click Hide → product hidden, button changes to Unhide
- Click Unhide → product unhidden
- Try delete product with purchases → error + hide suggestion
- Delete product without dependencies → success

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Large purchase history | Grid handles scrolling; pagination if needed |
| Stale data after edit | Refresh product data after dialog closes |
| Delete race condition | Single-user app, not a concern |

## Definition of Done Checklist

- [ ] Dialog opens with product data
- [ ] All info fields populated (name, brand, ingredient, category, package, supplier, price)
- [ ] Edit button opens AddProductDialog in edit mode
- [ ] Hide button toggles to Unhide when product hidden
- [ ] Hide/Unhide actually toggles is_hidden
- [ ] Delete confirms before action
- [ ] Delete blocked with appropriate message if dependencies exist
- [ ] Purchase history grid displays when purchases exist
- [ ] "No purchase history" message displays when empty
- [ ] History sorted by date descending (newest first)

## Review Guidance

**Key Checkpoints**:
1. Double-click from grid opens dialog (WP05 integration)
2. All product fields display correctly
3. Hide/Unhide actually toggles state
4. Delete shows dependencies error for products with purchases
5. Purchase history is newest-first

## Activity Log

- 2025-12-22T14:35:00Z – system – lane=planned – Prompt created via /spec-kitty.tasks
