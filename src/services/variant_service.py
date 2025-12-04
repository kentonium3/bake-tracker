"""Variant Service - Brand/package variant management.

This module provides business logic for managing brand-specific product variants
for ingredients, including preferred variant toggling, UPC tracking, and dependency
checking.

All functions are stateless and use session_scope() for transaction management.

Key Features:
- Brand and package size tracking
- Preferred variant toggle (atomic - only one preferred per ingredient)
- UPC/GTIN barcode support for future scanning
- Display name auto-calculation from brand + package size
- Dependency checking before deletion
- Supplier tracking for shopping recommendations

Example Usage:
  >>> from src.services.variant_service import create_variant, set_preferred_variant
  >>> from decimal import Decimal
  >>>
  >>> # Create a variant
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
  >>>
  >>> # Set preferred variant (atomic toggle)
  >>> set_preferred_variant(variant.id)
"""

from typing import Dict, Any, List, Optional
from decimal import Decimal

from ..models import Variant
from .database import session_scope
from .exceptions import (
    VariantNotFound,
    VariantInUse,
    IngredientNotFoundBySlug,
    ValidationError as ServiceValidationError,
    DatabaseError,
)
from .ingredient_service import get_ingredient
from ..utils.validators import validate_variant_data
from sqlalchemy.orm import joinedload


def create_variant(ingredient_slug: str, variant_data: Dict[str, Any]) -> Variant:
    """Create a new variant for an ingredient.

    If preferred=True, this function will automatically set all other variants
    for this ingredient to preferred=False (atomic operation).

    Args:
        ingredient_slug: Slug of parent ingredient
        variant_data: Dictionary containing:
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
        Variant: Created variant object with auto-calculated display_name

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
        >>> variant.preferred
        True
    """
    # Validate ingredient exists
    ingredient = get_ingredient(ingredient_slug)

    # Validate variant data
    is_valid, errors = validate_variant_data(variant_data, ingredient_slug)
    if not is_valid:
        raise ServiceValidationError(errors)

    try:
        with session_scope() as session:
            # If preferred=True, clear all other variants for this ingredient
            if variant_data.get("preferred", False):
                session.query(Variant).filter_by(ingredient_id=ingredient.id).update(
                    {"preferred": False}
                )

            # Create variant instance
            variant = Variant(
                ingredient_id=ingredient.id,
                brand=variant_data["brand"],
                package_size=variant_data.get("package_size"),
                purchase_unit=variant_data["purchase_unit"],
                purchase_quantity=variant_data["purchase_quantity"],
                upc_code=variant_data.get("upc"),
                gtin=variant_data.get("gtin"),
                supplier=variant_data.get("supplier"),
                preferred=variant_data.get("preferred", False),
                net_content_value=variant_data.get("net_content_value"),
                net_content_uom=variant_data.get("net_content_uom"),
            )

            session.add(variant)
            session.flush()  # Get ID before commit

            return variant

    except IngredientNotFoundBySlug:
        raise
    except ServiceValidationError:
        raise
    except Exception as e:
        raise DatabaseError(f"Failed to create variant", original_error=e)


def get_variant(variant_id: int) -> Variant:
    """Retrieve variant by ID.

    Args:
        variant_id: Variant identifier

    Returns:
        Variant: Variant object with ingredient relationship eager-loaded

    Raises:
        VariantNotFound: If variant_id doesn't exist

    Example:
        >>> variant = get_variant(123)
        >>> variant.brand
        'King Arthur'
        >>> variant.ingredient.name
        'All-Purpose Flour'
    """
    with session_scope() as session:
        variant = (
            session.query(Variant)
            .options(
                joinedload(Variant.ingredient),
                joinedload(Variant.purchases),
                joinedload(Variant.pantry_items),
            )
            .filter_by(id=variant_id)
            .first()
        )

        if not variant:
            raise VariantNotFound(variant_id)

        return variant


