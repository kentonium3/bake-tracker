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
from src.utils.slug_utils import create_slug_for_model, validate_slug_format


def generate_supplier_slug(
    name: str,
    supplier_type: str,
    city: Optional[str] = None,
    state: Optional[str] = None,
    session: Optional[Session] = None,
) -> str:
    """Generate slug for supplier based on type.

    Transaction boundary: Read-only operation (with optional uniqueness check).
    If session is provided, performs uniqueness check within existing transaction.

    Physical suppliers: {name}_{city}_{state} normalized
    Online suppliers: {name} only

    Uses Unicode normalization and conflict resolution matching existing
    Ingredient/Material patterns.

    Args:
        name: Supplier name (required)
        supplier_type: 'physical' or 'online'
        city: City name (used for physical suppliers)
        state: 2-letter state code (used for physical suppliers)
        session: Optional session for uniqueness checking

    Returns:
        Generated slug string

    Examples:
        >>> generate_supplier_slug("Wegmans", "physical", "Burlington", "MA")
        'wegmans_burlington_ma'

        >>> generate_supplier_slug("King Arthur Baking", "online")
        'king_arthur_baking'
    """
    if supplier_type == "online":
        input_string = name
    else:
        # Physical supplier: include location
        parts = [name]
        if city:
            parts.append(city)
        if state:
            parts.append(state)
        input_string = " ".join(parts)

    return create_slug_for_model(input_string, Supplier, session)


def validate_supplier_data(supplier_data: Dict[str, Any]) -> List[str]:
    """Validate supplier data before creation or import.

    Transaction boundary: Pure validation function. No database access required.

    This function validates supplier data, checking required fields and
    format constraints. Used during import operations to validate data
    before committing to the database.

    Args:
        supplier_data: Dictionary containing supplier fields

    Returns:
        List of validation error messages (empty if valid)

    Example:
        >>> errors = validate_supplier_data({"name": ""})
        >>> errors
        ['Supplier name is required']

        >>> errors = validate_supplier_data({"name": "Test", "slug": "INVALID SLUG"})
        >>> errors
        ['Invalid slug format: must be lowercase, alphanumeric with underscores']
    """
    errors = []

    # Name is required
    name = supplier_data.get("name")
    if not name or not str(name).strip():
        errors.append("Supplier name is required")

    # Slug is auto-generated, but if provided, validate format
    if "slug" in supplier_data and supplier_data["slug"]:
        if not validate_slug_format(supplier_data["slug"]):
            errors.append("Invalid slug format: must be lowercase, alphanumeric with underscores")

    # Validate supplier_type if provided
    supplier_type = supplier_data.get("supplier_type", "physical")
    if supplier_type not in ("physical", "online"):
        errors.append("supplier_type must be 'physical' or 'online'")

    # Validate state format if provided
    state = supplier_data.get("state")
    if state:
        if len(state) != 2:
            errors.append("State must be a 2-letter code")

    # Physical suppliers require city, state, zip_code
    if supplier_type == "physical":
        if not supplier_data.get("city"):
            errors.append("City is required for physical suppliers")
        if not supplier_data.get("state"):
            errors.append("State is required for physical suppliers")
        if not supplier_data.get("zip_code"):
            errors.append("ZIP code is required for physical suppliers")

    return errors


