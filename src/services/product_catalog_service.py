"""Product Catalog Service - Catalog management for Feature 027.

This module provides business logic for product catalog management including:
- Product listing with filters and search (FR-014 through FR-018)
- Hide/unhide products for soft delete (FR-003)
- Purchase history retrieval (FR-012)
- Purchase creation (FR-011)
- Delete with dependency checking (FR-004, FR-005)

All functions follow the session pattern per CLAUDE.md for transactional safety.

Example Usage:
    >>> from src.services.product_catalog_service import get_products, hide_product
    >>>
    >>> # Get all visible products
    >>> products = get_products()
    >>> [p["product_name"] for p in products]
    ['King Arthur Flour 25lb', 'Costco Butter 4pk']
    >>>
    >>> # Hide a product (soft delete)
    >>> hidden = hide_product(1)
    >>> hidden["is_hidden"]
    True
"""

import logging
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import date
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func

from src.models import Product, Purchase, Ingredient, InventoryItem, Supplier, RecipeIngredient
from src.services.database import session_scope
from src.services.exceptions import ProductNotFound, ValidationError, NonLeafIngredientError

logger = logging.getLogger(__name__)


def get_products(
    include_hidden: bool = False,
    ingredient_id: Optional[int] = None,
    category: Optional[str] = None,
    supplier_id: Optional[int] = None,
    search: Optional[str] = None,
    session: Optional[Session] = None,
) -> List[Dict[str, Any]]:
    """Get products with optional filters and last purchase price.

    Transaction boundary: Read-only operation.

    Args:
        include_hidden: If True, include hidden products (default: False) (FR-018)
        ingredient_id: Filter by ingredient ID (FR-014)
        category: Filter by ingredient category (FR-015)
        supplier_id: Filter by preferred supplier ID (FR-016)
        search: Search term for product name (FR-017)
        session: Optional database session

    Returns:
        List[Dict[str, Any]]: Products with last_price and last_purchase_date enriched

    Example:
        >>> products = get_products(category="Flour")
        >>> len(products)
        5
        >>> products[0]["last_price"]
        '12.99'
    """
    if session is not None:
        return _get_products_impl(
            include_hidden, ingredient_id, category, supplier_id, search, session
        )
    with session_scope() as session:
        return _get_products_impl(
            include_hidden, ingredient_id, category, supplier_id, search, session
        )


def _get_products_impl(
    include_hidden: bool,
    ingredient_id: Optional[int],
    category: Optional[str],
    supplier_id: Optional[int],
    search: Optional[str],
    session: Session,
) -> List[Dict[str, Any]]:
    """Implementation of get_products.

    Transaction boundary: Inherits session from caller.
    """
    query = session.query(Product)

    # Filter hidden (FR-018)
    if not include_hidden:
        query = query.filter(Product.is_hidden == False)

    # Filter by ingredient (FR-014)
    if ingredient_id is not None:
        query = query.filter(Product.ingredient_id == ingredient_id)

    # Filter by category via ingredient (FR-015)
    if category:
        query = query.join(Ingredient).filter(Ingredient.category == category)

    # Filter by preferred supplier (FR-016)
    if supplier_id is not None:
        query = query.filter(Product.preferred_supplier_id == supplier_id)

    # Search by name (FR-017)
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Product.product_name.ilike(search_term)) | (Product.brand.ilike(search_term))
        )

    products = query.order_by(Product.product_name).all()

    # Enrich with last price and relationship data
    result = []
    for p in products:
        data = p.to_dict()
        last_purchase = _get_last_purchase(p.id, session)
        data["last_price"] = (
            float(last_purchase["unit_price"])
            if last_purchase and last_purchase["unit_price"] is not None
            else None
        )
        data["last_purchase_date"] = last_purchase["purchase_date"] if last_purchase else None

        # Enrich with ingredient info
        if p.ingredient:
            data["ingredient_name"] = p.ingredient.display_name
            data["category"] = p.ingredient.category
        else:
            data["ingredient_name"] = None
            data["category"] = None

        # Enrich with preferred supplier info
        if p.preferred_supplier:
            data["preferred_supplier_name"] = p.preferred_supplier.display_name
        else:
            data["preferred_supplier_name"] = None

        result.append(data)
    return result


