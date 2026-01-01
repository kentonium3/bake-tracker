---
work_package_id: "WP04"
subtasks:
  - "T020"
  - "T021"
  - "T022"
  - "T023"
  - "T024"
  - "T025"
title: "Products Tab Hierarchy"
phase: "Phase 2 - Products Tab"
lane: "for_review"
assignee: ""
agent: "claude"
shell_pid: "35513"
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-31T23:59:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP04 - Products Tab Hierarchy

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

**Goal**: Add hierarchy path display and cascading hierarchy filters to the Products tab.

**Success Criteria**:
- Products grid shows full ingredient hierarchy path (L0 -> L1 -> L2)
- Deprecated category filter removed
- Cascading hierarchy filters (L0 -> L1 -> L2) work correctly
- Selecting L0 shows all products using ingredients under that hierarchy
- Column widths accommodate hierarchy path display

**User Story**: US4 - Filter Products by Ingredient Hierarchy

---

## Context & Constraints

**Reference Documents**:
- Spec: `kitty-specs/032-complete-f031-hierarchy/spec.md` (FR-013, FR-014, FR-015)
- Plan: `kitty-specs/032-complete-f031-hierarchy/plan.md`

**Key Service Functions**:
```python
from src.services import ingredient_hierarchy_service

# Get hierarchy path for display
ancestors = ingredient_hierarchy_service.get_ancestors(ingredient_id)
# Build path: "L0 -> L1 -> L2"

# Get root categories for L0 filter
categories = ingredient_hierarchy_service.get_root_ingredients()

# Get children for cascading filters
subcategories = ingredient_hierarchy_service.get_children(l0_id)
leaves = ingredient_hierarchy_service.get_children(l1_id)
```

**File to Modify**: `src/ui/products_tab.py`

**Dependencies**: Phase 1 complete (WP01-WP03) for pattern consistency

---

## Subtasks & Detailed Guidance

### Subtask T020 - Add Hierarchy Path Column

**Purpose**: Display full ingredient hierarchy path in products grid.

**Steps**:
1. Find column configuration in `products_tab.py`
2. Add or modify "Ingredient" column to show hierarchy path
3. Set appropriate column width (~250px for full path)
4. Position column appropriately in grid

**Files**: `src/ui/products_tab.py` - column configuration section

---

### Subtask T021 - Build Path Display Helper

**Purpose**: Create helper function to build "L0 -> L1 -> L2" display string.

**Steps**:
1. Create method `_get_hierarchy_path(ingredient_id) -> str`
2. Call `get_ancestors(ingredient_id)`
3. Get ingredient's own name
4. Build path string from ancestors and name
5. Return formatted path

**Implementation**:
```python
def _get_hierarchy_path(self, ingredient_id: int) -> str:
    """Build hierarchy path string like 'Chocolate -> Dark -> Chips'."""
    if not ingredient_id:
        return "--"

    ingredient = ingredient_service.get_ingredient(ingredient_id)
    if not ingredient:
        return "--"

    ancestors = ingredient_hierarchy_service.get_ancestors(ingredient_id)

    # Build path from root to leaf
    path_parts = []

    # Add ancestors in reverse order (root first)
    for ancestor in reversed(ancestors):
        path_parts.append(ancestor.get("display_name", "?"))

    # Add the ingredient itself
    path_parts.append(ingredient.get("display_name", "?"))

    return " -> ".join(path_parts)
```

**Files**: `src/ui/products_tab.py`

**Notes**: Consider caching if performance is an issue with many products.

---

### Subtask T022 - Remove Category Filter

**Purpose**: Remove the deprecated category filter from Products tab.

**Steps**:
1. Find category filter dropdown in products tab
2. Remove the widget and its label
3. Remove category-related event handlers
4. Remove category filtering logic

**Files**: `src/ui/products_tab.py` - filter UI section

---

### Subtask T023 - Add Cascading Hierarchy Filters

**Purpose**: Add L0 -> L1 -> L2 cascading filter dropdowns.

**Steps**:
1. Add L0 filter dropdown (populated from `get_root_ingredients()`)
2. Add L1 filter dropdown (initially disabled, cascades from L0)
3. Add L2 filter dropdown (initially disabled, cascades from L1)
4. Add "All" option as first choice in each dropdown
5. Implement cascade event handlers

**Implementation**:
```python
# L0 Filter
categories = ingredient_hierarchy_service.get_root_ingredients()
self.categories_map = {cat["display_name"]: cat for cat in categories}
l0_values = ["All Categories"] + sorted(self.categories_map.keys())

self.l0_filter_var = ctk.StringVar(value="All Categories")
self.l0_filter = ctk.CTkComboBox(
    filter_frame,
    values=l0_values,
    variable=self.l0_filter_var,
    command=self._on_l0_filter_change
)

# L1 Filter (initially disabled)
self.l1_filter_var = ctk.StringVar(value="All Subcategories")
self.l1_filter = ctk.CTkComboBox(
    filter_frame,
    values=["All Subcategories"],
    variable=self.l1_filter_var,
    state="disabled",
    command=self._on_l1_filter_change
)

# L2 Filter (initially disabled)
self.l2_filter_var = ctk.StringVar(value="All Ingredients")
self.l2_filter = ctk.CTkComboBox(
    filter_frame,
    values=["All Ingredients"],
    variable=self.l2_filter_var,
    state="disabled",
    command=self._apply_filters
)
```

