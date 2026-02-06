# Work Packages: Recipe Category Management

**Inputs**: Design documents from `kitty-specs/096-recipe-category-management/`
**Prerequisites**: plan.md (required), spec.md (user stories)

**Organization**: Fine-grained subtasks (`Txxx`) roll up into work packages (`WPxx`). Each work package must be independently deliverable and testable.

**Prompt Files**: Each work package references a matching prompt file in `tasks/`.

---

## Work Package WP01: RecipeCategory Model + Service + Tests (Priority: P0)

**Goal**: Create the data foundation -- RecipeCategory model, CRUD service with full session parameter pattern, exception type, and unit tests.
**Independent Test**: Service unit tests pass. CRUD operations work via service functions. Slug auto-generation works. Delete validation prevents orphaning recipes.
**Prompt**: `tasks/WP01-model-service-tests.md`
**Estimated Size**: ~450 lines

### Included Subtasks
- [x] T001 Create RecipeCategory model in `src/models/recipe_category.py`
- [x] T002 Add RecipeCategoryNotFound exception to `src/services/exceptions.py`
- [x] T003 Create recipe_category_service.py with list and create operations
- [x] T004 Add get, update, delete, and is_in_use operations to service
- [x] T005 Register RecipeCategory model in database init imports
- [x] T006 [P] Write unit tests for all CRUD operations

### Implementation Notes
- Follow MaterialCategory model exactly (simplified: no hierarchy/subcategories)
- All service functions must use session parameter pattern with `_impl()` inner function
- Use existing `slugify()` utility for slug auto-generation
- `get_category_by_name()` and `get_category_by_id()` raise exceptions (F094 pattern)
- `delete_category()` checks Recipe.category usage via query

### Parallel Opportunities
- T006 (tests) can be written in parallel with T003-T004 if files are split

### Dependencies
- None (foundation package)

### Risks & Mitigations
- Slug collision: Use `_generate_unique_slug()` pattern from material_catalog_service
- Test database: Use existing test fixtures and in-memory SQLite

---

## Work Package WP02: Admin UI Dialog + Menu Integration (Priority: P1)

**Goal**: Create user-facing admin dialog for recipe category CRUD and add it to the Catalog menu.
**Independent Test**: Open app, click Catalog > "Recipe Categories...", dialog opens with categories. Add, edit, delete, reorder operations work.
**Prompt**: `tasks/WP02-admin-ui-dialog.md`
**Estimated Size**: ~500 lines

### Included Subtasks
- [x] T007 Create `src/ui/catalog/` directory and `__init__.py`
- [x] T008 Create RecipeCategoriesDialog with list view and action buttons
- [x] T009 Add category edit form (name, description, sort_order fields)
- [x] T010 Implement delete confirmation with in-use validation
- [x] T011 Add sort order management (move up/down buttons)
- [x] T012 Add "Recipe Categories..." menu item to Catalog menu in main_window.py

### Implementation Notes
- Dialog is CTkToplevel (not HierarchyAdminWindow -- flat list, not tree)
- Follow material admin handler pattern: lazy import, single instance, on_close callback
- Category list uses Listbox or Treeview (single-level, not hierarchical)
- Delete button shows confirmation with recipe count if category in use
- Sort order adjusted via move up/down buttons (swap sort_order values)

### Parallel Opportunities
- T012 (menu integration) can proceed in parallel with T008-T011

### Dependencies
- Depends on WP01 (needs model and service)

### Risks & Mitigations
- UI responsiveness: Keep service calls off main thread for large datasets (unlikely for categories, but good practice)
- Window management: Follow single-instance pattern to prevent duplicate dialogs

---

## Work Package WP03: Form Integration + Database Seeding (Priority: P1)

**Goal**: Replace hardcoded category list in finished_unit_form.py with database query. Seed database with default and existing categories.
**Independent Test**: App starts with 7 default categories in database. Finished Unit form dropdown shows database categories. Warning appears for unlisted categories.
**Prompt**: `tasks/WP03-form-integration-seeding.md`
**Estimated Size**: ~400 lines

### Included Subtasks
- [x] T013 Add seed_recipe_categories() to database.py
- [x] T014 Call seed_recipe_categories() from init_database()
- [x] T015 Replace hardcoded category list in finished_unit_form.py with database query
- [x] T016 Add save-time validation warning for unlisted categories
- [x] T017 Add auto-add option in the warning dialog

