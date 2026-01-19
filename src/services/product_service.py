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
  ...     "package_unit": "lb",
  ...     "package_unit_quantity": Decimal("25.0"),
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
    NonLeafIngredientError,
)
from .ingredient_service import get_ingredient
from ..utils.validators import validate_product_data
from sqlalchemy.orm import joinedload
import re


# ============================================================================
# F057: Product Slug Generation
# ============================================================================


def _slugify_component(value: str) -> str:
    """Convert a string component to a slug-safe format.

    Args:
        value: String to slugify

    Returns:
        Lowercase string with special chars replaced by underscores
    """
    if not value:
        return "unknown"
    slug = value.lower()
    slug = re.sub(r"[\s\-]+", "_", slug)
    slug = re.sub(r"[^a-z0-9_]", "", slug)
    slug = re.sub(r"_+", "_", slug)
    slug = slug.strip("_")
    return slug or "unknown"


def _generate_product_slug(
    ingredient_slug: str,
    brand: str,
    package_unit_quantity: float,
    package_unit: str,
) -> str:
    """Generate a product slug from its components.

    Format: ingredient_slug:brand:qty:unit
    Example: all_purpose_flour:king_arthur:5.0:lb

    Args:
        ingredient_slug: Slug of the parent ingredient
        brand: Brand name
        package_unit_quantity: Package quantity
        package_unit: Package unit

    Returns:
        Composite slug string
    """
    brand_slug = _slugify_component(brand)
    unit_slug = _slugify_component(package_unit)
    return f"{ingredient_slug}:{brand_slug}:{package_unit_quantity}:{unit_slug}"


def _generate_unique_product_slug(
    base_slug: str,
    session,
    exclude_id: Optional[int] = None,
) -> str:
    """Generate a unique product slug by appending a suffix if needed.

    Args:
        base_slug: The base slug to make unique
        session: Database session
        exclude_id: ID to exclude from uniqueness check (for updates)

    Returns:
        Unique slug (e.g., "flour:brand:5.0:lb" or "flour:brand:5.0:lb-2")
    """
    slug = base_slug
    counter = 1

    while True:
        query = session.query(Product).filter(Product.slug == slug)
        if exclude_id is not None:
            query = query.filter(Product.id != exclude_id)

        if query.first() is None:
            return slug

        counter += 1
        slug = f"{base_slug}-{counter}"


# ============================================================================
# Feature 031: Hierarchy Validation Helpers
# ============================================================================


def _validate_leaf_ingredient_for_product(ingredient, session) -> None:
    """
    Validate that an ingredient is a leaf (level 2) before linking to a product.

    Args:
        ingredient: Ingredient object to validate
        session: Database session

    Raises:
        NonLeafIngredientError: If ingredient is not a leaf (hierarchy_level != 2)
    """
    if ingredient.hierarchy_level != 2:
        # Get leaf suggestions from descendants
        from src.services import ingredient_hierarchy_service

        suggestions = []
        try:
            descendants = ingredient_hierarchy_service.get_leaf_ingredients(
                parent_id=ingredient.id, session=session
            )
            suggestions = [d["display_name"] for d in descendants[:3]]
        except Exception:
            # If we can't get suggestions, continue without them
            pass

        raise NonLeafIngredientError(
            ingredient_id=ingredient.id,
            ingredient_name=ingredient.display_name,
            context="product",
            suggestions=suggestions,
        )


# ============================================================================
# CRUD Operations
# ============================================================================


