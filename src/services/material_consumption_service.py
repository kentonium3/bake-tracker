"""Material Consumption Service - Assembly material consumption operations.

This module provides business logic for consuming materials during assembly,
including inventory validation, consumption recording with snapshots, and
inventory decrements. Part of Feature 047: Materials Management System.

Key Features:
- Validate material availability before assembly
- Record material consumption with full snapshots
- Atomic inventory decrements
- Strict blocking when inventory insufficient (no bypass)

All functions accept optional session parameter per CLAUDE.md session management rules.
"""

from typing import Optional, List, Dict, Any, Union
from decimal import Decimal

from sqlalchemy.orm import Session

from ..models import (
    Composition,
    FinishedGood,
    MaterialProduct,
    MaterialUnit,
    MaterialConsumption,
    MaterialInventoryItem,
)
from .database import session_scope
from .exceptions import ValidationError
from .material_unit_service import get_current_cost, get_available_inventory


# =============================================================================
# Custom Exceptions
# =============================================================================


class MaterialConsumptionError(Exception):
    """Base exception for material consumption errors."""

    pass


class InsufficientMaterialError(MaterialConsumptionError):
    """Raised when material inventory is insufficient for consumption."""

    def __init__(self, material_name: str, needed: float, available: float):
        self.material_name = material_name
        self.needed = needed
        self.available = available
        super().__init__(
            f"Material '{material_name}' has insufficient inventory "
            f"(need {needed}, have {available})"
        )


class MaterialAssignmentRequiredError(MaterialConsumptionError):
    """Raised when generic material requires product assignment but none provided."""

    def __init__(self, material_name: str, composition_id: int):
        self.material_name = material_name
        self.composition_id = composition_id
        super().__init__(
            f"Generic material '{material_name}' (composition {composition_id}) "
            f"requires product assignment"
        )


# =============================================================================
# Internal Implementation Functions
# =============================================================================


def _get_pending_materials_impl(
    finished_good_id: int,
    session: Session,
) -> List[Dict[str, Any]]:
    """Implementation for get_pending_materials."""
    # Feature 084: generic material placeholders removed (material_id column removed).
    # Pending materials are no longer applicable.
    return []


def _validate_material_availability_impl(
    finished_good_id: int,
    assembly_quantity: int,
    material_assignments: Optional[Dict[int, Dict[int, float]]],
    session: Session,
) -> Dict[str, Any]:
    """Implementation for validate_material_availability.

    Args:
        finished_good_id: FinishedGood being assembled
        assembly_quantity: Number of assemblies
        material_assignments: Deprecated (generic material placeholders removed).
        session: Database session

    Returns:
        Validation result dict
    """
    # Get all material compositions for this FinishedGood
    compositions = (
        session.query(Composition)
        .filter(Composition.assembly_id == finished_good_id)
        .filter(Composition.material_unit_id.isnot(None))
        .all()
    )

    errors = []
    material_requirements = []

    for comp in compositions:
        if comp.material_unit_id:
            # Specific MaterialUnit - check availability via service
            unit = session.query(MaterialUnit).filter_by(id=comp.material_unit_id).first()
            if not unit:
                errors.append(f"MaterialUnit {comp.material_unit_id} not found")
                continue

            # Calculate needed units with proper rounding (avoid int() truncation)
            raw_needed = comp.component_quantity * assembly_quantity
            needed_units = round(raw_needed)
            available_units = get_available_inventory(comp.material_unit_id, session=session)
            base_units_needed = needed_units * unit.quantity_per_unit
            base_available = available_units * unit.quantity_per_unit

            sufficient = available_units >= needed_units

            if not sufficient:
                errors.append(
                    f"Material '{unit.name}' has insufficient inventory "
                    f"(need {needed_units} units, have {available_units})"
                )

            material_requirements.append(
                {
                    "composition_id": comp.id,
                    "is_generic": False,
                    "material_name": unit.name,
                    "units_needed": needed_units,
                    "base_units_needed": base_units_needed,
                    "available_units": available_units,
                    "base_available": base_available,
                    "sufficient": sufficient,
                }
            )

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "material_requirements": material_requirements,
    }


