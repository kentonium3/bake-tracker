---
work_package_id: "WP03"
subtasks:
  - "T012"
  - "T013"
  - "T014"
  - "T015"
  - "T016"
  - "T017"
  - "T018"
  - "T019"
title: "Ingredient Edit Form Hierarchy"
phase: "Phase 1 - Ingredients Tab"
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

# Work Package Prompt: WP03 - Ingredient Edit Form Hierarchy

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

**Goal**: Replace the deprecated category dropdown with cascading L0/L1 dropdowns in the ingredient edit form, supporting creation of ingredients at any hierarchy level.

**Success Criteria**:
- Category dropdown removed from edit form
- Ingredient type selector (Root/Subcategory/Leaf) controls form behavior
- L0 dropdown populated from `get_root_ingredients()`
- L1 dropdown cascades based on L0 selection
- Editing pre-populates L0/L1 from current hierarchy position
- Can create L0, L1, and L2 ingredients
- Modal dialog is stable (no visibility issues)

**User Story**: US3 - Create/Edit Ingredients with Hierarchy Position

---

## Context & Constraints

**Reference Documents**:
- Spec: `kitty-specs/032-complete-f031-hierarchy/spec.md` (FR-008 through FR-012)
- Plan: `kitty-specs/032-complete-f031-hierarchy/plan.md`
- Pattern reference: `src/ui/forms/add_product_dialog.py` (cascading dropdown implementation)

**Key Service Functions**:
```python
from src.services import ingredient_hierarchy_service

# Get all root categories (L0) for dropdown
categories = ingredient_hierarchy_service.get_root_ingredients()

# Get children of a parent (L1s under selected L0)
subcategories = ingredient_hierarchy_service.get_children(parent_id)

# Get ancestry for pre-populating edit form
ancestors = ingredient_hierarchy_service.get_ancestors(ingredient_id)
# For L2: ancestors[0] = L1 parent, ancestors[1] = L0 grandparent
# For L1: ancestors[0] = L0 parent
# For L0: empty list
```

**File to Modify**: `src/ui/ingredients_tab.py` (edit dialog/form section)

**Modal Pattern** (from previous fix):
```python
self.withdraw()  # Hide while building
self.transient(parent)
# ... build UI ...
self.deiconify()
self.update()
try:
    self.wait_visibility()
    self.grab_set()
except Exception:
    if not self.winfo_exists():
        return
self.lift()
self.focus_force()
```

---

## Subtasks & Detailed Guidance

### Subtask T012 - Remove Category Dropdown from Form

**Purpose**: Remove the deprecated category dropdown from the ingredient edit form.

**Steps**:
1. Find the ingredient edit dialog/form in `ingredients_tab.py`
2. Remove the category dropdown widget and its label
3. Remove category-related variables and event handlers
4. Remove category from save logic

**Files**: `src/ui/ingredients_tab.py` - edit form section

---

### Subtask T013 - Add Ingredient Type Selector

**Purpose**: Allow user to select what type of ingredient they're creating/editing.

**Steps**:
1. Add a type selector with options: "Root Category (L0)", "Subcategory (L1)", "Leaf Ingredient (L2)"
2. On type change, show/hide appropriate parent dropdowns:
   - L0: Hide both L0 and L1 parent dropdowns
   - L1: Show L0 dropdown, hide L1 dropdown
   - L2: Show both L0 and L1 dropdowns
3. Default to "Leaf Ingredient (L2)" for new ingredients

**Implementation**:
```python
self.type_var = ctk.StringVar(value="Leaf Ingredient (L2)")
self.type_selector = ctk.CTkComboBox(
    form_frame,
    values=["Root Category (L0)", "Subcategory (L1)", "Leaf Ingredient (L2)"],
    variable=self.type_var,
    command=self._on_type_change
)

def _on_type_change(self, choice: str):
    if "L0" in choice:
        # Creating root category - no parents
        self.l0_frame.pack_forget()
        self.l1_frame.pack_forget()
    elif "L1" in choice:
        # Creating subcategory - needs L0 parent only
        self.l0_frame.pack(fill="x", pady=5)
        self.l1_frame.pack_forget()
    else:
        # Creating leaf - needs both parents
        self.l0_frame.pack(fill="x", pady=5)
        self.l1_frame.pack(fill="x", pady=5)
```

