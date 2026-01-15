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


class TestGetAggregatedUsageCounts:
    """Tests for get_aggregated_usage_counts() (Feature 052 - review fix)."""

    def test_material_returns_direct_count(self, test_db):
        """Test material returns direct product count only."""
        red_satin = test_db.query(Material).filter(Material.slug == "red-satin-1-inch").first()

        result = material_hierarchy_service.get_aggregated_usage_counts(
            "material", red_satin.id, session=test_db
        )

        assert "product_count" in result
        assert result["material_count"] == 1  # Just itself

    def test_subcategory_aggregates_materials(self, test_db):
        """Test subcategory aggregates counts from all child materials."""
        satin = test_db.query(MaterialSubcategory).filter(MaterialSubcategory.slug == "satin").first()

        result = material_hierarchy_service.get_aggregated_usage_counts(
            "subcategory", satin.id, session=test_db
        )

        assert "product_count" in result
        # Satin has red and blue satin materials
        assert result["material_count"] >= 2

    def test_category_aggregates_all_materials(self, test_db):
        """Test category aggregates counts from all subcategories and materials."""
        ribbons = test_db.query(MaterialCategory).filter(MaterialCategory.slug == "ribbons").first()

        result = material_hierarchy_service.get_aggregated_usage_counts(
            "category", ribbons.id, session=test_db
        )

        assert "product_count" in result
        # Ribbons has satin (2 materials) and grosgrain (1 material)
        assert result["material_count"] >= 3

    def test_empty_subcategory_returns_zeros(self, test_db):
        """Test empty subcategory returns zero counts."""
        # Create empty subcategory
        ribbons = test_db.query(MaterialCategory).filter(MaterialCategory.slug == "ribbons").first()
        empty_subcat = MaterialSubcategory(
            name="Empty Subcategory",
            slug="empty-subcategory",
            category_id=ribbons.id,
            sort_order=99,
        )
        test_db.add(empty_subcat)
        test_db.flush()

        result = material_hierarchy_service.get_aggregated_usage_counts(
            "subcategory", empty_subcat.id, session=test_db
        )

        assert result["product_count"] == 0
        assert result["material_count"] == 0


