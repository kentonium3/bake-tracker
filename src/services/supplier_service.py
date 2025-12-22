"""Supplier Service - CRUD operations for supplier management (Feature 027).

This module provides business logic for managing suppliers including
CRUD operations, soft delete (deactivate/reactivate), and supplier lookup.

All functions follow the session pattern per CLAUDE.md for transactional safety.

Key Features:
- Create/Read/Update suppliers with validation
- Soft delete via deactivate/reactivate (preserves purchase history)
- Hard delete only when no purchases exist
- Deactivate cascade clears product.preferred_supplier_id (FR-009)
- Active supplier filtering for dropdown population (FR-010)

Example Usage:
    >>> from src.services.supplier_service import create_supplier, get_supplier
    >>>
    >>> # Create a supplier
    >>> supplier = create_supplier(
    ...     name="Costco",
    ...     city="Issaquah",
    ...     state="WA",
    ...     zip_code="98027"
    ... )
    >>> supplier["name"]
    'Costco'
    >>>
    >>> # Get active suppliers for dropdown
    >>> suppliers = get_active_suppliers()
    >>> [s["name"] for s in suppliers]
    ['Costco', 'Wegmans']
"""

from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from src.models import Supplier, Product, Purchase
from src.services.database import session_scope
from src.services.exceptions import SupplierNotFoundError


def create_supplier(
    name: str,
    city: str,
    state: str,
    zip_code: str,
    street_address: Optional[str] = None,
    notes: Optional[str] = None,
    session: Optional[Session] = None,
) -> Dict[str, Any]:
    """Create a new supplier.

    Args:
        name: Supplier/store name (required)
        city: City (required)
        state: 2-letter state code (required, will be uppercased)
        zip_code: ZIP code (required)
        street_address: Street address (optional)
        notes: Additional notes (optional)
        session: Optional database session for transactional atomicity

    Returns:
        Dict[str, Any]: Created supplier as dictionary

    Raises:
        ValueError: If state is not a 2-letter code

    Example:
        >>> supplier = create_supplier(
        ...     name="Costco",
        ...     city="Issaquah",
        ...     state="wa",  # Will be uppercased
        ...     zip_code="98027"
        ... )
        >>> supplier["state"]
        'WA'
    """
    if session is not None:
        return _create_supplier_impl(name, city, state, zip_code, street_address, notes, session)
    with session_scope() as session:
        return _create_supplier_impl(name, city, state, zip_code, street_address, notes, session)


def _create_supplier_impl(
    name: str,
    city: str,
    state: str,
    zip_code: str,
    street_address: Optional[str],
    notes: Optional[str],
    session: Session,
) -> Dict[str, Any]:
    """Implementation of create_supplier."""
    # Validate and normalize state
    state = state.upper()
    if len(state) != 2:
        raise ValueError("State must be a 2-letter code")

    supplier = Supplier(
        name=name,
        city=city,
        state=state,
        zip_code=zip_code,
        street_address=street_address,
        notes=notes,
    )
    session.add(supplier)
    session.flush()
    return supplier.to_dict()


def get_supplier(supplier_id: int, session: Optional[Session] = None) -> Optional[Dict[str, Any]]:
    """Get supplier by ID.

    Args:
        supplier_id: Supplier ID
        session: Optional database session

    Returns:
        Dict[str, Any]: Supplier data as dictionary, or None if not found

    Example:
        >>> supplier = get_supplier(1)
        >>> supplier["name"] if supplier else "Not found"
        'Costco'
    """
    if session is not None:
        return _get_supplier_impl(supplier_id, session)
    with session_scope() as session:
        return _get_supplier_impl(supplier_id, session)


def _get_supplier_impl(supplier_id: int, session: Session) -> Optional[Dict[str, Any]]:
    """Implementation of get_supplier."""
    supplier = session.query(Supplier).filter(Supplier.id == supplier_id).first()
    return supplier.to_dict() if supplier else None


