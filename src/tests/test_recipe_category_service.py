"""Tests for recipe_category_service CRUD operations.

Feature 096: Recipe Category Management.
"""

import pytest

from src.models.recipe_category import RecipeCategory
from src.services import recipe_category_service
from src.services.exceptions import (
    RecipeCategoryNotFoundById,
    RecipeCategoryNotFoundByName,
    ValidationError,
)


# ============================================================================
# create_category tests
# ============================================================================


class TestCreateCategory:
    """Tests for recipe_category_service.create_category()."""

    def test_create_with_name_generates_slug(self, test_db):
        """Happy path: name provided, slug auto-generated."""
        cat = recipe_category_service.create_category(name="Layer Cakes")
        assert cat.name == "Layer Cakes"
        assert cat.slug == "layer-cakes"
        assert cat.sort_order == 0
        assert cat.description is None
        assert cat.id is not None
        assert cat.uuid is not None

    def test_create_with_explicit_slug(self, test_db):
        """Explicit slug provided is used as-is."""
        cat = recipe_category_service.create_category(
            name="Cookies", slug="cookie-jar"
        )
        assert cat.slug == "cookie-jar"

    def test_create_with_sort_order(self, test_db):
        """Sort order is stored correctly."""
        cat = recipe_category_service.create_category(
            name="Cakes", sort_order=10
        )
        assert cat.sort_order == 10

    def test_create_with_description(self, test_db):
        """Description is stored correctly."""
        cat = recipe_category_service.create_category(
            name="Cakes", description="Layer cakes, sheet cakes, bundt cakes"
        )
        assert cat.description == "Layer cakes, sheet cakes, bundt cakes"

    def test_create_duplicate_name_raises(self, test_db):
        """Duplicate name raises ValidationError."""
        recipe_category_service.create_category(name="Cakes")
        with pytest.raises(ValidationError, match="already exists"):
            recipe_category_service.create_category(name="Cakes")

    def test_create_empty_name_raises(self, test_db):
        """Empty name raises ValidationError."""
        with pytest.raises(ValidationError, match="cannot be empty"):
            recipe_category_service.create_category(name="")

    def test_create_whitespace_name_raises(self, test_db):
        """Whitespace-only name raises ValidationError."""
        with pytest.raises(ValidationError, match="cannot be empty"):
            recipe_category_service.create_category(name="   ")

    def test_create_strips_name(self, test_db):
        """Leading/trailing whitespace is stripped from name."""
        cat = recipe_category_service.create_category(name="  Cakes  ")
        assert cat.name == "Cakes"

    def test_create_slug_collision_appends_suffix(self, test_db):
        """Slug collision resolved by appending numeric suffix."""
        cat1 = recipe_category_service.create_category(
            name="Cakes", slug="cakes"
        )
        cat2 = recipe_category_service.create_category(
            name="Cakes Redux", slug="cakes"
        )
        assert cat1.slug == "cakes"
        assert cat2.slug == "cakes-2"

    def test_create_with_session(self, test_db):
        """Creating with explicit session works."""
        session = test_db()
        cat = recipe_category_service.create_category(
            name="Cakes", session=session
        )
        assert cat.id is not None
        session.commit()


# ============================================================================
# list_categories tests
# ============================================================================


class TestListCategories:
    """Tests for recipe_category_service.list_categories()."""

    def test_list_empty(self, test_db):
        """Returns empty list when no categories exist."""
        result = recipe_category_service.list_categories()
        assert result == []

    def test_list_ordered_by_sort_order(self, test_db):
        """Returns categories ordered by sort_order, then name."""
        recipe_category_service.create_category(name="Cookies", sort_order=20)
        recipe_category_service.create_category(name="Cakes", sort_order=10)
        recipe_category_service.create_category(name="Bars", sort_order=30)

        result = recipe_category_service.list_categories()
        names = [c.name for c in result]
        assert names == ["Cakes", "Cookies", "Bars"]

    def test_list_tiebreak_by_name(self, test_db):
        """Same sort_order falls back to name ordering."""
        recipe_category_service.create_category(name="Cookies", sort_order=10)
        recipe_category_service.create_category(name="Cakes", sort_order=10)
        recipe_category_service.create_category(name="Bars", sort_order=10)

        result = recipe_category_service.list_categories()
        names = [c.name for c in result]
        assert names == ["Bars", "Cakes", "Cookies"]


# ============================================================================
# get_category_by_id tests
# ============================================================================


class TestGetCategoryById:
    """Tests for recipe_category_service.get_category_by_id()."""

    def test_get_existing(self, test_db):
        """Happy path returns category."""
        created = recipe_category_service.create_category(name="Cakes")
        found = recipe_category_service.get_category_by_id(created.id)
        assert found.name == "Cakes"
        assert found.id == created.id

    def test_get_nonexistent_raises(self, test_db):
        """Non-existent ID raises RecipeCategoryNotFoundById."""
        with pytest.raises(RecipeCategoryNotFoundById):
            recipe_category_service.get_category_by_id(99999)


# ============================================================================
# get_category_by_name tests
# ============================================================================


class TestGetCategoryByName:
    """Tests for recipe_category_service.get_category_by_name()."""

    def test_get_existing(self, test_db):
        """Happy path returns category."""
        recipe_category_service.create_category(name="Cakes")
        found = recipe_category_service.get_category_by_name("Cakes")
        assert found.name == "Cakes"

    def test_get_nonexistent_raises(self, test_db):
        """Non-existent name raises RecipeCategoryNotFoundByName."""
        with pytest.raises(RecipeCategoryNotFoundByName):
            recipe_category_service.get_category_by_name("Nonexistent")


