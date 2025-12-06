"""Product Service - Brand/package product management.

This module provides business logic for managing brand-specific products
for ingredients, including preferred product toggling, UPC tracking, and dependency
checking.

All functions are stateless and use session_scope() for transaction management.

Key Features:
- Brand and package size tracking
- Preferred product toggle (atomic - only one preferred per ingredient)
- UPC/GTIN barcode support for future scanning
- Display name auto-calculation from brand + package size
- Dependency checking before deletion
- Supplier tracking for shopping recommendations

Example Usage:
  >>> from src.services.product_service import create_product, set_preferred_product
  >>> from decimal import Decimal
  >>>
  >>> # Create a product
  >>> data = {
  ...     "brand": "King Arthur",
  ...     "package_size": "25 lb bag",
  ...     "purchase_unit": "lb",
  ...     "purchase_quantity": Decimal("25.0"),
  ...     "preferred": True
  ... }
  >>> product = create_product("all_purpose_flour", data)
  >>> product.display_name
  'King Arthur - 25 lb bag'
  >>>
  >>> # Set preferred product (atomic toggle)
  >>> set_preferred_product(product.id)
"""

from typing import Dict, Any, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..models import Ingredient
from decimal import Decimal
from math import ceil

from ..models import Product
from .unit_converter import convert_any_units
from .database import session_scope
from .exceptions import (
    ProductNotFound,
    ProductInUse,
    IngredientNotFoundBySlug,
    ValidationError as ServiceValidationError,
    DatabaseError,
)
from .ingredient_service import get_ingredient
from ..utils.validators import validate_product_data
from sqlalchemy.orm import joinedload


def create_product(ingredient_slug: str, product_data: Dict[str, Any]) -> Product:
    """Create a new variant for an ingredient.

    If preferred=True, this function will automatically set all other variants
    for this ingredient to preferred=False (atomic operation).

    Args:
        ingredient_slug: Slug of parent ingredient
        product_data: Dictionary containing:
            - brand (str, required): Brand name
            - package_size (str, optional): Human-readable size
            - purchase_unit (str, required): Unit purchased in
            - purchase_quantity (Decimal, required): Quantity in package
            - upc (str, optional): Universal Product Code
            - gtin (str, optional): Global Trade Item Number
            - supplier (str, optional): Where to buy
            - preferred (bool, optional): Mark as preferred variant (default False)
            - net_content_value (Decimal, optional): Industry standard field
            - net_content_uom (str, optional): Industry standard field

    Returns:
        Product: Created variant object with auto-calculated display_name

    Raises:
        IngredientNotFoundBySlug: If ingredient_slug doesn't exist
        ValidationError: If required fields missing or invalid
        DatabaseError: If database operation fails

    Note:
        Display name is auto-calculated as "{brand} - {package_size}" or just "{brand}"
        if package_size is not provided.

    Example:
        >>> data = {
        ...     "brand": "King Arthur",
        ...     "package_size": "25 lb bag",
        ...     "purchase_unit": "lb",
        ...     "purchase_quantity": Decimal("25.0"),
        ...     "preferred": True
        ... }
        >>> variant = create_variant("all_purpose_flour", data)
        >>> variant.display_name
        'King Arthur - 25 lb bag'
        >>> product.preferred
        True
    """
    # Validate ingredient exists
    ingredient = get_ingredient(ingredient_slug)

    # Validate variant data
    is_valid, errors = validate_product_data(product_data, ingredient_slug)
    if not is_valid:
        raise ServiceValidationError(errors)

    try:
        with session_scope() as session:
            # If preferred=True, clear all other variants for this ingredient
            if product_data.get("preferred", False):
                session.query(Product).filter_by(ingredient_id=ingredient.id).update(
                    {"preferred": False}
                )

            # Create variant instance
            product = Product(
                ingredient_id=ingredient.id,
                brand=product_data["brand"],
                package_size=product_data.get("package_size"),
                purchase_unit=product_data["purchase_unit"],
                purchase_quantity=product_data["purchase_quantity"],
                upc_code=product_data.get("upc"),
                gtin=product_data.get("gtin"),
                supplier=product_data.get("supplier"),
                preferred=product_data.get("preferred", False),
                net_content_value=product_data.get("net_content_value"),
                net_content_uom=product_data.get("net_content_uom"),
            )

            session.add(variant)
            session.flush()  # Get ID before commit

            return variant

    except IngredientNotFoundBySlug:
        raise
    except ServiceValidationError:
        raise
    except Exception as e:
        raise DatabaseError("Failed to create variant", original_error=e)