class TestAddMaterial:
    """Tests for add_material() (Feature 052)."""

    def test_add_material_success(self, test_db):
        """Test adding material under subcategory."""
        # Get a subcategory
        satin = test_db.query(MaterialSubcategory).filter(MaterialSubcategory.slug == "satin").first()

        result = material_hierarchy_service.add_material(
            subcategory_id=satin.id,
            name="Green Satin 1-inch",
            base_unit_type="linear_inches",
            session=test_db,
        )

        assert result is not None
        assert result["name"] == "Green Satin 1-inch"
        assert result["subcategory_id"] == satin.id
        assert result["base_unit_type"] == "linear_inches"
        assert "slug" in result

    def test_add_material_default_unit_type(self, test_db):
        """Test that default unit type is 'each'."""
        satin = test_db.query(MaterialSubcategory).filter(MaterialSubcategory.slug == "satin").first()

        result = material_hierarchy_service.add_material(
            subcategory_id=satin.id, name="Yellow Satin 1-inch", session=test_db
        )

        assert result["base_unit_type"] == "each"

    def test_add_material_trims_whitespace(self, test_db):
        """Test that leading/trailing whitespace is trimmed."""
        satin = test_db.query(MaterialSubcategory).filter(MaterialSubcategory.slug == "satin").first()

        result = material_hierarchy_service.add_material(
            subcategory_id=satin.id, name="  Purple Satin 1-inch  ", session=test_db
        )

        assert result["name"] == "Purple Satin 1-inch"

    def test_add_material_subcategory_not_found(self, test_db):
        """Test error when subcategory doesn't exist."""
        with pytest.raises(ValueError, match="not found"):
            material_hierarchy_service.add_material(
                subcategory_id=99999, name="Test Material", session=test_db
            )

    def test_add_material_invalid_unit_type(self, test_db):
        """Test error for invalid unit type."""
        satin = test_db.query(MaterialSubcategory).filter(MaterialSubcategory.slug == "satin").first()

        with pytest.raises(ValueError, match="Invalid unit type"):
            material_hierarchy_service.add_material(
                subcategory_id=satin.id,
                name="Test Material",
                base_unit_type="invalid_type",
                session=test_db,
            )

    def test_add_material_duplicate_name(self, test_db):
        """Test error when name already exists in subcategory."""
        satin = test_db.query(MaterialSubcategory).filter(MaterialSubcategory.slug == "satin").first()
        existing = test_db.query(Material).filter(Material.subcategory_id == satin.id).first()

        with pytest.raises(ValueError, match="already exists"):
            material_hierarchy_service.add_material(
                subcategory_id=satin.id, name=existing.name, session=test_db
            )

    def test_add_material_empty_name(self, test_db):
        """Test error when name is empty."""
        satin = test_db.query(MaterialSubcategory).filter(MaterialSubcategory.slug == "satin").first()

        with pytest.raises(ValueError, match="cannot be empty"):
            material_hierarchy_service.add_material(
                subcategory_id=satin.id, name="", session=test_db
            )

    def test_add_material_whitespace_only_name(self, test_db):
        """Test error when name is whitespace only."""
        satin = test_db.query(MaterialSubcategory).filter(MaterialSubcategory.slug == "satin").first()

        with pytest.raises(ValueError, match="cannot be empty"):
            material_hierarchy_service.add_material(
                subcategory_id=satin.id, name="   ", session=test_db
            )

    def test_add_material_generates_slug(self, test_db):
        """Test that slug is auto-generated from name."""
        satin = test_db.query(MaterialSubcategory).filter(MaterialSubcategory.slug == "satin").first()

        result = material_hierarchy_service.add_material(
            subcategory_id=satin.id, name="Orange Satin 2-inch", session=test_db
        )

        assert result["slug"] == "orange-satin-2-inch"

    def test_add_material_case_insensitive_duplicate_check(self, test_db):
        """Test that duplicate check is case-insensitive."""
        satin = test_db.query(MaterialSubcategory).filter(MaterialSubcategory.slug == "satin").first()
        existing = test_db.query(Material).filter(Material.subcategory_id == satin.id).first()

        with pytest.raises(ValueError, match="already exists"):
            material_hierarchy_service.add_material(
                subcategory_id=satin.id, name=existing.name.upper(), session=test_db
            )