**Files**: `src/ui/ingredients_tab.py` - edit form section

---

### Subtask T014 - Add L0 (Root Category) Dropdown

**Purpose**: Add dropdown for selecting the root category parent.

**Steps**:
1. Create frame for L0 dropdown (can be hidden)
2. Populate dropdown from `get_root_ingredients()`
3. Build map: display_name -> ingredient dict for lookup
4. Add "(Select Category)" placeholder as first option

**Implementation**:
```python
# In form setup
categories = ingredient_hierarchy_service.get_root_ingredients()
self.categories_map = {cat["display_name"]: cat for cat in categories}
category_names = ["(Select Category)"] + sorted(self.categories_map.keys())

self.l0_var = ctk.StringVar(value="(Select Category)")
self.l0_dropdown = ctk.CTkComboBox(
    self.l0_frame,
    values=category_names,
    variable=self.l0_var,
    command=self._on_category_change
)
```

**Files**: `src/ui/ingredients_tab.py` - edit form section

---

### Subtask T015 - Add L1 (Subcategory) Dropdown

**Purpose**: Add dropdown for selecting the subcategory parent (cascades from L0).

**Steps**:
1. Create frame for L1 dropdown (can be hidden)
2. Initially disabled with placeholder "(Select category first)"
3. Enabled when L0 is selected
4. Populated dynamically based on L0 selection

**Implementation**:
```python
self.l1_var = ctk.StringVar(value="(Select category first)")
self.l1_dropdown = ctk.CTkComboBox(
    self.l1_frame,
    values=["(Select category first)"],
    variable=self.l1_var,
    state="disabled"
)
```

**Files**: `src/ui/ingredients_tab.py` - edit form section

---

### Subtask T016 - Implement Cascade Logic

**Purpose**: Populate L1 dropdown based on L0 selection.

**Steps**:
1. Create `_on_category_change(choice)` handler
2. Get selected L0 ingredient from map
3. Call `get_children(l0_id)` to get subcategories
4. Build subcategories map
5. Update L1 dropdown values
6. Enable L1 dropdown (or show "(No subcategories)" if empty)

**Implementation**:
```python
def _on_category_change(self, choice: str):
    """Handle L0 category selection - populate L1 dropdown."""
    if choice == "(Select Category)" or choice not in self.categories_map:
        self.l1_dropdown.configure(values=["(Select category first)"], state="disabled")
        self.l1_var.set("(Select category first)")
        return

    category = self.categories_map[choice]
    subcategories = ingredient_hierarchy_service.get_children(category["id"])
    self.subcategories_map = {sub["display_name"]: sub for sub in subcategories}

    if subcategories:
        sub_names = ["(Select Subcategory)"] + sorted(self.subcategories_map.keys())
        self.l1_dropdown.configure(values=sub_names, state="normal")
        self.l1_var.set("(Select Subcategory)")
    else:
        self.l1_dropdown.configure(values=["(No subcategories)"], state="disabled")
        self.l1_var.set("(No subcategories)")
```

**Files**: `src/ui/ingredients_tab.py` - edit form section

---

### Subtask T017 - Pre-populate on Edit

**Purpose**: When editing an existing ingredient, pre-populate the form with current hierarchy position.

**Steps**:
1. Detect if editing (ingredient_id is not None)
2. Call `get_ancestors(ingredient_id)` to get hierarchy
3. Determine ingredient type from `hierarchy_level` field
4. Set type selector to appropriate value
5. If L1 or L2: Set L0 dropdown to grandparent (for L2) or parent (for L1)
6. If L2: Trigger cascade, then set L1 dropdown to parent

