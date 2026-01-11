"""Material Consumption Service - Assembly material consumption operations.

This module provides business logic for consuming materials during assembly,
including inventory validation, consumption recording with snapshots, and
inventory decrements. Part of Feature 047: Materials Management System.

Key Features:
- Find pending generic materials requiring resolution
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
    Material,
    MaterialProduct,
    MaterialUnit,
    MaterialConsumption,
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
    # Find compositions with generic material placeholders (material_id set)
    compositions = (
        session.query(Composition)
        .filter(Composition.assembly_id == finished_good_id)
        .filter(Composition.material_id.isnot(None))
        .all()
    )

    pending = []
    for comp in compositions:
        material = session.query(Material).filter_by(id=comp.material_id).first()
        if not material:
            continue

        # Get available products for this material
        products = (
            session.query(MaterialProduct)
            .filter(MaterialProduct.material_id == material.id)
            .filter(MaterialProduct.current_inventory > 0)
            .all()
        )

        available_products = []
        for prod in products:
            # Calculate available units based on material's base unit
            available_products.append({
                "product_id": prod.id,
                "name": prod.display_name,
                "available_inventory": prod.current_inventory,
                "unit_cost": prod.weighted_avg_cost or Decimal("0"),
            })

        pending.append({
            "composition_id": comp.id,
            "material_id": material.id,
            "material_name": material.name,
            "quantity_needed": comp.component_quantity,
            "available_products": available_products,
        })

    return pending


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
        material_assignments: Dict mapping composition_id -> {product_id: quantity_to_consume}
            for generic materials. Allows split allocation across multiple products.
        session: Database session

    Returns:
        Validation result dict
    """
    material_assignments = material_assignments or {}

    # Get all material compositions for this FinishedGood
    compositions = (
        session.query(Composition)
        .filter(Composition.assembly_id == finished_good_id)
        .filter(
            (Composition.material_unit_id.isnot(None)) |
            (Composition.material_id.isnot(None))
        )
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

            material_requirements.append({
                "composition_id": comp.id,
                "is_generic": False,
                "material_name": unit.name,
                "units_needed": needed_units,
                "base_units_needed": base_units_needed,
                "available_units": available_units,
                "base_available": base_available,
                "sufficient": sufficient,
            })

        elif comp.material_id:
            # Generic Material placeholder - requires assignment (supports split allocation)
            material = session.query(Material).filter_by(id=comp.material_id).first()
            if not material:
                errors.append(f"Material {comp.material_id} not found")
                continue

            base_units_needed = comp.component_quantity * assembly_quantity

            # Check if assignment provided
            if comp.id not in material_assignments:
                errors.append(
                    f"Generic material '{material.name}' (composition {comp.id}) "
                    f"requires product assignment"
                )
                material_requirements.append({
                    "composition_id": comp.id,
                    "is_generic": True,
                    "material_name": material.name,
                    "base_units_needed": base_units_needed,
                    "available": 0,
                    "sufficient": False,
                    "assignment_required": True,
                })
                continue

            # Get the allocations for this composition
            allocations = material_assignments[comp.id]

            # Support both old format (single product_id) and new format (dict)
            if isinstance(allocations, int):
                # Legacy format: single product_id - convert to new format
                allocations = {allocations: base_units_needed}

            # Validate allocations
            if not allocations:
                errors.append(
                    f"Generic material '{material.name}' (composition {comp.id}) "
                    f"requires at least one product allocation"
                )
                continue

            # Calculate total allocated quantity
            total_allocated = sum(allocations.values())

            # Validate total matches needed quantity
            if abs(total_allocated - base_units_needed) > 0.001:  # Float tolerance
                errors.append(
                    f"Material '{material.name}' allocation mismatch: "
                    f"allocated {total_allocated}, need {base_units_needed}"
                )
                continue

            # Validate each product allocation
            allocation_details = []
            all_sufficient = True
            total_available = 0

            for product_id, quantity_to_use in allocations.items():
                product = session.query(MaterialProduct).filter_by(id=product_id).first()

                if not product:
                    errors.append(f"Assigned product {product_id} not found")
                    all_sufficient = False
                    continue

                if product.material_id != material.id:
                    errors.append(
                        f"Product {product_id} is not for material '{material.name}'"
                    )
                    all_sufficient = False
                    continue

                if product.current_inventory < quantity_to_use:
                    errors.append(
                        f"Product '{product.display_name}' has insufficient inventory "
                        f"(need {quantity_to_use}, have {product.current_inventory})"
                    )
                    all_sufficient = False

                total_available += product.current_inventory
                allocation_details.append({
                    "product_id": product_id,
                    "product_name": product.display_name,
                    "quantity_to_use": quantity_to_use,
                    "available": product.current_inventory,
                    "sufficient": product.current_inventory >= quantity_to_use,
                })

            material_requirements.append({
                "composition_id": comp.id,
                "is_generic": True,
                "material_name": material.name,
                "base_units_needed": base_units_needed,
                "total_available": total_available,
                "sufficient": all_sufficient,
                "allocations": allocation_details,
            })

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "material_requirements": material_requirements,
    }


