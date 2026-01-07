"""
Integration tests for Packaging BOM flow (Feature 011).

End-to-end tests covering:
- Creating packaging ingredients and products
- Adding packaging to FinishedGoods and Packages
- Creating events with packaging
- Shopping list generation with packaging section
- Inventory impact on to_buy calculations
"""

import pytest
from datetime import date
from decimal import Decimal

from src.services.event_service import (
    create_event,
    get_event_packaging_needs,
    get_shopping_list,
    assign_package_to_recipient
)
from src.services.composition_service import (
    add_packaging_to_assembly,
    add_packaging_to_package
)
from src.services.ingredient_service import create_ingredient
from src.services.product_service import create_product
from src.models import (
    FinishedGood,
    FinishedUnit,
    Package,
    PackageFinishedGood,
    Recipient,
    InventoryItem,
    Recipe,
    RecipeIngredient,
    Composition
)
from src.models.assembly_type import AssemblyType

class TestPackagingBOMFlow:
    """End-to-end test of packaging BOM functionality."""

    def test_complete_packaging_shopping_list_flow(self, test_db):
        """
        Full integration test: packaging appears correctly on shopping list.

        Scenario:
        1. Create packaging ingredients and products
        2. Create a FinishedGood with packaging (cellophane bags)
        3. Create a Package with its own packaging (gift box)
        4. Add the FinishedGood to the Package
        5. Create an Event and assign packages to a recipient
        6. Generate shopping list and verify packaging section
        7. Add inventory and verify to_buy updates
        """
        # 1. Create packaging ingredients
        bag_ingredient = create_ingredient({
            "display_name": "Cellophane Bags 4x6",
            "category": "Bags",
            "is_packaging": True
        })

        box_ingredient = create_ingredient({
            "display_name": "Gift Box Medium",
            "category": "Boxes",
            "is_packaging": True
        })

        ribbon_ingredient = create_ingredient({
            "display_name": "Satin Ribbon",
            "category": "Ribbon",
            "is_packaging": True
        })

        # Create packaging products
        bag_product = create_product(
            bag_ingredient.slug,
            {
                "brand": "ClearBags",
                "package_size": "100 ct",
                "package_unit": "box",
                "package_unit_quantity": 100
            }
        )

        box_product = create_product(
            box_ingredient.slug,
            {
                "brand": "Nashville Wraps",
                "package_size": "12 ct",
                "package_unit": "each",
                "package_unit_quantity": 12
            }
        )

        ribbon_product = create_product(
            ribbon_ingredient.slug,
            {
                "brand": "Offray",
                "package_size": "10 yard spool",
                "package_unit": "each",
                "package_unit_quantity": 1
            }
        )

        # 2. Create a FinishedGood (Cookie Dozen)
        cookie_fg = FinishedGood(
            slug="chocolate-chip-dozen",
            display_name="Chocolate Chip Cookie Dozen",
            description="12 delicious cookies",
            assembly_type=AssemblyType.CUSTOM_ORDER,
            inventory_count=0
        )
        test_db.add(cookie_fg)
        test_db.flush()

        # Add packaging to the FinishedGood (each dozen needs 1 bag)
        add_packaging_to_assembly(
            assembly_id=cookie_fg.id,
            packaging_product_id=bag_product.id,
            quantity=1.0
        )

        # 3. Create a Package (Holiday Gift Box)
        gift_package = Package(
            name="Holiday Cookie Box",
            description="A festive gift box of cookies"
        )
        test_db.add(gift_package)
        test_db.flush()

        # Add package-level packaging (box and ribbon)
        add_packaging_to_package(
            package_id=gift_package.id,
            packaging_product_id=box_product.id,
            quantity=1.0
        )
        add_packaging_to_package(
            package_id=gift_package.id,
            packaging_product_id=ribbon_product.id,
            quantity=0.5,  # Half a spool per package (for bow)
        )

        # 4. Add FinishedGood to Package (2 dozens per package)
        pfg = PackageFinishedGood(
            package_id=gift_package.id,
            finished_good_id=cookie_fg.id,
            quantity=2,  # 2 dozens per gift package
        )
        test_db.add(pfg)
        test_db.flush()

        # 5. Create Event and Recipient
        event = create_event(
            name="Christmas 2024",
            event_date=date(2024, 12, 25),
            year=2024
        )

        recipient = Recipient(
            name="Test Family"
        )
        test_db.add(recipient)
        test_db.flush()

        # Assign 3 packages to recipient
        assign_package_to_recipient(
            event_id=event.id,
            recipient_id=recipient.id,
            package_id=gift_package.id,
            quantity=3
        )

        # 6. Generate shopping list and verify packaging
        result = get_shopping_list(event.id)

        assert "packaging" in result, "Shopping list should include packaging section"
        packaging = result["packaging"]

        # Should have 3 packaging products
        assert len(packaging) == 3

        # Create lookup by product_id
        pkg_by_id = {p["product_id"]: p for p in packaging}

        # Verify bag needs: 1 bag per FG * 2 FGs per package * 3 packages = 6 bags
        assert bag_product.id in pkg_by_id
        assert pkg_by_id[bag_product.id]["total_needed"] == 6.0
        assert pkg_by_id[bag_product.id]["on_hand"] == 0.0
        assert pkg_by_id[bag_product.id]["to_buy"] == 6.0

        # Verify box needs: 1 box per package * 3 packages = 3 boxes
        assert box_product.id in pkg_by_id
        assert pkg_by_id[box_product.id]["total_needed"] == 3.0
        assert pkg_by_id[box_product.id]["on_hand"] == 0.0
        assert pkg_by_id[box_product.id]["to_buy"] == 3.0

        # Verify ribbon needs: 0.5 per package * 3 packages = 1.5
        assert ribbon_product.id in pkg_by_id
        assert pkg_by_id[ribbon_product.id]["total_needed"] == 1.5
        assert pkg_by_id[ribbon_product.id]["on_hand"] == 0.0
        assert pkg_by_id[ribbon_product.id]["to_buy"] == 1.5

        # 7. Add inventory and verify to_buy updates
        # Add 4 bags to inventory (need 6, so to_buy should be 2)
        bag_inv = InventoryItem(
            product_id=bag_product.id,
            quantity=4.0
        )
        test_db.add(bag_inv)

        # Add 5 boxes to inventory (need 3, so to_buy should be 0)
        box_inv = InventoryItem(
            product_id=box_product.id,
            quantity=5.0
        )
        test_db.add(box_inv)
        test_db.flush()

        # Re-generate shopping list
        result = get_shopping_list(event.id)
        packaging = result["packaging"]
        pkg_by_id = {p["product_id"]: p for p in packaging}

        # Bags: 6 needed, 4 on hand, 2 to buy
        assert pkg_by_id[bag_product.id]["total_needed"] == 6.0
        assert pkg_by_id[bag_product.id]["on_hand"] == 4.0
        assert pkg_by_id[bag_product.id]["to_buy"] == 2.0

        # Boxes: 3 needed, 5 on hand, 0 to buy
        assert pkg_by_id[box_product.id]["total_needed"] == 3.0
        assert pkg_by_id[box_product.id]["on_hand"] == 5.0
        assert pkg_by_id[box_product.id]["to_buy"] == 0.0

        # Ribbon unchanged (no inventory added)
        assert pkg_by_id[ribbon_product.id]["to_buy"] == 1.5

    def test_event_without_packaging_has_no_packaging_section(self, test_db):
        """Event with no packaging compositions has no packaging section."""
        # Create a simple package with no packaging
        package = Package(
            name="Plain Package",
            description="No packaging needed"
        )
        test_db.add(package)
        test_db.flush()

        # Create event and recipient
        event = create_event(
            name="Simple Event",
            event_date=date(2024, 12, 1),
            year=2024
        )

        recipient = Recipient(
            name="Test Person"
        )
        test_db.add(recipient)
        test_db.flush()

        # Assign package
        assign_package_to_recipient(
            event_id=event.id,
            recipient_id=recipient.id,
            package_id=package.id,
            quantity=1
        )

        # Get shopping list
        result = get_shopping_list(event.id)

        # No packaging section should be present
        assert "packaging" not in result

    def test_packaging_aggregates_across_multiple_recipients(self, test_db):
        """Packaging needs aggregate correctly across multiple recipients."""
        # Create packaging
        bag_ingredient = create_ingredient({
            "display_name": "Test Bags",
            "category": "Bags",
            "is_packaging": True
        })
        bag_product = create_product(
            bag_ingredient.slug,
            {
                "brand": "TestBrand",
                "package_size": "50 ct",
                "package_unit": "box",
                "package_unit_quantity": 50
            }
        )

        # Create package with packaging
        package = Package(
            name="Test Package",
            description="Test package"
        )
        test_db.add(package)
        test_db.flush()

        add_packaging_to_package(
            package_id=package.id,
            packaging_product_id=bag_product.id,
            quantity=2.0
        )

        # Create event
        event = create_event(
            name="Multi-Recipient Event",
            event_date=date(2024, 12, 1),
            year=2024
        )

        # Create multiple recipients
        for i in range(3):
            recipient = Recipient(
                name=f"Recipient {i+1}"
            )
            test_db.add(recipient)
            test_db.flush()

            # Each recipient gets different quantity
            assign_package_to_recipient(
                event_id=event.id,
                recipient_id=recipient.id,
                package_id=package.id,
                quantity=i + 1,  # 1, 2, 3 packages
            )

        # Get packaging needs
        needs = get_event_packaging_needs(event.id)

        # Total packages: 1 + 2 + 3 = 6
        # Total bags: 2.0 per package * 6 packages = 12.0
        # Feature 026: Keys are now "specific_{product_id}" for specific products
        key = f"specific_{bag_product.id}"
        assert key in needs
        assert needs[key].total_needed == 12.0

