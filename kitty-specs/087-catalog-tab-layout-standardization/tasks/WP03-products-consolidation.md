---
work_package_id: WP03
title: ProductsTab Row Consolidation
lane: "done"
dependencies: [WP01]
base_branch: 087-catalog-tab-layout-standardization-WP01
base_commit: 3fa9a8a9fe5337dea329dbf424521b0b5b73b4bd
created_at: '2026-01-31T02:55:03.282525+00:00'
subtasks:
- T012
- T013
- T014
- T015
- T016
phase: Phase 2 - Layout Standardization
assignee: ''
agent: ''
shell_pid: "7638"
review_status: "approved"
reviewed_by: "Kent Gale"
history:
- timestamp: '2026-01-31T02:38:50Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP03 – ProductsTab Row Consolidation

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.

---

## Review Feedback

> **Populated by `/spec-kitty.review`**

*[This section is empty initially.]*

---

## Implementation Command

```bash
spec-kitty implement WP03 --base WP01
```

---

## Objectives & Success Criteria

**Primary Objective**: Remove "Product Catalog" header and consolidate 5 control rows into 3 rows.

**Success Criteria**:
1. No "Product Catalog" title visible
2. All filters + search in a single row (row 0)
3. Add Product button + Show Hidden/Needs Review in row 1
4. Data grid fills remaining space (row 2)
5. All filter dropdowns work (L0, L1, L2, Brand, Supplier)
6. Search works
7. Add Product, Show Hidden, Needs Review all work

---

## Context & Constraints

**Reference Files**:
- `src/ui/products_tab.py` - Target file (1152 lines)
- `kitty-specs/087-catalog-tab-layout-standardization/research.md` - Pattern documentation

**Current State** (5 rows):
- Row 0: Header with "Product Catalog" title ← REMOVE
- Row 1: Toolbar with "Add Product" button
- Row 2: Filters (L0, L1, L2, Brand, Supplier, Clear)
- Row 3: Search + Show Hidden + Needs Review + count
- Row 4: Data grid (ttk.Treeview)

**Target State** (3 rows):
- Row 0: All filters + search (consolidated)
- Row 1: Add Product button + Show Hidden + Needs Review + count
- Row 2: Data grid (weight=1)

---

## Subtasks & Detailed Guidance

### Subtask T012 – Remove "Product Catalog" Header

**Purpose**: Eliminate redundant title that wastes vertical space.

**Steps**:
1. Locate `_create_header()` method (lines 82-93):
   ```python
   def _create_header(self):
       """Create the header with title."""
       header_frame = ctk.CTkFrame(self)
       header_frame.grid(row=0, column=0, padx=10, pady=(10, 0), sticky="ew")
       ...
   ```
2. Delete the entire `_create_header()` method
3. Remove the call to `self._create_header()` in `__init__()` (around line 66)

**Files**: `src/ui/products_tab.py`

---

### Subtask T013 – Merge Toolbar + Filters + Search into 2 Rows

**Purpose**: Consolidate controls for compact layout.

**New Layout Design**:
- **Row 0**: All filter dropdowns + search entry
  - Category (L0) | Subcategory (L1) | Ingredient (L2) | Brand | Supplier | Clear | Search
- **Row 1**: Action buttons + checkboxes + count
  - Add Product | Show Hidden | Needs Review (badge) | Count label

**Steps**:

1. **Merge `_create_filters()` and `_create_search()` into single frame for row 0**:

   Rewrite `_create_filters()` to include search:
   ```python
   def _create_filters(self):
       """Create filter controls and search in a single row."""
       filter_frame = ctk.CTkFrame(self)
       filter_frame.grid(row=0, column=0, padx=10, pady=5, sticky="ew")

       # L0 (Category) filter
       l0_label = ctk.CTkLabel(filter_frame, text="Category:")
       l0_label.pack(side="left", padx=(5, 2), pady=5)
       # ... (keep existing L0 dropdown code)

       # L1 (Subcategory) filter
       # ... (keep existing L1 dropdown code)

       # L2 (Ingredient) filter
       # ... (keep existing L2 dropdown code)

       # Brand filter
       # ... (keep existing Brand dropdown code)

       # Supplier filter
       # ... (keep existing Supplier dropdown code)

       # Clear button
       # ... (keep existing Clear button code)

       # MOVE Search entry here (from _create_search)
       search_label = ctk.CTkLabel(filter_frame, text="Search:")
       search_label.pack(side="left", padx=(15, 2), pady=5)

       self.search_var = ctk.StringVar()
       self.search_var.trace_add("write", self._on_search_change)
       self.search_entry = ctk.CTkEntry(
           filter_frame,
           textvariable=self.search_var,
           width=150,  # Reduce width to fit
           placeholder_text="Search...",
       )
       self.search_entry.pack(side="left", padx=5, pady=5)
   ```