def _decrement_inventory(
    product: MaterialProduct,
    base_units_consumed: float,
    session: Session,
) -> Dict[str, Any]:
    """Decrease product inventory atomically using FIFO.

    Args:
        product: MaterialProduct to decrement
        base_units_consumed: Amount to decrement (in base units)
        session: Database session (ensures atomic operation)

    Returns:
        Dict with consumption details (breakdown, total_cost, inventory_item_id)

    Raises:
        InsufficientMaterialError: If inventory insufficient
    """
    from .material_inventory_service import consume_material_fifo

    # Determine the correct target_unit based on material's base_unit_type (F058)
    # Map base_unit_type to the self-referential unit name
    base_unit_type = product.material.base_unit_type if product.material else "linear_cm"
    target_unit_map = {
        "linear_cm": "cm",
        "square_cm": "square_cm",
        "each": "each",
    }
    target_unit = target_unit_map.get(base_unit_type, "cm")

    # Use FIFO consumption from material_inventory_service (F058)
    result = consume_material_fifo(
        material_product_id=product.id,
        quantity_needed=Decimal(str(base_units_consumed)),
        target_unit=target_unit,
        dry_run=False,
        session=session,
    )

    if not result["satisfied"]:
        # Get current inventory for error message
        inv_items = (
            session.query(MaterialInventoryItem)
            .filter(
                MaterialInventoryItem.material_product_id == product.id,
                MaterialInventoryItem.quantity_remaining >= 0.001,
            )
            .all()
        )
        product_inventory = sum(item.quantity_remaining for item in inv_items)

        raise InsufficientMaterialError(
            product.display_name,
            base_units_consumed,
            product_inventory,
        )

    return result


def _record_material_consumption_impl(
    assembly_run_id: int,
    finished_good_id: int,
    assembly_quantity: int,
    material_assignments: Optional[Dict[int, Dict[int, float]]],
    session: Session,
) -> List[MaterialConsumption]:
    """Implementation for record_material_consumption.

    Args:
        assembly_run_id: ID of the AssemblyRun being recorded
        finished_good_id: FinishedGood being assembled
        assembly_quantity: Number of assemblies
        material_assignments: Dict mapping composition_id -> {product_id: quantity_to_consume}
            for generic materials. Allows split allocation across multiple products.
        session: Database session

    Returns:
        List of created MaterialConsumption records

    Raises:
        ValidationError: If material availability validation fails
        InsufficientMaterialError: If inventory insufficient during consumption
    """
    # First validate availability - this enforces "no bypass" rule
    validation = _validate_material_availability_impl(
        finished_good_id, assembly_quantity, material_assignments, session
    )

    if not validation["valid"]:
        raise ValidationError(validation["errors"])

    # Get all material compositions
    compositions = (
        session.query(Composition)
        .filter(Composition.assembly_id == finished_good_id)
        .filter(Composition.material_unit_id.isnot(None))
        .all()
    )

    consumptions = []

    for comp in compositions:
        if comp.material_unit_id:
            # MaterialUnit is scoped to a specific MaterialProduct (Feature 084).
            unit = session.query(MaterialUnit).filter_by(id=comp.material_unit_id).first()
            if not unit or not unit.material_product:
                continue

            product = unit.material_product
            material = product.material

            # Calculate needed units with proper rounding (avoid int() truncation)
            raw_needed = comp.component_quantity * assembly_quantity
            needed_units = round(raw_needed)
            base_units_needed = needed_units * unit.quantity_per_unit

            # Use FIFO decrement and get cost from the result
            fifo_result = _decrement_inventory(product, base_units_needed, session)
            unit_cost = (
                fifo_result["total_cost"] / Decimal(str(base_units_needed))
                if base_units_needed > 0
                else Decimal("0")
            )
            total_cost = fifo_result["total_cost"]

            # Get inventory_item_id from first breakdown entry if available
            inv_item_id = (
                fifo_result["breakdown"][0]["inventory_item_id"]
                if fifo_result.get("breakdown")
                else None
            )

            consumption = MaterialConsumption(
                assembly_run_id=assembly_run_id,
                product_id=product.id,
                inventory_item_id=inv_item_id,  # F058: Link to FIFO lot
                quantity_consumed=base_units_needed,
                unit_cost=unit_cost,
                total_cost=total_cost,
                # Snapshot fields
                product_name=product.display_name,
                material_name=material.name if material else "",
                subcategory_name=(
                    material.subcategory.name if material and material.subcategory else ""
                ),
                category_name=(
                    material.subcategory.category.name
                    if material and material.subcategory and material.subcategory.category
                    else ""
                ),
                supplier_name=product.supplier.name if product.supplier else None,
            )
            session.add(consumption)
            consumptions.append(consumption)

    session.flush()
    return consumptions


# =============================================================================
# Public API Functions
# =============================================================================


def get_pending_materials(
    finished_good_id: int,
    session: Optional[Session] = None,
) -> List[Dict[str, Any]]:
    """Find materials requiring resolution for a FinishedGood.

    Feature 084 removed generic material placeholders, so this now returns
    an empty list to preserve API compatibility.

    Args:
        finished_good_id: FinishedGood to check
        session: Optional database session

    Returns:
        List of dicts (empty under Feature 084).

    Example:
        >>> pending = get_pending_materials(fg.id)
        >>> assert pending == []
    """
    if session is not None:
        return _get_pending_materials_impl(finished_good_id, session)
    with session_scope() as sess:
        return _get_pending_materials_impl(finished_good_id, sess)


