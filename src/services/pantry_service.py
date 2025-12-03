"""Pantry Service - Inventory management with FIFO consumption.

This module provides business logic for managing pantry inventory including
lot tracking, FIFO (First In, First Out) consumption, expiration monitoring,
and value calculation.

All functions are stateless and use session_scope() for transaction management.

Key Features:
- Lot-based inventory tracking (purchase date, expiration, location)
- **FIFO consumption algorithm** - oldest lots consumed first
- Unit conversion during consumption
- Expiration date monitoring
- Location-based filtering
- Inventory value calculation (when cost data available)

Example Usage:
      >>> from src.services.pantry_service import add_to_pantry, consume_fifo
      >>> from decimal import Decimal
      >>> from datetime import date
      >>>
      >>> # Add inventory
      >>> item = add_to_pantry(
      ...     variant_id=123,
      ...     quantity=Decimal("25.0"),
      ...     unit="lb",
      ...     purchase_date=date(2025, 1, 1),
      ...     location="Main Pantry"
      ... )
      >>>
      >>> # Consume using FIFO
      >>> result = consume_fifo("all_purpose_flour", Decimal("10.0"))
      >>> result["satisfied"]  # True if enough inventory
      >>> result["shortfall"]  # 0.0 if satisfied, otherwise amount short
"""

from typing import Dict, Any, List, Optional
from decimal import Decimal
from datetime import date, timedelta

from ..models import PantryItem, Variant
from .database import session_scope
from .exceptions import (
      VariantNotFound,
      PantryItemNotFound,
      ValidationError as ServiceValidationError,
      DatabaseError,
)
from .variant_service import get_variant
from .ingredient_service import get_ingredient
from sqlalchemy.orm import joinedload


def add_to_pantry(
      variant_id: int,
      quantity: Decimal,
      purchase_date: date,
      expiration_date: Optional[date] = None,
      location: Optional[str] = None,
      notes: Optional[str] = None
) -> PantryItem:
      """Add a new pantry item (lot) to inventory.

      This function adds a discrete lot of inventory to the pantry. Each lot
      is tracked separately for FIFO consumption, expiration monitoring, and
      location management.

      Args:
          variant_id: ID of product variant being added
          quantity: Amount being added (must be > 0)
          purchase_date: Date this lot was purchased (for FIFO ordering)
          expiration_date: Optional expiration date (must be >= purchase_date)
          location: Optional storage location (e.g., "Main Pantry", "Basement")
          notes: Optional user notes

      Returns:
          PantryItem: Created pantry item with assigned ID

      Raises:
          VariantNotFound: If variant_id doesn't exist
          ValidationError: If quantity <= 0 or expiration_date < purchase_date
          DatabaseError: If database operation fails

      Example:
          >>> from decimal import Decimal
          >>> from datetime import date
          >>> item = add_to_pantry(
          ...     variant_id=123,
          ...     quantity=Decimal("25.0"),
          ...     unit="lb",
          ...     purchase_date=date(2025, 1, 15),
          ...     expiration_date=date(2026, 1, 15),
          ...     location="Main Pantry"
          ... )
          >>> item.quantity
          Decimal('25.0')
      """
      # Validate variant exists
      variant = get_variant(variant_id)

      # Validate quantity > 0
      if quantity <= 0:
          raise ServiceValidationError("Quantity must be positive")

      # Validate dates
      if expiration_date and expiration_date < purchase_date:
          raise ServiceValidationError("Expiration date cannot be before purchase date")

      try:
          with session_scope() as session:
              item = PantryItem(
                  variant_id=variant_id,
                  quantity=float(quantity),  # Model uses Float, convert from Decimal
                  purchase_date=purchase_date,
                  expiration_date=expiration_date,
                  location=location,
                  notes=notes
              )
              session.add(item)
              session.flush()
              return item

      except VariantNotFound:
          raise
      except ServiceValidationError:
          raise
      except Exception as e:
          raise DatabaseError(f"Failed to add pantry item", original_error=e)


