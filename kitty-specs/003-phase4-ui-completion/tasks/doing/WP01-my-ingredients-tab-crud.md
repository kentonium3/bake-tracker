---
id: WP01
title: My Ingredients Tab - Ingredient Catalog CRUD
feature: 003-phase4-ui-completion
lane: planned
priority: P1
estimate: 12-15 hours
assignee: ""
agent: ""
shell_pid: ""
tags:
  - ui
  - ingredients
  - customtkinter
dependencies: []
history:
  - timestamp: "2025-11-10T18:01:00Z"
    lane: "planned"
    agent: ""
    shell_pid: ""
    action: "Work package created"
---

# WP01: My Ingredients Tab - Ingredient Catalog CRUD

## Objective

Create My Ingredients tab with basic ingredient catalog management interface. Users can view, search, filter, add, edit, and delete generic ingredients.

## Scope

- Create new `src/ui/ingredients_tab.py` module
- Implement ingredient list view with search and filter
- Create add/edit/delete forms and dialogs
- Integrate with ingredient_service
- Add to main_window.py

## Tasks

- [ ] Create `src/ui/ingredients_tab.py` with tab frame structure
- [ ] Implement ingredient list view (CTkScrollableFrame with table)
  - [ ] Columns: Name, Category, Recipe Unit, Density, Actions
  - [ ] Empty state message when no ingredients
- [ ] Add search bar widget
  - [ ] Filter by ingredient name (case-insensitive)
  - [ ] Clear search button
- [ ] Add category filter dropdown
  - [ ] Populate with unique categories from ingredients
  - [ ] "All Categories" option
- [ ] Create "Add Ingredient" form dialog
  - [ ] Fields: Name (required), Category (required), Recipe Unit (required), Density (optional, g/ml)
  - [ ] Validation: non-empty name, valid numeric density
  - [ ] Call ingredient_service.create_ingredient()
  - [ ] Handle exceptions (ValidationError, DatabaseError)
  - [ ] Display success/error messages
- [ ] Create "Edit Ingredient" form dialog
  - [ ] Pre-populate with current ingredient values
  - [ ] Same fields as Add form
  - [ ] Call ingredient_service.update_ingredient()
  - [ ] Handle exceptions
- [ ] Implement delete ingredient
  - [ ] Confirmation dialog: "Are you sure?"
  - [ ] Call ingredient_service.delete_ingredient()
  - [ ] Handle NotFound exception
  - [ ] Handle dependency errors (variants/recipes exist)
  - [ ] Display error: "Cannot delete ingredient with existing variants/recipes"
- [ ] Add tab to main_window.py
  - [ ] Insert after Dashboard tab
  - [ ] Tab label: "My Ingredients"
  - [ ] Icon (optional)
- [ ] Test CRUD operations through UI
  - [ ] Create 3 test ingredients
  - [ ] Search and filter tests
  - [ ] Edit ingredient
  - [ ] Delete ingredient (with and without dependencies)

## Technical Notes

**Service Methods to Use:**
- `ingredient_service.get_all_ingredients()` - list view
- `ingredient_service.search_ingredients(query)` - search
- `ingredient_service.get_ingredients_by_category(category)` - filter
- `ingredient_service.create_ingredient(data)` - create
- `ingredient_service.get_ingredient(slug)` - read for edit
- `ingredient_service.update_ingredient(slug, data)` - update
- `ingredient_service.delete_ingredient(slug)` - delete

**Exception Handling:**
- `NotFound` - ingredient doesn't exist
- `ValidationError` - invalid input data
- `DatabaseError` - database operation failed

**UI Patterns:**
- Follow existing tab patterns from other tabs (recipe_tab.py, event_tab.py)
- Use CustomTkinter widgets (CTkFrame, CTkScrollableFrame, CTkButton, CTkEntry, CTkLabel)
- Reuse widgets from `src/ui/widgets/` if available

## Acceptance Criteria

- [ ] My Ingredients tab is visible in main window
- [ ] User can view list of all ingredients
- [ ] Search by name filters ingredients correctly
- [ ] Category filter shows only ingredients in selected category
- [ ] User can add new ingredient with all fields
- [ ] User can edit existing ingredient
- [ ] User can delete ingredient without dependencies
- [ ] Deletion blocked when ingredient has variants/recipes (with clear error message)
- [ ] All error messages are user-friendly
- [ ] UI refreshes after create/update/delete operations

## Testing Checklist

- [ ] Create ingredient with all fields → success
- [ ] Create ingredient with missing required field → validation error
- [ ] Create ingredient with invalid density (negative) → validation error
- [ ] Search for ingredient by partial name → correct results
- [ ] Filter by category → correct results
- [ ] Edit ingredient name → saves correctly
- [ ] Edit ingredient density → saves correctly
- [ ] Delete ingredient with no dependencies → succeeds
- [ ] Delete ingredient with variants → error message displayed
- [ ] UI state updates after each operation

## Files to Create/Modify

**New Files:**
- `src/ui/ingredients_tab.py`

**Modified Files:**
- `src/ui/main_window.py` (add tab)

## Dependencies

**Requires:**
- ✅ ingredient_service.py (complete)
- ✅ CustomTkinter framework

**Blocks:**
- WP02 (Variant Management - needs ingredient list)

## Estimated Effort

12-15 hours

## Activity Log

- 2025-11-10 – Claude Code – lane=planned – Work package created