class TestRenameItem:
    """Tests for rename_item() (Feature 052)."""

    def test_rename_material_success(self, test_db):
        """Test renaming a material."""
        mat = test_db.query(Material).filter(Material.slug == "red-satin-1-inch").first()

        result = material_hierarchy_service.rename_item(
            item_type="material", item_id=mat.id, new_name="Crimson Satin", session=test_db
        )

        assert result["name"] == "Crimson Satin"
        assert "crimson-satin" in result["slug"]

    def test_rename_subcategory_success(self, test_db):
        """Test renaming a subcategory."""
        subcat = test_db.query(MaterialSubcategory).filter(MaterialSubcategory.slug == "satin").first()

        result = material_hierarchy_service.rename_item(
            item_type="subcategory",
            item_id=subcat.id,
            new_name="Silk Satin",
            session=test_db,
        )

        assert result["name"] == "Silk Satin"
        assert "silk-satin" in result["slug"]

    def test_rename_category_success(self, test_db):
        """Test renaming a category."""
        cat = test_db.query(MaterialCategory).filter(MaterialCategory.slug == "ribbons").first()

        result = material_hierarchy_service.rename_item(
            item_type="category", item_id=cat.id, new_name="Fabric Ribbons", session=test_db
        )

        assert result["name"] == "Fabric Ribbons"
        assert "fabric-ribbons" in result["slug"]

    def test_rename_item_invalid_type(self, test_db):
        """Test error for invalid item type."""
        mat = test_db.query(Material).first()

        with pytest.raises(ValueError, match="Invalid item type"):
            material_hierarchy_service.rename_item(
                item_type="invalid", item_id=mat.id, new_name="Test", session=test_db
            )

    def test_rename_item_empty_name(self, test_db):
        """Test error for empty name."""
        mat = test_db.query(Material).first()

        with pytest.raises(ValueError, match="cannot be empty"):
            material_hierarchy_service.rename_item(
                item_type="material", item_id=mat.id, new_name="   ", session=test_db
            )

    def test_rename_material_not_found(self, test_db):
        """Test error when material doesn't exist."""
        with pytest.raises(ValueError, match="not found"):
            material_hierarchy_service.rename_item(
                item_type="material", item_id=99999, new_name="Test", session=test_db
            )

    def test_rename_category_not_found(self, test_db):
        """Test error when category doesn't exist."""
        with pytest.raises(ValueError, match="not found"):
            material_hierarchy_service.rename_item(
                item_type="category", item_id=99999, new_name="Test", session=test_db
            )

    def test_rename_subcategory_not_found(self, test_db):
        """Test error when subcategory doesn't exist."""
        with pytest.raises(ValueError, match="not found"):
            material_hierarchy_service.rename_item(
                item_type="subcategory", item_id=99999, new_name="Test", session=test_db
            )

    def test_rename_material_duplicate_in_subcategory(self, test_db):
        """Test error when renaming to existing material name in same subcategory."""
        satin = test_db.query(MaterialSubcategory).filter(MaterialSubcategory.slug == "satin").first()
        materials = test_db.query(Material).filter(Material.subcategory_id == satin.id).all()

        if len(materials) >= 2:
            with pytest.raises(ValueError, match="already exists"):
                material_hierarchy_service.rename_item(
                    item_type="material",
                    item_id=materials[0].id,
                    new_name=materials[1].name,
                    session=test_db,
                )

    def test_rename_item_trims_whitespace(self, test_db):
        """Test that whitespace is trimmed on rename."""
        mat = test_db.query(Material).first()

        result = material_hierarchy_service.rename_item(
            item_type="material",
            item_id=mat.id,
            new_name="  Trimmed Name  ",
            session=test_db,
        )

        assert result["name"] == "Trimmed Name"

    def test_rename_same_name_succeeds(self, test_db):
        """Test that renaming to same name succeeds."""
        mat = test_db.query(Material).first()
        original_name = mat.name

        result = material_hierarchy_service.rename_item(
            item_type="material", item_id=mat.id, new_name=original_name, session=test_db
        )

        assert result["name"] == original_name


class TestReparentMaterial:
    """Tests for reparent_material() (Feature 052)."""

    def test_reparent_material_success(self, test_db):
        """Test moving material to different subcategory."""
        red_satin = test_db.query(Material).filter(Material.slug == "red-satin-1-inch").first()
        satin = test_db.query(MaterialSubcategory).filter(MaterialSubcategory.slug == "satin").first()
        grosgrain = (
            test_db.query(MaterialSubcategory).filter(MaterialSubcategory.slug == "grosgrain").first()
        )

        # Verify it's currently under satin
        assert red_satin.subcategory_id == satin.id

        result = material_hierarchy_service.reparent_material(
            material_id=red_satin.id, new_subcategory_id=grosgrain.id, session=test_db
        )

        assert result["subcategory_id"] == grosgrain.id

    def test_reparent_material_to_same_subcategory_fails(self, test_db):
        """Test that moving to same subcategory fails."""
        red_satin = test_db.query(Material).filter(Material.slug == "red-satin-1-inch").first()

        with pytest.raises(ValueError, match="already under"):
            material_hierarchy_service.reparent_material(
                material_id=red_satin.id,
                new_subcategory_id=red_satin.subcategory_id,
                session=test_db,
            )

    def test_reparent_material_duplicate_name_fails(self, test_db):
        """Test that duplicate name in new subcategory fails."""
        satin = test_db.query(MaterialSubcategory).filter(MaterialSubcategory.slug == "satin").first()
        grosgrain = (
            test_db.query(MaterialSubcategory).filter(MaterialSubcategory.slug == "grosgrain").first()
        )
        red_satin = test_db.query(Material).filter(Material.slug == "red-satin-1-inch").first()

        # Create material with same name under target subcategory
        duplicate = Material(
            name=red_satin.name,
            slug="dup-red-satin",
            subcategory_id=grosgrain.id,
            base_unit_type="linear_inches",
        )
        test_db.add(duplicate)
        test_db.flush()

        with pytest.raises(ValueError, match="already exists"):
            material_hierarchy_service.reparent_material(
                material_id=red_satin.id, new_subcategory_id=grosgrain.id, session=test_db
            )

    def test_reparent_material_not_found(self, test_db):
        """Test error when material doesn't exist."""
        grosgrain = (
            test_db.query(MaterialSubcategory).filter(MaterialSubcategory.slug == "grosgrain").first()
        )

        with pytest.raises(ValueError, match="not found"):
            material_hierarchy_service.reparent_material(
                material_id=99999, new_subcategory_id=grosgrain.id, session=test_db
            )

    def test_reparent_material_subcategory_not_found(self, test_db):
        """Test error when new subcategory doesn't exist."""
        red_satin = test_db.query(Material).filter(Material.slug == "red-satin-1-inch").first()

        with pytest.raises(ValueError, match="not found"):
            material_hierarchy_service.reparent_material(
                material_id=red_satin.id, new_subcategory_id=99999, session=test_db
            )

    def test_reparent_material_cross_category(self, test_db):
        """Test moving material to subcategory in different category."""
        red_satin = test_db.query(Material).filter(Material.slug == "red-satin-1-inch").first()
        window_boxes = (
            test_db.query(MaterialSubcategory).filter(MaterialSubcategory.slug == "window-boxes").first()
        )

        result = material_hierarchy_service.reparent_material(
            material_id=red_satin.id, new_subcategory_id=window_boxes.id, session=test_db
        )

        assert result["subcategory_id"] == window_boxes.id