def get_product_with_last_price(
    product_id: int,
    session: Optional[Session] = None,
) -> Optional[Dict[str, Any]]:
    """Get product by ID with last purchase price.

    Transaction boundary: Read-only operation.

    Args:
        product_id: Product ID
        session: Optional database session

    Returns:
        Dict[str, Any]: Product data with last_price and last_purchase_date, or None if not found

    Example:
        >>> product = get_product_with_last_price(1)
        >>> product["product_name"]
        'King Arthur Flour 25lb'
        >>> product["last_price"]
        '12.99'
    """
    if session is not None:
        return _get_product_with_last_price_impl(product_id, session)
    with session_scope() as session:
        return _get_product_with_last_price_impl(product_id, session)


def _get_product_with_last_price_impl(
    product_id: int, session: Session
) -> Optional[Dict[str, Any]]:
    """Implementation of get_product_with_last_price.

    Transaction boundary: Inherits session from caller.
    """
    product = session.query(Product).filter(Product.id == product_id).first()
    if not product:
        return None
    data = product.to_dict()
    last_purchase = _get_last_purchase(product_id, session)
    data["last_price"] = (
        float(last_purchase["unit_price"])
        if last_purchase and last_purchase["unit_price"] is not None
        else None
    )
    data["last_purchase_date"] = last_purchase["purchase_date"] if last_purchase else None

    # Enrich with ingredient info
    if product.ingredient:
        data["ingredient_name"] = product.ingredient.display_name
        data["category"] = product.ingredient.category
    else:
        data["ingredient_name"] = None
        data["category"] = None

    # Enrich with preferred supplier info
    if product.preferred_supplier:
        data["preferred_supplier_name"] = product.preferred_supplier.display_name
    else:
        data["preferred_supplier_name"] = None

    return data


def _get_last_purchase(product_id: int, session: Session) -> Optional[Dict[str, Any]]:
    """Internal helper to get most recent purchase for a product."""
    purchase = (
        session.query(Purchase)
        .filter(Purchase.product_id == product_id)
        .order_by(Purchase.purchase_date.desc())
        .first()
    )
    return purchase.to_dict() if purchase else None


def create_product(
    product_name: str,
    ingredient_id: int,
    package_unit: str,
    package_unit_quantity: float,
    preferred_supplier_id: Optional[int] = None,
    brand: Optional[str] = None,
    package_type: Optional[str] = None,
    gtin: Optional[str] = None,
    upc_code: Optional[str] = None,
    session: Optional[Session] = None,
) -> Dict[str, Any]:
    """Create a new product (FR-001, FR-002).

    Transaction boundary: Multi-step operation (atomic).
    Steps executed atomically:
    1. Validate leaf-only constraint (hierarchy_level == 2)
    2. Validate GTIN uniqueness (if provided)
    3. Validate UPC uniqueness (if provided)
    4. Create Product record

    CRITICAL: If session parameter is provided, caller maintains transactional
    control. All validation and creation steps share the same session.

    Args:
        product_name: Product name/description
        ingredient_id: ID of the parent ingredient
        package_unit: Unit the package contains (e.g., "lb", "oz")
        package_unit_quantity: Quantity per package
        preferred_supplier_id: Optional preferred supplier ID
        brand: Optional brand name
        package_type: Optional package type (e.g., "bag", "can", "jar")
        gtin: Optional GS1 GTIN barcode
        upc_code: Optional UPC barcode
        session: Optional database session

    Returns:
        Dict[str, Any]: Created product as dictionary

    Example:
        >>> product = create_product(
        ...     product_name="King Arthur Flour 25lb",
        ...     ingredient_id=1,
        ...     package_unit="lb",
        ...     package_unit_quantity=25.0,
        ...     brand="King Arthur"
        ... )
        >>> product["is_hidden"]
        False
    """
    if session is not None:
        return _create_product_impl(
            product_name,
            ingredient_id,
            package_unit,
            package_unit_quantity,
            preferred_supplier_id,
            brand,
            package_type,
            gtin,
            upc_code,
            session,
        )
    with session_scope() as session:
        return _create_product_impl(
            product_name,
            ingredient_id,
            package_unit,
            package_unit_quantity,
            preferred_supplier_id,
            brand,
            package_type,
            gtin,
            upc_code,
            session,
        )