def get_pantry_items(
      ingredient_slug: Optional[str] = None,
      variant_id: Optional[int] = None,
      location: Optional[str] = None,
      min_quantity: Optional[Decimal] = None
) -> List[PantryItem]:
      """Retrieve pantry items with optional filtering.

      This function supports flexible filtering for inventory queries. Items
      are returned ordered by purchase_date (oldest first) for FIFO visibility.

      Args:
          ingredient_slug: Optional ingredient filter (e.g., "all_purpose_flour")
          variant_id: Optional variant filter (specific brand/package)
          location: Optional location filter (exact match)
          min_quantity: Optional minimum quantity filter (excludes depleted lots)

      Returns:
          List[PantryItem]: Matching pantry items, ordered by purchase_date ASC

      Example:
          >>> # Get all flour in main pantry with quantity > 0
          >>> items = get_pantry_items(
          ...     ingredient_slug="all_purpose_flour",
          ...     location="Main Pantry",
          ...     min_quantity=Decimal("0.001")
          ... )
          >>> len(items)
          3
          >>> items[0].purchase_date < items[1].purchase_date
          True
      """
      with session_scope() as session:
          q = session.query(PantryItem).options(
              joinedload(PantryItem.variant).joinedload(Variant.ingredient)
          )

          # Join Variant if filtering by ingredient_slug
          if ingredient_slug:
                ingredient = get_ingredient(ingredient_slug)
                q = q.join(Variant).filter(Variant.ingredient_id == ingredient.id)

          # Apply other filters
          if variant_id:
              q = q.filter(PantryItem.variant_id == variant_id)
          if location:
              q = q.filter(PantryItem.location == location)
          if min_quantity is not None:
              q = q.filter(PantryItem.quantity >= float(min_quantity))

          # Order by purchase_date (FIFO order)
          return q.order_by(PantryItem.purchase_date.asc()).all()


def get_total_quantity(ingredient_slug: str) -> Dict[str, Decimal]:
      """Calculate total quantity for ingredient grouped by unit.

      This function aggregates inventory across all lots, grouping by unit
      since we no longer convert to a single standard unit.

      Args:
          ingredient_slug: Ingredient identifier

      Returns:
          Dict[str, Decimal]: Total quantities by unit (e.g., {"lb": 25.0, "cup": 3.5})

      Raises:
          IngredientNotFoundBySlug: If ingredient_slug doesn't exist

      Example:
          >>> totals = get_total_quantity("all_purpose_flour")
          >>> totals
          {"lb": Decimal('25.0'), "cup": Decimal('3.5')}

          >>> # Empty inventory returns empty dict
          >>> get_total_quantity("new_ingredient")
          {}
      """
      ingredient = get_ingredient(ingredient_slug)  # Validate exists

      # Get all pantry items for this ingredient with quantity > 0
      items = get_pantry_items(
          ingredient_slug=ingredient_slug,
          min_quantity=Decimal("0.001")
      )

      # Group quantities by unit
      unit_totals = {}
      for item in items:
          unit = item.variant.purchase_unit
          if unit:
              if unit not in unit_totals:
                  unit_totals[unit] = Decimal("0.0")
              unit_totals[unit] += Decimal(str(item.quantity))

      return unit_totals


