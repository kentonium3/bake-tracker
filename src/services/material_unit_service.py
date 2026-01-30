"""Material Unit Service - MaterialUnit management and inventory calculations.

This module provides business logic for managing MaterialUnits and calculating
availability and costs. Part of Feature 047: Materials Management System.

Feature 084: MaterialUnits now belong to MaterialProduct (not Material).
- CRUD operations use material_product_id
- Slug uniqueness scoped to product
- Name uniqueness enforced per product

Key Features:
- MaterialUnit CRUD operations
- Available inventory from parent MaterialProduct
- Cost calculation from product's FIFO inventory
- Consumption preview without modifying inventory

All functions accept optional session parameter per CLAUDE.md session management rules.
"""

from typing import Optional, List, Dict, Any
from decimal import Decimal
import json
import math
import re
import unicodedata

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from ..models import (
    MaterialProduct,
    MaterialUnit,
    MaterialUnitSnapshot,
    Composition,
    MaterialInventoryItem,
)
from .database import session_scope
from .exceptions import ValidationError


# =============================================================================
# Custom Exceptions
# =============================================================================


class MaterialUnitNotFoundError(Exception):
    """Raised when a material unit is not found."""

    def __init__(self, unit_id: int):
        self.unit_id = unit_id
        super().__init__(f"Material unit not found: {unit_id}")


class MaterialProductNotFoundError(Exception):
    """Raised when a material product is not found."""

    def __init__(self, product_id: int):
        self.product_id = product_id
        super().__init__(f"Material product not found: {product_id}")


# Feature 084: Deprecated - no longer used
# class MaterialNotFoundError(Exception):
#     """Raised when a material is not found."""
#     pass


class MaterialUnitInUseError(Exception):
    """Raised when attempting to delete a unit that is in use."""

    def __init__(self, unit_id: int, usage_count: int, fg_names: List[str] = None):
        self.unit_id = unit_id
        self.usage_count = usage_count
        self.fg_names = fg_names or []
        if fg_names:
            super().__init__(
                f"MaterialUnit {unit_id} is used in {usage_count} composition(s): "
                f"{', '.join(set(fg_names))}"
            )
        else:
            super().__init__(f"MaterialUnit {unit_id} is used in {usage_count} composition(s)")


class SnapshotCreationError(Exception):
    """Raised when snapshot creation fails."""

    pass


# =============================================================================
# Slug Generation (Feature 084: hyphen style, scoped to product)
# =============================================================================


def _generate_material_unit_slug(name: str) -> str:
    """Generate URL-safe slug from name using hyphen style.

    Feature 084: Uses hyphen separators (not underscore) per research.md pattern.
    """
    if not name:
        return "unknown-unit"

    # Normalize unicode
    slug = unicodedata.normalize("NFKD", name)
    slug = slug.encode("ascii", "ignore").decode("ascii")
    slug = slug.lower()

    # Replace spaces and underscores with hyphens
    slug = re.sub(r"[\s_]+", "-", slug)

    # Remove non-alphanumeric except hyphens
    slug = re.sub(r"[^a-z0-9-]", "", slug)

    # Collapse multiple hyphens
    slug = re.sub(r"-+", "-", slug)

    # Strip leading/trailing hyphens
    slug = slug.strip("-")

    return slug if slug else "unknown-unit"


def _generate_unique_slug(
    name: str,
    session: Session,
    material_product_id: int,
    exclude_id: Optional[int] = None,
) -> str:
    """Generate unique slug within product scope.

    Feature 084: Slugs are unique within a MaterialProduct, not globally.
    Same slug can exist for different products.
    """
    base_slug = _generate_material_unit_slug(name)
    max_attempts = 1000

    for attempt in range(max_attempts):
        candidate = base_slug if attempt == 0 else f"{base_slug}-{attempt + 1}"

        query = session.query(MaterialUnit).filter(
            MaterialUnit.material_product_id == material_product_id,
            MaterialUnit.slug == candidate,
        )
        if exclude_id:
            query = query.filter(MaterialUnit.id != exclude_id)

        if not query.first():
            return candidate

    raise ValidationError(
        [f"Unable to generate unique slug for '{name}' after {max_attempts} attempts"]
    )