def _create_product_impl(
    product_name: str,
    ingredient_id: int,
    package_unit: str,
    package_unit_quantity: float,
    preferred_supplier_id: Optional[int],
    brand: Optional[str],
    package_type: Optional[str],
    gtin: Optional[str],
    upc_code: Optional[str],
    session: Session,
) -> Dict[str, Any]:
    """Implementation of create_product.

    Transaction boundary: Inherits session from caller.
    """
    # Feature 031: Validate leaf-only constraint
    ingredient = session.query(Ingredient).filter(Ingredient.id == ingredient_id).first()
    if ingredient and ingredient.hierarchy_level != 2:
        # Get leaf suggestions from descendants
        from src.services import ingredient_hierarchy_service

        suggestions = []
        try:
            descendants = ingredient_hierarchy_service.get_leaf_ingredients(
                parent_id=ingredient_id, session=session
            )
            suggestions = [d["display_name"] for d in descendants[:3]]
        except Exception:
            pass

        raise NonLeafIngredientError(
            ingredient_id=ingredient_id,
            ingredient_name=ingredient.display_name if ingredient else f"ID {ingredient_id}",
            usage_context="product",
            suggestions=suggestions,
        )

    # Validate GTIN uniqueness
    if gtin:
        duplicate = session.query(Product).filter(Product.gtin == gtin).first()
        if duplicate:
            raise ValidationError(
                [
                    f"GTIN {gtin} is already used by product '{duplicate.brand}' "
                    f"(ID: {duplicate.id}). GTINs must be unique."
                ]
            )

    # Validate UPC uniqueness
    if upc_code:
        duplicate = session.query(Product).filter(Product.upc_code == upc_code).first()
        if duplicate:
            raise ValidationError(
                [
                    f"UPC {upc_code} is already used by product '{duplicate.brand}' "
                    f"(ID: {duplicate.id}). UPCs must be unique."
                ]
            )

    product = Product(
        product_name=product_name,
        ingredient_id=ingredient_id,
        package_type=package_type,
        package_unit=package_unit,
        package_unit_quantity=package_unit_quantity,
        preferred_supplier_id=preferred_supplier_id,
        brand=brand,
        gtin=gtin,
        upc_code=upc_code,
        is_hidden=False,
    )
    session.add(product)
    session.flush()
    return product.to_dict()


def update_product(
    product_id: int,
    session: Optional[Session] = None,
    **kwargs,
) -> Dict[str, Any]:
    """Update product attributes.

    Transaction boundary: Multi-step operation (atomic).
    Steps executed atomically:
    1. Validate product exists
    2. Validate GTIN uniqueness (if changing, excluding self)
    3. Validate UPC uniqueness (if changing, excluding self)
    4. Validate leaf-only constraint if ingredient_id is changing
    5. Update allowed fields

    CRITICAL: If session parameter is provided, caller maintains transactional
    control. All validation and update steps share the same session.

    Args:
        product_id: Product ID
        session: Optional database session
        **kwargs: Fields to update (product_name, ingredient_id, package_unit,
                  package_unit_quantity, preferred_supplier_id, brand)

    Returns:
        Dict[str, Any]: Updated product as dictionary

    Raises:
        ProductNotFound: If product not found

    Example:
        >>> product = update_product(1, brand="New Brand")
        >>> product["brand"]
        'New Brand'
    """
    if session is not None:
        return _update_product_impl(product_id, session, **kwargs)
    with session_scope() as session:
        return _update_product_impl(product_id, session, **kwargs)


def _update_product_impl(product_id: int, session: Session, **kwargs) -> Dict[str, Any]:
    """Implementation of update_product.

    Transaction boundary: Inherits session from caller.
    """
    product = session.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise ProductNotFound(product_id)

    # Validate GTIN uniqueness (excluding current product)
    new_gtin = kwargs.get("gtin")
    if new_gtin:  # Only check if GTIN is being set to a non-empty value
        duplicate = (
            session.query(Product)
            .filter(Product.gtin == new_gtin, Product.id != product_id)  # Exclude current product
            .first()
        )
        if duplicate:
            raise ValidationError(
                [
                    f"GTIN {new_gtin} is already used by product '{duplicate.brand}' "
                    f"(ID: {duplicate.id}). GTINs must be unique."
                ]
            )

    # Validate UPC uniqueness (excluding current product) - same pattern
    new_upc = kwargs.get("upc_code")
    if new_upc:  # Only check if UPC is being set to a non-empty value
        duplicate = (
            session.query(Product)
            .filter(
                Product.upc_code == new_upc, Product.id != product_id  # Exclude current product
            )
            .first()
        )
        if duplicate:
            raise ValidationError(
                [
                    f"UPC {new_upc} is already used by product '{duplicate.brand}' "
                    f"(ID: {duplicate.id}). UPCs must be unique."
                ]
            )

    # Feature 031: Validate leaf-only constraint if ingredient_id is being changed
    new_ingredient_id = kwargs.get("ingredient_id")
    if new_ingredient_id is not None and new_ingredient_id != product.ingredient_id:
        ingredient = session.query(Ingredient).filter(Ingredient.id == new_ingredient_id).first()
        if ingredient and ingredient.hierarchy_level != 2:
            from src.services import ingredient_hierarchy_service

            suggestions = []
            try:
                descendants = ingredient_hierarchy_service.get_leaf_ingredients(
                    parent_id=new_ingredient_id, session=session
                )
                suggestions = [d["display_name"] for d in descendants[:3]]
            except Exception:
                pass

            raise NonLeafIngredientError(
                ingredient_id=new_ingredient_id,
                ingredient_name=ingredient.display_name,
                usage_context="product",
                suggestions=suggestions,
            )

    allowed_fields = {
        "product_name",
        "ingredient_id",
        "package_type",
        "package_unit",
        "package_unit_quantity",
        "preferred_supplier_id",
        "brand",
        "gtin",
        "upc_code",
    }
    for key, value in kwargs.items():
        if key in allowed_fields:
            setattr(product, key, value)

    session.flush()
    return product.to_dict()


