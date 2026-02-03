"""
Schema Validation Service - Pre-import JSON schema validation.

Validates import file structure before database operations begin.
Returns structured results with actionable error messages.

Usage:
    from src.services.schema_validation_service import validate_import_file

    result = validate_import_file(data)
    if not result.valid:
        for error in result.errors:
            print(f"Error at {error.field}: {error.message}")
"""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from src.utils.constants import MEASUREMENT_UNITS


# ============================================================================
# Dataclasses
# ============================================================================


@dataclass
class ValidationError:
    """A validation error with context for actionable error messages."""

    field: str  # Field path (e.g., "ingredients[0].display_name")
    message: str  # Human-readable error message
    record_number: int  # 1-indexed record number (0 if top-level)
    expected: Optional[str] = None  # Expected type or format
    actual: Optional[str] = None  # Actual value or type found


@dataclass
class ValidationWarning:
    """A validation warning (non-fatal issue)."""

    field: str  # Field path
    message: str  # Human-readable warning message
    record_number: int  # 1-indexed record number


@dataclass
class ValidationResult:
    """Result of schema validation."""

    valid: bool  # True if no errors (warnings OK)
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationWarning] = field(default_factory=list)

    @property
    def error_count(self) -> int:
        return len(self.errors)

    @property
    def warning_count(self) -> int:
        return len(self.warnings)

    def merge(self, other: "ValidationResult") -> "ValidationResult":
        """Merge another ValidationResult into this one."""
        return ValidationResult(
            valid=self.valid and other.valid,
            errors=self.errors + other.errors,
            warnings=self.warnings + other.warnings,
        )


# ============================================================================
# Helper Functions
# ============================================================================

# Slug pattern: lowercase alphanumeric with hyphens and underscores
SLUG_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


def _is_valid_slug(value: str) -> bool:
    """Check if a string is a valid slug format."""
    if not value:
        return False
    return bool(SLUG_PATTERN.match(value))


def _is_non_empty_string(value: Any) -> bool:
    """Check if value is a non-empty string."""
    return isinstance(value, str) and len(value.strip()) > 0


def _is_positive_number(value: Any) -> bool:
    """Check if value is a positive number."""
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return value > 0
    return False


def _is_non_negative_number(value: Any) -> bool:
    """Check if value is a non-negative number."""
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return value >= 0
    return False