# =============================================================================
# Internal Implementation Functions
# =============================================================================


def _create_unit_impl(
    material_product_id: int,
    name: str,
    quantity_per_unit: float,
    slug: Optional[str],
    description: Optional[str],
    session: Session,
) -> MaterialUnit:
    """Implementation for create_unit.

    Feature 084: Changed from material_id to material_product_id.
    """
    # Validate material product exists
    product = session.query(MaterialProduct).filter_by(id=material_product_id).first()
    if not product:
        raise MaterialProductNotFoundError(material_product_id)

    # Validate quantity_per_unit > 0
    if quantity_per_unit <= 0:
        raise ValidationError(["quantity_per_unit must be positive"])

    # Validate name
    if not name or not name.strip():
        raise ValidationError(["name cannot be empty"])

    clean_name = name.strip()

    # Feature 084: Check name uniqueness within product
    existing_name = (
        session.query(MaterialUnit)
        .filter(
            MaterialUnit.material_product_id == material_product_id,
            MaterialUnit.name == clean_name,
        )
        .first()
    )
    if existing_name:
        raise ValidationError(
            [f"MaterialUnit with name '{clean_name}' already exists for this product"]
        )

    # Generate or validate slug (scoped to product)
    if slug:
        # Validate provided slug is unique within product
        existing_slug = (
            session.query(MaterialUnit)
            .filter(
                MaterialUnit.material_product_id == material_product_id,
                MaterialUnit.slug == slug,
            )
            .first()
        )
        if existing_slug:
            raise ValidationError([f"Slug '{slug}' already exists for this product"])
    else:
        slug = _generate_unique_slug(clean_name, session, material_product_id)

    unit = MaterialUnit(
        material_product_id=material_product_id,
        name=clean_name,
        slug=slug,
        quantity_per_unit=quantity_per_unit,
        description=description,
    )
    session.add(unit)
    session.flush()
    return unit


def _get_unit_impl(
    unit_id: Optional[int],
    slug: Optional[str],
    session: Session,
) -> MaterialUnit:
    """Implementation for get_unit."""
    if unit_id is None and slug is None:
        raise ValidationError(["Provide either unit_id or slug"])

    if unit_id is not None:
        unit = session.query(MaterialUnit).filter_by(id=unit_id).first()
    else:
        unit = session.query(MaterialUnit).filter_by(slug=slug).first()

    if not unit:
        identifier = unit_id if unit_id is not None else slug
        raise MaterialUnitNotFoundError(identifier)

    return unit


def _list_units_impl(
    material_product_id: Optional[int],
    session: Session,
) -> List[MaterialUnit]:
    """Implementation for list_units.

    Feature 084: Changed filter from material_id to material_product_id.
    """
    query = session.query(MaterialUnit)
    if material_product_id is not None:
        query = query.filter(MaterialUnit.material_product_id == material_product_id)
    return query.order_by(MaterialUnit.name).all()


def _update_unit_impl(
    unit_id: int,
    name: Optional[str],
    description: Optional[str],
    session: Session,
) -> MaterialUnit:
    """Implementation for update_unit.

    Feature 084: Added name uniqueness check within product.
    """
    unit = session.query(MaterialUnit).filter_by(id=unit_id).first()
    if not unit:
        raise MaterialUnitNotFoundError(unit_id)

    if name is not None:
        clean_name = name.strip()
        if not clean_name:
            raise ValidationError(["name cannot be empty"])

        # Feature 084: Check name uniqueness within same product (excluding self)
        if clean_name != unit.name:
            existing = (
                session.query(MaterialUnit)
                .filter(
                    MaterialUnit.material_product_id == unit.material_product_id,
                    MaterialUnit.name == clean_name,
                    MaterialUnit.id != unit_id,
                )
                .first()
            )
            if existing:
                raise ValidationError(
                    [f"MaterialUnit with name '{clean_name}' already exists for this product"]
                )
            unit.name = clean_name

    if description is not None:
        unit.description = description

    session.flush()
    return unit


