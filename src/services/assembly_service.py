"""
Assembly Service for recording assembly runs.

This module provides functions for:
- Checking component availability before assembly (FinishedUnits, packaging, nested FGs)
- Recording assembly with component consumption
- Creating assembly runs with consumption ledger entries
- Tracking component costs

The service integrates with:
- Composition model for BOM discovery
- FinishedUnit and FinishedGood inventory tracking
- inventory_item_service.consume_fifo() for packaging consumption
- AssemblyRun and consumption models for persistence

Feature 013: Production & Inventory Tracking
"""

from typing import Dict, Any, List, Optional
from decimal import Decimal
from datetime import datetime

from sqlalchemy.orm import joinedload

from src.models import (
    AssemblyRun,
    AssemblyFinishedUnitConsumption,
    AssemblyPackagingConsumption,
    FinishedGood,
    FinishedUnit,
    Composition,
    Product,
    Event,
)
from src.services.database import session_scope
from src.services import inventory_item_service


# =============================================================================
# Custom Exceptions
# =============================================================================


class FinishedGoodNotFoundError(Exception):
    """Raised when a finished good cannot be found."""

    def __init__(self, finished_good_id: int):
        self.finished_good_id = finished_good_id
        super().__init__(f"FinishedGood with ID {finished_good_id} not found")


class InsufficientFinishedUnitError(Exception):
    """Raised when there is insufficient FinishedUnit inventory."""

    def __init__(self, finished_unit_id: int, needed: int, available: int):
        self.finished_unit_id = finished_unit_id
        self.needed = needed
        self.available = available
        super().__init__(
            f"Insufficient FinishedUnit {finished_unit_id}: need {needed}, have {available}"
        )


class InsufficientFinishedGoodError(Exception):
    """Raised when there is insufficient FinishedGood inventory (nested assembly)."""

    def __init__(self, finished_good_id: int, needed: int, available: int):
        self.finished_good_id = finished_good_id
        self.needed = needed
        self.available = available
        super().__init__(
            f"Insufficient FinishedGood {finished_good_id}: need {needed}, have {available}"
        )


class InsufficientPackagingError(Exception):
    """Raised when there is insufficient packaging inventory."""

    def __init__(self, product_id: int, needed: Decimal, available: Decimal):
        self.product_id = product_id
        self.needed = needed
        self.available = available
        super().__init__(
            f"Insufficient packaging product {product_id}: need {needed}, have {available}"
        )


class EventNotFoundError(Exception):
    """Raised when an event cannot be found."""

    def __init__(self, event_id: int):
        self.event_id = event_id
        super().__init__(f"Event with ID {event_id} not found")


# =============================================================================
# Availability Check Functions
# =============================================================================


def check_can_assemble(
    finished_good_id: int,
    quantity: int,
    *,
    session=None,
) -> Dict[str, Any]:
    """
    Check if a FinishedGood can be assembled with current component inventory.

    Checks availability of:
    - FinishedUnit components (via inventory_count)
    - FinishedGood components (nested assemblies, via inventory_count)
    - Packaging products (via consume_fifo dry_run)

    Args:
        finished_good_id: ID of the FinishedGood to assemble
        quantity: Number of FinishedGoods to assemble
        session: Optional database session (uses session_scope if not provided)

    Returns:
        Dict with keys:
            - "can_assemble" (bool): True if all components available
            - "missing" (List[Dict]): List of missing components with details:
                - component_type: "finished_unit" | "finished_good" | "packaging"
                - component_id: int
                - component_name: str
                - needed: int or Decimal
                - available: int or Decimal
                - unit: str (for packaging only)

    Raises:
        FinishedGoodNotFoundError: If finished good doesn't exist
    """
    # Use provided session or create a new one
    if session is not None:
        return _check_can_assemble_impl(finished_good_id, quantity, session)
    with session_scope() as session:
        return _check_can_assemble_impl(finished_good_id, quantity, session)


