---
work_package_id: "WP07"
subtasks:
  - "T036"
  - "T037"
  - "T038"
  - "T039"
  - "T040"
title: "Leaf-Only Validation"
phase: "Phase 4 - Validation & Testing"
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

# Work Package Prompt: WP07 - Leaf-Only Validation

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

**Goal**: Prevent products and recipes from being assigned to non-leaf (L0/L1) ingredients.

**Success Criteria**:
- Product ingredient selectors show only L2 (leaf) ingredients
- Recipe ingredient selectors show only L2 (leaf) ingredients
- User-friendly error message if non-leaf somehow selected
- Existing add_product_dialog pattern verified as reference

**User Story**: US6 - Prevent Invalid Hierarchy Assignments

---

## Context & Constraints

**Reference Documents**:
- Spec: `kitty-specs/032-complete-f031-hierarchy/spec.md` (FR-021, FR-022)
- Plan: `kitty-specs/032-complete-f031-hierarchy/plan.md`

**Key Service Functions**:
```python
from src.services import ingredient_hierarchy_service

# Get only leaf ingredients for dropdowns
leaves = ingredient_hierarchy_service.get_leaf_ingredients()
# Returns list of L2 ingredients only
```

**Files to Modify**:
- Product-related forms (verify `src/ui/forms/add_product_dialog.py`)
- Recipe-related forms (if ingredient selection exists)

**Dependencies**: WP03 (edit form patterns established)

---

## Subtasks & Detailed Guidance

### Subtask T036 - Update Product Ingredient Selector

**Purpose**: Ensure product forms only allow leaf ingredient selection.

**Steps**:
1. Find ingredient selector in product forms
2. Change data source from `get_all_ingredients()` to `get_leaf_ingredients()`
3. Verify dropdown only shows L2 ingredients

**Implementation**:
```python
# Instead of:
# ingredients = ingredient_service.get_all_ingredients()

# Use:
leaves = ingredient_hierarchy_service.get_leaf_ingredients()
self.ingredients_map = {ing["display_name"]: ing for ing in leaves}
ingredient_names = sorted(self.ingredients_map.keys())
```

**Files**: Check all product-related forms

---

### Subtask T037 - Add Product Validation Message

**Purpose**: Provide clear error if non-leaf is somehow selected.

**Steps**:
1. Add validation in save logic
2. Check ingredient's hierarchy_level before save
3. Display error message if level != 2

**Implementation**:
```python
def _validate_and_save(self):
    selected_ingredient = self.ingredients_map.get(self.ingredient_var.get())

    if not selected_ingredient:
        self._show_error("Please select an ingredient")
        return

    if selected_ingredient.get("hierarchy_level") != 2:
        self._show_error("Only leaf ingredients (L2) can be assigned to products")
        return

    # ... proceed with save ...
```

**Notes**: This is belt-and-suspenders validation since T036 prevents selection in the first place.

**Files**: Product form save logic

---

### Subtask T038 - Update Recipe Ingredient Selector

**Purpose**: Ensure recipe forms only allow leaf ingredient selection.

**Steps**:
1. Find recipe ingredient selector (if exists)
2. Change data source to `get_leaf_ingredients()`
3. Verify dropdown only shows L2 ingredients
4. Add validation message similar to T037

**Files**: Recipe-related forms (check `src/ui/recipes_tab.py` or similar)

**Notes**: If recipe ingredient selection doesn't exist yet, document for future implementation.

**Parallel?**: Yes, can proceed alongside T036-T037.

---

### Subtask T039 - Verify add_product_dialog Reference

**Purpose**: Confirm the existing add_product_dialog implements leaf-only correctly.

**Steps**:
1. Review `src/ui/forms/add_product_dialog.py`
2. Check if it already uses `get_leaf_ingredients()` or cascading to L2
3. Document findings
4. If already correct, note as reference implementation

**Files**: `src/ui/forms/add_product_dialog.py`

**Notes**: This dialog was fixed in a previous session. Verify it matches the pattern.

---

### Subtask T040 - Add User-Friendly Error Message

**Purpose**: Ensure error messages are clear and actionable.

**Steps**:
1. Define standard error message text
2. Use consistently across all validation points
3. Message should explain WHY (only leaf ingredients can have products)

**Standard Message**:
```
"Only leaf ingredients (L2) can be assigned to products.
Please select a specific ingredient, not a category."
```

**Files**: All forms with ingredient validation

---

## Test Strategy

**Manual Testing**:
1. Open product add/edit form, verify dropdown shows only leaf ingredients
2. Attempt to save product with no ingredient selected - verify error
3. Open recipe form (if exists), verify dropdown shows only leaves
4. Verify add_product_dialog works correctly (reference implementation)
5. Search for any other ingredient selectors that might need update

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Existing invalid data | This is UI-only; backend should already be valid |
| Missing some selectors | Search codebase for ingredient dropdowns |
| Recipe forms don't exist yet | Document for future; skip if not present |

---

## Definition of Done Checklist

- [ ] Product selector uses `get_leaf_ingredients()`
- [ ] Product validation message added
- [ ] Recipe selector updated (if exists)
- [ ] add_product_dialog verified as reference
- [ ] Error messages are user-friendly
- [ ] Manual testing confirms leaf-only enforcement

---

## Review Guidance

**Key Checkpoints**:
1. All ingredient selectors use `get_leaf_ingredients()`
2. Validation exists at save time (belt-and-suspenders)
3. Error messages are clear and helpful
4. No non-leaf ingredients can be selected in UI

---

## Activity Log

- 2025-12-31T23:59:00Z - system - lane=planned - Prompt created via /spec-kitty.tasks
- 2026-01-01T18:22:26Z – claude – shell_pid=35513 – lane=doing – Starting implementation