def _delete_unit_impl(
    unit_id: int,
    session: Session,
) -> bool:
    """Implementation for delete_unit.

    Feature 084: Added validation to prevent deletion if referenced by Composition.
    """
    unit = session.query(MaterialUnit).filter_by(id=unit_id).first()
    if not unit:
        raise MaterialUnitNotFoundError(unit_id)

    # Check if used in any Composition
    references = session.query(Composition).filter(Composition.material_unit_id == unit_id).all()

    if references:
        # Build list of FinishedGoods/Packages that reference this unit
        fg_names = []
        for comp in references:
            if comp.assembly:
                fg_names.append(comp.assembly.display_name or f"Assembly #{comp.assembly_id}")
            elif comp.package:
                fg_names.append(f"Package #{comp.package_id}")
            else:
                fg_names.append(f"Composition #{comp.id}")

        raise MaterialUnitInUseError(unit_id, len(references), fg_names)

    session.delete(unit)
    session.flush()
    return True


def _get_available_inventory_impl(
    unit_id: int,
    session: Session,
) -> int:
    """Implementation for get_available_inventory.

    Feature 084: Changed to get inventory from parent MaterialProduct only.
    """
    unit = session.query(MaterialUnit).filter_by(id=unit_id).first()
    if not unit:
        raise MaterialUnitNotFoundError(unit_id)

    # Get inventory from parent product (Feature 084: single product, not all products)
    product = unit.material_product
    if not product:
        return 0

    # Sum inventory from FIFO lots (F058)
    inv_items = (
        session.query(MaterialInventoryItem)
        .filter(
            MaterialInventoryItem.material_product_id == product.id,
            MaterialInventoryItem.quantity_remaining >= 0.001,
        )
        .all()
    )
    total_inventory = sum(Decimal(str(item.quantity_remaining)) for item in inv_items)

    # Calculate complete units available (floor)
    if unit.quantity_per_unit <= 0:
        return 0

    return math.floor(float(total_inventory) / unit.quantity_per_unit)


def _get_current_cost_impl(
    unit_id: int,
    session: Session,
) -> Decimal:
    """Implementation for get_current_cost.

    Feature 084: Changed to get cost from parent MaterialProduct only.
    """
    unit = session.query(MaterialUnit).filter_by(id=unit_id).first()
    if not unit:
        raise MaterialUnitNotFoundError(unit_id)

    product = unit.material_product
    if not product:
        return Decimal("0")

    # Calculate weighted average cost from FIFO inventory (F058)
    inv_items = (
        session.query(MaterialInventoryItem)
        .filter(
            MaterialInventoryItem.material_product_id == product.id,
            MaterialInventoryItem.quantity_remaining >= 0.001,
        )
        .all()
    )

    total_value = Decimal("0")
    total_inventory = Decimal("0")

    for item in inv_items:
        inv = Decimal(str(item.quantity_remaining))
        cost = Decimal(str(item.cost_per_unit)) if item.cost_per_unit else Decimal("0")
        total_value += inv * cost
        total_inventory += inv

    if total_inventory == 0:
        return Decimal("0")

    weighted_avg = total_value / total_inventory

    # Multiply by quantity_per_unit
    unit_cost = weighted_avg * Decimal(str(unit.quantity_per_unit))

    # Round to 4 decimal places
    return unit_cost.quantize(Decimal("0.0001"))


