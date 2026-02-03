"""
FK Resolver Service - Handles missing foreign key resolution during import.

This service provides a pluggable framework for resolving missing foreign keys
when importing data. It supports three resolution strategies:
- CREATE: Create a new entity with provided data
- MAP: Map to an existing entity by ID
- SKIP: Skip records that reference this missing FK

The service uses a callback protocol allowing CLI and UI to provide different
resolution UX while sharing the same underlying logic.

Usage:
    from src.services.fk_resolver_service import (
        resolve_missing_fks, find_similar_entities,
        MissingFK, Resolution, ResolutionChoice
    )

    # Define a resolver callback
    class MyResolver:
        def resolve(self, missing: MissingFK) -> Resolution:
            # Interactive resolution logic
            return Resolution(choice=ResolutionChoice.SKIP, ...)

    # Resolve all missing FKs
    mapping, resolutions = resolve_missing_fks(missing_fks, MyResolver(), session)
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple, Protocol, Any

from sqlalchemy.orm import Session

from src.services.database import session_scope
from src.models.supplier import Supplier
from src.models.ingredient import Ingredient
from src.models.product import Product
from src.services.supplier_service import generate_supplier_slug
from src.services.exceptions import ServiceError


# ============================================================================
# Exceptions
# ============================================================================


class FKResolutionError(ServiceError):
    """Raised when FK resolution fails due to validation or logic errors.

    HTTP Status: 400 Bad Request
    """

    http_status_code = 400


class EntityCreationError(FKResolutionError):
    """Raised when entity creation fails due to missing required fields.

    Args:
        entity_type: The entity type being created
        missing_fields: List of missing required fields
        correlation_id: Optional correlation ID for tracing

    HTTP Status: 400 Bad Request (validation error)
    """

    http_status_code = 400

    def __init__(
        self,
        entity_type: str,
        missing_fields: List[str],
        correlation_id: Optional[str] = None
    ):
        self.entity_type = entity_type
        self.missing_fields = missing_fields
        super().__init__(
            f"Cannot create {entity_type}: missing required fields: {', '.join(missing_fields)}",
            correlation_id=correlation_id,
            entity_type=entity_type,
            missing_fields=missing_fields
        )


# ============================================================================
# Enums and Data Classes
# ============================================================================


class ResolutionChoice(str, Enum):
    """User's choice for how to resolve a missing FK reference."""

    CREATE = "create"  # Create a new entity
    MAP = "map"  # Map to an existing entity
    SKIP = "skip"  # Skip records referencing this FK


@dataclass
class MissingFK:
    """
    Information about a missing foreign key reference.

    Attributes:
        entity_type: Type of the missing entity ("supplier", "ingredient", "product")
        missing_value: The slug/name that wasn't found in the database
        field_name: The field name in the import data (e.g., "supplier_name", "ingredient_slug")
        affected_record_count: Number of import records affected by this missing FK
        sample_records: First 3 affected records for context display
    """

    entity_type: str
    missing_value: str
    field_name: str
    affected_record_count: int
    sample_records: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class Resolution:
    """
    User's resolution for a missing FK.

    Attributes:
        choice: The resolution choice (CREATE, MAP, or SKIP)
        entity_type: Type of entity being resolved
        missing_value: The original missing value being resolved
        mapped_id: ID of existing entity (for MAP choice)
        created_entity: Entity data for creation (for CREATE choice)
    """

    choice: ResolutionChoice
    entity_type: str
    missing_value: str
    mapped_id: Optional[int] = None
    created_entity: Optional[Dict[str, Any]] = None


# ============================================================================
# Protocol Definition
# ============================================================================


class FKResolverCallback(Protocol):
    """
    Protocol for FK resolution callbacks.

    CLI and UI implement this protocol to provide different resolution UX.
    The CLI implementation prompts via text, the UI shows dialogs.
    """

    def resolve(self, missing: MissingFK) -> Resolution:
        """
        Called for each missing FK. Returns user's resolution choice.

        Args:
            missing: Information about the missing FK

        Returns:
            Resolution object with user's choice and any additional data
        """
        ...


# ============================================================================
# Entity Creation Functions
# ============================================================================


def _validate_required_fields(
    data: Dict[str, Any], required_fields: List[str], entity_type: str
) -> None:
    """
    Validate that all required fields are present in the data.

    Args:
        data: Entity data dictionary
        required_fields: List of required field names
        entity_type: Type of entity for error message

    Raises:
        EntityCreationError: If any required fields are missing
    """
    missing = [f for f in required_fields if not data.get(f)]
    if missing:
        raise EntityCreationError(entity_type, missing)


