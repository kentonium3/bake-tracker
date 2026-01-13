"""
Tests for schema_validation_service.

Tests cover:
- ValidationResult, ValidationError, ValidationWarning dataclasses
- Entity validators (suppliers, ingredients, products, recipes)
- Main dispatcher (validate_import_file)
- Edge cases (empty data, null values, wrong types)
"""

import pytest
from src.services.schema_validation_service import (
    ValidationError,
    ValidationWarning,
    ValidationResult,
    validate_supplier_schema,
    validate_ingredient_schema,
    validate_product_schema,
    validate_recipe_schema,
    validate_import_file,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def valid_supplier_data():
    """Valid supplier import data."""
    return {
        "suppliers": [
            {"name": "Costco", "slug": "costco", "contact_info": "123-456-7890"},
            {"name": "Local Farm", "slug": "local-farm", "notes": "Great produce"},
        ]
    }


@pytest.fixture
def valid_ingredient_data():
    """Valid ingredient import data."""
    return {
        "ingredients": [
            {"display_name": "All-Purpose Flour", "category": "Flour"},
            {
                "display_name": "Sugar",
                "package_unit": "lb",
                "package_unit_quantity": 5.0,
            },
        ]
    }


@pytest.fixture
def valid_product_data():
    """Valid product import data."""
    return {
        "products": [
            {
                "display_name": "King Arthur Flour",
                "ingredient_slug": "all_purpose_flour",
                "brand": "King Arthur",
            },
            {
                "display_name": "Costco Sugar",
                "ingredient_slug": "sugar",
                "supplier_slug": "costco",
                "unit_cost": 5.99,
            },
        ]
    }


@pytest.fixture
def valid_recipe_data():
    """Valid recipe import data."""
    return {
        "recipes": [
            {
                "name": "Chocolate Chip Cookies",
                "category": "Cookies",
                "yield_quantity": 24,
                "yield_unit": "cookies",
                "ingredients": [
                    {"ingredient_name": "All-Purpose Flour", "quantity": 2.25, "unit": "cup"},
                    {"ingredient_slug": "sugar", "quantity": 0.75, "unit": "cup"},
                ],
            }
        ]
    }


@pytest.fixture
def valid_multi_entity_data(valid_supplier_data, valid_ingredient_data, valid_product_data):
    """Valid multi-entity import data."""
    return {
        **valid_supplier_data,
        **valid_ingredient_data,
        **valid_product_data,
        "version": "4.0",
        "export_date": "2026-01-13T10:00:00Z",
    }


# ============================================================================
# ValidationResult Tests
# ============================================================================


class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_valid_result(self):
        """Test creation of valid result."""
        result = ValidationResult(valid=True, errors=[], warnings=[])
        assert result.valid is True
        assert result.error_count == 0
        assert result.warning_count == 0

    def test_invalid_result_with_errors(self):
        """Test result with errors is invalid."""
        error = ValidationError(
            field="test.field",
            message="Test error",
            record_number=1,
            expected="string",
            actual="integer",
        )
        result = ValidationResult(valid=False, errors=[error], warnings=[])
        assert result.valid is False
        assert result.error_count == 1
        assert result.warning_count == 0

    def test_result_with_warnings_only(self):
        """Test result with warnings only is still valid."""
        warning = ValidationWarning(
            field="test.field",
            message="Test warning",
            record_number=1,
        )
        result = ValidationResult(valid=True, errors=[], warnings=[warning])
        assert result.valid is True
        assert result.warning_count == 1

    def test_merge_results(self):
        """Test merging two validation results."""
        error = ValidationError(
            field="a.field", message="Error A", record_number=1
        )
        warning = ValidationWarning(
            field="b.field", message="Warning B", record_number=2
        )

        result1 = ValidationResult(valid=False, errors=[error], warnings=[])
        result2 = ValidationResult(valid=True, errors=[], warnings=[warning])

        merged = result1.merge(result2)

        assert merged.valid is False  # False because result1 was invalid
        assert merged.error_count == 1
        assert merged.warning_count == 1

    def test_merge_both_valid(self):
        """Test merging two valid results stays valid."""
        result1 = ValidationResult(valid=True)
        result2 = ValidationResult(valid=True)

        merged = result1.merge(result2)
        assert merged.valid is True


# ============================================================================
# Supplier Schema Tests
# ============================================================================


class TestSupplierSchema:
    """Tests for validate_supplier_schema()."""

    def test_valid_suppliers(self, valid_supplier_data):
        """Test valid supplier data passes validation."""
        result = validate_supplier_schema(valid_supplier_data)
        assert result.valid is True
        assert result.error_count == 0

    def test_missing_required_name(self):
        """Test missing 'name' field produces error."""
        data = {"suppliers": [{"slug": "test-supplier"}]}
        result = validate_supplier_schema(data)

        assert result.valid is False
        assert result.error_count == 1
        assert "name" in result.errors[0].field
        assert "missing" in result.errors[0].message.lower()

    def test_empty_name(self):
        """Test empty 'name' field produces error."""
        data = {"suppliers": [{"name": ""}]}
        result = validate_supplier_schema(data)

        assert result.valid is False
        assert result.error_count == 1
        assert "non-empty" in result.errors[0].message.lower()

    def test_invalid_slug_format(self):
        """Test invalid slug format produces error."""
        data = {"suppliers": [{"name": "Test", "slug": "Invalid Slug!"}]}
        result = validate_supplier_schema(data)

        assert result.valid is False
        assert result.error_count == 1
        assert "slug" in result.errors[0].field

    def test_valid_slug_formats(self):
        """Test various valid slug formats."""
        valid_slugs = ["costco", "local-farm", "supplier_123", "a-b_c"]
        for slug in valid_slugs:
            data = {"suppliers": [{"name": "Test", "slug": slug}]}
            result = validate_supplier_schema(data)
            assert result.valid is True, f"Slug '{slug}' should be valid"

    def test_wrong_type_for_name(self):
        """Test wrong type for 'name' produces error with expected/actual."""
        data = {"suppliers": [{"name": 123}]}
        result = validate_supplier_schema(data)

        assert result.valid is False
        assert result.errors[0].expected is not None
        assert result.errors[0].actual is not None

    def test_unexpected_field_warning(self):
        """Test unexpected field produces warning, not error."""
        data = {"suppliers": [{"name": "Test", "unknown_field": "value"}]}
        result = validate_supplier_schema(data)

        assert result.valid is True  # Warnings don't fail validation
        assert result.warning_count == 1
        assert "unknown_field" in result.warnings[0].field

    def test_suppliers_not_array(self):
        """Test non-array suppliers field produces error."""
        data = {"suppliers": "not an array"}
        result = validate_supplier_schema(data)

        assert result.valid is False
        assert "array" in result.errors[0].expected

    def test_empty_suppliers_array(self):
        """Test empty suppliers array is valid."""
        data = {"suppliers": []}
        result = validate_supplier_schema(data)
        assert result.valid is True

    def test_no_suppliers_key(self):
        """Test missing suppliers key returns valid (nothing to validate)."""
        data = {"ingredients": []}
        result = validate_supplier_schema(data)
        assert result.valid is True

    def test_null_optional_fields(self):
        """Test null values for optional fields are accepted."""
        data = {"suppliers": [{"name": "Test", "contact_info": None, "notes": None}]}
        result = validate_supplier_schema(data)
        assert result.valid is True


# ============================================================================
# Ingredient Schema Tests
# ============================================================================


class TestIngredientSchema:
    """Tests for validate_ingredient_schema()."""

    def test_valid_ingredients(self, valid_ingredient_data):
        """Test valid ingredient data passes validation."""
        result = validate_ingredient_schema(valid_ingredient_data)
        assert result.valid is True

    def test_missing_display_name(self):
        """Test missing 'display_name' produces error."""
        data = {"ingredients": [{"category": "Flour"}]}
        result = validate_ingredient_schema(data)

        assert result.valid is False
        assert "display_name" in result.errors[0].field

    def test_invalid_package_unit_quantity(self):
        """Test negative package_unit_quantity produces error."""
        data = {
            "ingredients": [
                {"display_name": "Flour", "package_unit_quantity": -1}
            ]
        }
        result = validate_ingredient_schema(data)

        assert result.valid is False
        assert "positive" in result.errors[0].message.lower()

    def test_unknown_package_unit_warning(self):
        """Test unknown package unit produces warning, not error."""
        data = {
            "ingredients": [
                {"display_name": "Flour", "package_unit": "unknown_unit"}
            ]
        }
        result = validate_ingredient_schema(data)

        assert result.valid is True  # Warnings don't fail
        assert result.warning_count == 1

    def test_valid_package_units(self):
        """Test valid package units pass validation."""
        valid_units = ["oz", "lb", "cup", "each", "bag"]
        for unit in valid_units:
            data = {"ingredients": [{"display_name": "Test", "package_unit": unit}]}
            result = validate_ingredient_schema(data)
            assert result.valid is True, f"Unit '{unit}' should be valid"

    def test_record_number_in_errors(self):
        """Test error includes correct record number (1-indexed)."""
        data = {
            "ingredients": [
                {"display_name": "Valid"},
                {"display_name": ""},  # Invalid - empty string
                {"display_name": "Also Valid"},
            ]
        }
        result = validate_ingredient_schema(data)

        assert result.valid is False
        assert result.errors[0].record_number == 2  # Second record, 1-indexed


# ============================================================================
# Product Schema Tests
# ============================================================================


class TestProductSchema:
    """Tests for validate_product_schema()."""

    def test_valid_products(self, valid_product_data):
        """Test valid product data passes validation."""
        result = validate_product_schema(valid_product_data)
        assert result.valid is True

    def test_missing_ingredient_slug(self):
        """Test missing 'ingredient_slug' produces error."""
        data = {"products": [{"display_name": "Test Product"}]}
        result = validate_product_schema(data)

        assert result.valid is False
        assert "ingredient_slug" in result.errors[0].field

    def test_negative_unit_cost(self):
        """Test negative unit_cost produces error."""
        data = {
            "products": [
                {
                    "display_name": "Test",
                    "ingredient_slug": "flour",
                    "unit_cost": -5.99,
                }
            ]
        }
        result = validate_product_schema(data)

        assert result.valid is False
        assert "non-negative" in result.errors[0].message.lower()

    def test_zero_unit_cost_valid(self):
        """Test zero unit_cost is valid (non-negative)."""
        data = {
            "products": [
                {
                    "display_name": "Free Sample",
                    "ingredient_slug": "flour",
                    "unit_cost": 0,
                }
            ]
        }
        result = validate_product_schema(data)
        assert result.valid is True

    def test_multiple_errors_same_record(self):
        """Test multiple errors can be reported for same record."""
        data = {"products": [{"brand": "Test"}]}  # Missing display_name AND ingredient_slug
        result = validate_product_schema(data)

        assert result.valid is False
        assert result.error_count == 2  # Both required fields missing


# ============================================================================
# Recipe Schema Tests
# ============================================================================


class TestRecipeSchema:
    """Tests for validate_recipe_schema()."""

    def test_valid_recipes(self, valid_recipe_data):
        """Test valid recipe data passes validation."""
        result = validate_recipe_schema(valid_recipe_data)
        assert result.valid is True

    def test_missing_name(self):
        """Test missing 'name' produces error."""
        data = {"recipes": [{"category": "Cookies"}]}
        result = validate_recipe_schema(data)

        assert result.valid is False
        assert "name" in result.errors[0].field

    def test_negative_yield_quantity(self):
        """Test negative yield_quantity produces error."""
        data = {"recipes": [{"name": "Cookies", "yield_quantity": -10}]}
        result = validate_recipe_schema(data)

        assert result.valid is False
        assert "positive" in result.errors[0].message.lower()

    def test_recipe_ingredient_missing_identifier(self):
        """Test recipe ingredient without name or slug produces error."""
        data = {
            "recipes": [
                {
                    "name": "Test Recipe",
                    "ingredients": [{"quantity": 1, "unit": "cup"}],
                }
            ]
        }
        result = validate_recipe_schema(data)

        assert result.valid is False
        assert "ingredient_name" in result.errors[0].message

    def test_recipe_ingredient_missing_quantity(self):
        """Test recipe ingredient without quantity produces error."""
        data = {
            "recipes": [
                {
                    "name": "Test Recipe",
                    "ingredients": [{"ingredient_name": "Flour", "unit": "cup"}],
                }
            ]
        }
        result = validate_recipe_schema(data)

        assert result.valid is False
        assert "quantity" in result.errors[0].field

    def test_recipe_ingredient_missing_unit(self):
        """Test recipe ingredient without unit produces error."""
        data = {
            "recipes": [
                {
                    "name": "Test Recipe",
                    "ingredients": [{"ingredient_name": "Flour", "quantity": 2}],
                }
            ]
        }
        result = validate_recipe_schema(data)

        assert result.valid is False
        assert "unit" in result.errors[0].field

    def test_recipe_with_components(self):
        """Test recipe with components (nested recipes) validates."""
        data = {
            "recipes": [
                {
                    "name": "Layer Cake",
                    "components": [
                        {"recipe_name": "Vanilla Cake", "quantity": 2},
                        {"recipe_slug": "cream_cheese_frosting"},
                    ],
                }
            ]
        }
        result = validate_recipe_schema(data)
        assert result.valid is True

    def test_recipe_component_missing_identifier(self):
        """Test recipe component without name or slug produces error."""
        data = {
            "recipes": [
                {"name": "Test Recipe", "components": [{"quantity": 2}]}
            ]
        }
        result = validate_recipe_schema(data)

        assert result.valid is False
        assert "recipe_name" in result.errors[0].message

    def test_recipe_with_both_name_and_slug(self):
        """Test recipe ingredient can have both name and slug."""
        data = {
            "recipes": [
                {
                    "name": "Test Recipe",
                    "ingredients": [
                        {
                            "ingredient_name": "Flour",
                            "ingredient_slug": "flour",
                            "quantity": 2,
                            "unit": "cup",
                        }
                    ],
                }
            ]
        }
        result = validate_recipe_schema(data)
        assert result.valid is True


# ============================================================================
# Dispatcher Tests
# ============================================================================


class TestValidateImportFile:
    """Tests for validate_import_file() dispatcher."""

    def test_valid_multi_entity_file(self, valid_multi_entity_data):
        """Test multi-entity file validates all entities."""
        result = validate_import_file(valid_multi_entity_data)
        assert result.valid is True

    def test_empty_file(self):
        """Test empty file is valid."""
        result = validate_import_file({})
        assert result.valid is True

    def test_file_with_only_metadata(self):
        """Test file with only metadata (no entities) is valid."""
        data = {"version": "4.0", "export_date": "2026-01-13"}
        result = validate_import_file(data)
        assert result.valid is True

    def test_unknown_top_level_key_warning(self):
        """Test unknown top-level key produces warning."""
        data = {"unknown_entity": [{"foo": "bar"}]}
        result = validate_import_file(data)

        assert result.valid is True  # Warnings don't fail
        assert result.warning_count == 1
        assert "unknown_entity" in result.warnings[0].message

    def test_non_dict_input(self):
        """Test non-dict input produces error."""
        result = validate_import_file([])
        assert result.valid is False
        assert "object" in result.errors[0].expected

    def test_merges_errors_from_multiple_entities(self):
        """Test errors from multiple entities are merged."""
        data = {
            "suppliers": [{"slug": "no-name"}],  # Missing name
            "products": [{"display_name": "Test"}],  # Missing ingredient_slug
        }
        result = validate_import_file(data)

        assert result.valid is False
        assert result.error_count == 2  # One error from each entity

    def test_known_metadata_keys_not_warned(self):
        """Test known metadata keys don't produce warnings."""
        data = {
            "version": "4.0",
            "export_date": "2026-01-13",
            "source": "Bake Tracker",
            "_meta": {"editable_fields": []},
            "metadata": {"info": "test"},
            "suppliers": [{"name": "Test"}],
        }
        result = validate_import_file(data)

        assert result.valid is True
        # No warnings about version, export_date, source, _meta, metadata
        unexpected_warnings = [
            w
            for w in result.warnings
            if w.field in ["version", "export_date", "source", "_meta", "metadata"]
        ]
        assert len(unexpected_warnings) == 0


# ============================================================================
# Edge Case Tests
# ============================================================================


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_null_value_in_array(self):
        """Test null value in entity array produces error."""
        data = {"suppliers": [None]}
        result = validate_supplier_schema(data)

        assert result.valid is False
        assert "object" in result.errors[0].expected

    def test_nested_null_in_recipe_ingredients(self):
        """Test null in recipe ingredients array produces error."""
        data = {"recipes": [{"name": "Test", "ingredients": [None]}]}
        result = validate_recipe_schema(data)

        assert result.valid is False

    def test_boolean_treated_as_wrong_type(self):
        """Test boolean is not treated as number."""
        data = {"recipes": [{"name": "Test", "yield_quantity": True}]}
        result = validate_recipe_schema(data)

        assert result.valid is False
        assert "positive number" in result.errors[0].expected

    def test_string_number_not_valid(self):
        """Test string representation of number is not valid for numeric fields."""
        data = {
            "ingredients": [
                {"display_name": "Test", "package_unit_quantity": "5.0"}
            ]
        }
        result = validate_ingredient_schema(data)

        assert result.valid is False
        assert "positive number" in result.errors[0].expected

    def test_large_array_validates_all(self):
        """Test large arrays validate all records."""
        # Create 100 valid suppliers
        suppliers = [{"name": f"Supplier {i}"} for i in range(100)]
        # Add one invalid at the end
        suppliers.append({"slug": "no-name"})

        data = {"suppliers": suppliers}
        result = validate_supplier_schema(data)

        assert result.valid is False
        assert result.error_count == 1
        assert result.errors[0].record_number == 101  # Last record

    def test_whitespace_only_string_not_valid(self):
        """Test whitespace-only string is not valid for required fields."""
        data = {"suppliers": [{"name": "   "}]}
        result = validate_supplier_schema(data)

        assert result.valid is False

    def test_special_characters_in_name(self):
        """Test special characters in name are allowed."""
        data = {"suppliers": [{"name": "O'Brien's Farm & Market"}]}
        result = validate_supplier_schema(data)
        assert result.valid is True

    def test_unicode_in_fields(self):
        """Test unicode characters are handled correctly."""
        data = {"suppliers": [{"name": "日本の農場", "notes": "にほんご"}]}
        result = validate_supplier_schema(data)
        assert result.valid is True
