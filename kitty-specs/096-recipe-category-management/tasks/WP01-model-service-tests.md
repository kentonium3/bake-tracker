---
work_package_id: WP01
title: RecipeCategory Model + Service + Tests
lane: "done"
dependencies: []
base_branch: main
base_commit: a8ebe8b9e4b4d52e88ff0925deebde70244ae7d2
created_at: '2026-02-06T04:21:51.024739+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
phase: Phase 1 - Foundation
assignee: ''
agent: "gemini-review"
shell_pid: "96223"
review_status: "approved"
reviewed_by: "Kent Gale"
history:
- timestamp: '2026-02-06T04:30:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP01 -- RecipeCategory Model + Service + Tests

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
spec-kitty implement WP01
```

No dependencies (foundation package).

---

## Objectives & Success Criteria

- Create `RecipeCategory` model with all required fields and constraints.
- Create `recipe_category_service.py` with complete CRUD operations.
- Add `RecipeCategoryNotFound` exception to the exceptions module.
- Write comprehensive unit tests for all service functions.
- Register the new model in database initialization.

**Success criteria:**
- RecipeCategory model creates table with correct schema
- All CRUD service functions work with session parameter pattern
- Slug auto-generation produces correct kebab-case slugs
- Delete validation prevents deletion of in-use categories
- All new tests pass, all existing tests continue to pass

## Context & Constraints

- **Spec**: `kitty-specs/096-recipe-category-management/spec.md`
- **Plan**: `kitty-specs/096-recipe-category-management/plan.md`
- **Constitution**: `.kittify/memory/constitution.md` -- Principles IV (TDD), V (Layered Architecture), VI.C (Session Pattern), VI.D (API Consistency)

**Exemplar to follow**: `src/models/material_category.py` and `src/services/material_catalog_service.py` (category CRUD section, lines 224-431). Study these files before implementing.

**Key patterns to replicate**:
- BaseModel inheritance (provides id, uuid, created_at, updated_at)
- Session parameter pattern with `_impl()` inner function
- Exception-based returns (F094 pattern -- raise, don't return None)
- `slugify()` utility for slug generation

## Subtasks & Detailed Guidance

### Subtask T001 -- Create RecipeCategory model

- **Purpose**: Define the database table and ORM model for recipe categories.
- **Steps**:
  1. Create `src/models/recipe_category.py`
  2. Import BaseModel from `src/models/base.py`
  3. Define class `RecipeCategory(BaseModel)`:
     ```python
     __tablename__ = "recipe_categories"

     name = Column(String(100), nullable=False, unique=True)
     slug = Column(String(100), nullable=False, unique=True, index=True)
     sort_order = Column(Integer, nullable=False, default=0)
     description = Column(Text, nullable=True)
     ```
  4. Add `__table_args__` with indexes on name and slug (follow MaterialCategory pattern)
  5. Add `__repr__()` method returning `<RecipeCategory(name='{self.name}')>`
  6. Override `to_dict()` to include all fields:
     ```python
     def to_dict(self) -> dict:
         d = super().to_dict()
         d.update({
             "name": self.name,
             "slug": self.slug,
             "sort_order": self.sort_order,
             "description": self.description,
         })
         return d
     ```
- **Files**: `src/models/recipe_category.py` (new file)
- **Notes**: Study `src/models/material_category.py` for exact import style and BaseModel usage. Do NOT add hierarchy fields (parent_id, subcategories) -- RecipeCategory is flat.

### Subtask T002 -- Add RecipeCategoryNotFound exception

- **Purpose**: Provide a domain-specific exception for the service layer (F094 compliance).
- **Steps**:
  1. Open `src/services/exceptions.py`
  2. Add `RecipeCategoryNotFound` exception class following the existing naming pattern (`{Entity}NotFoundBy{LookupField}`)
  3. Create two variants:
     - `RecipeCategoryNotFoundById` (lookup by id)
     - `RecipeCategoryNotFoundByName` (lookup by name)
  4. Each should store the lookup value and provide a descriptive message
- **Files**: `src/services/exceptions.py` (modify)
- **Notes**: Follow the pattern of existing exceptions like `RecipeNotFoundBySlug`, `MaterialCategoryNotFound`. Check the exception hierarchy in the file.

### Subtask T003 -- Create recipe_category_service.py with list and create

- **Purpose**: Implement the first two CRUD operations following the service pattern.
- **Steps**:
  1. Create `src/services/recipe_category_service.py`
  2. Implement `list_categories(session=None) -> List[RecipeCategory]`:
     - Query all RecipeCategory ordered by sort_order, then name
     - Use session parameter pattern with `_impl()`
  3. Implement `create_category(name, slug=None, sort_order=0, description=None, session=None) -> RecipeCategory`:
     - Validate name is non-empty (raise ValidationError if empty)
     - Auto-generate slug from name using `slugify()` if slug not provided
     - Handle slug collisions (append numeric suffix if needed)
     - Create and return RecipeCategory instance
     - Raise ValidationError for duplicate name
  4. Import pattern:
     ```python
     from typing import List, Optional
     from sqlalchemy.orm import Session
     from src.models.recipe_category import RecipeCategory
     from src.services.database import session_scope
     from src.services.exceptions import RecipeCategoryNotFoundById, RecipeCategoryNotFoundByName, ValidationError
     ```
- **Files**: `src/services/recipe_category_service.py` (new file)
- **Notes**: Find the `slugify()` utility -- check `src/utils/` or `src/services/` for existing slug generation. The `material_catalog_service.py` uses `_generate_unique_slug()` -- replicate that pattern.

### Subtask T004 -- Add get, update, delete, and is_in_use operations

- **Purpose**: Complete the CRUD service with remaining operations.
- **Steps**:
  1. Add `get_category_by_id(category_id, session=None) -> RecipeCategory`:
     - Raise `RecipeCategoryNotFoundById` if not found
  2. Add `get_category_by_name(name, session=None) -> RecipeCategory`:
     - Raise `RecipeCategoryNotFoundByName` if not found
  3. Add `update_category(category_id, name=None, sort_order=None, description=None, session=None) -> RecipeCategory`:
     - Get category by ID (raises if not found)
     - Update only provided fields (skip None values)
     - Validate non-empty name if provided
     - Do NOT update slug after creation
  4. Add `is_category_in_use(category_id, session=None) -> bool`:
     - Query Recipe table for any recipe with `category` matching the RecipeCategory's name
     - Return True if any recipes use this category
  5. Add `delete_category(category_id, session=None) -> None`:
     - Get category by ID
     - Check `is_category_in_use()` -- raise ValidationError with count if in use
     - Delete the category
- **Files**: `src/services/recipe_category_service.py` (modify)
- **Notes**: For `is_category_in_use()`, query `Recipe.category == category.name` since Recipe.category is a string field (not a FK). Import Recipe model for this check.

### Subtask T005 -- Register RecipeCategory model in database init

- **Purpose**: Ensure the RecipeCategory table is created when the database initializes.
- **Steps**:
  1. Open `src/services/database.py`
  2. Find the `init_database()` function and its model imports section
  3. Add: `from ..models import recipe_category` (or appropriate import path matching existing pattern)
  4. This ensures SQLAlchemy's `Base.metadata.create_all()` knows about the table
- **Files**: `src/services/database.py` (modify)
- **Notes**: Check existing import pattern in `init_database()`. The import just needs to be executed so the model class registers with Base.metadata.

### Subtask T006 -- Write unit tests for all CRUD operations

- **Purpose**: Verify all service functions work correctly with edge cases.
- **Steps**:
  1. Create `src/tests/test_recipe_category_service.py`
  2. Test `create_category()`:
     - Happy path: name provided, slug auto-generated
     - Explicit slug provided
     - Duplicate name raises ValidationError
     - Empty name raises ValidationError
     - Sort order defaults to 0
  3. Test `list_categories()`:
     - Returns empty list when no categories
     - Returns categories ordered by sort_order, then name
  4. Test `get_category_by_id()`:
     - Happy path returns category
     - Non-existent ID raises RecipeCategoryNotFoundById
  5. Test `get_category_by_name()`:
     - Happy path returns category
     - Non-existent name raises RecipeCategoryNotFoundByName
  6. Test `update_category()`:
     - Update name only
     - Update sort_order only
     - Update description only
     - Non-existent ID raises exception
     - Empty name raises ValidationError
  7. Test `delete_category()`:
     - Happy path: unused category deleted
     - Category in use: raises ValidationError with recipe count
  8. Test `is_category_in_use()`:
     - Returns True when recipes use the category
     - Returns False when no recipes use it
- **Files**: `src/tests/test_recipe_category_service.py` (new file)
- **Parallel?**: Yes -- can be written alongside T003-T004 if different developer
- **Notes**: Use existing test patterns from `src/tests/`. Tests should use in-memory SQLite via test fixtures. Create Recipe instances in tests that reference category names to test delete validation.

## Risks & Mitigations

- **Risk**: Slug collision when categories have similar names.
  **Mitigation**: Use `_generate_unique_slug()` pattern that appends numeric suffix.

- **Risk**: Import circular dependency between recipe_category_service and recipe model.
  **Mitigation**: Import Recipe inside the function that needs it (lazy import in `is_category_in_use`).

## Definition of Done Checklist

- [ ] RecipeCategory model exists with all fields and constraints
- [ ] RecipeCategoryNotFoundById and RecipeCategoryNotFoundByName exceptions exist
- [ ] recipe_category_service.py has all 7 functions with session parameter pattern
- [ ] Slug auto-generation works correctly
- [ ] Delete validation prevents orphaning recipes
- [ ] Model registered in database init
- [ ] All new tests pass
- [ ] All existing tests continue to pass

## Review Guidance

- **Model**: Compare field definitions against MaterialCategory. Verify unique constraints and indexes.
- **Service**: Verify all functions use session parameter pattern. Check exception types match F094 convention.
- **Tests**: Verify edge cases covered (empty name, duplicate, delete-in-use).
- **No UI changes**: This WP is data layer only.

## Activity Log

- 2026-02-06T04:30:00Z -- system -- lane=planned -- Prompt created.
- 2026-02-06T04:21:51Z – claude-opus – shell_pid=94373 – lane=doing – Assigned agent via workflow command
- 2026-02-06T04:34:56Z – claude-opus – shell_pid=94373 – lane=for_review – Ready for review: RecipeCategory model, service with full CRUD, 31 tests all passing, 3524 total tests pass
- 2026-02-06T04:35:16Z – gemini-review – shell_pid=96223 – lane=doing – Started review via workflow command
- 2026-02-06T05:13:45Z – gemini-review – shell_pid=96223 – lane=done – Review passed: All 7 CRUD functions follow session pattern with _impl(). Exception types follow F094 convention. Model matches MaterialCategory pattern (simplified, no hierarchy). Slug auto-generation and collision handling correct. Delete validation prevents orphaning recipes. 31 tests cover happy paths, edge cases, and errors. 3524 total tests pass with zero regressions.
