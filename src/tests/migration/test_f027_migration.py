"""
Tests for F027 migration transformation logic.

These tests verify the migration script's transformation functions work correctly
without actually modifying any database.
"""

import pytest
from datetime import datetime
from decimal import Decimal
import copy
import sys
from pathlib import Path

# Add scripts directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "scripts"))

from migrate_f027 import (
    create_unknown_supplier,
    transform_inventory_to_purchases,
    link_items_to_purchases,
    initialize_product_fields,
    validate_transformation,
)


class MockArgs:
    """Mock args object for testing."""

    def __init__(self, skip_validation=False):
        self.skip_validation = skip_validation
        self.dry_run = True
        self.backup_dir = "backups"
        self.db_path = "data/bake_tracker.db"
        self.output_json = None


class TestCreateUnknownSupplier:
    """Tests for create_unknown_supplier function."""

    def test_unknown_supplier_created(self):
        """Unknown supplier is created with required fields."""
        data = {}
        result_data, supplier_id = create_unknown_supplier(data)

        assert "suppliers" in result_data
        assert len(result_data["suppliers"]) == 1

        supplier = result_data["suppliers"][0]
        assert supplier["id"] == 1
        assert supplier["name"] == "Unknown"
        assert supplier["state"] == "XX"  # Intentionally invalid
        assert supplier["is_active"] is True

    def test_unknown_supplier_reserves_id_1(self):
        """Unknown supplier uses reserved ID 1."""
        data = {}
        result_data, supplier_id = create_unknown_supplier(data)

        assert supplier_id == 1
        assert result_data["suppliers"][0]["id"] == 1

    def test_unknown_supplier_has_special_uuid(self):
        """Unknown supplier has the reserved UUID."""
        data = {}
        result_data, _ = create_unknown_supplier(data)

        supplier = result_data["suppliers"][0]
        assert supplier["uuid"] == "00000000-0000-0000-0000-000000000001"

    def test_existing_suppliers_preserved(self):
        """Existing suppliers are preserved when adding Unknown."""
        data = {
            "suppliers": [
                {"id": 2, "name": "Costco", "state": "WA"},
                {"id": 3, "name": "Amazon", "state": "WA"},
            ]
        }
        result_data, _ = create_unknown_supplier(data)

        assert len(result_data["suppliers"]) == 3
        # Unknown is inserted at front
        assert result_data["suppliers"][0]["name"] == "Unknown"
        assert result_data["suppliers"][1]["name"] == "Costco"
        assert result_data["suppliers"][2]["name"] == "Amazon"

    def test_unknown_supplier_skipped_if_exists(self):
        """Unknown supplier creation is skipped if one already exists."""
        existing_unknown = {
            "id": 99,
            "name": "Unknown",
            "state": "XX",
        }
        data = {"suppliers": [existing_unknown]}
        result_data, supplier_id = create_unknown_supplier(data)

        # Should return existing ID, not create new
        assert supplier_id == 99
        assert len(result_data["suppliers"]) == 1


