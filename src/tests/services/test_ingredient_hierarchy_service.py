"""
Tests for ingredient hierarchy service (Feature 031 and Feature 033).

Tests cover:
- get_root_ingredients()
- get_children()
- get_ancestors()
- get_descendants()
- get_leaf_ingredients()
- get_ingredients_by_level()
- get_ingredient_by_id()
- get_ingredient_tree()
- is_leaf()
- validate_hierarchy_level()
- would_create_cycle()
- validate_hierarchy()
- move_ingredient()
- search_ingredients()
- get_child_count() (F033)
- get_product_count() (F033)
- can_change_parent() (F033)
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from src.models.base import Base
from src.models.ingredient import Ingredient
from src.models.product import Product
from src.services.exceptions import (
    IngredientNotFound,
    CircularReferenceError,
    MaxDepthExceededError,
    HierarchyValidationError,
)
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
    """Tests for get_descendants()."""

    def test_root_has_all_descendants(self, test_db):
        """Test getting all descendants of a root ingredient."""
        chocolate = test_db.query(Ingredient).filter(Ingredient.slug == "chocolate").first()
        descendants = ingredient_hierarchy_service.get_descendants(chocolate.id, session=test_db)

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
        descendants = ingredient_hierarchy_service.get_descendants(dark.id, session=test_db)

        assert len(descendants) == 2
        names = [d["display_name"] for d in descendants]
        assert "Semi-Sweet Chips" in names
        assert "Bittersweet Chips" in names

    def test_leaf_has_no_descendants(self, test_db):
        """Test that leaf ingredients have no descendants."""
        semi_sweet = test_db.query(Ingredient).filter(Ingredient.slug == "semi-sweet-chips").first()
        descendants = ingredient_hierarchy_service.get_descendants(semi_sweet.id, session=test_db)
        assert descendants == []

    def test_ingredient_not_found(self, test_db):
        """Test that IngredientNotFound is raised for invalid id."""
        with pytest.raises(IngredientNotFound):
            ingredient_hierarchy_service.get_descendants(99999, session=test_db)


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
        leaves = ingredient_hierarchy_service.get_leaf_ingredients(
            parent_id=dark.id, session=test_db
        )

        assert len(leaves) == 2
        names = [l["display_name"] for l in leaves]
        assert "Semi-Sweet Chips" in names
        assert "Bittersweet Chips" in names

    def test_filter_by_root_parent(self, test_db):
        """Test filtering leaves by root parent."""
        chocolate = test_db.query(Ingredient).filter(Ingredient.slug == "chocolate").first()
        leaves = ingredient_hierarchy_service.get_leaf_ingredients(
            parent_id=chocolate.id, session=test_db
        )

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


# =============================================================================
# Validation Function Tests (WP03)
# =============================================================================


class TestValidateHierarchyLevel:
    """Tests for validate_hierarchy_level()."""

    def test_valid_level_returns_true(self, test_db):
        """Test that valid level returns True."""
        semi_sweet = test_db.query(Ingredient).filter(Ingredient.slug == "semi-sweet-chips").first()
        result = ingredient_hierarchy_service.validate_hierarchy_level(
            semi_sweet.id, [2], session=test_db
        )
        assert result is True

    def test_invalid_level_raises_error(self, test_db):
        """Test that invalid level raises HierarchyValidationError."""
        chocolate = test_db.query(Ingredient).filter(Ingredient.slug == "chocolate").first()
        with pytest.raises(HierarchyValidationError) as exc_info:
            ingredient_hierarchy_service.validate_hierarchy_level(
                chocolate.id, [2], session=test_db
            )
        assert "level 0" in str(exc_info.value)
        assert "only levels [2]" in str(exc_info.value)

    def test_multiple_allowed_levels(self, test_db):
        """Test validation with multiple allowed levels."""
        dark = test_db.query(Ingredient).filter(Ingredient.slug == "dark-chocolate").first()
        result = ingredient_hierarchy_service.validate_hierarchy_level(
            dark.id, [0, 1], session=test_db
        )
        assert result is True

    def test_ingredient_not_found(self, test_db):
        """Test that IngredientNotFound is raised for invalid id."""
        with pytest.raises(IngredientNotFound):
            ingredient_hierarchy_service.validate_hierarchy_level(99999, [2], session=test_db)


class TestWouldCreateCycle:
    """Tests for would_create_cycle()."""

    def test_direct_self_reference_is_cycle(self, test_db):
        """Test that self-reference is detected as cycle."""
        chocolate = test_db.query(Ingredient).filter(Ingredient.slug == "chocolate").first()
        result = ingredient_hierarchy_service.would_create_cycle(
            chocolate.id, chocolate.id, session=test_db
        )
        assert result is True

    def test_indirect_cycle_detected(self, test_db):
        """Test that indirect cycle is detected (parent becomes child of descendant)."""
        chocolate = test_db.query(Ingredient).filter(Ingredient.slug == "chocolate").first()
        dark = test_db.query(Ingredient).filter(Ingredient.slug == "dark-chocolate").first()
        # Trying to make Chocolate a child of Dark Chocolate (its own child)
        result = ingredient_hierarchy_service.would_create_cycle(
            chocolate.id, dark.id, session=test_db
        )
        assert result is True

    def test_deep_cycle_detected(self, test_db):
        """Test cycle detection through grandchild."""
        chocolate = test_db.query(Ingredient).filter(Ingredient.slug == "chocolate").first()
        semi_sweet = test_db.query(Ingredient).filter(Ingredient.slug == "semi-sweet-chips").first()
        # Trying to make Chocolate a child of Semi-Sweet (its grandchild)
        result = ingredient_hierarchy_service.would_create_cycle(
            chocolate.id, semi_sweet.id, session=test_db
        )
        assert result is True

    def test_safe_move_returns_false(self, test_db):
        """Test that valid move returns False."""
        semi_sweet = test_db.query(Ingredient).filter(Ingredient.slug == "semi-sweet-chips").first()
        milk = test_db.query(Ingredient).filter(Ingredient.slug == "milk-chocolate").first()
        # Moving Semi-Sweet to Milk Chocolate is safe (both are siblings under Chocolate)
        result = ingredient_hierarchy_service.would_create_cycle(
            semi_sweet.id, milk.id, session=test_db
        )
        assert result is False


class TestMoveIngredient:
    """Tests for move_ingredient()."""

    def test_valid_move_updates_parent(self, test_db):
        """Test that valid move updates parent and level."""
        semi_sweet = test_db.query(Ingredient).filter(Ingredient.slug == "semi-sweet-chips").first()
        milk = test_db.query(Ingredient).filter(Ingredient.slug == "milk-chocolate").first()

        result = ingredient_hierarchy_service.move_ingredient(
            semi_sweet.id, milk.id, session=test_db
        )

        assert result["parent_ingredient_id"] == milk.id
        assert result["hierarchy_level"] == 2  # Level stays same (milk is level 1)

    def test_move_to_root(self, test_db):
        """Test moving ingredient to root (no parent)."""
        dark = test_db.query(Ingredient).filter(Ingredient.slug == "dark-chocolate").first()

        result = ingredient_hierarchy_service.move_ingredient(dark.id, None, session=test_db)

        assert result["parent_ingredient_id"] is None
        assert result["hierarchy_level"] == 0

    def test_cycle_raises_error(self, test_db):
        """Test that cycle raises CircularReferenceError."""
        chocolate = test_db.query(Ingredient).filter(Ingredient.slug == "chocolate").first()
        dark = test_db.query(Ingredient).filter(Ingredient.slug == "dark-chocolate").first()

        with pytest.raises(CircularReferenceError):
            ingredient_hierarchy_service.move_ingredient(chocolate.id, dark.id, session=test_db)

    def test_max_depth_exceeded_raises_error(self, test_db):
        """Test that exceeding max depth raises MaxDepthExceededError."""
        # Try to move a leaf under another leaf (would make it level 3)
        semi_sweet = test_db.query(Ingredient).filter(Ingredient.slug == "semi-sweet-chips").first()
        bittersweet = (
            test_db.query(Ingredient).filter(Ingredient.slug == "bittersweet-chips").first()
        )

        with pytest.raises(MaxDepthExceededError):
            ingredient_hierarchy_service.move_ingredient(
                semi_sweet.id, bittersweet.id, session=test_db
            )

    def test_ingredient_not_found(self, test_db):
        """Test that IngredientNotFound is raised for invalid id."""
        with pytest.raises(IngredientNotFound):
            ingredient_hierarchy_service.move_ingredient(99999, 1, session=test_db)

    def test_parent_not_found(self, test_db):
        """Test that IngredientNotFound is raised for invalid parent."""
        semi_sweet = test_db.query(Ingredient).filter(Ingredient.slug == "semi-sweet-chips").first()
        with pytest.raises(IngredientNotFound):
            ingredient_hierarchy_service.move_ingredient(semi_sweet.id, 99999, session=test_db)


class TestSearchIngredients:
    """Tests for search_ingredients()."""

    def test_match_found(self, test_db):
        """Test that matching ingredients are returned."""
        results = ingredient_hierarchy_service.search_ingredients("chocolate", session=test_db)

        # Should match: Chocolate, Dark Chocolate, Milk Chocolate, Milk Chocolate Chips
        assert len(results) >= 4
        names = [r["display_name"] for r in results]
        assert "Chocolate" in names
        assert "Dark Chocolate" in names

    def test_partial_match(self, test_db):
        """Test partial match works."""
        results = ingredient_hierarchy_service.search_ingredients("chips", session=test_db)

        names = [r["display_name"] for r in results]
        assert "Semi-Sweet Chips" in names
        assert "Bittersweet Chips" in names
        assert "Milk Chocolate Chips" in names

    def test_case_insensitive(self, test_db):
        """Test case-insensitive search."""
        results = ingredient_hierarchy_service.search_ingredients("CHOCOLATE", session=test_db)
        assert len(results) >= 1

    def test_no_match_returns_empty(self, test_db):
        """Test that no matches returns empty list."""
        results = ingredient_hierarchy_service.search_ingredients("xyz123", session=test_db)
        assert results == []

    def test_includes_ancestors(self, test_db):
        """Test that results include ancestors field."""
        results = ingredient_hierarchy_service.search_ingredients("Semi-Sweet", session=test_db)

        assert len(results) == 1
        assert "ancestors" in results[0]
        ancestor_names = [a["display_name"] for a in results[0]["ancestors"]]
        assert "Dark Chocolate" in ancestor_names
        assert "Chocolate" in ancestor_names

    def test_limit_parameter(self, test_db):
        """Test that limit parameter restricts results."""
        # Search for "chocolate" should find at least 4 ingredients
        all_results = ingredient_hierarchy_service.search_ingredients("chocolate", session=test_db)
        assert len(all_results) >= 4

        # With limit=2, should get exactly 2
        limited_results = ingredient_hierarchy_service.search_ingredients(
            "chocolate", limit=2, session=test_db
        )
        assert len(limited_results) == 2


class TestGetIngredientsByLevel:
    """Tests for get_ingredients_by_level()."""

    def test_returns_root_level_ingredients(self, test_db):
        """Test getting root level (0) ingredients."""
        results = ingredient_hierarchy_service.get_ingredients_by_level(0, session=test_db)

        assert len(results) == 2  # Chocolate, Flour
        names = [r["display_name"] for r in results]
        assert "Chocolate" in names
        assert "Flour" in names

    def test_returns_mid_level_ingredients(self, test_db):
        """Test getting mid level (1) ingredients."""
        results = ingredient_hierarchy_service.get_ingredients_by_level(1, session=test_db)

        assert len(results) == 2  # Dark Chocolate, Milk Chocolate
        names = [r["display_name"] for r in results]
        assert "Dark Chocolate" in names
        assert "Milk Chocolate" in names

    def test_returns_leaf_level_ingredients(self, test_db):
        """Test getting leaf level (2) ingredients."""
        results = ingredient_hierarchy_service.get_ingredients_by_level(2, session=test_db)

        # 4 leaves: Semi-Sweet, Bittersweet, Milk Chocolate Chips, All-Purpose Flour
        assert len(results) == 4
        names = [r["display_name"] for r in results]
        assert "Semi-Sweet Chips" in names
        assert "All-Purpose Flour" in names

    def test_sorted_by_display_name(self, test_db):
        """Test results are sorted by display_name."""
        results = ingredient_hierarchy_service.get_ingredients_by_level(2, session=test_db)
        names = [r["display_name"] for r in results]
        assert names == sorted(names)


class TestGetIngredientById:
    """Tests for get_ingredient_by_id()."""

    def test_returns_ingredient(self, test_db):
        """Test getting an ingredient by ID."""
        # Get chocolate root's ID
        roots = ingredient_hierarchy_service.get_root_ingredients(session=test_db)
        chocolate = next(r for r in roots if r["display_name"] == "Chocolate")

        result = ingredient_hierarchy_service.get_ingredient_by_id(chocolate["id"], session=test_db)

        assert result is not None
        assert result["display_name"] == "Chocolate"
        assert result["hierarchy_level"] == 0

    def test_returns_none_for_nonexistent(self, test_db):
        """Test returns None for nonexistent ID."""
        result = ingredient_hierarchy_service.get_ingredient_by_id(99999, session=test_db)
        assert result is None


class TestGetIngredientTree:
    """Tests for get_ingredient_tree()."""

    def test_returns_nested_structure(self, test_db):
        """Test that tree has proper nested structure."""
        tree = ingredient_hierarchy_service.get_ingredient_tree(session=test_db)

        # Should have 2 roots
        assert len(tree) == 2
        root_names = [r["display_name"] for r in tree]
        assert "Chocolate" in root_names
        assert "Flour" in root_names

    def test_children_are_nested(self, test_db):
        """Test that children are properly nested."""
        tree = ingredient_hierarchy_service.get_ingredient_tree(session=test_db)

        chocolate = next(r for r in tree if r["display_name"] == "Chocolate")

        # Chocolate should have 2 children: Dark Chocolate, Milk Chocolate
        assert len(chocolate["children"]) == 2
        child_names = [c["display_name"] for c in chocolate["children"]]
        assert "Dark Chocolate" in child_names
        assert "Milk Chocolate" in child_names

    def test_grandchildren_are_nested(self, test_db):
        """Test that grandchildren are properly nested."""
        tree = ingredient_hierarchy_service.get_ingredient_tree(session=test_db)

        chocolate = next(r for r in tree if r["display_name"] == "Chocolate")
        dark_choc = next(c for c in chocolate["children"] if c["display_name"] == "Dark Chocolate")

        # Dark Chocolate should have 2 leaves
        assert len(dark_choc["children"]) == 2
        leaf_names = [c["display_name"] for c in dark_choc["children"]]
        assert "Semi-Sweet Chips" in leaf_names
        assert "Bittersweet Chips" in leaf_names


class TestValidateHierarchy:
    """Tests for validate_hierarchy()."""

    def test_valid_parent_returns_true(self, test_db):
        """Test that valid parent assignment returns True."""
        # Get IDs
        roots = ingredient_hierarchy_service.get_root_ingredients(session=test_db)
        chocolate = next(r for r in roots if r["display_name"] == "Chocolate")
        leaves = ingredient_hierarchy_service.get_leaf_ingredients(session=test_db)
        semi_sweet = next(l for l in leaves if l["display_name"] == "Semi-Sweet Chips")

        # Moving a leaf under root is valid
        result = ingredient_hierarchy_service.validate_hierarchy(
            semi_sweet["id"], chocolate["id"], session=test_db
        )
        assert result is True

    def test_becoming_root_is_valid(self, test_db):
        """Test that making an ingredient root is valid."""
        leaves = ingredient_hierarchy_service.get_leaf_ingredients(session=test_db)
        semi_sweet = next(l for l in leaves if l["display_name"] == "Semi-Sweet Chips")

        result = ingredient_hierarchy_service.validate_hierarchy(
            semi_sweet["id"], None, session=test_db
        )
        assert result is True

    def test_cycle_raises_error(self, test_db):
        """Test that circular reference raises error."""
        roots = ingredient_hierarchy_service.get_root_ingredients(session=test_db)
        chocolate = next(r for r in roots if r["display_name"] == "Chocolate")
        children = ingredient_hierarchy_service.get_children(chocolate["id"], session=test_db)
        dark_choc = next(c for c in children if c["display_name"] == "Dark Chocolate")

        # Trying to make Chocolate a child of Dark Chocolate creates a cycle
        with pytest.raises(CircularReferenceError):
            ingredient_hierarchy_service.validate_hierarchy(
                chocolate["id"], dark_choc["id"], session=test_db
            )

    def test_max_depth_raises_error(self, test_db):
        """Test that exceeding max depth raises error."""
        leaves = ingredient_hierarchy_service.get_leaf_ingredients(session=test_db)
        semi_sweet = next(l for l in leaves if l["display_name"] == "Semi-Sweet Chips")
        bittersweet = next(l for l in leaves if l["display_name"] == "Bittersweet Chips")

        # Trying to make a leaf a child of another leaf exceeds depth
        with pytest.raises(MaxDepthExceededError):
            ingredient_hierarchy_service.validate_hierarchy(
                semi_sweet["id"], bittersweet["id"], session=test_db
            )

    def test_ingredient_not_found(self, test_db):
        """Test that nonexistent ingredient raises error."""
        with pytest.raises(IngredientNotFound):
            ingredient_hierarchy_service.validate_hierarchy(99999, None, session=test_db)

    def test_parent_not_found(self, test_db):
        """Test that nonexistent parent raises error."""
        leaves = ingredient_hierarchy_service.get_leaf_ingredients(session=test_db)
        semi_sweet = next(l for l in leaves if l["display_name"] == "Semi-Sweet Chips")

        with pytest.raises(IngredientNotFound):
            ingredient_hierarchy_service.validate_hierarchy(
                semi_sweet["id"], 99999, session=test_db
            )


# =============================================================================
# Feature 033: Convenience Function Tests
# =============================================================================


@pytest.fixture
def test_db_with_products():
    """Create a test database with sample hierarchy data AND products."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    Session = scoped_session(session_factory)
    session = Session()

    # Create sample hierarchy:
    # Chocolate (level 0)
    #   - Dark Chocolate (level 1)
    #       - Semi-Sweet Chips (level 2) [3 products]
    #       - Bittersweet Chips (level 2) [0 products]
    #   - Milk Chocolate (level 1)
    #       - Milk Chocolate Chips (level 2) [2 products]
    # Flour (level 0)
    #   - All-Purpose Flour (level 2) [0 products]

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
    session.flush()

    bittersweet = Ingredient(
        display_name="Bittersweet Chips",
        slug="bittersweet-chips",
        category="Chocolate",
        hierarchy_level=2,
        parent_ingredient_id=dark_chocolate.id,
    )
    session.add(bittersweet)
    session.flush()

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
    session.flush()

    flour = Ingredient(
        display_name="Flour",
        slug="flour",
        category="Flour",
        hierarchy_level=0,
        parent_ingredient_id=None,
    )
    session.add(flour)
    session.flush()

    ap_flour = Ingredient(
        display_name="All-Purpose Flour",
        slug="all-purpose-flour",
        category="Flour",
        hierarchy_level=2,
        parent_ingredient_id=flour.id,
    )
    session.add(ap_flour)
    session.flush()

    # Add products linked to ingredients
    # 3 products linked to Semi-Sweet Chips
    for i in range(3):
        product = Product(
            product_name=f"Semi-Sweet Product {i+1}",
            brand=f"Brand {i+1}",
            ingredient_id=semi_sweet.id,
            package_unit="bag",
            package_unit_quantity=12.0,
        )
        session.add(product)

    # 2 products linked to Milk Chocolate Chips
    for i in range(2):
        product = Product(
            product_name=f"Milk Chips Product {i+1}",
            brand=f"Brand {i+1}",
            ingredient_id=milk_chips.id,
            package_unit="bag",
            package_unit_quantity=12.0,
        )
        session.add(product)

    session.commit()

    yield session

    session.close()
    Session.remove()


