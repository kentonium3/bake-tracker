---
work_package_id: "WP02"
subtasks:
  - "T005"
  - "T006"
  - "T007"
  - "T008"
  - "T009"
  - "T010"
title: "UI Form Fix - Remove Level Selector"
phase: "Phase 2 - User Story 1 (P1)"
lane: "done"
assignee: "claude"
agent: "claude-reviewer"
shell_pid: "81353"
review_status: "approved without changes"
reviewed_by: "claude-reviewer"
history:
  - timestamp: "2026-01-02T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP02 - UI Form Fix - Remove Level Selector

## Review Feedback

> **Populated by `/spec-kitty.review`** - Reviewers add detailed feedback here when work needs changes.

*[This section is empty initially.]*

---

## Objectives & Success Criteria

**Goal**: Fix the conceptual model issue by removing the explicit level dropdown and displaying computed level based on parent selection.

**Success Criteria**:
- No `ingredient_level_dropdown` or `ingredient_level_var` in the form
- Level displays as read-only text computed from parent selection
- Parent dropdowns only show L0 and L1 ingredients (L2 cannot have children)
- Informational warnings display inline when changing parent of existing ingredient
- All acceptance scenarios from User Story 1 pass

**Acceptance Scenarios** (from spec):
1. Given user opens Add Ingredient form, When they select no parent, Then form shows "Level: L0 (Root)"
2. Given user opens Add Ingredient form, When they select an L0 as parent, Then form shows "Level: L1 (Subcategory)"
3. Given user opens Add Ingredient form, When they select an L1 as parent, Then form shows "Level: L2 (Leaf)"
4. Given user opens Add Ingredient form, When viewing parent options, Then only L0 and L1 ingredients appear (not L2)

## Context & Constraints

**Reference Documents**:
- Constitution: `.kittify/memory/constitution.md` (Principle I: User-Centric Design)
- Plan: `kitty-specs/033-phase-1-ingredient/plan.md`
- Spec: `kitty-specs/033-phase-1-ingredient/spec.md` (User Story 1)

**Dependencies**:
- Requires WP01 complete (needs `can_change_parent()` for T010)

**Key Design Decision**:
- Warnings are INFORMATIONAL ONLY (non-blocking per planning decision)
- No confirmation dialogs required

**Current Code Location**:
- Level dropdown: `src/ui/ingredients_tab.py` lines ~866-879
- L0 dropdown: lines ~882-900
- L1 dropdown: lines ~902-920

## Subtasks & Detailed Guidance

### Subtask T005 - Remove Level Dropdown

**Purpose**: Remove the explicit level selector that causes conceptual confusion.

**Steps**:
1. Open `src/ui/ingredients_tab.py`
2. Find and remove:
   - `self.ingredient_level_var = ctk.StringVar(...)` (~line 870)
   - `self.ingredient_level_dropdown = ctk.CTkOptionMenu(...)` (~lines 871-878)
   - The `.grid()` call for the dropdown (~line 878)
   - The label "Ingredient Level*:" (~lines 867-869)
3. Find and remove `_on_ingredient_level_change()` method if it exists
4. Remove any references to `ingredient_level_var` in `_save_ingredient()` or similar

**Files**: `src/ui/ingredients_tab.py`

**Notes**:
- Keep the row counter logic intact; adjust row numbers as needed
- The level dropdown was in the F032 implementation but is now removed

### Subtask T006 - Add Level Display Label

**Purpose**: Show computed level as read-only information.

**Steps**:
1. Add a new label to display the computed level (where dropdown was removed)
2. Create `self.level_display_var = ctk.StringVar(value="Level: L0 (Root)")`
3. Create `self.level_display = ctk.CTkLabel(form_frame, textvariable=self.level_display_var)`
4. Grid the label in the form

**Files**: `src/ui/ingredients_tab.py`

**Implementation**:
```python
# After the parent dropdowns section
self.level_display_var = ctk.StringVar(value="Level: L0 (Root)")
self.level_display = ctk.CTkLabel(
    form_frame,
    textvariable=self.level_display_var,
    font=ctk.CTkFont(size=13, weight="bold"),
    text_color="gray"
)
self.level_display.grid(row=row, column=0, columnspan=2, sticky="w", padx=10, pady=5)
row += 1
```

### Subtask T007 - Implement Level Computation Helper

**Purpose**: Create reusable method to compute and display level.

**Steps**:
1. Add method `_compute_and_display_level()` to the class
2. Method reads current parent selection and computes level
3. Updates `self.level_display_var` with appropriate text

**Files**: `src/ui/ingredients_tab.py`

**Implementation**:
```python
def _compute_and_display_level(self):
    """Compute and display the ingredient level based on parent selection."""
    l0_selection = self.l0_var.get()
    l1_selection = self.l1_var.get()

    if l0_selection == "(Select Category)" or l0_selection == "":
        # No parent selected = L0 (Root)
        level = 0
        level_text = "Level: L0 (Root Category)"
    elif l1_selection == "(Select category first)" or l1_selection == "" or l1_selection == "(None - create L1)":
        # L0 selected, no L1 = L1 (Subcategory)
        level = 1
        level_text = "Level: L1 (Subcategory)"
    else:
        # L1 selected = L2 (Leaf)
        level = 2
        level_text = "Level: L2 (Leaf Ingredient)"

    self.level_display_var.set(level_text)
    return level
```

### Subtask T008 - Update Parent Change Callbacks

**Purpose**: Call level computation when parent dropdowns change.

