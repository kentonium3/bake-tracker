"""Material Unit Service - MaterialUnit management and inventory calculations.

This module provides business logic for managing MaterialUnits and calculating
availability and costs. Part of Feature 047: Materials Management System.

Key Features:
- MaterialUnit CRUD operations
- Available inventory aggregation across products
- Cost calculation with weighted average
- Consumption preview without modifying inventory

All functions accept optional session parameter per CLAUDE.md session management rules.
"""

from typing import Optional, List, Dict, Any
from decimal import Decimal
import math

from sqlalchemy.orm import Session

from ..models import Material, MaterialProduct, MaterialUnit, Composition, MaterialInventoryItem
from .database import session_scope
from .exceptions import ValidationError
from .material_catalog_service import slugify


# =============================================================================
# Custom Exceptions
# =============================================================================


class MaterialUnitNotFoundError(Exception):
    """Raised when a material unit is not found."""

    def __init__(self, unit_id: int):
        self.unit_id = unit_id
        super().__init__(f"Material unit not found: {unit_id}")


class MaterialNotFoundError(Exception):
    """Raised when a material is not found."""

    def __init__(self, material_id: int):
        self.material_id = material_id
        super().__init__(f"Material not found: {material_id}")


class MaterialUnitInUseError(Exception):
    """Raised when attempting to delete a unit that is in use."""

    def __init__(self, unit_id: int, usage_count: int):
        self.unit_id = unit_id
        self.usage_count = usage_count
        super().__init__(f"Material unit {unit_id} is used in {usage_count} composition(s)")


# =============================================================================
# Internal Implementation Functions
# =============================================================================


def _generate_unique_slug(base_slug: str, session: Session) -> str:
    """Generate a unique slug by appending numbers if needed."""
    slug = base_slug
    counter = 1
    while session.query(MaterialUnit).filter_by(slug=slug).first():
        slug = f"{base_slug}_{counter}"
        counter += 1
    return slug


def _create_unit_impl(
    material_id: int,
    name: str,
    quantity_per_unit: float,
    slug: Optional[str],
    description: Optional[str],
    session: Session,
) -> MaterialUnit:
    """Implementation for create_unit."""
    # Validate material exists
    material = session.query(Material).filter_by(id=material_id).first()
    if not material:
        raise MaterialNotFoundError(material_id)

    # Validate quantity_per_unit > 0
    if quantity_per_unit <= 0:
        raise ValidationError(["quantity_per_unit must be positive"])

    # Validate name
    if not name or not name.strip():
        raise ValidationError(["name cannot be empty"])

    # Generate slug if not provided
    if slug:
        # Validate slug uniqueness
        existing = session.query(MaterialUnit).filter_by(slug=slug).first()
        if existing:
            raise ValidationError([f"Slug '{slug}' already exists"])
    else:
        slug = _generate_unique_slug(slugify(name), session)

    unit = MaterialUnit(
        material_id=material_id,
        name=name.strip(),
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
    material_id: Optional[int],
    session: Session,
) -> List[MaterialUnit]:
    """Implementation for list_units."""
    query = session.query(MaterialUnit)
    if material_id is not None:
        query = query.filter(MaterialUnit.material_id == material_id)
    return query.order_by(MaterialUnit.name).all()


def _update_unit_impl(
    unit_id: int,
    name: Optional[str],
    description: Optional[str],
    session: Session,
) -> MaterialUnit:
    """Implementation for update_unit."""
    unit = session.query(MaterialUnit).filter_by(id=unit_id).first()
    if not unit:
        raise MaterialUnitNotFoundError(unit_id)

    if name is not None:
        if not name.strip():
            raise ValidationError(["name cannot be empty"])
        unit.name = name.strip()

    if description is not None:
        unit.description = description

    session.flush()
    return unit


def _delete_unit_impl(
    unit_id: int,
    session: Session,
) -> bool:
    """Implementation for delete_unit."""
    unit = session.query(MaterialUnit).filter_by(id=unit_id).first()
    if not unit:
        raise MaterialUnitNotFoundError(unit_id)

    # Check if used in any Composition (once WP05 adds material_unit_id)
    # For now, check if the column exists before querying
    if hasattr(Composition, 'material_unit_id') and Composition.material_unit_id is not None:
        usage_count = (
            session.query(Composition)
            .filter(Composition.material_unit_id == unit_id)
            .count()
        )
        if usage_count > 0:
            raise MaterialUnitInUseError(unit_id, usage_count)

    session.delete(unit)
    session.flush()
    return True