def _check_can_assemble_impl(
    finished_good_id: int,
    quantity: int,
    session,
) -> Dict[str, Any]:
    """Implementation of check_can_assemble that uses provided session."""
    # Validate FinishedGood exists
    finished_good = session.query(FinishedGood).filter_by(id=finished_good_id).first()
    if not finished_good:
        raise FinishedGoodNotFoundError(finished_good_id)

    # Query Composition for this FinishedGood's components
    compositions = (
        session.query(Composition)
        .filter(Composition.assembly_id == finished_good_id)
        .all()
    )

    missing = []

    for comp in compositions:
        if comp.finished_unit_id:
            # FinishedUnit component
            fu = session.query(FinishedUnit).filter_by(id=comp.finished_unit_id).first()
            if fu:
                needed = int(comp.component_quantity * quantity)
                if fu.inventory_count < needed:
                    missing.append(
                        {
                            "component_type": "finished_unit",
                            "component_id": fu.id,
                            "component_name": fu.display_name,
                            "needed": needed,
                            "available": fu.inventory_count,
                        }
                    )

        elif comp.finished_good_id:
            # FinishedGood component (nested assembly)
            nested_fg = session.query(FinishedGood).filter_by(id=comp.finished_good_id).first()
            if nested_fg:
                needed = int(comp.component_quantity * quantity)
                if nested_fg.inventory_count < needed:
                    missing.append(
                        {
                            "component_type": "finished_good",
                            "component_id": nested_fg.id,
                            "component_name": nested_fg.display_name,
                            "needed": needed,
                            "available": nested_fg.inventory_count,
                        }
                    )

        elif comp.packaging_product_id:
            # Packaging product - check via consume_fifo dry_run
            # Pass session to maintain transactional consistency
            product = session.query(Product).filter_by(id=comp.packaging_product_id).first()
            if product and product.ingredient:
                ingredient_slug = product.ingredient.slug
                needed = Decimal(str(comp.component_quantity * quantity))
                # For packaging, target_unit is the product's package_unit
                target_unit = product.package_unit
                result = inventory_item_service.consume_fifo(
                    ingredient_slug, needed, target_unit, dry_run=True, session=session
                )
                if not result["satisfied"]:
                    missing.append(
                        {
                            "component_type": "packaging",
                            "component_id": product.id,
                            "component_name": product.display_name,
                            "needed": needed,
                            "available": result["consumed"],
                            "unit": target_unit,
                        }
                    )

    return {
        "can_assemble": len(missing) == 0,
        "missing": missing,
    }


# =============================================================================
# Assembly Recording Functions
# =============================================================================


def record_assembly(
    finished_good_id: int,
    quantity: int,
    *,
    assembled_at: Optional[datetime] = None,
    notes: Optional[str] = None,
    event_id: Optional[int] = None,
    session=None,
) -> Dict[str, Any]:
    """
    Record an assembly run with component consumption.

    This function atomically:
    1. Validates FinishedGood exists
    2. Validates event exists if provided (Feature 016)
    3. Decrements FinishedUnit.inventory_count for FU components
    4. Decrements FinishedGood.inventory_count for nested FG components
    5. Consumes packaging via FIFO
    6. Increments the target FinishedGood.inventory_count
    7. Creates AssemblyRun and consumption ledger records

    Args:
        finished_good_id: ID of the FinishedGood being assembled
        quantity: Number of FinishedGoods to assemble
        assembled_at: Optional assembly timestamp (defaults to now)
        notes: Optional assembly notes
        event_id: Optional event ID to link assembly to (Feature 016)
        session: Optional database session (uses session_scope if not provided)

    Returns:
        Dict with keys:
            - "assembly_run_id": int
            - "finished_good_id": int
            - "quantity_assembled": int
            - "total_component_cost": Decimal
            - "per_unit_cost": Decimal
            - "finished_unit_consumptions": List[Dict]
            - "packaging_consumptions": List[Dict]
            - "event_id": Optional[int] - linked event ID (Feature 016)

    Raises:
        FinishedGoodNotFoundError: If finished good doesn't exist
        InsufficientFinishedUnitError: If FU inventory is insufficient
        InsufficientFinishedGoodError: If nested FG inventory is insufficient
        InsufficientPackagingError: If packaging inventory is insufficient
        EventNotFoundError: If event_id is provided but event doesn't exist
    """
    # Use provided session or create a new one
    if session is not None:
        return _record_assembly_impl(
            finished_good_id, quantity, assembled_at, notes, event_id, session
        )
    with session_scope() as session:
        return _record_assembly_impl(
            finished_good_id, quantity, assembled_at, notes, event_id, session
        )


