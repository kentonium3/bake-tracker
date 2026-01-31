---
work_package_id: WP02
title: IngredientsTab Layout Cleanup
lane: "doing"
dependencies: [WP01]
base_branch: 087-catalog-tab-layout-standardization-WP01
base_commit: 3fa9a8a9fe5337dea329dbf424521b0b5b73b4bd
created_at: '2026-01-31T02:54:52.871618+00:00'
subtasks:
- T008
- T009
- T010
- T011
phase: Phase 2 - Layout Standardization
assignee: ''
agent: ''
shell_pid: "7520"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-01-31T02:38:50Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP02 – IngredientsTab Layout Cleanup

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.

---

## Review Feedback

> **Populated by `/spec-kitty.review`**

*[This section is empty initially.]*

---

## Implementation Command

```bash
spec-kitty implement WP02 --base WP01
```

---

## Objectives & Success Criteria

**Primary Objective**: Remove the "My Ingredients" title label and standardize to the 3-row layout pattern.

**Success Criteria**:
1. No "My Ingredients" title visible at top of tab
2. Search/filter controls appear at row 0 (top of tab)
3. Action buttons at row 1
4. Data grid at row 2 (fills remaining space)
5. Status bar at row 3 (if present)
6. Vertical padding uses PADDING_MEDIUM consistently
7. All existing functionality preserved (search, filter, CRUD)

---

## Context & Constraints

**Reference Files**:
- `src/ui/ingredients_tab.py` - Target file
- `kitty-specs/087-catalog-tab-layout-standardization/research.md` - Pattern documentation

**Current State** (before changes):
- Row 0: Title label "My Ingredients" ← REMOVE
- Row 1: Search/filter controls
- Row 2: Action buttons
- Row 3: Data grid (ttk.Treeview)
- Row 4: Status bar

**Target State** (after changes):
- Row 0: Search/filter controls
- Row 1: Action buttons
- Row 2: Data grid (weight=1)
- Row 3: Status bar (weight=0)

---

## Subtasks & Detailed Guidance

### Subtask T008 – Remove "My Ingredients" Title Label

**Purpose**: Eliminate redundant title that wastes vertical space.

**Steps**:
1. Locate `_create_title()` method (around line 116-123)
2. Delete the entire method:
   ```python
   # DELETE THIS ENTIRE METHOD
   def _create_title(self):
       """Create the title label."""
       title_label = ctk.CTkLabel(
           self,
           text="My Ingredients",
           font=ctk.CTkFont(size=24, weight="bold"),
       )
       title_label.grid(row=0, column=0, sticky="w", padx=PADDING_MEDIUM, pady=(PADDING_MEDIUM, 5))
   ```
3. Remove the call to `self._create_title()` in `__init__()` (around line 104)

**Files**: `src/ui/ingredients_tab.py`

---

### Subtask T009 – Update Grid Row Indices

**Purpose**: Shift all components up by one row since title is removed.

**Steps**:
1. In `_create_search_filter()`: Change `row=1` to `row=0` in the `filter_frame.grid()` call
2. In `_create_action_buttons()`: Change `row=2` to `row=1` in the `button_frame.grid()` call
3. In `_create_ingredient_list()`: Change `row=3` to `row=2` in the `grid_container.grid()` call
4. In `_create_status_bar()`: Change `row=4` to `row=3` in the `status_label.grid()` call

**Current to Target Mapping**:
| Component | Current Row | Target Row |
|-----------|-------------|------------|
| Search/filter | 1 | 0 |
| Action buttons | 2 | 1 |
| Grid container | 3 | 2 |
| Status bar | 4 | 3 |

**Files**: `src/ui/ingredients_tab.py`

---

### Subtask T010 – Update grid_rowconfigure Calls

**Purpose**: Ensure proper weight distribution for new row indices.

**Steps**:
1. Locate grid configuration in `__init__()` (around lines 96-101)
2. Update from:
   ```python
   self.grid_rowconfigure(0, weight=0)  # Title
   self.grid_rowconfigure(1, weight=0)  # Search/filter
   self.grid_rowconfigure(2, weight=0)  # Action buttons
   self.grid_rowconfigure(3, weight=1)  # Ingredient list
   self.grid_rowconfigure(4, weight=0)  # Status bar
   ```
3. To:
   ```python
   self.grid_rowconfigure(0, weight=0)  # Search/filter (fixed)
   self.grid_rowconfigure(1, weight=0)  # Action buttons (fixed)
   self.grid_rowconfigure(2, weight=1)  # Ingredient list (expandable)
   self.grid_rowconfigure(3, weight=0)  # Status bar (fixed)
   ```

**Validation**: After this change, resizing the window vertically should expand/contract only the data grid.

**Files**: `src/ui/ingredients_tab.py`

---

### Subtask T011 – Reduce Vertical Padding to PADDING_MEDIUM

**Purpose**: Create compact layout while maintaining readability.

**Steps**:
1. Review all `pady` values in grid() calls
2. Standardize to `PADDING_MEDIUM` (which is 10 per constants.py)
3. Specific locations to check:
   - `filter_frame.grid(...)` - use `pady=PADDING_MEDIUM`
   - `button_frame.grid(...)` - use `pady=PADDING_MEDIUM`
   - `grid_container.grid(...)` - use `pady=PADDING_MEDIUM`
   - `status_label.grid(...)` - use `pady=PADDING_MEDIUM`

**Note**: Import PADDING_MEDIUM is already present (line 51-57). Use `PADDING_MEDIUM` instead of hardcoded values.

**Files**: `src/ui/ingredients_tab.py`

---

## Test Strategy

Manual verification:
1. Open Ingredients tab - should NOT show "My Ingredients" title
2. Verify search/filters appear at top
3. Click a row - Edit button should enable
4. Resize window vertically - only grid should expand
5. All filter dropdowns should work
6. Search should filter results

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Row indices off by one | Verify each component placement visually |
| Forgot to remove method call | Search for `_create_title` usage |
| Padding inconsistent | Use PADDING_MEDIUM constant, not literals |

---

## Definition of Done Checklist

- [ ] "My Ingredients" title label removed
- [ ] `_create_title()` method deleted
- [ ] All grid row indices updated (1→0, 2→1, 3→2, 4→3)
- [ ] grid_rowconfigure updated for 4 rows
- [ ] Padding uses PADDING_MEDIUM consistently
- [ ] Window resize expands only grid
- [ ] All existing functionality works
- [ ] `tasks.md` updated with status change

---

## Review Guidance

**Key checkpoints**:
1. No title visible
2. Search at top of tab
3. Grid expands on window resize
4. All filters and CRUD work

---

## Activity Log

- 2026-01-31T02:38:50Z – system – lane=planned – Prompt created.