def hide_product(
    product_id: int,
    session: Optional[Session] = None,
) -> Dict[str, Any]:
    """Hide product (soft delete) (FR-003).

    Transaction boundary: Single-step write. Automatically atomic.

    Args:
        product_id: Product ID
        session: Optional database session

    Returns:
        Dict[str, Any]: Updated product with is_hidden=True

    Raises:
        ProductNotFound: If product not found

    Example:
        >>> product = hide_product(1)
        >>> product["is_hidden"]
        True
    """
    if session is not None:
        return _hide_product_impl(product_id, session)
    with session_scope() as session:
        return _hide_product_impl(product_id, session)


def _hide_product_impl(product_id: int, session: Session) -> Dict[str, Any]:
    """Implementation of hide_product.

    Transaction boundary: Inherits session from caller.
    """
    product = session.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise ProductNotFound(product_id)

    product.is_hidden = True
    session.flush()
    return product.to_dict()


def unhide_product(
    product_id: int,
    session: Optional[Session] = None,
) -> Dict[str, Any]:
    """Unhide product (restore) (FR-003).

    Transaction boundary: Single-step write. Automatically atomic.

    Args:
        product_id: Product ID
        session: Optional database session

    Returns:
        Dict[str, Any]: Updated product with is_hidden=False

    Raises:
        ProductNotFound: If product not found

    Example:
        >>> product = unhide_product(1)
        >>> product["is_hidden"]
        False
    """
    if session is not None:
        return _unhide_product_impl(product_id, session)
    with session_scope() as session:
        return _unhide_product_impl(product_id, session)


def _unhide_product_impl(product_id: int, session: Session) -> Dict[str, Any]:
    """Implementation of unhide_product.

    Transaction boundary: Inherits session from caller.
    """
    product = session.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise ProductNotFound(product_id)

    product.is_hidden = False
    session.flush()
    return product.to_dict()


def delete_product(
    product_id: int,
    session: Optional[Session] = None,
) -> bool:
    """Delete product if no purchases or inventory exist (FR-004, FR-005).

    Transaction boundary: Multi-step operation (atomic).
    Steps executed atomically:
    1. Validate product exists
    2. Check for purchase dependencies
    3. Check for inventory item dependencies
    4. Delete product if no dependencies

    CRITICAL: If session parameter is provided, caller maintains transactional
    control. All validation and deletion steps share the same session.

    Args:
        product_id: Product ID
        session: Optional database session

    Returns:
        bool: True if deleted successfully

    Raises:
        ProductNotFound: If product not found
        ValueError: If product has purchases or inventory items

    Example:
        >>> delete_product(1)  # Product with no dependencies
        True

        >>> delete_product(2)  # Product with purchases
        ValueError: Cannot delete product with 5 purchases. Hide instead.
    """
    if session is not None:
        return _delete_product_impl(product_id, session)
    with session_scope() as session:
        return _delete_product_impl(product_id, session)


