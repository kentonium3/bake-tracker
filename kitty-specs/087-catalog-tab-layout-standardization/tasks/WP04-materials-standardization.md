---
work_package_id: WP04
title: MaterialsTab and Sub-tabs Standardization
lane: "doing"
dependencies: [WP01]
base_branch: 087-catalog-tab-layout-standardization-WP01
base_commit: 3fa9a8a9fe5337dea329dbf424521b0b5b73b4bd
created_at: '2026-01-31T02:55:13.030707+00:00'
subtasks:
- T017
- T018
- T019
- T020
- T021
- T022
phase: Phase 2 - Layout Standardization
assignee: ''
agent: ''
shell_pid: "7821"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-01-31T02:38:50Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP04 – MaterialsTab and Sub-tabs Standardization

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
spec-kitty implement WP04 --base WP01
```

---

## Objectives & Success Criteria

**Primary Objective**: Remove outer "Materials Catalog" title and apply 3-row pattern to all 3 sub-tabs.

**Success Criteria**:
1. No "Materials Catalog" title visible at top of MaterialsTab
2. CTkTabview appears at row 0 (fills tab area)
3. Each sub-tab (Materials Catalog, Material Products, Material Units) follows 3-row pattern:
   - Row 0: Filters/Search
   - Row 1: Action buttons
   - Row 2: Data grid (weight=1)
4. All sub-tab grids expand on window resize
5. All existing functionality preserved in all sub-tabs

---

## Context & Constraints

**Reference Files**:
- `src/ui/materials_tab.py` - Target file (large file with 3 inner tab classes)
- `kitty-specs/087-catalog-tab-layout-standardization/research.md` - Pattern documentation

**Structure**:
MaterialsTab (outer) contains:
- `_create_title()` - Creates "Materials Catalog" title ← REMOVE
- `_create_tabview()` - Creates CTkTabview with 3 tabs

Inner classes (all in same file):
- `MaterialsCatalogTab` - Material definitions
- `MaterialProductsTab` - Products linked to materials
- `MaterialUnitsTab` - Units with inventory/cost

**Current MaterialsTab State**:
- Row 0: Title "Materials Catalog" ← REMOVE
- Row 1: CTkTabview

**Target MaterialsTab State**:
- Row 0: CTkTabview (weight=1)

---

## Subtasks & Detailed Guidance

### Subtask T017 – Remove "Materials Catalog" Title from Outer Container

**Purpose**: Eliminate redundant outer title.

**Steps**:
1. Locate `_create_title()` method (lines 86-93):
   ```python
   def _create_title(self):
       """Create the title label."""
       title_label = ctk.CTkLabel(
           self,
           text="Materials Catalog",
           font=ctk.CTkFont(size=24, weight="bold"),
       )
       title_label.grid(row=0, column=0, sticky="w", padx=PADDING_MEDIUM, pady=(PADDING_MEDIUM, 5))
   ```
2. Delete the entire `_create_title()` method
3. Remove the call to `self._create_title()` in `__init__()` (around line 79-80)

**Files**: `src/ui/materials_tab.py`

---

### Subtask T018 – Update Outer grid_rowconfigure for Tabview

**Purpose**: Make tabview fill the entire MaterialsTab.

**Steps**:
1. Locate grid configuration in `__init__()` (around lines 74-77):
   ```python
   self.grid_rowconfigure(0, weight=0)  # Title
   self.grid_rowconfigure(1, weight=1)  # Tabview
   ```
2. Update to:
   ```python
   self.grid_rowconfigure(0, weight=1)  # Tabview (fills space)
   ```
3. Update `_create_tabview()` to use row=0:
   ```python
   self.tabview.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
   ```

**Files**: `src/ui/materials_tab.py`

---

### Subtask T019 – Apply 3-Row Pattern to MaterialsCatalogTab

**Purpose**: Standardize MaterialsCatalogTab inner layout.

**Steps**:
1. Locate `MaterialsCatalogTab` class (search for `class MaterialsCatalogTab`)
2. Review its current layout and identify components:
   - Filter/search controls
   - Action buttons
   - Data grid (ttk.Treeview)
3. Ensure grid configuration:
   ```python
   self.grid_rowconfigure(0, weight=0)  # Filters/Search
   self.grid_rowconfigure(1, weight=0)  # Action buttons
   self.grid_rowconfigure(2, weight=1)  # Data grid
   ```
4. Verify each component is gridded at correct row
5. Remove any title labels within this sub-tab

**Files**: `src/ui/materials_tab.py`

---

### Subtask T020 – Apply 3-Row Pattern to MaterialProductsTab

**Purpose**: Standardize MaterialProductsTab inner layout.

**Steps**:
1. Locate `MaterialProductsTab` class
2. Apply same pattern as T019:
   - Row 0: Filters/Search (weight=0)
   - Row 1: Action buttons (weight=0)
   - Row 2: Data grid (weight=1)
3. Remove any title labels
4. Update grid() calls to use correct row indices

**Files**: `src/ui/materials_tab.py`

---

### Subtask T021 – Apply 3-Row Pattern to MaterialUnitsTab

**Purpose**: Standardize MaterialUnitsTab inner layout.

**Steps**:
1. Locate `MaterialUnitsTab` class
2. Apply same pattern as T019 and T020:
   - Row 0: Filters/Search (weight=0)
   - Row 1: Action buttons (weight=0)
   - Row 2: Data grid (weight=1)
3. Remove any title labels
4. Update grid() calls to use correct row indices

**Files**: `src/ui/materials_tab.py`

---

### Subtask T022 – Verify Grid Weight=1 in All Sub-tabs

**Purpose**: Ensure all data grids expand properly on window resize.

**Steps**:
1. For each sub-tab (MaterialsCatalogTab, MaterialProductsTab, MaterialUnitsTab):
   - Verify `self.grid_rowconfigure(2, weight=1)` is set for the grid row
   - Verify the grid container uses `sticky="nsew"` in its grid() call
   - Verify `grid_columnconfigure(0, weight=1)` for horizontal expansion
2. Test by resizing the window - all grids should expand/contract

**Verification Pattern**:
```python
# In each sub-tab __init__:
self.grid_columnconfigure(0, weight=1)
self.grid_rowconfigure(0, weight=0)  # Controls
self.grid_rowconfigure(1, weight=0)  # Buttons
self.grid_rowconfigure(2, weight=1)  # Grid

