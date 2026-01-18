---
work_package_id: WP03
title: Products Tab Review Queue
lane: "doing"
dependencies: []
subtasks: [T013, T014, T015, T016, T017]
agent: "claude"
history:
- date: '2026-01-17'
  action: created
  agent: claude
estimated_lines: 350
priority: P2
---

# WP03: Products Tab Review Queue

**Feature**: F057 Purchase Management with Provisional Products
**Objective**: Add review queue capabilities to Products tab with badge indicator and filter.

## Implementation Command

```bash
spec-kitty implement WP03 --base WP01
```

## Context

This work package implements User Story 2: Review Provisional Products. After users create provisional products during purchase entry, they need a way to find and complete those products' details. This WP adds a "Needs Review" filter and badge to the existing Products tab.

**Key Design Decisions** (from plan.md):
- Filter + badge in existing Products tab (no new tab)
- Badge shows count to draw attention
- Visual indicator for incomplete fields
- "Mark as Reviewed" action removes from queue

**Reference File**: `src/ui/products_tab.py` (1015 lines)

The Products tab already has:
- Cascading hierarchy filters (L0 -> L1 -> L2)
- Brand and supplier filters
- Search box
- Show Hidden checkbox
- Context menu with Edit/Hide/Delete actions

## Subtasks

### T013: Add "Needs Review" filter option to Products tab filters

**Purpose**: Add a filter that shows only provisional products awaiting review.

**File**: `src/ui/products_tab.py`

**Steps**:

1. Add checkbox in `_create_search()` method (after Show Hidden checkbox):
```python
def _create_search(self):
    """Create search box and filter checkboxes."""
    search_frame = ctk.CTkFrame(self)
    search_frame.grid(row=3, column=0, padx=10, pady=5, sticky="ew")

    # ... existing search label and entry ...

    # Show Hidden checkbox
    self.show_hidden_var = ctk.BooleanVar(value=False)
    self.show_hidden_cb = ctk.CTkCheckBox(
        search_frame,
        text="Show Hidden",
        variable=self.show_hidden_var,
        command=self._on_filter_change,
    )
    self.show_hidden_cb.pack(side="left", padx=20, pady=5)

    # F057: Needs Review checkbox
    self.needs_review_var = ctk.BooleanVar(value=False)
    self.needs_review_cb = ctk.CTkCheckBox(
        search_frame,
        text="Needs Review",
        variable=self.needs_review_var,
        command=self._on_needs_review_change,
    )
    self.needs_review_cb.pack(side="left", padx=10, pady=5)

    # Product count label (move to after checkboxes)
    self.count_label = ctk.CTkLabel(
        search_frame,
        text="",
        font=ctk.CTkFont(size=12),
    )
    self.count_label.pack(side="right", padx=10, pady=5)
```

2. Add handler for the checkbox:
```python
def _on_needs_review_change(self, *args) -> None:
    """Handle Needs Review checkbox change."""
    # Clear other filters when checking Needs Review for focused view
    if self.needs_review_var.get():
        # Save current filters in case user wants to restore
        self._saved_filters = {
            "l0": self.l0_filter_var.get(),
            "l1": self.l1_filter_var.get(),
            "l2": self.l2_filter_var.get(),
            "brand": self.brand_var.get(),
            "supplier": self.supplier_var.get(),
            "search": self.search_var.get(),
        }
        # Clear filters for unobstructed view of provisional products
        self._clear_filters_silent()
    else:
        # Optionally restore previous filters
        pass

    self._load_products()
```

3. Modify `_load_products()` to filter by provisional status:
```python
def _load_products(self):
    """Load and display products based on current filters."""
    # ... existing clear and param building ...

    # F057: Add needs_review filter
    if self.needs_review_var.get():
        # Use dedicated service method for provisional products
        from src.services import product_catalog_service
        try:
            self.products = product_catalog_service.get_provisional_products()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to fetch provisional products: {e}", parent=self)
            self.products = []
    else:
        # Existing product fetch logic
        try:
            self.products = product_catalog_service.get_products(**params)
        except Exception as e:
            # ... existing error handling ...
```

**Validation**:
- [ ] "Needs Review" checkbox appears in filter row
- [ ] Checking it shows only provisional products
- [ ] Unchecking returns to normal product view
- [ ] Count label updates to reflect filtered count

---

### T014: Add provisional count badge to filter area

**Purpose**: Show visual indicator when provisional products exist, drawing user attention.

**File**: `src/ui/products_tab.py`

