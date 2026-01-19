---
work_package_id: "WP04"
subtasks:
  - "T018"
  - "T019"
  - "T020"
  - "T021"
  - "T022"
  - "T023"
  - "T024"
title: "Material Inventory Display"
phase: "Wave 1 - Core UI"
lane: "done"
assignee: ""
agent: "claude-opus"
shell_pid: "83783"
review_status: "approved"
reviewed_by: "Kent Gale"
dependencies:
  - "WP02"
history:
  - timestamp: "2026-01-18T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP04 - Material Inventory Display

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
# Depends on WP02 (needs list_inventory_items service method)
spec-kitty implement WP04
```

---

## Objectives & Success Criteria

Add Materials section/tab to purchases_tab.py showing MaterialInventoryItem lots. This enables users to:
- View all material inventory with product details
- Sort by any column (date, quantity, cost, etc.)
- Filter by product, date range, and depletion status
- See proper empty state when no inventory exists

**Success Criteria**:
- [ ] Materials tab/section displays MaterialInventoryItem data
- [ ] Columns sortable by clicking headers
- [ ] Cascading filters work correctly
- [ ] Empty state message displays when no items
- [ ] Item count shows accurate totals
- [ ] All tests pass

---

## Context & Constraints

**Feature**: F059 - Materials Purchase Integration & Workflows
**Reference Documents**:
- Spec: `kitty-specs/059-materials-purchase-integration/spec.md`
- Plan: `kitty-specs/059-materials-purchase-integration/plan.md`
- Research: `kitty-specs/059-materials-purchase-integration/research.md`

**Pattern Reference** (from research.md):
- Follow `src/ui/inventory_tab.py` patterns for ttk.Treeview
- Sort by `purchased_at DESC` by default (newest first for user visibility)
- Use re-entry guard pattern for filter cascading

**Key Files**:
- `src/ui/tabs/purchases_tab.py` (modify - add Materials section)
- `src/ui/inventory_tab.py` (reference - patterns)
- `src/services/material_inventory_service.py` (consume - list_inventory_items)

---

## Subtasks & Detailed Guidance

### Subtask T018 - Add Materials Tab/Section Structure

**Purpose**: Create the structural layout for material inventory display.

**Steps**:
1. Open `src/ui/tabs/purchases_tab.py`
2. Add a new section/frame for Materials (may be a tab within purchases or a separate section)
3. Create the basic frame structure:

```python
# Materials Inventory Section
self._materials_frame = ctk.CTkFrame(self)
self._materials_frame.pack(fill="both", expand=True, padx=10, pady=10)

# Header with title
self._materials_header = ctk.CTkLabel(
    self._materials_frame,
    text="Material Inventory",
    font=ctk.CTkFont(size=16, weight="bold")
)
self._materials_header.pack(anchor="w", pady=(0, 10))

# Filter controls frame
self._materials_filter_frame = ctk.CTkFrame(self._materials_frame)
self._materials_filter_frame.pack(fill="x", pady=(0, 10))

# Treeview container (will hold the ttk.Treeview)
self._materials_tree_frame = ctk.CTkFrame(self._materials_frame)
self._materials_tree_frame.pack(fill="both", expand=True)

# Status bar frame
self._materials_status_frame = ctk.CTkFrame(self._materials_frame)
self._materials_status_frame.pack(fill="x", pady=(10, 0))
```

**Files**:
- `src/ui/tabs/purchases_tab.py` (modify)

**Validation**:
- [ ] Frame structure exists and lays out correctly
- [ ] Section is visible in the Purchases tab
- [ ] Layout is responsive to window resizing

---

### Subtask T019 - Create ttk.Treeview with Required Columns

**Purpose**: Set up the data table for displaying inventory items.

**Steps**:
1. Create ttk.Treeview with columns:

```python
import tkinter.ttk as ttk

# Define columns
self._materials_columns = (
    "id", "product", "brand", "date", "qty_purchased",
    "qty_remaining", "cost_per_unit", "value"
)

# Create Treeview
self._materials_tree = ttk.Treeview(
    self._materials_tree_frame,
    columns=self._materials_columns,
    show="headings",
    selectmode="browse"
)