class TestGetChildCount:
    """Tests for get_child_count() (Feature 033)."""

    def test_root_with_children(self, test_db_with_products):
        """Test counting children of root ingredient with children."""
        chocolate = (
            test_db_with_products.query(Ingredient).filter(Ingredient.slug == "chocolate").first()
        )
        count = ingredient_hierarchy_service.get_child_count(
            chocolate.id, session=test_db_with_products
        )
        assert count == 2  # Dark Chocolate, Milk Chocolate

    def test_mid_tier_with_children(self, test_db_with_products):
        """Test counting children of mid-tier ingredient."""
        dark_choc = (
            test_db_with_products.query(Ingredient)
            .filter(Ingredient.slug == "dark-chocolate")
            .first()
        )
        count = ingredient_hierarchy_service.get_child_count(
            dark_choc.id, session=test_db_with_products
        )
        assert count == 2  # Semi-Sweet, Bittersweet

    def test_leaf_has_no_children(self, test_db_with_products):
        """Test that leaf ingredient has 0 children."""
        semi_sweet = (
            test_db_with_products.query(Ingredient)
            .filter(Ingredient.slug == "semi-sweet-chips")
            .first()
        )
        count = ingredient_hierarchy_service.get_child_count(
            semi_sweet.id, session=test_db_with_products
        )
        assert count == 0

    def test_nonexistent_ingredient_returns_zero(self, test_db_with_products):
        """Test that nonexistent ingredient returns 0 (not an error)."""
        count = ingredient_hierarchy_service.get_child_count(99999, session=test_db_with_products)
        assert count == 0