def get_product(product_id: int) -> Product:
    """Retrieve variant by ID.

    Args:
        product_id: Product identifier

    Returns:
        Product: Product object with ingredient relationship eager-loaded

    Raises:
        ProductNotFound: If product_id doesn't exist

    Example:
        >>> variant = get_variant(123)
        >>> product.brand
        'King Arthur'
        >>> product.ingredient.name
        'All-Purpose Flour'
    """
    with session_scope() as session:
        variant = (
            session.query(Product)
            .options(
                joinedload(Product.ingredient),
                joinedload(Product.purchases),
                joinedload(Product.pantry_items),
            )
            .filter_by(id=product_id)
            .first()
        )

        if not product:
            raise ProductNotFound(product_id)

        return variant


def get_products_for_ingredient(ingredient_slug: str) -> List[Product]:
    """Retrieve all variants for an ingredient, sorted with preferred first.

    Args:
        ingredient_slug: Ingredient identifier

    Returns:
        List[Product]: All variants for ingredient, preferred variant first, then by brand

    Raises:
        IngredientNotFoundBySlug: If ingredient_slug doesn't exist

    Example:
        >>> variants = get_products_for_ingredient("all_purpose_flour")
        >>> variants[0].preferred
        True
        >>> [v.brand for v in variants]
        ['King Arthur', "Bob's Red Mill", 'Store Brand']
    """
    # Validate ingredient exists
    ingredient = get_ingredient(ingredient_slug)

    with session_scope() as session:
        return (
            session.query(Product)
            .options(
                joinedload(Product.ingredient),
                joinedload(Product.purchases),
                joinedload(Product.pantry_items),
            )
            .filter_by(ingredient_id=ingredient.id)
            .order_by(
                Product.preferred.desc(),  # Preferred first
                Product.brand,  # Then alphabetical by brand
            )
            .all()
        )


def set_preferred_product(product_id: int) -> Product:
    """Mark variant as preferred, clearing preferred flag on all other variants for same ingredient.

    This function ensures atomicity: all variants for the ingredient are set to
    preferred=False, then the specified variant is set to preferred=True, all
    within a single transaction.

    Args:
        product_id: ID of variant to mark as preferred

    Returns:
        Product: Updated variant with preferred=True

    Raises:
        ProductNotFound: If product_id doesn't exist
        DatabaseError: If database operation fails

    Note:
        This function ensures only one variant per ingredient is marked preferred.
        All other variants for the same ingredient will have preferred=False.

    Example:
        >>> variant = set_preferred_variant(456)
        >>> product.preferred
        True
        >>> # All other variants for this ingredient now have preferred=False
    """
    # Get variant to find ingredient_slug
    variant = get_variant(product_id)

    try:
        with session_scope() as session:
            # Atomic operation: UPDATE all to False, then SET one to True
            session.query(Product).filter_by(ingredient_id=product.ingredient_id).update(
                {"preferred": False}
            )

            # Set this variant to preferred
            product_to_update = (
                session.query(Product)
                .options(
                    joinedload(Product.ingredient),
                    joinedload(Product.purchases),
                    joinedload(Product.pantry_items),
                )
                .get(product_id)
            )
            product_to_update.preferred = True

            return product_to_update

    except ProductNotFound:
        raise
    except Exception as e:
        raise DatabaseError(f"Failed to set preferred variant {product_id}", original_error=e)