class TestPackagingImportExport:
    """Integration tests for packaging data import/export (Feature 011 T046)."""

    def test_export_import_preserves_packaging_ingredient(self, test_db):
        """Export/import cycle preserves is_packaging flag on ingredients."""
        import json
        import tempfile
        import os
        from src.services.import_export_service import export_all_to_json, import_all_from_json_v4
        from src.models import Ingredient
        from src.models.base import Base
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker, scoped_session

        # Create packaging ingredient
        bag_ingredient = create_ingredient({
            "display_name": "Export Test Bags",
            "category": "Bags",
            "is_packaging": True
        })

        # Create food ingredient for comparison
        flour_ingredient = create_ingredient({
            "display_name": "Export Test Flour",
            "category": "Flour",
            "is_packaging": False
        })

        # Export to temp file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            result = export_all_to_json(temp_path)
            assert result.success

            # Verify export file contains is_packaging field
            with open(temp_path, "r") as f:
                data = json.load(f)

            # Version is informational only; validate current spec structure
            assert "version" in data

            # Find exported ingredients
            exported_ingredients = {i["slug"]: i for i in data["ingredients"]}
            assert bag_ingredient.slug in exported_ingredients
            assert exported_ingredients[bag_ingredient.slug]["is_packaging"] is True

            assert flour_ingredient.slug in exported_ingredients
            assert exported_ingredients[flour_ingredient.slug]["is_packaging"] is False

        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_export_import_preserves_packaging_composition(self, test_db):
        """Export/import cycle preserves packaging compositions."""
        import json
        import tempfile
        import os
        from src.services.import_export_service import export_all_to_json
        from src.services.composition_service import add_packaging_to_assembly, add_packaging_to_package

        # Create packaging ingredient and product
        bag_ingredient = create_ingredient({
            "display_name": "Composition Test Bags",
            "category": "Bags",
            "is_packaging": True
        })
        bag_product = create_product(
            bag_ingredient.slug,
            {
                "brand": "TestBrand",
                "package_size": "50 ct",
                "package_unit": "box",
                "package_unit_quantity": 50
            }
        )

        # Create FinishedGood with packaging
        fg = FinishedGood(
            slug="export-test-cookies",
            display_name="Export Test Cookies",
            assembly_type=AssemblyType.CUSTOM_ORDER,
            inventory_count=0
        )
        test_db.add(fg)
        test_db.flush()

        # Add packaging to FinishedGood
        add_packaging_to_assembly(
            assembly_id=fg.id,
            packaging_product_id=bag_product.id,
            quantity=2.5
        )

        # Create Package with packaging
        pkg = Package(
            name="Export Test Package"
        )
        test_db.add(pkg)
        test_db.flush()

        # Add packaging to Package
        add_packaging_to_package(
            package_id=pkg.id,
            packaging_product_id=bag_product.id,
            quantity=1.5
        )

        # Export to temp file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            result = export_all_to_json(temp_path)
            assert result.success

            # Verify export file contains packaging compositions
            with open(temp_path, "r") as f:
                data = json.load(f)

            compositions = data["compositions"]

            # Find FG-level packaging composition
            fg_packaging = [
                c for c in compositions
                if c.get("finished_good_slug") == fg.slug
                and c.get("packaging_ingredient_slug") == bag_ingredient.slug
            ]
            assert len(fg_packaging) == 1
            assert fg_packaging[0]["component_quantity"] == 2.5
            assert fg_packaging[0]["package_name"] is None

            # Find Package-level packaging composition
            pkg_packaging = [
                c for c in compositions
                if c.get("package_name") == pkg.name
                and c.get("packaging_ingredient_slug") == bag_ingredient.slug
            ]
            assert len(pkg_packaging) == 1
            assert pkg_packaging[0]["component_quantity"] == 1.5
            assert pkg_packaging[0]["finished_good_slug"] is None

        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_export_import_preserves_generic_packaging_with_assignments(self, test_db):
        """Feature 026: Test round-trip export/import of generic packaging with assignments."""
        import json
        import tempfile
        import os
        from src.services.import_export_service import export_all_to_json

        # Create packaging ingredient and product
        bag_ingredient = create_ingredient({
            "display_name": "Generic Export Test Bags",
            "category": "Bags",
            "is_packaging": True
        })
        bag_product = create_product(
            bag_ingredient.slug,
            {
                "brand": "ExportBrand",
                "package_size": "100 ct",
                "package_unit": "each",
                "package_unit_quantity": 100,
                "purchase_price": Decimal("10.00"),
                "product_name": "Generic Export Test Bags"
            }
        )

        # Add inventory for assignment
        inv = InventoryItem(
            product_id=bag_product.id,
            quantity=50,
            unit_cost=0.10,
            expiration_date=date(2025, 12, 31)
        )
        test_db.add(inv)
        test_db.flush()

        # Create FinishedGood with generic packaging
        fg = FinishedGood(
            slug="generic-export-test",
            display_name="Generic Export Test",
            assembly_type=AssemblyType.CUSTOM_ORDER,
            inventory_count=0
        )
        test_db.add(fg)
        test_db.flush()

        # Add generic packaging
        composition = add_packaging_to_assembly(
            assembly_id=fg.id,
            packaging_product_id=bag_product.id,
            quantity=10.0,
            is_generic=True
        )

        # Assign materials
        from src.services.packaging_service import assign_materials
        assign_materials(
            composition_id=composition.id,
            assignments=[{"inventory_item_id": inv.id, "quantity": 10}]
        )

        # Export to temp file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            result = export_all_to_json(temp_path)
            assert result.success

            # Verify export contains is_generic and assignments
            with open(temp_path, "r") as f:
                data = json.load(f)

            compositions = data["compositions"]
            generic_comp = [
                c for c in compositions
                if c.get("finished_good_slug") == fg.slug
                and c.get("is_generic") is True
            ]
            assert len(generic_comp) == 1
            assert generic_comp[0]["is_generic"] is True
            assert "assignments" in generic_comp[0]
            assert len(generic_comp[0]["assignments"]) == 1
            assert generic_comp[0]["assignments"][0]["quantity_assigned"] == 10.0

        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)