def _record_assembly_impl(
    finished_good_id: int,
    quantity: int,
    assembled_at: Optional[datetime],
    notes: Optional[str],
    event_id: Optional[int],
    session,
) -> Dict[str, Any]:
    """Implementation of record_assembly that uses provided session."""
    # Validate FinishedGood exists
    finished_good = session.query(FinishedGood).filter_by(id=finished_good_id).first()
    if not finished_good:
        raise FinishedGoodNotFoundError(finished_good_id)

    # Feature 016: Validate event exists if event_id provided
    if event_id is not None:
        event = session.query(Event).filter_by(id=event_id).first()
        if not event:
            raise EventNotFoundError(event_id)

    # Query Composition for this FinishedGood's components
    compositions = (
        session.query(Composition)
        .filter(Composition.assembly_id == finished_good_id)
        .all()
    )

    # Track consumption data
    total_component_cost = Decimal("0.0000")
    fu_consumptions = []
    pkg_consumptions = []

    # Process each component
    for comp in compositions:
        if comp.finished_unit_id:
            # FinishedUnit component - decrement inventory_count
            fu = session.query(FinishedUnit).filter_by(id=comp.finished_unit_id).first()
            if fu:
                needed = int(comp.component_quantity * quantity)
                if fu.inventory_count < needed:
                    raise InsufficientFinishedUnitError(
                        fu.id, needed, fu.inventory_count
                    )

                # Capture cost before decrementing
                unit_cost = fu.unit_cost or Decimal("0.0000")
                cost = unit_cost * Decimal(str(needed))

                fu.inventory_count -= needed
                total_component_cost += cost

                fu_consumptions.append(
                    {
                        "finished_unit_id": fu.id,
                        "quantity_consumed": needed,
                        "unit_cost_at_consumption": unit_cost,
                        "total_cost": cost,
                    }
                )

        elif comp.finished_good_id:
            # FinishedGood component (nested assembly) - decrement inventory_count
            # KNOWN LIMITATION: No consumption ledger entry is created for nested FGs.
            # See docs/known_limitations.md for details and future enhancement plan.
            nested_fg = session.query(FinishedGood).filter_by(id=comp.finished_good_id).first()
            if nested_fg:
                needed = int(comp.component_quantity * quantity)
                if nested_fg.inventory_count < needed:
                    raise InsufficientFinishedGoodError(
                        nested_fg.id, needed, nested_fg.inventory_count
                    )

                # Capture cost (FinishedGood uses total_cost as unit cost)
                unit_cost = nested_fg.total_cost or Decimal("0.0000")
                cost = unit_cost * Decimal(str(needed))

                nested_fg.inventory_count -= needed
                total_component_cost += cost

        elif comp.packaging_product_id:
            # Packaging product - consume via FIFO (same session for atomicity)
            product = session.query(Product).filter_by(id=comp.packaging_product_id).first()
            if product and product.ingredient:
                ingredient = product.ingredient

                # Validate that the ingredient is marked as packaging material
                if not getattr(ingredient, 'is_packaging', False):
                    raise ValueError(
                        f"Product '{product.display_name}' ({ingredient.display_name}) "
                        f"is not marked as packaging material"
                    )

                ingredient_slug = ingredient.slug
                needed = Decimal(str(comp.component_quantity * quantity))
                # For packaging, target_unit is the product's package_unit
                target_unit = product.package_unit

                # Pass session for atomic transaction
                result = inventory_item_service.consume_fifo(
                    ingredient_slug, needed, target_unit, dry_run=False, session=session
                )
                if not result["satisfied"]:
                    raise InsufficientPackagingError(
                        product.id, needed, result["consumed"]
                    )

                total_component_cost += result["total_cost"]
                pkg_consumptions.append(
                    {
                        "product_id": product.id,
                        "quantity_consumed": needed,
                        "unit": target_unit,
                        "total_cost": result["total_cost"],
                    }
                )

    # Increment FinishedGood inventory (same session, atomic with consumption)
    finished_good.inventory_count += quantity

    # Calculate per-unit cost
    per_unit_cost = total_component_cost / Decimal(str(quantity)) if quantity > 0 else Decimal("0.0000")

    # Create AssemblyRun record
    assembly_run = AssemblyRun(
        finished_good_id=finished_good_id,
        quantity_assembled=quantity,
        assembled_at=assembled_at or datetime.utcnow(),
        notes=notes,
        total_component_cost=total_component_cost,
        per_unit_cost=per_unit_cost,
        event_id=event_id,  # Feature 016
    )
    session.add(assembly_run)
    session.flush()  # Get the ID

    # Create consumption ledger records
    for fu_data in fu_consumptions:
        consumption = AssemblyFinishedUnitConsumption(
            assembly_run_id=assembly_run.id,
            finished_unit_id=fu_data["finished_unit_id"],
            quantity_consumed=fu_data["quantity_consumed"],
            unit_cost_at_consumption=fu_data["unit_cost_at_consumption"],
            total_cost=fu_data["total_cost"],
        )
        session.add(consumption)

    for pkg_data in pkg_consumptions:
        consumption = AssemblyPackagingConsumption(
            assembly_run_id=assembly_run.id,
            product_id=pkg_data["product_id"],
            quantity_consumed=pkg_data["quantity_consumed"],
            unit=pkg_data["unit"],
            total_cost=pkg_data["total_cost"],
        )
        session.add(consumption)

    # Commit happens automatically via session_scope

    return {
        "assembly_run_id": assembly_run.id,
        "finished_good_id": finished_good_id,
        "quantity_assembled": quantity,
        "total_component_cost": total_component_cost,
        "per_unit_cost": per_unit_cost,
        "finished_unit_consumptions": fu_consumptions,
        "packaging_consumptions": pkg_consumptions,
        "event_id": event_id,  # Feature 016
    }


