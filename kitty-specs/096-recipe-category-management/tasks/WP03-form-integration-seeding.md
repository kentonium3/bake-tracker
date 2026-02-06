---
work_package_id: WP03
title: Form Integration + Database Seeding
lane: "doing"
dependencies: [WP01]
base_branch: 096-recipe-category-management-WP01
base_commit: b7f26a5b07ecebc9cf4d303370df518cc846377d
created_at: '2026-02-06T04:35:38.567178+00:00'
subtasks:
- T013
- T014
- T015
- T016
- T017
phase: Phase 2 - User Story 2 & 3 (Form + Migration)
assignee: ''
agent: ''
shell_pid: "96580"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-02-06T04:30:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP03 -- Form Integration + Database Seeding

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
spec-kitty implement WP03 --base WP01
```

Depends on WP01 (needs RecipeCategory model and service).

---

## Objectives & Success Criteria

- Seed the database with default recipe categories on initialization.
- Replace the hardcoded category list in finished_unit_form.py with a database query.
- Add validation warning when users enter a category not in the database.
- Provide auto-add option in the warning dialog.

**Success criteria:**
- App starts with 7 default categories in recipe_categories table
- Existing Recipe.category values are also seeded
- Finished Unit form dropdown shows database categories in sort order
- Warning appears for unlisted categories with option to add
- Seeding is idempotent (safe to run multiple times)

## Context & Constraints

- **Spec**: `kitty-specs/096-recipe-category-management/spec.md`
- **Plan**: `kitty-specs/096-recipe-category-management/plan.md`
- **Constitution**: `.kittify/memory/constitution.md` -- Principles II (Data Integrity), VII (Schema Change Strategy)

**Key files to study**:
- `src/services/database.py` -- `init_database()` and `seed_units()` pattern (idempotent seeding)
- `src/ui/forms/finished_unit_form.py` line 155 -- current hardcoded list
- `src/services/recipe_service.py` line 1404 -- `get_recipe_category_list()` (existing helper that gets distinct categories from recipes)

**Design decision**: Recipe.category stays as a string field. No FK. Validate on save with warning, not blocking error.

## Subtasks & Detailed Guidance

### Subtask T013 -- Add seed_recipe_categories() to database.py

- **Purpose**: Seed default categories so the dropdown is populated on first run.
- **Steps**:
  1. Open `src/services/database.py`
  2. Add a `seed_recipe_categories()` function following the `seed_units()` pattern:
     ```python
     def seed_recipe_categories() -> None:
         """Seed default recipe categories. Idempotent."""
         from ..models.recipe_category import RecipeCategory
         from ..models.recipe import Recipe

         with session_scope() as session:
             existing_count = session.query(RecipeCategory).count()
             if existing_count > 0:
                 logger.debug("Recipe categories already exist, skipping seed")
                 return

             # Default categories with sort_order gaps for easy reordering
             defaults = [
                 ("Cakes", "cakes", 10),
                 ("Cookies", "cookies", 20),
                 ("Candies", "candies", 30),
                 ("Brownies", "brownies", 40),
                 ("Bars", "bars", 50),
                 ("Breads", "breads", 60),
                 ("Other", "other", 70),
             ]

             # Also discover existing recipe categories not in defaults
             default_names = {name for name, _, _ in defaults}
             existing_recipe_cats = (
                 session.query(Recipe.category)
                 .distinct()
                 .filter(Recipe.category.isnot(None))
                 .all()
             )

             sort_order = 80
             for (cat_name,) in existing_recipe_cats:
                 if cat_name and cat_name not in default_names:
                     slug = cat_name.lower().replace(" ", "-")
                     defaults.append((cat_name, slug, sort_order))
                     sort_order += 10

             for name, slug, order in defaults:
                 category = RecipeCategory(
                     name=name, slug=slug, sort_order=order
                 )
                 session.add(category)

             logger.info(f"Seeded {len(defaults)} recipe categories")
     ```
  3. Import logger if not already imported at module level
- **Files**: `src/services/database.py` (modify)
- **Parallel?**: Yes -- different file from T015-T017
- **Notes**: The key pattern is idempotency -- check if categories exist before seeding. Use sort_order gaps of 10 to allow easy reordering later.

### Subtask T014 -- Call seed_recipe_categories() from init_database()

- **Purpose**: Ensure categories are seeded whenever the database is initialized.
- **Steps**:
  1. In `src/services/database.py`, find `init_database()`
  2. After the existing `seed_units()` call, add:
     ```python
     seed_recipe_categories()
     ```
  3. Ensure this comes after `Base.metadata.create_all(engine)` so the table exists
- **Files**: `src/services/database.py` (modify)
- **Notes**: The order is: create tables -> seed units -> seed recipe categories. Seeding is idempotent so multiple calls are safe.

### Subtask T015 -- Replace hardcoded category list in finished_unit_form.py

- **Purpose**: Make the category dropdown database-driven instead of hardcoded.
- **Steps**:
  1. Open `src/ui/forms/finished_unit_form.py`
  2. Find line 155 (or nearby):
     ```python
     categories = ["Cakes", "Cookies", "Candies", "Brownies", "Bars", "Breads", "Other"]
     ```
  3. Replace with:
     ```python
     from src.services import recipe_category_service
     db_categories = recipe_category_service.list_categories()
     categories = [cat.name for cat in db_categories]
     ```
  4. If the import would cause circular dependency, use lazy import inside the method
  5. Ensure the empty string is still prepended: `values=[""] + categories`
  6. Verify the ComboBox still works with the dynamic list
- **Files**: `src/ui/forms/finished_unit_form.py` (modify)
- **Parallel?**: Yes -- different section from T016-T017
- **Notes**: The dropdown should refresh when the form is opened (not cached at class level). If categories change while the app is running, reopening the form should show updated list.

### Subtask T016 -- Add save-time validation warning for unlisted categories

- **Purpose**: Warn users when they enter a category not in the database, directing them to the admin UI.
- **Steps**:
  1. Find the save/submit handler in finished_unit_form.py
  2. Get the selected/entered category value
  3. Check if it exists in the database:
     ```python
     from src.services import recipe_category_service
     db_categories = recipe_category_service.list_categories()
     category_names = [cat.name for cat in db_categories]

     if entered_category and entered_category not in category_names:
         # Show warning
     ```
  4. Show a warning dialog:
     - Message: "Category '{entered_category}' is not in the database."
     - Suggestion: "Add it via Catalog > Recipe Categories, or click 'Add Now' to create it."
     - Buttons: "Add Now" | "Save Anyway" | "Cancel"
  5. If "Save Anyway": proceed with save (Recipe.category is a string, so any value is valid)
  6. If "Cancel": return to form without saving
- **Files**: `src/ui/forms/finished_unit_form.py` (modify)
- **Notes**: The warning is advisory, not blocking. Users can save any category string. The goal is to encourage using managed categories.

### Subtask T017 -- Add auto-add option in the warning dialog

- **Purpose**: Let users quickly add a new category from the save dialog without switching to admin UI.
- **Steps**:
  1. In the warning dialog from T016, handle "Add Now" button:
     ```python
     if response == "Add Now":
         try:
             recipe_category_service.create_category(
                 name=entered_category
             )
             # Category created, proceed with save
         except ValidationError as e:
             # Show error (e.g., duplicate)
             messagebox.showerror("Error", str(e))
             return
     ```
  2. After successful auto-add, proceed with the normal save flow
  3. The newly added category will appear in the dropdown next time the form opens
- **Files**: `src/ui/forms/finished_unit_form.py` (modify)
- **Notes**: Use a custom dialog with 3 buttons. `tkinter.messagebox` only supports 2 buttons, so you may need a simple CTkToplevel dialog or use `askyesnocancel` creatively (Yes=Add Now, No=Save Anyway, Cancel=Cancel).

## Risks & Mitigations

- **Risk**: Seeding runs on existing database with categories already present.
  **Mitigation**: Idempotent check (skip if count > 0).

- **Risk**: Existing recipes have category values not in defaults.
  **Mitigation**: seed_recipe_categories() discovers distinct Recipe.category values and adds them.

- **Risk**: Form dropdown is empty if no categories exist.
  **Mitigation**: Seeding ensures defaults exist. Empty list is valid (user can type).

## Definition of Done Checklist

- [ ] seed_recipe_categories() exists and is idempotent
- [ ] init_database() calls seed_recipe_categories()
- [ ] Default 7 categories seeded on fresh database
- [ ] Existing recipe category values discovered and seeded
- [ ] Hardcoded list removed from finished_unit_form.py
- [ ] Form dropdown populated from database
- [ ] Warning shown for unlisted categories
- [ ] "Add Now" option creates category and proceeds with save
- [ ] All existing tests continue to pass

## Review Guidance

- **Seeding**: Verify idempotency by running init_database() twice
- **Form**: Verify dropdown shows database categories, not hardcoded list
- **Warning**: Enter a non-existent category and verify all 3 options work
- **Data preservation**: Verify existing recipe categories are discovered during seeding
- **No FK change**: Confirm Recipe.category is still a plain string column

## Activity Log

- 2026-02-06T04:30:00Z -- system -- lane=planned -- Prompt created.