def _create_supplier(data: Dict[str, Any], session: Session) -> int:
    """
    Create a new Supplier entity.

    Args:
        data: Supplier data dictionary with fields:
            - name (required): Supplier name
            - city (required): City name
            - state (required): Two-letter state code
            - zip_code (required): ZIP code
            - street_address (optional): Street address
            - notes (optional): Additional notes

        session: SQLAlchemy session

    Returns:
        ID of the created supplier

    Raises:
        EntityCreationError: If required fields are missing
    """
    _validate_required_fields(data, ["name", "city", "state", "zip_code"], "supplier")

    # Normalize state to uppercase
    state = data["state"].upper() if data.get("state") else ""

    # Feature 050: Generate slug for supplier
    supplier_type = data.get("supplier_type", "physical")
    slug = generate_supplier_slug(
        name=data["name"],
        supplier_type=supplier_type,
        city=data["city"],
        state=state,
        session=session,
    )

    supplier = Supplier(
        name=data["name"],
        slug=slug,
        supplier_type=supplier_type,
        city=data["city"],
        state=state,
        zip_code=data["zip_code"],
        street_address=data.get("street_address"),
        notes=data.get("notes"),
        is_active=True,
    )
    session.add(supplier)
    session.flush()  # Get the ID
    return supplier.id


def _create_ingredient(data: Dict[str, Any], session: Session) -> int:
    """
    Create a new Ingredient entity.

    Args:
        data: Ingredient data dictionary with fields:
            - slug (required): URL-friendly identifier
            - display_name (required): Display name
            - category (required): Category name
            - description (optional): Description

        session: SQLAlchemy session

    Returns:
        ID of the created ingredient

    Raises:
        EntityCreationError: If required fields are missing
    """
    _validate_required_fields(data, ["slug", "display_name", "category"], "ingredient")

    ingredient = Ingredient(
        slug=data["slug"],
        display_name=data["display_name"],
        category=data["category"],
        description=data.get("description"),
    )
    session.add(ingredient)
    session.flush()  # Get the ID
    return ingredient.id


def _create_product(
    data: Dict[str, Any], session: Session, ingredient_id: Optional[int] = None
) -> int:
    """
    Create a new Product entity.

    Args:
        data: Product data dictionary with fields:
            - ingredient_slug (required if ingredient_id not provided): Ingredient slug
            - package_unit (required): Unit the package contains
            - package_unit_quantity (required): Quantity per package
            - brand (optional): Brand name
            - product_name (optional): Product variant name
            - package_size (optional): Size description
            - package_type (optional): Package type

        session: SQLAlchemy session
        ingredient_id: Optional ingredient ID (if already resolved)

    Returns:
        ID of the created product

    Raises:
        EntityCreationError: If required fields are missing
        FKResolutionError: If ingredient_slug cannot be resolved
    """
    _validate_required_fields(data, ["package_unit", "package_unit_quantity"], "product")

    # Resolve ingredient_id if not provided
    if ingredient_id is None:
        ingredient_slug = data.get("ingredient_slug")
        if not ingredient_slug:
            raise EntityCreationError("product", ["ingredient_slug or ingredient_id"])

        ingredient = session.query(Ingredient).filter(Ingredient.slug == ingredient_slug).first()
        if not ingredient:
            raise FKResolutionError(
                f"Cannot create product: ingredient '{ingredient_slug}' not found"
            )
        ingredient_id = ingredient.id

    product = Product(
        ingredient_id=ingredient_id,
        brand=data.get("brand"),
        product_name=data.get("product_name"),
        package_size=data.get("package_size"),
        package_type=data.get("package_type"),
        package_unit=data["package_unit"],
        package_unit_quantity=data["package_unit_quantity"],
        preferred=data.get("preferred", False),
    )
    session.add(product)
    session.flush()  # Get the ID
    return product.id


# ============================================================================
# Fuzzy Search Functions
# ============================================================================


