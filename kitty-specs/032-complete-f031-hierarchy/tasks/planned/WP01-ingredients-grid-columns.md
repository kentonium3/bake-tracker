---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
  - "T003"
  - "T004"
  - "T005"
  - "T006"
title: "Ingredients Grid Columns"
phase: "Phase 1 - Ingredients Tab"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-31T23:59:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 - Ingredients Grid Columns

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

**Goal**: Replace the deprecated "Category" column with three-tier hierarchy columns (Root L0, Subcategory L1, Name) in the Ingredients tab grid.

**Success Criteria**:
- Ingredients grid displays three columns: Root (L0), Subcategory (L1), Name
- Deprecated "Category" column is removed
- Each column is sortable by clicking header
- L0/L1 ingredients show dash ("--") for child-level columns
- No performance degradation with ~400 ingredients

**User Story**: US1 - View Ingredients by Hierarchy

---

## Context & Constraints

**Reference Documents**:
- Spec: `kitty-specs/032-complete-f031-hierarchy/spec.md`
- Plan: `kitty-specs/032-complete-f031-hierarchy/plan.md`
- Quickstart: `kitty-specs/032-complete-f031-hierarchy/quickstart.md`
- Bug spec: `docs/bugs/BUG_F031_incomplete_hierarchy_ui.md`

**Key Service Functions**:
```python
from src.services import ingredient_hierarchy_service

# Get ancestry chain for display
ancestors = ingredient_hierarchy_service.get_ancestors(ingredient_id)
# Returns: [immediate_parent, grandparent, ...] ordered from closest to root
# For L2 leaf: ancestors[0] = L1, ancestors[1] = L0
# For L1: ancestors[0] = L0
# For L0: empty list
```

**File to Modify**: `src/ui/ingredients_tab.py`

**Pattern Reference**: `src/ui/forms/add_product_dialog.py` for hierarchy service usage

---

## Subtasks & Detailed Guidance

### Subtask T001 - Build Hierarchy Cache

**Purpose**: Avoid N+1 queries by building a cache mapping ingredient ID to (L0_name, L1_name) tuple.

**Steps**:
1. Add a method `_build_hierarchy_cache(self) -> Dict[int, Tuple[str, str]]` to the ingredients tab class
2. Iterate over all ingredients once
3. For each ingredient, call `get_ancestors(ingredient_id)`
4. Extract L0 and L1 names from ancestors list
5. Store in cache dict keyed by ingredient ID
6. Call cache builder once per display refresh, not per row

**Implementation**:
```python
def _build_hierarchy_cache(self) -> Dict[int, Tuple[str, str]]:
    """Build cache mapping ingredient ID to (L0_name, L1_name)."""
    cache = {}
    for ingredient in self.ingredients:
        ing_id = ingredient.get("id")
        if not ing_id:
            continue
        ancestors = ingredient_hierarchy_service.get_ancestors(ing_id)
        # ancestors[0] = immediate parent (L1 for leaf), ancestors[1] = grandparent (L0)
        if len(ancestors) >= 2:
            # L2 ingredient
            l0_name = ancestors[1].get("display_name", "--")
            l1_name = ancestors[0].get("display_name", "--")
        elif len(ancestors) == 1:
            # L1 ingredient
            l0_name = ancestors[0].get("display_name", "--")
            l1_name = "--"
        else:
            # L0 ingredient (root)
            l0_name = "--"
            l1_name = "--"
        cache[ing_id] = (l0_name, l1_name)
    return cache
```

**Notes**: Cache should be rebuilt when ingredients list changes (after add/edit/delete).

---

### Subtask T002 - Add L0 Column Header

**Purpose**: Replace "Category" column with "Root (L0)" column.

**Steps**:
1. Find column configuration in `ingredients_tab.py`
2. Remove or rename "Category" column
3. Add "Root (L0)" column in appropriate position (first or second column)
4. Set reasonable column width (~150px)

**Files**: `src/ui/ingredients_tab.py` - column configuration section

---