class TestGetProductCount:
    """Tests for get_product_count() (Feature 033)."""

    def test_ingredient_with_products(self, test_db_with_products):
        """Test counting products for ingredient with products."""
        semi_sweet = (
            test_db_with_products.query(Ingredient)
            .filter(Ingredient.slug == "semi-sweet-chips")
            .first()
        )
        count = ingredient_hierarchy_service.get_product_count(
            semi_sweet.id, session=test_db_with_products
        )
        assert count == 3

    def test_ingredient_with_different_product_count(self, test_db_with_products):
        """Test counting products for another ingredient."""
        milk_chips = (
            test_db_with_products.query(Ingredient)
            .filter(Ingredient.slug == "milk-chocolate-chips")
            .first()
        )
        count = ingredient_hierarchy_service.get_product_count(
            milk_chips.id, session=test_db_with_products
        )
        assert count == 2

    def test_ingredient_with_no_products(self, test_db_with_products):
        """Test that ingredient with no products returns 0."""
        bittersweet = (
            test_db_with_products.query(Ingredient)
            .filter(Ingredient.slug == "bittersweet-chips")
            .first()
        )
        count = ingredient_hierarchy_service.get_product_count(
            bittersweet.id, session=test_db_with_products
        )
        assert count == 0

    def test_nonexistent_ingredient_returns_zero(self, test_db_with_products):
        """Test that nonexistent ingredient returns 0."""
        count = ingredient_hierarchy_service.get_product_count(99999, session=test_db_with_products)
        assert count == 0


