"""
Unit tests for FinishedGoodSnapshot model and service functions.

Feature 064: FinishedGoods Snapshot Architecture - WP03

Tests cover:
- Snapshot creation with various component types
- Recursive snapshot creation for nested FinishedGoods
- Circular reference detection
- Max depth enforcement
- Generic material placeholder handling
- Query functions
- Atomicity on failure
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.models.base import Base
from src.models import (
    FinishedGood,
    FinishedUnit,
    Composition,
    Recipe,
    Material,
    MaterialProduct,
    MaterialCategory,
    MaterialSubcategory,
    MaterialUnit,
    PlanningSnapshot,
    FinishedGoodSnapshot,
    FinishedUnitSnapshot,
    MaterialUnitSnapshot,
    AssemblyType,
)
from src.models.finished_unit import YieldMode
from src.services.finished_good_service import (
    create_finished_good_snapshot,
    get_finished_good_snapshot,
    get_finished_good_snapshots_by_planning_id,
    SnapshotCreationError,
    SnapshotCircularReferenceError,
    MaxDepthExceededError,
    MAX_NESTING_DEPTH,
)
from src.services import database


@pytest.fixture(scope="function")
def db_session():
    """
    Create a test database session.

    This fixture creates an in-memory database for each test,
    ensuring tests are isolated. It also patches the global
    session factory so services use the test database.
    """
    # Create in-memory database
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    # Create session factory with expire_on_commit=False
    Session = sessionmaker(bind=engine, expire_on_commit=False)

    # Patch the global session factory
    original_get_session = database.get_session
    database._session_factory = Session

    def patched_get_session():
        return Session()

    database.get_session = patched_get_session

    # Create a session for the test
    session = Session()

    yield session

    # Cleanup
    session.close()
    database.get_session = original_get_session


@pytest.fixture
def recipe(db_session):
    """Create a basic recipe for testing."""
    recipe = Recipe(
        name="Test Recipe",
        category="Cookies",
        source="Test",
    )
    db_session.add(recipe)
    db_session.flush()
    return recipe


@pytest.fixture
def finished_unit(db_session, recipe):
    """Create a basic FinishedUnit for testing."""
    fu = FinishedUnit(
        slug="test-finished-unit",
        display_name="Test Finished Unit",
        description="A test finished unit",
        recipe_id=recipe.id,
        yield_mode=YieldMode.DISCRETE_COUNT,
        items_per_batch=12,
        item_unit="cookies",
        category="baked",
        inventory_count=10,
    )
    db_session.add(fu)
    db_session.flush()
    return fu


@pytest.fixture
def material_category(db_session):
    """Create a material category for testing."""
    cat = MaterialCategory(name="Packaging", slug="packaging")
    db_session.add(cat)
    db_session.flush()
    return cat


@pytest.fixture
def material_subcategory(db_session, material_category):
    """Create a material subcategory for testing."""
    subcat = MaterialSubcategory(
        name="Ribbons",
        slug="ribbons",
        category_id=material_category.id,
    )
    db_session.add(subcat)
    db_session.flush()
    return subcat


@pytest.fixture
def material(db_session, material_subcategory):
    """Create a material for testing."""
    mat = Material(
        name="Red Ribbon",
        slug="red-ribbon",
        subcategory_id=material_subcategory.id,
        base_unit_type="linear_cm",
    )
    db_session.add(mat)
    db_session.flush()
    return mat


@pytest.fixture
def material_product(db_session, material):
    """Create a material product for testing."""
    product = MaterialProduct(
        material_id=material.id,
        name="Red Ribbon Roll",
        slug="red-ribbon-roll",
        package_quantity=100,
        package_unit="cm",
        quantity_in_base_units=100,
    )
    db_session.add(product)
    db_session.flush()
    return product


@pytest.fixture
def material_unit(db_session, material_product):
    """Create a MaterialUnit for testing."""
    mu = MaterialUnit(
        slug="red-ribbon-6in",
        name="6-inch Red Ribbon",
        description="6 inches of red ribbon",
        material_product_id=material_product.id,
        quantity_per_unit=6.0,
    )
    db_session.add(mu)
    db_session.flush()
    return mu


@pytest.fixture
def planning_snapshot(db_session):
    """Create a planning snapshot for context testing."""
    ps = PlanningSnapshot(notes="Test planning snapshot")
    db_session.add(ps)
    db_session.flush()
    return ps


@pytest.fixture
def simple_finished_good(db_session, finished_unit):
    """Create a simple FinishedGood with one FinishedUnit component."""
    fg = FinishedGood(
        slug="simple-gift-box",
        display_name="Simple Gift Box",
        description="A simple gift box with cookies",
        assembly_type=AssemblyType.BUNDLE,
        inventory_count=5,
    )
    db_session.add(fg)
    db_session.flush()

    # Add FinishedUnit component
    comp = Composition(
        assembly_id=fg.id,
        finished_unit_id=finished_unit.id,
        component_quantity=2,
        component_notes="2 dozen cookies",
        sort_order=1,
    )
    db_session.add(comp)
    db_session.flush()
    return fg


@pytest.fixture
def finished_good_with_material(db_session, finished_unit, material_unit):
    """Create a FinishedGood with both FinishedUnit and MaterialUnit components."""
    fg = FinishedGood(
        slug="decorated-gift-box",
        display_name="Decorated Gift Box",
        description="Gift box with ribbon",
        assembly_type=AssemblyType.BUNDLE,
    )
    db_session.add(fg)
    db_session.flush()

    # Add FinishedUnit component
    comp1 = Composition(
        assembly_id=fg.id,
        finished_unit_id=finished_unit.id,
        component_quantity=1,
        sort_order=1,
    )
    db_session.add(comp1)

    # Add MaterialUnit component
    comp2 = Composition(
        assembly_id=fg.id,
        material_unit_id=material_unit.id,
        component_quantity=2,
        sort_order=2,
    )
    db_session.add(comp2)
    db_session.flush()
    return fg


@pytest.fixture
def base_finished_good(db_session):
    """Create a minimal FinishedGood for model tests."""
    fg = FinishedGood(
        slug="base-fg",
        display_name="Base FG",
        assembly_type=AssemblyType.BUNDLE,
    )
    db_session.add(fg)
    db_session.flush()
    return fg


class TestFinishedGoodSnapshotModel:
    """Tests for the FinishedGoodSnapshot model."""

    def test_model_creation(self, db_session, base_finished_good):
        """Test basic model creation."""
        snapshot = FinishedGoodSnapshot(
            finished_good_id=base_finished_good.id,
            definition_data='{"slug": "test", "display_name": "Test"}',
        )
        db_session.add(snapshot)
        db_session.flush()

        assert snapshot.id is not None
        assert snapshot.finished_good_id == base_finished_good.id
        assert snapshot.is_backfilled is False
        assert snapshot.snapshot_date is not None

    def test_get_definition_data(self, db_session, base_finished_good):
        """Test JSON parsing of definition_data."""
        snapshot = FinishedGoodSnapshot(
            finished_good_id=base_finished_good.id,
            definition_data='{"slug": "test", "display_name": "Test Item", "components": []}',
        )
        db_session.add(snapshot)
        db_session.flush()

        result = snapshot.get_definition_data()
        assert result["slug"] == "test"
        assert result["display_name"] == "Test Item"
        assert result["components"] == []

    def test_get_definition_data_handles_empty(self, db_session, base_finished_good):
        """Test get_definition_data with empty/null data."""
        snapshot = FinishedGoodSnapshot(
            finished_good_id=base_finished_good.id,
            definition_data="",
        )
        result = snapshot.get_definition_data()
        assert result == {}

    def test_get_definition_data_handles_invalid_json(self, db_session, base_finished_good):
        """Test get_definition_data with invalid JSON."""
        snapshot = FinishedGoodSnapshot(
            finished_good_id=base_finished_good.id,
            definition_data="not valid json",
        )
        result = snapshot.get_definition_data()
        assert result == {}


class TestCreateFinishedGoodSnapshot:
    """Tests for create_finished_good_snapshot function."""

    def test_creates_snapshot_basic(self, db_session, simple_finished_good, planning_snapshot):
        """Test basic snapshot creation."""
        result = create_finished_good_snapshot(
            finished_good_id=simple_finished_good.id,
            planning_snapshot_id=planning_snapshot.id,
            session=db_session,
        )

        assert result["id"] is not None
        assert result["finished_good_id"] == simple_finished_good.id
        assert result["planning_snapshot_id"] == planning_snapshot.id
        assert result["is_backfilled"] is False
        assert result["definition_data"]["slug"] == "simple-gift-box"
        assert result["definition_data"]["display_name"] == "Simple Gift Box"

    def test_creates_snapshot_with_finished_unit_components(
        self, db_session, simple_finished_good, planning_snapshot
    ):
        """Snapshot includes FinishedUnit component snapshots."""
        result = create_finished_good_snapshot(
            finished_good_id=simple_finished_good.id,
            planning_snapshot_id=planning_snapshot.id,
            session=db_session,
        )

        components = result["definition_data"]["components"]
        assert len(components) == 1
        assert components[0]["component_type"] == "finished_unit"
        assert components[0]["snapshot_id"] is not None
        assert components[0]["component_name"] == "Test Finished Unit"
        assert components[0]["component_quantity"] == 2

        # Verify FinishedUnitSnapshot was created
        fu_snapshot = (
            db_session.query(FinishedUnitSnapshot)
            .filter_by(id=components[0]["snapshot_id"])
            .first()
        )
        assert fu_snapshot is not None

    def test_creates_snapshot_with_material_unit_components(
        self, db_session, finished_good_with_material, planning_snapshot
    ):
        """Snapshot includes MaterialUnit component snapshots."""
        result = create_finished_good_snapshot(
            finished_good_id=finished_good_with_material.id,
            planning_snapshot_id=planning_snapshot.id,
            session=db_session,
        )

        components = result["definition_data"]["components"]
        assert len(components) == 2

        # Find the material unit component
        mu_component = next(
            (c for c in components if c["component_type"] == "material_unit"), None
        )
        assert mu_component is not None
        assert mu_component["snapshot_id"] is not None
        assert mu_component["component_name"] == "6-inch Red Ribbon"

        # Verify MaterialUnitSnapshot was created
        mu_snapshot = (
            db_session.query(MaterialUnitSnapshot)
            .filter_by(id=mu_component["snapshot_id"])
            .first()
        )
        assert mu_snapshot is not None

    def test_recursively_snapshots_nested_finished_goods(
        self, db_session, simple_finished_good, planning_snapshot
    ):
        """Nested FinishedGood components are snapshotted recursively."""
        # Create a parent FinishedGood containing the simple one
        parent_fg = FinishedGood(
            slug="parent-gift-set",
            display_name="Parent Gift Set",
            assembly_type=AssemblyType.BUNDLE,
        )
        db_session.add(parent_fg)
        db_session.flush()

        comp = Composition(
            assembly_id=parent_fg.id,
            finished_good_id=simple_finished_good.id,
            component_quantity=2,
            sort_order=1,
        )
        db_session.add(comp)
        db_session.flush()

        result = create_finished_good_snapshot(
            finished_good_id=parent_fg.id,
            planning_snapshot_id=planning_snapshot.id,
            session=db_session,
        )

        components = result["definition_data"]["components"]
        assert len(components) == 1
        assert components[0]["component_type"] == "finished_good"
        assert components[0]["snapshot_id"] is not None
        assert components[0]["component_name"] == "Simple Gift Box"

        # Verify the nested FinishedGoodSnapshot was created
        nested_snapshot = (
            db_session.query(FinishedGoodSnapshot)
            .filter_by(id=components[0]["snapshot_id"])
            .first()
        )
        assert nested_snapshot is not None
        nested_data = nested_snapshot.get_definition_data()
        assert nested_data["slug"] == "simple-gift-box"
        # Verify the nested snapshot also captured its components
        assert len(nested_data["components"]) == 1

    def test_detects_circular_reference(self, db_session, planning_snapshot):
        """CircularReferenceError raised for A->B->A pattern."""
        # Create two FinishedGoods that reference each other
        fg_a = FinishedGood(
            slug="fg-a",
            display_name="FG A",
            assembly_type=AssemblyType.BUNDLE,
        )
        fg_b = FinishedGood(
            slug="fg-b",
            display_name="FG B",
            assembly_type=AssemblyType.BUNDLE,
        )
        db_session.add_all([fg_a, fg_b])
        db_session.flush()

        # A contains B
        comp_ab = Composition(
            assembly_id=fg_a.id,
            finished_good_id=fg_b.id,
            component_quantity=1,
            sort_order=1,
        )
        # B contains A (circular!)
        comp_ba = Composition(
            assembly_id=fg_b.id,
            finished_good_id=fg_a.id,
            component_quantity=1,
            sort_order=1,
        )
        db_session.add_all([comp_ab, comp_ba])
        db_session.flush()

        with pytest.raises(SnapshotCircularReferenceError) as exc_info:
            create_finished_good_snapshot(
                finished_good_id=fg_a.id,
                planning_snapshot_id=planning_snapshot.id,
                session=db_session,
            )

        assert exc_info.value.finished_good_id == fg_a.id
        assert fg_a.id in exc_info.value.path

    def test_detects_indirect_circular_reference(self, db_session, planning_snapshot):
        """CircularReferenceError raised for A->B->C->A pattern."""
        # Create three FinishedGoods in a cycle
        fg_a = FinishedGood(
            slug="fg-a",
            display_name="FG A",
            assembly_type=AssemblyType.BUNDLE,
        )
        fg_b = FinishedGood(
            slug="fg-b",
            display_name="FG B",
            assembly_type=AssemblyType.BUNDLE,
        )
        fg_c = FinishedGood(
            slug="fg-c",
            display_name="FG C",
            assembly_type=AssemblyType.BUNDLE,
        )
        db_session.add_all([fg_a, fg_b, fg_c])
        db_session.flush()

        # A -> B -> C -> A
        comp_ab = Composition(
            assembly_id=fg_a.id,
            finished_good_id=fg_b.id,
            component_quantity=1,
        )
        comp_bc = Composition(
            assembly_id=fg_b.id,
            finished_good_id=fg_c.id,
            component_quantity=1,
        )
        comp_ca = Composition(
            assembly_id=fg_c.id,
            finished_good_id=fg_a.id,
            component_quantity=1,
        )
        db_session.add_all([comp_ab, comp_bc, comp_ca])
        db_session.flush()

        with pytest.raises(SnapshotCircularReferenceError) as exc_info:
            create_finished_good_snapshot(
                finished_good_id=fg_a.id,
                planning_snapshot_id=planning_snapshot.id,
                session=db_session,
            )

        assert fg_a.id in exc_info.value.path

    def test_max_depth_exceeded(self, db_session, planning_snapshot):
        """MaxDepthExceededError raised at 11 levels."""
        # Create a chain of 12 nested FinishedGoods (0 through 11)
        fgs = []
        for i in range(12):
            fg = FinishedGood(
                slug=f"fg-level-{i}",
                display_name=f"FG Level {i}",
                assembly_type=AssemblyType.BUNDLE,
            )
            db_session.add(fg)
            fgs.append(fg)
        db_session.flush()

        # Create chain: fg[0] -> fg[1] -> fg[2] -> ... -> fg[11]
        for i in range(11):
            comp = Composition(
                assembly_id=fgs[i].id,
                finished_good_id=fgs[i + 1].id,
                component_quantity=1,
            )
            db_session.add(comp)
        db_session.flush()

        with pytest.raises(MaxDepthExceededError) as exc_info:
            create_finished_good_snapshot(
                finished_good_id=fgs[0].id,
                planning_snapshot_id=planning_snapshot.id,
                session=db_session,
            )

        assert exc_info.value.depth > MAX_NESTING_DEPTH

    def test_handles_material_unit_component(
        self, db_session, material_unit, planning_snapshot
    ):
        """Material unit components create snapshots."""
        fg = FinishedGood(
            slug="fg-with-generic",
            display_name="FG With Generic Material",
            assembly_type=AssemblyType.BUNDLE,
        )
        db_session.add(fg)
        db_session.flush()

        # Add material unit component
        comp = Composition(
            assembly_id=fg.id,
            material_unit_id=material_unit.id,
            component_quantity=1,
            sort_order=1,
        )
        db_session.add(comp)
        db_session.flush()

        result = create_finished_good_snapshot(
            finished_good_id=fg.id,
            planning_snapshot_id=planning_snapshot.id,
            session=db_session,
        )

        components = result["definition_data"]["components"]
        assert len(components) == 1
        assert components[0]["component_type"] == "material_unit"
        assert components[0]["snapshot_id"] is not None
        assert components[0]["is_generic"] is False
        assert components[0]["component_name"] == "6-inch Red Ribbon"

    def test_raises_error_for_nonexistent_finished_good(
        self, db_session, planning_snapshot
    ):
        """SnapshotCreationError raised if FinishedGood not found."""
        with pytest.raises(SnapshotCreationError) as exc_info:
            create_finished_good_snapshot(
                finished_good_id=99999,
                planning_snapshot_id=planning_snapshot.id,
                session=db_session,
            )

        assert "not found" in str(exc_info.value)

    def test_components_sorted_by_sort_order(self, db_session, finished_unit, planning_snapshot):
        """Components in definition_data are sorted by sort_order."""
        # Create a second FinishedUnit
        fu2 = FinishedUnit(
            slug="second-unit",
            display_name="Second Unit",
            recipe_id=finished_unit.recipe_id,
            yield_mode=YieldMode.DISCRETE_COUNT,
            items_per_batch=6,
            item_unit="pieces",
        )
        db_session.add(fu2)
        db_session.flush()

        fg = FinishedGood(
            slug="sorted-fg",
            display_name="Sorted FG",
            assembly_type=AssemblyType.BUNDLE,
        )
        db_session.add(fg)
        db_session.flush()

        # Add components in reverse sort order
        comp1 = Composition(
            assembly_id=fg.id,
            finished_unit_id=fu2.id,
            component_quantity=1,
            sort_order=2,
        )
        comp2 = Composition(
            assembly_id=fg.id,
            finished_unit_id=finished_unit.id,
            component_quantity=1,
            sort_order=1,
        )
        db_session.add_all([comp1, comp2])
        db_session.flush()

        result = create_finished_good_snapshot(
            finished_good_id=fg.id,
            planning_snapshot_id=planning_snapshot.id,
            session=db_session,
        )

        components = result["definition_data"]["components"]
        assert components[0]["sort_order"] == 1
        assert components[0]["component_name"] == "Test Finished Unit"
        assert components[1]["sort_order"] == 2
        assert components[1]["component_name"] == "Second Unit"


class TestGetFinishedGoodSnapshot:
    """Tests for get_finished_good_snapshot function."""

    def test_returns_snapshot_by_id(self, db_session, simple_finished_good, planning_snapshot):
        """Get snapshot returns correct data."""
        created = create_finished_good_snapshot(
            finished_good_id=simple_finished_good.id,
            planning_snapshot_id=planning_snapshot.id,
            session=db_session,
        )

        result = get_finished_good_snapshot(created["id"], session=db_session)

        assert result is not None
        assert result["id"] == created["id"]
        assert result["finished_good_id"] == simple_finished_good.id
        assert result["definition_data"]["slug"] == "simple-gift-box"

    def test_returns_none_for_nonexistent_id(self, db_session):
        """Returns None if snapshot not found."""
        result = get_finished_good_snapshot(99999, session=db_session)
        assert result is None


class TestGetFinishedGoodSnapshotsByPlanningId:
    """Tests for get_finished_good_snapshots_by_planning_id function."""

    def test_returns_all_snapshots_for_planning_id(
        self, db_session, simple_finished_good, finished_good_with_material, planning_snapshot
    ):
        """Returns all snapshots associated with a planning snapshot."""
        create_finished_good_snapshot(
            finished_good_id=simple_finished_good.id,
            planning_snapshot_id=planning_snapshot.id,
            session=db_session,
        )
        create_finished_good_snapshot(
            finished_good_id=finished_good_with_material.id,
            planning_snapshot_id=planning_snapshot.id,
            session=db_session,
        )

        results = get_finished_good_snapshots_by_planning_id(
            planning_snapshot.id, session=db_session
        )

        assert len(results) == 2
        slugs = [r["definition_data"]["slug"] for r in results]
        assert "simple-gift-box" in slugs
        assert "decorated-gift-box" in slugs

    def test_returns_empty_list_for_no_snapshots(self, db_session, planning_snapshot):
        """Returns empty list if no snapshots for planning ID."""
        results = get_finished_good_snapshots_by_planning_id(
            planning_snapshot.id, session=db_session
        )
        assert results == []


class TestSnapshotAtomicity:
    """Tests for transaction atomicity during snapshot creation."""

    def test_all_related_snapshots_created_in_same_transaction(
        self, db_session, finished_good_with_material, planning_snapshot
    ):
        """All component snapshots created atomically."""
        result = create_finished_good_snapshot(
            finished_good_id=finished_good_with_material.id,
            planning_snapshot_id=planning_snapshot.id,
            session=db_session,
        )

        # Count all snapshots created
        fg_count = db_session.query(FinishedGoodSnapshot).count()
        fu_count = db_session.query(FinishedUnitSnapshot).count()
        mu_count = db_session.query(MaterialUnitSnapshot).count()

        assert fg_count == 1
        assert fu_count == 1
        assert mu_count == 1

        # All should have same planning_snapshot_id
        fg_snapshots = db_session.query(FinishedGoodSnapshot).all()
        fu_snapshots = db_session.query(FinishedUnitSnapshot).all()
        mu_snapshots = db_session.query(MaterialUnitSnapshot).all()

        for s in fg_snapshots + fu_snapshots + mu_snapshots:
            assert s.planning_snapshot_id == planning_snapshot.id
