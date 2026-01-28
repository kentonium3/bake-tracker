---
work_package_id: WP02
title: Recipe Service Slug Generation
lane: "done"
dependencies: [WP01]
base_branch: 080-recipe-slug-support-WP01
base_commit: 66d36d44d002cb8ddd617bb2075cb49b881ea664
created_at: '2026-01-28T16:50:29.245025+00:00'
subtasks:
- T006
- T007
- T008
- T009
- T010
- T011
- T012
phase: Phase 0 - Foundation
assignee: ''
agent: "claude-code"
shell_pid: "57085"
review_status: "approved"
reviewed_by: "Kent Gale"
history:
- timestamp: '2026-01-28T07:45:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP02 – Recipe Service Slug Generation

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Implementation Command

```bash
# Depends on WP01
spec-kitty implement WP02 --base WP01
```

---

## Objectives & Success Criteria

**Objective**: Implement slug generation methods in RecipeService with collision handling and rename support.

**Success Criteria**:
- [ ] `_generate_slug(name)` creates valid slugs from recipe names
- [ ] `_generate_unique_slug(name, session, exclude_id)` handles collisions with -2, -3 suffixes
- [ ] `create_recipe()` generates slug automatically
- [ ] `update_recipe()` handles rename: regenerates slug, preserves old slug in `previous_slug`
- [ ] Unit tests cover slug generation with various inputs
- [ ] Unit tests cover collision handling
- [ ] Unit tests cover rename behavior
- [ ] All tests pass

---

## Context & Constraints

**Reference Documents**:
- Plan: `kitty-specs/080-recipe-slug-support/plan.md`
- Research: `kitty-specs/080-recipe-slug-support/research.md`

**Pattern Sources (COPY EXACTLY)**:
- `_generate_slug()`: `src/services/finished_unit_service.py:629-652`
- `_generate_unique_slug()`: `src/services/finished_unit_service.py:655-679`

**Constraints**:
- Slug format: lowercase, hyphens (NOT underscores), alphanumeric-and-hyphens only
- Max length: 200 characters (truncate if longer)
- Collision suffix: `-2`, `-3`, etc. (NOT `_2` like Supplier)
- Max collision attempts: 1000 (raise ValidationError if exceeded)

---

## Subtasks & Detailed Guidance

### Subtask T006 – Create `_generate_slug()` Static Method

**Purpose**: Generate a URL-safe slug from a recipe name.

**Steps**:
1. Open `src/services/recipe_service.py`
2. Add imports at top:
   ```python
   import re
   import unicodedata
   ```

3. Add the static method to RecipeService class:
   ```python
   @staticmethod
   def _generate_slug(name: str) -> str:
       """Generate URL-safe slug from recipe name.

       Args:
           name: Recipe name to convert to slug

       Returns:
           Lowercase slug with hyphens, alphanumeric only
       """
       if not name:
           return "unknown-recipe"

       # Normalize unicode characters (handles accents like  -> e)
       slug = unicodedata.normalize("NFKD", name)
       slug = slug.encode("ascii", "ignore").decode("ascii")

       # Convert to lowercase
       slug = slug.lower()

       # Replace spaces and underscores with hyphens
       slug = re.sub(r"[\s_]+", "-", slug)

       # Remove non-alphanumeric characters (except hyphens)
       slug = re.sub(r"[^a-z0-9-]", "", slug)

       # Collapse multiple hyphens
       slug = re.sub(r"-+", "-", slug)

       # Remove leading/trailing hyphens
       slug = slug.strip("-")

       # Ensure not empty
       if not slug:
           return "unknown-recipe"

       # Limit length (200 chars)
       if len(slug) > 200:
           slug = slug[:200].rstrip("-")

       return slug
   ```

**Files**:
- `src/services/recipe_service.py` (modify)

**Pattern Reference**: `src/services/finished_unit_service.py:629-652`

**Test Cases**:
| Input | Expected Output |
|-------|-----------------|
| "Chocolate Chip Cookies" | "chocolate-chip-cookies" |
| "Grandma's Apple Pie" | "grandmas-apple-pie" |
| "Crme Brle" | "creme-brulee" |
| "Test Recipe 2025!" | "test-recipe-2025" |
| "" | "unknown-recipe" |
| "   " | "unknown-recipe" |
| "a" * 250 | 200-char truncated slug |

---

### Subtask T007 – Create `_generate_unique_slug()` Method

**Purpose**: Generate a unique slug, appending numeric suffix if collision detected.