def update_product(product_id: int, product_data: Dict[str, Any]) -> Product:
    """Update variant attributes.

    Args:
        product_id: Product identifier
        product_data: Dictionary with fields to update (partial update supported)
            - brand (str, optional): New brand
            - package_size (str, optional): New package size
            - purchase_unit (str, optional): New purchase unit
            - purchase_quantity (Decimal, optional): New purchase quantity
            - upc, gtin, supplier (optional): Update identification/sourcing
            - preferred (bool, optional): Change preferred status
            - net_content_value, net_content_uom (optional): Industry fields

    Returns:
        Product: Updated variant object

    Raises:
        ProductNotFound: If product_id doesn't exist
        ValidationError: If update data invalid or attempting to change ingredient_slug
        DatabaseError: If database operation fails

    Note:
        ingredient_slug (FK) cannot be changed after creation.
        If updating preferred to True, use set_preferred_variant() instead for proper toggling.

    Example:
        >>> updated = update_variant(123, {
        ...     "package_size": "50 lb bag",
        ...     "purchase_quantity": Decimal("50.0")
        ... })
        >>> updated.package_size
        '50 lb bag'
    """
    # Prevent ingredient_slug changes
    if "ingredient_id" in product_data:
        raise ServiceValidationError("Ingredient cannot be changed after variant creation")

    try:
        with session_scope() as session:
            # Get existing variant
            variant = (
                session.query(Product)
                .options(
                    joinedload(Product.ingredient),
                    joinedload(Product.purchases),
                    joinedload(Product.pantry_items),
                )
                .filter_by(id=product_id)
                .first()
            )
            if not product:
                raise ProductNotFound(product_id)

            # Update attributes
            for key, value in product_data.items():
                if hasattr(variant, key):
                    setattr(variant, key, value)

            return variant

    except ProductNotFound:
        raise
    except ServiceValidationError:
        raise
    except Exception as e:
        raise DatabaseError(f"Failed to update variant {product_id}", original_error=e)


def delete_product(product_id: int) -> bool:
    """Delete variant if not referenced by pantry items or purchases.

    Args:
        product_id: Product identifier

    Returns:
        bool: True if deletion successful

    Raises:
        ProductNotFound: If product_id doesn't exist
        ProductInUse: If variant has dependencies (pantry items, purchases)
        DatabaseError: If database operation fails

    Example:
        >>> delete_variant(789)
        True

        >>> delete_variant(123)  # Has pantry items
        Traceback (most recent call last):
        ...
        ProductInUse: Cannot delete variant 123: used in 12 pantry_items, 25 purchases
    """
    # Check dependencies first
    deps = check_product_dependencies(product_id)

    if any(deps.values()):
        raise ProductInUse(product_id, deps)

    try:
        with session_scope() as session:
            variant = session.query(Product).filter_by(id=product_id).first()
            if not product:
                raise ProductNotFound(product_id)

            session.delete(variant)
            return True

    except ProductNotFound:
        raise
    except ProductInUse:
        raise
    except Exception as e:
        raise DatabaseError(f"Failed to delete variant {product_id}", original_error=e)


def check_product_dependencies(product_id: int) -> Dict[str, int]:
    """Check if variant is referenced by other entities.

    Args:
        product_id: Product identifier

    Returns:
        Dict[str, int]: Dependency counts
            - "pantry_items": Number of pantry items using this variant
            - "purchases": Number of purchase records for this variant

    Raises:
        ProductNotFound: If product_id doesn't exist

    Example:
        >>> deps = check_product_dependencies(123)
        >>> deps
        {'pantry_items': 5, 'purchases': 12}
    """
    # Import models here to avoid circular dependencies
    # from ..models import PantryItem, Purchase

    # Verify variant exists (validates product_id)
    get_variant(product_id)

    # TODO: Implement when PantryItem and Purchase models are connected
    # with session_scope() as session:
    #     pantry_count = session.query(PantryItem).filter_by(product_id=product_id).count()
    #     purchase_count = session.query(Purchase).filter_by(product_id=product_id).count()
    pantry_count = 0
    purchase_count = 0

    return {"pantry_items": pantry_count, "purchases": purchase_count}


def search_products_by_upc(upc: str) -> List[Product]:
    """Search variants by UPC code (exact match).

    Args:
        upc: Universal Product Code (12-14 digits)

    Returns:
        List[Product]: Matching variants (may be multiple if same UPC across suppliers)

    Example:
        >>> variants = search_variants_by_upc("012345678901")
        >>> len(variants)
        2  # Same product from different suppliers
        >>> [v.brand for v in variants]
        ['Costco Kirkland', 'Amazon Basics']
    """
    with session_scope() as session:
        return (
            session.query(Product)
            .options(
                joinedload(Product.ingredient),
                joinedload(Product.purchases),
                joinedload(Product.pantry_items),
            )
            .filter_by(upc=upc)
            .all()
        )


