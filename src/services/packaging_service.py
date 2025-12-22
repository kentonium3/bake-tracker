"""
Packaging Service - Generic packaging operations for deferred packaging decisions.

Feature 026: Deferred Packaging Decisions

This module provides functions for:
- Getting distinct generic product types (by product_name)
- Calculating inventory summaries across product variants
- Estimating costs based on average prices
- Managing material assignments to generic requirements
- Finding pending (unassigned) packaging requirements

The service integrates with:
- Product model for packaging product data
- Composition model for generic requirement tracking
- CompositionAssignment model for material assignments
- InventoryItem for availability checks
"""

from typing import Dict, Any, List, Optional
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime
import logging

from sqlalchemy.orm import Session
from sqlalchemy import func

from src.services.database import session_scope
from src.models import (
    Product,
    Ingredient,
    InventoryItem,
    Composition,
    CompositionAssignment,
)
from src.models.event import EventAssemblyTarget, EventRecipientPackage

logger = logging.getLogger(__name__)


# =============================================================================
# Custom Exceptions
# =============================================================================


class PackagingServiceError(Exception):
    """Base exception for packaging service errors."""

    pass


class GenericProductNotFoundError(PackagingServiceError):
    """Raised when a generic product type is not found."""

    def __init__(self, product_name: str):
        self.product_name = product_name
        super().__init__(f"No packaging products found with product_name '{product_name}'")


class CompositionNotFoundError(PackagingServiceError):
    """Raised when a composition is not found."""

    def __init__(self, composition_id: int):
        self.composition_id = composition_id
        super().__init__(f"Composition with ID {composition_id} not found")


class NotGenericCompositionError(PackagingServiceError):
    """Raised when operation requires a generic composition but found non-generic."""

    def __init__(self, composition_id: int):
        self.composition_id = composition_id
        super().__init__(f"Composition {composition_id} is not a generic composition")


class InvalidAssignmentError(PackagingServiceError):
    """Raised when assignment validation fails."""

    pass


class InsufficientInventoryError(PackagingServiceError):
    """Raised when there is insufficient inventory for assignment."""

    def __init__(self, inventory_item_id: int, requested: float, available: float):
        self.inventory_item_id = inventory_item_id
        self.requested = requested
        self.available = available
        super().__init__(
            f"Insufficient inventory for item {inventory_item_id}: "
            f"requested {requested}, available {available}"
        )


class ProductMismatchError(PackagingServiceError):
    """Raised when assigned product doesn't match the generic requirement."""

    def __init__(self, expected_name: str, actual_name: str):
        self.expected_name = expected_name
        self.actual_name = actual_name
        super().__init__(f"Product name mismatch: expected '{expected_name}', got '{actual_name}'")


# =============================================================================
# Generic Product Discovery
# =============================================================================


def get_generic_products(*, session: Optional[Session] = None) -> List[str]:
    """
    Get distinct product_name values for packaging products with inventory.

    These represent the generic product types available for deferred selection.

    Args:
        session: Optional database session

    Returns:
        List of distinct product_name values, sorted alphabetically
    """

    def _impl(s: Session) -> List[str]:
        # Query distinct product_name values from Products
        # that are linked to ingredients where is_packaging=True
        # and have inventory > 0
        result = (
            s.query(Product.product_name)
            .join(Ingredient, Product.ingredient_id == Ingredient.id)
            .join(InventoryItem, InventoryItem.product_id == Product.id)
            .filter(Ingredient.is_packaging == True)
            .filter(Product.product_name.isnot(None))
            .filter(Product.product_name != "")
            .filter(InventoryItem.quantity > 0)
            .distinct()
            .order_by(Product.product_name)
            .all()
        )
        return [row[0] for row in result]

    if session is not None:
        return _impl(session)
    with session_scope() as s:
        return _impl(s)