class TestTransformInventoryToPurchases:
    """Tests for transform_inventory_to_purchases function."""

    def test_inventory_item_with_cost_creates_purchase(self):
        """Inventory item with unit_cost creates a Purchase record."""
        data = {
            "inventory_items": [
                {
                    "id": 1,
                    "product_id": 10,
                    "unit_cost": "5.99",
                    "purchase_date": "2025-01-15",
                }
            ],
            "purchases": [],
        }
        result_data, new_purchases = transform_inventory_to_purchases(data, unknown_supplier_id=1)

        assert len(new_purchases) == 1
        assert new_purchases[0]["product_id"] == 10
        assert new_purchases[0]["unit_price"] == "5.99"
        assert new_purchases[0]["supplier_id"] == 1  # Unknown supplier
        assert new_purchases[0]["quantity_purchased"] == 1

    def test_inventory_item_without_cost_skipped(self):
        """Inventory item without unit_cost doesn't create Purchase."""
        data = {
            "inventory_items": [
                {"id": 1, "product_id": 10, "unit_cost": None, "purchase_date": "2025-01-15"},
                {"id": 2, "product_id": 11, "unit_cost": "3.50", "purchase_date": "2025-01-16"},
            ],
            "purchases": [],
        }
        result_data, new_purchases = transform_inventory_to_purchases(data, unknown_supplier_id=1)

        # Only item 2 has unit_cost, so only 1 purchase
        assert len(new_purchases) == 1
        assert new_purchases[0]["product_id"] == 11

    def test_multiple_items_create_multiple_purchases(self):
        """Each inventory item with cost gets its own Purchase."""
        data = {
            "inventory_items": [
                {"id": 1, "product_id": 10, "unit_cost": "5.99", "purchase_date": "2025-01-15"},
                {"id": 2, "product_id": 11, "unit_cost": "3.50", "purchase_date": "2025-01-16"},
                {"id": 3, "product_id": 12, "unit_cost": "7.25", "purchase_date": "2025-01-17"},
            ],
            "purchases": [],
        }
        result_data, new_purchases = transform_inventory_to_purchases(data, unknown_supplier_id=1)

        assert len(new_purchases) == 3
        # Verify sequential IDs
        assert new_purchases[0]["id"] == 1
        assert new_purchases[1]["id"] == 2
        assert new_purchases[2]["id"] == 3

    def test_existing_purchases_preserved(self):
        """Existing purchases are preserved with new ones added after."""
        data = {
            "inventory_items": [
                {"id": 1, "product_id": 10, "unit_cost": "5.99", "purchase_date": "2025-01-15"},
            ],
            "purchases": [
                {"id": 1, "product_id": 5, "unit_price": "2.99"},
                {"id": 2, "product_id": 6, "unit_price": "4.99"},
            ],
        }
        result_data, new_purchases = transform_inventory_to_purchases(data, unknown_supplier_id=1)

        # New purchase should have ID 3 (after existing 1, 2)
        assert len(new_purchases) == 1
        assert new_purchases[0]["id"] == 3
        # Total purchases should be 3
        assert len(result_data["purchases"]) == 3

    def test_negative_cost_handled_with_zero(self):
        """Negative unit_cost is logged and converted to 0.00."""
        data = {
            "inventory_items": [
                {"id": 1, "product_id": 10, "unit_cost": "-5.99", "purchase_date": "2025-01-15"},
            ],
            "purchases": [],
        }
        result_data, new_purchases = transform_inventory_to_purchases(data, unknown_supplier_id=1)

        assert len(new_purchases) == 1
        assert new_purchases[0]["unit_price"] == "0.00"

    def test_zero_cost_allowed(self):
        """Zero unit_cost is valid (could be a gift/sample)."""
        data = {
            "inventory_items": [
                {"id": 1, "product_id": 10, "unit_cost": "0.00", "purchase_date": "2025-01-15"},
            ],
            "purchases": [],
        }
        result_data, new_purchases = transform_inventory_to_purchases(data, unknown_supplier_id=1)

        assert len(new_purchases) == 1
        assert new_purchases[0]["unit_price"] == "0.00"

    def test_purchase_notes_contain_source_reference(self):
        """Purchase notes contain reference to source inventory item."""
        data = {
            "inventory_items": [
                {"id": 42, "product_id": 10, "unit_cost": "5.99", "purchase_date": "2025-01-15"},
            ],
            "purchases": [],
        }
        result_data, new_purchases = transform_inventory_to_purchases(data, unknown_supplier_id=1)

        assert "inventory_item 42" in new_purchases[0]["notes"]
        assert "F027 migration" in new_purchases[0]["notes"]