**Files**: `src/ui/products_tab.py` - filter UI section

---

### Subtask T024 - Implement Filter Logic

**Purpose**: Filter products based on selected hierarchy levels.

**Steps**:
1. Create `_on_l0_filter_change()` handler:
   - If "All Categories", disable L1/L2, reset to All
   - Otherwise, populate L1 with children, enable it, reset L2
2. Create `_on_l1_filter_change()` handler:
   - If "All Subcategories", disable L2, reset to All
   - Otherwise, populate L2 with children, enable it
3. Update `_apply_filters()` to filter by selected hierarchy:
   - L0 selected: Show products where ingredient is under that L0
   - L1 selected: Show products where ingredient is under that L1
   - L2 selected: Show products where ingredient matches that L2

**Implementation**:
```python
def _apply_filters(self, *args):
    filtered_products = self.products

    # Get selected filters
    l0_val = self.l0_filter_var.get()
    l1_val = self.l1_filter_var.get()
    l2_val = self.l2_filter_var.get()

    # Build set of matching ingredient IDs
    matching_ingredient_ids = None

    if l2_val != "All Ingredients" and l2_val in self.leaves_map:
        # Exact ingredient match
        matching_ingredient_ids = {self.leaves_map[l2_val]["id"]}
    elif l1_val != "All Subcategories" and l1_val in self.subcategories_map:
        # All leaves under this L1
        l1_id = self.subcategories_map[l1_val]["id"]
        leaves = ingredient_hierarchy_service.get_children(l1_id)
        matching_ingredient_ids = {leaf["id"] for leaf in leaves}
    elif l0_val != "All Categories" and l0_val in self.categories_map:
        # All leaves under this L0 (through L1s)
        l0_id = self.categories_map[l0_val]["id"]
        matching_ingredient_ids = self._get_all_descendants(l0_id)

    # Apply filter
    if matching_ingredient_ids is not None:
        filtered_products = [
            p for p in filtered_products
            if p.get("ingredient_id") in matching_ingredient_ids
        ]

    # Apply other filters (search, etc.)
    # ...

    self._display_products(filtered_products)

def _get_all_descendants(self, parent_id: int) -> set:
    """Get all leaf ingredient IDs under a parent."""
    descendants = set()
    children = ingredient_hierarchy_service.get_children(parent_id)
    for child in children:
        if child.get("hierarchy_level") == 2:
            descendants.add(child["id"])
        else:
            descendants.update(self._get_all_descendants(child["id"]))
    return descendants
```

**Files**: `src/ui/products_tab.py` - filter logic section

---

### Subtask T025 - Update Column Widths

**Purpose**: Adjust column widths to accommodate hierarchy path.

**Steps**:
1. Set hierarchy path column width to ~250-300px
2. Adjust other columns if needed to prevent horizontal scroll
3. Test with longest expected path (e.g., "Chocolate -> Dark Chocolate -> Semi-Sweet Chips")

**Files**: `src/ui/products_tab.py` - column configuration section

**Parallel?**: Yes, can be done alongside filter work.

---

## Test Strategy

**Manual Testing**:
1. Open Products tab, verify hierarchy path column displays correctly
2. Verify path format: "Chocolate -> Dark Chocolate -> Semi-Sweet Chips"
3. Select L0 filter "Chocolate", verify all chocolate products appear
4. Verify L1 filter enables and shows correct subcategories
5. Select L1 filter, verify L2 filter enables and shows correct leaves
6. Select L2 filter, verify only products with that exact ingredient appear
7. Reset to "All" at each level, verify filter broadens correctly
8. Verify no "category" filter remains

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Performance with deep hierarchy traversal | Cache descendant sets, lazy load |
| Column width issues | Test with longest paths, allow column resize |
| Filter state complexity | Clear cascade state on parent change |

---

## Definition of Done Checklist

- [ ] Hierarchy path column displays correctly
- [ ] Path format is "L0 -> L1 -> L2"
- [ ] Category filter removed
- [ ] L0 filter dropdown working
- [ ] L1 cascade from L0 working
- [ ] L2 cascade from L1 working
- [ ] Filter logic shows correct products
- [ ] Column widths appropriate

---

## Review Guidance

**Key Checkpoints**:
1. Path helper uses `get_ancestors()` correctly
2. Cascade enables/disables appropriately
3. "All" options work at each level
4. No deprecated category references remain

---

## Activity Log

- 2025-12-31T23:59:00Z - system - lane=planned - Prompt created via /spec-kitty.tasks
- 2026-01-01T18:12:44Z – claude – shell_pid=35513 – lane=doing – Starting implementation
- 2026-01-01T18:16:01Z – claude – shell_pid=35513 – lane=for_review – Ready for review - hierarchy path and cascading filters implemented
