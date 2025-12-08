---
work_package_id: "WP06"
subtasks:
  - "T047"
  - "T048"
  - "T049"
  - "T050"
  - "T051"
  - "T052"
  - "T053"
  - "T054"
  - "T055"
title: "UI Integration"
phase: "Phase 2 - User Stories"
lane: "doing"
assignee: ""
agent: "claude"
shell_pid: "39066"
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-08T12:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP06 - UI Integration

## Objectives & Success Criteria

**Goal**: Add packaging sections to existing dialogs for FinishedGood and Package editing.

**Success Criteria**:
- [ ] Ingredients tab shows packaging indicator
- [ ] Can create/edit ingredient with is_packaging checkbox
- [ ] Packaging category dropdown shows when is_packaging=True
- [ ] FinishedGood dialog has "Packaging" section to add/edit packaging
- [ ] Package dialog has "Packaging" section to add/edit packaging
- [ ] Shopping list displays separate "Packaging" section
- [ ] My Pantry visually distinguishes packaging from food

## Context & Constraints

**Reference Documents**:
- Plan: `kitty-specs/011-packaging-bom-foundation/plan.md` (Q3: Simple inline forms)
- Spec: SC-001, SC-002, SC-003, SC-004 (success criteria for UI)

**Dependencies**:
- WP01-WP04 must be complete (all service layer work)

**UI Framework**: CustomTkinter

**Design Decision**: Simple inline forms within existing dialogs. Reuse existing composition editing patterns.

## Subtasks & Detailed Guidance

### Subtask T047 - Update Ingredients tab to show is_packaging indicator
- **Purpose**: Visual distinction for packaging ingredients in list
- **File**: `src/ui/ingredients_tab.py`
- **Steps**:
  1. Find ingredients list/treeview
  2. Add "Type" or "Packaging" column
  3. Display "Packaging" or icon for is_packaging=True ingredients
  4. Consider color coding or icon in existing columns
- **Parallel?**: Yes - independent of dialogs
- **Notes**: Keep subtle; user shouldn't be overwhelmed

### Subtask T048 - Update ingredient create/edit dialog
- **Purpose**: Allow user to mark ingredient as packaging
- **File**: `src/ui/ingredients_tab.py` or ingredient dialog file
- **Steps**:
  1. Find ingredient create/edit dialog
  2. Add checkbox: "This is a packaging material"
  3. Wire checkbox to `is_packaging` field
  4. Pass `is_packaging` to service on save
- **Parallel?**: Yes - independent of other dialogs

### Subtask T049 - Add packaging category dropdown
- **Purpose**: Show packaging-specific categories when is_packaging=True
- **File**: `src/ui/ingredients_tab.py` or ingredient dialog file
- **Steps**:
  1. Import PACKAGING_CATEGORIES from ingredient_service
  2. When is_packaging checkbox checked:
     - Swap category dropdown to show PACKAGING_CATEGORIES
  3. When unchecked:
     - Swap back to food categories
  4. Example:
     ```python
     def on_packaging_checkbox_change():
         if is_packaging_var.get():
             category_dropdown.configure(values=PACKAGING_CATEGORIES)
         else:
             category_dropdown.configure(values=FOOD_CATEGORIES)
     ```
- **Parallel?**: Yes - independent of other dialogs

### Subtask T050 - Add "Packaging" section to FinishedGood dialog
- **Purpose**: Allow user to define packaging requirements for FinishedGood
- **File**: `src/ui/finished_good_dialog.py` or similar
- **Steps**:
  1. Find FinishedGood edit dialog
  2. Add "Packaging" frame/section below components
  3. Display list of current packaging compositions
  4. Add buttons: "Add Packaging", "Remove"
  5. Wire to composition_service methods
- **Parallel?**: Yes - independent of Package dialog