2. **Rewrite `_create_toolbar()` to include checkboxes and count (row 1)**:
   ```python
   def _create_toolbar(self):
       """Create toolbar with action buttons, checkboxes, and count."""
       toolbar_frame = ctk.CTkFrame(self)
       toolbar_frame.grid(row=1, column=0, padx=10, pady=5, sticky="ew")

       # Add Product button (existing)
       self.add_btn = ctk.CTkButton(
           toolbar_frame,
           text="Add Product",
           command=self._on_add_product,
           width=120,
       )
       self.add_btn.pack(side="left", padx=5, pady=5)

       # MOVE Show Hidden checkbox here (from _create_search)
       self.show_hidden_var = ctk.BooleanVar(value=False)
       self.show_hidden_cb = ctk.CTkCheckBox(
           toolbar_frame,
           text="Show Hidden",
           variable=self.show_hidden_var,
           command=self._on_filter_change,
       )
       self.show_hidden_cb.pack(side="left", padx=15, pady=5)

       # MOVE Needs Review checkbox + badge here (from _create_search)
       review_frame = ctk.CTkFrame(toolbar_frame, fg_color="transparent")
       review_frame.pack(side="left", padx=10, pady=5)

       self.needs_review_var = ctk.BooleanVar(value=False)
       self.needs_review_cb = ctk.CTkCheckBox(
           review_frame,
           text="Needs Review",
           variable=self.needs_review_var,
           command=self._on_needs_review_change,
       )
       self.needs_review_cb.pack(side="left")

       self.review_badge = ctk.CTkLabel(
           review_frame,
           text="",
           font=ctk.CTkFont(size=10, weight="bold"),
           fg_color="#FF6B35",
           text_color="white",
           corner_radius=10,
           width=24,
           height=20,
       )
       # Badge shown conditionally in _update_review_badge()

       # MOVE Product count label here (from _create_search)
       self.count_label = ctk.CTkLabel(
           toolbar_frame,
           text="",
           font=ctk.CTkFont(size=12),
       )
       self.count_label.pack(side="right", padx=10, pady=5)
   ```

3. **Delete `_create_search()` method entirely** (its contents moved to other methods)

4. **Update `__init__()` to remove `_create_search()` call and update order**:
   ```python
   # Create UI components
   self._create_filters()   # Row 0 - filters + search
   self._create_toolbar()   # Row 1 - buttons + checkboxes
   self._create_grid()      # Row 2 - data grid
   ```

**Files**: `src/ui/products_tab.py`

---

### Subtask T014 – Update Grid Row Indices

**Purpose**: Adjust row numbers for the new 3-row layout.

**Steps**:
1. `_create_filters()`: Already uses row=0 (keep as is after consolidation)
2. `_create_toolbar()`: Change to `row=1`
3. `_create_grid()`: Change `grid_container.grid(row=4, ...)` to `row=2`

**Mapping**:
| Component | Old Row | New Row |
|-----------|---------|---------|
| Filters + Search | 2, 3 | 0 |
| Toolbar + Checkboxes | 1 | 1 |
| Grid | 4 | 2 |

**Files**: `src/ui/products_tab.py`

---

### Subtask T015 – Update grid_rowconfigure Calls

**Purpose**: Set proper weights for 3-row layout.

**Steps**:
1. Locate grid configuration in `__init__()` (around lines 58-64)
2. Update from:
   ```python
   self.grid_rowconfigure(0, weight=0)  # Header
   self.grid_rowconfigure(1, weight=0)  # Toolbar
   self.grid_rowconfigure(2, weight=0)  # Filters
   self.grid_rowconfigure(3, weight=0)  # Search
   self.grid_rowconfigure(4, weight=1)  # Grid
   ```
3. To:
   ```python
   self.grid_rowconfigure(0, weight=0)  # Filters + Search (fixed)
   self.grid_rowconfigure(1, weight=0)  # Toolbar + Checkboxes (fixed)
   self.grid_rowconfigure(2, weight=1)  # Grid (expandable)
   ```

**Files**: `src/ui/products_tab.py`

---

### Subtask T016 – Reduce Vertical Padding

**Purpose**: Create compact, consistent spacing.

**Steps**:
1. Use `pady=5` or `PADDING_MEDIUM` consistently
2. Check these locations:
   - `filter_frame.grid(row=0, ..., pady=5, ...)`
   - `toolbar_frame.grid(row=1, ..., pady=5, ...)`
   - `grid_container.grid(row=2, ..., pady=5, ...)`

**Files**: `src/ui/products_tab.py`

---

## Test Strategy

Manual verification:
1. No "Product Catalog" title visible
2. All filters appear in single row with search
3. Add Product button visible with checkboxes
4. Each filter dropdown works (L0 cascades to L1, L1 cascades to L2)
5. Search filters results
6. Show Hidden toggles correctly
7. Needs Review filter works with badge
8. Window resize expands only the grid

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Too many controls for one row | Use smaller widths, test on target resolution |
| Lost checkbox/badge logic | Move code carefully, verify badge updates |
| Filter cascade breaks | Test L0→L1→L2 cascade after changes |

---

## Definition of Done Checklist

- [ ] "Product Catalog" header removed
- [ ] `_create_header()` method deleted
- [ ] `_create_search()` method merged and deleted
- [ ] Filters + Search in row 0
- [ ] Toolbar + Checkboxes + Count in row 1
- [ ] Grid in row 2
- [ ] grid_rowconfigure updated for 3 rows
- [ ] All filter cascades work
- [ ] Search, Add, Show Hidden, Needs Review all work
- [ ] `tasks.md` updated with status change

---

## Review Guidance

**Key checkpoints**:
1. No title visible
2. All controls visible and functional
3. Filter cascade works (L0→L1→L2)
4. Grid expands on resize

---

## Activity Log

- 2026-01-31T02:38:50Z – system – lane=planned – Prompt created.
- 2026-01-31T03:02:54Z – unknown – shell_pid=7638 – lane=for_review – ProductsTab consolidated to 3-row layout
- 2026-01-31T03:03:53Z – unknown – shell_pid=7638 – lane=done – Review passed