**Steps**:
1. Add to RecipeService class:
   ```python
   @staticmethod
   def _generate_unique_slug(
       name: str,
       session: Session,
       exclude_id: Optional[int] = None
   ) -> str:
       """Generate unique slug, adding suffix if collision detected.

       Args:
           name: Recipe name to convert to slug
           session: Database session for uniqueness check
           exclude_id: Recipe ID to exclude from collision check (for updates)

       Returns:
           Unique slug string

       Raises:
           ValidationError: If unable to generate unique slug after 1000 attempts
       """
       from src.models.recipe import Recipe

       base_slug = RecipeService._generate_slug(name)

       max_attempts = 1000
       for attempt in range(max_attempts):
           if attempt == 0:
               candidate_slug = base_slug
           else:
               candidate_slug = f"{base_slug}-{attempt + 1}"

           # Check for existing slug
           query = session.query(Recipe).filter(Recipe.slug == candidate_slug)
           if exclude_id:
               query = query.filter(Recipe.id != exclude_id)

           existing = query.first()
           if not existing:
               return candidate_slug

       raise ValidationError(
           f"Unable to generate unique slug for '{name}' after {max_attempts} attempts"
       )
   ```

2. Ensure ValidationError import exists:
   ```python
   from src.utils.exceptions import ValidationError
   ```

   If ValidationError doesn't exist, create a simple one or use ValueError.

**Files**:
- `src/services/recipe_service.py` (modify)

**Pattern Reference**: `src/services/finished_unit_service.py:655-679`

**Notes**:
- Uses `-2`, `-3` suffix (not `-1` - first collision gets `-2`)
- exclude_id prevents self-collision during updates
- 1000 attempts is generous; in practice, collisions are rare

---

### Subtask T008 – Update `create_recipe()` to Generate Slug

**Purpose**: Ensure new recipes automatically get unique slugs.

**Steps**:
1. Find `create_recipe()` method in `src/services/recipe_service.py`
2. Add slug generation before creating the Recipe object:
   ```python
   def create_recipe(
       self,
       name: str,
       category: Optional[str] = None,
       # ... other params ...
       session: Optional[Session] = None
   ) -> Recipe:
       """Create a new recipe with auto-generated slug."""

       def _create_impl(sess: Session) -> Recipe:
           # Generate unique slug
           slug = RecipeService._generate_unique_slug(name, sess)

           recipe = Recipe(
               name=name,
               slug=slug,  # Add this field
               category=category,
               # ... other fields ...
           )
           sess.add(recipe)
           sess.flush()
           return recipe

       if session:
           return _create_impl(session)
       with session_scope() as sess:
           return _create_impl(sess)
   ```

**Files**:
- `src/services/recipe_service.py` (modify)

**Notes**:
- The event listener in WP01 provides fallback, but explicit generation here enables collision handling
- Use `_generate_unique_slug()` to ensure uniqueness
- Pass session to avoid nested session issues

---

### Subtask T009 – Update `update_recipe()` for Rename Handling

**Purpose**: When recipe name changes, regenerate slug and preserve old slug in `previous_slug`.

**Steps**:
1. Find `update_recipe()` method in `src/services/recipe_service.py`
2. Add rename detection and slug handling:
   ```python
   def update_recipe(
       self,
       recipe_id: int,
       name: Optional[str] = None,
       # ... other params ...
       session: Optional[Session] = None
   ) -> Recipe:
       """Update recipe, handling name changes with slug regeneration."""

       def _update_impl(sess: Session) -> Recipe:
           recipe = sess.query(Recipe).filter(Recipe.id == recipe_id).first()
           if not recipe:
               raise ValidationError(f"Recipe with id {recipe_id} not found")

           # Check if name is changing
           if name is not None and name != recipe.name:
               # Preserve current slug in previous_slug
               recipe.previous_slug = recipe.slug

               # Generate new unique slug
               recipe.slug = RecipeService._generate_unique_slug(
                   name, sess, exclude_id=recipe_id
               )

               recipe.name = name

           # Update other fields as before...
           # (category, source, etc.)

           sess.flush()
           return recipe

       if session:
           return _update_impl(session)
       with session_scope() as sess:
           return _update_impl(sess)
   ```

**Files**:
- `src/services/recipe_service.py` (modify)

**Notes**:
- Only update slug if name actually changes
- Old slug goes to `previous_slug` (enables import compatibility)
- Previous `previous_slug` is discarded (one-rename grace period)
- Use exclude_id to prevent self-collision

---

