"""
Tests for recipe category seeding functionality.

Feature 096: Recipe Category Management (WP03).

Tests cover:
- Fresh database has 7 default categories after seeding
- Categories have correct sort_order values (gaps of 10)
- Seeding is idempotent (no duplicates on second run)
- Existing Recipe.category values are discovered and added
- seed_recipe_categories() is called from init_database() indirectly
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from src.models.base import Base
from src.models.recipe_category import RecipeCategory
from src.services.database import seed_recipe_categories


@pytest.fixture(scope="function")
def test_db():
    """Provide a clean test database for seeding tests.

    This fixture creates an in-memory SQLite database,
    patches the session factory, and cleans up afterward.
    """
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)

    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    Session = scoped_session(session_factory)

    # Monkey-patch the global session factory for tests
    import src.services.database as db_module

    original_get_session_factory = db_module.get_session_factory
    db_module.get_session_factory = lambda: Session

    yield Session

    # Cleanup
    Session.remove()
    with engine.connect() as conn:
        conn.exec_driver_sql("PRAGMA foreign_keys=OFF")
        Base.metadata.drop_all(conn)
        conn.exec_driver_sql("PRAGMA foreign_keys=ON")
    db_module.get_session_factory = original_get_session_factory


class TestSeedRecipeCategories:
    """Tests for seed_recipe_categories() functionality."""

    def test_seeds_7_default_categories(self, test_db):
        """Fresh database gets exactly 7 default recipe categories."""
        session = test_db()
        assert session.query(RecipeCategory).count() == 0
        session.close()

        seed_recipe_categories()

        session = test_db()
        count = session.query(RecipeCategory).count()
        session.close()

        assert count == 7

    def test_default_category_names(self, test_db):
        """Default categories have the expected names."""
        seed_recipe_categories()

        session = test_db()
        categories = (
            session.query(RecipeCategory)
            .order_by(RecipeCategory.sort_order)
            .all()
        )
        names = [c.name for c in categories]
        session.close()

        assert names == [
            "Cakes", "Cookies", "Candies", "Brownies",
            "Bars", "Breads", "Other",
        ]

    def test_default_category_slugs(self, test_db):
        """Default categories have correct slugs."""
        seed_recipe_categories()

        session = test_db()
        categories = (
            session.query(RecipeCategory)
            .order_by(RecipeCategory.sort_order)
            .all()
        )
        slugs = [c.slug for c in categories]
        session.close()

        assert slugs == [
            "cakes", "cookies", "candies", "brownies",
            "bars", "breads", "other",
        ]

    def test_sort_order_gaps_of_10(self, test_db):
        """Default categories have sort_order in gaps of 10."""
        seed_recipe_categories()

        session = test_db()
        categories = (
            session.query(RecipeCategory)
            .order_by(RecipeCategory.sort_order)
            .all()
        )
        orders = [c.sort_order for c in categories]
        session.close()

        assert orders == [10, 20, 30, 40, 50, 60, 70]

    def test_seeding_is_idempotent(self, test_db):
        """Running seed_recipe_categories() twice does not create duplicates."""
        seed_recipe_categories()

        session = test_db()
        first_count = session.query(RecipeCategory).count()
        session.close()

        seed_recipe_categories()

        session = test_db()
        second_count = session.query(RecipeCategory).count()
        session.close()

        assert first_count == 7
        assert second_count == 7, "Duplicate seeding created extra categories"

    def test_discovers_existing_recipe_categories(self, test_db):
        """Existing Recipe.category values are added during seeding."""
        from src.models.recipe import Recipe

        # Add a recipe with a category not in defaults
        session = test_db()
        recipe = Recipe(
            name="Fruit Tart",
            slug="fruit-tart",
            category="Pastries",
        )
        session.add(recipe)
        session.commit()
        session.close()

        seed_recipe_categories()

        session = test_db()
        count = session.query(RecipeCategory).count()
        pastry_cat = (
            session.query(RecipeCategory)
            .filter(RecipeCategory.name == "Pastries")
            .first()
        )
        session.close()

        assert count == 8  # 7 defaults + 1 discovered
        assert pastry_cat is not None
        assert pastry_cat.slug == "pastries"
        assert pastry_cat.sort_order == 80

    def test_does_not_duplicate_default_categories_from_recipes(self, test_db):
        """Recipes with category matching a default do not create duplicates."""
        from src.models.recipe import Recipe

        # Add a recipe with a category that matches a default
        session = test_db()
        recipe = Recipe(
            name="Chocolate Cake",
            slug="chocolate-cake",
            category="Cakes",
        )
        session.add(recipe)
        session.commit()
        session.close()

        seed_recipe_categories()

        session = test_db()
        count = session.query(RecipeCategory).count()
        session.close()

        assert count == 7  # No extra category for "Cakes"

    def test_discovers_multiple_recipe_categories(self, test_db):
        """Multiple distinct Recipe.category values are all discovered."""
        from src.models.recipe import Recipe

        session = test_db()
        session.add(Recipe(
            name="Fruit Tart", slug="fruit-tart", category="Pastries"
        ))
        session.add(Recipe(
            name="Scone", slug="scone", category="Scones"
        ))
        session.add(Recipe(
            name="Muffin", slug="muffin", category="Muffins"
        ))
        session.commit()
        session.close()

        seed_recipe_categories()

        session = test_db()
        count = session.query(RecipeCategory).count()
        session.close()

        assert count == 10  # 7 defaults + 3 discovered

    def test_ignores_empty_string_recipe_categories(self, test_db):
        """Recipes with empty string category are not seeded as new categories."""
        from src.models.recipe import Recipe

        session = test_db()
        recipe = Recipe(
            name="No Category Recipe",
            slug="no-category-recipe",
            category="",
        )
        session.add(recipe)
        session.commit()
        session.close()

        seed_recipe_categories()

        session = test_db()
        count = session.query(RecipeCategory).count()
        session.close()

        assert count == 7  # Only defaults, no empty-string category
