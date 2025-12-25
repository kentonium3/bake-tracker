---
work_package_id: "WP06"
subtasks:
  - "T034"
  - "T035"
  - "T036"
  - "T037"
  - "T038"
  - "T039"
  - "T040"
title: "AddInventoryDialog - Type-Ahead Integration"
phase: "Phase 2 - Core Integration"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-24T23:15:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP06 – AddInventoryDialog Type-Ahead Integration

## Objectives & Success Criteria

**Goal**: Refactor AddInventoryDialog to use TypeAheadComboBox for Category/Ingredient/Product dropdowns.

**Success Criteria**:
- [ ] Category dropdown filters on 1 character
- [ ] Ingredient dropdown filters on 2 characters, filtered by category
- [ ] Product dropdown filters on 2 characters, filtered by ingredient
- [ ] Recent items appear with ⭐ marker at top
- [ ] Separator and create option handled correctly
- [ ] Tab navigation works through all fields
- [ ] Dialog functions correctly for full add workflow

## Context & Constraints

**References**:
- Plan: `kitty-specs/029-streamlined-inventory-entry/plan.md`
- Spec: `kitty-specs/029-streamlined-inventory-entry/spec.md` (User Stories 1-2)
- Design: `docs/design/F029_streamlined_inventory_entry.md`

**Constraints**:
- Depends on WP04 (TypeAheadComboBox)
- Depends on WP05 (dropdown builders)
- Must preserve existing dialog functionality
- Careful integration to avoid breaking changes

**Note**: This is a 🎯 MVP work package - core value delivery.

## Subtasks & Detailed Guidance

### Subtask T034 – Replace Category CTkComboBox

**Purpose**: Add type-ahead to category selection.

**Steps**:
1. Open dialog file (find existing AddInventoryDialog)
2. Import TypeAheadComboBox from widgets
3. Replace category CTkComboBox with TypeAheadComboBox
4. Set min_chars=1

**Code Pattern**:
```python
from src.ui.widgets.type_ahead_combobox import TypeAheadComboBox

# In dialog __init__ or setup method:
self.category_combo = TypeAheadComboBox(
    self,
    values=[],  # Loaded in _load_initial_data
    min_chars=1,
    command=self._on_category_selected
)
```

### Subtask T035 – Replace Ingredient CTkComboBox

**Purpose**: Add type-ahead to ingredient selection.

**Steps**:
1. Replace ingredient CTkComboBox with TypeAheadComboBox
2. Set min_chars=2
3. Initially disabled until category selected

**Code Pattern**:
```python
self.ingredient_combo = TypeAheadComboBox(
    self,
    values=[],
    min_chars=2,
    command=self._on_ingredient_selected,
    state="disabled"
)
```

### Subtask T036 – Replace Product CTkComboBox

**Purpose**: Add type-ahead to product selection.

**Steps**:
1. Replace product CTkComboBox with TypeAheadComboBox
2. Set min_chars=2
3. Initially disabled until ingredient selected

### Subtask T037 – Wire up category selection

**Purpose**: Load filtered ingredients when category changes.

**Steps**:
1. Implement/update `_on_category_selected(value)` handler
2. Strip ⭐ from value if present
3. Call dropdown builder to get ingredient list
4. Update ingredient combo with reset_values()
5. Clear ingredient and product selections
6. Enable ingredient dropdown

**Code Pattern**:
```python
def _on_category_selected(self, selected_value: str):
    """Handle category selection - load ingredients."""
    # Strip star if present
    category = selected_value.replace("⭐ ", "").strip()

    with session_scope() as session:
        # Build ingredient dropdown with recency
        ingredient_values = build_ingredient_dropdown_values(category, session)
        self.ingredient_combo.reset_values(ingredient_values)
        self.ingredient_combo.configure(state="normal")

        # Clear downstream
        self.ingredient_combo.set("")
        self.product_combo.set("")
        self.product_combo.configure(state="disabled")
```