# =============================================================================
# Custom Exception for History Queries
# =============================================================================


class AssemblyRunNotFoundError(Exception):
    """Raised when an assembly run cannot be found."""

    def __init__(self, assembly_run_id: int):
        self.assembly_run_id = assembly_run_id
        super().__init__(f"AssemblyRun with ID {assembly_run_id} not found")


# =============================================================================
# History Query Functions
# =============================================================================


def get_assembly_history(
    *,
    finished_good_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 100,
    offset: int = 0,
    include_consumptions: bool = False,
    session=None,
) -> List[Dict[str, Any]]:
    """
    Query assembly run history with optional filters.

    Args:
        finished_good_id: Optional filter by finished good ID
        start_date: Optional filter by minimum assembled_at
        end_date: Optional filter by maximum assembled_at
        limit: Maximum number of results (default 100)
        offset: Number of results to skip (for pagination)
        include_consumptions: If True, include consumption ledger details
        session: Optional database session

    Returns:
        List of assembly run dictionaries with details
    """
    with session_scope() as session:
        query = session.query(AssemblyRun)

        # Apply filters
        if finished_good_id:
            query = query.filter(AssemblyRun.finished_good_id == finished_good_id)
        if start_date:
            query = query.filter(AssemblyRun.assembled_at >= start_date)
        if end_date:
            query = query.filter(AssemblyRun.assembled_at <= end_date)

        # Eager load relationships to avoid N+1
        query = query.options(joinedload(AssemblyRun.finished_good))
        if include_consumptions:
            query = query.options(
                joinedload(AssemblyRun.finished_unit_consumptions).joinedload(
                    AssemblyFinishedUnitConsumption.finished_unit
                ),
                joinedload(AssemblyRun.packaging_consumptions).joinedload(
                    AssemblyPackagingConsumption.product
                ),
            )

        # Order and paginate
        query = query.order_by(AssemblyRun.assembled_at.desc())
        query = query.offset(offset).limit(limit)

        runs = query.all()
        return [_assembly_run_to_dict(run, include_consumptions) for run in runs]