def _get_available_inventory_impl(
    unit_id: int,
    session: Session,
) -> int:
    """Implementation for get_available_inventory."""
    unit = session.query(MaterialUnit).filter_by(id=unit_id).first()
    if not unit:
        raise MaterialUnitNotFoundError(unit_id)

    # Get all products for this material
    products = (
        session.query(MaterialProduct)
        .filter(MaterialProduct.material_id == unit.material_id)
        .all()
    )

    # Sum inventory across all products using MaterialInventoryItem (F058 FIFO)
    total_inventory = Decimal("0")
    for product in products:
        inv_items = (
            session.query(MaterialInventoryItem)
            .filter(
                MaterialInventoryItem.material_product_id == product.id,
                MaterialInventoryItem.quantity_remaining >= 0.001,
            )
            .all()
        )
        total_inventory += sum(
            Decimal(str(item.quantity_remaining)) for item in inv_items
        )

    # Calculate complete units available (floor)
    if unit.quantity_per_unit <= 0:
        return 0

    return math.floor(float(total_inventory) / unit.quantity_per_unit)


def _get_current_cost_impl(
    unit_id: int,
    session: Session,
) -> Decimal:
    """Implementation for get_current_cost."""
    unit = session.query(MaterialUnit).filter_by(id=unit_id).first()
    if not unit:
        raise MaterialUnitNotFoundError(unit_id)

    # Get all products for this material
    products = (
        session.query(MaterialProduct)
        .filter(MaterialProduct.material_id == unit.material_id)
        .all()
    )

    if not products:
        return Decimal("0")

    # Calculate inventory-weighted average cost using MaterialInventoryItem (F058 FIFO)
    total_value = Decimal("0")
    total_inventory = Decimal("0")

    for product in products:
        inv_items = (
            session.query(MaterialInventoryItem)
            .filter(
                MaterialInventoryItem.material_product_id == product.id,
                MaterialInventoryItem.quantity_remaining >= 0.001,
            )
            .all()
        )

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
    """Implementation for preview_consumption."""
    unit = session.query(MaterialUnit).filter_by(id=unit_id).first()
    if not unit:
        raise MaterialUnitNotFoundError(unit_id)

    # Calculate total base units needed
    base_units_needed = quantity_needed * unit.quantity_per_unit

    # Get products for this material
    products = (
        session.query(MaterialProduct)
        .filter(MaterialProduct.material_id == unit.material_id)
        .all()
    )

    # Build inventory data per product using MaterialInventoryItem (F058 FIFO)
    product_inventory = {}  # product_id -> (inventory, weighted_cost)
    total_inventory = Decimal("0")

    for product in products:
        inv_items = (
            session.query(MaterialInventoryItem)
            .filter(
                MaterialInventoryItem.material_product_id == product.id,
                MaterialInventoryItem.quantity_remaining >= 0.001,
            )
            .all()
        )

        product_inv = Decimal("0")
        product_value = Decimal("0")

        for item in inv_items:
            qty = Decimal(str(item.quantity_remaining))
            cost = Decimal(str(item.cost_per_unit)) if item.cost_per_unit else Decimal("0")
            product_inv += qty
            product_value += qty * cost

        if product_inv > 0:
            weighted_cost = product_value / product_inv
            product_inventory[product.id] = {
                "product": product,
                "inventory": float(product_inv),
                "weighted_cost": weighted_cost,
            }
            total_inventory += product_inv

    total_inv_float = float(total_inventory)

    # Determine if we can fulfill
    can_fulfill = total_inv_float >= base_units_needed
    shortage = 0 if can_fulfill else base_units_needed - total_inv_float

    # Allocate proportionally across products
    allocations = []
    total_cost = Decimal("0")

    if product_inventory and base_units_needed > 0:
        units_to_allocate = min(base_units_needed, total_inv_float)

        for product_id, data in product_inventory.items():
            product = data["product"]
            product_inv = data["inventory"]
            weighted_cost = data["weighted_cost"]

            if total_inv_float > 0:
                # Proportional allocation
                proportion = product_inv / total_inv_float
                base_units = proportion * units_to_allocate

                line_cost = Decimal(str(base_units)) * weighted_cost

                allocations.append({
                    "product_id": product.id,
                    "product_name": product.display_name,
                    "base_units_consumed": round(base_units, 2),
                    "unit_cost": str(weighted_cost.quantize(Decimal("0.0001"))),
                    "total_cost": str(line_cost.quantize(Decimal("0.01"))),
                })

                total_cost += line_cost

    return {
        "can_fulfill": can_fulfill,
        "quantity_needed": quantity_needed,
        "base_units_needed": base_units_needed,
        "available_base_units": total_inv_float,
        "available_units": math.floor(total_inv_float / unit.quantity_per_unit) if unit.quantity_per_unit > 0 else 0,
        "shortage_base_units": shortage,
        "shortage_units": math.ceil(shortage / unit.quantity_per_unit) if unit.quantity_per_unit > 0 and shortage > 0 else 0,
        "allocations": allocations,
        "total_cost": str(total_cost.quantize(Decimal("0.01"))),
    }