class TestCanChangeParent:
    """Tests for can_change_parent() (Feature 033)."""

    def test_valid_change_returns_allowed(self, test_db_with_products):
        """Test that valid parent change returns allowed=True."""
        semi_sweet = (
            test_db_with_products.query(Ingredient)
            .filter(Ingredient.slug == "semi-sweet-chips")
            .first()
        )
        milk_choc = (
            test_db_with_products.query(Ingredient)
            .filter(Ingredient.slug == "milk-chocolate")
            .first()
        )

        result = ingredient_hierarchy_service.can_change_parent(
            semi_sweet.id, milk_choc.id, session=test_db_with_products
        )

        assert result["allowed"] is True
        assert result["reason"] == ""
        assert result["new_level"] == 2  # Child of L1 = L2

    def test_becoming_root_is_allowed(self, test_db_with_products):
        """Test that becoming root is allowed."""
        semi_sweet = (
            test_db_with_products.query(Ingredient)
            .filter(Ingredient.slug == "semi-sweet-chips")
            .first()
        )

        result = ingredient_hierarchy_service.can_change_parent(
            semi_sweet.id, None, session=test_db_with_products
        )

        assert result["allowed"] is True
        assert result["new_level"] == 0

    def test_circular_reference_blocked(self, test_db_with_products):
        """Test that circular reference is blocked."""
        chocolate = (
            test_db_with_products.query(Ingredient).filter(Ingredient.slug == "chocolate").first()
        )
        dark_choc = (
            test_db_with_products.query(Ingredient)
            .filter(Ingredient.slug == "dark-chocolate")
            .first()
        )

        # Try to make Chocolate a child of Dark Chocolate (its own child)
        result = ingredient_hierarchy_service.can_change_parent(
            chocolate.id, dark_choc.id, session=test_db_with_products
        )

        assert result["allowed"] is False
        assert "circular" in result["reason"].lower()

    def test_depth_exceeded_blocked(self, test_db_with_products):
        """Test that exceeding max depth is blocked."""
        semi_sweet = (
            test_db_with_products.query(Ingredient)
            .filter(Ingredient.slug == "semi-sweet-chips")
            .first()
        )
        bittersweet = (
            test_db_with_products.query(Ingredient)
            .filter(Ingredient.slug == "bittersweet-chips")
            .first()
        )

        # Try to make semi-sweet a child of bittersweet (both are L2, would make L3)
        result = ingredient_hierarchy_service.can_change_parent(
            semi_sweet.id, bittersweet.id, session=test_db_with_products
        )

        assert result["allowed"] is False
        assert "depth" in result["reason"].lower()

    def test_product_warning_included(self, test_db_with_products):
        """Test that product count is included in warnings."""
        semi_sweet = (
            test_db_with_products.query(Ingredient)
            .filter(Ingredient.slug == "semi-sweet-chips")
            .first()
        )
        milk_choc = (
            test_db_with_products.query(Ingredient)
            .filter(Ingredient.slug == "milk-chocolate")
            .first()
        )

        result = ingredient_hierarchy_service.can_change_parent(
            semi_sweet.id, milk_choc.id, session=test_db_with_products
        )

        assert result["allowed"] is True
        assert result["product_count"] == 3
        assert any("3 linked product" in w for w in result["warnings"])

    def test_child_warning_included(self, test_db_with_products):
        """Test that child count is included in warnings."""
        dark_choc = (
            test_db_with_products.query(Ingredient)
            .filter(Ingredient.slug == "dark-chocolate")
            .first()
        )
        chocolate = (
            test_db_with_products.query(Ingredient).filter(Ingredient.slug == "chocolate").first()
        )

        # Moving dark_choc to be directly under root (stays L1)
        result = ingredient_hierarchy_service.can_change_parent(
            dark_choc.id, None, session=test_db_with_products
        )

        assert result["allowed"] is True
        assert result["child_count"] == 2
        assert any("2 child ingredient" in w for w in result["warnings"])

    def test_no_warnings_when_no_products_or_children(self, test_db_with_products):
        """Test that no warnings when ingredient has no products or children."""
        bittersweet = (
            test_db_with_products.query(Ingredient)
            .filter(Ingredient.slug == "bittersweet-chips")
            .first()
        )
        milk_choc = (
            test_db_with_products.query(Ingredient)
            .filter(Ingredient.slug == "milk-chocolate")
            .first()
        )

        result = ingredient_hierarchy_service.can_change_parent(
            bittersweet.id, milk_choc.id, session=test_db_with_products
        )

        assert result["allowed"] is True
        assert result["product_count"] == 0
        assert result["child_count"] == 0
        assert len(result["warnings"]) == 0

    def test_counts_returned_even_when_blocked(self, test_db_with_products):
        """Test that counts are still returned when change is blocked."""
        semi_sweet = (
            test_db_with_products.query(Ingredient)
            .filter(Ingredient.slug == "semi-sweet-chips")
            .first()
        )
        bittersweet = (
            test_db_with_products.query(Ingredient)
            .filter(Ingredient.slug == "bittersweet-chips")
            .first()
        )

        result = ingredient_hierarchy_service.can_change_parent(
            semi_sweet.id, bittersweet.id, session=test_db_with_products
        )

        assert result["allowed"] is False
        assert result["product_count"] == 3  # Still counted
        assert result["child_count"] == 0  # Still counted