def _delete_product_impl(product_id: int, session: Session) -> bool:
    """Implementation of delete_product.

    Transaction boundary: Inherits session from caller.
    """
    product = session.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise ProductNotFound(product_id)

    # Check for purchases (FR-004)
    purchase_count = session.query(Purchase).filter(Purchase.product_id == product_id).count()
    if purchase_count > 0:
        raise ValueError(f"Cannot delete product with {purchase_count} purchases. Hide instead.")

    # Check for inventory items (FR-005)
    inventory_count = (
        session.query(InventoryItem).filter(InventoryItem.product_id == product_id).count()
    )
    if inventory_count > 0:
        raise ValueError(
            f"Cannot delete product with {inventory_count} inventory items. Hide instead."
        )

    session.delete(product)
    session.flush()
    return True


def get_purchase_history(
    product_id: int,
    session: Optional[Session] = None,
) -> List[Dict[str, Any]]:
    """Get purchase history for product, sorted by date DESC (FR-012).

    Transaction boundary: Read-only operation.

    Args:
        product_id: Product ID
        session: Optional database session

    Returns:
        List[Dict[str, Any]]: Purchase records with supplier info

    Example:
        >>> history = get_purchase_history(1)
        >>> len(history)
        5
        >>> history[0]["supplier_name"]
        'Costco'
    """
    if session is not None:
        return _get_purchase_history_impl(product_id, session)
    with session_scope() as session:
        return _get_purchase_history_impl(product_id, session)


def _get_purchase_history_impl(product_id: int, session: Session) -> List[Dict[str, Any]]:
    """Implementation of get_purchase_history.

    Transaction boundary: Inherits session from caller.
    """
    purchases = (
        session.query(Purchase)
        .filter(Purchase.product_id == product_id)
        .order_by(Purchase.purchase_date.desc())
        .all()
    )

    result = []
    for p in purchases:
        data = p.to_dict()
        # Include supplier name for display
        if p.supplier:
            data["supplier_name"] = p.supplier.name
            data["supplier_location"] = f"{p.supplier.city}, {p.supplier.state}"
        result.append(data)
    return result


def create_purchase(
    product_id: int,
    supplier_id: int,
    purchase_date: date,
    unit_price: Decimal,
    quantity_purchased: int,
    notes: Optional[str] = None,
    session: Optional[Session] = None,
) -> Dict[str, Any]:
    """Create a purchase record (FR-011).

    Transaction boundary: Single-step write. Automatically atomic.

    Args:
        product_id: Product ID
        supplier_id: Supplier ID
        purchase_date: Date of purchase
        unit_price: Price per unit
        quantity_purchased: Number of units purchased
        notes: Optional notes
        session: Optional database session

    Returns:
        Dict[str, Any]: Created purchase as dictionary

    Raises:
        ValueError: If unit_price is negative or quantity is not positive

    Example:
        >>> purchase = create_purchase(
        ...     product_id=1,
        ...     supplier_id=1,
        ...     purchase_date=date.today(),
        ...     unit_price=Decimal("12.99"),
        ...     quantity_purchased=2
        ... )
        >>> purchase["total_cost"]
        '25.98'
    """
    if session is not None:
        return _create_purchase_impl(
            product_id, supplier_id, purchase_date, unit_price, quantity_purchased, notes, session
        )
    with session_scope() as session:
        return _create_purchase_impl(
            product_id, supplier_id, purchase_date, unit_price, quantity_purchased, notes, session
        )


def _create_purchase_impl(
    product_id: int,
    supplier_id: int,
    purchase_date: date,
    unit_price: Decimal,
    quantity_purchased: int,
    notes: Optional[str],
    session: Session,
) -> Dict[str, Any]:
    """Implementation of create_purchase.

    Transaction boundary: Inherits session from caller.
    """
    if unit_price < 0:
        raise ValueError("Unit price cannot be negative")
    if quantity_purchased <= 0:
        raise ValueError("Quantity must be positive")

    purchase = Purchase(
        product_id=product_id,
        supplier_id=supplier_id,
        purchase_date=purchase_date,
        unit_price=unit_price,
        quantity_purchased=quantity_purchased,
        notes=notes,
    )
    session.add(purchase)
    session.flush()
    return purchase.to_dict()


def get_products_by_category(
    category: str,
    include_hidden: bool = False,
    session: Optional[Session] = None,
) -> List[Dict[str, Any]]:
    """Get products by ingredient category (convenience method).

    Transaction boundary: Read-only operation. Delegates to get_products().

    Args:
        category: Ingredient category to filter by
        include_hidden: If True, include hidden products (default: False)
        session: Optional database session

    Returns:
        List[Dict[str, Any]]: Products in the specified category

    Example:
        >>> products = get_products_by_category("Flour")
        >>> len(products)
        5
    """
    return get_products(category=category, include_hidden=include_hidden, session=session)


