---
work_package_id: "WP02"
subtasks:
  - "T008"
  - "T009"
  - "T010"
  - "T011"
  - "T012"
  - "T013"
  - "T014"
  - "T015"
title: "Purchases Tab - List & Filters"
phase: "Phase 2 - Core UI"
lane: "done"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-08T22:30:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP02 - Purchases Tab - List & Filters

## Objectives & Success Criteria

Create the `PurchasesTab` component with:
- Purchase list view (ttk.Treeview with 7 columns)
- Filter controls (date range, supplier, search)
- Column sorting
- Context menu for actions
- Integration into PurchaseDashboard

**Success Criteria**:
- Navigate to PURCHASE mode → Purchases tab is visible
- List displays purchases with all columns (Date, Product, Supplier, Qty, Price, Total, Remaining)
- Filters work: date range dropdown, supplier dropdown, search box
- Clicking column header sorts the list
- Context menu shows Edit, Delete, View Details options
- At least 20 rows visible without scrolling

## Context & Constraints

**Reference Documents**:
- `kitty-specs/042-purchases-tab-crud-operations/research.md` - InventoryTab pattern
- `kitty-specs/042-purchases-tab-crud-operations/plan.md` - UI structure

**Pattern Reference**: Follow `src/ui/inventory_tab.py` structure exactly

**Key Constraints**:
- Default date range: "Last 30 days"
- Grid row 2 (content) must have weight=1 for expansion
- Use ttk.Treeview for performance with 500+ rows

## Subtasks & Detailed Guidance

### Subtask T008 - Create PurchasesTab Class Structure

**Purpose**: Establish the base frame and grid configuration.

**Steps**:
1. Create `src/ui/tabs/purchases_tab.py`
2. Import dependencies:
   ```python
   import customtkinter as ctk
   from tkinter import ttk
   from typing import Optional, List, Dict
   from src.services.purchase_service import PurchaseService
   ```
3. Create class:
   ```python
   class PurchasesTab(ctk.CTkFrame):
       def __init__(self, parent):
           super().__init__(parent)

           # State
           self.purchases: List[Dict] = []
           self.filtered_purchases: List[Dict] = []
           self._data_loaded = False
           self._sort_column = "purchase_date"
           self._sort_reverse = True

           # Grid configuration
           self.grid_columnconfigure(0, weight=1)
           self.grid_rowconfigure(0, weight=0)  # Header
           self.grid_rowconfigure(1, weight=0)  # Controls
           self.grid_rowconfigure(2, weight=1)  # Content (expands)

           self._create_header()
           self._create_controls()
           self._create_purchase_list()
   ```

**Files**: `src/ui/tabs/purchases_tab.py`
**Parallel?**: No (foundation for other subtasks)

### Subtask T009 - Implement Header Section

**Purpose**: Title and subtitle for the tab.

**Steps**:
1. Add `_create_header()` method:
   ```python
   def _create_header(self):
       header_frame = ctk.CTkFrame(self, fg_color="transparent")
       header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))

       title = ctk.CTkLabel(
           header_frame,
           text="Purchase History",
           font=ctk.CTkFont(size=20, weight="bold")
       )
       title.pack(anchor="w")

       subtitle = ctk.CTkLabel(
           header_frame,
           text="View, add, and manage your purchases",
           font=ctk.CTkFont(size=12),
           text_color="gray"
       )
       subtitle.pack(anchor="w")
   ```

**Files**: `src/ui/tabs/purchases_tab.py`
**Parallel?**: Yes (independent section)

### Subtask T010 - Implement Filter Controls

**Purpose**: Date range, supplier filter, and search box.

**Steps**:
1. Add `_create_controls()` method with controls frame
2. Add "Add Purchase" button (left side):
   ```python
   add_btn = ctk.CTkButton(
       controls_frame,
       text="+ Add Purchase",
       command=self._on_add_purchase
   )
   ```
3. Add date range dropdown (options: "Last 30 days", "Last 90 days", "Last year", "All time"):
   ```python
   self.date_range_var = ctk.StringVar(value="Last 30 days")
   date_dropdown = ctk.CTkOptionMenu(
       controls_frame,
       variable=self.date_range_var,
       values=["Last 30 days", "Last 90 days", "Last year", "All time"],
       command=self._on_filter_change
   )
   ```
4. Add supplier dropdown (populated from SupplierService):
   ```python
   self.supplier_var = ctk.StringVar(value="All")
   # Populate with ["All"] + [supplier.name for supplier in suppliers]
   ```
5. Add search entry with KeyRelease binding:
   ```python
   self.search_var = ctk.StringVar()
   search_entry = ctk.CTkEntry(
       controls_frame,
       placeholder_text="Search products...",
       textvariable=self.search_var
   )
   search_entry.bind("<KeyRelease>", self._on_filter_change)
   ```

**Files**: `src/ui/tabs/purchases_tab.py`
**Parallel?**: Yes (independent section)

### Subtask T011 - Implement Treeview List

**Purpose**: Main purchase list with columns.

**Steps**:
1. Add `_create_purchase_list()` method
2. Create Treeview with columns:
   ```python
   columns = ("date", "product", "supplier", "qty", "price", "total", "remaining")
   self.tree = ttk.Treeview(
       list_frame,
       columns=columns,
       show="headings",
       selectmode="browse"
   )
   ```
3. Configure column headings and widths:
   - Date: 100px
   - Product: 200px
   - Supplier: 120px
   - Qty: 60px (right-align)
   - Unit Price: 80px (right-align)
   - Total: 80px (right-align)
   - Remaining: 80px (right-align)