def create_product(ingredient_slug: str, product_data: Dict[str, Any]) -> Product:
    """Create a new product for an ingredient.

    If preferred=True, this function will automatically set all other products
    for this ingredient to preferred=False (atomic operation).

    Args:
        ingredient_slug: Slug of parent ingredient
        product_data: Dictionary containing:
            - brand (str, required): Brand name
            - product_name (str, optional): Variant name (e.g., "70% Cacao", "Extra Virgin")
            - package_size (str, optional): Human-readable size
            - package_unit (str, required): Unit the package contains
            - package_unit_quantity (Decimal, required): Quantity in package
            - upc (str, optional): Universal Product Code
            - gtin (str, optional): Global Trade Item Number
            - supplier (str, optional): Where to buy
            - preferred (bool, optional): Mark as preferred product (default False)
            - net_content_value (Decimal, optional): Industry standard field
            - net_content_uom (str, optional): Industry standard field

    Returns:
        Product: Created product object with auto-calculated display_name

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
        ...     "package_unit": "lb",
        ...     "package_unit_quantity": Decimal("25.0"),
        ...     "preferred": True
        ... }
        >>> product = create_product("all_purpose_flour", data)
        >>> product.display_name
        'King Arthur - 25 lb bag'
        >>> product.preferred
        True
    """
    # Validate ingredient exists
    ingredient = get_ingredient(ingredient_slug)

    # Validate product data
    is_valid, errors = validate_product_data(product_data, ingredient_slug)
    if not is_valid:
        raise ServiceValidationError(errors)

    try:
        with session_scope() as session:
            # Feature 031: Validate leaf-only constraint
            _validate_leaf_ingredient_for_product(ingredient, session)

            # If preferred=True, clear all other products for this ingredient
            if product_data.get("preferred", False):
                session.query(Product).filter_by(ingredient_id=ingredient.id).update(
                    {"preferred": False}
                )

            # Normalize empty product_name to None
            product_name = product_data.get("product_name")
            if product_name == "":
                product_name = None

            # Create product instance
            product = Product(
                ingredient_id=ingredient.id,
                brand=product_data["brand"],
                product_name=product_name,
                package_size=product_data.get("package_size"),
                package_unit=product_data["package_unit"],
                package_unit_quantity=product_data["package_unit_quantity"],
                upc_code=product_data.get("upc"),
                gtin=product_data.get("gtin"),
                supplier=product_data.get("supplier"),
                preferred=product_data.get("preferred", False),
                net_content_value=product_data.get("net_content_value"),
                net_content_uom=product_data.get("net_content_uom"),
            )

            session.add(product)
            session.flush()  # Get ID before commit

            return product

    except IngredientNotFoundBySlug:
        raise
    except (ServiceValidationError, NonLeafIngredientError):
        raise
    except Exception as e:
        raise DatabaseError("Failed to create product", original_error=e)


def create_provisional_product(
    ingredient_id: int,
    brand: str,
    package_unit: str,
    package_unit_quantity: float,
    product_name: Optional[str] = None,
    upc_code: Optional[str] = None,
    session: Optional[Any] = None,
) -> Product:
    """Create a provisional product for immediate use during purchase entry.

    Provisional products are created with is_provisional=True, indicating they
    need review to complete missing information. They are fully functional for
    purchases and inventory tracking.

    Args:
        ingredient_id: ID of the parent ingredient (required, must be leaf level)
        brand: Brand name (required, can be "Unknown")
        package_unit: Unit the package contains, e.g., "lb", "oz" (required)
        package_unit_quantity: Quantity per package (required)
        product_name: Optional variant name
        upc_code: Optional UPC/barcode (may have from scanning)
        session: Optional database session for transaction composability

    Returns:
        Product: Created product with is_provisional=True

    Raises:
        ValidationError: If ingredient_id invalid or not a leaf ingredient
        NonLeafIngredientError: If ingredient is not a leaf (hierarchy_level != 2)
        DatabaseError: If database operation fails

    Example:
        >>> product = create_provisional_product(
        ...     ingredient_id=42,
        ...     brand="King Arthur",
        ...     package_unit="lb",
        ...     package_unit_quantity=5.0,
        ... )
        >>> product.is_provisional
        True
    """
    # Validate quantity is positive
    if package_unit_quantity is None or package_unit_quantity <= 0:
        raise ServiceValidationError(
            f"package_unit_quantity must be positive, got {package_unit_quantity}"
        )

    from ..models import Ingredient

    def _create_impl(sess):
        # Validate ingredient exists
        ingredient = sess.query(Ingredient).filter_by(id=ingredient_id).first()
        if not ingredient:
            raise ServiceValidationError(f"Ingredient with id {ingredient_id} not found")

        # Validate leaf-only constraint (hierarchy_level == 2)
        _validate_leaf_ingredient_for_product(ingredient, sess)

        # Normalize empty product_name to None
        normalized_product_name = product_name if product_name != "" else None

        # F057: Generate unique slug for the product
        base_slug = _generate_product_slug(
            ingredient_slug=ingredient.slug,
            brand=brand,
            package_unit_quantity=package_unit_quantity,
            package_unit=package_unit,
        )
        unique_slug = _generate_unique_product_slug(base_slug, sess)

        # Create provisional product with minimal required fields
        product = Product(
            ingredient_id=ingredient_id,
            brand=brand,
            product_name=normalized_product_name,
            package_unit=package_unit,
            package_unit_quantity=package_unit_quantity,
            upc_code=upc_code,
            slug=unique_slug,  # F057: Unique slug for portability
            is_provisional=True,  # Key flag for F057
        )

        sess.add(product)
        sess.flush()  # Get ID before returning

        return product

    try:
        if session is not None:
            return _create_impl(session)
        else:
            with session_scope() as sess:
                return _create_impl(sess)
    except (ServiceValidationError, NonLeafIngredientError):
        raise
    except Exception as e:
        raise DatabaseError("Failed to create provisional product", original_error=e)