def get_preferred_product(ingredient_slug: str) -> Optional[Product]:
    """Get the preferred variant for an ingredient.

    Args:
        ingredient_slug: Ingredient identifier

    Returns:
        Optional[Product]: Preferred variant, or None if no variant marked preferred

    Raises:
        IngredientNotFoundBySlug: If ingredient_slug doesn't exist

    Example:
        >>> preferred = get_preferred_variant("all_purpose_flour")
        >>> preferred.brand if preferred else "No preferred variant set"
        'King Arthur'

        >>> preferred = get_preferred_variant("new_ingredient")
        >>> preferred is None
        True
    """
    # Validate ingredient exists
    ingredient = get_ingredient(ingredient_slug)

    with session_scope() as session:
        return (
            session.query(Product)
            .options(
                joinedload(Product.ingredient),
                joinedload(Product.purchases),
                joinedload(Product.pantry_items),
            )
            .filter_by(ingredient_id=ingredient.id, preferred=True)
            .first()
        )


def _calculate_product_cost(
    product: Product,
    shortfall: Decimal,
    recipe_unit: str,
    ingredient: "Ingredient",
) -> Dict[str, Any]:
    """Calculate cost metrics for a variant given an ingredient shortfall.

    This helper function computes all the cost and quantity metrics needed
    for a shopping list recommendation.

    Args:
        product: Product model instance with purchases relationship loaded
        shortfall: Amount needed in recipe units (e.g., 5 cups)
        recipe_unit: Unit used in recipes (e.g., "cup", "oz")
        ingredient: Ingredient model instance for unit conversion

    Returns:
        Dict containing:
            - product_id: Product ID
            - brand: Brand name
            - package_size: Human-readable size (e.g., "25 lb bag")
            - package_quantity: Numeric quantity per package
            - purchase_unit: Unit purchased in
            - cost_per_purchase_unit: Cost per purchase unit (e.g., $0.72/lb)
            - cost_per_recipe_unit: Cost per recipe unit (e.g., $0.18/cup)
            - min_packages: Minimum whole packages needed to cover shortfall
            - total_cost: Total purchase cost for min_packages
            - is_preferred: Whether this is the preferred variant
            - cost_available: Whether cost data is available
            - cost_message: Message if cost unavailable (e.g., "Cost unknown")
            - conversion_error: True if unit conversion failed
            - error_message: Conversion error message if applicable

    Example:
        >>> rec = _calculate_product_cost(flour_variant, Decimal("5"), "cup", flour_ingredient)
        >>> rec['min_packages']
        1
        >>> rec['cost_per_recipe_unit']
        Decimal('0.18')
    """
    result = {
        "product_id": product.id,
        "brand": product.brand or "",
        "package_size": product.package_size or "",
        "package_quantity": float(product.purchase_quantity),
        "purchase_unit": product.purchase_unit,
        "is_preferred": product.preferred,
        "cost_available": True,
        "cost_message": "",
        "conversion_error": False,
        "error_message": "",
        "cost_per_purchase_unit": None,
        "cost_per_recipe_unit": None,
        "min_packages": 0,
        "total_cost": None,
    }

    # Get cost per purchase unit from most recent purchase
    cost_per_purchase_unit = product.get_current_cost_per_unit()

    if cost_per_purchase_unit == 0 or cost_per_purchase_unit is None:
        # No purchase history - can still recommend variant but no cost
        result["cost_available"] = False
        result["cost_message"] = "Cost unknown"
        result["cost_per_purchase_unit"] = Decimal("0")
    else:
        result["cost_per_purchase_unit"] = Decimal(str(cost_per_purchase_unit))

    # Convert shortfall from recipe_unit to purchase_unit
    success, shortfall_in_purchase_units, msg = convert_any_units(
        float(shortfall),
        recipe_unit,
        product.purchase_unit,
        ingredient=ingredient,
    )

    if not success:
        # Unit conversion failed
        result["conversion_error"] = True
        result["error_message"] = msg or "Unit conversion unavailable"
        # Still return variant info but can't calculate packages/cost
        return result

    # Guard against division by zero
    if product.purchase_quantity <= 0:
        result["conversion_error"] = True
        result["error_message"] = "Invalid package quantity"
        return result

    # Calculate minimum packages (always round UP to cover shortfall)
    min_packages = ceil(shortfall_in_purchase_units / product.purchase_quantity)
    result["min_packages"] = max(1, min_packages)  # At least 1 package

    # Calculate total cost if cost data is available
    if result["cost_available"]:
        # Total cost = packages * quantity_per_package * cost_per_unit
        actual_quantity = Decimal(str(result["min_packages"])) * Decimal(
            str(product.purchase_quantity)
        )
        result["total_cost"] = actual_quantity * result["cost_per_purchase_unit"]

        # Calculate cost per recipe unit
        # Need conversion factor: how many recipe_units per purchase_unit
        success, conversion_factor, _ = convert_any_units(
            1.0,
            product.purchase_unit,
            recipe_unit,
            ingredient=ingredient,
        )

        if success and conversion_factor > 0:
            result["cost_per_recipe_unit"] = result["cost_per_purchase_unit"] / Decimal(
                str(conversion_factor)
            )
        else:
            # Can't calculate cost per recipe unit but still have total cost
            result["cost_per_recipe_unit"] = None

    return result