# =============================================================================
# Feature 052: Leaf Ingredients with Ancestors Tests
# =============================================================================


class TestGetAllLeafIngredientsWithAncestors:
    """Tests for get_all_leaf_ingredients_with_ancestors() (Feature 052)."""

    def test_returns_only_l2_ingredients(self, test_db):
        """Test that only L2 (leaf) ingredients are returned."""
        results = ingredient_hierarchy_service.get_all_leaf_ingredients_with_ancestors(
            session=test_db
        )

        # Should have 4 L2 ingredients: Semi-Sweet, Bittersweet, Milk Chips, All-Purpose Flour
        assert len(results) == 4
        l2_names = [r["l2_name"] for r in results]
        assert "Semi-Sweet Chips" in l2_names
        assert "Bittersweet Chips" in l2_names
        assert "Milk Chocolate Chips" in l2_names
        assert "All-Purpose Flour" in l2_names

    def test_l0_and_l1_names_populated(self, test_db):
        """Test that L0 and L1 ancestor names are correctly populated."""
        results = ingredient_hierarchy_service.get_all_leaf_ingredients_with_ancestors(
            session=test_db
        )

        # Find Semi-Sweet Chips and check ancestors
        semi_sweet = next(r for r in results if r["l2_name"] == "Semi-Sweet Chips")
        assert semi_sweet["l0_name"] == "Chocolate"
        assert semi_sweet["l1_name"] == "Dark Chocolate"

    def test_ingredient_dict_included(self, test_db):
        """Test that full ingredient dict is included."""
        results = ingredient_hierarchy_service.get_all_leaf_ingredients_with_ancestors(
            session=test_db
        )

        semi_sweet = next(r for r in results if r["l2_name"] == "Semi-Sweet Chips")
        assert "ingredient" in semi_sweet
        assert semi_sweet["ingredient"]["display_name"] == "Semi-Sweet Chips"
        assert semi_sweet["ingredient"]["hierarchy_level"] == 2
        assert semi_sweet["ingredient"]["slug"] == "semi-sweet-chips"

    def test_l0_filter_returns_only_matching_descendants(self, test_db):
        """Test that L0 filter returns only descendants of that L0."""
        # Get chocolate ID
        chocolate = test_db.query(Ingredient).filter(Ingredient.slug == "chocolate").first()

        results = ingredient_hierarchy_service.get_all_leaf_ingredients_with_ancestors(
            l0_filter_id=chocolate.id, session=test_db
        )

        # Should have only chocolate descendants (3): Semi-Sweet, Bittersweet, Milk Chips
        assert len(results) == 3
        l2_names = [r["l2_name"] for r in results]
        assert "Semi-Sweet Chips" in l2_names
        assert "Bittersweet Chips" in l2_names
        assert "Milk Chocolate Chips" in l2_names
        # All-Purpose Flour should NOT be included
        assert "All-Purpose Flour" not in l2_names

    def test_l0_filter_with_no_matching_leaves(self, test_db):
        """Test L0 filter with category that has no L2 descendants."""
        # Create an L0 with no leaves (edge case)
        empty_root = Ingredient(
            display_name="Empty Category",
            slug="empty-category",
            category="Empty",
            hierarchy_level=0,
            parent_ingredient_id=None,
        )
        test_db.add(empty_root)
        test_db.flush()

        results = ingredient_hierarchy_service.get_all_leaf_ingredients_with_ancestors(
            l0_filter_id=empty_root.id, session=test_db
        )

        assert results == []

    def test_handles_l2_with_missing_l0_parent(self, test_db):
        """Test that L2 directly under L0 (missing L1) returns empty L1 name."""
        # All-Purpose Flour is directly under Flour (L0), skipping L1
        results = ingredient_hierarchy_service.get_all_leaf_ingredients_with_ancestors(
            session=test_db
        )

        ap_flour = next(r for r in results if r["l2_name"] == "All-Purpose Flour")
        # In this test data, All-Purpose Flour is L2 directly under L0 (Flour)
        # This means its parent is Flour (L0), but its parent.parent is None
        assert ap_flour["l1_name"] == "Flour"  # Parent is Flour
        assert ap_flour["l0_name"] == ""  # No grandparent

    def test_results_sorted_by_l2_name(self, test_db):
        """Test that results are sorted by L2 (ingredient) name."""
        results = ingredient_hierarchy_service.get_all_leaf_ingredients_with_ancestors(
            session=test_db
        )

        l2_names = [r["l2_name"] for r in results]
        assert l2_names == sorted(l2_names)