def find_similar_entities(
    entity_type: str,
    search_value: str,
    session: Optional[Session] = None,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    """
    Find entities with similar names for mapping suggestions.

    Uses case-insensitive substring matching to find potential matches.

    Args:
        entity_type: Type of entity to search ("supplier", "ingredient", "product")
        search_value: Value to search for
        session: Optional SQLAlchemy session
        limit: Maximum number of results to return (default: 5)

    Returns:
        List of dictionaries with entity info for display
    """
    if session is not None:
        return _find_similar_entities_impl(entity_type, search_value, session, limit)
    with session_scope() as sess:
        return _find_similar_entities_impl(entity_type, search_value, sess, limit)


def _find_similar_entities_impl(
    entity_type: str,
    search_value: str,
    session: Session,
    limit: int,
) -> List[Dict[str, Any]]:
    """Internal implementation of find_similar_entities."""
    search_lower = search_value.lower()

    if entity_type == "supplier":
        matches = (
            session.query(Supplier)
            .filter(
                Supplier.is_active == True,  # noqa: E712
                Supplier.name.ilike(f"%{search_lower}%"),
            )
            .limit(limit)
            .all()
        )
        return [
            {
                "id": s.id,
                "name": s.name,
                "city": s.city,
                "state": s.state,
                "display": f"{s.name} ({s.city}, {s.state})",
            }
            for s in matches
        ]

    elif entity_type == "ingredient":
        matches = (
            session.query(Ingredient)
            .filter(
                Ingredient.display_name.ilike(f"%{search_lower}%")
                | Ingredient.slug.ilike(f"%{search_lower}%")
            )
            .limit(limit)
            .all()
        )
        return [
            {
                "id": i.id,
                "slug": i.slug,
                "display_name": i.display_name,
                "category": i.category,
                "display": f"{i.display_name} ({i.category})",
            }
            for i in matches
        ]

    elif entity_type == "product":
        # Product search is more complex - search by brand and ingredient display name
        matches = (
            session.query(Product)
            .join(Ingredient)
            .filter(
                Product.brand.ilike(f"%{search_lower}%")
                | Ingredient.display_name.ilike(f"%{search_lower}%")
            )
            .limit(limit)
            .all()
        )
        return [
            {
                "id": p.id,
                "brand": p.brand,
                "ingredient_slug": p.ingredient.slug,
                "package_unit": p.package_unit,
                "package_unit_quantity": p.package_unit_quantity,
                "display": p.display_name,
            }
            for p in matches
        ]

    return []


# ============================================================================
# Core Resolution Logic
# ============================================================================


# Dependency order for resolution (entities with no dependencies first)
ENTITY_DEPENDENCY_ORDER = ["supplier", "ingredient", "product"]


def resolve_missing_fks(
    missing_fks: List[MissingFK],
    resolver: FKResolverCallback,
    session: Optional[Session] = None,
) -> Tuple[Dict[str, Dict[str, int]], List[Resolution]]:
    """
    Resolve missing FKs in dependency order.

    Processes suppliers and ingredients first (no dependencies), then products
    (which may depend on ingredients).

    Args:
        missing_fks: List of missing FK references to resolve
        resolver: Callback implementing FKResolverCallback protocol
        session: Optional SQLAlchemy session for transactional composition

    Returns:
        Tuple of:
            - mapping: {entity_type: {missing_value: resolved_id}}
            - resolutions: List of all Resolution objects made
    """
    if session is not None:
        return _resolve_missing_fks_impl(missing_fks, resolver, session)
    with session_scope() as sess:
        return _resolve_missing_fks_impl(missing_fks, resolver, sess)


def _resolve_missing_fks_impl(
    missing_fks: List[MissingFK],
    resolver: FKResolverCallback,
    session: Session,
) -> Tuple[Dict[str, Dict[str, int]], List[Resolution]]:
    """Internal implementation of resolve_missing_fks."""
    # Initialize mapping structure
    mapping: Dict[str, Dict[str, int]] = {
        "supplier": {},
        "ingredient": {},
        "product": {},
    }
    resolutions: List[Resolution] = []

    # Sort missing FKs by dependency order
    def sort_key(missing: MissingFK) -> int:
        try:
            return ENTITY_DEPENDENCY_ORDER.index(missing.entity_type)
        except ValueError:
            return len(ENTITY_DEPENDENCY_ORDER)  # Unknown types go last

    sorted_missing = sorted(missing_fks, key=sort_key)

    # Process each missing FK
    for missing in sorted_missing:
        resolution = resolver.resolve(missing)
        resolutions.append(resolution)

        if resolution.choice == ResolutionChoice.CREATE:
            # Create the entity and store the ID
            entity_id = _apply_create_resolution(resolution, session, mapping)
            if entity_id is not None:
                mapping[resolution.entity_type][resolution.missing_value] = entity_id

        elif resolution.choice == ResolutionChoice.MAP:
            # Store the mapped ID
            if resolution.mapped_id is not None:
                mapping[resolution.entity_type][resolution.missing_value] = resolution.mapped_id

        # SKIP: No mapping entry - records will be skipped during import

    return mapping, resolutions


def _apply_create_resolution(
    resolution: Resolution,
    session: Session,
    mapping: Dict[str, Dict[str, int]],
) -> Optional[int]:
    """
    Apply a CREATE resolution by creating the entity.

    Args:
        resolution: Resolution with CREATE choice and created_entity data
        session: SQLAlchemy session
        mapping: Current FK mapping (for resolving dependencies)

    Returns:
        ID of created entity, or None if creation failed
    """
    if not resolution.created_entity:
        return None

    entity_type = resolution.entity_type
    data = resolution.created_entity

    if entity_type == "supplier":
        return _create_supplier(data, session)

    elif entity_type == "ingredient":
        return _create_ingredient(data, session)

    elif entity_type == "product":
        # Check if we have a resolved ingredient_id from earlier resolutions
        ingredient_slug = data.get("ingredient_slug")
        ingredient_id = None
        if ingredient_slug and ingredient_slug in mapping.get("ingredient", {}):
            ingredient_id = mapping["ingredient"][ingredient_slug]
        return _create_product(data, session, ingredient_id)

    return None


# ============================================================================
# Utility Functions
# ============================================================================


def collect_missing_fks(
    records: List[Dict[str, Any]],
    entity_type: str,
    fk_fields: Dict[str, str],
    session: Optional[Session] = None,
) -> List[MissingFK]:
    """
    Scan records to collect missing FK references.

    Args:
        records: List of import records to scan
        entity_type: Type of entity in the records (for context)
        fk_fields: Mapping of field_name -> target_entity_type
                   e.g., {"supplier_name": "supplier", "ingredient_slug": "ingredient"}
        session: Optional SQLAlchemy session

    Returns:
        List of MissingFK objects for all missing references
    """
    if session is not None:
        return _collect_missing_fks_impl(records, entity_type, fk_fields, session)
    with session_scope() as sess:
        return _collect_missing_fks_impl(records, entity_type, fk_fields, sess)


def _collect_missing_fks_impl(
    records: List[Dict[str, Any]],
    entity_type: str,
    fk_fields: Dict[str, str],
    session: Session,
) -> List[MissingFK]:
    """Internal implementation of collect_missing_fks."""
    # Build lookup sets for each target entity type
    existing: Dict[str, set] = {}

    for field_name, target_type in fk_fields.items():
        if target_type not in existing:
            if target_type == "supplier":
                # Feature 050: Collect both slugs and names for supplier matching
                # (Import records may use either slug or name in supplier_name field)
                supplier_values = set()
                for s in (
                    session.query(Supplier.slug, Supplier.name)
                    .filter(Supplier.is_active == True)  # noqa: E712
                    .all()
                ):
                    if s.slug:
                        supplier_values.add(s.slug)
                    if s.name:
                        supplier_values.add(s.name)
                existing["supplier"] = supplier_values
            elif target_type == "ingredient":
                existing["ingredient"] = {
                    i.slug
                    for i in session.query(Ingredient.slug)
                    .filter(Ingredient.slug.isnot(None))
                    .all()
                }
            elif target_type == "product":
                # Products are matched by composite key - more complex
                # For now, we track by a composite string
                existing["product"] = set()
                for p in session.query(Product).all():
                    key = (
                        f"{p.ingredient.slug}|{p.brand}|{p.package_unit_quantity}|{p.package_unit}"
                    )
                    existing["product"].add(key)

    # Collect missing values
    missing_map: Dict[Tuple[str, str, str], List[Dict[str, Any]]] = {}

    for record in records:
        for field_name, target_type in fk_fields.items():
            value = record.get(field_name)
            if not value:
                continue

            # Check if value exists
            is_missing = False
            if target_type == "supplier":
                is_missing = value not in existing.get("supplier", set())
            elif target_type == "ingredient":
                is_missing = value not in existing.get("ingredient", set())
            elif target_type == "product":
                # For products, we'd need to build the composite key
                # This is simplified for now
                is_missing = False  # Products require more context

            if is_missing:
                key = (target_type, value, field_name)
                if key not in missing_map:
                    missing_map[key] = []
                if len(missing_map[key]) < 3:  # Keep max 3 samples
                    missing_map[key].append(record)

    # Build MissingFK objects
    result = []
    for (target_type, value, field_name), samples in missing_map.items():
        # Count all affected records
        count = sum(1 for r in records if r.get(field_name) == value)

        result.append(
            MissingFK(
                entity_type=target_type,
                missing_value=value,
                field_name=field_name,
                affected_record_count=count,
                sample_records=samples,
            )
        )

    return result