def _preview_consumption_impl(
    unit_id: int,
    quantity_needed: int,
    session: Session,
) -> Dict[str, Any]:
    """Implementation for preview_consumption.

    Feature 084: Changed to use parent MaterialProduct only.
    """
    unit = session.query(MaterialUnit).filter_by(id=unit_id).first()
    if not unit:
        raise MaterialUnitNotFoundError(unit_id)

    # Calculate total base units needed
    base_units_needed = quantity_needed * unit.quantity_per_unit

    product = unit.material_product
    if not product:
        return {
            "can_fulfill": False,
            "quantity_needed": quantity_needed,
            "base_units_needed": base_units_needed,
            "available_base_units": 0,
            "available_units": 0,
            "shortage_base_units": base_units_needed,
            "shortage_units": quantity_needed,
            "allocations": [],
            "total_cost": "0.00",
        }

    # Get inventory from FIFO lots (F058)
    inv_items = (
        session.query(MaterialInventoryItem)
        .filter(
            MaterialInventoryItem.material_product_id == product.id,
            MaterialInventoryItem.quantity_remaining >= 0.001,
        )
        .all()
    )

    total_inventory = Decimal("0")
    total_value = Decimal("0")

    for item in inv_items:
        qty = Decimal(str(item.quantity_remaining))
        cost = Decimal(str(item.cost_per_unit)) if item.cost_per_unit else Decimal("0")
        total_inventory += qty
        total_value += qty * cost

    total_inv_float = float(total_inventory)

    # Determine if we can fulfill
    can_fulfill = total_inv_float >= base_units_needed
    shortage = 0 if can_fulfill else base_units_needed - total_inv_float

    # Calculate cost
    allocations = []
    total_cost = Decimal("0")

    if total_inventory > 0 and base_units_needed > 0:
        weighted_cost = total_value / total_inventory
        units_to_consume = min(base_units_needed, total_inv_float)
        line_cost = Decimal(str(units_to_consume)) * weighted_cost

        allocations.append(
            {
                "product_id": product.id,
                "product_name": product.display_name,
                "base_units_consumed": round(units_to_consume, 2),
                "unit_cost": str(weighted_cost.quantize(Decimal("0.0001"))),
                "total_cost": str(line_cost.quantize(Decimal("0.01"))),
            }
        )
        total_cost = line_cost

    return {
        "can_fulfill": can_fulfill,
        "quantity_needed": quantity_needed,
        "base_units_needed": base_units_needed,
        "available_base_units": total_inv_float,
        "available_units": (
            math.floor(total_inv_float / unit.quantity_per_unit)
            if unit.quantity_per_unit > 0
            else 0
        ),
        "shortage_base_units": shortage,
        "shortage_units": (
            math.ceil(shortage / unit.quantity_per_unit)
            if unit.quantity_per_unit > 0 and shortage > 0
            else 0
        ),
        "allocations": allocations,
        "total_cost": str(total_cost.quantize(Decimal("0.01"))),
    }


# =============================================================================
# Public API Functions
# =============================================================================


def create_unit(
    material_product_id: int,
    name: str,
    quantity_per_unit: float,
    slug: Optional[str] = None,
    description: Optional[str] = None,
    session: Optional[Session] = None,
) -> MaterialUnit:
    """Create a new MaterialUnit.

    Feature 084: Changed from material_id to material_product_id.

    Args:
        material_product_id: ID of the parent MaterialProduct
        name: Unit display name (e.g., "6-inch Red Ribbon")
        quantity_per_unit: Base units consumed per use (must be > 0)
        slug: Optional URL-friendly identifier (auto-generated if not provided)
        description: Optional description
        session: Optional database session

    Returns:
        Created MaterialUnit

    Raises:
        MaterialProductNotFoundError: If material_product_id doesn't exist
        ValidationError: If validation fails (name empty, duplicate name/slug, etc.)

    Example:
        >>> unit = create_unit(
        ...     material_product_id=1,
        ...     name="6-inch ribbon",
        ...     quantity_per_unit=15.24
        ... )
        >>> unit.slug
        '6-inch-ribbon'
    """
    if session is not None:
        return _create_unit_impl(
            material_product_id, name, quantity_per_unit, slug, description, session
        )
    with session_scope() as sess:
        return _create_unit_impl(
            material_product_id, name, quantity_per_unit, slug, description, sess
        )


