---
work_package_id: "WP05"
subtasks:
  - "T026"
  - "T027"
  - "T028"
  - "T029"
  - "T030"
  - "T031"
title: "Inventory Grid Hierarchy"
phase: "Phase 3 - Inventory Tab"
lane: "doing"
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

# Work Package Prompt: WP05 - Inventory Grid Hierarchy

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

**Goal**: Replace the deprecated category column with hierarchy display and filtering in the Inventory tab.

**Success Criteria**:
- Inventory grid shows hierarchy columns or path instead of category
- Deprecated category column and filter removed
- Hierarchy-based filtering works correctly
- Display is consistent with Products tab pattern (WP04)

**User Story**: US5 - View Inventory with Hierarchy Information

---

## Context & Constraints

**Reference Documents**:
- Spec: `kitty-specs/032-complete-f031-hierarchy/spec.md` (FR-016, FR-017, FR-018)
- Plan: `kitty-specs/032-complete-f031-hierarchy/plan.md`

**Relationship Chain**: Inventory Item -> Product -> Ingredient -> Hierarchy

**Key Service Functions**:
```python
# Get ingredient via product relationship
product = product_service.get_product(inventory_item.product_id)
ingredient_id = product.ingredient_id

# Then use hierarchy service as in WP04
ancestors = ingredient_hierarchy_service.get_ancestors(ingredient_id)
```

**File to Modify**: `src/ui/inventory_tab.py`

**Dependencies**: WP04 (Products tab) for pattern consistency

---

## Subtasks & Detailed Guidance

### Subtask T026 - Remove Category Column

**Purpose**: Remove the deprecated category column from Inventory grid.

**Steps**:
1. Find column configuration in `inventory_tab.py`
2. Remove "Category" column definition
3. Remove category from row data population

**Files**: `src/ui/inventory_tab.py` - column configuration section

---

### Subtask T027 - Add Hierarchy Columns

**Purpose**: Add hierarchy display to inventory grid.

**Steps**:
1. Choose approach: Either three columns (L0, L1, L2) or single path column
2. If path column: Similar to WP04, show "L0 -> L1 -> L2"
3. If three columns: Mirror WP01 approach but traverse product->ingredient
4. Add column(s) to grid configuration

**Recommendation**: Use single path column for consistency with Products tab.

**Files**: `src/ui/inventory_tab.py` - column configuration section

---

### Subtask T028 - Build Inventory Hierarchy Cache

**Purpose**: Build cache for efficient hierarchy display (inventory -> product -> ingredient).

**Steps**:
1. Create method `_build_inventory_hierarchy_cache() -> Dict[int, str]`
2. For each inventory item, get product, then ingredient_id
3. Build hierarchy path using same logic as WP04
4. Cache maps inventory_item_id -> path string

**Implementation**:
```python
def _build_inventory_hierarchy_cache(self) -> Dict[int, str]:
    """Build cache mapping inventory item ID to hierarchy path."""
    cache = {}
    for item in self.inventory_items:
        item_id = item.get("id")
        product_id = item.get("product_id")

        if not item_id or not product_id:
            cache[item_id] = "--"
            continue

        product = product_service.get_product(product_id)
        if not product or not product.get("ingredient_id"):
            cache[item_id] = "--"
            continue

        ingredient_id = product.get("ingredient_id")
        cache[item_id] = self._get_hierarchy_path(ingredient_id)

    return cache
```

**Files**: `src/ui/inventory_tab.py`

---

### Subtask T029 - Update Inventory Display

**Purpose**: Populate hierarchy column(s) from cache when displaying inventory.

**Steps**:
1. Build cache at start of display update
2. For each inventory row, look up hierarchy path from cache
3. Set column value accordingly

**Files**: `src/ui/inventory_tab.py` - display/refresh method

---

### Subtask T030 - Remove Category Filter

**Purpose**: Remove the deprecated category filter from Inventory tab.

**Steps**:
1. Find category filter in inventory tab
2. Remove the widget and label
3. Remove category filtering logic

**Files**: `src/ui/inventory_tab.py` - filter UI section

**Parallel?**: Yes, can proceed alongside display changes.

---

### Subtask T031 - Add Hierarchy Filter

**Purpose**: Add hierarchy-based filtering to Inventory tab.

**Steps**:
1. Implement similar to WP04 (cascading L0 -> L1 -> L2 filters)
2. OR implement simpler single-dropdown with combined options
3. Filter inventory items based on ingredient hierarchy membership

**Recommendation**: Match Products tab pattern (cascading) for consistency.

**Implementation**: Reuse filter logic from WP04, adapted for inventory context.

**Files**: `src/ui/inventory_tab.py` - filter section

**Parallel?**: Yes, can proceed alongside display changes.

---

## Test Strategy

**Manual Testing**:
1. Open Inventory tab, verify hierarchy column/path displays correctly
2. Verify path traces: Inventory Item -> Product -> Ingredient -> Hierarchy
3. Verify no "Category" column exists
4. Test hierarchy filter - select L0, verify correct items appear
5. Test filter cascade if implemented
6. Clear filter, verify all items appear

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Deeper relationship chain (inv->prod->ing) | Cache to avoid repeated lookups |
| Null product or ingredient | Handle gracefully with "--" display |
| Inconsistency with Products tab | Follow same patterns from WP04 |

---

## Definition of Done Checklist

- [ ] Category column removed
- [ ] Hierarchy column(s) or path displays correctly
- [ ] Cache built for efficient display
- [ ] Category filter removed
- [ ] Hierarchy filter working
- [ ] Display consistent with Products tab

---

## Review Guidance

**Key Checkpoints**:
1. Relationship chain traversal is correct (inv->prod->ing)
2. Null handling for missing products/ingredients
3. Pattern consistency with Products tab
4. No deprecated category references

---

## Activity Log

- 2025-12-31T23:59:00Z - system - lane=planned - Prompt created via /spec-kitty.tasks
- 2026-01-01T18:16:21Z – claude – shell_pid=35513 – lane=doing – Starting implementation