def get_generic_inventory_summary(
    product_name: str, *, session: Optional[Session] = None
) -> Dict[str, Any]:
    """
    Get inventory summary for a generic product type.

    Returns total quantity available and breakdown by brand/variant.

    Args:
        product_name: The generic product type name (e.g., "Cellophane Bags 6x10")
        session: Optional database session

    Returns:
        Dict with:
        - 'total': Total quantity available across all variants
        - 'breakdown': List of dicts with brand, product_id, and available quantity

    Raises:
        GenericProductNotFoundError: If no products match the product_name
    """

    def _impl(s: Session) -> Dict[str, Any]:
        # Find all packaging products with this product_name
        products = (
            s.query(Product)
            .join(Ingredient, Product.ingredient_id == Ingredient.id)
            .filter(Ingredient.is_packaging == True)
            .filter(Product.product_name == product_name)
            .all()
        )

        if not products:
            raise GenericProductNotFoundError(product_name)

        breakdown = []
        total = Decimal("0")

        for product in products:
            # Sum inventory for this product (quantity is the field, not remaining_quantity)
            available = (
                s.query(func.coalesce(func.sum(InventoryItem.quantity), 0))
                .filter(InventoryItem.product_id == product.id)
                .filter(InventoryItem.quantity > 0)
                .scalar()
            ) or Decimal("0")

            if available > 0:
                breakdown.append(
                    {
                        "brand": product.brand or "(No brand)",
                        "product_id": product.id,
                        "available": float(available),
                    }
                )
                total += Decimal(str(available))

        return {
            "total": float(total),
            "breakdown": sorted(breakdown, key=lambda x: x["brand"]),
        }

    if session is not None:
        return _impl(session)
    with session_scope() as s:
        return _impl(s)


def get_available_inventory_items(
    product_name: str, *, session: Optional[Session] = None
) -> List[Dict[str, Any]]:
    """
    Get available inventory items for a generic product type.

    Returns individual inventory items (not aggregated by product) for use in
    the assignment dialog where users select specific inventory to assign.

    Args:
        product_name: The generic product type name (e.g., "Cellophane Bags 6x10")
        session: Optional database session

    Returns:
        List of dicts with:
        - 'inventory_item_id': ID of the inventory item
        - 'product_id': ID of the product
        - 'brand': Product brand
        - 'available': Available quantity
        - 'unit_cost': Cost per unit

    Raises:
        GenericProductNotFoundError: If no products match the product_name
    """

    def _impl(s: Session) -> List[Dict[str, Any]]:
        # Find all packaging products with this product_name
        products = (
            s.query(Product)
            .join(Ingredient, Product.ingredient_id == Ingredient.id)
            .filter(Ingredient.is_packaging == True)
            .filter(Product.product_name == product_name)
            .all()
        )

        if not products:
            raise GenericProductNotFoundError(product_name)

        items = []
        product_ids = [p.id for p in products]

        # Get all inventory items with quantity > 0
        inventory_items = (
            s.query(InventoryItem)
            .filter(InventoryItem.product_id.in_(product_ids))
            .filter(InventoryItem.quantity > 0)
            .all()
        )

        for inv_item in inventory_items:
            product = inv_item.product
            items.append(
                {
                    "inventory_item_id": inv_item.id,
                    "product_id": product.id,
                    "brand": product.brand or "(No brand)",
                    "available": float(inv_item.quantity),
                    "unit_cost": float(inv_item.unit_cost) if inv_item.unit_cost else 0.0,
                }
            )

        return sorted(items, key=lambda x: x["brand"])

    if session is not None:
        return _impl(session)
    with session_scope() as s:
        return _impl(s)


# =============================================================================
# Cost Estimation
# =============================================================================


