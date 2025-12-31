"""
Tests for ingredient hierarchy service (Feature 031).

Tests cover:
- get_root_ingredients()
- get_children()
- get_ancestors()
- get_all_descendants()
- get_leaf_ingredients()
- is_leaf()
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from src.models.base import Base
from src.models.ingredient import Ingredient
from src.services.exceptions import IngredientNotFound
from src.services import ingredient_hierarchy_service


@pytest.fixture
def test_db():
    """Create a test database with sample hierarchy data."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    Session = scoped_session(session_factory)
    session = Session()

    # Create sample hierarchy:
    # Chocolate (level 0)
    #   └─ Dark Chocolate (level 1)
    #       └─ Semi-Sweet Chips (level 2)
    #       └─ Bittersweet Chips (level 2)
    #   └─ Milk Chocolate (level 1)
    #       └─ Milk Chocolate Chips (level 2)
    # Flour (level 0)
    #   └─ All-Purpose Flour (level 2) - direct child of root

    chocolate = Ingredient(
        display_name="Chocolate",
        slug="chocolate",
        category="Chocolate",
        hierarchy_level=0,
        parent_ingredient_id=None,
    )
    session.add(chocolate)
    session.flush()

    dark_chocolate = Ingredient(
        display_name="Dark Chocolate",
        slug="dark-chocolate",
        category="Chocolate",
        hierarchy_level=1,
        parent_ingredient_id=chocolate.id,
    )
    session.add(dark_chocolate)
    session.flush()

    semi_sweet = Ingredient(
        display_name="Semi-Sweet Chips",
        slug="semi-sweet-chips",
        category="Chocolate",
        hierarchy_level=2,
        parent_ingredient_id=dark_chocolate.id,
    )
    session.add(semi_sweet)

    bittersweet = Ingredient(
        display_name="Bittersweet Chips",
        slug="bittersweet-chips",
        category="Chocolate",
        hierarchy_level=2,
        parent_ingredient_id=dark_chocolate.id,
    )
    session.add(bittersweet)

    milk_chocolate = Ingredient(
        display_name="Milk Chocolate",
        slug="milk-chocolate",
        category="Chocolate",
        hierarchy_level=1,
        parent_ingredient_id=chocolate.id,
    )
    session.add(milk_chocolate)
    session.flush()

    milk_chips = Ingredient(
        display_name="Milk Chocolate Chips",
        slug="milk-chocolate-chips",
        category="Chocolate",
        hierarchy_level=2,
        parent_ingredient_id=milk_chocolate.id,
    )
    session.add(milk_chips)

    flour = Ingredient(
        display_name="Flour",
        slug="flour",
        category="Flour",
        hierarchy_level=0,
        parent_ingredient_id=None,
    )
    session.add(flour)
    session.flush()

    # Direct leaf under root (skipping mid-tier)
    ap_flour = Ingredient(
        display_name="All-Purpose Flour",
        slug="all-purpose-flour",
        category="Flour",
        hierarchy_level=2,
        parent_ingredient_id=flour.id,
    )
    session.add(ap_flour)

    session.commit()

    yield session

    session.close()
    Session.remove()


class TestGetRootIngredients:
    """Tests for get_root_ingredients()."""

    def test_returns_root_level_ingredients(self, test_db):
        """Test that only level 0 ingredients are returned."""
        roots = ingredient_hierarchy_service.get_root_ingredients(session=test_db)
        assert len(roots) == 2
        names = [r["display_name"] for r in roots]
        assert "Chocolate" in names
        assert "Flour" in names

    def test_sorted_by_display_name(self, test_db):
        """Test that results are sorted alphabetically."""
        roots = ingredient_hierarchy_service.get_root_ingredients(session=test_db)
        names = [r["display_name"] for r in roots]
        assert names == sorted(names)

    def test_empty_database(self):
        """Test with empty database."""
        engine = create_engine("sqlite:///:memory:", echo=False)
        Base.metadata.create_all(engine)
        session_factory = sessionmaker(bind=engine)
        session = session_factory()

        roots = ingredient_hierarchy_service.get_root_ingredients(session=session)
        assert roots == []

        session.close()