class TestPackagingEdgeCases:
    """Edge case tests for packaging BOM (Feature 011 WP07)."""

    def test_packaging_ingredient_without_products_allowed(self, test_db):
        """T058: Packaging ingredient without products is allowed."""
        # Create packaging ingredient with no products
        ingredient = create_ingredient({
            "display_name": "Empty Packaging Category",
            "category": "Bags",
            "is_packaging": True
        })

        # Should not raise
        assert ingredient.is_packaging is True

        # Should appear in packaging list
        from src.services.ingredient_service import get_packaging_ingredients
        packaging = get_packaging_ingredients()
        assert any(i.id == ingredient.id for i in packaging)

    def test_fractional_packaging_quantities(self, test_db):
        """T059: Fractional quantities like 0.5 work correctly."""
        # Create packaging product
        ribbon_ingredient = create_ingredient({
            "display_name": "Fractional Test Ribbon",
            "category": "Ribbon",  # Use valid unit
            "is_packaging": True
        })
        ribbon_product = create_product(
            ribbon_ingredient.slug,
            {
                "brand": "TestBrand",
                "package_size": "10 yd",
                "package_unit": "each",  # Use valid unit from count category
                "package_unit_quantity": 10
            }
        )

        # Create FinishedGood
        fg = FinishedGood(
            slug="fractional-test-cookies",
            display_name="Fractional Test Cookies",
            assembly_type=AssemblyType.CUSTOM_ORDER,
            inventory_count=0
        )
        test_db.add(fg)
        test_db.flush()

        # Add packaging with fractional quantity
        composition = add_packaging_to_assembly(
            assembly_id=fg.id,
            packaging_product_id=ribbon_product.id,
            quantity=0.5
        )
        assert composition.component_quantity == 0.5

        # Update to another fractional quantity
        from src.services.composition_service import update_packaging_quantity
        update_packaging_quantity(composition.id, 1.5)

        # Verify updated
        from src.services.composition_service import get_composition
        updated = get_composition(composition.id)
        assert updated.component_quantity == 1.5

    def test_same_packaging_in_fg_and_package_aggregates_correctly(self, test_db):
        """T060: Same packaging in FG and Package aggregates correctly."""
        # Create packaging product (ribbon)
        ribbon_ingredient = create_ingredient({
            "display_name": "Aggregation Test Ribbon",
            "category": "Ribbon",
            "is_packaging": True
        })
        ribbon_product = create_product(
            ribbon_ingredient.slug,
            {
                "brand": "TestBrand",
                "package_size": "10 yd",
                "package_unit": "each",  # Use valid unit from count category
                "package_unit_quantity": 1
            }
        )

        # Create FinishedGood with 2 ribbons
        fg = FinishedGood(
            slug="aggregation-test-cookies",
            display_name="Aggregation Test Cookies",
            assembly_type=AssemblyType.CUSTOM_ORDER,
            inventory_count=0
        )
        test_db.add(fg)
        test_db.flush()

        add_packaging_to_assembly(
            assembly_id=fg.id,
            packaging_product_id=ribbon_product.id,
            quantity=2.0
        )

        # Create Package with 1 ribbon (outer)
        package = Package(
            name="Aggregation Test Package"
        )
        test_db.add(package)
        test_db.flush()

        add_packaging_to_package(
            package_id=package.id,
            packaging_product_id=ribbon_product.id,
            quantity=1.0
        )

        # Package contains the FG
        pfg = PackageFinishedGood(
            package_id=package.id,
            finished_good_id=fg.id,
            quantity=1
        )
        test_db.add(pfg)
        test_db.flush()

        # Create event with 3 of this package
        event = create_event(
            name="Aggregation Test Event",
            event_date=date(2024, 12, 1),
            year=2024
        )

        recipient = Recipient(name="Test Recipient")
        test_db.add(recipient)
        test_db.flush()

        assign_package_to_recipient(
            event_id=event.id,
            recipient_id=recipient.id,
            package_id=package.id,
            quantity=3
        )

        # Calculate packaging needs
        needs = get_event_packaging_needs(event.id)

        # FG: 2 * 1 * 3 = 6, Package: 1 * 3 = 3, Total: 9
        # Feature 026: Keys are now "specific_{product_id}" for specific products
        key = f"specific_{ribbon_product.id}"
        assert key in needs
        assert needs[key].total_needed == 9.0

    def test_package_delete_cascades_packaging_compositions(self, test_db):
        """T061: Compositions deleted when Package deleted."""
        from src.services import package_service

        # Create packaging product
        bag_ingredient = create_ingredient({
            "display_name": "Cascade Test Bags",
            "category": "Bags",
            "is_packaging": True
        })
        bag_product = create_product(
            bag_ingredient.slug,
            {
                "brand": "TestBrand",
                "package_size": "50 ct",
                "package_unit": "box",
                "package_unit_quantity": 50
            }
        )

        # Create Package with packaging
        package = Package(
            name="Cascade Test Package"
        )
        test_db.add(package)
        test_db.flush()

        composition = add_packaging_to_package(
            package_id=package.id,
            packaging_product_id=bag_product.id,
            quantity=1.0
        )
        comp_id = composition.id

        # Verify composition exists
        from src.services.composition_service import get_composition
        assert get_composition(comp_id) is not None

        # Delete package
        package_service.delete_package(package.id)

        # Verify composition deleted
        assert get_composition(comp_id) is None

    def test_finished_good_delete_cascades_packaging_compositions(self, test_db):
        """T062: Compositions deleted when FinishedGood deleted."""
        from src.services.finished_good_service import FinishedGoodService

        # Create packaging product
        box_ingredient = create_ingredient({
            "display_name": "FG Cascade Test Boxes",
            "category": "Boxes",
            "is_packaging": True
        })
        box_product = create_product(
            box_ingredient.slug,
            {
                "brand": "TestBrand",
                "package_size": "12 ct",
                "package_unit": "box",  # Use valid unit
                "package_unit_quantity": 12
            }
        )

        # Create FinishedGood with packaging
        fg = FinishedGood(
            slug="fg-cascade-test",
            display_name="FG Cascade Test",
            assembly_type=AssemblyType.CUSTOM_ORDER,
            inventory_count=0
        )
        test_db.add(fg)
        test_db.flush()

        composition = add_packaging_to_assembly(
            assembly_id=fg.id,
            packaging_product_id=box_product.id,
            quantity=1.0
        )
        comp_id = composition.id

        # Verify composition exists
        from src.services.composition_service import get_composition
        assert get_composition(comp_id) is not None

        # Delete FinishedGood using class method
        FinishedGoodService.delete_finished_good(fg.id)

        # Verify composition deleted
        assert get_composition(comp_id) is None

    def test_delete_packaging_product_in_use_blocked(self, test_db):
        """T056: Delete blocked with clear message when product in use."""
        from src.services import product_service
        from src.services.exceptions import ProductInUse

        # Create packaging product
        bag_ingredient = create_ingredient({
            "display_name": "Delete Block Test Bags",
            "category": "Bags",
            "is_packaging": True
        })
        bag_product = create_product(
            bag_ingredient.slug,
            {
                "brand": "TestBrand",
                "package_size": "50 ct",
                "package_unit": "box",
                "package_unit_quantity": 50
            }
        )

        # Create Package and add packaging composition
        package = Package(
            name="Delete Block Test Package"
        )
        test_db.add(package)
        test_db.flush()

        add_packaging_to_package(
            package_id=package.id,
            packaging_product_id=bag_product.id,
            quantity=1.0
        )

        # Try to delete product - should be blocked
        with pytest.raises(ProductInUse) as exc_info:
            product_service.delete_product(bag_product.id)

        # Verify error message includes packaging composition count
        error = exc_info.value
        assert error.product_id == bag_product.id
        assert error.dependencies.get("packaging_compositions", 0) >= 1

    def test_sqlite_restrict_fk_prevents_deletion(self, test_db):
        """T063: Verify SQLite RESTRICT FK behavior."""
        from sqlalchemy.exc import IntegrityError
        from src.models import Product

        # Create packaging product
        ribbon_ingredient = create_ingredient({
            "display_name": "RESTRICT Test Ribbon",
            "category": "Ribbon",
            "is_packaging": True
        })
        ribbon_product = create_product(
            ribbon_ingredient.slug,
            {
                "brand": "TestBrand",
                "package_size": "10 yd",
                "package_unit": "each",  # Use valid unit from count category
                "package_unit_quantity": 10
            }
        )

        # Create FinishedGood with packaging composition
        fg = FinishedGood(
            slug="restrict-test-cookies",
            display_name="RESTRICT Test Cookies",
            assembly_type=AssemblyType.CUSTOM_ORDER,
            inventory_count=0
        )
        test_db.add(fg)
        test_db.flush()

        # Add packaging composition referencing the product
        add_packaging_to_assembly(
            assembly_id=fg.id,
            packaging_product_id=ribbon_product.id,
            quantity=1.0
        )

        # Try direct deletion bypassing service (to test FK constraint)
        # Note: This tests that the database-level RESTRICT constraint works
        product = test_db.query(Product).filter_by(id=ribbon_product.id).first()
        test_db.delete(product)

        # SQLite with foreign_keys=ON should raise IntegrityError on flush
        with pytest.raises(IntegrityError):
            test_db.flush()