def get_product_or_raise(
    product_id: int,
    session: Optional[Session] = None,
) -> Dict[str, Any]:
    """Get product by ID, raising ProductNotFound if not found.

    Transaction boundary: Read-only operation. Delegates to get_product_with_last_price().

    Args:
        product_id: Product ID
        session: Optional database session

    Returns:
        Dict[str, Any]: Product data

    Raises:
        ProductNotFound: If product not found

    Example:
        >>> product = get_product_or_raise(1)
        >>> product["product_name"]
        'King Arthur Flour 25lb'
    """
    result = get_product_with_last_price(product_id, session=session)
    if result is None:
        raise ProductNotFound(product_id)
    return result


# ============================================================================
# Force Delete with Dependency Analysis
# ============================================================================


@dataclass
class ProductDependencies:
    """Analysis of product dependencies for deletion safety check.

    This dataclass provides detailed information about what would be deleted
    if a product is force-deleted, and whether deletion should be blocked.

    Attributes:
        product_id: The product ID being analyzed
        product_name: Product display name
        brand: Product brand (or "Unknown")
        purchase_count: Number of purchase records
        inventory_count: Number of inventory items
        recipe_count: Number of recipes using this product's ingredient
        purchases: List of purchase details
        inventory_items: List of inventory item details
        recipes: List of recipe names using the ingredient
        has_valid_purchases: True if any purchase has price > 0
        has_supplier_data: True if any purchase has supplier info
        is_used_in_recipes: True if the product's ingredient is used in recipes
    """

    product_id: int
    product_name: str
    brand: str

    # Counts
    purchase_count: int
    inventory_count: int
    recipe_count: int

    # Details
    purchases: List[Dict[str, Any]] = field(default_factory=list)
    inventory_items: List[Dict[str, Any]] = field(default_factory=list)
    recipes: List[str] = field(default_factory=list)

    # Safety flags
    has_valid_purchases: bool = False
    has_supplier_data: bool = False
    is_used_in_recipes: bool = False

    @property
    def can_force_delete(self) -> bool:
        """Can only force delete if NOT used in recipes."""
        return not self.is_used_in_recipes

    @property
    def deletion_risk_level(self) -> str:
        """Risk level: LOW, MEDIUM, or BLOCKED.

        BLOCKED: Product's ingredient is used in recipes
        MEDIUM: Has valid purchase data (price > 0) or supplier info
        LOW: No valuable data to lose
        """
        if self.is_used_in_recipes:
            return "BLOCKED"
        if self.has_valid_purchases or self.has_supplier_data:
            return "MEDIUM"
        return "LOW"


def analyze_product_dependencies(
    product_id: int,
    session: Optional[Session] = None,
) -> ProductDependencies:
    """Analyze what will be deleted if product is force-deleted.

    Transaction boundary: Read-only operation.

    This function examines all dependencies of a product to help the user
    understand what data will be lost if they proceed with force deletion.

    Note: Recipe blocking is based on whether the product's INGREDIENT is
    used in recipes (since recipes are brand-agnostic).

    Args:
        product_id: Product ID to analyze
        session: Optional database session

    Returns:
        ProductDependencies: Detailed dependency information

    Raises:
        ProductNotFound: If product doesn't exist

    Example:
        >>> deps = analyze_product_dependencies(1)
        >>> deps.can_force_delete
        False  # If ingredient is used in recipes
        >>> deps.deletion_risk_level
        'BLOCKED'
    """
    if session is not None:
        return _analyze_product_dependencies_impl(product_id, session)
    with session_scope() as session:
        return _analyze_product_dependencies_impl(product_id, session)