class TestReparentSubcategory:
    """Tests for reparent_subcategory() (Feature 052)."""

    def test_reparent_subcategory_success(self, test_db):
        """Test moving subcategory to different category."""
        satin = test_db.query(MaterialSubcategory).filter(MaterialSubcategory.slug == "satin").first()
        ribbons = test_db.query(MaterialCategory).filter(MaterialCategory.slug == "ribbons").first()
        boxes = test_db.query(MaterialCategory).filter(MaterialCategory.slug == "boxes").first()

        # Verify it's currently under ribbons
        assert satin.category_id == ribbons.id

        result = material_hierarchy_service.reparent_subcategory(
            subcategory_id=satin.id, new_category_id=boxes.id, session=test_db
        )

        assert result["category_id"] == boxes.id

    def test_reparent_subcategory_to_same_category_fails(self, test_db):
        """Test that moving to same category fails."""
        satin = test_db.query(MaterialSubcategory).filter(MaterialSubcategory.slug == "satin").first()

        with pytest.raises(ValueError, match="already under"):
            material_hierarchy_service.reparent_subcategory(
                subcategory_id=satin.id, new_category_id=satin.category_id, session=test_db
            )

    def test_reparent_subcategory_duplicate_name_fails(self, test_db):
        """Test that duplicate name in new category fails."""
        satin = test_db.query(MaterialSubcategory).filter(MaterialSubcategory.slug == "satin").first()
        boxes = test_db.query(MaterialCategory).filter(MaterialCategory.slug == "boxes").first()

        # Create subcategory with same name under target category
        duplicate = MaterialSubcategory(
            name=satin.name,
            slug="dup-satin",
            category_id=boxes.id,
            sort_order=99,
        )
        test_db.add(duplicate)
        test_db.flush()

        with pytest.raises(ValueError, match="already exists"):
            material_hierarchy_service.reparent_subcategory(
                subcategory_id=satin.id, new_category_id=boxes.id, session=test_db
            )

    def test_reparent_subcategory_not_found(self, test_db):
        """Test error when subcategory doesn't exist."""
        boxes = test_db.query(MaterialCategory).filter(MaterialCategory.slug == "boxes").first()

        with pytest.raises(ValueError, match="not found"):
            material_hierarchy_service.reparent_subcategory(
                subcategory_id=99999, new_category_id=boxes.id, session=test_db
            )

    def test_reparent_subcategory_category_not_found(self, test_db):
        """Test error when new category doesn't exist."""
        satin = test_db.query(MaterialSubcategory).filter(MaterialSubcategory.slug == "satin").first()

        with pytest.raises(ValueError, match="not found"):
            material_hierarchy_service.reparent_subcategory(
                subcategory_id=satin.id, new_category_id=99999, session=test_db
            )
