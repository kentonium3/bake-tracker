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

from typing import Optional, List, Dict, Any
from datetime import date
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func

from src.models import Product, Purchase, Ingredient, InventoryItem, Supplier
from src.services.database import session_scope
from src.services.exceptions import ProductNotFound


def get_products(
    include_hidden: bool = False,
    ingredient_id: Optional[int] = None,
    category: Optional[str] = None,
    supplier_id: Optional[int] = None,
    search: Optional[str] = None,
    session: Optional[Session] = None,
) -> List[Dict[str, Any]]:
    """Get products with optional filters and last purchase price.

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
        return _get_products_impl(include_hidden, ingredient_id, category, supplier_id, search, session)
    with session_scope() as session:
        return _get_products_impl(include_hidden, ingredient_id, category, supplier_id, search, session)


def _get_products_impl(
    include_hidden: bool,
    ingredient_id: Optional[int],
    category: Optional[str],
    supplier_id: Optional[int],
    search: Optional[str],
    session: Session,
) -> List[Dict[str, Any]]:
    """Implementation of get_products."""
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
            (Product.product_name.ilike(search_term)) |
            (Product.brand.ilike(search_term))
        )

    products = query.order_by(Product.product_name).all()

    # Enrich with last price and relationship data
    result = []
    for p in products:
        data = p.to_dict()
        last_purchase = _get_last_purchase(p.id, session)
        data["last_price"] = str(last_purchase["unit_price"]) if last_purchase else None
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


def _get_product_with_last_price_impl(product_id: int, session: Session) -> Optional[Dict[str, Any]]:
    """Implementation of get_product_with_last_price."""
    product = session.query(Product).filter(Product.id == product_id).first()
    if not product:
        return None
    data = product.to_dict()
    last_purchase = _get_last_purchase(product_id, session)
    data["last_price"] = str(last_purchase["unit_price"]) if last_purchase else None
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
    purchase = session.query(Purchase).filter(
        Purchase.product_id == product_id
    ).order_by(Purchase.purchase_date.desc()).first()
    return purchase.to_dict() if purchase else None


def create_product(
    product_name: str,
    ingredient_id: int,
    package_unit: str,
    package_unit_quantity: float,
    preferred_supplier_id: Optional[int] = None,
    brand: Optional[str] = None,
    session: Optional[Session] = None,
) -> Dict[str, Any]:
    """Create a new product (FR-001, FR-002).

    Args:
        product_name: Product name/description
        ingredient_id: ID of the parent ingredient
        package_unit: Unit the package contains (e.g., "lb", "oz")
        package_unit_quantity: Quantity per package
        preferred_supplier_id: Optional preferred supplier ID
        brand: Optional brand name
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
            product_name, ingredient_id, package_unit, package_unit_quantity,
            preferred_supplier_id, brand, session
        )
    with session_scope() as session:
        return _create_product_impl(
            product_name, ingredient_id, package_unit, package_unit_quantity,
            preferred_supplier_id, brand, session
        )


def _create_product_impl(
    product_name: str,
    ingredient_id: int,
    package_unit: str,
    package_unit_quantity: float,
    preferred_supplier_id: Optional[int],
    brand: Optional[str],
    session: Session,
) -> Dict[str, Any]:
    """Implementation of create_product."""
    product = Product(
        product_name=product_name,
        ingredient_id=ingredient_id,
        package_unit=package_unit,
        package_unit_quantity=package_unit_quantity,
        preferred_supplier_id=preferred_supplier_id,
        brand=brand,
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
    """Implementation of update_product."""
    product = session.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise ProductNotFound(product_id)

    allowed_fields = {
        "product_name", "ingredient_id", "package_unit",
        "package_unit_quantity", "preferred_supplier_id", "brand"
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
    """Implementation of hide_product."""
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
    """Implementation of unhide_product."""
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
    """Implementation of delete_product."""
    product = session.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise ProductNotFound(product_id)

    # Check for purchases (FR-004)
    purchase_count = session.query(Purchase).filter(
        Purchase.product_id == product_id
    ).count()
    if purchase_count > 0:
        raise ValueError(
            f"Cannot delete product with {purchase_count} purchases. Hide instead."
        )

    # Check for inventory items (FR-005)
    inventory_count = session.query(InventoryItem).filter(
        InventoryItem.product_id == product_id
    ).count()
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
    """Implementation of get_purchase_history."""
    purchases = session.query(Purchase).filter(
        Purchase.product_id == product_id
    ).order_by(Purchase.purchase_date.desc()).all()

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
            product_id, supplier_id, purchase_date, unit_price,
            quantity_purchased, notes, session
        )
    with session_scope() as session:
        return _create_purchase_impl(
            product_id, supplier_id, purchase_date, unit_price,
            quantity_purchased, notes, session
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
    """Implementation of create_purchase."""
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
