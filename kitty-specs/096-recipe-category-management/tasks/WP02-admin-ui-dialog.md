---
work_package_id: WP02
title: Admin UI Dialog + Menu Integration
lane: "done"
dependencies: [WP01]
base_branch: 096-recipe-category-management-WP01
base_commit: b7f26a5b07ecebc9cf4d303370df518cc846377d
created_at: '2026-02-06T04:35:28.154316+00:00'
subtasks:
- T007
- T008
- T009
- T010
- T011
- T012
phase: Phase 2 - User Story 1 (Admin Management)
assignee: ''
agent: "gemini-review"
shell_pid: "99983"
review_status: "approved"
reviewed_by: "Kent Gale"
history:
- timestamp: '2026-02-06T04:30:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP02 -- Admin UI Dialog + Menu Integration

## Important: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Implementation Command

```bash
spec-kitty implement WP02 --base WP01
```

Depends on WP01 (needs RecipeCategory model and service).

---

## Objectives & Success Criteria

- Create a RecipeCategoriesDialog for CRUD management of recipe categories.
- Add "Recipe Categories..." menu item to the Catalog menu.
- Support add, edit, delete, and reorder operations in the dialog.
- Delete must be prevented for categories in use with informative message.

**Success criteria:**
- Dialog opens from Catalog > "Recipe Categories..."
- All CRUD operations work (add, edit, delete)
- Move up/down reorders categories (updates sort_order)
- Delete blocked with warning for in-use categories
- Single-instance window management (no duplicate dialogs)

## Context & Constraints

- **Spec**: `kitty-specs/096-recipe-category-management/spec.md`
- **Plan**: `kitty-specs/096-recipe-category-management/plan.md`
- **Constitution**: `.kittify/memory/constitution.md` -- Principle V (Layered Architecture -- UI calls service, not DB)

**Exemplar files to study**:
- `src/ui/hierarchy_admin_window.py` -- UI structure patterns (but NOT the tree view -- we need simpler list)
- `src/ui/main_window.py` lines 112-118 -- Catalog menu structure
- `src/ui/main_window.py` lines 375-395 -- Material admin handler pattern (lazy import, single instance, on_close)

**Key constraint**: RecipeCategory is FLAT (no hierarchy). Do NOT use Treeview in hierarchical mode. Use a simple list display with Listbox or single-level Treeview.

## Subtasks & Detailed Guidance

### Subtask T007 -- Create src/ui/catalog/ directory and __init__.py

- **Purpose**: Establish the new package for catalog-related UI components.
- **Steps**:
  1. Create directory `src/ui/catalog/`
  2. Create `src/ui/catalog/__init__.py` (empty or with brief docstring)
- **Files**: `src/ui/catalog/__init__.py` (new)
- **Notes**: This directory groups catalog management dialogs. Future dialogs could also go here.

### Subtask T008 -- Create RecipeCategoriesDialog with list view

- **Purpose**: Build the main dialog window showing all recipe categories.
- **Steps**:
  1. Create `src/ui/catalog/recipe_categories_dialog.py`
  2. Define `RecipeCategoriesDialog(ctk.CTkToplevel)`:
     - Constructor accepts `master` and optional `on_close` callback
     - Set window title "Recipe Categories"
     - Set reasonable size (500x600 or similar)
     - Create left panel with category list (use `ttk.Treeview` with columns: Name, Sort Order, Description)
     - Treeview should be single-level (no tree hierarchy)
     - Create right panel with action buttons: "Add", "Edit", "Delete", "Move Up", "Move Down"
     - Load categories on open: call `recipe_category_service.list_categories()`
     - Populate treeview with category data
  3. Add `_refresh_list()` method to reload categories from service
  4. Add window close handler that calls `on_close` callback
  5. Center dialog on parent window
- **Files**: `src/ui/catalog/recipe_categories_dialog.py` (new file)
- **Notes**: Import service lazily inside methods (not at module level) to avoid circular imports. Use `from src.services import recipe_category_service` pattern.

### Subtask T009 -- Add category edit form

- **Purpose**: Allow users to create and edit category details.
- **Steps**:
  1. Add `_show_add_dialog()` method:
     - Open a simple form dialog (CTkToplevel or CTkInputDialog)
     - Fields: Name (required), Description (optional), Sort Order (integer, default 0)
     - On save: call `recipe_category_service.create_category()`
     - Handle ValidationError (duplicate name) -- show error message
     - Refresh list after successful add
  2. Add `_show_edit_dialog()` method:
     - Pre-populate form with selected category's data
     - On save: call `recipe_category_service.update_category()`
     - Handle ValidationError -- show error message
     - Refresh list after successful edit
  3. Wire Add button to `_show_add_dialog()` and Edit button to `_show_edit_dialog()`
  4. Double-click on list item should also open edit
- **Files**: `src/ui/catalog/recipe_categories_dialog.py` (modify)
- **Notes**: Keep the form simple -- 3 fields. Use CTkEntry for name, CTkTextbox for description, CTkEntry for sort_order (with integer validation).

### Subtask T010 -- Implement delete confirmation with in-use validation