def get_assembly_run(
    assembly_run_id: int,
    *,
    include_consumptions: bool = True,
    session=None,
) -> Dict[str, Any]:
    """
    Get a single assembly run with full details.

    Args:
        assembly_run_id: ID of the assembly run
        include_consumptions: If True, include consumption ledger details
        session: Optional database session

    Returns:
        Assembly run dictionary with details

    Raises:
        AssemblyRunNotFoundError: If assembly run doesn't exist
    """
    with session_scope() as session:
        query = session.query(AssemblyRun).filter(
            AssemblyRun.id == assembly_run_id
        )

        query = query.options(joinedload(AssemblyRun.finished_good))
        if include_consumptions:
            query = query.options(
                joinedload(AssemblyRun.finished_unit_consumptions).joinedload(
                    AssemblyFinishedUnitConsumption.finished_unit
                ),
                joinedload(AssemblyRun.packaging_consumptions).joinedload(
                    AssemblyPackagingConsumption.product
                ),
            )

        run = query.first()
        if not run:
            raise AssemblyRunNotFoundError(assembly_run_id)

        return _assembly_run_to_dict(run, include_consumptions)


def _assembly_run_to_dict(
    run: AssemblyRun, include_consumptions: bool = False
) -> Dict[str, Any]:
    """Convert an AssemblyRun to a dictionary representation."""
    result = {
        "id": run.id,
        "uuid": str(run.uuid) if run.uuid else None,
        "finished_good_id": run.finished_good_id,
        "quantity_assembled": run.quantity_assembled,
        "assembled_at": run.assembled_at.isoformat() if run.assembled_at else None,
        "notes": run.notes,
        "total_component_cost": str(run.total_component_cost),
        "per_unit_cost": str(run.per_unit_cost),
    }

    # Add relationship data
    if run.finished_good:
        result["finished_good"] = {
            "id": run.finished_good.id,
            "slug": run.finished_good.slug,
            "display_name": run.finished_good.display_name,
        }
        result["finished_good_name"] = run.finished_good.display_name

    if include_consumptions:
        # FinishedUnit consumptions
        if run.finished_unit_consumptions:
            result["finished_unit_consumptions"] = [
                {
                    "id": c.id,
                    "uuid": str(c.uuid) if c.uuid else None,
                    "finished_unit_id": c.finished_unit_id,
                    "finished_unit_name": c.finished_unit.display_name if c.finished_unit else None,
                    "quantity_consumed": c.quantity_consumed,
                    "unit_cost_at_consumption": str(c.unit_cost_at_consumption),
                    "total_cost": str(c.total_cost),
                }
                for c in run.finished_unit_consumptions
            ]

        # Packaging consumptions
        if run.packaging_consumptions:
            result["packaging_consumptions"] = [
                {
                    "id": c.id,
                    "uuid": str(c.uuid) if c.uuid else None,
                    "product_id": c.product_id,
                    "product_name": c.product.display_name if c.product else None,
                    "quantity_consumed": str(c.quantity_consumed),
                    "unit": c.unit,
                    "total_cost": str(c.total_cost),
                }
                for c in run.packaging_consumptions
            ]

    return result


# =============================================================================
# Import/Export Functions
# =============================================================================


def export_assembly_history(
    *,
    finished_good_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    session=None,
) -> Dict[str, Any]:
    """
    Export assembly history to JSON-compatible dict.

    Uses slugs instead of IDs for portability.
    Decimal values are serialized as strings to preserve precision.

    Args:
        finished_good_id: Optional filter by finished good ID
        start_date: Optional filter by minimum assembled_at
        end_date: Optional filter by maximum assembled_at
        session: Optional database session

    Returns:
        Dict with version, exported_at timestamp, and assembly_runs list
    """
    runs = get_assembly_history(
        finished_good_id=finished_good_id,
        start_date=start_date,
        end_date=end_date,
        include_consumptions=True,
        limit=10000,  # Export all matching
    )

    exported_runs = []
    for run in runs:
        exported_run = {
            "uuid": run.get("uuid"),
            "finished_good_slug": run.get("finished_good", {}).get("slug"),
            "quantity_assembled": run["quantity_assembled"],
            "assembled_at": run["assembled_at"],
            "notes": run.get("notes"),
            "total_component_cost": run["total_component_cost"],
            "per_unit_cost": run["per_unit_cost"],
            "finished_unit_consumptions": [
                {
                    "uuid": c.get("uuid"),
                    "finished_unit_id": c["finished_unit_id"],
                    "finished_unit_name": c.get("finished_unit_name"),
                    "quantity_consumed": c["quantity_consumed"],
                    "unit_cost_at_consumption": c["unit_cost_at_consumption"],
                    "total_cost": c["total_cost"],
                }
                for c in run.get("finished_unit_consumptions", [])
            ],
            "packaging_consumptions": [
                {
                    "uuid": c.get("uuid"),
                    "product_id": c["product_id"],
                    "product_name": c.get("product_name"),
                    "quantity_consumed": c["quantity_consumed"],
                    "unit": c.get("unit"),
                    "total_cost": c["total_cost"],
                }
                for c in run.get("packaging_consumptions", [])
            ],
        }
        exported_runs.append(exported_run)

    return {
        "version": "1.0",
        "exported_at": datetime.utcnow().isoformat(),
        "assembly_runs": exported_runs,
    }