def get_product(product_id: int) -> Product:
    """Retrieve product by ID.

    Args:
        product_id: Product identifier

    Returns:
        Product: Product object with ingredient relationship eager-loaded

    Raises:
        ProductNotFound: If product_id doesn't exist

    Example:
        >>> product = get_product(123)
        >>> product.brand
        'King Arthur'
        >>> product.ingredient.display_name
        'All-Purpose Flour'
    """
    with session_scope() as session:
        product = (
            session.query(Product)
            .options(
                joinedload(Product.ingredient),
                joinedload(Product.purchases),
                joinedload(Product.inventory_items),
            )
            .filter_by(id=product_id)
            .first()
        )

        if not product:
            raise ProductNotFound(product_id)

        return product


def get_products_for_ingredient(ingredient_slug: str) -> List[Product]:
    """Retrieve all products for an ingredient, sorted with preferred first.

    Args:
        ingredient_slug: Ingredient identifier

    Returns:
        List[Product]: All products for ingredient, preferred product first, then by brand

    Raises:
        IngredientNotFoundBySlug: If ingredient_slug doesn't exist

    Example:
        >>> products = get_products_for_ingredient("all_purpose_flour")
        >>> products[0].preferred
        True
        >>> [p.brand for p in products]
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
                joinedload(Product.inventory_items),
            )
            .filter_by(ingredient_id=ingredient.id)
            .order_by(
                Product.preferred.desc(),  # Preferred first
                Product.brand,  # Then alphabetical by brand
            )
            .all()
        )


def set_preferred_product(product_id: int) -> Product:
    """Mark product as preferred, clearing preferred flag on all other products for same ingredient.

    This function ensures atomicity: all products for the ingredient are set to
    preferred=False, then the specified product is set to preferred=True, all
    within a single transaction.

    Args:
        product_id: ID of product to mark as preferred

    Returns:
        Product: Updated product with preferred=True

    Raises:
        ProductNotFound: If product_id doesn't exist
        DatabaseError: If database operation fails

    Note:
        This function ensures only one product per ingredient is marked preferred.
        All other products for the same ingredient will have preferred=False.

    Example:
        >>> product = set_preferred_product(456)
        >>> product.preferred
        True
        >>> # All other products for this ingredient now have preferred=False
    """
    # Get product to find ingredient_id
    product = get_product(product_id)

    try:
        with session_scope() as session:
            # Atomic operation: UPDATE all to False, then SET one to True
            session.query(Product).filter_by(ingredient_id=product.ingredient_id).update(
                {"preferred": False}
            )

            # Set this product to preferred
            product_to_update = (
                session.query(Product)
                .options(
                    joinedload(Product.ingredient),
                    joinedload(Product.purchases),
                    joinedload(Product.inventory_items),
                )
                .get(product_id)
            )
            product_to_update.preferred = True

            return product_to_update

    except ProductNotFound:
        raise
    except Exception as e:
        raise DatabaseError(f"Failed to set preferred product {product_id}", original_error=e)


def update_product(product_id: int, product_data: Dict[str, Any]) -> Product:
    """Update product attributes.

    Args:
        product_id: Product identifier
        product_data: Dictionary with fields to update (partial update supported)
            - brand (str, optional): New brand
            - product_name (str, optional): Variant name (e.g., "70% Cacao", "Extra Virgin")
            - package_size (str, optional): New package size
            - package_unit (str, optional): New package unit
            - package_unit_quantity (Decimal, optional): New package quantity
            - upc, gtin, supplier (optional): Update identification/sourcing
            - preferred (bool, optional): Change preferred status
            - net_content_value, net_content_uom (optional): Industry fields

    Returns:
        Product: Updated product object

    Raises:
        ProductNotFound: If product_id doesn't exist
        ValidationError: If update data invalid or attempting to change ingredient_slug
        DatabaseError: If database operation fails

    Note:
        ingredient_slug (FK) cannot be changed after creation.
        If updating preferred to True, use set_preferred_product() instead for proper toggling.

    Example:
        >>> updated = update_product(123, {
        ...     "package_size": "50 lb bag",
        ...     "package_unit_quantity": Decimal("50.0")
        ... })
        >>> updated.package_size
        '50 lb bag'
    """
    # Prevent ingredient_slug changes
    if "ingredient_id" in product_data:
        raise ServiceValidationError("Ingredient cannot be changed after product creation")

    try:
        with session_scope() as session:
            # Get existing product
            product = (
                session.query(Product)
                .options(
                    joinedload(Product.ingredient),
                    joinedload(Product.purchases),
                    joinedload(Product.inventory_items),
                )
                .filter_by(id=product_id)
                .first()
            )
            if not product:
                raise ProductNotFound(product_id)

            # Normalize empty product_name to None
            if "product_name" in product_data:
                if product_data["product_name"] == "":
                    product_data["product_name"] = None

            # Update attributes
            for key, value in product_data.items():
                if hasattr(product, key):
                    setattr(product, key, value)

            return product

    except ProductNotFound:
        raise
    except ServiceValidationError:
        raise
    except Exception as e:
        raise DatabaseError(f"Failed to update product {product_id}", original_error=e)


def delete_product(product_id: int) -> bool:
    """Delete product if not referenced by inventory items or purchases.

    Args:
        product_id: Product identifier

    Returns:
        bool: True if deletion successful

    Raises:
        ProductNotFound: If product_id doesn't exist
        ProductInUse: If product has dependencies (inventory items, purchases)
        DatabaseError: If database operation fails

    Example:
        >>> delete_product(789)
        True

        >>> delete_product(123)  # Has inventory items
        Traceback (most recent call last):
        ...
        ProductInUse: Cannot delete product 123: used in 12 inventory_items, 25 purchases
    """
    # Check dependencies first
    deps = check_product_dependencies(product_id)

    if any(deps.values()):
        raise ProductInUse(product_id, deps)

    try:
        with session_scope() as session:
            product = session.query(Product).filter_by(id=product_id).first()
            if not product:
                raise ProductNotFound(product_id)

            session.delete(product)
            return True

    except ProductNotFound:
        raise
    except ProductInUse:
        raise
    except Exception as e:
        raise DatabaseError(f"Failed to delete product {product_id}", original_error=e)


def check_product_dependencies(product_id: int) -> Dict[str, int]:
    """Check if product is referenced by other entities.

    Args:
        product_id: Product identifier

    Returns:
        Dict[str, int]: Dependency counts
            - "inventory_items": Number of inventory items using this product
            - "purchases": Number of purchase records for this product
            - "packaging_compositions": Number of packaging compositions using this product

    Raises:
        ProductNotFound: If product_id doesn't exist

    Example:
        >>> deps = check_product_dependencies(123)
        >>> deps
        {'inventory_items': 5, 'purchases': 12, 'packaging_compositions': 3}
    """
    from src.models import Composition

    # Verify product exists (validates product_id)
    get_product(product_id)

    # TODO: Implement when InventoryItem and Purchase models are connected
    # with session_scope() as session:
    #     inventory_count = session.query(InventoryItem).filter_by(product_id=product_id).count()
    #     purchase_count = session.query(Purchase).filter_by(product_id=product_id).count()
    inventory_count = 0
    purchase_count = 0

    # Feature 011: Check for packaging compositions using this product
    with session_scope() as session:
        packaging_count = (
            session.query(Composition)
            .filter(Composition.packaging_product_id == product_id)
            .count()
        )

    return {
        "inventory_items": inventory_count,
        "purchases": purchase_count,
        "packaging_compositions": packaging_count,
    }


def search_products_by_upc(upc: str) -> List[Product]:
    """Search products by UPC code (exact match).

    Args:
        upc: Universal Product Code (12-14 digits)

    Returns:
        List[Product]: Matching products (may be multiple if same UPC across suppliers)

    Example:
        >>> products = search_products_by_upc("012345678901")
        >>> len(products)
        2  # Same product from different suppliers
        >>> [p.brand for p in products]
        ['Costco Kirkland', 'Amazon Basics']
    """
    with session_scope() as session:
        return (
            session.query(Product)
            .options(
                joinedload(Product.ingredient),
                joinedload(Product.purchases),
                joinedload(Product.inventory_items),
            )
            .filter_by(upc=upc)
            .all()
        )


def get_preferred_product(ingredient_slug: str) -> Optional[Product]:
    """Get the preferred product for an ingredient.

    Args:
        ingredient_slug: Ingredient identifier

    Returns:
        Optional[Product]: Preferred product, or None if no product marked preferred

    Raises:
        IngredientNotFoundBySlug: If ingredient_slug doesn't exist

    Example:
        >>> preferred = get_preferred_product("all_purpose_flour")
        >>> preferred.brand if preferred else "No preferred product set"
        'King Arthur'

        >>> preferred = get_preferred_product("new_ingredient")
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
                joinedload(Product.inventory_items),
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
    """Calculate cost metrics for a product given an ingredient shortfall.

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
            - package_unit: Unit the package contains
            - cost_per_package_unit: Cost per package unit (e.g., $0.72/lb)
            - cost_per_recipe_unit: Cost per recipe unit (e.g., $0.18/cup)
            - min_packages: Minimum whole packages needed to cover shortfall
            - total_cost: Total purchase cost for min_packages
            - is_preferred: Whether this is the preferred product
            - cost_available: Whether cost data is available
            - cost_message: Message if cost unavailable (e.g., "Cost unknown")
            - conversion_error: True if unit conversion failed
            - error_message: Conversion error message if applicable

    Example:
        >>> rec = _calculate_product_cost(flour_product, Decimal("5"), "cup", flour_ingredient)
        >>> rec['min_packages']
        1
        >>> rec['cost_per_recipe_unit']
        Decimal('0.18')
    """
    result = {
        "product_id": product.id,
        "brand": product.brand or "",
        "package_size": product.package_size or "",
        "package_quantity": float(product.package_unit_quantity),
        "package_unit": product.package_unit,
        "is_preferred": product.preferred,
        "cost_available": True,
        "cost_message": "",
        "conversion_error": False,
        "error_message": "",
        "cost_per_package_unit": None,
        "cost_per_recipe_unit": None,
        "min_packages": 0,
        "total_cost": None,
    }

    # Get cost per package unit from most recent purchase
    cost_per_package_unit = product.get_current_cost_per_unit()

    if cost_per_package_unit == 0 or cost_per_package_unit is None:
        # No purchase history - can still recommend product but no cost
        result["cost_available"] = False
        result["cost_message"] = "Cost unknown"
        result["cost_per_package_unit"] = Decimal("0")
    else:
        result["cost_per_package_unit"] = Decimal(str(cost_per_package_unit))

    # Convert shortfall from recipe_unit to package_unit
    success, shortfall_in_package_units, msg = convert_any_units(
        float(shortfall),
        recipe_unit,
        product.package_unit,
        ingredient=ingredient,
    )

    if not success:
        # Unit conversion failed
        result["conversion_error"] = True
        result["error_message"] = msg or "Unit conversion unavailable"
        # Still return product info but can't calculate packages/cost
        return result

    # Guard against division by zero
    if product.package_unit_quantity <= 0:
        result["conversion_error"] = True
        result["error_message"] = "Invalid package quantity"
        return result

    # Calculate minimum packages (always round UP to cover shortfall)
    min_packages = ceil(shortfall_in_package_units / product.package_unit_quantity)
    result["min_packages"] = max(1, min_packages)  # At least 1 package

    # Calculate total cost if cost data is available
    if result["cost_available"]:
        # Total cost = packages * quantity_per_package * cost_per_unit
        actual_quantity = Decimal(str(result["min_packages"])) * Decimal(
            str(product.package_unit_quantity)
        )
        result["total_cost"] = actual_quantity * result["cost_per_package_unit"]

        # Calculate cost per recipe unit
        # Need conversion factor: how many recipe_units per package_unit
        success, conversion_factor, _ = convert_any_units(
            1.0,
            product.package_unit,
            recipe_unit,
            ingredient=ingredient,
        )

        if success and conversion_factor > 0:
            result["cost_per_recipe_unit"] = result["cost_per_package_unit"] / Decimal(
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
    """Get product recommendation(s) for an ingredient shortfall.

    This function determines which product(s) to recommend for purchasing
    to cover an ingredient shortfall. It handles three scenarios:
    - Preferred product exists: return that as the recommendation
    - Multiple products, none preferred: return all products for user choice
    - No products configured: return status indicating this

    Args:
        ingredient_slug: Slug identifier for the ingredient
        shortfall: Amount needed in recipe units
        recipe_unit: Unit used in recipes (e.g., "cup", "oz")

    Returns:
        Dict containing:
            - product_status: 'preferred' | 'multiple' | 'none' | 'sufficient'
            - product_recommendation: Primary recommendation dict (or None)
            - all_products: List of all product recommendations
            - message: Optional status message

    Raises:
        IngredientNotFoundBySlug: If ingredient_slug doesn't exist

    Example:
        >>> rec = get_product_recommendation("all_purpose_flour", Decimal("5"), "cup")
        >>> rec['product_status']
        'preferred'
        >>> rec['product_recommendation']['brand']
        'King Arthur'
    """
    # Handle zero or negative shortfall
    if shortfall <= 0:
        return {
            "product_status": "sufficient",
            "product_recommendation": None,
            "all_products": [],
            "message": "Sufficient stock",
        }

    # Get ingredient (will raise IngredientNotFoundBySlug if not found)
    try:
        ingredient = get_ingredient(ingredient_slug)
    except IngredientNotFoundBySlug:
        return {
            "product_status": "none",
            "product_recommendation": None,
            "all_products": [],
            "message": "Ingredient not found",
        }

    # Get all products for ingredient
    products = get_products_for_ingredient(ingredient_slug)

    if not products:
        return {
            "product_status": "none",
            "product_recommendation": None,
            "all_products": [],
            "message": "No product configured",
        }

    # Calculate cost metrics for all products
    all_recommendations = []
    for p in products:
        rec = _calculate_product_cost(p, shortfall, recipe_unit, ingredient)
        all_recommendations.append(rec)

    # Sort by total_cost (cheapest first, None values at end)
    def sort_key(r):
        if r.get("total_cost") is None:
            return (1, float("inf"))  # Put at end
        return (0, float(r["total_cost"]))

    all_recommendations.sort(key=sort_key)

    # Check for preferred product
    preferred = get_preferred_product(ingredient_slug)

    if preferred:
        # Find the recommendation for the preferred product
        preferred_rec = next(
            (r for r in all_recommendations if r["product_id"] == preferred.id),
            None,
        )
        return {
            "product_status": "preferred",
            "product_recommendation": preferred_rec,
            "all_products": [preferred_rec] if preferred_rec else [],
            "message": "",
        }
    else:
        # Multiple products, none preferred - return all for user choice
        return {
            "product_status": "multiple",
            "product_recommendation": None,
            "all_products": all_recommendations,
            "message": "",
        }