def create_supplier(
    name: str,
    city: Optional[str] = None,
    state: Optional[str] = None,
    zip_code: Optional[str] = None,
    street_address: Optional[str] = None,
    notes: Optional[str] = None,
    supplier_type: str = "physical",
    website_url: Optional[str] = None,
    session: Optional[Session] = None,
) -> Dict[str, Any]:
    """Create a new supplier.

    Transaction boundary: Multi-step operation (atomic).
    Steps executed atomically:
    1. Validate input fields (name, supplier_type, state format, URL format)
    2. Generate unique slug via generate_supplier_slug()
    3. Create Supplier record

    CRITICAL: All steps share the same session. If session parameter is
    provided, caller maintains transactional control.

    Supports two supplier types:
    - 'physical': Requires city, state, zip_code
    - 'online': Only requires name (website_url recommended)

    Args:
        name: Supplier/store name (required)
        city: City (required for physical, optional for online)
        state: 2-letter state code (required for physical, will be uppercased)
        zip_code: ZIP code (required for physical, optional for online)
        street_address: Street address (optional)
        notes: Additional notes (optional)
        supplier_type: 'physical' or 'online' (default: 'physical')
        website_url: Website URL (recommended for online vendors)
        session: Optional database session for transactional atomicity

    Returns:
        Dict[str, Any]: Created supplier as dictionary

    Raises:
        ValueError: If validation fails (missing required fields for type)

    Example:
        >>> # Physical store
        >>> supplier = create_supplier(
        ...     name="Costco",
        ...     city="Issaquah",
        ...     state="wa",
        ...     zip_code="98027"
        ... )
        >>> supplier["state"]
        'WA'

        >>> # Online vendor
        >>> supplier = create_supplier(
        ...     name="King Arthur Baking",
        ...     supplier_type="online",
        ...     website_url="https://www.kingarthurbaking.com"
        ... )
        >>> supplier["is_online"]
        True
    """
    if session is not None:
        return _create_supplier_impl(
            name, city, state, zip_code, street_address, notes, supplier_type, website_url, session
        )
    with session_scope() as session:
        return _create_supplier_impl(
            name, city, state, zip_code, street_address, notes, supplier_type, website_url, session
        )


def _create_supplier_impl(
    name: str,
    city: Optional[str],
    state: Optional[str],
    zip_code: Optional[str],
    street_address: Optional[str],
    notes: Optional[str],
    supplier_type: str,
    website_url: Optional[str],
    session: Session,
) -> Dict[str, Any]:
    """Implementation of create_supplier.

    Transaction boundary: Inherits session from caller.
    """
    # Validate name (service-layer validation so callers don't rely on DB errors)
    if name is None or not str(name).strip():
        raise ValueError("Name is required")
    name = str(name).strip()

    # Validate supplier_type
    if supplier_type not in ("physical", "online"):
        raise ValueError("supplier_type must be 'physical' or 'online'")

    # Validate based on type
    if supplier_type == "physical":
        if not city:
            raise ValueError("City is required for physical stores")
        if not state:
            raise ValueError("State is required for physical stores")
        if not zip_code:
            raise ValueError("ZIP code is required for physical stores")
        # Normalize state
        state = state.upper()
        if len(state) != 2:
            raise ValueError("State must be a 2-letter code")
    else:
        # Online vendor - normalize state if provided
        if state:
            state = state.upper()
            if len(state) != 2:
                raise ValueError("State must be a 2-letter code")

    # Validate URL format if provided
    if website_url and not website_url.startswith(("http://", "https://")):
        raise ValueError("Website URL must start with http:// or https://")

    # Generate unique slug based on supplier type
    slug = generate_supplier_slug(
        name=name,
        supplier_type=supplier_type,
        city=city,
        state=state,
        session=session,
    )

    supplier = Supplier(
        name=name,
        slug=slug,
        supplier_type=supplier_type,
        website_url=website_url,
        city=city,
        state=state,
        zip_code=zip_code,
        street_address=street_address,
        notes=notes,
    )
    session.add(supplier)
    session.flush()
    return supplier.to_dict()


def get_supplier(supplier_id: int, session: Optional[Session] = None) -> Dict[str, Any]:
    """Get supplier by ID.

    Transaction boundary: Read-only operation.

    Args:
        supplier_id: Supplier ID
        session: Optional database session

    Returns:
        Dict[str, Any]: Supplier data as dictionary

    Raises:
        SupplierNotFoundError: If supplier doesn't exist

    Example:
        >>> supplier = get_supplier(1)
        >>> supplier["name"]
        'Costco'
    """
    if session is not None:
        return _get_supplier_impl(supplier_id, session)
    with session_scope() as session:
        return _get_supplier_impl(supplier_id, session)


def _get_supplier_impl(supplier_id: int, session: Session) -> Dict[str, Any]:
    """Implementation of get_supplier.

    Transaction boundary: Inherits session from caller.
    """
    supplier = session.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise SupplierNotFoundError(supplier_id)
    return supplier.to_dict()