### Subtask T051 - Implement packaging product selector
- **Purpose**: Dropdown to select packaging products (filtered to is_packaging=True)
- **File**: `src/ui/` (component or dialog)
- **Steps**:
  1. Create product selector that filters to packaging products:
     ```python
     def get_packaging_products():
         packaging_ingredients = ingredient_service.get_packaging_ingredients()
         products = []
         for ing in packaging_ingredients:
             products.extend(product_service.get_products_for_ingredient(ing.id))
         return products
     ```
  2. Display as dropdown with "Ingredient - Product" format
  3. Reuse for both FinishedGood and Package dialogs
- **Parallel?**: No - shared component for T050, T053

### Subtask T052 - Implement decimal quantity input
- **Purpose**: Allow decimal quantities like "0.5" for packaging
- **File**: `src/ui/` (component or dialog)
- **Steps**:
  1. Use entry field that accepts float values
  2. Validate on input or blur:
     ```python
     def validate_quantity(value):
         try:
             qty = float(value)
             return qty > 0
         except ValueError:
             return False
     ```
  3. Display current quantity with reasonable precision (1-2 decimal places)
- **Parallel?**: No - shared component for T050, T053

### Subtask T053 - Add "Packaging" section to Package dialog
- **Purpose**: Allow user to define packaging requirements for Package
- **File**: `src/ui/package_dialog.py` or similar
- **Steps**:
  1. Find Package edit dialog
  2. Add "Packaging" frame/section
  3. Display list of current packaging compositions
  4. Reuse product selector (T051) and quantity input (T052)
  5. Wire to composition_service.add_packaging_to_package
- **Parallel?**: Yes - independent of FinishedGood dialog

### Subtask T054 - Update shopping list display
- **Purpose**: Show separate "Packaging" section after "Ingredients"
- **File**: `src/ui/shopping_list_view.py` or event detail view
- **Steps**:
  1. Find shopping list display
  2. After ingredients section, add "Packaging" header
  3. Display packaging items with:
     - Ingredient name
     - Product name
     - Total needed
     - On hand
     - To buy
     - Unit
  4. Only show section if packaging needs exist
- **Parallel?**: No - depends on service returning packaging data

### Subtask T055 - Add packaging visual distinction in My Pantry
- **Purpose**: Help user see packaging vs food at a glance
- **File**: `src/ui/inventory_tab.py` or pantry view
- **Steps**:
  1. Find inventory/pantry list
  2. Add visual distinction for packaging items:
     - Different background color (subtle)
     - Icon or badge
     - "Type" column showing "Packaging"
  3. Consider optional filter to show/hide packaging
- **Parallel?**: Yes - independent enhancement

## Test Strategy

**Manual Testing Checklist**:
1. Create packaging ingredient - verify checkbox and category dropdown
2. View ingredients list - verify packaging indicator visible
3. Open FinishedGood dialog - verify Packaging section exists
4. Add packaging to FinishedGood - verify saved and displayed
5. Open Package dialog - verify Packaging section exists
6. Add packaging to Package - verify saved and displayed
7. View shopping list with packaging - verify separate section
8. View My Pantry with packaging - verify visual distinction

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| UI complexity overwhelming user | Medium | Medium | Keep forms simple; test with primary user |
| CustomTkinter layout issues | Low | Low | Follow existing patterns |

## Definition of Done Checklist

- [ ] All 9 subtasks completed
- [ ] Ingredients tab shows packaging indicator
- [ ] Ingredient dialog has is_packaging checkbox
- [ ] Category dropdown switches for packaging
- [ ] FinishedGood dialog has Packaging section
- [ ] Package dialog has Packaging section
- [ ] Product selector filters to packaging only
- [ ] Decimal quantities work
- [ ] Shopping list shows Packaging section
- [ ] My Pantry distinguishes packaging
- [ ] Manual testing complete
- [ ] tasks.md updated

## Review Guidance

**Key Checkpoints**:
1. Create packaging ingredient end-to-end
2. Add packaging to FinishedGood, verify persisted
3. Add packaging to Package, verify persisted
4. View shopping list with packaging
5. User feedback: Is it intuitive?

## Activity Log

- 2025-12-08T12:00:00Z - system - lane=planned - Prompt created via /spec-kitty.tasks
- 2025-12-08T17:34:40Z – claude – shell_pid=39066 – lane=doing – Started implementation
