"""
Tests for material hierarchy service (Feature 052).

Tests cover:
- get_materials_with_parents()
- get_material_with_parents()
- get_category_hierarchy()
- get_hierarchy_tree()
- get_usage_counts()
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from src.models.base import Base
from src.models.material import Material
from src.models.material_subcategory import MaterialSubcategory
from src.models.material_category import MaterialCategory
from src.services import material_hierarchy_service


@pytest.fixture
def test_db():
    """Create a test database with sample material hierarchy data."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    Session = scoped_session(session_factory)
    session = Session()

    # Create sample hierarchy:
    # Ribbons (category)
    #   └─ Satin (subcategory)
    #       └─ Red Satin 1-inch (material)
    #       └─ Blue Satin 1-inch (material)
    #   └─ Grosgrain (subcategory)
    #       └─ White Grosgrain 5/8 (material)
    # Boxes (category)
    #   └─ Window Boxes (subcategory)
    #       └─ 10x10 Window Box (material)

    ribbons = MaterialCategory(
        name="Ribbons",
        slug="ribbons",
        description="Ribbon materials",
        sort_order=0,
    )
    session.add(ribbons)
    session.flush()

    satin = MaterialSubcategory(
        category_id=ribbons.id,
        name="Satin",
        slug="satin",
        sort_order=0,
    )
    session.add(satin)
    session.flush()

    red_satin = Material(
        subcategory_id=satin.id,
        name="Red Satin 1-inch",
        slug="red-satin-1-inch",
        base_unit_type="linear_inches",
    )
    session.add(red_satin)

    blue_satin = Material(
        subcategory_id=satin.id,
        name="Blue Satin 1-inch",
        slug="blue-satin-1-inch",
        base_unit_type="linear_inches",
    )
    session.add(blue_satin)

    grosgrain = MaterialSubcategory(
        category_id=ribbons.id,
        name="Grosgrain",
        slug="grosgrain",
        sort_order=1,
    )
    session.add(grosgrain)
    session.flush()

    white_grosgrain = Material(
        subcategory_id=grosgrain.id,
        name="White Grosgrain 5/8",
        slug="white-grosgrain-5-8",
        base_unit_type="linear_inches",
    )
    session.add(white_grosgrain)

    boxes = MaterialCategory(
        name="Boxes",
        slug="boxes",
        description="Box materials",
        sort_order=1,
    )
    session.add(boxes)
    session.flush()

    window_boxes = MaterialSubcategory(
        category_id=boxes.id,
        name="Window Boxes",
        slug="window-boxes",
        sort_order=0,
    )
    session.add(window_boxes)
    session.flush()

    box_10x10 = Material(
        subcategory_id=window_boxes.id,
        name="10x10 Window Box",
        slug="10x10-window-box",
        base_unit_type="each",
    )
    session.add(box_10x10)

    session.commit()

    yield session

    session.close()
    Session.remove()