def get_supplier_by_uuid(uuid: str, session: Optional[Session] = None) -> Dict[str, Any]:
    """Get supplier by UUID.

    Transaction boundary: Read-only operation.

    Args:
        uuid: Supplier UUID (36-character string)
        session: Optional database session

    Returns:
        Dict[str, Any]: Supplier data as dictionary

    Raises:
        SupplierNotFoundError: If supplier doesn't exist

    Example:
        >>> supplier = get_supplier_by_uuid("550e8400-e29b-41d4-a716-446655440000")
        >>> supplier["name"]
        'Costco'
    """
    if session is not None:
        return _get_supplier_by_uuid_impl(uuid, session)
    with session_scope() as session:
        return _get_supplier_by_uuid_impl(uuid, session)


def _get_supplier_by_uuid_impl(uuid: str, session: Session) -> Dict[str, Any]:
    """Implementation of get_supplier_by_uuid.

    Transaction boundary: Inherits session from caller.
    """
    supplier = session.query(Supplier).filter(Supplier.uuid == uuid).first()
    if not supplier:
        raise SupplierNotFoundError(f"uuid:{uuid}")
    return supplier.to_dict()


def get_all_suppliers(
    include_inactive: bool = False,
    session: Optional[Session] = None,
) -> List[Dict[str, Any]]:
    """Get all suppliers, optionally including inactive.

    Transaction boundary: Read-only operation.

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
    """Implementation of get_all_suppliers.

    Transaction boundary: Inherits session from caller.
    """
    query = session.query(Supplier)
    if not include_inactive:
        query = query.filter(Supplier.is_active == True)
    return [s.to_dict() for s in query.order_by(Supplier.name).all()]


def get_active_suppliers(session: Optional[Session] = None) -> List[Dict[str, Any]]:
    """Get active suppliers for dropdown population (FR-010).

    Transaction boundary: Read-only operation. Delegates to get_all_suppliers().

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
    """Update supplier attributes. Slug is immutable and cannot be changed.

    Transaction boundary: Single-step write. Automatically atomic.

    Args:
        supplier_id: Supplier ID
        session: Optional database session
        **kwargs: Fields to update (name, city, state, zip_code, street_address,
            notes, supplier_type, website_url). Slug changes are rejected.

    Returns:
        Dict[str, Any]: Updated supplier as dictionary

    Raises:
        SupplierNotFoundError: If supplier not found
        ValueError: If state is invalid or attempting to modify slug

    Note:
        Slug is generated once at creation and NEVER regenerated, even if
        name/city/state changes. This preserves data portability for exports.

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
    """Implementation of update_supplier.

    Transaction boundary: Inherits session from caller.
    """
    supplier = session.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise SupplierNotFoundError(supplier_id)

    # Feature 050: Slug immutability enforcement
    # Slug is generated once at creation and NEVER regenerated,
    # even if name/city/state changes. This preserves data portability.
    if "slug" in kwargs:
        new_slug = kwargs["slug"]
        if new_slug != supplier.slug:
            raise ValueError(
                f"Slug cannot be modified after creation. "
                f"Current: '{supplier.slug}', Attempted: '{new_slug}'. "
                f"Slugs are immutable to preserve data portability."
            )
        # Remove slug from kwargs (even if same value - it's a no-op)
        kwargs = {k: v for k, v in kwargs.items() if k != "slug"}

    # Validate supplier_type if provided
    if "supplier_type" in kwargs:
        if kwargs["supplier_type"] not in ("physical", "online"):
            raise ValueError("supplier_type must be 'physical' or 'online'")

    # Validate state if provided
    if "state" in kwargs and kwargs["state"]:
        kwargs["state"] = kwargs["state"].upper()
        if len(kwargs["state"]) != 2:
            raise ValueError("State must be a 2-letter code")

    # Validate URL format if provided
    if "website_url" in kwargs and kwargs["website_url"]:
        if not kwargs["website_url"].startswith(("http://", "https://")):
            raise ValueError("Website URL must start with http:// or https://")

    # Determine effective supplier_type for validation
    new_type = kwargs.get("supplier_type", supplier.supplier_type)

    # Validate required fields for physical stores
    if new_type == "physical":
        # Check if we're clearing required fields
        new_city = kwargs.get("city", supplier.city)
        new_state = kwargs.get("state", supplier.state)
        new_zip = kwargs.get("zip_code", supplier.zip_code)

        if not new_city:
            raise ValueError("City is required for physical stores")
        if not new_state:
            raise ValueError("State is required for physical stores")
        if not new_zip:
            raise ValueError("ZIP code is required for physical stores")

    # Update allowed fields
    allowed_fields = {
        "name",
        "city",
        "state",
        "zip_code",
        "street_address",
        "notes",
        "supplier_type",
        "website_url",
    }
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

    Transaction boundary: Multi-step operation (atomic).
    Steps executed atomically:
    1. Validate supplier exists
    2. Set supplier's is_active flag to False
    3. Clear preferred_supplier_id on all affected products

    CRITICAL: All steps share the same session. If session parameter is
    provided, caller maintains transactional control.

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
    """Implementation of deactivate_supplier.

    Transaction boundary: Inherits session from caller.
    """
    supplier = session.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise SupplierNotFoundError(supplier_id)

    supplier.is_active = False

    # FR-009: Clear preferred_supplier_id on products
    affected_products = (
        session.query(Product).filter(Product.preferred_supplier_id == supplier_id).all()
    )
    for product in affected_products:
        product.preferred_supplier_id = None

    session.flush()
    return supplier.to_dict()


def reactivate_supplier(
    supplier_id: int,
    session: Optional[Session] = None,
) -> Dict[str, Any]:
    """Reactivate a previously deactivated supplier.

    Transaction boundary: Single-step write. Automatically atomic.

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
    """Implementation of reactivate_supplier.

    Transaction boundary: Inherits session from caller.
    """
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

    Transaction boundary: Multi-step operation (atomic).
    Steps executed atomically:
    1. Validate supplier exists
    2. Check for purchase dependencies
    3. Delete supplier if no dependencies

    CRITICAL: All steps share the same session. If session parameter is
    provided, caller maintains transactional control.

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
    """Implementation of delete_supplier.

    Transaction boundary: Inherits session from caller.
    """
    supplier = session.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise SupplierNotFoundError(supplier_id)

    # Check for purchases
    purchase_count = session.query(Purchase).filter(Purchase.supplier_id == supplier_id).count()

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

    DEPRECATED: Use get_supplier() instead - it now raises exceptions directly.

    This function is kept for backward compatibility but is now a simple alias
    for get_supplier().

    Transaction boundary: Read-only operation. Delegates to get_supplier().

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
    return get_supplier(supplier_id, session=session)