# ============================================================================
# update_category tests
# ============================================================================


class TestUpdateCategory:
    """Tests for recipe_category_service.update_category()."""

    def test_update_name(self, test_db):
        """Update name only."""
        cat = recipe_category_service.create_category(name="Cakes")
        updated = recipe_category_service.update_category(
            cat.id, name="Layer Cakes"
        )
        assert updated.name == "Layer Cakes"
        # Slug should NOT change on name update
        assert updated.slug == "cakes"

    def test_update_sort_order(self, test_db):
        """Update sort_order only."""
        cat = recipe_category_service.create_category(
            name="Cakes", sort_order=10
        )
        updated = recipe_category_service.update_category(
            cat.id, sort_order=50
        )
        assert updated.sort_order == 50
        assert updated.name == "Cakes"

    def test_update_description(self, test_db):
        """Update description only."""
        cat = recipe_category_service.create_category(name="Cakes")
        updated = recipe_category_service.update_category(
            cat.id, description="All kinds of cakes"
        )
        assert updated.description == "All kinds of cakes"

    def test_update_nonexistent_raises(self, test_db):
        """Non-existent ID raises RecipeCategoryNotFoundById."""
        with pytest.raises(RecipeCategoryNotFoundById):
            recipe_category_service.update_category(99999, name="Foo")

    def test_update_empty_name_raises(self, test_db):
        """Empty name raises ValidationError."""
        cat = recipe_category_service.create_category(name="Cakes")
        with pytest.raises(ValidationError, match="cannot be empty"):
            recipe_category_service.update_category(cat.id, name="")

    def test_update_duplicate_name_raises(self, test_db):
        """Duplicate name raises ValidationError."""
        recipe_category_service.create_category(name="Cakes")
        cat2 = recipe_category_service.create_category(name="Cookies")
        with pytest.raises(ValidationError, match="already exists"):
            recipe_category_service.update_category(cat2.id, name="Cakes")

    def test_update_same_name_no_error(self, test_db):
        """Updating to the same name doesn't raise duplicate error."""
        cat = recipe_category_service.create_category(name="Cakes")
        updated = recipe_category_service.update_category(
            cat.id, name="Cakes"
        )
        assert updated.name == "Cakes"


# ============================================================================
# is_category_in_use tests
# ============================================================================


class TestIsCategoryInUse:
    """Tests for recipe_category_service.is_category_in_use()."""

    def test_not_in_use(self, test_db):
        """Returns False when no recipes use the category."""
        cat = recipe_category_service.create_category(name="Cakes")
        assert recipe_category_service.is_category_in_use(cat.id) is False

    def test_in_use(self, test_db):
        """Returns True when recipes use the category."""
        from src.models.recipe import Recipe

        cat = recipe_category_service.create_category(name="Cakes")

        session = test_db()
        recipe = Recipe(
            name="Chocolate Cake",
            slug="chocolate-cake",
            category="Cakes",
        )
        session.add(recipe)
        session.commit()

        assert recipe_category_service.is_category_in_use(cat.id) is True

    def test_nonexistent_category_raises(self, test_db):
        """Non-existent ID raises RecipeCategoryNotFoundById."""
        with pytest.raises(RecipeCategoryNotFoundById):
            recipe_category_service.is_category_in_use(99999)


# ============================================================================
# delete_category tests
# ============================================================================


class TestDeleteCategory:
    """Tests for recipe_category_service.delete_category()."""

    def test_delete_unused(self, test_db):
        """Happy path: unused category is deleted."""
        cat = recipe_category_service.create_category(name="Cakes")
        recipe_category_service.delete_category(cat.id)

        with pytest.raises(RecipeCategoryNotFoundById):
            recipe_category_service.get_category_by_id(cat.id)

    def test_delete_in_use_raises(self, test_db):
        """Category in use raises ValidationError with recipe count."""
        from src.models.recipe import Recipe

        cat = recipe_category_service.create_category(name="Cakes")

        session = test_db()
        recipe = Recipe(
            name="Chocolate Cake",
            slug="chocolate-cake",
            category="Cakes",
        )
        session.add(recipe)
        session.commit()

        with pytest.raises(ValidationError, match="used by 1 recipe"):
            recipe_category_service.delete_category(cat.id)

    def test_delete_nonexistent_raises(self, test_db):
        """Non-existent ID raises RecipeCategoryNotFoundById."""
        with pytest.raises(RecipeCategoryNotFoundById):
            recipe_category_service.delete_category(99999)


# ============================================================================
# to_dict tests
# ============================================================================


class TestToDict:
    """Tests for RecipeCategory.to_dict()."""

    def test_to_dict_includes_all_fields(self, test_db):
        """to_dict includes name, slug, sort_order, description."""
        cat = recipe_category_service.create_category(
            name="Cakes",
            sort_order=10,
            description="All cakes",
        )
        d = cat.to_dict()
        assert d["name"] == "Cakes"
        assert d["slug"] == "cakes"
        assert d["sort_order"] == 10
        assert d["description"] == "All cakes"
        assert "id" in d
        assert "uuid" in d
        assert "created_at" in d
        assert "updated_at" in d