### Subtask T010 – Add Unit Tests for Slug Generation

**Purpose**: Verify `_generate_slug()` produces correct output for various inputs.

**Steps**:
1. Create or update test file `src/tests/test_recipe_service.py`
2. Add tests:
   ```python
   import pytest
   from src.services.recipe_service import RecipeService


   class TestRecipeSlugGeneration:
       """Tests for RecipeService._generate_slug()"""

       def test_basic_slug_generation(self):
           """Test basic name to slug conversion."""
           assert RecipeService._generate_slug("Chocolate Chip Cookies") == "chocolate-chip-cookies"

       def test_apostrophe_removal(self):
           """Test apostrophes are removed."""
           assert RecipeService._generate_slug("Grandma's Apple Pie") == "grandmas-apple-pie"

       def test_unicode_normalization(self):
           """Test accented characters are normalized."""
           assert RecipeService._generate_slug("Crme Brle") == "creme-brulee"

       def test_special_characters_removed(self):
           """Test special characters are stripped."""
           assert RecipeService._generate_slug("Test Recipe 2025!") == "test-recipe-2025"
           assert RecipeService._generate_slug("Cookies & Cream") == "cookies-cream"

       def test_empty_name_fallback(self):
           """Test empty names return fallback slug."""
           assert RecipeService._generate_slug("") == "unknown-recipe"
           assert RecipeService._generate_slug("   ") == "unknown-recipe"
           assert RecipeService._generate_slug(None) == "unknown-recipe"  # if handling None

       def test_long_name_truncation(self):
           """Test names longer than 200 chars are truncated."""
           long_name = "a" * 250
           slug = RecipeService._generate_slug(long_name)
           assert len(slug) <= 200
           assert not slug.endswith("-")

       def test_multiple_spaces_collapsed(self):
           """Test multiple spaces become single hyphen."""
           assert RecipeService._generate_slug("Recipe   With   Spaces") == "recipe-with-spaces"

       def test_underscores_become_hyphens(self):
           """Test underscores are converted to hyphens."""
           assert RecipeService._generate_slug("Recipe_With_Underscores") == "recipe-with-underscores"
   ```

**Files**:
- `src/tests/test_recipe_service.py` (create or modify)

**Parallel**: Yes - can be written alongside T011, T012

---

### Subtask T011 – Add Unit Tests for Collision Handling

**Purpose**: Verify `_generate_unique_slug()` appends suffixes correctly.

**Steps**:
1. Add to test file:
   ```python
   class TestRecipeSlugCollision:
       """Tests for RecipeService._generate_unique_slug() collision handling."""

       def test_unique_slug_no_collision(self, session):
           """Test slug generation when no collision exists."""
           slug = RecipeService._generate_unique_slug("New Recipe", session)
           assert slug == "new-recipe"

       def test_unique_slug_with_collision(self, session):
           """Test suffix appended when collision detected."""
           # Create existing recipe
           from src.models.recipe import Recipe
           existing = Recipe(name="Test Recipe", slug="test-recipe")
           session.add(existing)
           session.flush()

           # Generate slug for another recipe with same name
           slug = RecipeService._generate_unique_slug("Test Recipe", session)
           assert slug == "test-recipe-2"

       def test_unique_slug_multiple_collisions(self, session):
           """Test incrementing suffix for multiple collisions."""
           from src.models.recipe import Recipe

           # Create recipes with slugs
           for i in range(3):
               suffix = "" if i == 0 else f"-{i + 1}"
               recipe = Recipe(name=f"Recipe {i}", slug=f"duplicate{suffix}")
               session.add(recipe)
           session.flush()

           # Should get -4
           slug = RecipeService._generate_unique_slug("Duplicate", session)
           assert slug == "duplicate-4"

       def test_unique_slug_exclude_self(self, session):
           """Test exclude_id prevents self-collision during update."""
           from src.models.recipe import Recipe

           existing = Recipe(name="My Recipe", slug="my-recipe")
           session.add(existing)
           session.flush()

           # Same slug should be returned when excluding self
           slug = RecipeService._generate_unique_slug(
               "My Recipe", session, exclude_id=existing.id
           )
           assert slug == "my-recipe"
   ```

**Files**:
- `src/tests/test_recipe_service.py` (modify)

**Note**: Tests need a session fixture. Check existing test patterns in codebase.

**Parallel**: Yes - can be written alongside T010, T012

---

### Subtask T012 – Add Unit Tests for Rename Behavior

**Purpose**: Verify `update_recipe()` correctly handles name changes.