def get_or_create_supplier(
    name: str,
    city: str = "Unknown",
    state: str = "XX",
    zip_code: str = "00000",
    session: Optional[Session] = None,
) -> Supplier:
    """Get existing supplier by name or create with provided defaults.

    Transaction boundary: Single query + possible insert (atomic).
    If session provided, operates within caller's transaction for
    transactional composition. If session is None, creates own session_scope().

    This function is designed for use by purchase_service to centralize
    supplier lookup/creation logic that was previously inline.

    Args:
        name: Supplier name (required)
        city: City (default: "Unknown")
        state: State code (default: "XX")
        zip_code: ZIP code (default: "00000")
        session: Optional session for transactional composition

    Returns:
        Supplier: Existing or newly created supplier MODEL object

    Notes:
        - Defaults match legacy purchase service behavior for backward compatibility
        - Future: Will generate slug when TD-009 implemented
        - Lookup by name only (city/state not used for matching)
        - Returns Supplier MODEL (not dict) for direct .id access

    Example:
        >>> supplier = get_or_create_supplier("Costco", session=session)
        >>> supplier.id
        42

        >>> # With custom location
        >>> supplier = get_or_create_supplier(
        ...     name="Wegmans",
        ...     city="Burlington",
        ...     state="MA",
        ...     zip_code="01803",
        ...     session=session
        ... )
    """
    if session is not None:
        return _get_or_create_supplier_impl(name, city, state, zip_code, session)
    with session_scope() as sess:
        return _get_or_create_supplier_impl(name, city, state, zip_code, sess)