def import_assembly_history(
    data: Dict[str, Any],
    *,
    skip_duplicates: bool = True,
    session=None,
) -> Dict[str, Any]:
    """
    Import assembly history from JSON-compatible dict.

    Resolves references by slug. Validates all foreign keys exist.
    Uses UUIDs for duplicate detection.

    Args:
        data: Dict with assembly_runs to import
        skip_duplicates: If True, skip existing UUIDs; if False, report as error
        session: Optional database session

    Returns:
        Dict with imported count, skipped count, and errors list
    """
    imported = 0
    skipped = 0
    errors = []

    with session_scope() as session:
        for run_data in data.get("assembly_runs", []):
            try:
                run_uuid = run_data.get("uuid")

                # Check for duplicate by UUID if provided
                if run_uuid:
                    existing = (
                        session.query(AssemblyRun).filter_by(uuid=run_uuid).first()
                    )
                    if existing:
                        if skip_duplicates:
                            skipped += 1
                            continue
                        else:
                            errors.append(f"Duplicate UUID: {run_uuid}")
                            continue

                # Resolve finished_good by slug
                fg_slug = run_data.get("finished_good_slug")
                finished_good = (
                    session.query(FinishedGood).filter_by(slug=fg_slug).first()
                )
                if not finished_good:
                    errors.append(f"FinishedGood not found: {fg_slug}")
                    continue

                # Create AssemblyRun
                run = AssemblyRun(
                    uuid=run_uuid,
                    finished_good_id=finished_good.id,
                    quantity_assembled=run_data["quantity_assembled"],
                    assembled_at=datetime.fromisoformat(run_data["assembled_at"]),
                    notes=run_data.get("notes"),
                    total_component_cost=Decimal(run_data["total_component_cost"]),
                    per_unit_cost=Decimal(run_data["per_unit_cost"]),
                )
                session.add(run)
                session.flush()  # Get ID

                # Create finished_unit consumptions
                for c_data in run_data.get("finished_unit_consumptions", []):
                    consumption = AssemblyFinishedUnitConsumption(
                        uuid=c_data.get("uuid"),
                        assembly_run_id=run.id,
                        finished_unit_id=c_data["finished_unit_id"],
                        quantity_consumed=c_data["quantity_consumed"],
                        unit_cost_at_consumption=Decimal(
                            c_data["unit_cost_at_consumption"]
                        ),
                        total_cost=Decimal(c_data["total_cost"]),
                    )
                    session.add(consumption)

                # Create packaging consumptions
                for c_data in run_data.get("packaging_consumptions", []):
                    consumption = AssemblyPackagingConsumption(
                        uuid=c_data.get("uuid"),
                        assembly_run_id=run.id,
                        product_id=c_data["product_id"],
                        quantity_consumed=Decimal(c_data["quantity_consumed"]),
                        unit=c_data.get("unit", ""),
                        total_cost=Decimal(c_data["total_cost"]),
                    )
                    session.add(consumption)

                imported += 1

            except Exception as e:
                errors.append(
                    f"Error importing {run_data.get('uuid', 'unknown')}: {str(e)}"
                )

    return {
        "imported": imported,
        "skipped": skipped,
        "errors": errors,
    }