def get_supplier_by_uuid(uuid: str, session: Optional[Session] = None) -> Optional[Dict[str, Any]]:
    """Get supplier by UUID.

    Args:
        uuid: Supplier UUID (36-character string)
        session: Optional database session

    Returns:
        Dict[str, Any]: Supplier data as dictionary, or None if not found

    Example:
        >>> supplier = get_supplier_by_uuid("550e8400-e29b-41d4-a716-446655440000")
        >>> supplier["name"] if supplier else "Not found"
        'Costco'
    """
    if session is not None:
        return _get_supplier_by_uuid_impl(uuid, session)
    with session_scope() as session:
        return _get_supplier_by_uuid_impl(uuid, session)


def _get_supplier_by_uuid_impl(uuid: str, session: Session) -> Optional[Dict[str, Any]]:
    """Implementation of get_supplier_by_uuid."""
    supplier = session.query(Supplier).filter(Supplier.uuid == uuid).first()
    return supplier.to_dict() if supplier else None


def get_all_suppliers(
    include_inactive: bool = False,
    session: Optional[Session] = None,
) -> List[Dict[str, Any]]:
    """Get all suppliers, optionally including inactive.

    Args:
        include_inactive: If True, include deactivated suppliers (default: False)
        session: Optional database session

    Returns:
        List[Dict[str, Any]]: List of supplier dictionaries, sorted by name

    Example:
        >>> suppliers = get_all_suppliers()
        >>> len(suppliers)
        3
        >>> suppliers = get_all_suppliers(include_inactive=True)
        >>> len(suppliers)
        5
    """
    if session is not None:
        return _get_all_suppliers_impl(include_inactive, session)
    with session_scope() as session:
        return _get_all_suppliers_impl(include_inactive, session)


def _get_all_suppliers_impl(include_inactive: bool, session: Session) -> List[Dict[str, Any]]:
    """Implementation of get_all_suppliers."""
    query = session.query(Supplier)
    if not include_inactive:
        query = query.filter(Supplier.is_active == True)
    return [s.to_dict() for s in query.order_by(Supplier.name).all()]


def get_active_suppliers(session: Optional[Session] = None) -> List[Dict[str, Any]]:
    """Get active suppliers for dropdown population (FR-010).

    This is a convenience method that returns only active suppliers,
    intended for populating dropdown menus in the UI.

    Args:
        session: Optional database session

    Returns:
        List[Dict[str, Any]]: List of active supplier dictionaries, sorted by name

    Example:
        >>> suppliers = get_active_suppliers()
        >>> all(s["is_active"] for s in suppliers)
        True
    """
    return get_all_suppliers(include_inactive=False, session=session)


def update_supplier(
    supplier_id: int,
    session: Optional[Session] = None,
    **kwargs,
) -> Dict[str, Any]:
    """Update supplier attributes.

    Args:
        supplier_id: Supplier ID
        session: Optional database session
        **kwargs: Fields to update (name, city, state, zip_code, street_address, notes)

    Returns:
        Dict[str, Any]: Updated supplier as dictionary

    Raises:
        SupplierNotFoundError: If supplier not found
        ValueError: If state is invalid

    Example:
        >>> supplier = update_supplier(1, name="Costco Business Center")
        >>> supplier["name"]
        'Costco Business Center'
    """
    if session is not None:
        return _update_supplier_impl(supplier_id, session, **kwargs)
    with session_scope() as session:
        return _update_supplier_impl(supplier_id, session, **kwargs)


def _update_supplier_impl(supplier_id: int, session: Session, **kwargs) -> Dict[str, Any]:
    """Implementation of update_supplier."""
    supplier = session.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise SupplierNotFoundError(supplier_id)

    # Validate state if provided
    if "state" in kwargs:
        kwargs["state"] = kwargs["state"].upper()
        if len(kwargs["state"]) != 2:
            raise ValueError("State must be a 2-letter code")

    # Update allowed fields
    allowed_fields = {"name", "city", "state", "zip_code", "street_address", "notes"}
    for key, value in kwargs.items():
        if key in allowed_fields:
            setattr(supplier, key, value)

    session.flush()
    return supplier.to_dict()