def _get_or_create_supplier_impl(
    name: str,
    city: str,
    state: str,
    zip_code: str,
    session: Session,
) -> Supplier:
    """Implementation of get_or_create_supplier.

    Transaction boundary: Inherits session from caller.
    This function MUST be called with an active session - it does not
    create its own session_scope().
    """
    # Try to find existing supplier by name
    supplier = session.query(Supplier).filter(Supplier.name == name).first()

    if supplier:
        return supplier

    # Create new supplier with defaults
    # Note: Not generating slug here - deferred to TD-009
    supplier = Supplier(
        name=name,
        city=city,
        state=state,
        zip_code=zip_code,
    )
    session.add(supplier)
    session.flush()  # Get ID for return
    return supplier


def migrate_supplier_slugs(
    session: Optional[Session] = None,
) -> Dict[str, Any]:
    """Generate slugs for all existing suppliers.

    Transaction boundary: Multi-step operation (atomic).
    Steps executed atomically:
    1. Query all suppliers ordered by ID
    2. For each supplier: generate base slug, check for conflicts, assign unique slug
    3. Flush all changes

    CRITICAL: All steps share the same session. This ensures slug uniqueness
    is maintained across the entire migration. If session parameter is
    provided, caller maintains transactional control.

    Per clarification (session 2026-01-12): ALL slugs are regenerated to
    enforce consistency, even if a supplier already has a slug. This ensures
    all slugs follow the standard pattern.

    The migration is idempotent - running it multiple times produces the
    same result (though slugs may change if supplier data changes).

    Args:
        session: Optional database session for transactional atomicity

    Returns:
        Dict with migration results:
            - migrated: Number of suppliers processed
            - conflicts: Number of slug conflicts resolved with suffixes
            - errors: List of error messages (if any)

    Example:
        >>> result = migrate_supplier_slugs()
        >>> result["migrated"]
        6
        >>> result["conflicts"]
        0

        >>> # With conflicting suppliers
        >>> result = migrate_supplier_slugs()
        >>> result["conflicts"]
        1  # One supplier needed _1 suffix
    """
    if session is not None:
        return _migrate_supplier_slugs_impl(session)
    with session_scope() as session:
        return _migrate_supplier_slugs_impl(session)


def _migrate_supplier_slugs_impl(session: Session) -> Dict[str, Any]:
    """Implementation of migrate_supplier_slugs.

    Transaction boundary: Inherits session from caller.
    """
    suppliers = session.query(Supplier).order_by(Supplier.id).all()
    migrated = 0
    conflicts = 0
    errors = []

    # Track slugs we've assigned in this migration to detect conflicts
    # within the same migration run
    assigned_slugs = set()

    for supplier in suppliers:
        try:
            # Generate the base slug (without uniqueness check)
            base_slug = generate_supplier_slug(
                name=supplier.name,
                supplier_type=supplier.supplier_type,
                city=supplier.city,
                state=supplier.state,
                session=None,  # No session = no uniqueness check
            )

            # Check if this base slug conflicts with one we've already assigned
            # in this migration run
            if base_slug in assigned_slugs:
                # Need to find a unique variant
                conflicts += 1
                counter = 1
                while True:
                    candidate_slug = f"{base_slug}_{counter}"
                    if candidate_slug not in assigned_slugs:
                        # Also check database for slugs assigned to other suppliers
                        # we haven't processed yet
                        existing = (
                            session.query(Supplier)
                            .filter(Supplier.slug == candidate_slug, Supplier.id != supplier.id)
                            .first()
                        )
                        if not existing:
                            supplier.slug = candidate_slug
                            assigned_slugs.add(candidate_slug)
                            break
                    counter += 1
                    if counter > 10000:
                        errors.append(
                            f"Could not generate unique slug for supplier {supplier.id}: {supplier.name}"
                        )
                        break
            else:
                # Check if another supplier (not yet migrated) has this slug
                existing = (
                    session.query(Supplier)
                    .filter(Supplier.slug == base_slug, Supplier.id != supplier.id)
                    .first()
                )
                if existing:
                    # The existing supplier will be re-slugged when we process it
                    # We can take this slug
                    pass
                supplier.slug = base_slug
                assigned_slugs.add(base_slug)

            migrated += 1

        except Exception as e:
            errors.append(f"Error migrating supplier {supplier.id}: {str(e)}")

    session.flush()

    return {
        "migrated": migrated,
        "conflicts": conflicts,
        "errors": errors,
    }