**Steps**:

1. Add badge widget in `_create_search()` (next to checkbox):
```python
def _create_search(self):
    """Create search box and filter checkboxes."""
    # ... existing code ...

    # F057: Needs Review checkbox with badge
    review_frame = ctk.CTkFrame(search_frame, fg_color="transparent")
    review_frame.pack(side="left", padx=10, pady=5)

    self.needs_review_var = ctk.BooleanVar(value=False)
    self.needs_review_cb = ctk.CTkCheckBox(
        review_frame,
        text="Needs Review",
        variable=self.needs_review_var,
        command=self._on_needs_review_change,
    )
    self.needs_review_cb.pack(side="left")

    # Badge for count
    self.review_badge = ctk.CTkLabel(
        review_frame,
        text="",
        font=ctk.CTkFont(size=10, weight="bold"),
        fg_color="#FF6B35",  # Orange badge
        corner_radius=10,
        width=24,
        height=20,
    )
    # Badge hidden by default, shown when count > 0
```

2. Add method to update badge:
```python
def _update_review_badge(self) -> None:
    """Update the provisional product count badge."""
    from src.services import product_catalog_service

    try:
        count = product_catalog_service.get_provisional_count()
        if count > 0:
            self.review_badge.configure(text=str(count))
            self.review_badge.pack(side="left", padx=(5, 0))
        else:
            self.review_badge.pack_forget()
    except Exception:
        self.review_badge.pack_forget()
```

3. Call badge update in `refresh()` and `_load_products()`:
```python
def refresh(self):
    """Refresh product list and filter dropdowns from database."""
    try:
        # ... existing refresh code ...

        # F057: Update provisional badge
        self._update_review_badge()

    except Exception as e:
        # ... error handling ...

def _load_products(self):
    """Load and display products based on current filters."""
    # ... existing code ...

    # F057: Update badge after loading
    self._update_review_badge()
```

**Validation**:
- [ ] Badge appears when provisional products exist
- [ ] Badge shows correct count
- [ ] Badge hidden when count is 0
- [ ] Badge updates after marking product reviewed
- [ ] Badge updates after creating provisional product (when tab refreshed)

---

### T015: Add visual indicator for incomplete fields in product rows

**Purpose**: Highlight products with missing information to guide user attention.

**File**: `src/ui/products_tab.py`

**Steps**:

1. Add tag configuration for provisional products in `_create_grid()`:
```python
def _create_grid(self):
    """Create the product grid using ttk.Treeview."""
    # ... existing code ...

    # Configure tag for hidden products (grayed out)
    self.tree.tag_configure("hidden", foreground="gray")

    # F057: Configure tag for provisional products
    self.tree.tag_configure("provisional", foreground="#FF6B35")  # Orange text
```

2. Update row insertion to apply provisional tag:
```python
def _load_products(self):
    """Load and display products based on current filters."""
    # ... existing code ...

    for p in self.products:
        # ... existing value building ...

        # Determine tags
        tags = []
        if p.get("is_hidden"):
            tags.append("hidden")
        if p.get("is_provisional"):
            tags.append("provisional")

        self.tree.insert("", "end", iid=str(p["id"]), values=values, tags=tuple(tags))
```

3. Add visual indicator column or prefix for incomplete data:
```python
def _load_products(self):
    # When building values for product row:
    product_name = p.get("product_name", "")

    # F057: Add indicator for provisional products
    if p.get("is_provisional"):
        # Add review icon/indicator to product name
        product_name = f"[REVIEW] {product_name}" if product_name else "[REVIEW]"

    values = (
        hierarchy_path,
        product_name,  # Now includes indicator if provisional
        # ... rest of values
    )
```

**Alternative approach** - add a new column for status:
```python
# In _create_grid(), add status column:
columns = (
    "status",  # F057: New status column
    "hierarchy_path",
    "product_name",
    # ...
)
self.tree.heading("status", text="", anchor="w")  # No header text
self.tree.column("status", width=30, minwidth=30)

# In _load_products(), add status value:
status = "!" if p.get("is_provisional") else ""
values = (status, hierarchy_path, product_name, ...)
```

**Validation**:
- [ ] Provisional products visually distinct from regular products
- [ ] Visual indicator clear and noticeable
- [ ] Hidden products still show gray styling
- [ ] Indicator disappears when product marked as reviewed

---

### T016: Add "Mark as Reviewed" action to product context menu

**Purpose**: Allow user to clear provisional flag from context menu.

