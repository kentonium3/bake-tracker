"""
Tests for Recipe Slug Generation - Feature 080.

This module tests the slug generation functionality added in Feature 080:
- T010: Unit tests for slug generation from various names
- T011: Unit tests for collision handling (-2, -3 suffixes)
- T012: Unit tests for rename behavior (previous_slug preservation)
"""

import pytest

from src.models import Recipe
from src.services import recipe_service
from src.services.recipe_service import _generate_slug, _generate_unique_slug
from src.services.database import session_scope
from src.services.exceptions import RecipeNotFoundBySlug, ValidationError


# Note: Tests use `test_db` fixture from conftest.py which yields a Session


class TestGenerateSlug:
    """T010: Unit tests for _generate_slug() static method."""

    def test_basic_name_conversion(self):
        """Simple name converts to lowercase with hyphens."""
        assert _generate_slug("Chocolate Chip Cookies") == "chocolate-chip-cookies"

    def test_unicode_normalization(self):
        """Unicode accented characters are normalized to ASCII."""
        assert _generate_slug("Café au Lait") == "cafe-au-lait"
        assert _generate_slug("Crème Brûlée") == "creme-brulee"

    def test_special_characters_removed(self):
        """Special characters are stripped."""
        assert _generate_slug("Mom's Famous Pie!") == "moms-famous-pie"
        assert _generate_slug("100% Whole Wheat") == "100-whole-wheat"

    def test_underscores_converted(self):
        """Underscores are converted to hyphens."""
        assert _generate_slug("chocolate_chip_cookies") == "chocolate-chip-cookies"

    def test_multiple_spaces_collapsed(self):
        """Multiple spaces become single hyphen."""
        assert _generate_slug("Double   Space") == "double-space"

    def test_leading_trailing_hyphens_stripped(self):
        """Leading and trailing hyphens are removed."""
        assert _generate_slug("-Leading Hyphen") == "leading-hyphen"
        assert _generate_slug("Trailing Hyphen-") == "trailing-hyphen"

    def test_empty_name_returns_default(self):
        """Empty name returns 'unknown-recipe'."""
        assert _generate_slug("") == "unknown-recipe"
        assert _generate_slug(None) == "unknown-recipe"

    def test_all_special_chars_returns_default(self):
        """Name with only special chars returns 'unknown-recipe'."""
        assert _generate_slug("!!!") == "unknown-recipe"
        assert _generate_slug("@#$%") == "unknown-recipe"

    def test_max_length_truncation(self):
        """Long names are truncated to 200 chars."""
        long_name = "A" * 250
        slug = _generate_slug(long_name)
        assert len(slug) <= 200
        assert slug == "a" * 200

    def test_truncation_removes_trailing_hyphen(self):
        """Truncation doesn't leave trailing hyphen."""
        # Create a name that when slugified and truncated would end with hyphen
        # 199 chars + space + "x" = name that truncates mid-word
        name = "a" * 199 + " x"
        slug = _generate_slug(name)
        assert not slug.endswith("-")

    def test_numbers_preserved(self):
        """Numbers are kept in slug."""
        assert _generate_slug("Recipe 123") == "recipe-123"
        assert _generate_slug("24 Hour Bread") == "24-hour-bread"

    def test_mixed_case_lowered(self):
        """Mixed case is converted to lowercase."""
        assert _generate_slug("SHOUTING Recipe") == "shouting-recipe"
        assert _generate_slug("CamelCase") == "camelcase"