def get_unit(
    unit_id: Optional[int] = None,
    slug: Optional[str] = None,
    session: Optional[Session] = None,
) -> MaterialUnit:
    """Get a MaterialUnit by ID or slug.

    Args:
        unit_id: Unit ID
        slug: Unit slug
        session: Optional database session

    Returns:
        MaterialUnit

    Raises:
        MaterialUnitNotFoundError: If unit not found
        ValidationError: If neither unit_id nor slug provided
    """
    if session is not None:
        return _get_unit_impl(unit_id, slug, session)
    with session_scope() as sess:
        return _get_unit_impl(unit_id, slug, sess)


def list_units(
    material_product_id: Optional[int] = None,
    session: Optional[Session] = None,
) -> List[MaterialUnit]:
    """List MaterialUnits, optionally filtered by product.

    Feature 084: Changed filter from material_id to material_product_id.

    Args:
        material_product_id: Filter by product (optional)
        session: Optional database session

    Returns:
        List of MaterialUnits ordered by name
    """
    if session is not None:
        return _list_units_impl(material_product_id, session)
    with session_scope() as sess:
        return _list_units_impl(material_product_id, sess)


def update_unit(
    unit_id: int,
    name: Optional[str] = None,
    description: Optional[str] = None,
    session: Optional[Session] = None,
) -> MaterialUnit:
    """Update a MaterialUnit.

    Note: quantity_per_unit cannot be changed after creation.

    Feature 084: Name uniqueness validated within product.

    Args:
        unit_id: Unit to update
        name: New name (optional)
        description: New description (optional)
        session: Optional database session

    Returns:
        Updated MaterialUnit

    Raises:
        MaterialUnitNotFoundError: If unit not found
        ValidationError: If name is empty or duplicate within product
    """
    if session is not None:
        return _update_unit_impl(unit_id, name, description, session)
    with session_scope() as sess:
        return _update_unit_impl(unit_id, name, description, sess)


def delete_unit(
    unit_id: int,
    session: Optional[Session] = None,
) -> bool:
    """Delete a MaterialUnit.

    Feature 084: Deletion fails if unit is referenced by any Composition.

    Args:
        unit_id: Unit to delete
        session: Optional database session

    Returns:
        True if deleted

    Raises:
        MaterialUnitNotFoundError: If unit not found
        MaterialUnitInUseError: If unit is used in compositions
    """
    if session is not None:
        return _delete_unit_impl(unit_id, session)
    with session_scope() as sess:
        return _delete_unit_impl(unit_id, sess)


def get_available_inventory(
    unit_id: int,
    session: Optional[Session] = None,
) -> int:
    """Get available inventory in complete units.

    Calculates how many complete MaterialUnits can be fulfilled from
    the current inventory of the parent MaterialProduct.

    Feature 084: Changed from aggregating across all products of a material
    to using only the parent MaterialProduct's inventory.

    Formula: floor(product.inventory / quantity_per_unit)

    Args:
        unit_id: MaterialUnit ID
        session: Optional database session

    Returns:
        Number of complete units available (integer)

    Raises:
        MaterialUnitNotFoundError: If unit not found

    Example:
        >>> # Product has 1200 cm inventory
        >>> # MaterialUnit "6-inch ribbon" has quantity_per_unit = 15.24 cm
        >>> get_available_inventory(unit.id)
        78  # floor(1200 / 15.24)
    """
    if session is not None:
        return _get_available_inventory_impl(unit_id, session)
    with session_scope() as sess:
        return _get_available_inventory_impl(unit_id, sess)