def get_variants_for_ingredient(ingredient_slug: str) -> List[Variant]:
    """Retrieve all variants for an ingredient, sorted with preferred first.

    Args:
        ingredient_slug: Ingredient identifier

    Returns:
        List[Variant]: All variants for ingredient, preferred variant first, then by brand

    Raises:
        IngredientNotFoundBySlug: If ingredient_slug doesn't exist

    Example:
        >>> variants = get_variants_for_ingredient("all_purpose_flour")
        >>> variants[0].preferred
        True
        >>> [v.brand for v in variants]
        ['King Arthur', "Bob's Red Mill", 'Store Brand']
    """
    # Validate ingredient exists
    ingredient = get_ingredient(ingredient_slug)

    with session_scope() as session:
        return (
            session.query(Variant)
            .options(
                joinedload(Variant.ingredient),
                joinedload(Variant.purchases),
                joinedload(Variant.pantry_items),
            )
            .filter_by(ingredient_id=ingredient.id)
            .order_by(
                Variant.preferred.desc(),  # Preferred first
                Variant.brand,  # Then alphabetical by brand
            )
            .all()
        )


def set_preferred_variant(variant_id: int) -> Variant:
    """Mark variant as preferred, clearing preferred flag on all other variants for same ingredient.

    This function ensures atomicity: all variants for the ingredient are set to
    preferred=False, then the specified variant is set to preferred=True, all
    within a single transaction.

    Args:
        variant_id: ID of variant to mark as preferred

    Returns:
        Variant: Updated variant with preferred=True

    Raises:
        VariantNotFound: If variant_id doesn't exist
        DatabaseError: If database operation fails

    Note:
        This function ensures only one variant per ingredient is marked preferred.
        All other variants for the same ingredient will have preferred=False.

    Example:
        >>> variant = set_preferred_variant(456)
        >>> variant.preferred
        True
        >>> # All other variants for this ingredient now have preferred=False
    """
    # Get variant to find ingredient_slug
    variant = get_variant(variant_id)

    try:
        with session_scope() as session:
            # Atomic operation: UPDATE all to False, then SET one to True
            session.query(Variant).filter_by(ingredient_id=variant.ingredient_id).update(
                {"preferred": False}
            )

            # Set this variant to preferred
            variant_to_update = (
                session.query(Variant)
                .options(
                    joinedload(Variant.ingredient),
                    joinedload(Variant.purchases),
                    joinedload(Variant.pantry_items),
                )
                .get(variant_id)
            )
            variant_to_update.preferred = True

            return variant_to_update

    except VariantNotFound:
        raise
    except Exception as e:
        raise DatabaseError(f"Failed to set preferred variant {variant_id}", original_error=e)