class TestGetChildren:
    """Tests for get_children()."""

    def test_returns_direct_children(self, test_db):
        """Test that direct children are returned."""
        # Get chocolate's ID
        chocolate = test_db.query(Ingredient).filter(Ingredient.slug == "chocolate").first()
        children = ingredient_hierarchy_service.get_children(chocolate.id, session=test_db)

        assert len(children) == 2
        names = [c["display_name"] for c in children]
        assert "Dark Chocolate" in names
        assert "Milk Chocolate" in names

    def test_returns_leaf_children(self, test_db):
        """Test getting children of a mid-tier ingredient."""
        dark = test_db.query(Ingredient).filter(Ingredient.slug == "dark-chocolate").first()
        children = ingredient_hierarchy_service.get_children(dark.id, session=test_db)

        assert len(children) == 2
        names = [c["display_name"] for c in children]
        assert "Semi-Sweet Chips" in names
        assert "Bittersweet Chips" in names

    def test_parent_not_found(self, test_db):
        """Test that IngredientNotFound is raised for invalid parent_id."""
        with pytest.raises(IngredientNotFound):
            ingredient_hierarchy_service.get_children(99999, session=test_db)

    def test_no_children(self, test_db):
        """Test ingredient with no children returns empty list."""
        semi_sweet = test_db.query(Ingredient).filter(Ingredient.slug == "semi-sweet-chips").first()
        children = ingredient_hierarchy_service.get_children(semi_sweet.id, session=test_db)
        assert children == []


class TestGetAncestors:
    """Tests for get_ancestors()."""

    def test_leaf_has_ancestors(self, test_db):
        """Test getting ancestors of a leaf ingredient."""
        semi_sweet = test_db.query(Ingredient).filter(Ingredient.slug == "semi-sweet-chips").first()
        ancestors = ingredient_hierarchy_service.get_ancestors(semi_sweet.id, session=test_db)

        # Should have Dark Chocolate (immediate parent) and Chocolate (root)
        assert len(ancestors) == 2
        assert ancestors[0]["display_name"] == "Dark Chocolate"  # Immediate parent first
        assert ancestors[1]["display_name"] == "Chocolate"  # Root last

    def test_mid_tier_has_one_ancestor(self, test_db):
        """Test getting ancestors of a mid-tier ingredient."""
        dark = test_db.query(Ingredient).filter(Ingredient.slug == "dark-chocolate").first()
        ancestors = ingredient_hierarchy_service.get_ancestors(dark.id, session=test_db)

        assert len(ancestors) == 1
        assert ancestors[0]["display_name"] == "Chocolate"

    def test_root_has_no_ancestors(self, test_db):
        """Test that root ingredients have no ancestors."""
        chocolate = test_db.query(Ingredient).filter(Ingredient.slug == "chocolate").first()
        ancestors = ingredient_hierarchy_service.get_ancestors(chocolate.id, session=test_db)
        assert ancestors == []

    def test_ingredient_not_found(self, test_db):
        """Test that IngredientNotFound is raised for invalid id."""
        with pytest.raises(IngredientNotFound):
            ingredient_hierarchy_service.get_ancestors(99999, session=test_db)