def get_current_cost(
    unit_id: int,
    session: Optional[Session] = None,
) -> Decimal:
    """Get current cost for one MaterialUnit.

    Calculates the cost by:
    1. Computing inventory-weighted average cost from parent product
    2. Multiplying by quantity_per_unit

    Feature 084: Changed from aggregating across all products of a material
    to using only the parent MaterialProduct's inventory.

    Args:
        unit_id: MaterialUnit ID
        session: Optional database session

    Returns:
        Cost per unit as Decimal

    Raises:
        MaterialUnitNotFoundError: If unit not found

    Example:
        >>> # Product has 1000 cm at $0.10/cm weighted avg
        >>> # Unit is 15.24 cm: cost = 15.24 * 0.10 = $1.524
        >>> get_current_cost(unit.id)
        Decimal('1.5240')
    """
    if session is not None:
        return _get_current_cost_impl(unit_id, session)
    with session_scope() as sess:
        return _get_current_cost_impl(unit_id, sess)


def preview_consumption(
    unit_id: int,
    quantity_needed: int,
    session: Optional[Session] = None,
) -> Dict[str, Any]:
    """Preview what inventory would be consumed for a given quantity.

    This is a read-only operation that calculates the allocation plan
    without modifying inventory. Use this to show the user what would
    happen before committing to actual consumption.

    Feature 084: Changed from allocating across multiple products to
    using only the parent MaterialProduct.

    Args:
        unit_id: MaterialUnit ID
        quantity_needed: Number of units to consume
        session: Optional database session

    Returns:
        Dict with:
            - can_fulfill: bool
            - quantity_needed: int
            - base_units_needed: float
            - available_base_units: float
            - available_units: int
            - shortage_base_units: float (0 if can_fulfill)
            - shortage_units: int (0 if can_fulfill)
            - allocations: list with single product allocation
            - total_cost: Decimal as string

    Raises:
        MaterialUnitNotFoundError: If unit not found

    Example:
        >>> preview = preview_consumption(unit.id, quantity_needed=50)
        >>> preview['can_fulfill']
        True
        >>> preview['total_cost']
        '76.20'
    """
    if session is not None:
        return _preview_consumption_impl(unit_id, quantity_needed, session)
    with session_scope() as sess:
        return _preview_consumption_impl(unit_id, quantity_needed, sess)


# =============================================================================
# Snapshot Functions
# =============================================================================


def create_material_unit_snapshot(
    material_unit_id: int,
    planning_snapshot_id: Optional[int] = None,
    assembly_run_id: Optional[int] = None,
    session: Optional[Session] = None,
) -> dict:
    """
    Create immutable snapshot of MaterialUnit definition.

    Feature 084: Updated to use material_product relationship.

    Args:
        material_unit_id: Source MaterialUnit ID
        planning_snapshot_id: Optional planning context
        assembly_run_id: Optional assembly context
        session: Optional session for transaction sharing

    Returns:
        dict with snapshot id and definition_data

    Raises:
        SnapshotCreationError: If MaterialUnit not found or creation fails
    """
    if session is not None:
        return _create_material_unit_snapshot_impl(
            material_unit_id, planning_snapshot_id, assembly_run_id, session
        )

    try:
        with session_scope() as session:
            return _create_material_unit_snapshot_impl(
                material_unit_id, planning_snapshot_id, assembly_run_id, session
            )
    except SQLAlchemyError as e:
        raise SnapshotCreationError(f"Database error creating snapshot: {e}")


