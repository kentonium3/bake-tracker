---
id: WP01
title: My Ingredients Tab - Ingredient Catalog CRUD
feature: 003-phase4-ui-completion
lane: done
priority: P1
estimate: 12-15 hours
assignee: "Claude Code"
agent: "Claude Code"
shell_pid: "1"
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
  - timestamp: "2025-11-13T20:00:00Z"
    lane: "done"
    agent: "Claude Code"
    shell_pid: "1"
    action: "Work package completed - ingredients tab fully implemented with CRUD functionality"
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

- [x] Create `src/ui/ingredients_tab.py` with tab frame structure
- [x] Implement ingredient list view (CTkScrollableFrame with table)
  - [x] Columns: Name, Category, Recipe Unit, Density, Actions
  - [x] Empty state message when no ingredients
- [x] Add search bar widget
  - [x] Filter by ingredient name (case-insensitive)
  - [x] Clear search button
- [x] Add category filter dropdown
  - [x] Populate with unique categories from ingredients
  - [x] "All Categories" option
- [x] Create "Add Ingredient" form dialog
  - [x] Fields: Name (required), Category (required), Recipe Unit (required), Density (optional, g/ml)
  - [x] Validation: non-empty name, valid numeric density
  - [x] Call ingredient_service.create_ingredient()
  - [x] Handle exceptions (ValidationError, DatabaseError)
  - [x] Display success/error messages
- [x] Create "Edit Ingredient" form dialog
  - [x] Pre-populate with current ingredient values
  - [x] Same fields as Add form
  - [x] Call ingredient_service.update_ingredient()
  - [x] Handle exceptions
- [x] Implement delete ingredient
  - [x] Confirmation dialog: "Are you sure?"
  - [x] Call ingredient_service.delete_ingredient()
  - [x] Handle NotFound exception
  - [x] Handle dependency errors (variants/recipes exist)
  - [x] Display error: "Cannot delete ingredient with existing variants/recipes"
- [x] Add tab to main_window.py
  - [x] Insert after Dashboard tab
  - [x] Tab label: "My Ingredients"
  - [x] Icon (optional)
- [x] Test CRUD operations through UI
  - [x] Create 3 test ingredients
  - [x] Search and filter tests
  - [x] Edit ingredient
  - [x] Delete ingredient (with and without dependencies)

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

- [x] My Ingredients tab is visible in main window
- [x] User can view list of all ingredients
- [x] Search by name filters ingredients correctly
- [x] Category filter shows only ingredients in selected category
- [x] User can add new ingredient with all fields
- [x] User can edit existing ingredient
- [x] User can delete ingredient without dependencies
- [x] Deletion blocked when ingredient has variants/recipes (with clear error message)
- [x] All error messages are user-friendly
- [x] UI refreshes after create/update/delete operations

## Testing Checklist

- [x] Create ingredient with all fields → success
- [x] Create ingredient with missing required field → validation error
- [x] Create ingredient with invalid density (negative) → validation error
- [x] Search for ingredient by partial name → correct results
- [x] Filter by category → correct results
- [x] Edit ingredient name → saves correctly
- [x] Edit ingredient density → saves correctly
- [x] Delete ingredient with no dependencies → succeeds
- [x] Delete ingredient with variants → error message displayed
- [x] UI state updates after each operation

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

- 2025-11-10T18:01:00Z – Claude Code – shell_pid=1 – lane=planned – Work package created
- 2025-11-13T20:00:00Z – Claude Code – shell_pid=1 – lane=done – Work package completed - ingredients tab fully implemented with CRUD functionality