def update_variant(variant_id: int, variant_data: Dict[str, Any]) -> Variant:
    """Update variant attributes.

    Args:
        variant_id: Variant identifier
        variant_data: Dictionary with fields to update (partial update supported)
            - brand (str, optional): New brand
            - package_size (str, optional): New package size
            - purchase_unit (str, optional): New purchase unit
            - purchase_quantity (Decimal, optional): New purchase quantity
            - upc, gtin, supplier (optional): Update identification/sourcing
            - preferred (bool, optional): Change preferred status
            - net_content_value, net_content_uom (optional): Industry fields

    Returns:
        Variant: Updated variant object

    Raises:
        VariantNotFound: If variant_id doesn't exist
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
    if "ingredient_id" in variant_data:
        raise ServiceValidationError("Ingredient cannot be changed after variant creation")

    try:
        with session_scope() as session:
            # Get existing variant
            variant = (
                session.query(Variant)
                .options(
                    joinedload(Variant.ingredient),
                    joinedload(Variant.purchases),
                    joinedload(Variant.pantry_items),
                )
                .filter_by(id=variant_id)
                .first()
            )
            if not variant:
                raise VariantNotFound(variant_id)

            # Update attributes
            for key, value in variant_data.items():
                if hasattr(variant, key):
                    setattr(variant, key, value)

            return variant

    except VariantNotFound:
        raise
    except ServiceValidationError:
        raise
    except Exception as e:
        raise DatabaseError(f"Failed to update variant {variant_id}", original_error=e)


def delete_variant(variant_id: int) -> bool:
    """Delete variant if not referenced by pantry items or purchases.

    Args:
        variant_id: Variant identifier

    Returns:
        bool: True if deletion successful

    Raises:
        VariantNotFound: If variant_id doesn't exist
        VariantInUse: If variant has dependencies (pantry items, purchases)
        DatabaseError: If database operation fails

    Example:
        >>> delete_variant(789)
        True

        >>> delete_variant(123)  # Has pantry items
        Traceback (most recent call last):
        ...
        VariantInUse: Cannot delete variant 123: used in 12 pantry_items, 25 purchases
    """
    # Check dependencies first
    deps = check_variant_dependencies(variant_id)

    if any(deps.values()):
        raise VariantInUse(variant_id, deps)

    try:
        with session_scope() as session:
            variant = session.query(Variant).filter_by(id=variant_id).first()
            if not variant:
                raise VariantNotFound(variant_id)

            session.delete(variant)
            return True

    except VariantNotFound:
        raise
    except VariantInUse:
        raise
    except Exception as e:
        raise DatabaseError(f"Failed to delete variant {variant_id}", original_error=e)


def check_variant_dependencies(variant_id: int) -> Dict[str, int]:
    """Check if variant is referenced by other entities.

    Args:
        variant_id: Variant identifier

    Returns:
        Dict[str, int]: Dependency counts
            - "pantry_items": Number of pantry items using this variant
            - "purchases": Number of purchase records for this variant

    Raises:
        VariantNotFound: If variant_id doesn't exist

    Example:
        >>> deps = check_variant_dependencies(123)
        >>> deps
        {'pantry_items': 5, 'purchases': 12}
    """
    # Import models here to avoid circular dependencies
    # from ..models import PantryItem, Purchase

    # Verify variant exists
    variant = get_variant(variant_id)

    with session_scope() as session:
        # TODO: Implement when PantryItem model exists
        pantry_count = 0
        # pantry_count = session.query(PantryItem).filter_by(variant_id=variant_id).count()

        # TODO: Implement when Purchase model exists
        purchase_count = 0
        # purchase_count = session.query(Purchase).filter_by(variant_id=variant_id).count()

        return {"pantry_items": pantry_count, "purchases": purchase_count}


def search_variants_by_upc(upc: str) -> List[Variant]:
    """Search variants by UPC code (exact match).

    Args:
        upc: Universal Product Code (12-14 digits)

    Returns:
        List[Variant]: Matching variants (may be multiple if same UPC across suppliers)

    Example:
        >>> variants = search_variants_by_upc("012345678901")
        >>> len(variants)
        2  # Same product from different suppliers
        >>> [v.brand for v in variants]
        ['Costco Kirkland', 'Amazon Basics']
    """
    with session_scope() as session:
        return (
            session.query(Variant)
            .options(
                joinedload(Variant.ingredient),
                joinedload(Variant.purchases),
                joinedload(Variant.pantry_items),
            )
            .filter_by(upc=upc)
            .all()
        )


def get_preferred_variant(ingredient_slug: str) -> Optional[Variant]:
    """Get the preferred variant for an ingredient.

    Args:
        ingredient_slug: Ingredient identifier

    Returns:
        Optional[Variant]: Preferred variant, or None if no variant marked preferred

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
            session.query(Variant)
            .options(
                joinedload(Variant.ingredient),
                joinedload(Variant.purchases),
                joinedload(Variant.pantry_items),
            )
            .filter_by(ingredient_id=ingredient.id, preferred=True)
            .first()
        )