# Grid container should use:
grid_container.grid(row=2, column=0, sticky="nsew", ...)
```

**Files**: `src/ui/materials_tab.py`

---

## Test Strategy

Manual verification for each change:

**Outer MaterialsTab**:
1. No "Materials Catalog" title visible
2. CTkTabview fills the entire tab area

**Each Sub-tab (Catalog, Products, Units)**:
1. Switch to sub-tab
2. Verify no inner title label
3. Verify filters/search at top
4. Verify action buttons below filters
5. Verify grid fills remaining space
6. Resize window - grid should expand/contract
7. Test all CRUD operations

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Sub-tab layouts vary | Systematically check each one |
| Grid weight not working | Verify sticky="nsew" on container |
| Broke functionality | Test each sub-tab's features after changes |

---

## Definition of Done Checklist

- [ ] Outer "Materials Catalog" title removed
- [ ] Outer `_create_title()` method deleted
- [ ] Tabview at row 0 with weight=1
- [ ] MaterialsCatalogTab follows 3-row pattern
- [ ] MaterialProductsTab follows 3-row pattern
- [ ] MaterialUnitsTab follows 3-row pattern
- [ ] All grids use weight=1 and sticky="nsew"
- [ ] Window resize works correctly
- [ ] All sub-tab CRUD operations work
- [ ] `tasks.md` updated with status change

---

## Review Guidance

**Key checkpoints**:
1. No outer title visible
2. Switch between all 3 sub-tabs - each should have consistent layout
3. Resize window - all grids should expand
4. Test add/edit/delete in each sub-tab

---

## Activity Log

- 2026-01-31T02:38:50Z – system – lane=planned – Prompt created.