def _decrement_inventory(
    product: MaterialProduct,
    base_units_consumed: float,
    session: Session,
) -> None:
    """Decrease product inventory atomically.

    Args:
        product: MaterialProduct to decrement
        base_units_consumed: Amount to decrement
        session: Database session (ensures atomic operation)

    Raises:
        InsufficientMaterialError: If inventory insufficient
    """
    if product.current_inventory < base_units_consumed:
        raise InsufficientMaterialError(
            product.display_name,
            base_units_consumed,
            product.current_inventory,
        )

    product.current_inventory -= base_units_consumed
    session.flush()


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
    material_assignments = material_assignments or {}

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
        .filter(
            (Composition.material_unit_id.isnot(None)) |
            (Composition.material_id.isnot(None))
        )
        .all()
    )

    consumptions = []

    for comp in compositions:
        if comp.material_unit_id:
            # Specific MaterialUnit - consume proportionally from products
            unit = session.query(MaterialUnit).filter_by(id=comp.material_unit_id).first()
            if not unit:
                continue

            # Calculate needed units with proper rounding (avoid int() truncation)
            raw_needed = comp.component_quantity * assembly_quantity
            needed_units = round(raw_needed)
            base_units_needed = needed_units * unit.quantity_per_unit

            # Get material for snapshot
            material = session.query(Material).filter_by(id=unit.material_id).first()
            if not material:
                continue

            # Get products with inventory for proportional consumption
            products = (
                session.query(MaterialProduct)
                .filter(MaterialProduct.material_id == material.id)
                .filter(MaterialProduct.current_inventory > 0)
                .all()
            )

            if not products:
                raise InsufficientMaterialError(unit.name, base_units_needed, 0)

            # Calculate total available inventory
            total_inventory = sum(p.current_inventory for p in products)

            if total_inventory < base_units_needed:
                raise InsufficientMaterialError(unit.name, base_units_needed, total_inventory)

            # Consume proportionally from each product
            remaining_to_consume = base_units_needed

            for product in products:
                if remaining_to_consume <= 0:
                    break

                # Proportional allocation (consume from this product)
                proportion = product.current_inventory / total_inventory
                to_consume = min(
                    proportion * base_units_needed,
                    product.current_inventory,
                    remaining_to_consume,
                )

                if to_consume <= 0:
                    continue

                # Get unit cost
                unit_cost = product.weighted_avg_cost or Decimal("0")
                total_cost = unit_cost * Decimal(str(to_consume))

                # Decrement inventory
                _decrement_inventory(product, to_consume, session)

                # Create consumption record with full snapshot
                consumption = MaterialConsumption(
                    assembly_run_id=assembly_run_id,
                    product_id=product.id,
                    quantity_consumed=to_consume,
                    unit_cost=unit_cost,
                    total_cost=total_cost,
                    # Snapshot fields
                    product_name=product.display_name,
                    material_name=material.name,
                    subcategory_name=material.subcategory.name if material.subcategory else "",
                    category_name=(
                        material.subcategory.category.name
                        if material.subcategory and material.subcategory.category
                        else ""
                    ),
                    supplier_name=product.supplier.name if product.supplier else None,
                )
                session.add(consumption)
                consumptions.append(consumption)

                remaining_to_consume -= to_consume

        elif comp.material_id:
            # Generic Material - use assigned product(s) with split allocation support
            if comp.id not in material_assignments:
                raise MaterialAssignmentRequiredError(
                    comp.material_component.name if comp.material_component else "Unknown",
                    comp.id,
                )

            material = session.query(Material).filter_by(id=comp.material_id).first()
            if not material:
                raise ValidationError([f"Material {comp.material_id} not found"])

            base_units_needed = comp.component_quantity * assembly_quantity

            # Get allocations - support both old and new format
            allocations = material_assignments[comp.id]
            if isinstance(allocations, int):
                # Legacy format: single product_id - convert to new format
                allocations = {allocations: base_units_needed}

            # Process each allocation (supports split across multiple products)
            for product_id, quantity_to_use in allocations.items():
                product = session.query(MaterialProduct).filter_by(id=product_id).first()
                if not product:
                    raise ValidationError([f"Assigned product {product_id} not found"])

                # Get unit cost
                unit_cost = product.weighted_avg_cost or Decimal("0")
                total_cost = unit_cost * Decimal(str(quantity_to_use))

                # Decrement inventory
                _decrement_inventory(product, quantity_to_use, session)

                # Create consumption record with full snapshot
                consumption = MaterialConsumption(
                    assembly_run_id=assembly_run_id,
                    product_id=product.id,
                    quantity_consumed=quantity_to_use,
                    unit_cost=unit_cost,
                    total_cost=total_cost,
                    # Snapshot fields
                    product_name=product.display_name,
                    material_name=material.name,
                    subcategory_name=material.subcategory.name if material.subcategory else "",
                    category_name=(
                        material.subcategory.category.name
                        if material.subcategory and material.subcategory.category
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
    """Find generic materials requiring resolution for a FinishedGood.

    Identifies compositions with generic Material placeholders (material_id set)
    that need a specific product selected before assembly.

    Args:
        finished_good_id: FinishedGood to check
        session: Optional database session

    Returns:
        List of dicts with:
            - composition_id: int
            - material_id: int
            - material_name: str
            - quantity_needed: float
            - available_products: List of available products with inventory

    Example:
        >>> pending = get_pending_materials(fg.id)
        >>> for p in pending:
        ...     print(f"{p['material_name']} needs {p['quantity_needed']}")
        ...     for prod in p['available_products']:
        ...         print(f"  - {prod['name']}: {prod['available_inventory']}")
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

    Validates both specific MaterialUnit components and generic Material
    placeholders with their assigned products. Supports split allocation
    where a material need can be fulfilled from multiple products.

    Args:
        finished_good_id: FinishedGood being assembled
        assembly_quantity: Number of assemblies
        material_assignments: Dict mapping composition_id to either:
            - int (legacy): single product_id (system calculates quantity)
            - Dict[int, float] (new): {product_id: quantity_to_use, ...}
              for split allocation across multiple products
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
            assembly_run_id, finished_good_id, assembly_quantity,
            material_assignments, session
        )
    with session_scope() as sess:
        return _record_material_consumption_impl(
            assembly_run_id, finished_good_id, assembly_quantity,
            material_assignments, sess
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