**File**: `src/ui/products_tab.py`

**Steps**:

1. Modify `_on_right_click()` to add new menu option for provisional products:
```python
def _on_right_click(self, event):
    """Handle right-click to show context menu."""
    # Identify the row under cursor
    item = self.tree.identify_row(event.y)
    if not item:
        return

    # Select the item
    self.tree.selection_set(item)

    # Get product info
    product = self._get_product_by_id(int(item))
    if not product:
        return

    is_hidden = product.get("is_hidden", False)
    is_provisional = product.get("is_provisional", False)

    # Create context menu
    menu = tk.Menu(self, tearoff=0)
    menu.add_command(label="Edit", command=self._on_edit_product)

    # F057: Add "Mark as Reviewed" for provisional products
    if is_provisional:
        menu.add_command(
            label="Mark as Reviewed",
            command=self._on_mark_reviewed,
        )
        menu.add_separator()

    menu.add_command(
        label="Unhide" if is_hidden else "Hide",
        command=self._on_toggle_hidden,
    )
    menu.add_separator()
    menu.add_command(label="Delete", command=self._on_delete_product)

    # Display menu at cursor position
    try:
        menu.tk_popup(event.x_root, event.y_root)
    finally:
        menu.grab_release()
```

**Validation**:
- [ ] "Mark as Reviewed" appears only for provisional products
- [ ] "Mark as Reviewed" appears before Hide/Delete options
- [ ] Separator separates it from other actions
- [ ] Menu appears at correct position

---

### T017: Wire "Mark as Reviewed" to `mark_product_reviewed()` service

**Purpose**: Implement the handler that clears the provisional flag.

**File**: `src/ui/products_tab.py`

**Steps**:

1. Add handler method:
```python
def _on_mark_reviewed(self) -> None:
    """Mark selected provisional product as reviewed."""
    selection = self.tree.selection()
    if not selection:
        return

    product_id = int(selection[0])
    product = self._get_product_by_id(product_id)
    if not product:
        return

    try:
        from src.services import product_catalog_service

        product_catalog_service.mark_product_reviewed(product_id)

        product_name = product.get("product_name") or product.get("display_name", "Unknown")
        messagebox.showinfo(
            "Success",
            f"'{product_name}' marked as reviewed.",
            parent=self,
        )

        # Refresh to update display
        self._load_products()

    except Exception as e:
        messagebox.showerror(
            "Error",
            f"Failed to mark product as reviewed: {str(e)}",
            parent=self,
        )
```

2. Optionally add keyboard shortcut for quick review:
```python
def _create_grid(self):
    # ... existing bindings ...

    # F057: Add keyboard shortcut for mark reviewed
    self.tree.bind("<r>", self._on_mark_reviewed_shortcut)

def _on_mark_reviewed_shortcut(self, event) -> None:
    """Handle 'r' key to mark selected product as reviewed."""
    selection = self.tree.selection()
    if not selection:
        return

    product = self._get_product_by_id(int(selection[0]))
    if product and product.get("is_provisional"):
        self._on_mark_reviewed()
```

**Validation**:
- [ ] Clicking "Mark as Reviewed" calls service method
- [ ] Success message shows product name
- [ ] Product removed from list when Needs Review filter is active
- [ ] Badge count decrements
- [ ] Visual indicator removed from product row
- [ ] Error shown if service call fails

---

## Definition of Done

- [ ] All 5 subtasks completed
- [ ] "Needs Review" checkbox filters to provisional products only
- [ ] Badge shows count when provisional products exist
- [ ] Badge updates after marking reviewed
- [ ] Provisional products visually distinct in list
- [ ] "Mark as Reviewed" in context menu for provisional products
- [ ] Service method called successfully
- [ ] Manual test: Full workflow from filter to review complete

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Badge not updating | Call `_update_review_badge()` after every relevant action |
| Performance with many provisional | Badge uses efficient count query |
| Confusion about filter interaction | Clear filters when Needs Review checked |
| Visual indicator too subtle | Use orange color and prefix text |

## Reviewer Notes

When reviewing this WP:
1. Test filter combination: Needs Review + Show Hidden
2. Verify badge updates in all scenarios (add, mark, delete)
3. Check keyboard shortcut doesn't conflict with existing bindings
4. Ensure visual styling consistent with existing patterns
5. Test with 0, 1, and many provisional products

## Activity Log

- 2026-01-18T02:16:22Z – claude – lane=doing – Starting implementation of Products Tab Review Queue