**Implementation**:
```python
def _load_ingredient_for_edit(self, ingredient_id: int):
    ingredient = ingredient_service.get_ingredient(ingredient_id)
    level = ingredient.get("hierarchy_level", 2)

    # Set type selector
    type_map = {0: "Root Category (L0)", 1: "Subcategory (L1)", 2: "Leaf Ingredient (L2)"}
    self.type_var.set(type_map.get(level, "Leaf Ingredient (L2)"))
    self._on_type_change(self.type_var.get())

    if level > 0:
        ancestors = ingredient_hierarchy_service.get_ancestors(ingredient_id)

        if level == 2 and len(ancestors) >= 2:
            # L2: Set L0 (grandparent), then L1 (parent)
            l0_name = ancestors[1].get("display_name")
            l1_name = ancestors[0].get("display_name")
            self.l0_var.set(l0_name)
            self._on_category_change(l0_name)  # Populate L1 dropdown
            self.l1_var.set(l1_name)
        elif level == 1 and len(ancestors) >= 1:
            # L1: Set L0 (parent)
            l0_name = ancestors[0].get("display_name")
            self.l0_var.set(l0_name)
```

**Files**: `src/ui/ingredients_tab.py` - edit form section

---

### Subtask T018 - Apply Modal Pattern

**Purpose**: Ensure dialog stability using withdraw/deiconify pattern.

**Steps**:
1. Add `self.withdraw()` at start of `__init__` (after super)
2. Add `self.transient(parent)` after withdraw
3. Build all UI components
4. At end of init, add visibility sequence:

**Implementation**:
```python
def __init__(self, parent, ingredient_id=None, **kwargs):
    super().__init__(parent, **kwargs)

    # Hide while building
    self.withdraw()
    self.transient(parent)

    # ... build UI ...

    # Show after UI complete
    self.deiconify()
    self.update()
    try:
        self.wait_visibility()
        self.grab_set()
    except Exception:
        if not self.winfo_exists():
            return
    self.lift()
    self.focus_force()
```

**Files**: `src/ui/ingredients_tab.py` - edit dialog class

---

### Subtask T019 - Handle No Children Edge Case

**Purpose**: Gracefully handle L0 categories that have no subcategories.

**Steps**:
1. In `_on_category_change()`, check if subcategories list is empty
2. If empty, set L1 dropdown to "(No subcategories)" and disable
3. For creating L2 under such an L0, user must first create an L1

**Notes**: Already handled in T016 implementation. This subtask is verification.

---

## Test Strategy

**Manual Testing**:
1. **Create L0**: Select "Root Category (L0)" type, enter name, save. Verify ingredient created at level 0.
2. **Create L1**: Select "Subcategory (L1)" type, select L0 parent, enter name, save. Verify ingredient created at level 1 under correct parent.
3. **Create L2**: Select "Leaf Ingredient (L2)" type, select L0, select L1, enter name, save. Verify ingredient created at level 2 under correct parents.
4. **Edit L2**: Edit existing L2 ingredient. Verify L0 and L1 dropdowns pre-populated correctly.
5. **Edit L1**: Edit existing L1 ingredient. Verify L0 dropdown pre-populated, L1 hidden.
6. **Edit L0**: Edit existing L0 ingredient. Verify both dropdowns hidden.
7. **Cascade**: Select different L0, verify L1 dropdown updates with correct children.
8. **No children**: Select L0 with no subcategories, verify L1 shows "(No subcategories)" disabled.

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Modal visibility issues | Use proven withdraw/deiconify pattern |
| Type selector confusion | Clear labels and immediate visual feedback on selection |
| Save logic complexity | Derive parent_id from form state, validate before save |
| Editing changes type incorrectly | Disable type selector when editing existing ingredient |

---

## Definition of Done Checklist

- [ ] Category dropdown removed from form
- [ ] Type selector with L0/L1/L2 options working
- [ ] L0 dropdown populated from service
- [ ] L1 dropdown cascades correctly
- [ ] Pre-populate works for editing all levels
- [ ] Modal pattern applied (no visibility issues)
- [ ] No children edge case handled
- [ ] Can create L0, L1, L2 ingredients successfully

---

## Review Guidance

**Key Checkpoints**:
1. Cascading logic triggers on L0 change
2. Pre-population uses `get_ancestors()` correctly
3. Save logic sets `parent_ingredient_id` and `hierarchy_level` correctly
4. Modal is stable across different scenarios
5. No deprecated "category" references remain

---

## Activity Log

- 2025-12-31T23:59:00Z - system - lane=planned - Prompt created via /spec-kitty.tasks
- 2026-01-01T18:07:54Z – claude – shell_pid=35513 – lane=doing – Started implementation
