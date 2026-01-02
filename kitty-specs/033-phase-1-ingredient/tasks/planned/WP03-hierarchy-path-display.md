---
work_package_id: "WP03"
subtasks:
  - "T011"
  - "T012"
  - "T013"
title: "Hierarchy Path Display"
phase: "Phase 3 - User Story 3 (P3)"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-02T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP03 - Hierarchy Path Display

## Review Feedback

> **Populated by `/spec-kitty.review`** - Reviewers add detailed feedback here when work needs changes.

*[This section is empty initially.]*

---

## Objectives & Success Criteria

**Goal**: Add hierarchy path column to ingredients tab list view showing full path like "Baking > Flour > All-Purpose Flour".

**Success Criteria**:
- New "Hierarchy" column visible in ingredients list
- All ingredients display correct hierarchy path
- L0 ingredients show just their name (no separator)
- L1 ingredients show "L0 > L1"
- L2 ingredients show "L0 > L1 > L2"
- No N+1 query performance issues (use caching)

**Acceptance Scenarios** (from spec):
1. Given an L2 ingredient "All-Purpose Flour" under "Flour" under "Baking", When user views ingredients list, Then they see "Baking > Flour > All-Purpose Flour"
2. Given an L0 ingredient "Baking", When user views ingredients list, Then they see just "Baking"

## Context & Constraints

**Reference Documents**:
- Plan: `kitty-specs/033-phase-1-ingredient/plan.md`
- Spec: `kitty-specs/033-phase-1-ingredient/spec.md` (User Story 3)

**Dependencies**:
- None (uses existing `get_ancestors()` function)
- Can run in parallel with WP02 (different section of ingredients_tab.py)

**Pattern Reference**:
- `src/ui/inventory_tab.py` already has hierarchy path display - follow same pattern

**Existing Function to Use**:
- `ingredient_hierarchy_service.get_ancestors(ingredient_id, session)` - returns ancestor chain

## Subtasks & Detailed Guidance

### Subtask T011 - Add Hierarchy Path Column to Treeview

**Purpose**: Define new column in the ingredients list treeview.

**Steps**:
1. Open `src/ui/ingredients_tab.py`
2. Find treeview column definitions (look for `self.tree` or CTkTreeview setup)
3. Add "Hierarchy" column with appropriate width

**Files**: `src/ui/ingredients_tab.py`

**Example**:
```python
# In treeview column definitions
columns = ("name", "hierarchy_path", "category", ...)  # Add hierarchy_path

# Configure column
self.tree.column("hierarchy_path", width=250, anchor="w")
self.tree.heading("hierarchy_path", text="Hierarchy")
```

**Notes**:
- Consider column order - hierarchy path should be prominent (early column)
- Width ~250 for paths like "Category > Subcategory > Ingredient"

### Subtask T012 - Implement Hierarchy Path Cache

**Purpose**: Build cache of hierarchy paths to avoid N+1 queries on every row render.

**Steps**:
1. Add `self._hierarchy_path_cache: Dict[int, str] = {}` instance variable
2. Create `_build_hierarchy_path_cache()` method
3. Call cache builder when loading/refreshing ingredient data

**Files**: `src/ui/ingredients_tab.py`

**Parallel?**: Yes - can implement alongside T011

**Implementation**:
```python
def _build_hierarchy_path_cache(self, ingredients: List[Dict]):
    """Build cache of hierarchy paths for all ingredients."""
    self._hierarchy_path_cache = {}

    for ing in ingredients:
        ingredient_id = ing.get("id")
        if ingredient_id is None:
            continue

        # Get ancestors using existing service function
        try:
            ancestors = ingredient_hierarchy_service.get_ancestors(ingredient_id)
            # ancestors is list from root to parent (not including self)
            ancestor_names = [a.get("display_name", "") for a in ancestors]
            # Add self at end
            ancestor_names.append(ing.get("display_name", ing.get("name", "")))
            # Build path
            path = " > ".join(ancestor_names)
            self._hierarchy_path_cache[ingredient_id] = path
        except Exception:
            # Fallback to just the name
            self._hierarchy_path_cache[ingredient_id] = ing.get("display_name", ing.get("name", ""))
```