def _analyze_product_dependencies_impl(
    product_id: int,
    session: Session,
) -> ProductDependencies:
    """Implementation of analyze_product_dependencies.

    Transaction boundary: Inherits session from caller.
    """
    product = session.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise ProductNotFound(product_id)

    # Get all purchases
    purchases = session.query(Purchase).filter(Purchase.product_id == product_id).all()

    purchase_details = []
    for p in purchases:
        purchase_details.append(
            {
                "id": p.id,
                "date": str(p.purchase_date) if p.purchase_date else None,
                "supplier": p.supplier.name if p.supplier else None,
                "price": float(p.unit_price or 0),
                "quantity": int(p.quantity_purchased or 0),
            }
        )

    # Get inventory items
    inventory = session.query(InventoryItem).filter(InventoryItem.product_id == product_id).all()

    inventory_details = []
    for i in inventory:
        inventory_details.append(
            {
                "id": i.id,
                "qty": float(i.quantity or 0),
                "location": i.location,
            }
        )

    # Get recipes using this product's INGREDIENT
    # (Recipes are brand-agnostic, so we check if the ingredient is used)
    recipe_ingredients = (
        session.query(RecipeIngredient)
        .filter(RecipeIngredient.ingredient_id == product.ingredient_id)
        .all()
    )

    recipe_names = []
    for ri in recipe_ingredients:
        if ri.recipe:
            recipe_names.append(ri.recipe.name)

    # Analyze data quality
    has_valid_purchases = any(p["price"] > 0 for p in purchase_details)
    has_supplier_data = any(p["supplier"] for p in purchase_details)

    return ProductDependencies(
        product_id=product_id,
        product_name=product.product_name or product.display_name,
        brand=product.brand or "Unknown",
        purchase_count=len(purchases),
        inventory_count=len(inventory),
        recipe_count=len(recipe_names),
        purchases=purchase_details,
        inventory_items=inventory_details,
        recipes=recipe_names,
        has_valid_purchases=has_valid_purchases,
        has_supplier_data=has_supplier_data,
        is_used_in_recipes=bool(recipe_names),
    )


def force_delete_product(
    product_id: int,
    confirmed: bool = False,
    session: Optional[Session] = None,
) -> ProductDependencies:
    """Force delete a product and all dependent data.

    Transaction boundary: Multi-step operation (atomic).
    Steps executed atomically:
    1. Analyze dependencies via _analyze_product_dependencies_impl()
    2. Check if ingredient is used in recipes (BLOCKING check)
    3. Validate confirmed=True
    4. Delete inventory items
    5. Delete purchases
    6. Delete product

    CRITICAL: All deletion steps share the same session. Deletions happen
    in FK-constraint order (inventory items -> purchases -> product).
    If session parameter is provided, caller maintains transactional control.

    CRITICAL: Cannot delete products whose ingredient is used in recipes.
    Recipes are brand-agnostic, so this checks ingredient usage.

    WARNING: This permanently deletes:
    - Purchase records
    - Inventory items
    - The product itself

    Args:
        product_id: Product to delete
        confirmed: Must be True to actually delete (safety check)
        session: Optional database session

    Returns:
        ProductDependencies: Object showing what was deleted

    Raises:
        ProductNotFound: If product doesn't exist
        ValueError: If confirmed=False (must confirm deletion)
        ValueError: If product's ingredient is used in recipes

    Example:
        >>> # First analyze to show user
        >>> deps = analyze_product_dependencies(1)
        >>> if deps.can_force_delete:
        ...     deps = force_delete_product(1, confirmed=True)
        ...     print(f"Deleted {deps.purchase_count} purchases")
    """
    if session is not None:
        return _force_delete_product_impl(product_id, confirmed, session)
    with session_scope() as session:
        return _force_delete_product_impl(product_id, confirmed, session)


def _force_delete_product_impl(
    product_id: int,
    confirmed: bool,
    session: Session,
) -> ProductDependencies:
    """Implementation of force_delete_product.

    Transaction boundary: Inherits session from caller.
    """
    # Analyze dependencies first
    deps = _analyze_product_dependencies_impl(product_id, session)

    # CRITICAL CHECK: Cannot delete if ingredient is used in recipes
    if deps.is_used_in_recipes:
        recipe_list = ", ".join(deps.recipes[:5])
        if len(deps.recipes) > 5:
            recipe_list += f", ... ({len(deps.recipes) - 5} more)"
        raise ValueError(
            f"Cannot delete product - its ingredient is used in {deps.recipe_count} recipe(s): "
            f"{recipe_list}. Remove ingredient from recipes first, or use hide_product() instead."
        )

    if not confirmed:
        raise ValueError(
            "Force delete requires confirmed=True. "
            "User must confirm deletion after seeing dependencies."
        )

    # Delete in correct order (respect FK constraints)
    # 1. Delete inventory items first (may reference purchases)
    deleted_inventory = (
        session.query(InventoryItem)
        .filter(InventoryItem.product_id == product_id)
        .delete(synchronize_session=False)
    )

    # 2. Delete purchases
    deleted_purchases = (
        session.query(Purchase)
        .filter(Purchase.product_id == product_id)
        .delete(synchronize_session=False)
    )

    # 3. Delete the product itself
    session.query(Product).filter(Product.id == product_id).delete(synchronize_session=False)

    session.flush()

    logger.warning(
        f"FORCE DELETED product {product_id}: {deps.brand} {deps.product_name} "
        f"({deleted_purchases} purchases, {deleted_inventory} inventory items)"
    )

    return deps