**Steps**:
1. Add to test file:
   ```python
   class TestRecipeRename:
       """Tests for recipe rename behavior with slug preservation."""

       def test_rename_preserves_previous_slug(self, session):
           """Test renaming recipe stores old slug in previous_slug."""
           from src.services.recipe_service import RecipeService

           service = RecipeService()

           # Create recipe
           recipe = service.create_recipe("Original Name", session=session)
           original_slug = recipe.slug
           assert original_slug == "original-name"
           assert recipe.previous_slug is None

           # Rename
           updated = service.update_recipe(
               recipe.id, name="New Name", session=session
           )

           assert updated.name == "New Name"
           assert updated.slug == "new-name"
           assert updated.previous_slug == "original-name"

       def test_rename_twice_overwrites_previous_slug(self, session):
           """Test second rename discards first previous_slug."""
           service = RecipeService()

           recipe = service.create_recipe("First Name", session=session)
           service.update_recipe(recipe.id, name="Second Name", session=session)
           service.update_recipe(recipe.id, name="Third Name", session=session)

           assert recipe.slug == "third-name"
           assert recipe.previous_slug == "second-name"  # NOT "first-name"

       def test_update_without_name_change_preserves_slug(self, session):
           """Test updating other fields doesn't change slug."""
           service = RecipeService()

           recipe = service.create_recipe("My Recipe", session=session)
           original_slug = recipe.slug

           # Update category only
           service.update_recipe(recipe.id, category="Desserts", session=session)

           assert recipe.slug == original_slug
           assert recipe.previous_slug is None

       def test_rename_handles_collision(self, session):
           """Test rename with collision appends suffix."""
           service = RecipeService()

           # Create two recipes
           recipe1 = service.create_recipe("Target Name", session=session)
           recipe2 = service.create_recipe("Other Recipe", session=session)

           # Rename recipe2 to same name as recipe1
           service.update_recipe(recipe2.id, name="Target Name", session=session)

           assert recipe2.slug == "target-name-2"  # Collision handled
           assert recipe2.previous_slug == "other-recipe"
   ```

**Files**:
- `src/tests/test_recipe_service.py` (modify)

**Parallel**: Yes - can be written alongside T010, T011

---

## Test Strategy

**Run all tests after implementation**:
```bash
./run-tests.sh src/tests/test_recipe_service.py -v
```

**Expected test count**: ~15-20 new tests across three test classes

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Circular import with Recipe model | Use lazy import inside methods |
| Session handling issues | Follow existing session pattern (session=None parameter) |
| Collision loop infinite | 1000 attempt limit with clear error message |
| Unicode edge cases | Use unicodedata.normalize() pattern from FinishedUnitService |

---

## Definition of Done Checklist

- [ ] T006: `_generate_slug()` method implemented
- [ ] T007: `_generate_unique_slug()` method implemented with collision handling
- [ ] T008: `create_recipe()` generates slug automatically
- [ ] T009: `update_recipe()` handles rename with previous_slug preservation
- [ ] T010: Unit tests for slug generation pass
- [ ] T011: Unit tests for collision handling pass
- [ ] T012: Unit tests for rename behavior pass
- [ ] All existing tests still pass
- [ ] Code passes linting (`flake8 src/services/recipe_service.py`)

---

## Review Guidance

**Reviewers should verify**:
1. Slug format matches spec (lowercase, hyphens, alphanumeric)
2. Collision handling uses `-2`, `-3` suffix pattern
3. Rename correctly preserves previous_slug
4. Tests cover edge cases (empty, unicode, long names)
5. Session handling follows project patterns

---

## Activity Log

- 2026-01-28T07:45:00Z – system – lane=planned – Prompt created.
- 2026-01-28T16:57:37Z – claude-opus – shell_pid=48262 – lane=for_review – All T006-T012 subtasks implemented. 143 tests pass (113 existing + 30 new slug tests).
- 2026-01-28T17:30:45Z – claude-code – shell_pid=57085 – lane=doing – Started review via workflow command
- 2026-01-28T17:48:20Z – claude-code – shell_pid=57085 – lane=done – Review passed: All slug generation methods implemented correctly. _generate_slug handles unicode/special chars/max length, _generate_unique_slug handles collisions with -2/-3 suffixes, create_recipe and update_recipe correctly auto-generate slugs with previous_slug preservation on rename. 30 new tests + 113 existing tests pass. Pre-existing test failures (20) in unrelated modules are not WP02 regressions.