**Alternative Implementation** (if get_ancestors returns different format):
```python
def _build_hierarchy_path_cache(self, ingredients: List[Dict]):
    """Build cache of hierarchy paths for all ingredients."""
    self._hierarchy_path_cache = {}

    # Build a lookup for quick parent resolution
    id_to_ing = {ing["id"]: ing for ing in ingredients if "id" in ing}

    for ing in ingredients:
        ingredient_id = ing.get("id")
        if ingredient_id is None:
            continue

        # Build path by walking up parent chain
        path_parts = []
        current = ing
        while current:
            path_parts.insert(0, current.get("display_name", current.get("name", "")))
            parent_id = current.get("parent_ingredient_id")
            current = id_to_ing.get(parent_id) if parent_id else None

        self._hierarchy_path_cache[ingredient_id] = " > ".join(path_parts)
```

### Subtask T013 - Display Paths in List View

**Purpose**: Use cached paths when populating treeview rows.

**Steps**:
1. Find where treeview rows are inserted (look for `self.tree.insert()`)
2. Add hierarchy_path value from cache to row values
3. Handle missing cache entries gracefully

**Files**: `src/ui/ingredients_tab.py`

**Implementation**:
```python
# In the method that populates the treeview (e.g., _refresh_list, _load_ingredients)

# First, build the cache
self._build_hierarchy_path_cache(ingredients)

# Then, when inserting rows
for ing in ingredients:
    ingredient_id = ing.get("id")
    hierarchy_path = self._hierarchy_path_cache.get(ingredient_id, ing.get("display_name", ""))

    self.tree.insert(
        "",
        "end",
        iid=str(ingredient_id),
        values=(
            ing.get("display_name", ""),
            hierarchy_path,  # Add hierarchy path
            ing.get("category", ""),
            # ... other columns
        )
    )
```

**Notes**:
- Ensure cache is rebuilt when data changes (add, edit, delete)
- Call `_build_hierarchy_path_cache()` in refresh/reload methods

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| N+1 query performance | Use caching pattern (cache built once per refresh) |
| Cache stale after edits | Rebuild cache on any ingredient modification |
| get_ancestors format different | Check actual return format, adjust path building |
| Column order disruption | Verify other column references aren't broken |

## Definition of Done Checklist

- [ ] "Hierarchy" column added to treeview definition
- [ ] `_build_hierarchy_path_cache()` method implemented
- [ ] Cache built on data load/refresh
- [ ] Hierarchy paths display correctly in list
- [ ] L0 ingredients show just name (no " > ")
- [ ] L1 ingredients show "L0 > L1"
- [ ] L2 ingredients show "L0 > L1 > L2"
- [ ] Cache rebuilt on ingredient add/edit/delete
- [ ] Manual testing: verify paths for all hierarchy levels
- [ ] `tasks.md` updated with status change

## Review Guidance

**Key Acceptance Checkpoints**:
1. Verify column appears in correct position
2. Check paths for sample L0, L1, L2 ingredients
3. Verify no " > " prefix/suffix on paths
4. Test performance with 100+ ingredients (no lag)
5. Verify cache updates after CRUD operations

**Manual Test Scenarios**:
1. View ingredients list - hierarchy column visible
2. Check L0 ingredient - shows just name
3. Check L1 ingredient - shows "Parent > Name"
4. Check L2 ingredient - shows "GrandParent > Parent > Name"
5. Add new ingredient - hierarchy updates correctly
6. Edit ingredient parent - hierarchy updates correctly

## Activity Log

- 2026-01-02T00:00:00Z - system - lane=planned - Prompt created.