**Steps**:
1. Find `_on_l0_change()` method
2. Add call to `self._compute_and_display_level()` at the end
3. Find `_on_l1_change()` method (if exists) or L1 dropdown command
4. Add call to `self._compute_and_display_level()` at the end

**Files**: `src/ui/ingredients_tab.py`

**Example Update**:
```python
def _on_l0_change(self, selected_l0: str):
    """Handle L0 category selection change."""
    # ... existing logic to populate L1 dropdown ...

    # Compute and display level
    self._compute_and_display_level()
```

### Subtask T009 - Filter Parent Dropdowns to Exclude L2

**Purpose**: Only L0 and L1 ingredients can be parents (L2 cannot have children).

**Steps**:
1. Find `_build_l0_options()` method
2. Modify query/filter to only include `hierarchy_level in (0, 1)`
3. Verify L1 dropdown population also filters correctly

**Files**: `src/ui/ingredients_tab.py`

**Implementation**:
```python
def _build_l0_options(self) -> Dict[str, int]:
    """Build L0 dropdown options from root ingredients."""
    options = {}
    try:
        # Only get L0 ingredients (roots)
        roots = ingredient_hierarchy_service.get_root_ingredients()
        for ing in roots:
            options[ing["display_name"]] = ing["id"]
    except Exception:
        pass
    return options
```

For L1 dropdown population (when L0 is selected):
```python
def _refresh_l1_options(self, l0_id: int):
    """Refresh L1 dropdown with children of selected L0."""
    self._l1_options = {}
    try:
        # Get children of L0 (which are L1)
        children = ingredient_hierarchy_service.get_children(l0_id)
        for child in children:
            # Only include if hierarchy_level == 1
            if child.get("hierarchy_level") == 1:
                self._l1_options[child["display_name"]] = child["id"]
    except Exception:
        pass
    # Update dropdown values
    self.l1_dropdown.configure(values=["(None - create L1)"] + list(self._l1_options.keys()))
```

### Subtask T010 - Add Inline Warning Display

**Purpose**: Show informational warnings when editing existing ingredient's parent.

**Steps**:
1. Add warning label (initially hidden) below level display
2. When editing existing ingredient and parent changes, call `can_change_parent()`
3. If warnings exist, display them; if not allowed, show error text
4. Warnings are informational only - do not block save

**Files**: `src/ui/ingredients_tab.py`

**Implementation**:
```python
# Add warning label in form creation (after level display)
self.warning_label = ctk.CTkLabel(
    form_frame,
    text="",
    text_color="orange",
    wraplength=350
)
self.warning_label.grid(row=row, column=0, columnspan=2, sticky="w", padx=10, pady=2)
self.warning_label.grid_remove()  # Hidden by default
row += 1

# In parent change callback, check for warnings when editing existing ingredient
def _check_parent_change_warnings(self):
    """Check and display warnings for parent change on existing ingredient."""
    if not hasattr(self, '_editing_ingredient_id') or self._editing_ingredient_id is None:
        self.warning_label.grid_remove()
        return

    # Get selected parent ID
    new_parent_id = self._get_selected_parent_id()

    # Check with can_change_parent
    result = ingredient_hierarchy_service.can_change_parent(
        self._editing_ingredient_id,
        new_parent_id
    )

    if not result["allowed"]:
        self.warning_label.configure(text=result["reason"], text_color="red")
        self.warning_label.grid()
    elif result["warnings"]:
        warning_text = " | ".join(result["warnings"])
        self.warning_label.configure(text=warning_text, text_color="orange")
        self.warning_label.grid()
    else:
        self.warning_label.grid_remove()
```

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Breaking existing form functionality | Test add/edit flows manually after each change |
| Missing callback updates | Search for all references to removed dropdown |
| Grid row number misalignment | Carefully track row counter after removals |
| Level display not updating | Verify callbacks are wired correctly |

## Definition of Done Checklist

- [ ] Level dropdown completely removed (no `ingredient_level_dropdown`, `ingredient_level_var`)
- [ ] Level display label shows computed level
- [ ] `_compute_and_display_level()` method implemented
- [ ] L0 and L1 change callbacks update level display
- [ ] Parent dropdowns only show L0 and L1 ingredients
- [ ] Warning label displays for existing ingredient parent changes
- [ ] All acceptance scenarios from User Story 1 pass
- [ ] Manual testing: Add new L0, L1, L2 ingredients works correctly
- [ ] Manual testing: Edit ingredient parent works correctly
- [ ] `tasks.md` updated with status change

## Review Guidance

**Key Acceptance Checkpoints**:
1. Verify no level selector exists - only read-only display
2. Test parent dropdown filtering - L2 ingredients should not appear
3. Test level computation for all 3 levels
4. Verify warnings are informational only (save still works)
5. Test with existing ingredients that have products/children

**Manual Test Scenarios**:
1. Add new root ingredient (no parent) - shows "L0 (Root)"
2. Add ingredient under L0 - shows "L1 (Subcategory)"
3. Add ingredient under L1 - shows "L2 (Leaf)"
4. Edit L2 with products - warning should display
5. Edit L1 with children - warning should display

## Activity Log

- 2026-01-02T00:00:00Z - system - lane=planned - Prompt created.
- 2026-01-02T05:45:08Z – system – shell_pid= – lane=doing – Moved to doing
- 2026-01-02T05:48:28Z – system – shell_pid= – lane=for_review – Moved to for_review
- 2026-01-02T09:17:27Z – claude-reviewer – shell_pid=81353 – lane=done – Code review approved: Level selector removed, computed level display implemented, parent change warnings integrated with can_change_parent(). All acceptance scenarios satisfied.