class TestGenerateUniqueSlug:
    """T011: Unit tests for _generate_unique_slug() collision handling."""

    def test_unique_slug_first_attempt(self, test_db):
        """When no collision, base slug is returned."""
        slug = _generate_unique_slug("Test Recipe", test_db)
        assert slug == "test-recipe"

    def test_collision_adds_suffix_2(self, test_db):
        """First collision adds -2 suffix."""
        # Create recipe with base slug
        recipe = Recipe(
            name="Test Recipe",
            slug="test-recipe",
            category="Test",
        )
        test_db.add(recipe)
        test_db.flush()

        # Generate slug for same name
        slug = _generate_unique_slug("Test Recipe", test_db)
        assert slug == "test-recipe-2"

    def test_collision_increments_suffix(self, test_db):
        """Multiple collisions increment suffix (-2, -3, etc.)."""
        # Create recipes with existing slugs
        for i, suffix in enumerate(["", "-2", "-3"]):
            recipe = Recipe(
                name=f"Test Recipe {i}",
                slug=f"test-recipe{suffix}",
                category="Test",
            )
            test_db.add(recipe)
        test_db.flush()

        # Next slug should be -4
        slug = _generate_unique_slug("Test Recipe", test_db)
        assert slug == "test-recipe-4"

    def test_exclude_id_allows_self_match(self, test_db):
        """When exclude_id matches, slug can be reused."""
        # Create a recipe
        recipe = Recipe(
            name="Test Recipe",
            slug="test-recipe",
            category="Test",
        )
        test_db.add(recipe)
        test_db.flush()

        # Generate with exclude_id = recipe.id should return base slug
        slug = _generate_unique_slug("Test Recipe", test_db, exclude_id=recipe.id)
        assert slug == "test-recipe"

    def test_exclude_id_still_avoids_other_collisions(self, test_db):
        """exclude_id only excludes that specific record."""
        # Create two recipes
        recipe1 = Recipe(name="Test Recipe", slug="test-recipe", category="Test")
        recipe2 = Recipe(name="Test Recipe 2", slug="test-recipe-2", category="Test")
        test_db.add_all([recipe1, recipe2])
        test_db.flush()

        # Generate with exclude_id=recipe1.id - should still avoid recipe2's slug
        slug = _generate_unique_slug("Test Recipe", test_db, exclude_id=recipe1.id)
        # Can use base slug since recipe1 is excluded
        assert slug == "test-recipe"

    def test_many_collisions_handled(self, test_db):
        """Can handle many collisions (up to limit)."""
        # Create 10 recipes with sequential slugs
        for i in range(10):
            suffix = "" if i == 0 else f"-{i + 1}"
            recipe = Recipe(
                name=f"Test Recipe {i}",
                slug=f"test-recipe{suffix}",
                category="Test",
            )
            test_db.add(recipe)
        test_db.flush()

        # Should get -11
        slug = _generate_unique_slug("Test Recipe", test_db)
        assert slug == "test-recipe-11"


class TestCreateRecipeSlug:
    """T010/T011: Integration tests for create_recipe slug generation."""

    def test_create_recipe_generates_slug(self, test_db):
        """Creating a recipe auto-generates a slug."""
        recipe_data = {
            "name": "My New Recipe",
            "category": "Dessert",
        }
        recipe = recipe_service.create_recipe(recipe_data)

        assert recipe.slug == "my-new-recipe"

    def test_create_recipe_handles_collision(self, test_db):
        """Creating recipes with same name generates unique slugs."""
        recipe_data = {
            "name": "Duplicate Name",
            "category": "Dessert",
        }

        recipe1 = recipe_service.create_recipe(recipe_data)
        recipe2 = recipe_service.create_recipe(recipe_data.copy())

        assert recipe1.slug == "duplicate-name"
        assert recipe2.slug == "duplicate-name-2"

    def test_create_recipe_accepts_explicit_slug(self, test_db):
        """Can provide explicit slug in recipe_data."""
        recipe_data = {
            "name": "Recipe With Custom Slug",
            "slug": "custom-slug-value",
            "category": "Dessert",
        }
        recipe = recipe_service.create_recipe(recipe_data)

        assert recipe.slug == "custom-slug-value"