def get_estimated_cost(
    product_name: str, quantity: float, *, session: Optional[Session] = None
) -> float:
    """
    Calculate estimated cost for a generic packaging requirement.

    Uses weighted average price across all inventory items with matching product_name,
    weighted by their current quantities.

    Args:
        product_name: The generic product type name
        quantity: Number of units needed
        session: Optional database session

    Returns:
        Estimated total cost (quantity * weighted average unit price)

    Raises:
        GenericProductNotFoundError: If no products match the product_name
    """

    def _impl(s: Session) -> float:
        # Find all packaging products with this product_name
        products = (
            s.query(Product)
            .join(Ingredient, Product.ingredient_id == Ingredient.id)
            .filter(Ingredient.is_packaging == True)
            .filter(Product.product_name == product_name)
            .all()
        )

        if not products:
            raise GenericProductNotFoundError(product_name)

        # Calculate weighted average based on inventory items
        total_inventory = Decimal("0")
        weighted_sum = Decimal("0")

        for product in products:
            # Get inventory items for this product
            inv_items = (
                s.query(InventoryItem)
                .filter(InventoryItem.product_id == product.id)
                .filter(InventoryItem.quantity > 0)
                .all()
            )

            for item in inv_items:
                if item.unit_cost is not None and item.unit_cost > 0:
                    qty_decimal = Decimal(str(item.quantity))
                    price = Decimal(str(item.unit_cost))
                    weighted_sum += qty_decimal * price
                    total_inventory += qty_decimal

        if total_inventory == 0:
            # No inventory with valid costs - use product's current cost per unit
            prices = []
            for p in products:
                cost = p.get_current_cost_per_unit()
                if cost > 0:
                    prices.append(Decimal(str(cost)))
            if not prices:
                return 0.0
            avg_price = sum(prices) / len(prices)
        else:
            avg_price = weighted_sum / total_inventory

        result = avg_price * Decimal(str(quantity))
        return float(result.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

    if session is not None:
        return _impl(session)
    with session_scope() as s:
        return _impl(s)


def get_actual_cost(composition_id: int, *, session: Optional[Session] = None) -> float:
    """
    Calculate actual cost for a composition.

    For generic compositions: sums the cost of all assigned inventory items.
    For non-generic compositions: uses the product's current cost per unit.

    Args:
        composition_id: ID of the composition
        session: Optional database session

    Returns:
        Total actual cost from assignments or product cost

    Raises:
        CompositionNotFoundError: If composition doesn't exist
    """

    def _impl(s: Session) -> float:
        composition = s.query(Composition).filter_by(id=composition_id).first()
        if not composition:
            raise CompositionNotFoundError(composition_id)

        # For non-generic compositions, use the product's current cost per unit
        if not composition.is_generic:
            if composition.packaging_product:
                unit_cost = composition.packaging_product.get_current_cost_per_unit()
                return float(unit_cost * composition.component_quantity)
            return 0.0

        # Get all assignments and sum their costs
        assignments = s.query(CompositionAssignment).filter_by(composition_id=composition_id).all()

        total = Decimal("0")
        for assignment in assignments:
            if assignment.inventory_item:
                unit_cost = Decimal(str(assignment.inventory_item.unit_cost or 0))
                qty = Decimal(str(assignment.quantity_assigned))
                total += unit_cost * qty

        return float(total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

    if session is not None:
        return _impl(session)
    with session_scope() as s:
        return _impl(s)


# =============================================================================
# Material Assignment
# =============================================================================


def assign_materials(
    composition_id: int, assignments: List[Dict[str, Any]], *, session: Optional[Session] = None
) -> bool:
    """
    Create assignment records linking specific inventory to a generic requirement.

    Validates that:
    1. Composition exists and has is_generic=True
    2. Sum of assigned quantities equals component_quantity
    3. Each quantity doesn't exceed available inventory
    4. All assigned products have matching product_name

    Args:
        composition_id: ID of the generic composition
        assignments: List of dicts with 'inventory_item_id' and 'quantity'
        session: Optional database session

    Returns:
        True if assignment successful

    Raises:
        CompositionNotFoundError: If composition doesn't exist
        NotGenericCompositionError: If composition is not generic
        InvalidAssignmentError: If assignment validation fails
        InsufficientInventoryError: If inventory is insufficient
        ProductMismatchError: If product_name doesn't match requirement
    """

    def _impl(s: Session) -> bool:
        # Validate composition exists and is generic
        composition = s.query(Composition).filter_by(id=composition_id).first()
        if not composition:
            raise CompositionNotFoundError(composition_id)
        if not composition.is_generic:
            raise NotGenericCompositionError(composition_id)

        # Validate assignments list
        if not assignments:
            raise InvalidAssignmentError("At least one assignment required")

        # Get the template product's product_name
        if not composition.packaging_product:
            raise InvalidAssignmentError("Generic composition has no packaging product template")
        expected_product_name = composition.packaging_product.product_name

        # Validate each assignment
        total_assigned = Decimal("0")
        assignment_records = []

        for assignment in assignments:
            if "inventory_item_id" not in assignment or "quantity" not in assignment:
                raise InvalidAssignmentError(
                    "Each assignment must have 'inventory_item_id' and 'quantity'"
                )

            inv_item_id = assignment["inventory_item_id"]
            qty = Decimal(str(assignment["quantity"]))

            if qty <= 0:
                raise InvalidAssignmentError("Assignment quantity must be positive")

            # Get inventory item
            inv_item = s.query(InventoryItem).filter_by(id=inv_item_id).first()
            if not inv_item:
                raise InvalidAssignmentError(f"Inventory item {inv_item_id} not found")

            # Check product_name matches
            if inv_item.product and inv_item.product.product_name != expected_product_name:
                raise ProductMismatchError(expected_product_name, inv_item.product.product_name)

            # Check available quantity
            available = Decimal(str(inv_item.quantity))
            if qty > available:
                raise InsufficientInventoryError(inv_item_id, float(qty), float(available))

            total_assigned += qty
            assignment_records.append({"inventory_item": inv_item, "quantity": qty})

        # Validate total matches required quantity
        required = Decimal(str(composition.component_quantity))
        if total_assigned != required:
            raise InvalidAssignmentError(
                f"Total assigned ({float(total_assigned)}) must equal "
                f"required quantity ({float(required)})"
            )

        # Clear any existing assignments
        s.query(CompositionAssignment).filter_by(composition_id=composition_id).delete()

        # Create new assignment records
        for record in assignment_records:
            assignment = CompositionAssignment(
                composition_id=composition_id,
                inventory_item_id=record["inventory_item"].id,
                quantity_assigned=float(record["quantity"]),
                assigned_at=datetime.utcnow(),
            )
            s.add(assignment)

        logger.info(
            f"Assigned {len(assignment_records)} inventory items to composition {composition_id}"
        )
        return True

    if session is not None:
        return _impl(session)
    with session_scope() as s:
        return _impl(s)


def clear_assignments(composition_id: int, *, session: Optional[Session] = None) -> int:
    """
    Clear all material assignments for a composition.

    Args:
        composition_id: ID of the composition
        session: Optional database session

    Returns:
        Number of assignments deleted

    Raises:
        CompositionNotFoundError: If composition doesn't exist
    """

    def _impl(s: Session) -> int:
        composition = s.query(Composition).filter_by(id=composition_id).first()
        if not composition:
            raise CompositionNotFoundError(composition_id)

        count = s.query(CompositionAssignment).filter_by(composition_id=composition_id).delete()
        logger.info(f"Cleared {count} assignments from composition {composition_id}")
        return count

    if session is not None:
        return _impl(session)
    with session_scope() as s:
        return _impl(s)


def get_assignments(
    composition_id: int, *, session: Optional[Session] = None
) -> List[Dict[str, Any]]:
    """
    Get all assignments for a composition.

    Args:
        composition_id: ID of the composition
        session: Optional database session

    Returns:
        List of assignment dicts with inventory_item_id, quantity, and details

    Raises:
        CompositionNotFoundError: If composition doesn't exist
    """

    def _impl(s: Session) -> List[Dict[str, Any]]:
        composition = s.query(Composition).filter_by(id=composition_id).first()
        if not composition:
            raise CompositionNotFoundError(composition_id)

        assignments = s.query(CompositionAssignment).filter_by(composition_id=composition_id).all()

        result = []
        for a in assignments:
            inv_item = a.inventory_item
            product = inv_item.product if inv_item else None
            result.append(
                {
                    "assignment_id": a.id,
                    "inventory_item_id": a.inventory_item_id,
                    "quantity_assigned": a.quantity_assigned,
                    "assigned_at": a.assigned_at.isoformat() if a.assigned_at else None,
                    "product_id": product.id if product else None,
                    "brand": product.brand if product else None,
                    "unit_cost": float(inv_item.unit_cost or 0) if inv_item else 0,
                    "total_cost": a.total_cost,
                }
            )

        return result

    if session is not None:
        return _impl(session)
    with session_scope() as s:
        return _impl(s)


# =============================================================================
# Pending Requirements Query
# =============================================================================


def get_pending_requirements(
    event_id: Optional[int] = None,
    assembly_id: Optional[int] = None,
    *,
    session: Optional[Session] = None,
) -> List[Dict[str, Any]]:
    """
    Find compositions where is_generic=True and not fully assigned.

    Args:
        event_id: Optional filter by event ID (via assembly/package relationships)
        assembly_id: Optional filter by specific assembly ID
        session: Optional database session

    Returns:
        List of dicts with composition details and assignment status
    """

    def _impl(s: Session) -> List[Dict[str, Any]]:
        query = (
            s.query(Composition)
            .filter(Composition.is_generic == True)
            .filter(Composition.packaging_product_id.isnot(None))
        )

        if assembly_id is not None:
            query = query.filter(Composition.assembly_id == assembly_id)

        if event_id is not None:
            # Get finished_good_ids from EventAssemblyTarget for this event
            assembly_ids = (
                s.query(EventAssemblyTarget.finished_good_id)
                .filter(EventAssemblyTarget.event_id == event_id)
                .subquery()
            )
            # Get package_ids from EventRecipientPackage for this event
            package_ids = (
                s.query(EventRecipientPackage.package_id)
                .filter(EventRecipientPackage.event_id == event_id)
                .distinct()
                .subquery()
            )
            # Filter compositions that belong to this event
            from sqlalchemy import or_
            query = query.filter(
                or_(
                    Composition.assembly_id.in_(assembly_ids),
                    Composition.package_id.in_(package_ids),
                )
            )

        compositions = query.all()

        result = []
        for comp in compositions:
            # Check if fully assigned
            assigned_qty = (
                s.query(func.coalesce(func.sum(CompositionAssignment.quantity_assigned), 0))
                .filter(CompositionAssignment.composition_id == comp.id)
                .scalar()
            ) or 0

            required_qty = comp.component_quantity
            is_fully_assigned = float(assigned_qty) >= float(required_qty)

            if not is_fully_assigned:
                product = comp.packaging_product
                result.append(
                    {
                        "composition_id": comp.id,
                        "assembly_id": comp.assembly_id,
                        "package_id": comp.package_id,
                        "product_name": product.product_name if product else None,
                        "required_quantity": required_qty,
                        "assigned_quantity": float(assigned_qty),
                        "remaining": required_qty - float(assigned_qty),
                    }
                )

        return result

    if session is not None:
        return _impl(session)
    with session_scope() as s:
        return _impl(s)


def is_fully_assigned(composition_id: int, *, session: Optional[Session] = None) -> bool:
    """
    Check if a generic composition has complete material assignments.

    Args:
        composition_id: ID of the composition to check
        session: Optional database session

    Returns:
        True if assignments exist and total matches required quantity

    Raises:
        CompositionNotFoundError: If composition doesn't exist
    """

    def _impl(s: Session) -> bool:
        composition = s.query(Composition).filter_by(id=composition_id).first()
        if not composition:
            raise CompositionNotFoundError(composition_id)

        # Non-generic compositions are always "fully assigned"
        if not composition.is_generic:
            return True

        # Sum assigned quantities
        assigned_qty = (
            s.query(func.coalesce(func.sum(CompositionAssignment.quantity_assigned), 0))
            .filter(CompositionAssignment.composition_id == composition_id)
            .scalar()
        ) or 0

        required_qty = composition.component_quantity
        return float(assigned_qty) >= float(required_qty)

    if session is not None:
        return _impl(session)
    with session_scope() as s:
        return _impl(s)


def get_assignment_summary(
    composition_id: int, *, session: Optional[Session] = None
) -> Dict[str, Any]:
    """
    Get a summary of assignment status for a composition.

    Args:
        composition_id: ID of the composition
        session: Optional database session

    Returns:
        Dict with required, assigned, remaining, and is_complete fields

    Raises:
        CompositionNotFoundError: If composition doesn't exist
    """

    def _impl(s: Session) -> Dict[str, Any]:
        composition = s.query(Composition).filter_by(id=composition_id).first()
        if not composition:
            raise CompositionNotFoundError(composition_id)

        # Get product_name from packaging_product
        product_name = None
        if composition.packaging_product:
            product_name = composition.packaging_product.product_name

        if not composition.is_generic:
            return {
                "is_generic": False,
                "product_name": product_name,
                "required": composition.component_quantity,
                "assigned": composition.component_quantity,
                "remaining": 0,
                "is_complete": True,
            }

        assigned_qty = (
            s.query(func.coalesce(func.sum(CompositionAssignment.quantity_assigned), 0))
            .filter(CompositionAssignment.composition_id == composition_id)
            .scalar()
        ) or 0

        required = composition.component_quantity
        assigned = float(assigned_qty)
        remaining = max(0, required - assigned)

        return {
            "is_generic": True,
            "product_name": product_name,
            "required": required,
            "assigned": assigned,
            "remaining": remaining,
            "is_complete": assigned >= required,
        }

    if session is not None:
        return _impl(session)
    with session_scope() as s:
        return _impl(s)