4. Add scrollbar:
   ```python
   scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
   self.tree.configure(yscrollcommand=scrollbar.set)
   ```
5. Bind selection and double-click events

**Files**: `src/ui/tabs/purchases_tab.py`
**Parallel?**: No (depends on T008)

### Subtask T012 - Implement Sorting Logic

**Purpose**: Sort by clicking column headers.

**Steps**:
1. Add heading click binding for each column:
   ```python
   for col in columns:
       self.tree.heading(col, text=col_titles[col], command=lambda c=col: self._sort_by_column(c))
   ```
2. Implement `_sort_by_column()`:
   ```python
   def _sort_by_column(self, column: str):
       if self._sort_column == column:
           self._sort_reverse = not self._sort_reverse
       else:
           self._sort_column = column
           self._sort_reverse = False
       self._apply_sort()
       self._refresh_tree()
   ```
3. Implement `_apply_sort()` to sort `filtered_purchases` by column

**Files**: `src/ui/tabs/purchases_tab.py`
**Parallel?**: No (depends on T011)

### Subtask T013 - Implement Filter Application

**Purpose**: Apply all filters when any changes.

**Steps**:
1. Implement `_on_filter_change()`:
   ```python
   def _on_filter_change(self, *args):
       date_range = self._map_date_range(self.date_range_var.get())
       supplier_id = self._get_supplier_id(self.supplier_var.get())
       search = self.search_var.get().strip() or None

       self.purchases = PurchaseService().get_purchases_filtered(
           date_range=date_range,
           supplier_id=supplier_id,
           search_query=search
       )
       self.filtered_purchases = self.purchases.copy()
       self._apply_sort()
       self._refresh_tree()
   ```
2. Map display values to service parameters:
   - "Last 30 days" → "last_30_days"
   - "All" → None (supplier_id)
3. Implement `_refresh_tree()` to clear and repopulate

**Files**: `src/ui/tabs/purchases_tab.py`
**Parallel?**: No (depends on T011)

### Subtask T014 - Add Context Menu

**Purpose**: Right-click menu with Edit, Delete, View Details.

**Steps**:
1. Create context menu:
   ```python
   self.context_menu = tk.Menu(self, tearoff=0)
   self.context_menu.add_command(label="View Details", command=self._on_view_details)
   self.context_menu.add_command(label="Edit", command=self._on_edit)
   self.context_menu.add_separator()
   self.context_menu.add_command(label="Delete", command=self._on_delete)
   ```
2. Bind right-click:
   ```python
   self.tree.bind("<Button-3>", self._show_context_menu)  # Right-click
   self.tree.bind("<Button-2>", self._show_context_menu)  # macOS
   ```
3. Implement `_show_context_menu()`:
   - Select row under cursor
   - Show menu at cursor position
4. Add placeholder handlers (implemented in later WPs):
   ```python
   def _on_view_details(self):
       pass  # WP06

   def _on_edit(self):
       pass  # WP04

   def _on_delete(self):
       pass  # WP05
   ```

**Files**: `src/ui/tabs/purchases_tab.py`
**Parallel?**: No (depends on T011)

### Subtask T015 - Dashboard Integration

**Purpose**: Add Purchases tab to PurchaseDashboard.

**Steps**:
1. Open `src/ui/dashboards/purchase_dashboard.py`
2. Add import:
   ```python
   from src.ui.tabs.purchases_tab import PurchasesTab
   ```
3. In the tabview setup, add Purchases tab:
   ```python
   self.purchases_tab_frame = self.tabview.add("Purchases")
   self.purchases_tab = PurchasesTab(self.purchases_tab_frame)
   self.purchases_tab.pack(fill="both", expand=True)
   ```
4. Ensure tab order: Inventory, Purchases, Shopping Lists

**Files**: `src/ui/dashboards/purchase_dashboard.py`
**Parallel?**: No (integration)

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Filter changes cause lag | Debounce search input; use efficient queries |
| Empty state confusion | Show helpful message when no purchases |
| Column width issues | Set minwidth on columns; allow resize |

## Definition of Done Checklist

- [ ] PurchasesTab class created
- [ ] Header displays title and subtitle
- [ ] All 3 filter controls work (date range, supplier, search)
- [ ] Treeview shows 7 columns with correct widths
- [ ] Column sorting works (click header to toggle)
- [ ] Context menu appears on right-click
- [ ] Tab integrated into PurchaseDashboard
- [ ] Empty state shows guidance message
- [ ] At least 20 rows visible without scrolling

## Review Guidance

- Verify grid expansion works (resize window, list should expand)
- Check filter combinations work together
- Verify sorting toggles ascending/descending
- Test with empty database (empty state message)
- Test with 50+ purchases (performance)

## Activity Log

- 2026-01-08T22:30:00Z - system - lane=planned - Prompt created.
- 2026-01-09T03:39:23Z – agent – lane=doing – Started implementation via workflow command
- 2026-01-09T03:46:55Z – unknown – lane=for_review – PurchasesTab implemented with all 8 subtasks: header, filter controls, treeview, sorting, filter application, context menu, dashboard integration. All 45 tests pass.
- 2026-01-09T04:58:09Z – agent – lane=doing – Started review via workflow command
- 2026-01-09T04:58:29Z – unknown – lane=done – Review passed: PurchasesTab with header, controls, treeview, sorting, filters, context menu all implemented