class TestGetIngredientWithAncestors:
    """Tests for get_ingredient_with_ancestors() (Feature 052)."""

    def test_returns_ancestor_names(self, test_db):
        """Test that ancestor names are correctly returned."""
        semi_sweet = test_db.query(Ingredient).filter(Ingredient.slug == "semi-sweet-chips").first()

        result = ingredient_hierarchy_service.get_ingredient_with_ancestors(
            semi_sweet.id, session=test_db
        )

        assert result is not None
        assert result["l2_name"] == "Semi-Sweet Chips"
        assert result["l1_name"] == "Dark Chocolate"
        assert result["l0_name"] == "Chocolate"

    def test_includes_full_ingredient_dict(self, test_db):
        """Test that full ingredient dict is included."""
        semi_sweet = test_db.query(Ingredient).filter(Ingredient.slug == "semi-sweet-chips").first()

        result = ingredient_hierarchy_service.get_ingredient_with_ancestors(
            semi_sweet.id, session=test_db
        )

        assert "ingredient" in result
        assert result["ingredient"]["slug"] == "semi-sweet-chips"
        assert result["ingredient"]["hierarchy_level"] == 2

    def test_nonexistent_ingredient_returns_none(self, test_db):
        """Test that nonexistent ingredient returns None."""
        result = ingredient_hierarchy_service.get_ingredient_with_ancestors(99999, session=test_db)
        assert result is None

    def test_l1_ingredient_has_partial_ancestors(self, test_db):
        """Test that L1 ingredient has empty L0 and L1 is parent."""
        dark = test_db.query(Ingredient).filter(Ingredient.slug == "dark-chocolate").first()

        result = ingredient_hierarchy_service.get_ingredient_with_ancestors(dark.id, session=test_db)

        assert result is not None
        assert result["l2_name"] == "Dark Chocolate"
        assert result["l1_name"] == "Chocolate"  # Parent
        assert result["l0_name"] == ""  # No grandparent

    def test_l0_ingredient_has_no_ancestors(self, test_db):
        """Test that L0 (root) ingredient has empty ancestor names."""
        chocolate = test_db.query(Ingredient).filter(Ingredient.slug == "chocolate").first()

        result = ingredient_hierarchy_service.get_ingredient_with_ancestors(
            chocolate.id, session=test_db
        )

        assert result is not None
        assert result["l2_name"] == "Chocolate"
        assert result["l1_name"] == ""
        assert result["l0_name"] == ""