class TestGetMaterialsWithParents:
    """Tests for get_materials_with_parents() (Feature 052)."""

    def test_returns_all_materials(self, test_db):
        """Test that all materials are returned."""
        results = material_hierarchy_service.get_materials_with_parents(session=test_db)

        # Should have 4 materials
        assert len(results) == 4
        material_names = [r["material_name"] for r in results]
        assert "Red Satin 1-inch" in material_names
        assert "Blue Satin 1-inch" in material_names
        assert "White Grosgrain 5/8" in material_names
        assert "10x10 Window Box" in material_names

    def test_includes_hierarchy_names(self, test_db):
        """Test that category and subcategory names are populated."""
        results = material_hierarchy_service.get_materials_with_parents(session=test_db)

        # Find Red Satin and check hierarchy
        red_satin = next(r for r in results if r["material_name"] == "Red Satin 1-inch")
        assert red_satin["category_name"] == "Ribbons"
        assert red_satin["subcategory_name"] == "Satin"

        # Find Window Box and check hierarchy
        box = next(r for r in results if r["material_name"] == "10x10 Window Box")
        assert box["category_name"] == "Boxes"
        assert box["subcategory_name"] == "Window Boxes"

    def test_includes_material_dict(self, test_db):
        """Test that full material dict is included."""
        results = material_hierarchy_service.get_materials_with_parents(session=test_db)

        red_satin = next(r for r in results if r["material_name"] == "Red Satin 1-inch")
        assert "material" in red_satin
        assert red_satin["material"]["name"] == "Red Satin 1-inch"
        assert red_satin["material"]["slug"] == "red-satin-1-inch"
        assert red_satin["material"]["base_unit_type"] == "linear_inches"

    def test_category_filter(self, test_db):
        """Test filtering by category name."""
        results = material_hierarchy_service.get_materials_with_parents(
            category_filter="Ribbons", session=test_db
        )

        # Should only have ribbon materials (3)
        assert len(results) == 3
        material_names = [r["material_name"] for r in results]
        assert "Red Satin 1-inch" in material_names
        assert "Blue Satin 1-inch" in material_names
        assert "White Grosgrain 5/8" in material_names
        # No boxes
        assert "10x10 Window Box" not in material_names

    def test_category_filter_no_match(self, test_db):
        """Test filtering by category with no matches."""
        results = material_hierarchy_service.get_materials_with_parents(
            category_filter="Nonexistent", session=test_db
        )

        assert results == []

    def test_results_sorted_by_material_name(self, test_db):
        """Test that results are sorted by material name."""
        results = material_hierarchy_service.get_materials_with_parents(session=test_db)

        material_names = [r["material_name"] for r in results]
        assert material_names == sorted(material_names)

    def test_empty_database(self):
        """Test with empty database."""
        engine = create_engine("sqlite:///:memory:", echo=False)
        Base.metadata.create_all(engine)
        session_factory = sessionmaker(bind=engine)
        session = session_factory()

        results = material_hierarchy_service.get_materials_with_parents(session=session)
        assert results == []

        session.close()


class TestGetMaterialWithParents:
    """Tests for get_material_with_parents() (Feature 052)."""

    def test_returns_hierarchy_names(self, test_db):
        """Test that hierarchy names are correctly returned."""
        # Get a material ID
        mat = test_db.query(Material).filter(Material.slug == "red-satin-1-inch").first()

        result = material_hierarchy_service.get_material_with_parents(mat.id, session=test_db)

        assert result is not None
        assert result["material_name"] == "Red Satin 1-inch"
        assert result["subcategory_name"] == "Satin"
        assert result["category_name"] == "Ribbons"

    def test_includes_full_material_dict(self, test_db):
        """Test that full material dict is included."""
        mat = test_db.query(Material).filter(Material.slug == "red-satin-1-inch").first()

        result = material_hierarchy_service.get_material_with_parents(mat.id, session=test_db)

        assert "material" in result
        assert result["material"]["slug"] == "red-satin-1-inch"
        assert result["material"]["base_unit_type"] == "linear_inches"

    def test_nonexistent_material_returns_none(self, test_db):
        """Test that nonexistent material returns None."""
        result = material_hierarchy_service.get_material_with_parents(99999, session=test_db)
        assert result is None


class TestGetCategoryHierarchy:
    """Tests for get_category_hierarchy() (Feature 052)."""

    def test_returns_all_categories(self, test_db):
        """Test that all categories are returned."""
        results = material_hierarchy_service.get_category_hierarchy(session=test_db)

        assert len(results) == 2
        category_names = [r["name"] for r in results]
        assert "Ribbons" in category_names
        assert "Boxes" in category_names

    def test_includes_subcategories(self, test_db):
        """Test that subcategories are nested in categories."""
        results = material_hierarchy_service.get_category_hierarchy(session=test_db)

        ribbons = next(r for r in results if r["name"] == "Ribbons")
        assert "subcategories" in ribbons
        assert len(ribbons["subcategories"]) == 2
        subcat_names = [s["name"] for s in ribbons["subcategories"]]
        assert "Satin" in subcat_names
        assert "Grosgrain" in subcat_names

    def test_subcategories_include_material_count(self, test_db):
        """Test that subcategories include material count."""
        results = material_hierarchy_service.get_category_hierarchy(session=test_db)

        ribbons = next(r for r in results if r["name"] == "Ribbons")
        satin = next(s for s in ribbons["subcategories"] if s["name"] == "Satin")
        assert satin["material_count"] == 2  # Red and Blue Satin

        grosgrain = next(s for s in ribbons["subcategories"] if s["name"] == "Grosgrain")
        assert grosgrain["material_count"] == 1  # White Grosgrain

    def test_sorted_by_sort_order_then_name(self, test_db):
        """Test that categories are sorted by sort_order, then name."""
        results = material_hierarchy_service.get_category_hierarchy(session=test_db)

        # Ribbons has sort_order=0, Boxes has sort_order=1
        assert results[0]["name"] == "Ribbons"
        assert results[1]["name"] == "Boxes"