class TestUpdateRecipeSlugOnRename:
    """T012: Unit tests for rename behavior with previous_slug preservation."""

    def test_rename_regenerates_slug(self, test_db):
        """Renaming recipe regenerates slug from new name."""
        # Create recipe
        recipe = recipe_service.create_recipe({
            "name": "Original Name",
            "category": "Test",
        })
        original_id = recipe.id
        assert recipe.slug == "original-name"

        # Rename it
        updated = recipe_service.update_recipe(
            original_id,
            {"name": "New Name", "category": "Test"}
        )

        assert updated.slug == "new-name"

    def test_rename_preserves_previous_slug(self, test_db):
        """Renaming preserves old slug in previous_slug field."""
        # Create recipe
        recipe = recipe_service.create_recipe({
            "name": "Original Name",
            "category": "Test",
        })
        original_id = recipe.id
        old_slug = recipe.slug

        # Rename it
        updated = recipe_service.update_recipe(
            original_id,
            {"name": "New Name", "category": "Test"}
        )

        assert updated.previous_slug == old_slug
        assert updated.previous_slug == "original-name"

    def test_second_rename_overwrites_previous_slug(self, test_db):
        """Second rename only keeps one previous_slug (grace period)."""
        # Create and rename once
        recipe = recipe_service.create_recipe({
            "name": "Name One",
            "category": "Test",
        })
        original_id = recipe.id

        recipe_service.update_recipe(
            original_id,
            {"name": "Name Two", "category": "Test"}
        )

        # Rename again
        updated = recipe_service.update_recipe(
            original_id,
            {"name": "Name Three", "category": "Test"}
        )

        # previous_slug should be from the second name, not the first
        assert updated.slug == "name-three"
        assert updated.previous_slug == "name-two"

    def test_non_name_update_preserves_slug(self, test_db):
        """Updating non-name fields doesn't change slug."""
        # Create recipe
        recipe = recipe_service.create_recipe({
            "name": "Stable Name",
            "category": "Test",
        })
        original_id = recipe.id
        original_slug = recipe.slug

        # Update only category
        updated = recipe_service.update_recipe(
            original_id,
            {"name": "Stable Name", "category": "New Category"}
        )

        assert updated.slug == original_slug
        assert updated.previous_slug is None  # Not changed

    def test_same_name_update_preserves_slug(self, test_db):
        """Updating with same name doesn't regenerate slug."""
        # Create recipe
        recipe = recipe_service.create_recipe({
            "name": "Same Name",
            "category": "Test",
        })
        original_id = recipe.id
        original_slug = recipe.slug

        # Update with identical name
        updated = recipe_service.update_recipe(
            original_id,
            {"name": "Same Name", "category": "Test", "notes": "Added notes"}
        )

        assert updated.slug == original_slug
        assert updated.previous_slug is None


class TestGetRecipeBySlug:
    """Tests for get_recipe_by_slug lookup."""

    def test_get_by_current_slug(self, test_db):
        """Can retrieve recipe by current slug."""
        recipe = recipe_service.create_recipe({
            "name": "Find Me",
            "category": "Test",
        })

        found = recipe_service.get_recipe_by_slug("find-me")
        assert found is not None
        assert found.id == recipe.id

    def test_get_by_previous_slug(self, test_db):
        """Can retrieve recipe by previous_slug after rename."""
        recipe = recipe_service.create_recipe({
            "name": "Old Name",
            "category": "Test",
        })
        original_id = recipe.id

        # Rename
        recipe_service.update_recipe(
            original_id,
            {"name": "New Name", "category": "Test"}
        )

        # Find by old slug
        found = recipe_service.get_recipe_by_slug("old-name")
        assert found is not None
        assert found.id == original_id
        assert found.name == "New Name"

    def test_get_by_nonexistent_slug(self, test_db):
        """Raises RecipeNotFoundBySlug for non-existent slug."""
        with pytest.raises(RecipeNotFoundBySlug) as exc:
            recipe_service.get_recipe_by_slug("nonexistent-slug")
        assert exc.value.slug == "nonexistent-slug"

    def test_current_slug_takes_priority(self, test_db):
        """If a current slug matches, returns that recipe (not previous_slug match)."""
        # Create recipe A with slug "target"
        recipe_a = recipe_service.create_recipe({
            "name": "Target",
            "category": "Test",
        })

        # Create recipe B, rename it so previous_slug = "something"
        recipe_b = recipe_service.create_recipe({
            "name": "Something",
            "category": "Test",
        })
        recipe_service.update_recipe(
            recipe_b.id,
            {"name": "Changed", "category": "Test"}
        )
        # Now recipe_b.previous_slug = "something"

        # Search for "target" should find recipe_a (current slug), not recipe_b
        found = recipe_service.get_recipe_by_slug("target")
        assert found.id == recipe_a.id