# =============================================================================
# Feature 052: Usage Counts Tests
# =============================================================================


class TestGetUsageCounts:
    """Tests for get_usage_counts() (Feature 052)."""

    def test_returns_product_and_recipe_counts(self, test_db_with_products):
        """Test that both product and recipe counts are returned."""
        semi_sweet = (
            test_db_with_products.query(Ingredient)
            .filter(Ingredient.slug == "semi-sweet-chips")
            .first()
        )

        result = ingredient_hierarchy_service.get_usage_counts(
            semi_sweet.id, session=test_db_with_products
        )

        assert "product_count" in result
        assert "recipe_count" in result
        assert result["product_count"] == 3  # From test_db_with_products fixture

    def test_zero_counts_for_unused_ingredient(self, test_db_with_products):
        """Test that unused ingredient returns zero counts."""
        bittersweet = (
            test_db_with_products.query(Ingredient)
            .filter(Ingredient.slug == "bittersweet-chips")
            .first()
        )

        result = ingredient_hierarchy_service.get_usage_counts(
            bittersweet.id, session=test_db_with_products
        )

        assert result["product_count"] == 0
        assert result["recipe_count"] == 0

    def test_nonexistent_ingredient_returns_zeros(self, test_db_with_products):
        """Test that nonexistent ingredient returns zero counts."""
        result = ingredient_hierarchy_service.get_usage_counts(99999, session=test_db_with_products)
        assert result["product_count"] == 0
        assert result["recipe_count"] == 0