def consume_fifo(
      ingredient_slug: str,
      quantity_needed: Decimal,
      dry_run: bool = False
) -> Dict[str, Any]:
      """Consume pantry inventory using FIFO (First In, First Out) logic.

      **CRITICAL FUNCTION**: This implements the core inventory consumption algorithm.

      Algorithm:
          1. Query all lots for ingredient ordered by purchase_date ASC (oldest first)
          2. Iterate through lots, consuming from each until quantity_needed satisfied
          3. Convert between lot units and ingredient recipe_unit as needed
          4. Update lot quantities atomically within single transaction (unless dry_run)
          5. Track consumption breakdown for audit trail
          6. Calculate shortfall if insufficient inventory
          7. Calculate total FIFO cost of consumed inventory

      Args:
          ingredient_slug: Ingredient to consume from
          quantity_needed: Amount to consume in ingredient's recipe_unit
          dry_run: If True, simulate consumption without modifying database.
                   Returns cost data for recipe costing calculations.
                   If False (default), actually consume inventory.

      Returns:
          Dict[str, Any]: Consumption result with keys:
              - "consumed" (Decimal): Amount actually consumed in recipe_unit
              - "breakdown" (List[Dict]): Per-lot consumption details including unit_cost
              - "shortfall" (Decimal): Amount not available (0.0 if satisfied)
              - "satisfied" (bool): True if quantity_needed fully consumed
              - "total_cost" (Decimal): Total FIFO cost of consumed portion

      Raises:
          IngredientNotFoundBySlug: If ingredient_slug doesn't exist
          DatabaseError: If database operation fails

      Note:
          - All updates occur within single transaction (atomic) unless dry_run=True
          - Quantities maintained at 3 decimal precision
          - Unit conversion uses ingredient's unit_converter configuration
          - Empty lots (quantity=0) are kept for audit trail, not deleted
          - When dry_run=True, pantry quantities are NOT modified (read-only)
      """
      from ..services.unit_converter import convert_any_units

      ingredient = get_ingredient(ingredient_slug)  # Validate exists

      # Calculate density in g/cup if available
      density_g_per_cup = None
      if ingredient.density_g_per_ml:
          density_g_per_cup = ingredient.density_g_per_ml * 236.588  # Convert g/ml to g/cup

      try:
          with session_scope() as session:
              # Get all lots ordered by purchase_date ASC (oldest first)
              pantry_items = session.query(PantryItem).options(
                  joinedload(PantryItem.variant).joinedload(Variant.ingredient)
              ).join(Variant).filter(
                  Variant.ingredient_id == ingredient.id,
                  PantryItem.quantity >= 0.001  # Exclude negligible amounts from floating-point errors
              ).order_by(PantryItem.purchase_date.asc()).all()

              consumed = Decimal("0.0")
              total_cost = Decimal("0.0")
              breakdown = []
              remaining_needed = quantity_needed

              for item in pantry_items:
                  if remaining_needed <= Decimal("0.0"):
                      break

                  # Convert lot quantity to ingredient recipe_unit
                  item_qty_decimal = Decimal(str(item.quantity))
                  success, available_float, error = convert_any_units(
                      float(item_qty_decimal),
                      item.variant.purchase_unit,
                      ingredient.recipe_unit,
                      ingredient_name=ingredient.name,
                      density_override=density_g_per_cup
                  )
                  if not success:
                      raise ValueError(f"Unit conversion failed: {error}")
                  available = Decimal(str(available_float))

                  # Consume up to available amount
                  to_consume_in_recipe_unit = min(available, remaining_needed)

                  # Convert back to lot's unit for deduction
                  success, to_consume_float, error = convert_any_units(
                      float(to_consume_in_recipe_unit),
                      ingredient.recipe_unit,
                      item.variant.purchase_unit,
                      ingredient_name=ingredient.name,
                      density_override=density_g_per_cup
                  )
                  if not success:
                      raise ValueError(f"Unit conversion failed: {error}")
                  to_consume_in_lot_unit = Decimal(str(to_consume_float))

                  # Get unit cost from the pantry item (if available)
                  item_unit_cost = Decimal(str(item.unit_cost)) if item.unit_cost else Decimal("0.0")

                  # Calculate cost for this lot's consumption
                  lot_cost = to_consume_in_lot_unit * item_unit_cost
                  total_cost += lot_cost

                  # Update lot quantity only if NOT dry_run
                  if not dry_run:
                      item.quantity -= float(to_consume_in_lot_unit)

                  consumed += to_consume_in_recipe_unit
                  remaining_needed -= to_consume_in_recipe_unit

                  # Calculate remaining_in_lot (for dry_run, simulate the deduction)
                  if dry_run:
                      remaining_in_lot = item_qty_decimal - to_consume_in_lot_unit
                  else:
                      remaining_in_lot = Decimal(str(item.quantity))

                  breakdown.append({
                      "pantry_item_id": item.id,
                      "variant_id": item.variant_id,
                      "lot_date": item.purchase_date,
                      "quantity_consumed": to_consume_in_lot_unit,
                      "unit": item.variant.purchase_unit,
                      "remaining_in_lot": remaining_in_lot,
                      "unit_cost": item_unit_cost
                  })

                  # Only flush to database if NOT dry_run
                  if not dry_run:
                      session.flush()  # Persist update within transaction

              # Calculate results
              shortfall = max(Decimal("0.0"), remaining_needed)
              satisfied = shortfall == Decimal("0.0")

              return {
                  "consumed": consumed,
                  "breakdown": breakdown,
                  "shortfall": shortfall,
                  "satisfied": satisfied,
                  "total_cost": total_cost
              }

      except Exception as e:
          raise DatabaseError(
              f"Failed to consume FIFO for ingredient '{ingredient_slug}'",
              original_error=e
          )