### Subtask T038 – Wire up ingredient selection

**Purpose**: Load filtered products when ingredient changes.

**Steps**:
1. Implement/update `_on_ingredient_selected(value)` handler
2. Strip ⭐ from value if present
3. Look up ingredient by display_name
4. Call dropdown builder to get product list
5. Update product combo with reset_values()
6. Enable product dropdown

**Code Pattern**:
```python
def _on_ingredient_selected(self, selected_value: str):
    """Handle ingredient selection - load products."""
    # Strip star if present
    ingredient_name = selected_value.replace("⭐ ", "").strip()

    with session_scope() as session:
        # Find ingredient by display_name
        ingredient = session.query(Ingredient).filter_by(
            display_name=ingredient_name
        ).first()

        if not ingredient:
            return

        self.selected_ingredient = ingredient

        # Build product dropdown with recency
        product_values = build_product_dropdown_values(ingredient.id, session)
        self.product_combo.reset_values(product_values)
        self.product_combo.configure(state="normal")

        # Clear product selection
        self.product_combo.set("")
```

### Subtask T039 – Handle separator and create-new selections

**Purpose**: Ignore separator, trigger inline creation for create option.

**Steps**:
1. In product selection handler, check for special values
2. Ignore separator selection (reset to empty)
3. Trigger inline creation for "[+ Create New Product]"

**Code Pattern**:
```python
def _on_product_selected(self, selected_value: str):
    """Handle product selection."""
    # Ignore separator
    if "─" in selected_value:
        self.product_combo.set("")
        return

    # Check for create new option
    if "[+ Create New Product]" in selected_value:
        self._toggle_inline_create()
        return

    # Normal product selection
    product_name = selected_value.replace("⭐ ", "").strip()
    # ... rest of selection logic
```

### Subtask T040 – Update dialog import statements

**Purpose**: Ensure all new imports are in place.

**Steps**:
1. Add import for TypeAheadComboBox
2. Add import for dropdown builders
3. Add import for session_scope if not present
4. Verify no circular imports

**Imports**:
```python
from src.ui.widgets.type_ahead_combobox import TypeAheadComboBox
from src.ui.widgets.dropdown_builders import (
    build_ingredient_dropdown_values,
    build_product_dropdown_values,
    SEPARATOR,
    CREATE_NEW_OPTION
)
from src.database import session_scope
```

## Test Strategy

Manual testing required for UI integration:
1. Open Add Inventory dialog
2. Type in Category field - verify filtering at 1 char
3. Select category - verify ingredients load with recency
4. Type in Ingredient field - verify filtering at 2 chars
5. Select ingredient - verify products load with recency
6. Type in Product field - verify filtering at 2 chars
7. Click separator - verify no selection
8. Click create option - verify inline form triggers (if WP08 done)
9. Tab through all fields - verify navigation

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Breaking existing workflow | Extensive manual testing |
| Event binding conflicts | Review existing bindings |
| State management issues | Clear state on cascading changes |

## Definition of Done Checklist

- [ ] Category dropdown uses TypeAheadComboBox with min_chars=1
- [ ] Ingredient dropdown uses TypeAheadComboBox with min_chars=2
- [ ] Product dropdown uses TypeAheadComboBox with min_chars=2
- [ ] Category selection loads ingredients with recency
- [ ] Ingredient selection loads products with recency
- [ ] Separator ignored, create option triggers inline form
- [ ] Tab navigation works
- [ ] Full add workflow still functions

## Review Guidance

**Reviewers should verify**:
1. Type-ahead filtering works on all three dropdowns
2. Recency markers (⭐) appear correctly
3. Cascading clears work (category change clears ingredient/product)
4. Separator is not selectable
5. Create option triggers correctly

## Activity Log

- 2025-12-24T23:15:00Z – system – lane=planned – Prompt created.