# =============================================================================
# Feature 052: Add Leaf Ingredient Tests
# =============================================================================


class TestAddLeafIngredient:
    """Tests for add_leaf_ingredient() (Feature 052)."""

    def test_add_leaf_ingredient_success(self, test_db):
        """Test adding L2 ingredient under L1 parent."""
        # Get an L1 parent (dark-chocolate is level 1 in fixture)
        dark_choc = test_db.query(Ingredient).filter(Ingredient.slug == "dark-chocolate").first()

        result = ingredient_hierarchy_service.add_leaf_ingredient(
            parent_id=dark_choc.id, name="White Chocolate Chips", session=test_db
        )

        assert result is not None
        assert result["display_name"] == "White Chocolate Chips"
        assert result["hierarchy_level"] == 2
        assert result["parent_ingredient_id"] == dark_choc.id
        assert "slug" in result

    def test_add_leaf_ingredient_trims_whitespace(self, test_db):
        """Test that leading/trailing whitespace is trimmed."""
        dark_choc = test_db.query(Ingredient).filter(Ingredient.slug == "dark-chocolate").first()

        result = ingredient_hierarchy_service.add_leaf_ingredient(
            parent_id=dark_choc.id, name="  Caramel Chips  ", session=test_db
        )

        assert result["display_name"] == "Caramel Chips"

    def test_add_leaf_ingredient_parent_not_found(self, test_db):
        """Test error when parent doesn't exist."""
        with pytest.raises(ValueError, match="not found"):
            ingredient_hierarchy_service.add_leaf_ingredient(
                parent_id=99999, name="Test Ingredient", session=test_db
            )

    def test_add_leaf_ingredient_parent_not_l1(self, test_db):
        """Test error when parent is not L1 (e.g., L0 or L2)."""
        # Get an L0 ingredient
        chocolate = test_db.query(Ingredient).filter(Ingredient.slug == "chocolate").first()

        with pytest.raises(ValueError, match="must be L1"):
            ingredient_hierarchy_service.add_leaf_ingredient(
                parent_id=chocolate.id, name="Test Ingredient", session=test_db
            )

    def test_add_leaf_ingredient_duplicate_name(self, test_db):
        """Test error when name already exists under same parent."""
        # Get L1 parent that has children (dark-chocolate has semi-sweet and bittersweet)
        dark_choc = test_db.query(Ingredient).filter(Ingredient.slug == "dark-chocolate").first()
        existing = (
            test_db.query(Ingredient)
            .filter(Ingredient.parent_ingredient_id == dark_choc.id)
            .first()
        )

        with pytest.raises(ValueError, match="already exists"):
            ingredient_hierarchy_service.add_leaf_ingredient(
                parent_id=dark_choc.id, name=existing.display_name, session=test_db
            )

    def test_add_leaf_ingredient_empty_name(self, test_db):
        """Test error when name is empty."""
        dark_choc = test_db.query(Ingredient).filter(Ingredient.slug == "dark-chocolate").first()

        with pytest.raises(ValueError, match="cannot be empty"):
            ingredient_hierarchy_service.add_leaf_ingredient(
                parent_id=dark_choc.id, name="", session=test_db
            )

    def test_add_leaf_ingredient_whitespace_only_name(self, test_db):
        """Test error when name is whitespace only."""
        dark_choc = test_db.query(Ingredient).filter(Ingredient.slug == "dark-chocolate").first()

        with pytest.raises(ValueError, match="cannot be empty"):
            ingredient_hierarchy_service.add_leaf_ingredient(
                parent_id=dark_choc.id, name="   ", session=test_db
            )

    def test_add_leaf_ingredient_generates_slug(self, test_db):
        """Test that slug is auto-generated from name."""
        dark_choc = test_db.query(Ingredient).filter(Ingredient.slug == "dark-chocolate").first()

        result = ingredient_hierarchy_service.add_leaf_ingredient(
            parent_id=dark_choc.id, name="Extra Dark Chips", session=test_db
        )

        assert result["slug"] == "extra-dark-chips"

    def test_add_leaf_ingredient_case_insensitive_duplicate_check(self, test_db):
        """Test that duplicate check is case-insensitive."""
        dark_choc = test_db.query(Ingredient).filter(Ingredient.slug == "dark-chocolate").first()
        existing = (
            test_db.query(Ingredient)
            .filter(Ingredient.parent_ingredient_id == dark_choc.id)
            .first()
        )

        with pytest.raises(ValueError, match="already exists"):
            ingredient_hierarchy_service.add_leaf_ingredient(
                parent_id=dark_choc.id, name=existing.display_name.upper(), session=test_db
            )