def _create_material_unit_snapshot_impl(
    material_unit_id: int,
    planning_snapshot_id: Optional[int],
    assembly_run_id: Optional[int],
    session: Session,
) -> dict:
    """Internal implementation of snapshot creation.

    Feature 084: Updated to use material_product relationship.
    """
    mu = session.query(MaterialUnit).filter_by(id=material_unit_id).first()
    if not mu:
        raise SnapshotCreationError(f"MaterialUnit {material_unit_id} not found")

    # Feature 084: Use material_product → material chain
    product = mu.material_product
    material = product.material if product else None
    material_category = None
    if material and material.subcategory and material.subcategory.category:
        material_category = material.subcategory.category.name

    definition_data = {
        "slug": mu.slug,
        "name": mu.name,
        "description": mu.description,
        # Feature 084: Changed from material_id to material_product_id
        "material_product_id": mu.material_product_id,
        "material_product_name": product.name if product else None,
        "material_id": material.id if material else None,
        "material_name": material.name if material else None,
        "material_category": material_category,
        "quantity_per_unit": mu.quantity_per_unit,
    }

    snapshot = MaterialUnitSnapshot(
        material_unit_id=material_unit_id,
        planning_snapshot_id=planning_snapshot_id,
        assembly_run_id=assembly_run_id,
        definition_data=json.dumps(definition_data),
        is_backfilled=False,
    )

    session.add(snapshot)
    session.flush()

    return {
        "id": snapshot.id,
        "material_unit_id": snapshot.material_unit_id,
        "planning_snapshot_id": snapshot.planning_snapshot_id,
        "assembly_run_id": snapshot.assembly_run_id,
        "snapshot_date": snapshot.snapshot_date.isoformat(),
        "definition_data": definition_data,
        "is_backfilled": snapshot.is_backfilled,
    }


def get_material_unit_snapshot(
    snapshot_id: int,
    session: Optional[Session] = None,
) -> Optional[dict]:
    """
    Get a MaterialUnitSnapshot by its ID.

    Args:
        snapshot_id: Snapshot ID
        session: Optional session

    Returns:
        Snapshot dict or None if not found
    """
    if session is not None:
        return _get_material_unit_snapshot_impl(snapshot_id, session)

    with session_scope() as session:
        return _get_material_unit_snapshot_impl(snapshot_id, session)


def _get_material_unit_snapshot_impl(
    snapshot_id: int,
    session: Session,
) -> Optional[dict]:
    snapshot = session.query(MaterialUnitSnapshot).filter_by(id=snapshot_id).first()

    if not snapshot:
        return None

    return {
        "id": snapshot.id,
        "material_unit_id": snapshot.material_unit_id,
        "planning_snapshot_id": snapshot.planning_snapshot_id,
        "assembly_run_id": snapshot.assembly_run_id,
        "snapshot_date": snapshot.snapshot_date.isoformat(),
        "definition_data": snapshot.get_definition_data(),
        "is_backfilled": snapshot.is_backfilled,
    }


def get_material_unit_snapshots_by_planning_id(
    planning_snapshot_id: int,
    session: Optional[Session] = None,
) -> list[dict]:
    """
    Get all MaterialUnitSnapshots for a planning snapshot.

    Args:
        planning_snapshot_id: PlanningSnapshot ID
        session: Optional session

    Returns:
        List of snapshot dicts
    """
    if session is not None:
        return _get_mu_snapshots_by_planning_impl(planning_snapshot_id, session)

    with session_scope() as session:
        return _get_mu_snapshots_by_planning_impl(planning_snapshot_id, session)


def _get_mu_snapshots_by_planning_impl(
    planning_snapshot_id: int,
    session: Session,
) -> list[dict]:
    snapshots = (
        session.query(MaterialUnitSnapshot)
        .filter_by(planning_snapshot_id=planning_snapshot_id)
        .order_by(MaterialUnitSnapshot.snapshot_date.desc())
        .all()
    )

    return [
        {
            "id": s.id,
            "material_unit_id": s.material_unit_id,
            "planning_snapshot_id": s.planning_snapshot_id,
            "snapshot_date": s.snapshot_date.isoformat(),
            "definition_data": s.get_definition_data(),
            "is_backfilled": s.is_backfilled,
        }
        for s in snapshots
    ]