def get_product_recommendation(
    ingredient_slug: str,
    shortfall: Decimal,
    recipe_unit: str,
) -> Dict[str, Any]:
    """Get variant recommendation(s) for an ingredient shortfall.

    This function determines which variant(s) to recommend for purchasing
    to cover an ingredient shortfall. It handles three scenarios:
    - Preferred variant exists: return that as the recommendation
    - Multiple variants, none preferred: return all variants for user choice
    - No variants configured: return status indicating this

    Args:
        ingredient_slug: Slug identifier for the ingredient
        shortfall: Amount needed in recipe units
        recipe_unit: Unit used in recipes (e.g., "cup", "oz")

    Returns:
        Dict containing:
            - variant_status: 'preferred' | 'multiple' | 'none' | 'sufficient'
            - variant_recommendation: Primary recommendation dict (or None)
            - all_variants: List of all variant recommendations
            - message: Optional status message

    Raises:
        IngredientNotFoundBySlug: If ingredient_slug doesn't exist

    Example:
        >>> rec = get_product_recommendation("all_purpose_flour", Decimal("5"), "cup")
        >>> rec['variant_status']
        'preferred'
        >>> rec['variant_recommendation']['brand']
        'King Arthur'
    """
    # Handle zero or negative shortfall
    if shortfall <= 0:
        return {
            "variant_status": "sufficient",
            "variant_recommendation": None,
            "all_variants": [],
            "message": "Sufficient stock",
        }

    # Get ingredient (will raise IngredientNotFoundBySlug if not found)
    try:
        ingredient = get_ingredient(ingredient_slug)
    except IngredientNotFoundBySlug:
        return {
            "variant_status": "none",
            "variant_recommendation": None,
            "all_variants": [],
            "message": "Ingredient not found",
        }

    # Get all variants for ingredient
    variants = get_products_for_ingredient(ingredient_slug)

    if not variants:
        return {
            "variant_status": "none",
            "variant_recommendation": None,
            "all_variants": [],
            "message": "No variant configured",
        }

    # Calculate cost metrics for all variants
    all_recommendations = []
    for v in variants:
        rec = _calculate_product_cost(v, shortfall, recipe_unit, ingredient)
        all_recommendations.append(rec)

    # Sort by total_cost (cheapest first, None values at end)
    def sort_key(r):
        if r.get("total_cost") is None:
            return (1, float("inf"))  # Put at end
        return (0, float(r["total_cost"]))

    all_recommendations.sort(key=sort_key)

    # Check for preferred variant
    preferred = get_preferred_variant(ingredient_slug)

    if preferred:
        # Find the recommendation for the preferred variant
        preferred_rec = next(
            (r for r in all_recommendations if r["product_id"] == preferred.id),
            None,
        )
        return {
            "variant_status": "preferred",
            "variant_recommendation": preferred_rec,
            "all_variants": [preferred_rec] if preferred_rec else [],
            "message": "",
        }
    else:
        # Multiple variants, none preferred - return all for user choice
        return {
            "variant_status": "multiple",
            "variant_recommendation": None,
            "all_variants": all_recommendations,
            "message": "",
        }