def deactivate_supplier(
    supplier_id: int,
    session: Optional[Session] = None,
) -> Dict[str, Any]:
    """Deactivate supplier and clear preferred_supplier_id on affected products (FR-009).

    This implements soft delete for suppliers. When a supplier is deactivated:
    1. The supplier's is_active flag is set to False
    2. All products with this supplier as preferred_supplier have that reference cleared

    Args:
        supplier_id: Supplier ID
        session: Optional database session

    Returns:
        Dict[str, Any]: Deactivated supplier as dictionary

    Raises:
        SupplierNotFoundError: If supplier not found

    Example:
        >>> supplier = deactivate_supplier(1)
        >>> supplier["is_active"]
        False
    """
    if session is not None:
        return _deactivate_supplier_impl(supplier_id, session)
    with session_scope() as session:
        return _deactivate_supplier_impl(supplier_id, session)


def _deactivate_supplier_impl(supplier_id: int, session: Session) -> Dict[str, Any]:
    """Implementation of deactivate_supplier."""
    supplier = session.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise SupplierNotFoundError(supplier_id)

    supplier.is_active = False

    # FR-009: Clear preferred_supplier_id on products
    affected_products = session.query(Product).filter(
        Product.preferred_supplier_id == supplier_id
    ).all()
    for product in affected_products:
        product.preferred_supplier_id = None

    session.flush()
    return supplier.to_dict()


def reactivate_supplier(
    supplier_id: int,
    session: Optional[Session] = None,
) -> Dict[str, Any]:
    """Reactivate a previously deactivated supplier.

    Args:
        supplier_id: Supplier ID
        session: Optional database session

    Returns:
        Dict[str, Any]: Reactivated supplier as dictionary

    Raises:
        SupplierNotFoundError: If supplier not found

    Example:
        >>> supplier = reactivate_supplier(1)
        >>> supplier["is_active"]
        True
    """
    if session is not None:
        return _reactivate_supplier_impl(supplier_id, session)
    with session_scope() as session:
        return _reactivate_supplier_impl(supplier_id, session)


def _reactivate_supplier_impl(supplier_id: int, session: Session) -> Dict[str, Any]:
    """Implementation of reactivate_supplier."""
    supplier = session.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise SupplierNotFoundError(supplier_id)

    supplier.is_active = True
    session.flush()
    return supplier.to_dict()


def delete_supplier(
    supplier_id: int,
    session: Optional[Session] = None,
) -> bool:
    """Delete supplier if no purchases exist.

    Hard deletes a supplier only if they have no purchase history.
    If purchases exist, use deactivate_supplier() instead.

    Args:
        supplier_id: Supplier ID
        session: Optional database session

    Returns:
        bool: True if deleted successfully

    Raises:
        SupplierNotFoundError: If supplier not found
        ValueError: If supplier has purchases (cannot delete)

    Example:
        >>> delete_supplier(1)  # Supplier with no purchases
        True

        >>> delete_supplier(2)  # Supplier with purchases
        ValueError: Cannot delete supplier with 5 purchases. Deactivate instead.
    """
    if session is not None:
        return _delete_supplier_impl(supplier_id, session)
    with session_scope() as session:
        return _delete_supplier_impl(supplier_id, session)


def _delete_supplier_impl(supplier_id: int, session: Session) -> bool:
    """Implementation of delete_supplier."""
    supplier = session.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise SupplierNotFoundError(supplier_id)

    # Check for purchases
    purchase_count = session.query(Purchase).filter(
        Purchase.supplier_id == supplier_id
    ).count()

    if purchase_count > 0:
        raise ValueError(
            f"Cannot delete supplier with {purchase_count} purchases. Deactivate instead."
        )

    session.delete(supplier)
    session.flush()
    return True


def get_supplier_or_raise(
    supplier_id: int,
    session: Optional[Session] = None,
) -> Dict[str, Any]:
    """Get supplier by ID, raising SupplierNotFoundError if not found.

    Unlike get_supplier() which returns None for not found, this function
    raises an exception. Useful when supplier must exist.

    Args:
        supplier_id: Supplier ID
        session: Optional database session

    Returns:
        Dict[str, Any]: Supplier data as dictionary

    Raises:
        SupplierNotFoundError: If supplier not found

    Example:
        >>> supplier = get_supplier_or_raise(1)
        >>> supplier["name"]
        'Costco'

        >>> supplier = get_supplier_or_raise(999)
        SupplierNotFoundError: Supplier with ID 999 not found
    """
    result = get_supplier(supplier_id, session=session)
    if result is None:
        raise SupplierNotFoundError(supplier_id)
    return result