def validate_material_availability(
    finished_good_id: int,
    assembly_quantity: int,
    material_assignments: Optional[Dict[int, Union[int, Dict[int, float]]]] = None,
    session: Optional[Session] = None,
) -> Dict[str, Any]:
    """Check that all materials have sufficient inventory.

    Validates MaterialUnit components only. Generic material placeholders
    were removed in Feature 084; material_assignments is ignored.

    Args:
        finished_good_id: FinishedGood being assembled
        assembly_quantity: Number of assemblies
        material_assignments: Deprecated (generic material placeholders removed).
        session: Optional database session

    Returns:
        Dict with:
            - valid: bool - True if all materials have sufficient inventory
            - errors: List[str] - Error messages for any failures
            - material_requirements: List of requirement details

    Example (single product):
        >>> result = validate_material_availability(
        ...     fg.id, assembly_quantity=10,
        ...     material_assignments={comp_id: product_id}
        ... )

    Example (split allocation):
        >>> result = validate_material_availability(
        ...     fg.id, assembly_quantity=50,
        ...     material_assignments={comp_id: {prod1_id: 30, prod2_id: 20}}
        ... )
    """
    if session is not None:
        return _validate_material_availability_impl(
            finished_good_id, assembly_quantity, material_assignments, session
        )
    with session_scope() as sess:
        return _validate_material_availability_impl(
            finished_good_id, assembly_quantity, material_assignments, sess
        )


def record_material_consumption(
    assembly_run_id: int,
    finished_good_id: int,
    assembly_quantity: int,
    material_assignments: Optional[Dict[int, Union[int, Dict[int, float]]]] = None,
    session: Optional[Session] = None,
) -> List[MaterialConsumption]:
    """Record material consumption with full snapshots and inventory decrements.

    Creates MaterialConsumption records for all materials used in assembly,
    capturing snapshot data (product name, material name, category, supplier)
    for historical accuracy. Atomically decrements inventory. Supports split
    allocation where a material need can be fulfilled from multiple products.

    IMPORTANT: This function enforces strict inventory validation with NO bypass.
    If inventory is insufficient, a ValidationError is raised and assembly is blocked.

    Args:
        assembly_run_id: ID of the AssemblyRun being recorded
        finished_good_id: FinishedGood being assembled
        assembly_quantity: Number of assemblies
        material_assignments: Dict mapping composition_id to either:
            - int (legacy): single product_id (system calculates quantity)
            - Dict[int, float] (new): {product_id: quantity_to_use, ...}
              for split allocation across multiple products
        session: Optional database session

    Returns:
        List of created MaterialConsumption records

    Raises:
        ValidationError: If material availability validation fails
        InsufficientMaterialError: If inventory becomes insufficient during consumption
        MaterialAssignmentRequiredError: If generic material lacks assignment

    Example (single product):
        >>> consumptions = record_material_consumption(
        ...     assembly_run_id=run.id,
        ...     finished_good_id=fg.id,
        ...     assembly_quantity=10,
        ...     material_assignments={comp_id: product_id},
        ...     session=session
        ... )

    Example (split allocation):
        >>> consumptions = record_material_consumption(
        ...     assembly_run_id=run.id,
        ...     finished_good_id=fg.id,
        ...     assembly_quantity=50,
        ...     material_assignments={comp_id: {prod1_id: 30, prod2_id: 20}},
        ...     session=session
        ... )
    """
    if session is not None:
        return _record_material_consumption_impl(
            assembly_run_id, finished_good_id, assembly_quantity, material_assignments, session
        )
    with session_scope() as sess:
        return _record_material_consumption_impl(
            assembly_run_id, finished_good_id, assembly_quantity, material_assignments, sess
        )


def get_consumption_history(
    assembly_run_id: int,
    session: Optional[Session] = None,
) -> List[Dict[str, Any]]:
    """Get material consumption records for an assembly run.

    Returns snapshot data from consumption records, NOT current catalog data.

    Args:
        assembly_run_id: AssemblyRun to query
        session: Optional database session

    Returns:
        List of consumption records as dicts with snapshot fields
    """

    def _impl(sess: Session) -> List[Dict[str, Any]]:
        consumptions = (
            sess.query(MaterialConsumption)
            .filter(MaterialConsumption.assembly_run_id == assembly_run_id)
            .all()
        )
        return [c.to_dict() for c in consumptions]

    if session is not None:
        return _impl(session)
    with session_scope() as sess:
        return _impl(sess)