class TestGetHierarchyTree:
    """Tests for get_hierarchy_tree() (Feature 052)."""

    def test_returns_nested_structure(self, test_db):
        """Test that hierarchy tree has nested category->subcategory->material structure."""
        results = material_hierarchy_service.get_hierarchy_tree(session=test_db)

        # Should have 2 categories at top level
        assert len(results) == 2
        category_names = [r["name"] for r in results]
        assert "Ribbons" in category_names
        assert "Boxes" in category_names

    def test_nodes_have_correct_type(self, test_db):
        """Test that each node has correct type field."""
        results = material_hierarchy_service.get_hierarchy_tree(session=test_db)

        ribbons = next(r for r in results if r["name"] == "Ribbons")
        assert ribbons["type"] == "category"

        satin = next(c for c in ribbons["children"] if c["name"] == "Satin")
        assert satin["type"] == "subcategory"

        red_satin = next(m for m in satin["children"] if m["name"] == "Red Satin 1-inch")
        assert red_satin["type"] == "material"

    def test_subcategories_nested_in_categories(self, test_db):
        """Test that subcategories are nested under categories."""
        results = material_hierarchy_service.get_hierarchy_tree(session=test_db)

        ribbons = next(r for r in results if r["name"] == "Ribbons")
        assert "children" in ribbons
        assert len(ribbons["children"]) == 2

        subcat_names = [c["name"] for c in ribbons["children"]]
        assert "Satin" in subcat_names
        assert "Grosgrain" in subcat_names

    def test_materials_nested_in_subcategories(self, test_db):
        """Test that materials are nested under subcategories."""
        results = material_hierarchy_service.get_hierarchy_tree(session=test_db)

        ribbons = next(r for r in results if r["name"] == "Ribbons")
        satin = next(c for c in ribbons["children"] if c["name"] == "Satin")

        assert "children" in satin
        assert len(satin["children"]) == 2

        mat_names = [m["name"] for m in satin["children"]]
        assert "Red Satin 1-inch" in mat_names
        assert "Blue Satin 1-inch" in mat_names

    def test_material_nodes_have_empty_children(self, test_db):
        """Test that material nodes have empty children list."""
        results = material_hierarchy_service.get_hierarchy_tree(session=test_db)

        ribbons = next(r for r in results if r["name"] == "Ribbons")
        satin = next(c for c in ribbons["children"] if c["name"] == "Satin")
        red_satin = next(m for m in satin["children"] if m["name"] == "Red Satin 1-inch")

        assert red_satin["children"] == []

    def test_includes_entity_dicts(self, test_db):
        """Test that nodes include full entity dicts."""
        results = material_hierarchy_service.get_hierarchy_tree(session=test_db)

        ribbons = next(r for r in results if r["name"] == "Ribbons")
        assert "category" in ribbons
        assert ribbons["category"]["slug"] == "ribbons"

        satin = next(c for c in ribbons["children"] if c["name"] == "Satin")
        assert "subcategory" in satin
        assert satin["subcategory"]["slug"] == "satin"

        red_satin = next(m for m in satin["children"] if m["name"] == "Red Satin 1-inch")
        assert "material" in red_satin
        assert red_satin["material"]["slug"] == "red-satin-1-inch"


class TestGetUsageCounts:
    """Tests for get_usage_counts() (Feature 052)."""

    def test_material_with_no_products(self, test_db):
        """Test that material with no products returns zero count."""
        mat = test_db.query(Material).filter(Material.slug == "red-satin-1-inch").first()

        result = material_hierarchy_service.get_usage_counts(mat.id, session=test_db)

        assert result["product_count"] == 0

    def test_nonexistent_material_returns_zero(self, test_db):
        """Test that nonexistent material returns zero count."""
        result = material_hierarchy_service.get_usage_counts(99999, session=test_db)

        assert result["product_count"] == 0

    def test_returns_product_count_key(self, test_db):
        """Test that result dict has product_count key."""
        mat = test_db.query(Material).first()

        result = material_hierarchy_service.get_usage_counts(mat.id, session=test_db)

        assert "product_count" in result
        assert isinstance(result["product_count"], int)