def _get_type_name(value: Any) -> str:
    """Get a human-readable type name for a value."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


# ============================================================================
# Entity Validators
# ============================================================================


def validate_supplier_schema(
    data: Dict[str, Any], known_fields: Optional[Set[str]] = None
) -> ValidationResult:
    """
    Validate supplier entity records.

    Args:
        data: Parsed JSON data containing 'suppliers' array
        known_fields: Optional set of known fields for warning on unexpected

    Returns:
        ValidationResult with errors and warnings
    """
    errors: List[ValidationError] = []
    warnings: List[ValidationWarning] = []

    # Check suppliers array exists
    if "suppliers" not in data:
        return ValidationResult(valid=True, errors=[], warnings=[])

    suppliers = data["suppliers"]
    if not isinstance(suppliers, list):
        errors.append(
            ValidationError(
                field="suppliers",
                message="Expected an array of supplier records",
                record_number=0,
                expected="array",
                actual=_get_type_name(suppliers),
            )
        )
        return ValidationResult(valid=False, errors=errors, warnings=warnings)

    # Define known fields for suppliers (matches actual export format from F050)
    supplier_fields = {
        "name",
        "slug",
        "supplier_type",
        "street_address",
        "city",
        "state",
        "zip_code",
        "website_url",
        "notes",
        "is_active",
        "contact_info",  # Legacy field
        "id",
        "uuid",
    }

    for idx, supplier in enumerate(suppliers):
        record_num = idx + 1
        prefix = f"suppliers[{idx}]"

        if not isinstance(supplier, dict):
            errors.append(
                ValidationError(
                    field=prefix,
                    message="Expected a supplier object",
                    record_number=record_num,
                    expected="object",
                    actual=_get_type_name(supplier),
                )
            )
            continue

        # Required: name
        if "name" not in supplier:
            errors.append(
                ValidationError(
                    field=f"{prefix}.name",
                    message="Missing required field 'name'",
                    record_number=record_num,
                    expected="string",
                    actual="missing",
                )
            )
        elif not _is_non_empty_string(supplier["name"]):
            errors.append(
                ValidationError(
                    field=f"{prefix}.name",
                    message="Field 'name' must be a non-empty string",
                    record_number=record_num,
                    expected="non-empty string",
                    actual=_get_type_name(supplier["name"]),
                )
            )

        # Optional: slug (if present, must be valid slug format)
        if "slug" in supplier and supplier["slug"] is not None:
            if not isinstance(supplier["slug"], str):
                errors.append(
                    ValidationError(
                        field=f"{prefix}.slug",
                        message="Field 'slug' must be a string",
                        record_number=record_num,
                        expected="string",
                        actual=_get_type_name(supplier["slug"]),
                    )
                )
            elif supplier["slug"] and not _is_valid_slug(supplier["slug"]):
                errors.append(
                    ValidationError(
                        field=f"{prefix}.slug",
                        message="Field 'slug' must be lowercase alphanumeric with hyphens/underscores",
                        record_number=record_num,
                        expected="valid slug format (e.g., 'my-supplier')",
                        actual=repr(supplier["slug"]),
                    )
                )

        # Optional: contact_info (if present, must be string)
        if "contact_info" in supplier and supplier["contact_info"] is not None:
            if not isinstance(supplier["contact_info"], str):
                errors.append(
                    ValidationError(
                        field=f"{prefix}.contact_info",
                        message="Field 'contact_info' must be a string",
                        record_number=record_num,
                        expected="string",
                        actual=_get_type_name(supplier["contact_info"]),
                    )
                )

        # Optional: notes (if present, must be string)
        if "notes" in supplier and supplier["notes"] is not None:
            if not isinstance(supplier["notes"], str):
                errors.append(
                    ValidationError(
                        field=f"{prefix}.notes",
                        message="Field 'notes' must be a string",
                        record_number=record_num,
                        expected="string",
                        actual=_get_type_name(supplier["notes"]),
                    )
                )

        # Optional: supplier_type (if present, must be valid type)
        if "supplier_type" in supplier and supplier["supplier_type"] is not None:
            if not isinstance(supplier["supplier_type"], str):
                errors.append(
                    ValidationError(
                        field=f"{prefix}.supplier_type",
                        message="Field 'supplier_type' must be a string",
                        record_number=record_num,
                        expected="string",
                        actual=_get_type_name(supplier["supplier_type"]),
                    )
                )
            elif supplier["supplier_type"] not in ("physical", "online"):
                warnings.append(
                    ValidationWarning(
                        field=f"{prefix}.supplier_type",
                        message=f"Unknown supplier_type '{supplier['supplier_type']}' - expected 'physical' or 'online'",
                        record_number=record_num,
                    )
                )

        # Optional: city (if present, must be string)
        if "city" in supplier and supplier["city"] is not None:
            if not isinstance(supplier["city"], str):
                errors.append(
                    ValidationError(
                        field=f"{prefix}.city",
                        message="Field 'city' must be a string",
                        record_number=record_num,
                        expected="string",
                        actual=_get_type_name(supplier["city"]),
                    )
                )

        # Optional: state (if present, must be string)
        if "state" in supplier and supplier["state"] is not None:
            if not isinstance(supplier["state"], str):
                errors.append(
                    ValidationError(
                        field=f"{prefix}.state",
                        message="Field 'state' must be a string",
                        record_number=record_num,
                        expected="string",
                        actual=_get_type_name(supplier["state"]),
                    )
                )

        # Optional: zip_code (if present, must be string)
        if "zip_code" in supplier and supplier["zip_code"] is not None:
            if not isinstance(supplier["zip_code"], str):
                errors.append(
                    ValidationError(
                        field=f"{prefix}.zip_code",
                        message="Field 'zip_code' must be a string",
                        record_number=record_num,
                        expected="string",
                        actual=_get_type_name(supplier["zip_code"]),
                    )
                )

        # Optional: street_address (if present, must be string)
        if "street_address" in supplier and supplier["street_address"] is not None:
            if not isinstance(supplier["street_address"], str):
                errors.append(
                    ValidationError(
                        field=f"{prefix}.street_address",
                        message="Field 'street_address' must be a string",
                        record_number=record_num,
                        expected="string",
                        actual=_get_type_name(supplier["street_address"]),
                    )
                )

        # Optional: website_url (if present, must be string)
        if "website_url" in supplier and supplier["website_url"] is not None:
            if not isinstance(supplier["website_url"], str):
                errors.append(
                    ValidationError(
                        field=f"{prefix}.website_url",
                        message="Field 'website_url' must be a string",
                        record_number=record_num,
                        expected="string",
                        actual=_get_type_name(supplier["website_url"]),
                    )
                )

        # Optional: is_active (if present, must be boolean)
        if "is_active" in supplier and supplier["is_active"] is not None:
            if not isinstance(supplier["is_active"], bool):
                errors.append(
                    ValidationError(
                        field=f"{prefix}.is_active",
                        message="Field 'is_active' must be a boolean",
                        record_number=record_num,
                        expected="boolean",
                        actual=_get_type_name(supplier["is_active"]),
                    )
                )

        # Check for unexpected fields
        for key in supplier.keys():
            if key not in supplier_fields:
                warnings.append(
                    ValidationWarning(
                        field=f"{prefix}.{key}",
                        message=f"Unexpected field '{key}' will be ignored",
                        record_number=record_num,
                    )
                )

    return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)


def validate_ingredient_schema(
    data: Dict[str, Any], known_fields: Optional[Set[str]] = None
) -> ValidationResult:
    """
    Validate ingredient entity records.

    Args:
        data: Parsed JSON data containing 'ingredients' array
        known_fields: Optional set of known fields for warning on unexpected

    Returns:
        ValidationResult with errors and warnings
    """
    errors: List[ValidationError] = []
    warnings: List[ValidationWarning] = []

    # Check ingredients array exists
    if "ingredients" not in data:
        return ValidationResult(valid=True, errors=[], warnings=[])

    ingredients = data["ingredients"]
    if not isinstance(ingredients, list):
        errors.append(
            ValidationError(
                field="ingredients",
                message="Expected an array of ingredient records",
                record_number=0,
                expected="array",
                actual=_get_type_name(ingredients),
            )
        )
        return ValidationResult(valid=False, errors=errors, warnings=warnings)

    # Define known fields for ingredients
    ingredient_fields = {
        "display_name",
        "slug",
        "category",
        "package_unit",
        "package_unit_quantity",
        "notes",
        "density_volume_value",
        "density_volume_unit",
        "density_weight_value",
        "density_weight_unit",
        "foodon_id",
        "fdc_ids",
        "foodex2_code",
        "langual_terms",
        "allergens",
        "description",
        "hierarchy_level",
    }

    valid_units_lower = {u.lower() for u in MEASUREMENT_UNITS}

    for idx, ingredient in enumerate(ingredients):
        record_num = idx + 1
        prefix = f"ingredients[{idx}]"

        if not isinstance(ingredient, dict):
            errors.append(
                ValidationError(
                    field=prefix,
                    message="Expected an ingredient object",
                    record_number=record_num,
                    expected="object",
                    actual=_get_type_name(ingredient),
                )
            )
            continue

        # Required: display_name
        if "display_name" not in ingredient:
            errors.append(
                ValidationError(
                    field=f"{prefix}.display_name",
                    message="Missing required field 'display_name'",
                    record_number=record_num,
                    expected="string",
                    actual="missing",
                )
            )
        elif not _is_non_empty_string(ingredient["display_name"]):
            errors.append(
                ValidationError(
                    field=f"{prefix}.display_name",
                    message="Field 'display_name' must be a non-empty string",
                    record_number=record_num,
                    expected="non-empty string",
                    actual=_get_type_name(ingredient["display_name"]),
                )
            )

        # Optional: category (if present, must be string)
        if "category" in ingredient and ingredient["category"] is not None:
            if not isinstance(ingredient["category"], str):
                errors.append(
                    ValidationError(
                        field=f"{prefix}.category",
                        message="Field 'category' must be a string",
                        record_number=record_num,
                        expected="string",
                        actual=_get_type_name(ingredient["category"]),
                    )
                )

        # Optional: package_unit (if present, must be valid unit)
        if "package_unit" in ingredient and ingredient["package_unit"] is not None:
            if not isinstance(ingredient["package_unit"], str):
                errors.append(
                    ValidationError(
                        field=f"{prefix}.package_unit",
                        message="Field 'package_unit' must be a string",
                        record_number=record_num,
                        expected="string",
                        actual=_get_type_name(ingredient["package_unit"]),
                    )
                )
            elif ingredient["package_unit"].lower() not in valid_units_lower:
                warnings.append(
                    ValidationWarning(
                        field=f"{prefix}.package_unit",
                        message=f"Unknown unit '{ingredient['package_unit']}' - may not be recognized",
                        record_number=record_num,
                    )
                )

        # Optional: package_unit_quantity (if present, must be positive number)
        if (
            "package_unit_quantity" in ingredient
            and ingredient["package_unit_quantity"] is not None
        ):
            if not _is_positive_number(ingredient["package_unit_quantity"]):
                errors.append(
                    ValidationError(
                        field=f"{prefix}.package_unit_quantity",
                        message="Field 'package_unit_quantity' must be a positive number",
                        record_number=record_num,
                        expected="positive number",
                        actual=str(ingredient["package_unit_quantity"]),
                    )
                )

        # Optional: notes (if present, must be string)
        if "notes" in ingredient and ingredient["notes"] is not None:
            if not isinstance(ingredient["notes"], str):
                errors.append(
                    ValidationError(
                        field=f"{prefix}.notes",
                        message="Field 'notes' must be a string",
                        record_number=record_num,
                        expected="string",
                        actual=_get_type_name(ingredient["notes"]),
                    )
                )

        # Check for unexpected fields
        for key in ingredient.keys():
            if key not in ingredient_fields:
                warnings.append(
                    ValidationWarning(
                        field=f"{prefix}.{key}",
                        message=f"Unexpected field '{key}' will be ignored",
                        record_number=record_num,
                    )
                )

    return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)


def validate_product_schema(
    data: Dict[str, Any], known_fields: Optional[Set[str]] = None
) -> ValidationResult:
    """
    Validate product entity records.

    Args:
        data: Parsed JSON data containing 'products' array
        known_fields: Optional set of known fields for warning on unexpected

    Returns:
        ValidationResult with errors and warnings
    """
    errors: List[ValidationError] = []
    warnings: List[ValidationWarning] = []

    # Check products array exists
    if "products" not in data:
        return ValidationResult(valid=True, errors=[], warnings=[])

    products = data["products"]
    if not isinstance(products, list):
        errors.append(
            ValidationError(
                field="products",
                message="Expected an array of product records",
                record_number=0,
                expected="array",
                actual=_get_type_name(products),
            )
        )
        return ValidationResult(valid=False, errors=errors, warnings=warnings)

    # Define known fields for products
    product_fields = {
        "display_name",
        "ingredient_slug",
        "supplier_slug",
        "brand",
        "product_name",
        "package_unit",
        "package_unit_quantity",
        "package_size",
        "package_type",
        "unit_cost",
        "upc_code",
        "preferred",
        "supplier",
        "supplier_sku",
        "notes",
        "gtin",
        "brand_owner",
        "gpc_brick_code",
        "net_content_value",
        "net_content_uom",
        "country_of_sale",
        "off_id",
        "is_hidden",  # Export format field
        "id",
        "uuid",
    }

    valid_units_lower = {u.lower() for u in MEASUREMENT_UNITS}

    for idx, product in enumerate(products):
        record_num = idx + 1
        prefix = f"products[{idx}]"

        if not isinstance(product, dict):
            errors.append(
                ValidationError(
                    field=prefix,
                    message="Expected a product object",
                    record_number=record_num,
                    expected="object",
                    actual=_get_type_name(product),
                )
            )
            continue

        # Optional: display_name OR product_name (can be derived from brand + ingredient)
        # Validate if present but don't require it
        if "display_name" in product and product["display_name"] is not None:
            if not isinstance(product["display_name"], str):
                errors.append(
                    ValidationError(
                        field=f"{prefix}.display_name",
                        message="Field 'display_name' must be a string",
                        record_number=record_num,
                        expected="string",
                        actual=_get_type_name(product["display_name"]),
                    )
                )
        if "product_name" in product and product["product_name"] is not None:
            if not isinstance(product["product_name"], str):
                errors.append(
                    ValidationError(
                        field=f"{prefix}.product_name",
                        message="Field 'product_name' must be a string",
                        record_number=record_num,
                        expected="string",
                        actual=_get_type_name(product["product_name"]),
                    )
                )

        # Required: ingredient_slug
        if "ingredient_slug" not in product:
            errors.append(
                ValidationError(
                    field=f"{prefix}.ingredient_slug",
                    message="Missing required field 'ingredient_slug'",
                    record_number=record_num,
                    expected="string",
                    actual="missing",
                )
            )
        elif not _is_non_empty_string(product["ingredient_slug"]):
            errors.append(
                ValidationError(
                    field=f"{prefix}.ingredient_slug",
                    message="Field 'ingredient_slug' must be a non-empty string",
                    record_number=record_num,
                    expected="non-empty string",
                    actual=_get_type_name(product["ingredient_slug"]),
                )
            )

        # Optional: supplier_slug (if present, must be string)
        if "supplier_slug" in product and product["supplier_slug"] is not None:
            if not isinstance(product["supplier_slug"], str):
                errors.append(
                    ValidationError(
                        field=f"{prefix}.supplier_slug",
                        message="Field 'supplier_slug' must be a string",
                        record_number=record_num,
                        expected="string",
                        actual=_get_type_name(product["supplier_slug"]),
                    )
                )

        # Optional: brand (if present, must be string)
        if "brand" in product and product["brand"] is not None:
            if not isinstance(product["brand"], str):
                errors.append(
                    ValidationError(
                        field=f"{prefix}.brand",
                        message="Field 'brand' must be a string",
                        record_number=record_num,
                        expected="string",
                        actual=_get_type_name(product["brand"]),
                    )
                )

        # Optional: package_unit (if present, must be valid unit)
        if "package_unit" in product and product["package_unit"] is not None:
            if not isinstance(product["package_unit"], str):
                errors.append(
                    ValidationError(
                        field=f"{prefix}.package_unit",
                        message="Field 'package_unit' must be a string",
                        record_number=record_num,
                        expected="string",
                        actual=_get_type_name(product["package_unit"]),
                    )
                )
            elif product["package_unit"].lower() not in valid_units_lower:
                warnings.append(
                    ValidationWarning(
                        field=f"{prefix}.package_unit",
                        message=f"Unknown unit '{product['package_unit']}' - may not be recognized",
                        record_number=record_num,
                    )
                )

        # Optional: unit_cost (if present, must be non-negative number)
        if "unit_cost" in product and product["unit_cost"] is not None:
            if not _is_non_negative_number(product["unit_cost"]):
                errors.append(
                    ValidationError(
                        field=f"{prefix}.unit_cost",
                        message="Field 'unit_cost' must be a non-negative number",
                        record_number=record_num,
                        expected="non-negative number",
                        actual=str(product["unit_cost"]),
                    )
                )

        # Check for unexpected fields
        for key in product.keys():
            if key not in product_fields:
                warnings.append(
                    ValidationWarning(
                        field=f"{prefix}.{key}",
                        message=f"Unexpected field '{key}' will be ignored",
                        record_number=record_num,
                    )
                )

    return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)


def validate_recipe_schema(
    data: Dict[str, Any], known_fields: Optional[Set[str]] = None
) -> ValidationResult:
    """
    Validate recipe entity records.

    Args:
        data: Parsed JSON data containing 'recipes' array
        known_fields: Optional set of known fields for warning on unexpected

    Returns:
        ValidationResult with errors and warnings
    """
    errors: List[ValidationError] = []
    warnings: List[ValidationWarning] = []

    # Check recipes array exists
    if "recipes" not in data:
        return ValidationResult(valid=True, errors=[], warnings=[])

    recipes = data["recipes"]
    if not isinstance(recipes, list):
        errors.append(
            ValidationError(
                field="recipes",
                message="Expected an array of recipe records",
                record_number=0,
                expected="array",
                actual=_get_type_name(recipes),
            )
        )
        return ValidationResult(valid=False, errors=errors, warnings=warnings)

    # Define known fields for recipes
    # F056: yield_quantity, yield_unit removed - use FinishedUnit records instead
    recipe_fields = {
        "name",
        "slug",
        "category",
        "ingredients",
        "components",
        "instructions",
        "notes",
        "prep_time",
        "cook_time",
        "total_time",
    }

    # Define known fields for recipe ingredients
    recipe_ingredient_fields = {
        "ingredient_name",
        "ingredient_slug",
        "quantity",
        "unit",
        "notes",
        "optional",
    }

    # Define known fields for recipe components
    recipe_component_fields = {
        "recipe_name",
        "recipe_slug",
        "quantity",
        "notes",
    }

    for idx, recipe in enumerate(recipes):
        record_num = idx + 1
        prefix = f"recipes[{idx}]"

        if not isinstance(recipe, dict):
            errors.append(
                ValidationError(
                    field=prefix,
                    message="Expected a recipe object",
                    record_number=record_num,
                    expected="object",
                    actual=_get_type_name(recipe),
                )
            )
            continue

        # Required: name
        if "name" not in recipe:
            errors.append(
                ValidationError(
                    field=f"{prefix}.name",
                    message="Missing required field 'name'",
                    record_number=record_num,
                    expected="string",
                    actual="missing",
                )
            )
        elif not _is_non_empty_string(recipe["name"]):
            errors.append(
                ValidationError(
                    field=f"{prefix}.name",
                    message="Field 'name' must be a non-empty string",
                    record_number=record_num,
                    expected="non-empty string",
                    actual=_get_type_name(recipe["name"]),
                )
            )

        # Optional: category (if present, must be string)
        if "category" in recipe and recipe["category"] is not None:
            if not isinstance(recipe["category"], str):
                errors.append(
                    ValidationError(
                        field=f"{prefix}.category",
                        message="Field 'category' must be a string",
                        record_number=record_num,
                        expected="string",
                        actual=_get_type_name(recipe["category"]),
                    )
                )

        # F056: yield_quantity, yield_unit validation removed
        # These fields are deprecated - use FinishedUnit records instead
        # Legacy import files may still have these fields but they're ignored

        # Optional: ingredients (if present, must be array)
        if "ingredients" in recipe and recipe["ingredients"] is not None:
            if not isinstance(recipe["ingredients"], list):
                errors.append(
                    ValidationError(
                        field=f"{prefix}.ingredients",
                        message="Field 'ingredients' must be an array",
                        record_number=record_num,
                        expected="array",
                        actual=_get_type_name(recipe["ingredients"]),
                    )
                )
            else:
                # Validate each ingredient in the recipe
                for ing_idx, ing in enumerate(recipe["ingredients"]):
                    ing_prefix = f"{prefix}.ingredients[{ing_idx}]"

                    if not isinstance(ing, dict):
                        errors.append(
                            ValidationError(
                                field=ing_prefix,
                                message="Expected an ingredient object",
                                record_number=record_num,
                                expected="object",
                                actual=_get_type_name(ing),
                            )
                        )
                        continue

                    # Required: ingredient_name or ingredient_slug
                    has_name = "ingredient_name" in ing and _is_non_empty_string(
                        ing.get("ingredient_name")
                    )
                    has_slug = "ingredient_slug" in ing and _is_non_empty_string(
                        ing.get("ingredient_slug")
                    )
                    if not has_name and not has_slug:
                        errors.append(
                            ValidationError(
                                field=ing_prefix,
                                message="Recipe ingredient must have 'ingredient_name' or 'ingredient_slug'",
                                record_number=record_num,
                                expected="ingredient_name or ingredient_slug",
                                actual="missing",
                            )
                        )

                    # Required: quantity
                    if "quantity" not in ing:
                        errors.append(
                            ValidationError(
                                field=f"{ing_prefix}.quantity",
                                message="Missing required field 'quantity'",
                                record_number=record_num,
                                expected="number",
                                actual="missing",
                            )
                        )
                    elif not _is_positive_number(ing["quantity"]):
                        errors.append(
                            ValidationError(
                                field=f"{ing_prefix}.quantity",
                                message="Field 'quantity' must be a positive number",
                                record_number=record_num,
                                expected="positive number",
                                actual=str(ing.get("quantity")),
                            )
                        )

                    # Required: unit
                    if "unit" not in ing:
                        errors.append(
                            ValidationError(
                                field=f"{ing_prefix}.unit",
                                message="Missing required field 'unit'",
                                record_number=record_num,
                                expected="string",
                                actual="missing",
                            )
                        )
                    elif not _is_non_empty_string(ing["unit"]):
                        errors.append(
                            ValidationError(
                                field=f"{ing_prefix}.unit",
                                message="Field 'unit' must be a non-empty string",
                                record_number=record_num,
                                expected="non-empty string",
                                actual=_get_type_name(ing.get("unit")),
                            )
                        )

                    # Check for unexpected fields in recipe ingredient
                    for key in ing.keys():
                        if key not in recipe_ingredient_fields:
                            warnings.append(
                                ValidationWarning(
                                    field=f"{ing_prefix}.{key}",
                                    message=f"Unexpected field '{key}' will be ignored",
                                    record_number=record_num,
                                )
                            )

        # Optional: components (if present, must be array for nested recipes)
        if "components" in recipe and recipe["components"] is not None:
            if not isinstance(recipe["components"], list):
                errors.append(
                    ValidationError(
                        field=f"{prefix}.components",
                        message="Field 'components' must be an array",
                        record_number=record_num,
                        expected="array",
                        actual=_get_type_name(recipe["components"]),
                    )
                )
            else:
                # Validate each component in the recipe
                for comp_idx, comp in enumerate(recipe["components"]):
                    comp_prefix = f"{prefix}.components[{comp_idx}]"

                    if not isinstance(comp, dict):
                        errors.append(
                            ValidationError(
                                field=comp_prefix,
                                message="Expected a component object",
                                record_number=record_num,
                                expected="object",
                                actual=_get_type_name(comp),
                            )
                        )
                        continue

                    # Required: recipe_name or recipe_slug
                    has_name = "recipe_name" in comp and _is_non_empty_string(
                        comp.get("recipe_name")
                    )
                    has_slug = "recipe_slug" in comp and _is_non_empty_string(
                        comp.get("recipe_slug")
                    )
                    if not has_name and not has_slug:
                        errors.append(
                            ValidationError(
                                field=comp_prefix,
                                message="Recipe component must have 'recipe_name' or 'recipe_slug'",
                                record_number=record_num,
                                expected="recipe_name or recipe_slug",
                                actual="missing",
                            )
                        )

                    # Check for unexpected fields in recipe component
                    for key in comp.keys():
                        if key not in recipe_component_fields:
                            warnings.append(
                                ValidationWarning(
                                    field=f"{comp_prefix}.{key}",
                                    message=f"Unexpected field '{key}' will be ignored",
                                    record_number=record_num,
                                )
                            )

        # Check for unexpected fields in recipe
        for key in recipe.keys():
            if key not in recipe_fields:
                warnings.append(
                    ValidationWarning(
                        field=f"{prefix}.{key}",
                        message=f"Unexpected field '{key}' will be ignored",
                        record_number=record_num,
                    )
                )

    return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)


# ============================================================================
# Material Entity Validators (Feature 047)
# ============================================================================


def validate_material_category_schema(
    data: Dict[str, Any], known_fields: Optional[Set[str]] = None
) -> ValidationResult:
    """
    Validate material category entity records.

    Args:
        data: Parsed JSON data containing 'material_categories' array
        known_fields: Optional set of known fields for warning on unexpected

    Returns:
        ValidationResult with errors and warnings
    """
    errors: List[ValidationError] = []
    warnings: List[ValidationWarning] = []

    if "material_categories" not in data:
        return ValidationResult(valid=True, errors=[], warnings=[])

    categories = data["material_categories"]
    if not isinstance(categories, list):
        errors.append(
            ValidationError(
                field="material_categories",
                message="Expected an array of material category records",
                record_number=0,
                expected="array",
                actual=_get_type_name(categories),
            )
        )
        return ValidationResult(valid=False, errors=errors, warnings=warnings)

    category_fields = {"name", "slug", "description", "sort_order", "id", "uuid"}

    for idx, category in enumerate(categories):
        record_num = idx + 1
        prefix = f"material_categories[{idx}]"

        if not isinstance(category, dict):
            errors.append(
                ValidationError(
                    field=prefix,
                    message="Expected a material category object",
                    record_number=record_num,
                    expected="object",
                    actual=_get_type_name(category),
                )
            )
            continue

        # Required: name
        if "name" not in category:
            errors.append(
                ValidationError(
                    field=f"{prefix}.name",
                    message="Missing required field 'name'",
                    record_number=record_num,
                    expected="string",
                    actual="missing",
                )
            )
        elif not _is_non_empty_string(category["name"]):
            errors.append(
                ValidationError(
                    field=f"{prefix}.name",
                    message="Field 'name' must be a non-empty string",
                    record_number=record_num,
                    expected="non-empty string",
                    actual=_get_type_name(category["name"]),
                )
            )

        # Optional: slug (if present, must be valid slug format)
        if "slug" in category and category["slug"] is not None:
            if not isinstance(category["slug"], str):
                errors.append(
                    ValidationError(
                        field=f"{prefix}.slug",
                        message="Field 'slug' must be a string",
                        record_number=record_num,
                        expected="string",
                        actual=_get_type_name(category["slug"]),
                    )
                )

        # Optional: sort_order (if present, must be integer)
        if "sort_order" in category and category["sort_order"] is not None:
            if not isinstance(category["sort_order"], int) or isinstance(
                category["sort_order"], bool
            ):
                errors.append(
                    ValidationError(
                        field=f"{prefix}.sort_order",
                        message="Field 'sort_order' must be an integer",
                        record_number=record_num,
                        expected="integer",
                        actual=_get_type_name(category["sort_order"]),
                    )
                )

        # Check for unexpected fields
        for key in category.keys():
            if key not in category_fields:
                warnings.append(
                    ValidationWarning(
                        field=f"{prefix}.{key}",
                        message=f"Unexpected field '{key}' will be ignored",
                        record_number=record_num,
                    )
                )

    return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)


def validate_material_subcategory_schema(
    data: Dict[str, Any], known_fields: Optional[Set[str]] = None
) -> ValidationResult:
    """
    Validate material subcategory entity records.

    Args:
        data: Parsed JSON data containing 'material_subcategories' array
        known_fields: Optional set of known fields for warning on unexpected

    Returns:
        ValidationResult with errors and warnings
    """
    errors: List[ValidationError] = []
    warnings: List[ValidationWarning] = []

    if "material_subcategories" not in data:
        return ValidationResult(valid=True, errors=[], warnings=[])

    subcategories = data["material_subcategories"]
    if not isinstance(subcategories, list):
        errors.append(
            ValidationError(
                field="material_subcategories",
                message="Expected an array of material subcategory records",
                record_number=0,
                expected="array",
                actual=_get_type_name(subcategories),
            )
        )
        return ValidationResult(valid=False, errors=errors, warnings=warnings)

    subcategory_fields = {
        "name",
        "slug",
        "category_slug",
        "category_id",
        "description",
        "sort_order",
        "id",
        "uuid",
    }

    for idx, subcategory in enumerate(subcategories):
        record_num = idx + 1
        prefix = f"material_subcategories[{idx}]"

        if not isinstance(subcategory, dict):
            errors.append(
                ValidationError(
                    field=prefix,
                    message="Expected a material subcategory object",
                    record_number=record_num,
                    expected="object",
                    actual=_get_type_name(subcategory),
                )
            )
            continue

        # Required: name
        if "name" not in subcategory:
            errors.append(
                ValidationError(
                    field=f"{prefix}.name",
                    message="Missing required field 'name'",
                    record_number=record_num,
                    expected="string",
                    actual="missing",
                )
            )
        elif not _is_non_empty_string(subcategory["name"]):
            errors.append(
                ValidationError(
                    field=f"{prefix}.name",
                    message="Field 'name' must be a non-empty string",
                    record_number=record_num,
                    expected="non-empty string",
                    actual=_get_type_name(subcategory["name"]),
                )
            )

        # Required: category_slug (FK reference)
        if "category_slug" not in subcategory and "category_id" not in subcategory:
            errors.append(
                ValidationError(
                    field=f"{prefix}.category_slug",
                    message="Missing required field 'category_slug' or 'category_id'",
                    record_number=record_num,
                    expected="string",
                    actual="missing",
                )
            )
        elif "category_slug" in subcategory and subcategory["category_slug"] is not None:
            if not _is_non_empty_string(subcategory["category_slug"]):
                errors.append(
                    ValidationError(
                        field=f"{prefix}.category_slug",
                        message="Field 'category_slug' must be a non-empty string",
                        record_number=record_num,
                        expected="non-empty string",
                        actual=_get_type_name(subcategory["category_slug"]),
                    )
                )

        # Check for unexpected fields
        for key in subcategory.keys():
            if key not in subcategory_fields:
                warnings.append(
                    ValidationWarning(
                        field=f"{prefix}.{key}",
                        message=f"Unexpected field '{key}' will be ignored",
                        record_number=record_num,
                    )
                )

    return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)


def validate_material_schema(
    data: Dict[str, Any], known_fields: Optional[Set[str]] = None
) -> ValidationResult:
    """
    Validate material entity records.

    Args:
        data: Parsed JSON data containing 'materials' array
        known_fields: Optional set of known fields for warning on unexpected

    Returns:
        ValidationResult with errors and warnings
    """
    errors: List[ValidationError] = []
    warnings: List[ValidationWarning] = []

    if "materials" not in data:
        return ValidationResult(valid=True, errors=[], warnings=[])

    materials = data["materials"]
    if not isinstance(materials, list):
        errors.append(
            ValidationError(
                field="materials",
                message="Expected an array of material records",
                record_number=0,
                expected="array",
                actual=_get_type_name(materials),
            )
        )
        return ValidationResult(valid=False, errors=errors, warnings=warnings)

    material_fields = {
        "name",
        "display_name",
        "slug",
        "base_unit_type",
        "description",
        "notes",
        "category",
        "subcategory_slug",
        "subcategory_id",
        "category_slug",
        "category_id",
        "id",
        "uuid",
    }
    valid_base_units = {"each", "linear_inches", "square_inches"}

    for idx, material in enumerate(materials):
        record_num = idx + 1
        prefix = f"materials[{idx}]"

        if not isinstance(material, dict):
            errors.append(
                ValidationError(
                    field=prefix,
                    message="Expected a material object",
                    record_number=record_num,
                    expected="object",
                    actual=_get_type_name(material),
                )
            )
            continue

        # Required: name or display_name
        has_name = "name" in material and _is_non_empty_string(material.get("name"))
        has_display = "display_name" in material and _is_non_empty_string(
            material.get("display_name")
        )
        if not has_name and not has_display:
            errors.append(
                ValidationError(
                    field=f"{prefix}.name",
                    message="Missing required field 'name' or 'display_name'",
                    record_number=record_num,
                    expected="non-empty string",
                    actual="missing",
                )
            )

        # Optional: base_unit_type (if present, must be valid)
        if "base_unit_type" in material and material["base_unit_type"] is not None:
            if not isinstance(material["base_unit_type"], str):
                errors.append(
                    ValidationError(
                        field=f"{prefix}.base_unit_type",
                        message="Field 'base_unit_type' must be a string",
                        record_number=record_num,
                        expected="string",
                        actual=_get_type_name(material["base_unit_type"]),
                    )
                )
            elif material["base_unit_type"] not in valid_base_units:
                errors.append(
                    ValidationError(
                        field=f"{prefix}.base_unit_type",
                        message=f"Invalid base_unit_type '{material['base_unit_type']}'",
                        record_number=record_num,
                        expected=f"one of: {', '.join(valid_base_units)}",
                        actual=material["base_unit_type"],
                    )
                )

        # Check for unexpected fields
        for key in material.keys():
            if key not in material_fields:
                warnings.append(
                    ValidationWarning(
                        field=f"{prefix}.{key}",
                        message=f"Unexpected field '{key}' will be ignored",
                        record_number=record_num,
                    )
                )

    return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)


def validate_material_product_schema(
    data: Dict[str, Any], known_fields: Optional[Set[str]] = None
) -> ValidationResult:
    """
    Validate material product entity records.

    Args:
        data: Parsed JSON data containing 'material_products' array
        known_fields: Optional set of known fields for warning on unexpected

    Returns:
        ValidationResult with errors and warnings
    """
    errors: List[ValidationError] = []
    warnings: List[ValidationWarning] = []

    if "material_products" not in data:
        return ValidationResult(valid=True, errors=[], warnings=[])

    products = data["material_products"]
    if not isinstance(products, list):
        errors.append(
            ValidationError(
                field="material_products",
                message="Expected an array of material product records",
                record_number=0,
                expected="array",
                actual=_get_type_name(products),
            )
        )
        return ValidationResult(valid=False, errors=errors, warnings=warnings)

    product_fields = {
        "name",
        "display_name",
        "slug",
        "material_slug",
        "material",
        "material_id",
        "brand",
        "sku",
        "package_quantity",
        "package_unit",
        "quantity_in_base_units",
        "current_inventory",
        "weighted_avg_cost",
        "is_hidden",
        "notes",
        "supplier",
        "supplier_name",
        "supplier_slug",
        "supplier_id",
        "default_unit",  # Export format field
        "id",
        "uuid",
    }

    for idx, product in enumerate(products):
        record_num = idx + 1
        prefix = f"material_products[{idx}]"

        if not isinstance(product, dict):
            errors.append(
                ValidationError(
                    field=prefix,
                    message="Expected a material product object",
                    record_number=record_num,
                    expected="object",
                    actual=_get_type_name(product),
                )
            )
            continue

        # Required: name or display_name
        has_name = "name" in product and _is_non_empty_string(product.get("name"))
        has_display = "display_name" in product and _is_non_empty_string(
            product.get("display_name")
        )
        if not has_name and not has_display:
            errors.append(
                ValidationError(
                    field=f"{prefix}.name",
                    message="Missing required field 'name' or 'display_name'",
                    record_number=record_num,
                    expected="non-empty string",
                    actual="missing",
                )
            )

        # Optional: package_quantity (if present, must be positive number)
        if "package_quantity" in product and product["package_quantity"] is not None:
            if not _is_positive_number(product["package_quantity"]):
                errors.append(
                    ValidationError(
                        field=f"{prefix}.package_quantity",
                        message="Field 'package_quantity' must be a positive number",
                        record_number=record_num,
                        expected="positive number",
                        actual=str(product["package_quantity"]),
                    )
                )

        # Optional: package_unit or default_unit (if present, must be string)
        if "package_unit" in product and product["package_unit"] is not None:
            if not _is_non_empty_string(product["package_unit"]):
                errors.append(
                    ValidationError(
                        field=f"{prefix}.package_unit",
                        message="Field 'package_unit' must be a non-empty string",
                        record_number=record_num,
                        expected="non-empty string",
                        actual=_get_type_name(product["package_unit"]),
                    )
                )
        if "default_unit" in product and product["default_unit"] is not None:
            if not _is_non_empty_string(product["default_unit"]):
                errors.append(
                    ValidationError(
                        field=f"{prefix}.default_unit",
                        message="Field 'default_unit' must be a non-empty string",
                        record_number=record_num,
                        expected="non-empty string",
                        actual=_get_type_name(product["default_unit"]),
                    )
                )

        # Optional: quantity_in_base_units (if present, must be positive number)
        if "quantity_in_base_units" in product and product["quantity_in_base_units"] is not None:
            if not _is_positive_number(product["quantity_in_base_units"]):
                errors.append(
                    ValidationError(
                        field=f"{prefix}.quantity_in_base_units",
                        message="Field 'quantity_in_base_units' must be a positive number",
                        record_number=record_num,
                        expected="positive number",
                        actual=str(product["quantity_in_base_units"]),
                    )
                )

        # Optional: current_inventory (if present, must be non-negative)
        if "current_inventory" in product and product["current_inventory"] is not None:
            if not _is_non_negative_number(product["current_inventory"]):
                errors.append(
                    ValidationError(
                        field=f"{prefix}.current_inventory",
                        message="Field 'current_inventory' must be a non-negative number",
                        record_number=record_num,
                        expected="non-negative number",
                        actual=str(product["current_inventory"]),
                    )
                )

        # Optional: weighted_avg_cost (if present, must be non-negative)
        if "weighted_avg_cost" in product and product["weighted_avg_cost"] is not None:
            if not _is_non_negative_number(product["weighted_avg_cost"]):
                errors.append(
                    ValidationError(
                        field=f"{prefix}.weighted_avg_cost",
                        message="Field 'weighted_avg_cost' must be a non-negative number",
                        record_number=record_num,
                        expected="non-negative number",
                        actual=str(product["weighted_avg_cost"]),
                    )
                )

        # Optional: is_hidden (if present, must be boolean)
        if "is_hidden" in product and product["is_hidden"] is not None:
            if not isinstance(product["is_hidden"], bool):
                errors.append(
                    ValidationError(
                        field=f"{prefix}.is_hidden",
                        message="Field 'is_hidden' must be a boolean",
                        record_number=record_num,
                        expected="boolean",
                        actual=_get_type_name(product["is_hidden"]),
                    )
                )

        # Check for unexpected fields
        for key in product.keys():
            if key not in product_fields:
                warnings.append(
                    ValidationWarning(
                        field=f"{prefix}.{key}",
                        message=f"Unexpected field '{key}' will be ignored",
                        record_number=record_num,
                    )
                )

    return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)


def validate_material_unit_schema(
    data: Dict[str, Any], known_fields: Optional[Set[str]] = None
) -> ValidationResult:
    """
    Validate material unit entity records.

    Args:
        data: Parsed JSON data containing 'material_units' array
        known_fields: Optional set of known fields for warning on unexpected

    Returns:
        ValidationResult with errors and warnings
    """
    errors: List[ValidationError] = []
    warnings: List[ValidationWarning] = []

    if "material_units" not in data:
        return ValidationResult(valid=True, errors=[], warnings=[])

    units = data["material_units"]
    if not isinstance(units, list):
        errors.append(
            ValidationError(
                field="material_units",
                message="Expected an array of material unit records",
                record_number=0,
                expected="array",
                actual=_get_type_name(units),
            )
        )
        return ValidationResult(valid=False, errors=errors, warnings=warnings)

    unit_fields = {
        "name",
        "slug",
        "material_slug",
        "material_id",
        "quantity_per_unit",
        "description",
        "id",
        "uuid",
    }

    for idx, unit in enumerate(units):
        record_num = idx + 1
        prefix = f"material_units[{idx}]"

        if not isinstance(unit, dict):
            errors.append(
                ValidationError(
                    field=prefix,
                    message="Expected a material unit object",
                    record_number=record_num,
                    expected="object",
                    actual=_get_type_name(unit),
                )
            )
            continue

        # Required: name
        if "name" not in unit:
            errors.append(
                ValidationError(
                    field=f"{prefix}.name",
                    message="Missing required field 'name'",
                    record_number=record_num,
                    expected="string",
                    actual="missing",
                )
            )
        elif not _is_non_empty_string(unit["name"]):
            errors.append(
                ValidationError(
                    field=f"{prefix}.name",
                    message="Field 'name' must be a non-empty string",
                    record_number=record_num,
                    expected="non-empty string",
                    actual=_get_type_name(unit["name"]),
                )
            )

        # Required: material_slug (FK reference)
        if "material_slug" not in unit and "material_id" not in unit:
            errors.append(
                ValidationError(
                    field=f"{prefix}.material_slug",
                    message="Missing required field 'material_slug' or 'material_id'",
                    record_number=record_num,
                    expected="string",
                    actual="missing",
                )
            )
        elif "material_slug" in unit and unit["material_slug"] is not None:
            if not _is_non_empty_string(unit["material_slug"]):
                errors.append(
                    ValidationError(
                        field=f"{prefix}.material_slug",
                        message="Field 'material_slug' must be a non-empty string",
                        record_number=record_num,
                        expected="non-empty string",
                        actual=_get_type_name(unit["material_slug"]),
                    )
                )

        # Required: quantity_per_unit (positive number)
        if "quantity_per_unit" not in unit:
            errors.append(
                ValidationError(
                    field=f"{prefix}.quantity_per_unit",
                    message="Missing required field 'quantity_per_unit'",
                    record_number=record_num,
                    expected="positive number",
                    actual="missing",
                )
            )
        elif not _is_positive_number(unit["quantity_per_unit"]):
            errors.append(
                ValidationError(
                    field=f"{prefix}.quantity_per_unit",
                    message="Field 'quantity_per_unit' must be a positive number",
                    record_number=record_num,
                    expected="positive number",
                    actual=str(unit["quantity_per_unit"]),
                )
            )

        # Check for unexpected fields
        for key in unit.keys():
            if key not in unit_fields:
                warnings.append(
                    ValidationWarning(
                        field=f"{prefix}.{key}",
                        message=f"Unexpected field '{key}' will be ignored",
                        record_number=record_num,
                    )
                )

    return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)


# ============================================================================
# Main Dispatcher
# ============================================================================


def validate_import_file(data: Any) -> ValidationResult:
    """
    Validate import file structure, routing to appropriate entity validators.

    This is the main entry point for import validation. It detects which
    entity arrays are present and validates each one.

    Args:
        data: Parsed JSON data (dict) from import file

    Returns:
        ValidationResult with merged errors and warnings from all entities
    """
    if not isinstance(data, dict):
        return ValidationResult(
            valid=False,
            errors=[
                ValidationError(
                    field="",
                    message="Import file must be a JSON object",
                    record_number=0,
                    expected="object",
                    actual=_get_type_name(data),
                )
            ],
            warnings=[],
        )

    # Start with valid result and merge each entity validation
    result = ValidationResult(valid=True, errors=[], warnings=[])

    # Check for known entity arrays and validate each
    entity_validators = {
        "suppliers": validate_supplier_schema,
        "ingredients": validate_ingredient_schema,
        "products": validate_product_schema,
        "recipes": validate_recipe_schema,
        # Material entities (FR-012: full catalog validation)
        "material_categories": validate_material_category_schema,
        "material_subcategories": validate_material_subcategory_schema,
        "materials": validate_material_schema,
        "material_products": validate_material_product_schema,
        "material_units": validate_material_unit_schema,
    }

    entities_found = []
    for entity_key, validator in entity_validators.items():
        if entity_key in data:
            entities_found.append(entity_key)
            entity_result = validator(data)
            result = result.merge(entity_result)

    # If no known entities found, that's okay - empty import is valid
    # But warn if the file has unexpected top-level keys
    known_keys = set(entity_validators.keys()) | {
        "version",
        "export_date",
        "exported_at",  # Backup format field
        "application",  # Backup format field
        "source",
        "_meta",
        "metadata",
    }
    for key in data.keys():
        if key not in known_keys:
            result.warnings.append(
                ValidationWarning(
                    field=key,
                    message=f"Unknown top-level key '{key}' will be ignored",
                    record_number=0,
                )
            )

    return result