class TestGetAllDescendants:
    """Tests for get_all_descendants()."""

    def test_root_has_all_descendants(self, test_db):
        """Test getting all descendants of a root ingredient."""
        chocolate = test_db.query(Ingredient).filter(Ingredient.slug == "chocolate").first()
        descendants = ingredient_hierarchy_service.get_all_descendants(chocolate.id, session=test_db)

        # Chocolate has: Dark Chocolate, Milk Chocolate (level 1)
        #                Semi-Sweet, Bittersweet, Milk Chips (level 2)
        assert len(descendants) == 5
        names = [d["display_name"] for d in descendants]
        assert "Dark Chocolate" in names
        assert "Milk Chocolate" in names
        assert "Semi-Sweet Chips" in names
        assert "Bittersweet Chips" in names
        assert "Milk Chocolate Chips" in names

    def test_mid_tier_has_descendants(self, test_db):
        """Test getting descendants of a mid-tier ingredient."""
        dark = test_db.query(Ingredient).filter(Ingredient.slug == "dark-chocolate").first()
        descendants = ingredient_hierarchy_service.get_all_descendants(dark.id, session=test_db)

        assert len(descendants) == 2
        names = [d["display_name"] for d in descendants]
        assert "Semi-Sweet Chips" in names
        assert "Bittersweet Chips" in names

    def test_leaf_has_no_descendants(self, test_db):
        """Test that leaf ingredients have no descendants."""
        semi_sweet = test_db.query(Ingredient).filter(Ingredient.slug == "semi-sweet-chips").first()
        descendants = ingredient_hierarchy_service.get_all_descendants(semi_sweet.id, session=test_db)
        assert descendants == []

    def test_ingredient_not_found(self, test_db):
        """Test that IngredientNotFound is raised for invalid id."""
        with pytest.raises(IngredientNotFound):
            ingredient_hierarchy_service.get_all_descendants(99999, session=test_db)


class TestGetLeafIngredients:
    """Tests for get_leaf_ingredients()."""

    def test_returns_all_leaves(self, test_db):
        """Test getting all leaf ingredients without filter."""
        leaves = ingredient_hierarchy_service.get_leaf_ingredients(session=test_db)

        # Should have: Semi-Sweet, Bittersweet, Milk Chips, All-Purpose Flour
        assert len(leaves) == 4
        names = [l["display_name"] for l in leaves]
        assert "Semi-Sweet Chips" in names
        assert "Bittersweet Chips" in names
        assert "Milk Chocolate Chips" in names
        assert "All-Purpose Flour" in names

    def test_filter_by_parent(self, test_db):
        """Test filtering leaves by parent."""
        dark = test_db.query(Ingredient).filter(Ingredient.slug == "dark-chocolate").first()
        leaves = ingredient_hierarchy_service.get_leaf_ingredients(parent_id=dark.id, session=test_db)

        assert len(leaves) == 2
        names = [l["display_name"] for l in leaves]
        assert "Semi-Sweet Chips" in names
        assert "Bittersweet Chips" in names

    def test_filter_by_root_parent(self, test_db):
        """Test filtering leaves by root parent."""
        chocolate = test_db.query(Ingredient).filter(Ingredient.slug == "chocolate").first()
        leaves = ingredient_hierarchy_service.get_leaf_ingredients(parent_id=chocolate.id, session=test_db)

        # Should have all chocolate leaves (3)
        assert len(leaves) == 3
        names = [l["display_name"] for l in leaves]
        assert "Semi-Sweet Chips" in names
        assert "Bittersweet Chips" in names
        assert "Milk Chocolate Chips" in names

    def test_sorted_by_display_name(self, test_db):
        """Test that results are sorted alphabetically."""
        leaves = ingredient_hierarchy_service.get_leaf_ingredients(session=test_db)
        names = [l["display_name"] for l in leaves]
        assert names == sorted(names)


class TestIsLeaf:
    """Tests for is_leaf()."""

    def test_leaf_returns_true(self, test_db):
        """Test that leaf ingredients return True."""
        semi_sweet = test_db.query(Ingredient).filter(Ingredient.slug == "semi-sweet-chips").first()
        assert ingredient_hierarchy_service.is_leaf(semi_sweet.id, session=test_db) is True

    def test_mid_tier_returns_false(self, test_db):
        """Test that mid-tier ingredients return False."""
        dark = test_db.query(Ingredient).filter(Ingredient.slug == "dark-chocolate").first()
        assert ingredient_hierarchy_service.is_leaf(dark.id, session=test_db) is False

    def test_root_returns_false(self, test_db):
        """Test that root ingredients return False."""
        chocolate = test_db.query(Ingredient).filter(Ingredient.slug == "chocolate").first()
        assert ingredient_hierarchy_service.is_leaf(chocolate.id, session=test_db) is False

    def test_ingredient_not_found(self, test_db):
        """Test that IngredientNotFound is raised for invalid id."""
        with pytest.raises(IngredientNotFound):
            ingredient_hierarchy_service.is_leaf(99999, session=test_db)