# =============================================================================
# Public API Functions
# =============================================================================


def create_unit(
    material_id: int,
    name: str,
    quantity_per_unit: float,
    slug: Optional[str] = None,
    description: Optional[str] = None,
    session: Optional[Session] = None,
) -> MaterialUnit:
    """Create a new MaterialUnit.

    Args:
        material_id: ID of the parent Material
        name: Unit display name (e.g., "6-inch Red Ribbon")
        quantity_per_unit: Base units consumed per use (must be > 0)
        slug: Optional URL-friendly identifier (auto-generated if not provided)
        description: Optional description
        session: Optional database session

    Returns:
        Created MaterialUnit

    Raises:
        MaterialNotFoundError: If material_id doesn't exist
        ValidationError: If validation fails

    Example:
        >>> unit = create_unit(
        ...     material_id=1,
        ...     name="6-inch ribbon",
        ...     quantity_per_unit=6
        ... )
        >>> unit.slug
        '6_inch_ribbon'
    """
    if session is not None:
        return _create_unit_impl(
            material_id, name, quantity_per_unit, slug, description, session
        )
    with session_scope() as sess:
        return _create_unit_impl(
            material_id, name, quantity_per_unit, slug, description, sess
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
    material_id: Optional[int] = None,
    session: Optional[Session] = None,
) -> List[MaterialUnit]:
    """List MaterialUnits, optionally filtered by material.

    Args:
        material_id: Filter by material (optional)
        session: Optional database session

    Returns:
        List of MaterialUnits ordered by name
    """
    if session is not None:
        return _list_units_impl(material_id, session)
    with session_scope() as sess:
        return _list_units_impl(material_id, sess)


def update_unit(
    unit_id: int,
    name: Optional[str] = None,
    description: Optional[str] = None,
    session: Optional[Session] = None,
) -> MaterialUnit:
    """Update a MaterialUnit.

    Note: quantity_per_unit cannot be changed after creation.

    Args:
        unit_id: Unit to update
        name: New name (optional)
        description: New description (optional)
        session: Optional database session

    Returns:
        Updated MaterialUnit

    Raises:
        MaterialUnitNotFoundError: If unit not found
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
    the current inventory across all products of the material.

    Formula: floor(sum(product.current_inventory) / quantity_per_unit)

    Args:
        unit_id: MaterialUnit ID
        session: Optional database session

    Returns:
        Number of complete units available (integer)

    Raises:
        MaterialUnitNotFoundError: If unit not found

    Example:
        >>> # Material has 1200 inches total inventory
        >>> # MaterialUnit "6-inch ribbon" has quantity_per_unit = 6
        >>> get_available_inventory(unit.id)
        200  # floor(1200 / 6)
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
    1. Computing inventory-weighted average cost across products
    2. Multiplying by quantity_per_unit

    Args:
        unit_id: MaterialUnit ID
        session: Optional database session

    Returns:
        Cost per unit as Decimal

    Raises:
        MaterialUnitNotFoundError: If unit not found

    Example:
        >>> # Product A: 800 inches at $0.10/inch
        >>> # Product B: 400 inches at $0.14/inch
        >>> # Weighted avg = (800*0.10 + 400*0.14) / 1200 = $0.1133/inch
        >>> # Unit is 6 inches: cost = 6 * 0.1133 = $0.68
        >>> get_current_cost(unit.id)
        Decimal('0.68')
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
    """Preview what products would be consumed for a given quantity.

    This is a read-only operation that calculates the allocation plan
    without modifying inventory. Use this to show the user what would
    happen before committing to actual consumption.

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
            - allocations: list of product allocations
            - total_cost: Decimal as string

    Raises:
        MaterialUnitNotFoundError: If unit not found

    Example:
        >>> preview = preview_consumption(unit.id, quantity_needed=50)
        >>> preview['can_fulfill']
        True
        >>> preview['total_cost']
        '34.00'
    """
    if session is not None:
        return _preview_consumption_impl(unit_id, quantity_needed, session)
    with session_scope() as sess:
        return _preview_consumption_impl(unit_id, quantity_needed, sess)