class TestLinkItemsToPurchases:
    """Tests for link_items_to_purchases function."""

    def test_items_linked_to_purchases(self):
        """Inventory items get purchase_id set from new purchases."""
        new_purchases = [
            {
                "id": 5,
                "product_id": 10,
                "notes": "Migrated from inventory_item 1 during F027 migration",
            },
            {
                "id": 6,
                "product_id": 11,
                "notes": "Migrated from inventory_item 2 during F027 migration",
            },
        ]
        data = {
            "inventory_items": [
                {"id": 1, "product_id": 10, "purchase_id": None},
                {"id": 2, "product_id": 11, "purchase_id": None},
            ]
        }

        result_data = link_items_to_purchases(data, new_purchases)

        assert result_data["inventory_items"][0]["purchase_id"] == 5
        assert result_data["inventory_items"][1]["purchase_id"] == 6

    def test_items_without_purchases_stay_null(self):
        """Items without corresponding purchases keep purchase_id as None."""
        new_purchases = [
            {
                "id": 5,
                "product_id": 10,
                "notes": "Migrated from inventory_item 1 during F027 migration",
            },
        ]
        data = {
            "inventory_items": [
                {"id": 1, "product_id": 10, "purchase_id": None},
                {"id": 2, "product_id": 11, "purchase_id": None},  # No matching purchase
            ]
        }

        result_data = link_items_to_purchases(data, new_purchases)

        assert result_data["inventory_items"][0]["purchase_id"] == 5
        assert result_data["inventory_items"][1]["purchase_id"] is None

    def test_already_linked_items_preserved(self):
        """Items that already have purchase_id are not modified."""
        new_purchases = [
            {
                "id": 99,
                "product_id": 10,
                "notes": "Migrated from inventory_item 1 during F027 migration",
            },
        ]
        data = {
            "inventory_items": [
                {"id": 1, "product_id": 10, "purchase_id": 50},  # Already linked
            ]
        }

        result_data = link_items_to_purchases(data, new_purchases)

        # Should keep original purchase_id, not overwrite
        assert result_data["inventory_items"][0]["purchase_id"] == 50


class TestInitializeProductFields:
    """Tests for initialize_product_fields function."""

    def test_products_get_is_hidden_false(self):
        """All products get is_hidden=False."""
        data = {
            "products": [
                {"id": 1, "product_name": "Butter"},
                {"id": 2, "product_name": "Sugar"},
            ]
        }

        result_data = initialize_product_fields(data)

        assert result_data["products"][0]["is_hidden"] is False
        assert result_data["products"][1]["is_hidden"] is False

    def test_products_get_preferred_supplier_none(self):
        """All products get preferred_supplier_id=None."""
        data = {
            "products": [
                {"id": 1, "product_name": "Butter"},
            ]
        }

        result_data = initialize_product_fields(data)

        assert result_data["products"][0]["preferred_supplier_id"] is None

    def test_existing_is_hidden_preserved(self):
        """If is_hidden already exists, it's preserved."""
        data = {
            "products": [
                {"id": 1, "product_name": "Old Product", "is_hidden": True},
            ]
        }

        result_data = initialize_product_fields(data)

        # Should preserve existing True value
        assert result_data["products"][0]["is_hidden"] is True

    def test_empty_products_handled(self):
        """Empty products list doesn't cause errors."""
        data = {"products": []}

        result_data = initialize_product_fields(data)

        assert result_data["products"] == []


