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
    assign_package_to_recipient,
)
from src.services.composition_service import (
    add_packaging_to_assembly,
    add_packaging_to_package,
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
    Composition,
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
            "name": "Cellophane Bags 4x6",
            "category": "Bags",
            "recipe_unit": "each",
            "is_packaging": True,
        })

        box_ingredient = create_ingredient({
            "name": "Gift Box Medium",
            "category": "Boxes",
            "recipe_unit": "each",
            "is_packaging": True,
        })

        ribbon_ingredient = create_ingredient({
            "name": "Satin Ribbon",
            "category": "Ribbon",
            "recipe_unit": "each",
            "is_packaging": True,
        })

        # Create packaging products
        bag_product = create_product(
            bag_ingredient.slug,
            {
                "brand": "ClearBags",
                "package_size": "100 ct",
                "purchase_unit": "box",
                "purchase_quantity": 100,
            }
        )

        box_product = create_product(
            box_ingredient.slug,
            {
                "brand": "Nashville Wraps",
                "package_size": "12 ct",
                "purchase_unit": "each",
                "purchase_quantity": 12,
            }
        )

        ribbon_product = create_product(
            ribbon_ingredient.slug,
            {
                "brand": "Offray",
                "package_size": "10 yard spool",
                "purchase_unit": "each",
                "purchase_quantity": 1,
            }
        )

        # 2. Create a FinishedGood (Cookie Dozen)
        cookie_fg = FinishedGood(
            slug="chocolate-chip-dozen",
            display_name="Chocolate Chip Cookie Dozen",
            description="12 delicious cookies",
            assembly_type=AssemblyType.CUSTOM_ORDER,
            inventory_count=0,
        )
        test_db.add(cookie_fg)
        test_db.flush()

        # Add packaging to the FinishedGood (each dozen needs 1 bag)
        add_packaging_to_assembly(
            assembly_id=cookie_fg.id,
            packaging_product_id=bag_product.id,
            quantity=1.0,
        )

        # 3. Create a Package (Holiday Gift Box)
        gift_package = Package(
            name="Holiday Cookie Box",
            description="A festive gift box of cookies",
        )
        test_db.add(gift_package)
        test_db.flush()

        # Add package-level packaging (box and ribbon)
        add_packaging_to_package(
            package_id=gift_package.id,
            packaging_product_id=box_product.id,
            quantity=1.0,
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
            year=2024,
        )

        recipient = Recipient(
            name="Test Family",
        )
        test_db.add(recipient)
        test_db.flush()

        # Assign 3 packages to recipient
        assign_package_to_recipient(
            event_id=event.id,
            recipient_id=recipient.id,
            package_id=gift_package.id,
            quantity=3,
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
            quantity=4.0,
        )
        test_db.add(bag_inv)

        # Add 5 boxes to inventory (need 3, so to_buy should be 0)
        box_inv = InventoryItem(
            product_id=box_product.id,
            quantity=5.0,
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
            description="No packaging needed",
        )
        test_db.add(package)
        test_db.flush()

        # Create event and recipient
        event = create_event(
            name="Simple Event",
            event_date=date(2024, 12, 1),
            year=2024,
        )

        recipient = Recipient(
            name="Test Person",
        )
        test_db.add(recipient)
        test_db.flush()

        # Assign package
        assign_package_to_recipient(
            event_id=event.id,
            recipient_id=recipient.id,
            package_id=package.id,
            quantity=1,
        )

        # Get shopping list
        result = get_shopping_list(event.id)

        # No packaging section should be present
        assert "packaging" not in result

    def test_packaging_aggregates_across_multiple_recipients(self, test_db):
        """Packaging needs aggregate correctly across multiple recipients."""
        # Create packaging
        bag_ingredient = create_ingredient({
            "name": "Test Bags",
            "category": "Bags",
            "recipe_unit": "each",
            "is_packaging": True,
        })
        bag_product = create_product(
            bag_ingredient.slug,
            {
                "brand": "TestBrand",
                "package_size": "50 ct",
                "purchase_unit": "box",
                "purchase_quantity": 50,
            }
        )

        # Create package with packaging
        package = Package(
            name="Test Package",
            description="Test package",
        )
        test_db.add(package)
        test_db.flush()

        add_packaging_to_package(
            package_id=package.id,
            packaging_product_id=bag_product.id,
            quantity=2.0,
        )

        # Create event
        event = create_event(
            name="Multi-Recipient Event",
            event_date=date(2024, 12, 1),
            year=2024,
        )

        # Create multiple recipients
        for i in range(3):
            recipient = Recipient(
                name=f"Recipient {i+1}",
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
        assert bag_product.id in needs
        assert needs[bag_product.id].total_needed == 12.0