# ============================================================================
# F057: Provisional Product Support
# ============================================================================


def get_provisional_products(
    session: Optional[Session] = None,
) -> List[Dict[str, Any]]:
    """Get all products where is_provisional=True.

    Transaction boundary: Read-only operation.

    Returns products that were created during purchase entry and need
    review to complete their information.

    Args:
        session: Optional database session

    Returns:
        List[Dict[str, Any]]: Provisional products with enriched data
            (same format as get_products())

    Example:
        >>> products = get_provisional_products()
        >>> len(products)
        3
        >>> products[0]["is_provisional"]
        True
    """
    if session is not None:
        return _get_provisional_products_impl(session)
    with session_scope() as session:
        return _get_provisional_products_impl(session)


def _get_provisional_products_impl(session: Session) -> List[Dict[str, Any]]:
    """Implementation of get_provisional_products.

    Transaction boundary: Inherits session from caller.
    """
    query = (
        session.query(Product)
        .filter(
            Product.is_provisional == True,
            Product.is_hidden == False,
        )
        .order_by(Product.date_added.desc())
    )  # Most recent first

    products = query.all()

    # Enrich with same data as _get_products_impl
    result = []
    for p in products:
        data = p.to_dict()
        last_purchase = _get_last_purchase(p.id, session)
        data["last_price"] = (
            float(last_purchase["unit_price"])
            if last_purchase and last_purchase["unit_price"] is not None
            else None
        )
        data["last_purchase_date"] = last_purchase["purchase_date"] if last_purchase else None

        # Enrich with ingredient info
        if p.ingredient:
            data["ingredient_name"] = p.ingredient.display_name
            data["category"] = p.ingredient.category
        else:
            data["ingredient_name"] = None
            data["category"] = None

        # Enrich with preferred supplier info
        if p.preferred_supplier:
            data["preferred_supplier_name"] = p.preferred_supplier.display_name
        else:
            data["preferred_supplier_name"] = None

        result.append(data)
    return result


def get_provisional_count(
    session: Optional[Session] = None,
) -> int:
    """Get count of provisional products for badge display.

    Transaction boundary: Read-only operation.

    Efficient count-only query for UI badge that shows number of
    products needing review.

    Args:
        session: Optional database session

    Returns:
        int: Count of products where is_provisional=True

    Example:
        >>> count = get_provisional_count()
        >>> count
        3
    """
    if session is not None:
        return _get_provisional_count_impl(session)
    with session_scope() as session:
        return _get_provisional_count_impl(session)


def _get_provisional_count_impl(session: Session) -> int:
    """Implementation of get_provisional_count.

    Transaction boundary: Inherits session from caller.
    """
    return (
        session.query(func.count(Product.id))
        .filter(
            Product.is_provisional == True,
            Product.is_hidden == False,
        )
        .scalar()
        or 0
    )


def mark_product_reviewed(
    product_id: int,
    session: Optional[Session] = None,
) -> Dict[str, Any]:
    """Clear is_provisional flag after user completes product details.

    Transaction boundary: Single-step write. Automatically atomic.

    Marks a provisional product as reviewed, removing it from the
    review queue. Does not validate that all fields are complete -
    user decides when product info is sufficient.

    Args:
        product_id: Product ID to mark as reviewed
        session: Optional database session

    Returns:
        Dict[str, Any]: Updated product as dictionary

    Raises:
        ProductNotFound: If product_id doesn't exist

    Example:
        >>> product = mark_product_reviewed(123)
        >>> product["is_provisional"]
        False
    """
    if session is not None:
        return _mark_product_reviewed_impl(product_id, session)
    with session_scope() as session:
        return _mark_product_reviewed_impl(product_id, session)


def _mark_product_reviewed_impl(product_id: int, session: Session) -> Dict[str, Any]:
    """Implementation of mark_product_reviewed.

    Transaction boundary: Inherits session from caller.
    """
    product = session.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise ProductNotFound(product_id)

    product.is_provisional = False
    session.flush()
    return product.to_dict()