class TestValidateTransformation:
    """Tests for validate_transformation function."""

    def test_validation_passes_for_correct_transformation(self):
        """Validation passes when all checks are satisfied."""
        original = {
            "products": [{"id": 1}],
            "inventory_items": [{"id": 1}],
            "ingredients": [{"id": 1}],
            "suppliers": [],
            "purchases": [],
        }
        transformed = {
            "products": [{"id": 1, "is_hidden": False}],
            "inventory_items": [{"id": 1, "purchase_id": 1}],
            "ingredients": [{"id": 1}],
            "suppliers": [{"id": 1, "name": "Unknown"}],
            "purchases": [{"id": 1, "product_id": 1, "supplier_id": 1}],
        }

        args = MockArgs()
        result = validate_transformation(original, transformed, args)

        assert result is True

    def test_validation_fails_product_count_mismatch(self):
        """Validation fails if product count changes."""
        original = {
            "products": [{"id": 1}, {"id": 2}],
            "inventory_items": [],
            "ingredients": [],
            "suppliers": [],
            "purchases": [],
        }
        transformed = {
            "products": [{"id": 1, "is_hidden": False}],  # Missing one!
            "inventory_items": [],
            "ingredients": [],
            "suppliers": [],
            "purchases": [],
        }

        args = MockArgs()
        result = validate_transformation(original, transformed, args)

        assert result is False

    def test_validation_fails_invalid_purchase_product_fk(self):
        """Validation fails if purchase references nonexistent product."""
        original = {
            "products": [{"id": 1}],
            "inventory_items": [],
            "ingredients": [],
            "suppliers": [],
            "purchases": [],
        }
        transformed = {
            "products": [{"id": 1, "is_hidden": False}],
            "inventory_items": [],
            "ingredients": [],
            "suppliers": [{"id": 1}],
            "purchases": [{"id": 1, "product_id": 999, "supplier_id": 1}],  # Invalid product!
        }

        args = MockArgs()
        result = validate_transformation(original, transformed, args)

        assert result is False

    def test_validation_fails_invalid_purchase_supplier_fk(self):
        """Validation fails if purchase references nonexistent supplier."""
        original = {
            "products": [{"id": 1}],
            "inventory_items": [],
            "ingredients": [],
            "suppliers": [],
            "purchases": [],
        }
        transformed = {
            "products": [{"id": 1, "is_hidden": False}],
            "inventory_items": [],
            "ingredients": [],
            "suppliers": [{"id": 1}],
            "purchases": [{"id": 1, "product_id": 1, "supplier_id": 999}],  # Invalid supplier!
        }

        args = MockArgs()
        result = validate_transformation(original, transformed, args)

        assert result is False

    def test_validation_fails_invalid_item_purchase_fk(self):
        """Validation fails if inventory_item references nonexistent purchase."""
        original = {
            "products": [{"id": 1}],
            "inventory_items": [{"id": 1}],
            "ingredients": [],
            "suppliers": [],
            "purchases": [],
        }
        transformed = {
            "products": [{"id": 1, "is_hidden": False}],
            "inventory_items": [{"id": 1, "purchase_id": 999}],  # Invalid purchase!
            "ingredients": [],
            "suppliers": [{"id": 1}],
            "purchases": [{"id": 1, "product_id": 1, "supplier_id": 1}],
        }

        args = MockArgs()
        result = validate_transformation(original, transformed, args)

        assert result is False

    def test_validation_fails_missing_is_hidden(self):
        """Validation fails if product is missing is_hidden field."""
        original = {
            "products": [{"id": 1}],
            "inventory_items": [],
            "ingredients": [],
            "suppliers": [],
            "purchases": [],
        }
        transformed = {
            "products": [{"id": 1}],  # Missing is_hidden!
            "inventory_items": [],
            "ingredients": [],
            "suppliers": [],
            "purchases": [],
        }

        args = MockArgs()
        result = validate_transformation(original, transformed, args)

        assert result is False

    def test_validation_skipped_when_flag_set(self):
        """Validation returns True when skip_validation=True."""
        original = {"products": [{"id": 1}]}
        transformed = {"products": []}  # This would normally fail

        args = MockArgs(skip_validation=True)
        result = validate_transformation(original, transformed, args)

        assert result is True


class TestFullTransformationFlow:
    """Integration tests for the full transformation flow."""

    def test_full_transformation_preserves_data(self):
        """Full transformation preserves all original records."""
        original = {
            "ingredients": [
                {"id": 1, "name": "Butter", "category": "Dairy"},
            ],
            "products": [
                {"id": 10, "product_name": "Costco Butter", "ingredient_id": 1},
                {"id": 11, "product_name": "Store Butter", "ingredient_id": 1},
            ],
            "inventory_items": [
                {"id": 1, "product_id": 10, "unit_cost": "5.99", "purchase_date": "2025-01-15"},
                {"id": 2, "product_id": 11, "unit_cost": None, "purchase_date": "2025-01-16"},
            ],
            "suppliers": [],
            "purchases": [],
        }

        # Apply transformations in order
        data = copy.deepcopy(original)
        data, unknown_id = create_unknown_supplier(data)
        data, new_purchases = transform_inventory_to_purchases(data, unknown_id)
        data = link_items_to_purchases(data, new_purchases)
        data = initialize_product_fields(data)

        # Validate transformation
        args = MockArgs()
        assert validate_transformation(original, data, args) is True

        # Check specific outcomes
        assert len(data["ingredients"]) == 1
        assert len(data["products"]) == 2
        assert len(data["inventory_items"]) == 2
        assert len(data["suppliers"]) == 1
        assert len(data["purchases"]) == 1  # Only 1 item had unit_cost

        # Product fields initialized
        assert all(p["is_hidden"] is False for p in data["products"])
        assert all(p["preferred_supplier_id"] is None for p in data["products"])

        # Item linkage
        assert data["inventory_items"][0]["purchase_id"] is not None
        assert data["inventory_items"][1]["purchase_id"] is None
