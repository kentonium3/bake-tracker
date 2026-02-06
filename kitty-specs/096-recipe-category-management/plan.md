# Implementation Plan: Recipe Category Management

**Branch**: `096-recipe-category-management` | **Date**: 2026-02-06 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/096-recipe-category-management/spec.md`

## Summary

Replace the hardcoded recipe category list in `finished_unit_form.py` with a database-driven system. Create a RecipeCategory model (simplified MaterialCategory, no hierarchy), CRUD service, admin UI dialog in the Catalog menu, form integration with validation, database seeding, and import/export support. Follows the MaterialCategory exemplar pattern throughout.

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: CustomTkinter (UI), SQLAlchemy 2.x (ORM)
**Storage**: SQLite with WAL mode
**Testing**: pytest
**Target Platform**: Desktop (macOS/Windows)
**Project Type**: Single desktop application
**Performance Goals**: N/A (CRUD operations on small dataset)
**Constraints**: Must preserve existing recipe category data. UI must follow existing Catalog menu patterns.
**Scale/Scope**: 1 new model, 1 new service, 1 new UI dialog, 2 existing files modified, import/export integration

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. User-Centric Design | PASS | Direct user value: Marianne can customize recipe taxonomy. Intuitive admin UI follows established pattern. |
| II. Data Integrity & FIFO | PASS | Migration preserves all existing category data. No FIFO impact. |
| III. Future-Proof Schema | PASS | BaseModel provides UUID, timestamps. Slug field enables future localization. |
| IV. Test-Driven Development | PASS | Service layer will have unit tests for all CRUD operations. |
| V. Layered Architecture | PASS | Model -> Service -> UI separation. UI calls service, not database. |
| VI.A. Error Handling | PASS | Exception-based returns per F094. ValidationError for invalid operations. |
| VI.B. Configuration | PASS | Default categories defined as constants, not hardcoded in UI. |
| VI.C. Dependency/Session | PASS | All service functions accept optional session parameter. |
| VI.D. API Consistency | PASS | Follows MaterialCategoryService CRUD patterns exactly. |
| VI.G. Code Organization | PASS | New files follow existing naming and location conventions. |
| VII. Schema Change Strategy | PASS | New table via create_all(). Seeding is idempotent. Reset/re-import compatible. |
| VIII. Pragmatic Aspiration | PASS | Service layer is UI-independent, API-ready for web migration. |

No violations. No complexity tracking needed.

## Research Findings

### MaterialCategory Exemplar Pattern (Confirmed)

**Model** (`src/models/material_category.py`):
- Inherits BaseModel (provides id, uuid, created_at, updated_at, to_dict())
- Fields: name (String 100, unique), slug (String 100, unique, indexed), description (Text), sort_order (Integer, default 0)
- Indexes on name and slug via `__table_args__`
- Custom `to_dict()` with optional relationship inclusion

**Service** (`src/services/material_catalog_service.py`, lines 224-431):
- `create_category()` - auto-generates slug via `slugify()`, handles collisions
- `get_category()` - raises `MaterialCategoryNotFound` (not return None)
- `list_categories()` - ordered by sort_order, then name
- `update_category()` - updates name, description, sort_order (not slug)
- `delete_category()` - checks for children, raises ValidationError if has dependents
- All functions use session parameter pattern with `_impl()` inner function

**UI** (`src/ui/hierarchy_admin_window.py`):
- Material categories use HierarchyAdminWindow with Treeview (tree structure)
- RecipeCategory is flat (no hierarchy), so needs a simpler list-based dialog
- Will create new `recipe_categories_dialog.py` with simpler list UI

**Menu** (`src/ui/main_window.py`, lines 112-118):
- Catalog menu with `add_command()` for each item
- Handler pattern: lazy import, single-instance window management, on_close callback

**Import/Export** (`src/services/import_export_service.py`):
- Export: query all categories, serialize to dict list
- Import: via `catalog_import_service.py`, UUID matching, ADD_ONLY/augment modes

**Database Seeding** (`src/services/database.py`):
- `seed_units()` pattern: check count, seed if empty, idempotent
- Called from `init_database()` after `Base.metadata.create_all()`

**Current Hardcoded List** (`src/ui/forms/finished_unit_form.py:155`):
```python
categories = ["Cakes", "Cookies", "Candies", "Brownies", "Bars", "Breads", "Other"]
```

**Recipe.category** (`src/models/recipe.py:118`):
- `category = Column(String(100), nullable=False, index=True)`
- Plain string, no FK, stays as-is per design decision

**Existing helper** (`src/services/recipe_service.py:1404`):
- `get_recipe_category_list()` returns distinct categories from Recipe table

### Key Design Decisions

1. **Flat categories, no hierarchy** - Unlike MaterialCategory's 3-level tree, recipe categories are a simple flat list. No parent/child relationships needed.
2. **Simple list dialog, not HierarchyAdminWindow** - Since there's no tree structure, create a simpler dialog with a listbox instead of treeview.
3. **Recipe.category stays as string** - No FK to recipe_categories. Validate on save with warning, not blocking error.
4. **Idempotent seeding** - Seed 7 defaults + discover existing Recipe.category values. Safe to run multiple times.

## Project Structure

### Files Created (this feature)

```
src/models/recipe_category.py           # RecipeCategory model
src/services/recipe_category_service.py # CRUD service
src/ui/catalog/recipe_categories_dialog.py  # Admin dialog
src/tests/test_recipe_category_service.py   # Service unit tests
```

### Files Modified (this feature)

```
src/ui/main_window.py                   # Add Catalog menu item
src/ui/forms/finished_unit_form.py      # Replace hardcoded list with DB query
src/services/database.py                # Add seed_recipe_categories()
src/services/import_export_service.py   # Add recipe_categories to export
src/services/catalog_import_service.py  # Add recipe_categories import
src/models/__init__.py                  # Register RecipeCategory model (if needed)
```

### Documentation (this feature)

```
kitty-specs/096-recipe-category-management/
├── spec.md
├── plan.md              # This file
├── checklists/
│   └── requirements.md
└── tasks.md             # Generated by /spec-kitty.tasks
```

**Structure Decision**: Follows existing bake-tracker project structure. New model in `src/models/`, new service in `src/services/`, new dialog in `src/ui/catalog/` (new subdirectory matching the menu location pattern).

## Implementation Approach

### WP01: RecipeCategory Model + Service + Tests

Create the data foundation: model, service with full CRUD, and unit tests.

**Model** (`src/models/recipe_category.py`):
- Inherit from BaseModel
- Fields: name, slug, sort_order, description
- Unique constraints on name and slug
- `to_dict()` override for serialization
- `__repr__()` for debugging

**Service** (`src/services/recipe_category_service.py`):
- `list_categories(session=None) -> List[RecipeCategory]` - ordered by sort_order, name
- `create_category(name, slug=None, sort_order=0, description=None, session=None) -> RecipeCategory`
- `update_category(category_id, name=None, sort_order=None, description=None, session=None) -> RecipeCategory`
- `delete_category(category_id, session=None) -> None` - raises ValidationError if in use
- `get_category_by_name(name, session=None) -> RecipeCategory` - raises exception if not found
- `get_category_by_id(category_id, session=None) -> RecipeCategory` - raises exception if not found
- `is_category_in_use(category_id, session=None) -> bool`
- Auto-generate slug from name using existing `slugify()` utility

**Tests** (`src/tests/test_recipe_category_service.py`):
- Test all CRUD operations
- Test slug auto-generation
- Test unique constraint enforcement
- Test delete validation (in-use prevention)
- Test sort ordering

**Exception** - Add `RecipeCategoryNotFound` to `src/services/exceptions.py`

### WP02: Admin UI Dialog + Menu Integration

Create the user-facing category management interface.

**Dialog** (`src/ui/catalog/recipe_categories_dialog.py`):
- CTkToplevel dialog with category list
- List widget showing categories in sort order
- Add/Edit/Delete buttons
- Edit form: name, description, sort_order fields
- Delete confirmation with in-use check
- Save/Cancel for edit operations
- Refresh list after changes

**Menu** (`src/ui/main_window.py`):
- Add `catalog_menu.add_command(label="Recipe Categories...", command=self._open_recipe_categories)`
- Add `_open_recipe_categories()` handler following material admin pattern (lazy import, single instance, on_close callback)

### WP03: Form Integration + Database Seeding

Connect the new system to existing workflows.

**Form update** (`src/ui/forms/finished_unit_form.py`):
- Replace line 155 hardcoded list with `recipe_category_service.list_categories()`
- Populate dropdown with `[cat.name for cat in categories]`
- Add save-time validation: warn if entered category not in database
- Offer auto-add option in warning dialog

**Database seeding** (`src/services/database.py`):
- Add `seed_recipe_categories()` function
- Default categories: Cakes, Cookies, Candies, Brownies, Bars, Breads, Other (with sort_order gaps of 10)
- Also discover distinct Recipe.category values and seed any not in defaults
- Idempotent: skip if categories already exist
- Call from `init_database()` after table creation

### WP04: Import/Export Support

Add data portability for recipe categories.

**Export** (`src/services/import_export_service.py`):
- Add `recipe_categories` to full backup export
- Add `recipe_categories` to catalog export
- Serialize: name, slug, sort_order, description, uuid

**Import** (`src/services/catalog_import_service.py`):
- Add `import_recipe_categories()` function
- Match by UUID or slug for duplicate detection
- Support ADD_ONLY and augment modes
- Return CatalogImportResult with counts

**Integration**:
- Wire into existing export/import orchestration
- Add `recipe_categories` key to export data structure

## Complexity Tracking

No constitution violations. No complexity justification needed.