# Configure columns
column_configs = {
    "id": {"width": 50, "anchor": "center", "text": "ID"},
    "product": {"width": 200, "anchor": "w", "text": "Product"},
    "brand": {"width": 120, "anchor": "w", "text": "Brand"},
    "date": {"width": 100, "anchor": "center", "text": "Purchased"},
    "qty_purchased": {"width": 80, "anchor": "e", "text": "Qty Purchased"},
    "qty_remaining": {"width": 80, "anchor": "e", "text": "Qty Remaining"},
    "cost_per_unit": {"width": 80, "anchor": "e", "text": "Cost/Unit"},
    "value": {"width": 80, "anchor": "e", "text": "Value"},
}

for col, config in column_configs.items():
    self._materials_tree.heading(col, text=config["text"])
    self._materials_tree.column(col, width=config["width"], anchor=config["anchor"])

# Add scrollbars
y_scroll = ttk.Scrollbar(self._materials_tree_frame, orient="vertical", command=self._materials_tree.yview)
x_scroll = ttk.Scrollbar(self._materials_tree_frame, orient="horizontal", command=self._materials_tree.xview)
self._materials_tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)

# Grid layout for tree + scrollbars
self._materials_tree.grid(row=0, column=0, sticky="nsew")
y_scroll.grid(row=0, column=1, sticky="ns")
x_scroll.grid(row=1, column=0, sticky="ew")

self._materials_tree_frame.grid_rowconfigure(0, weight=1)
self._materials_tree_frame.grid_columnconfigure(0, weight=1)
```

2. Hide ID column from display (keep for internal reference):
```python
self._materials_tree.column("id", width=0, stretch=False)
```

**Files**:
- `src/ui/tabs/purchases_tab.py` (add to T018 structure)

**Validation**:
- [ ] Treeview displays with all columns
- [ ] Scrollbars work correctly
- [ ] Column headers are visible and readable
- [ ] ID column is hidden but accessible

---

### Subtask T020 - Implement Column Sorting

**Purpose**: Allow users to sort by clicking column headers.

**Steps**:
1. Add sort state tracking:

```python
self._materials_sort_column = "date"
self._materials_sort_reverse = True  # DESC by default (newest first)
```

2. Add click handler for column headers:

```python
def _on_materials_column_click(self, column: str):
    """Handle column header click for sorting."""
    if self._materials_sort_column == column:
        # Toggle direction if same column
        self._materials_sort_reverse = not self._materials_sort_reverse
    else:
        # New column, default to ascending (except date which defaults DESC)
        self._materials_sort_column = column
        self._materials_sort_reverse = column == "date"

    self._refresh_materials_display()
```

3. Bind click handlers to each column:

```python
for col in self._materials_columns:
    self._materials_tree.heading(
        col,
        text=column_configs[col]["text"],
        command=lambda c=col: self._on_materials_column_click(c)
    )
```

4. Add visual indicator for sort direction (optional enhancement):

```python
def _update_sort_indicators(self):
    """Update column headers to show sort direction."""
    for col in self._materials_columns:
        base_text = column_configs[col]["text"]
        if col == self._materials_sort_column:
            indicator = " ▼" if self._materials_sort_reverse else " ▲"
            self._materials_tree.heading(col, text=base_text + indicator)
        else:
            self._materials_tree.heading(col, text=base_text)
```

**Files**:
- `src/ui/tabs/purchases_tab.py` (extend)

**Parallel?**: No - depends on T019

**Validation**:
- [ ] Clicking column header sorts by that column
- [ ] Clicking same column toggles sort direction
- [ ] Sort indicator shows current sort column/direction
- [ ] Date column defaults to descending (newest first)

---

### Subtask T021 - Add Cascading Filters

**Purpose**: Enable filtering by product, date range, and depletion status.

**Steps**:
1. Create filter widgets in filter frame:

```python
# Product filter dropdown
self._materials_product_var = ctk.StringVar(value="All Products")
self._materials_product_dropdown = ctk.CTkComboBox(
    self._materials_filter_frame,
    variable=self._materials_product_var,
    values=["All Products"],  # Populated dynamically
    command=self._on_materials_filter_change,
    width=200
)
self._materials_product_dropdown.pack(side="left", padx=(0, 10))

# Date range filters (optional - start/end date entries)
self._materials_date_from_var = ctk.StringVar()
self._materials_date_to_var = ctk.StringVar()

# Show depleted checkbox
self._materials_show_depleted_var = ctk.BooleanVar(value=False)
self._materials_show_depleted_cb = ctk.CTkCheckBox(
    self._materials_filter_frame,
    text="Show Depleted",
    variable=self._materials_show_depleted_var,
    command=self._on_materials_filter_change
)
self._materials_show_depleted_cb.pack(side="left", padx=(0, 10))

