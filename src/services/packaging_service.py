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
from src.models import Product, Ingredient, InventoryItem, Composition

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


# =============================================================================
# Generic Product Discovery
# =============================================================================


def get_generic_products(*, session: Optional[Session] = None) -> List[str]:
    """
    Get distinct product_name values for packaging products.

    These represent the generic product types available for deferred selection.

    Args:
        session: Optional database session

    Returns:
        List of distinct product_name values, sorted alphabetically
    """
    def _impl(s: Session) -> List[str]:
        # Query distinct product_name values from Products
        # that are linked to ingredients where is_packaging=True
        result = (
            s.query(Product.product_name)
            .join(Ingredient, Product.ingredient_id == Ingredient.id)
            .filter(Ingredient.is_packaging == True)
            .filter(Product.product_name.isnot(None))
            .filter(Product.product_name != "")
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
    product_name: str,
    *,
    session: Optional[Session] = None
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
            # Sum inventory for this product
            # InventoryItem.remaining_quantity tracks current available
            available = (
                s.query(func.coalesce(func.sum(InventoryItem.remaining_quantity), 0))
                .filter(InventoryItem.product_id == product.id)
                .scalar()
            ) or Decimal("0")

            breakdown.append({
                "brand": product.brand or "(No brand)",
                "product_id": product.id,
                "available": float(available),
            })
            total += available

        return {
            "total": float(total),
            "breakdown": sorted(breakdown, key=lambda x: x["brand"]),
        }

    if session is not None:
        return _impl(session)
    with session_scope() as s:
        return _impl(s)


# =============================================================================
# Cost Estimation
# =============================================================================


def get_estimated_cost(
    product_name: str,
    quantity: float,
    *,
    session: Optional[Session] = None
) -> float:
    """
    Calculate estimated cost for a generic packaging requirement.

    Uses average price across all products with the matching product_name.

    Args:
        product_name: The generic product type name
        quantity: Number of units needed
        session: Optional database session

    Returns:
        Estimated total cost (quantity * average unit price)

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

        # Calculate average purchase price across all products
        prices = [
            float(p.purchase_price or Decimal("0"))
            for p in products
            if p.purchase_price is not None and p.purchase_price > 0
        ]

        if not prices:
            return 0.0

        avg_price = sum(prices) / len(prices)
        return round(avg_price * quantity, 2)

    if session is not None:
        return _impl(session)
    with session_scope() as s:
        return _impl(s)


# =============================================================================
# Material Assignment
# =============================================================================


def assign_materials(
    composition_id: int,
    assignments: List[Dict[str, Any]],
    *,
    session: Optional[Session] = None
) -> bool:
    """
    Create assignment records linking specific inventory to a generic requirement.

    This is a stub implementation that will be fully implemented in WP02.

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
    """
    # TODO: Full implementation in WP02
    # This stub validates basic inputs and returns True
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

        for assignment in assignments:
            if 'inventory_item_id' not in assignment or 'quantity' not in assignment:
                raise InvalidAssignmentError(
                    "Each assignment must have 'inventory_item_id' and 'quantity'"
                )
            if assignment['quantity'] <= 0:
                raise InvalidAssignmentError("Assignment quantity must be positive")

        # TODO: Create CompositionAssignment records
        # TODO: Validate total matches required quantity
        # TODO: Validate inventory availability

        logger.info(f"Stub: Would assign materials to composition {composition_id}")
        return True

    if session is not None:
        return _impl(session)
    with session_scope() as s:
        return _impl(s)


# =============================================================================
# Pending Requirements Query
# =============================================================================


def get_pending_requirements(
    event_id: Optional[int] = None,
    *,
    session: Optional[Session] = None
) -> List[Composition]:
    """
    Find compositions where is_generic=True and no assignments exist.

    Args:
        event_id: Optional filter by event ID
        session: Optional database session

    Returns:
        List of Composition objects with pending generic requirements
    """
    def _impl(s: Session) -> List[Composition]:
        query = (
            s.query(Composition)
            .filter(Composition.is_generic == True)
            .filter(Composition.packaging_product_id.isnot(None))
        )

        # TODO: Filter out compositions that have complete assignments
        # This will require the CompositionAssignment table from WP01

        if event_id is not None:
            # TODO: Filter by event - requires joining through assembly/package to event
            pass

        return query.all()

    if session is not None:
        return _impl(session)
    with session_scope() as s:
        return _impl(s)


def is_fully_assigned(
    composition_id: int,
    *,
    session: Optional[Session] = None
) -> bool:
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

        # TODO: Query CompositionAssignment table to sum assigned quantities
        # Return True if sum >= component_quantity

        # Stub: Return False for generic compositions (no assignments yet)
        return False

    if session is not None:
        return _impl(session)
    with session_scope() as s:
        return _impl(s)
