---
work_package_id: "WP02"
subtasks:
  - "T007"
  - "T008"
  - "T009"
  - "T010"
  - "T011"
title: "Ingredients Level Filter"
phase: "Phase 1 - Ingredients Tab"
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

# Work Package Prompt: WP02 - Ingredients Level Filter

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

**Goal**: Replace the deprecated category dropdown with a hierarchy level filter in the Ingredients tab.

**Success Criteria**:
- Category dropdown removed from filter area
- Level filter dropdown with options: All Levels, Root (L0), Subcategory (L1), Leaf (L2)
- Selecting a level shows only ingredients at that hierarchy level
- Search works across all levels regardless of filter selection
- Clear button resets all filters

**User Story**: US2 - Filter Ingredients by Hierarchy Level

---

## Context & Constraints

**Reference Documents**:
- Spec: `kitty-specs/032-complete-f031-hierarchy/spec.md` (FR-005, FR-006, FR-007)
- Plan: `kitty-specs/032-complete-f031-hierarchy/plan.md`

**Key Service Functions**:
```python
from src.services import ingredient_hierarchy_service

# Option 1: Get ingredients at specific level
level_0 = ingredient_hierarchy_service.get_ingredients_by_level(0)  # Roots
level_1 = ingredient_hierarchy_service.get_ingredients_by_level(1)  # Subcategories
level_2 = ingredient_hierarchy_service.get_ingredients_by_level(2)  # Leaves

# Option 2: Filter locally using hierarchy_level field on ingredient dict
filtered = [i for i in ingredients if i.get("hierarchy_level") == selected_level]
```

**File to Modify**: `src/ui/ingredients_tab.py`

**Dependencies**: WP01 (grid columns should exist for context)

---

## Subtasks & Detailed Guidance

### Subtask T007 - Remove Category Dropdown

**Purpose**: Remove the deprecated category dropdown from the filter area.

**Steps**:
1. Find the category dropdown/combobox in the filter section
2. Remove the widget and its label
3. Remove any event handlers tied to category selection
4. Remove category-related filtering logic from `_apply_filters()`
5. Clean up any category state variables

**Files**: `src/ui/ingredients_tab.py` - filter UI section

**Notes**: Search for "category" to find all references. Don't break other filters (search).

---

### Subtask T008 - Add Level Filter Dropdown

**Purpose**: Add a dropdown to filter by hierarchy level.

**Steps**:
1. Add a label "Level:" next to filter area
2. Add CTkComboBox or CTkOptionMenu with values:
   - "All Levels"
   - "Root Categories (L0)"
   - "Subcategories (L1)"
   - "Leaf Ingredients (L2)"
3. Set default to "All Levels"
4. Add event handler for selection change

**Implementation**:
```python
self.level_filter_var = ctk.StringVar(value="All Levels")
self.level_filter = ctk.CTkComboBox(
    filter_frame,
    values=["All Levels", "Root Categories (L0)", "Subcategories (L1)", "Leaf Ingredients (L2)"],
    variable=self.level_filter_var,
    command=self._on_level_filter_change,
    width=180
)
```

**Files**: `src/ui/ingredients_tab.py` - filter UI section

---

### Subtask T009 - Update Filter Logic

**Purpose**: Implement filtering by `hierarchy_level` field.

**Steps**:
1. Add/modify `_apply_filters()` method
2. Parse selected level filter value to get level number (or None for All)
3. Filter ingredients list by hierarchy_level if level selected
4. Combine with search filter (AND logic)

**Implementation**:
```python
def _get_selected_level(self) -> Optional[int]:
    """Convert filter dropdown value to hierarchy level."""
    value = self.level_filter_var.get()
    level_map = {
        "All Levels": None,
        "Root Categories (L0)": 0,
        "Subcategories (L1)": 1,
        "Leaf Ingredients (L2)": 2
    }
    return level_map.get(value)

def _apply_filters(self):
    filtered = self.ingredients

    # Apply level filter
    selected_level = self._get_selected_level()
    if selected_level is not None:
        filtered = [i for i in filtered if i.get("hierarchy_level") == selected_level]

    # Apply search filter (existing logic)
    search_term = self.search_var.get().lower()
    if search_term:
        filtered = [i for i in filtered if search_term in i.get("display_name", "").lower()]

    self._display_ingredients(filtered)
```

**Files**: `src/ui/ingredients_tab.py` - filter logic section

---

### Subtask T010 - Search Across Levels

**Purpose**: Ensure search works regardless of level filter.

**Steps**:
1. Verify search filters on display_name (or other searchable fields)
2. Ensure search applies AFTER level filter (AND logic)
3. Test: Set level to "Root (L0)", search for "choc" - should find "Chocolate" if it's L0
4. Test: Set level to "All", search for "choc" - should find all chocolates at any level

**Notes**: This may already work if T009 is implemented correctly. Verify with testing.

---

### Subtask T011 - Add Clear Button

**Purpose**: Provide a way to reset all filters at once.

**Steps**:
1. Add "Clear" button in filter area
2. On click, reset level filter to "All Levels"
3. On click, clear search text
4. Refresh display with no filters

**Implementation**:
```python
self.clear_button = ctk.CTkButton(
    filter_frame,
    text="Clear",
    width=60,
    command=self._clear_filters
)

def _clear_filters(self):
    self.level_filter_var.set("All Levels")
    self.search_var.set("")
    self._apply_filters()
```

**Files**: `src/ui/ingredients_tab.py` - filter UI section

---

## Test Strategy

**Manual Testing**:
1. Open Ingredients tab with sample data (L0, L1, L2 ingredients)
2. Verify level dropdown shows all four options
3. Select "Root Categories (L0)" - verify only L0 ingredients appear
4. Select "Subcategories (L1)" - verify only L1 ingredients appear
5. Select "Leaf Ingredients (L2)" - verify only L2 ingredients appear
6. Select "All Levels" - verify all ingredients appear
7. With L2 filter active, search for "chocolate" - verify only L2 chocolates appear
8. Click Clear - verify all filters reset and all ingredients display

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Filter state persists unexpectedly | Reset on tab switch or keep state (document choice) |
| Search case sensitivity | Use `.lower()` for case-insensitive search |
| Missing hierarchy_level on old data | Handle None/missing gracefully (treat as unfiltered) |

---

## Definition of Done Checklist

- [ ] Category dropdown removed
- [ ] Level filter dropdown added with 4 options
- [ ] Filtering by L0/L1/L2 works correctly
- [ ] "All Levels" shows all ingredients
- [ ] Search works with level filter (AND logic)
- [ ] Clear button resets all filters
- [ ] No deprecated category filter references remain

---

## Review Guidance

**Key Checkpoints**:
1. Dropdown values match specification exactly
2. Filter logic uses `hierarchy_level` field, not deprecated `category`
3. Search is case-insensitive
4. Clear button works correctly

---

## Activity Log

- 2025-12-31T23:59:00Z - system - lane=planned - Prompt created via /spec-kitty.tasks
- 2026-01-01T18:05:26Z – claude – shell_pid=35513 – lane=doing – Started implementation
- 2026-01-01T18:07:36Z – claude – shell_pid=35513 – lane=for_review – Ready for review - level filter implemented