# Clear filters button
self._materials_clear_btn = ctk.CTkButton(
    self._materials_filter_frame,
    text="Clear Filters",
    command=self._clear_materials_filters,
    width=100
)
self._materials_clear_btn.pack(side="right")
```

2. Implement filter change handler with re-entry guard:

```python
def _on_materials_filter_change(self, *args):
    """Handle filter change with re-entry guard."""
    if getattr(self, "_materials_filter_updating", False):
        return
    self._materials_filter_updating = True
    try:
        self._refresh_materials_display()
    finally:
        self._materials_filter_updating = False

def _clear_materials_filters(self):
    """Reset all filters to defaults."""
    self._materials_product_var.set("All Products")
    self._materials_show_depleted_var.set(False)
    self._materials_date_from_var.set("")
    self._materials_date_to_var.set("")
    self._refresh_materials_display()
```

3. Populate product dropdown from service:

```python
def _populate_materials_product_filter(self):
    """Load products for filter dropdown."""
    from src.services.material_catalog_service import list_products
    products = list_products(include_hidden=False)
    product_names = ["All Products"] + [p["name"] for p in products]
    self._materials_product_dropdown.configure(values=product_names)
```

**Files**:
- `src/ui/tabs/purchases_tab.py` (extend filter frame)

**Parallel?**: Yes - can develop alongside T022

**Validation**:
- [ ] Product dropdown filters to selected product
- [ ] Show Depleted checkbox shows/hides zero-quantity items
- [ ] Clear Filters resets all filters
- [ ] Filters cascade correctly (no infinite loops)

---

### Subtask T022 - Implement Item Count Display

**Purpose**: Show total count of displayed items in status bar.

**Steps**:
1. Add status label to status frame:

```python
self._materials_count_label = ctk.CTkLabel(
    self._materials_status_frame,
    text="0 items",
    font=ctk.CTkFont(size=12)
)
self._materials_count_label.pack(side="left")
```

2. Update count after each refresh:

```python
def _update_materials_count(self, count: int, total: int = None):
    """Update the item count display."""
    if total is not None and total != count:
        text = f"{count} of {total} items"
    else:
        text = f"{count} item{'s' if count != 1 else ''}"
    self._materials_count_label.configure(text=text)
```

3. Call from refresh method:

```python
# At end of _refresh_materials_display()
displayed_count = len(self._materials_tree.get_children())
self._update_materials_count(displayed_count)
```

**Files**:
- `src/ui/tabs/purchases_tab.py` (extend status frame)

**Parallel?**: Yes - can develop alongside T021

**Validation**:
- [ ] Count updates when data loads
- [ ] Count updates when filters change
- [ ] Singular/plural grammar correct ("1 item" vs "2 items")

---

### Subtask T023 - Add Empty State Message

**Purpose**: Display helpful message when no inventory items exist.

**Steps**:
1. Create empty state overlay:

```python
self._materials_empty_label = ctk.CTkLabel(
    self._materials_tree_frame,
    text="No material inventory items.\nPurchase materials to see them here.",
    font=ctk.CTkFont(size=14),
    text_color="gray"
)
```

2. Show/hide based on data:

```python
def _show_materials_empty_state(self, show: bool):
    """Show or hide the empty state message."""
    if show:
        # Hide treeview, show empty message
        self._materials_tree.grid_remove()
        self._materials_empty_label.place(relx=0.5, rely=0.5, anchor="center")
    else:
        # Show treeview, hide empty message
        self._materials_empty_label.place_forget()
        self._materials_tree.grid()
```

3. Call from refresh method:

```python
# At end of _refresh_materials_display()
if len(items) == 0:
    self._show_materials_empty_state(True)
else:
    self._show_materials_empty_state(False)
