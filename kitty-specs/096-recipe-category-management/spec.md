# Feature Specification: Recipe Category Management

**Feature Branch**: `096-recipe-category-management`
**Created**: 2026-02-05
**Status**: Draft
**Input**: F096 func-spec -- replace hardcoded recipe category list with database-driven management system following MaterialCategory pattern.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Admin Manages Recipe Categories (Priority: P1)

The user (Marianne) opens the Catalog menu and selects "Recipe Categories..." to open an admin dialog. She can view all current categories, add new ones (e.g., "Tarts", "Pastries"), edit existing ones, reorder them, and delete unused ones. The dialog follows the same pattern as Ingredient Hierarchy and Material Hierarchy management.

**Why this priority**: This is the core feature -- without category management UI, the user cannot customize their recipe taxonomy. Everything else depends on categories existing in the database.

**Independent Test**: Open app, go to Catalog menu, click "Recipe Categories...", verify dialog opens with the 7 default categories. Add "Tarts", edit "Other" to "Miscellaneous", reorder "Cookies" to the top, delete "Bars" (if unused). Verify changes persist after closing and reopening.

**Acceptance Scenarios**:

1. **Given** the app is running, **When** the user clicks Catalog > "Recipe Categories...", **Then** a dialog opens showing all recipe categories in sort order.
2. **Given** the category dialog is open, **When** the user clicks Add, enters "Tarts", and saves, **Then** "Tarts" appears in the list and persists after dialog close/reopen.
3. **Given** a category is not used by any recipe, **When** the user selects it and clicks Delete, **Then** the category is removed after confirmation.
4. **Given** a category IS used by recipes, **When** the user selects it and clicks Delete, **Then** the delete is prevented with a message showing how many recipes use it.
5. **Given** multiple categories exist, **When** the user reorders them, **Then** the new sort order persists and is reflected in all dropdowns.

---

### User Story 2 - Form Dropdown Uses Database Categories (Priority: P2)

When creating or editing a Finished Unit, the category dropdown is populated from the database instead of a hardcoded list. If the user types a category not in the database, a warning suggests adding it via Catalog > Recipe Categories first.

**Why this priority**: This connects the category management to the actual workflow. Without it, the database categories aren't used anywhere meaningful.

**Independent Test**: Open the Finished Unit form, verify the category dropdown shows categories from the database (in sort order). Type a non-existent category name and attempt to save -- verify a warning appears.

**Acceptance Scenarios**:

1. **Given** categories exist in the database, **When** the user opens the Finished Unit form, **Then** the category dropdown shows database categories in sort order.
2. **Given** a new category "Tarts" was added via admin UI, **When** the user opens the Finished Unit form, **Then** "Tarts" appears in the dropdown.
3. **Given** the user types a category not in the database, **When** they attempt to save, **Then** a warning appears suggesting they add it via Catalog > Recipe Categories, with an option to auto-add or cancel.

---

### User Story 3 - Existing Data Migrated Safely (Priority: P2)

When the database is initialized or upgraded, the 7 existing hardcoded categories plus any distinct categories found in existing recipe data are automatically seeded into the recipe_categories table. No recipe data is lost or broken.

**Why this priority**: Equal to P2 because migration must work for the feature to be usable. Existing data integrity is non-negotiable.

**Independent Test**: Start app with existing database containing recipes with various categories. Verify all distinct category values are present in the recipe_categories table. Verify all recipes still display their correct categories.

**Acceptance Scenarios**:

1. **Given** a fresh database, **When** the app starts, **Then** the 7 default categories (Cakes, Cookies, Candies, Brownies, Bars, Breads, Other) are seeded.
2. **Given** an existing database with recipes using "Pies" (a custom category), **When** the migration runs, **Then** "Pies" is added to the recipe_categories table alongside the defaults.
3. **Given** recipes with existing category values, **When** the migration completes, **Then** all recipes retain their original category strings.

---

### User Story 4 - Categories Included in Backup/Restore (Priority: P3)

Recipe categories are included in full backup exports and catalog exports. Importing a backup restores categories without duplicating existing ones.

**Why this priority**: Data portability is important but secondary to core functionality. The user needs backup/restore to work but won't use it daily.

**Independent Test**: Export a full backup, delete a category, import the backup. Verify the deleted category is restored. Export again and verify the import/export cycle preserves all data.

**Acceptance Scenarios**:

1. **Given** recipe categories exist, **When** a full backup is exported, **Then** the export includes recipe category data.
2. **Given** an export file with recipe categories, **When** imported into a database with some matching categories, **Then** duplicates are skipped (by slug) and new categories are added.
3. **Given** a catalog export, **When** performed, **Then** recipe categories are included alongside other catalog data.

---

### Edge Cases

- What happens when the user deletes ALL categories? The system should allow it but the form dropdown will be empty. This is acceptable -- the user can always add categories back.
- What happens when two categories have the same name but different case (e.g., "cookies" vs "Cookies")? The unique constraint should be case-insensitive to prevent this.
- What happens when Recipe.category contains a value not in recipe_categories table? The recipe still displays correctly (string field), but the value won't appear in the dropdown. Migration should catch all existing values.
- What happens during import when a category slug matches but the name differs? The import should skip the duplicate (match by slug, not name).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a RecipeCategory database table with fields: id, name, slug, sort_order, description, created_at, updated_at
- **FR-002**: System MUST enforce unique constraints on RecipeCategory name and slug
- **FR-003**: System MUST provide CRUD service functions (list, create, update, delete, get_by_name) following the session parameter pattern
- **FR-004**: System MUST prevent deletion of categories that are in use by recipes
- **FR-005**: System MUST auto-generate slug from name when slug is not provided
- **FR-006**: System MUST provide an admin dialog accessible via Catalog > "Recipe Categories..." menu item
- **FR-007**: Admin dialog MUST support add, edit, delete, and reorder operations
- **FR-008**: System MUST populate the Finished Unit form category dropdown from the database
- **FR-009**: System MUST warn when a user enters a category not in the database during save, with an option to auto-add it
- **FR-010**: System MUST seed default categories (Cakes, Cookies, Candies, Brownies, Bars, Breads, Other) on database initialization
- **FR-011**: System MUST discover and seed any additional distinct categories from existing recipe data during migration
- **FR-012**: System MUST include recipe categories in full backup and catalog exports
- **FR-013**: System MUST support importing recipe categories with duplicate detection by slug
- **FR-014**: Recipe.category field MUST remain a string (no foreign key) with validation against the database on save

### Key Entities

- **RecipeCategory**: Database table storing user-customizable recipe categories. Fields: id, name (unique), slug (unique), sort_order, description, timestamps. Flat structure (no hierarchy).
- **Recipe**: Existing model with `category` string field. Not modified structurally -- validation added at save time against RecipeCategory table.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Zero hardcoded category lists remain in UI code (down from 1 in finished_unit_form.py)
- **SC-002**: Users can add, edit, delete, and reorder recipe categories without code changes
- **SC-003**: Category dropdown in Finished Unit form shows database-driven categories in sort order
- **SC-004**: All existing recipe data preserved after migration -- no data loss
- **SC-005**: Delete prevention works for categories in use -- 100% of deletion attempts for in-use categories are blocked with informative message
- **SC-006**: Import/export cycle preserves all category data with no duplicates created
- **SC-007**: All existing tests continue to pass after implementation
- **SC-008**: Recipe Categories menu item appears in Catalog menu consistent with Ingredient/Material Hierarchy placement