### Subtask T003 - Add L1 Column Header

**Purpose**: Add "Subcategory (L1)" column between L0 and Name.

**Steps**:
1. Add "Subcategory (L1)" column after L0 column
2. Set reasonable column width (~150px)
3. Ensure column order is: L0, L1, Name (or ID, L0, L1, Name if ID shown)

**Files**: `src/ui/ingredients_tab.py` - column configuration section

---

### Subtask T004 - Update Display Method

**Purpose**: Populate L0/L1 columns from hierarchy cache when displaying ingredients.

**Steps**:
1. Find `_update_ingredient_display()` or equivalent method
2. Build or retrieve hierarchy cache at start of display update
3. For each ingredient row, look up (L0_name, L1_name) from cache
4. Set column values accordingly
5. Ensure ingredient's own name goes in "Name" column

**Implementation Pattern**:
```python
def _update_ingredient_display(self):
    # Build cache once
    hierarchy_cache = self._build_hierarchy_cache()

    for ingredient in filtered_ingredients:
        ing_id = ingredient.get("id")
        l0_name, l1_name = hierarchy_cache.get(ing_id, ("--", "--"))

        # Add row with: L0, L1, Name (adjust for actual grid API)
        self._add_row(l0_name, l1_name, ingredient.get("display_name"))
```

**Files**: `src/ui/ingredients_tab.py` - display/refresh method

---

### Subtask T005 - Implement Column Sorting

**Purpose**: Enable sorting by each hierarchy column.

**Steps**:
1. Verify existing sort functionality works with new columns
2. Ensure L0 column sorts alphabetically
3. Ensure L1 column sorts alphabetically
4. Ensure Name column sorts alphabetically
5. Handle "--" values in sort (should sort before/after letters consistently)

**Notes**: CustomTkinter treeview sorting may already work if columns are configured correctly.

---

### Subtask T006 - Handle Empty Levels Display

**Purpose**: Display dash for ingredients that don't have values at certain levels.

**Steps**:
1. L0 (root) ingredients: Show "--" for both L0 and L1 columns, show name in Name column
2. L1 (subcategory) ingredients: Show L0 parent in L0 column, "--" in L1 column, name in Name column
3. L2 (leaf) ingredients: Show L0 grandparent, L1 parent, name in respective columns

**Notes**: The cache building in T001 handles this logic; T006 ensures it displays correctly.

---

## Test Strategy

**Manual Testing**:
1. Open Ingredients tab with sample data containing L0, L1, and L2 ingredients
2. Verify columns display: Root (L0), Subcategory (L1), Name
3. Verify L2 ingredient "Semi-Sweet Chips" shows: Chocolate | Dark Chocolate | Semi-Sweet Chips
4. Verify L1 ingredient "Dark Chocolate" shows: Chocolate | -- | Dark Chocolate
5. Verify L0 ingredient "Chocolate" shows: -- | -- | Chocolate
6. Click each column header, verify alphabetical sorting
7. Verify no "Category" column exists

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Performance with 400+ ingredients | Cache-based approach avoids N+1 queries |
| Column width insufficient | Test with longest hierarchy names, adjust widths |
| Sort order inconsistency | Test "--" sort position, normalize if needed |

---

## Definition of Done Checklist

- [ ] Hierarchy cache builder method implemented
- [ ] "Category" column removed from grid
- [ ] "Root (L0)" column added and displays correctly
- [ ] "Subcategory (L1)" column added and displays correctly
- [ ] All three columns sortable
- [ ] Empty levels display as "--"
- [ ] Manual test with L0, L1, L2 ingredients passes
- [ ] No performance regression observed

---

## Review Guidance

**Key Checkpoints**:
1. Column data alignment - verify L0/L1/Name columns show correct hierarchy level
2. No deprecated "Category" references remain in this file
3. Cache is built once per refresh, not per row
4. Sort functionality works for all columns

---

## Activity Log

- 2025-12-31T23:59:00Z - system - lane=planned - Prompt created via /spec-kitty.tasks