### Implementation Notes
- Seeding must be idempotent (check count before seeding)
- Default categories: Cakes, Cookies, Candies, Brownies, Bars, Breads, Other (sort_order gaps of 10)
- Also discover distinct Recipe.category values and seed any not in defaults
- Form dropdown: `[cat.name for cat in recipe_category_service.list_categories()]`
- Warning on save: "Category 'X' not in database. Add it via Catalog > Recipe Categories?" with Add/Cancel

### Parallel Opportunities
- T013-T014 (seeding) can proceed in parallel with T015-T017 (form) since different files

### Dependencies
- Depends on WP01 (needs model and service)

### Risks & Mitigations
- Existing data: Seeding discovers existing Recipe.category values to prevent data loss
- Empty categories table: Form gracefully handles empty list (shows empty dropdown)

---

## Work Package WP04: Import/Export Support (Priority: P2)

**Goal**: Add recipe categories to full backup export and catalog export/import.
**Independent Test**: Export full backup, verify recipe_categories in JSON. Import backup with categories, verify no duplicates created. Round-trip preserves all data.
**Prompt**: `tasks/WP04-import-export.md`
**Estimated Size**: ~400 lines

### Included Subtasks
- [x] T018 Add recipe_categories to full backup export in import_export_service.py
- [x] T019 Add recipe_categories to catalog export
- [x] T020 Create import_recipe_categories() in catalog_import_service.py
- [x] T021 Wire recipe category import into main import orchestration
- [x] T022 Add round-trip test (export -> import -> verify)

### Implementation Notes
- Export format: `{"name", "slug", "sort_order", "description", "uuid"}`
- Import: match by UUID first, then slug for duplicate detection
- Support ADD_ONLY and augment modes (follow material_categories pattern)
- Return CatalogImportResult with entity counts
- Wire into existing import/export orchestration (same location as material_categories)

### Parallel Opportunities
- T018-T019 (export) and T020-T021 (import) touch different sections of the files

### Dependencies
- Depends on WP01 (needs model and service)
- Independent of WP02 and WP03

### Risks & Mitigations
- Import conflicts: UUID matching first, then slug fallback ensures correct dedup
- Backward compatibility: Missing recipe_categories key in old exports should be handled gracefully

---

## Dependency & Execution Summary

- **Sequence**: WP01 → {WP02, WP03, WP04} (WP02-04 can run in parallel after WP01)
- **Parallelization**: WP02 (UI), WP03 (form+seeding), WP04 (import/export) are independent and can be implemented by different agents simultaneously
- **MVP Scope**: WP01 + WP03 constitute the minimal release (database-driven categories replacing hardcoded list, with seeding)

---

## Subtask Index (Reference)

| Subtask ID | Summary | Work Package | Priority | Parallel? |
|------------|---------|--------------|----------|-----------|
| T001 | Create RecipeCategory model | WP01 | P0 | No |
| T002 | Add RecipeCategoryNotFound exception | WP01 | P0 | No |
| T003 | Create service with list/create operations | WP01 | P0 | No |
| T004 | Add get/update/delete/is_in_use to service | WP01 | P0 | No |
| T005 | Register model in database init | WP01 | P0 | No |
| T006 | Write unit tests for CRUD operations | WP01 | P0 | Yes |
| T007 | Create src/ui/catalog/ directory | WP02 | P1 | No |
| T008 | Create RecipeCategoriesDialog with list view | WP02 | P1 | No |
| T009 | Add category edit form | WP02 | P1 | No |
| T010 | Implement delete confirmation with in-use check | WP02 | P1 | No |
| T011 | Add sort order management (move up/down) | WP02 | P1 | No |
| T012 | Add menu item to Catalog menu | WP02 | P1 | Yes |
| T013 | Add seed_recipe_categories() to database.py | WP03 | P1 | Yes |
| T014 | Call seed from init_database() | WP03 | P1 | No |
| T015 | Replace hardcoded list in finished_unit_form.py | WP03 | P1 | Yes |
| T016 | Add save-time validation warning | WP03 | P1 | No |
| T017 | Add auto-add option in warning dialog | WP03 | P1 | No |
| T018 | Add recipe_categories to full backup export | WP04 | P2 | Yes |
| T019 | Add recipe_categories to catalog export | WP04 | P2 | Yes |
| T020 | Create import_recipe_categories() | WP04 | P2 | No |
| T021 | Wire import into orchestration | WP04 | P2 | No |
| T022 | Add round-trip test | WP04 | P2 | No |