def get_expiring_soon(days: int = 14) -> List[PantryItem]:
      """Get pantry items expiring within specified days.

      This function identifies items needing to be used soon to prevent waste.
      Items without expiration dates are excluded.

      Args:
          days: Number of days to look ahead (default: 14)

      Returns:
          List[PantryItem]: Items expiring within specified days,
                           ordered by expiration_date (soonest first)

      Example:
          >>> # Get items expiring in next 7 days
          >>> expiring = get_expiring_soon(days=7)
          >>> # Items already expired are excluded
          >>> # Items without expiration_date are excluded
      """
      cutoff_date = date.today() + timedelta(days=days)

      with session_scope() as session:
          return session.query(PantryItem).options(
              joinedload(PantryItem.variant).joinedload(Variant.ingredient)
          ).filter(
              PantryItem.expiration_date.isnot(None),
              PantryItem.expiration_date <= cutoff_date,
              PantryItem.quantity > 0
          ).order_by(PantryItem.expiration_date.asc()).all()


def update_pantry_item(pantry_item_id: int, item_data: Dict[str, Any]) -> PantryItem:
      """Update pantry item attributes.

      Allows updating quantity, expiration_date, location, and notes.
      Immutable fields (variant_id, purchase_date) cannot be changed to maintain
      FIFO integrity and audit trail.

      Args:
          pantry_item_id: Pantry item identifier
          item_data: Dictionary with fields to update (partial update supported)

      Returns:
          PantryItem: Updated pantry item

      Raises:
          PantryItemNotFound: If pantry_item_id doesn't exist
          ValidationError: If attempting to change variant_id or purchase_date
          DatabaseError: If database operation fails

      Note:
          variant_id and purchase_date are immutable to maintain FIFO order
          and prevent orphaned references.
      """
      # Prevent changing immutable fields
      if 'variant_id' in item_data:
          raise ServiceValidationError("Variant ID cannot be changed after creation")
      if 'purchase_date' in item_data:
          raise ServiceValidationError("Purchase date cannot be changed after creation")

      # Validate quantity if being updated
      if 'quantity' in item_data and item_data['quantity'] < 0:
          raise ServiceValidationError("Quantity cannot be negative")

      try:
          with session_scope() as session:
              item = session.query(PantryItem).options(
                  joinedload(PantryItem.variant).joinedload(Variant.ingredient)
              ).filter_by(id=pantry_item_id).first()
              if not item:
                  raise PantryItemNotFound(pantry_item_id)

              # Update attributes
              for key, value in item_data.items():
                  if hasattr(item, key):
                      # Convert Decimal to float for quantity
                      if key == 'quantity' and isinstance(value, Decimal):
                          value = float(value)
                      setattr(item, key, value)

              return item

      except PantryItemNotFound:
          raise
      except ServiceValidationError:
          raise
      except Exception as e:
          raise DatabaseError(f"Failed to update pantry item {pantry_item_id}", original_error=e)


def delete_pantry_item(pantry_item_id: int) -> bool:
      """Delete pantry item (lot).

      Deletes a pantry item record. Typically used for cleaning up depleted lots
      or removing erroneous entries.

      Args:
          pantry_item_id: Pantry item identifier

      Returns:
          bool: True if deletion successful

      Raises:
          PantryItemNotFound: If pantry_item_id doesn't exist
          DatabaseError: If database operation fails

      Note:
          Consider keeping depleted lots (quantity=0) for audit trail rather
          than deleting. Deletion is permanent and cannot be undone.
      """
      try:
          with session_scope() as session:
              item = session.query(PantryItem).filter_by(id=pantry_item_id).first()
              if not item:
                  raise PantryItemNotFound(pantry_item_id)

              session.delete(item)
              return True

      except PantryItemNotFound:
          raise
      except Exception as e:
          raise DatabaseError(f"Failed to delete pantry item {pantry_item_id}", original_error=e)


def get_pantry_value() -> Decimal:
      """Calculate total value of all pantry inventory.

      Calculates total monetary value of pantry by multiplying quantities by
      unit costs from purchase history.

      Returns:
          Decimal: Total inventory value (0.0 if cost tracking not implemented)

      Note:
          This function requires cost tracking integration with Purchase model.
          Returns 0.0 as placeholder until purchase_service.py implements
          cost history tracking.

      Future Implementation:
          - Join PantryItem with Purchase via variant_id
          - Get most recent unit_cost for each variant
          - Calculate: SUM(pantry_item.quantity * latest_purchase.unit_cost)
          - Handle unit conversions if pantry unit != purchase unit
      """
      # TODO: Implement when Purchase model and purchase_service.py are ready
      # Future logic:
      # 1. Query all PantryItem with quantity > 0
      # 2. Join with Purchase to get latest unit_cost per variant
      # 3. Convert quantities to purchase unit if needed
      # 4. Calculate: SUM(quantity * unit_cost)
      return Decimal("0.0")