- **Purpose**: Safely delete categories with user confirmation and in-use protection.
- **Steps**:
  1. Add `_delete_selected()` method:
     - Get selected category from treeview
     - If nothing selected, show info message "Select a category to delete"
     - Check `recipe_category_service.is_category_in_use(category_id)`:
       - If in use: show error "Cannot delete '{name}': used by N recipe(s). Remove the category from those recipes first."
       - If not in use: show confirmation "Delete category '{name}'? This cannot be undone."
     - On confirm: call `recipe_category_service.delete_category(category_id)`
     - Refresh list after successful delete
  2. Wire Delete button to `_delete_selected()`
- **Files**: `src/ui/catalog/recipe_categories_dialog.py` (modify)
- **Notes**: Use `tkinter.messagebox.askokcancel()` for confirmation and `tkinter.messagebox.showerror()` for in-use warning.

### Subtask T011 -- Add sort order management (move up/down)

- **Purpose**: Allow users to reorder categories for display preference.
- **Steps**:
  1. Add `_move_up()` method:
     - Get selected category
     - Find the category above it in the list (previous sort_order)
     - Swap sort_order values between the two categories
     - Call `recipe_category_service.update_category()` for both
     - Refresh list and re-select the moved category
  2. Add `_move_down()` method:
     - Same logic but swap with category below
  3. Wire Move Up and Move Down buttons
  4. Disable Move Up for first item, Move Down for last item
- **Files**: `src/ui/catalog/recipe_categories_dialog.py` (modify)
- **Notes**: Categories are displayed in sort_order. When swapping, update both categories' sort_order values. If sort_orders are equal, use name-based tiebreaker.

### Subtask T012 -- Add "Recipe Categories..." menu item to Catalog menu

- **Purpose**: Make the dialog accessible from the application menu bar.
- **Steps**:
  1. Open `src/ui/main_window.py`
  2. Find the Catalog menu section (around line 112-118)
  3. Add after the existing Material Hierarchy item:
     ```python
     catalog_menu.add_command(
         label="Recipe Categories...", command=self._open_recipe_categories
     )
     ```
  4. Add `_open_recipe_categories()` handler method:
     ```python
     def _open_recipe_categories(self):
         """Open Recipe Categories admin dialog."""
         from src.ui.catalog.recipe_categories_dialog import RecipeCategoriesDialog

         if (
             hasattr(self, "_recipe_categories_dialog")
             and self._recipe_categories_dialog is not None
             and self._recipe_categories_dialog.winfo_exists()
         ):
             self._recipe_categories_dialog.focus()
             self._recipe_categories_dialog.lift()
             return

         def on_close():
             self._recipe_categories_dialog = None

         self._recipe_categories_dialog = RecipeCategoriesDialog(
             self, on_close=on_close
         )
     ```
- **Files**: `src/ui/main_window.py` (modify)
- **Parallel?**: Yes -- can be done alongside T008-T011
- **Notes**: Follow the exact pattern from `_open_material_admin()` (lines 375-395). Lazy import, single instance, on_close callback.

## Risks & Mitigations

- **Risk**: Dialog doesn't match existing UI style.
  **Mitigation**: Use same widget types (CTk*, ttk.Treeview) as HierarchyAdminWindow.

- **Risk**: Race condition with concurrent category edits.
  **Mitigation**: Single-instance dialog and refresh after each operation.

## Definition of Done Checklist

- [ ] RecipeCategoriesDialog exists and opens from Catalog menu
- [ ] Category list displays all categories in sort order
- [ ] Add operation creates new category with form validation
- [ ] Edit operation updates selected category
- [ ] Delete shows confirmation, blocks for in-use categories
- [ ] Move up/down reorders categories
- [ ] Single-instance window management works
- [ ] All existing tests continue to pass

## Review Guidance

- **Menu placement**: Verify "Recipe Categories..." appears in Catalog menu after Material Hierarchy
- **Dialog style**: Compare with existing dialogs for consistent look and feel
- **Error handling**: Verify ValidationError from service is shown as user-friendly message
- **Single instance**: Open dialog, try opening again -- should focus existing window
- **No service logic in UI**: All business logic must be in recipe_category_service

## Activity Log

- 2026-02-06T04:30:00Z -- system -- lane=planned -- Prompt created.
- 2026-02-06T04:35:28Z – claude-opus – shell_pid=96308 – lane=doing – Assigned agent via workflow command
- 2026-02-06T04:50:58Z – claude-opus – shell_pid=96308 – lane=for_review – Ready for review: RecipeCategoriesDialog with CRUD, reorder, menu integration. 3524 tests pass.
- 2026-02-06T04:51:24Z – gemini-review – shell_pid=99983 – lane=doing – Started review via workflow command
- 2026-02-06T05:32:18Z – gemini-review – shell_pid=99983 – lane=done – Review passed: All 8 DoD criteria verified. Dialog implements full CRUD + reorder via service layer. Menu integration follows existing pattern. Single-instance management correct. All 3524 tests pass. No business logic in UI. Lazy imports prevent circular deps.