```

**Files**:
- `src/ui/tabs/purchases_tab.py` (extend)

**Validation**:
- [ ] Empty state shows when no items exist
- [ ] Empty state hides when items are loaded
- [ ] Message is centered and readable

---

### Subtask T024 - Wire Up Data Loading

**Purpose**: Connect UI to MaterialInventoryService for data.

**Steps**:
1. Create the main refresh method:

```python
def _refresh_materials_display(self):
    """Load and display material inventory items."""
    from src.services.material_inventory_service import list_inventory_items

    # Build filter parameters
    product_filter = self._materials_product_var.get()
    product_id = None
    if product_filter != "All Products":
        # Look up product ID by name
        product_id = self._get_product_id_by_name(product_filter)

    include_depleted = self._materials_show_depleted_var.get()

    # Fetch data from service
    items = list_inventory_items(
        product_id=product_id,
        include_depleted=include_depleted
    )

    # Apply local sorting
    sort_key = self._get_sort_key_for_column(self._materials_sort_column)
    items.sort(key=sort_key, reverse=self._materials_sort_reverse)

    # Clear existing items
    for item in self._materials_tree.get_children():
        self._materials_tree.delete(item)

    # Insert new items
    for item in items:
        values = (
            item["id"],
            item.get("product_name", "Unknown"),
            item.get("brand", ""),
            item.get("purchased_at", "").strftime("%Y-%m-%d") if item.get("purchased_at") else "",
            f"{item['quantity_purchased']:.2f}",
            f"{item['quantity_remaining']:.2f}",
            f"${item['cost_per_unit']:.4f}",
            f"${item['quantity_remaining'] * item['cost_per_unit']:.2f}",
        )
        self._materials_tree.insert("", "end", values=values)

    # Update UI state
    self._show_materials_empty_state(len(items) == 0)
    self._update_materials_count(len(items))
    self._update_sort_indicators()
```

2. Helper for sort key:

```python
def _get_sort_key_for_column(self, column: str):
    """Return a sort key function for the given column."""
    key_map = {
        "id": lambda x: x.get("id", 0),
        "product": lambda x: x.get("product_name", "").lower(),
        "brand": lambda x: x.get("brand", "").lower(),
        "date": lambda x: x.get("purchased_at") or datetime.min,
        "qty_purchased": lambda x: x.get("quantity_purchased", 0),
        "qty_remaining": lambda x: x.get("quantity_remaining", 0),
        "cost_per_unit": lambda x: x.get("cost_per_unit", 0),
        "value": lambda x: x.get("quantity_remaining", 0) * x.get("cost_per_unit", 0),
    }
    return key_map.get(column, lambda x: 0)
```

3. Call refresh on tab activation and initialization:

```python
def __init__(self, parent, ...):
    # ... existing init code ...
    self._populate_materials_product_filter()
    self._refresh_materials_display()
```

**Files**:
- `src/ui/tabs/purchases_tab.py` (complete integration)

**Validation**:
- [ ] Data loads from service on initialization
- [ ] Filters correctly reduce displayed items
- [ ] Sorting works on all columns
- [ ] Values format correctly (dates, decimals, currency)

---

## Test Strategy

Run tests with:
```bash
./run-tests.sh src/tests/ui/test_purchases_tab.py -v
```

Manual testing:
1. Open app, navigate to Purchases tab
2. Verify Materials section displays
3. Add material purchase, verify it appears in list
4. Test sorting by each column
5. Test filters (product, show depleted)
6. Verify empty state when no items

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| ttk.Treeview styling mismatch | Use ttk.Style to match CustomTkinter theme |
| Filter cascade loops | Re-entry guard pattern prevents infinite loops |
| Performance with large datasets | ttk.Treeview handles thousands of rows well |

---

## Definition of Done Checklist

- [ ] T018: Materials section structure added to purchases_tab
- [ ] T019: ttk.Treeview created with all columns
- [ ] T020: Column sorting implemented (click headers)
- [ ] T021: Cascading filters working (product, depleted)
- [ ] T022: Item count display updates correctly
- [ ] T023: Empty state message shows when appropriate
- [ ] T024: Data loading wired to MaterialInventoryService
- [ ] Manual testing passes all scenarios
- [ ] tasks.md updated with status change

---

## Review Guidance

- Verify sort order: newest first by default (purchased_at DESC)
- Check filter behavior: "All Products" shows all, checkbox controls depleted
- Ensure empty state is user-friendly (not just blank)
- Verify currency formatting matches rest of app

---

## Activity Log

- 2026-01-18T00:00:00Z - system - lane=planned - Prompt created.
- 2026-01-19T01:24:22Z – claude-opus – shell_pid=81785 – lane=doing – Started implementation via workflow command
- 2026-01-19T01:29:27Z – claude-opus – shell_pid=81785 – lane=for_review – Ready for review: Material Inventory tab with treeview, sorting, filters, item count, empty state. list_inventory_items service method added. 51 tests passing.
- 2026-01-19T01:31:31Z – claude-opus – shell_pid=83783 – lane=doing – Started review via workflow command
- 2026-01-19T01:32:34Z – claude-opus – shell_pid=83783 – lane=done – Review passed: Material Inventory tab implemented with treeview, sorting, filters, item count, empty state. list_inventory_items service added. 51 tests passing.
