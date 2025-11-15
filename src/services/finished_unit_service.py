"""
FinishedUnit Service - CRUD operations and business logic for individual consumable items.

This service provides comprehensive management for FinishedUnits, implementing User Story 1:
Track Individual Consumable Items with full CRUD operations, inventory management,
cost calculations, and search capabilities.

Key Features:
- Complete CRUD operations with validation and error handling
- Inventory management with non-negative constraints
- Cost calculation integration with existing FIFO patterns
- High-performance operations meeting desktop application requirements
- Comprehensive search and filtering capabilities
"""

import logging
from decimal import Decimal
from typing import List, Optional, Dict, Any
import re
import unicodedata
from datetime import datetime

from sqlalchemy import and_, or_, text
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from ..database import get_db_session, session_scope
from ..models import FinishedUnit, Recipe, Composition
from .exceptions import (
    ServiceError,
    ValidationError,
    DatabaseError
)

logger = logging.getLogger(__name__)


# Custom exceptions for FinishedUnit service
class FinishedUnitNotFoundError(ServiceError):
    """Raised when a FinishedUnit cannot be found."""
    pass


class InvalidInventoryError(ServiceError):
    """Raised when inventory operations would create invalid state."""
    pass


class DuplicateSlugError(ServiceError):
    """Raised when slug uniqueness is violated."""
    pass


class ReferencedUnitError(ServiceError):
    """Raised when attempting to delete unit used in compositions."""
    pass


class FinishedUnitService:
    """
    Service for FinishedUnit operations and business logic.

    Provides comprehensive CRUD operations, inventory management, cost calculations,
    and search capabilities for individual consumable items.
    """

    # Core Operations

    @staticmethod
    def get_finished_unit_count() -> int:
        """
        Get total count of all FinishedUnits.

        Returns:
            Integer count of FinishedUnit records

        Performance:
            Must complete in <100ms per contract
        """
        try:
            with get_db_session() as session:
                count = session.query(FinishedUnit).count()
                logger.debug(f"Retrieved FinishedUnit count: {count}")
                return count

        except SQLAlchemyError as e:
            logger.error(f"Database error getting FinishedUnit count: {e}")
            raise DatabaseError(f"Failed to get FinishedUnit count: {e}")

    @staticmethod
    def get_finished_unit_by_id(finished_unit_id: int) -> Optional[FinishedUnit]:
        """
        Retrieve a specific FinishedUnit by ID.

        Args:
            finished_unit_id: Integer ID of the FinishedUnit

        Returns:
            FinishedUnit instance or None if not found

        Performance:
            Must complete in <50ms per contract
        """
        try:
            with get_db_session() as session:
                unit = session.query(FinishedUnit)\
                    .options(selectinload(FinishedUnit.recipe))\
                    .filter(FinishedUnit.id == finished_unit_id)\
                    .first()

                if unit:
                    logger.debug(f"Retrieved FinishedUnit by ID {finished_unit_id}: {unit.display_name}")
                else:
                    logger.debug(f"FinishedUnit not found for ID {finished_unit_id}")

                return unit

        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving FinishedUnit ID {finished_unit_id}: {e}")
            raise DatabaseError(f"Failed to retrieve FinishedUnit by ID: {e}")

    @staticmethod
    def get_finished_unit_by_slug(slug: str) -> Optional[FinishedUnit]:
        """
        Retrieve a specific FinishedUnit by slug identifier.

        Args:
            slug: String slug identifier

        Returns:
            FinishedUnit instance or None if not found

        Performance:
            Must complete in <50ms per contract (indexed lookup)
        """
        try:
            with get_db_session() as session:
                unit = session.query(FinishedUnit)\
                    .options(selectinload(FinishedUnit.recipe))\
                    .filter(FinishedUnit.slug == slug)\
                    .first()

                if unit:
                    logger.debug(f"Retrieved FinishedUnit by slug '{slug}': {unit.display_name}")
                else:
                    logger.debug(f"FinishedUnit not found for slug '{slug}'")

                return unit

        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving FinishedUnit slug '{slug}': {e}")
            raise DatabaseError(f"Failed to retrieve FinishedUnit by slug: {e}")

    @staticmethod
    def get_all_finished_units() -> List[FinishedUnit]:
        """
        Retrieve all FinishedUnits.

        Returns:
            List of all FinishedUnit instances

        Performance:
            Must complete in <200ms for up to 10k records per contract
        """
        try:
            with get_db_session() as session:
                units = session.query(FinishedUnit)\
                    .options(selectinload(FinishedUnit.recipe))\
                    .order_by(FinishedUnit.display_name)\
                    .all()

                logger.debug(f"Retrieved {len(units)} FinishedUnits")
                return units

        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving all FinishedUnits: {e}")
            raise DatabaseError(f"Failed to retrieve all FinishedUnits: {e}")

    @staticmethod
    def create_finished_unit(
        display_name: str,
        recipe_id: Optional[int] = None,
        unit_cost: Decimal = Decimal('0.0000'),
        **kwargs
    ) -> FinishedUnit:
        """
        Create a new FinishedUnit.

        Args:
            display_name: Required string name
            recipe_id: Optional Recipe ID reference
            unit_cost: Optional unit cost (default 0)
            **kwargs: Additional optional fields

        Returns:
            Created FinishedUnit instance

        Raises:
            ValidationError: If validation fails
            DuplicateSlugError: If slug already exists
            DatabaseError: If database operation fails

        Performance:
            Must complete in <500ms per contract
        """
        try:
            # Validate required fields
            if not display_name or not display_name.strip():
                raise ValidationError("Display name is required and cannot be empty")

            # Generate unique slug
            slug = FinishedUnitService._generate_slug(display_name.strip())

            # Validate unit cost
            if unit_cost < 0:
                raise ValidationError("Unit cost must be non-negative")

            with session_scope() as session:
                # Check slug uniqueness
                existing = session.query(FinishedUnit)\
                    .filter(FinishedUnit.slug == slug)\
                    .first()

                if existing:
                    # Generate unique slug with suffix
                    slug = FinishedUnitService._generate_unique_slug(display_name.strip(), session)

                # Validate recipe reference if provided
                if recipe_id is not None:
                    recipe = session.query(Recipe).filter(Recipe.id == recipe_id).first()
                    if not recipe:
                        raise ValidationError(f"Recipe ID {recipe_id} does not exist")

                # Create FinishedUnit with validated data
                unit_data = {
                    'slug': slug,
                    'display_name': display_name.strip(),
                    'recipe_id': recipe_id,
                    'unit_cost': unit_cost,
                    'inventory_count': kwargs.get('inventory_count', 0),
                    'yield_mode': kwargs.get('yield_mode'),
                    'items_per_batch': kwargs.get('items_per_batch'),
                    'item_unit': kwargs.get('item_unit'),
                    'batch_percentage': kwargs.get('batch_percentage'),
                    'portion_description': kwargs.get('portion_description'),
                    'category': kwargs.get('category'),
                    'production_notes': kwargs.get('production_notes'),
                    'notes': kwargs.get('notes'),
                }

                # Remove None values
                unit_data = {k: v for k, v in unit_data.items() if v is not None}

                finished_unit = FinishedUnit(**unit_data)
                session.add(finished_unit)
                session.flush()  # Get the ID

                # Calculate unit cost from recipe if available and cost is zero
                if recipe_id and unit_cost == Decimal('0.0000'):
                    finished_unit.update_unit_cost_from_recipe()

                logger.info(f"Created FinishedUnit: {finished_unit.display_name} (ID: {finished_unit.id})")
                return finished_unit

        except IntegrityError as e:
            logger.error(f"Integrity error creating FinishedUnit: {e}")
            if "uq_finished_unit_slug" in str(e):
                raise DuplicateSlugError(f"Slug '{slug}' already exists")
            else:
                raise DatabaseError(f"Database integrity error: {e}")

        except SQLAlchemyError as e:
            logger.error(f"Database error creating FinishedUnit: {e}")
            raise DatabaseError(f"Failed to create FinishedUnit: {e}")

    @staticmethod
    def update_finished_unit(finished_unit_id: int, **updates) -> FinishedUnit:
        """
        Update an existing FinishedUnit.

        Args:
            finished_unit_id: ID of FinishedUnit to update
            **updates: Dictionary of fields to update

        Returns:
            Updated FinishedUnit instance

        Raises:
            FinishedUnitNotFoundError: If unit doesn't exist
            ValidationError: If validation fails
            DatabaseError: If database operation fails

        Performance:
            Must complete in <500ms per contract
        """
        try:
            with session_scope() as session:
                unit = session.query(FinishedUnit)\
                    .filter(FinishedUnit.id == finished_unit_id)\
                    .first()

                if not unit:
                    raise FinishedUnitNotFoundError(f"FinishedUnit ID {finished_unit_id} not found")

                # Validate updates
                if 'display_name' in updates:
                    display_name = updates['display_name']
                    if not display_name or not display_name.strip():
                        raise ValidationError("Display name cannot be empty")

                    # Update slug if display name changed
                    if display_name.strip() != unit.display_name:
                        new_slug = FinishedUnitService._generate_unique_slug(display_name.strip(), session, unit.id)
                        updates['slug'] = new_slug

                if 'unit_cost' in updates and updates['unit_cost'] < 0:
                    raise ValidationError("Unit cost must be non-negative")

                if 'inventory_count' in updates and updates['inventory_count'] < 0:
                    raise ValidationError("Inventory count must be non-negative")

                if 'recipe_id' in updates and updates['recipe_id'] is not None:
                    recipe = session.query(Recipe).filter(Recipe.id == updates['recipe_id']).first()
                    if not recipe:
                        raise ValidationError(f"Recipe ID {updates['recipe_id']} does not exist")

                # Apply updates
                for field, value in updates.items():
                    if hasattr(unit, field):
                        setattr(unit, field, value)

                unit.updated_at = datetime.utcnow()
                session.flush()

                logger.info(f"Updated FinishedUnit ID {finished_unit_id}: {unit.display_name}")
                return unit

        except SQLAlchemyError as e:
            logger.error(f"Database error updating FinishedUnit ID {finished_unit_id}: {e}")
            raise DatabaseError(f"Failed to update FinishedUnit: {e}")

    @staticmethod
    def delete_finished_unit(finished_unit_id: int) -> bool:
        """
        Delete a FinishedUnit.

        Args:
            finished_unit_id: ID of FinishedUnit to delete

        Returns:
            True if deleted, False if not found

        Raises:
            ReferencedUnitError: If unit is used in compositions
            DatabaseError: If database operation fails

        Performance:
            Must complete in <500ms per contract
        """
        try:
            with session_scope() as session:
                unit = session.query(FinishedUnit)\
                    .filter(FinishedUnit.id == finished_unit_id)\
                    .first()

                if not unit:
                    logger.debug(f"FinishedUnit ID {finished_unit_id} not found for deletion")
                    return False

                # Check for composition references
                composition_count = session.query(Composition)\
                    .filter(Composition.finished_unit_id == finished_unit_id)\
                    .count()

                if composition_count > 0:
                    raise ReferencedUnitError(
                        f"Cannot delete FinishedUnit '{unit.display_name}' - "
                        f"it is referenced in {composition_count} compositions"
                    )

                # Delete the unit
                display_name = unit.display_name
                session.delete(unit)

                logger.info(f"Deleted FinishedUnit ID {finished_unit_id}: {display_name}")
                return True

        except SQLAlchemyError as e:
            logger.error(f"Database error deleting FinishedUnit ID {finished_unit_id}: {e}")
            raise DatabaseError(f"Failed to delete FinishedUnit: {e}")

    # Inventory Management

    @staticmethod
    def update_inventory(finished_unit_id: int, quantity_change: int) -> FinishedUnit:
        """
        Adjust inventory count for a FinishedUnit.

        Args:
            finished_unit_id: ID of FinishedUnit
            quantity_change: Positive or negative integer change

        Returns:
            Updated FinishedUnit instance

        Raises:
            FinishedUnitNotFoundError: If unit doesn't exist
            InvalidInventoryError: If operation would result in negative inventory
            DatabaseError: If database operation fails

        Performance:
            Must complete in <200ms per contract
        """
        try:
            with session_scope() as session:
                unit = session.query(FinishedUnit)\
                    .filter(FinishedUnit.id == finished_unit_id)\
                    .first()

                if not unit:
                    raise FinishedUnitNotFoundError(f"FinishedUnit ID {finished_unit_id} not found")

                new_count = unit.inventory_count + quantity_change

                if new_count < 0:
                    raise InvalidInventoryError(
                        f"Inventory change of {quantity_change} would result in negative inventory "
                        f"(current: {unit.inventory_count}, would be: {new_count})"
                    )

                unit.inventory_count = new_count
                unit.updated_at = datetime.utcnow()
                session.flush()

                logger.info(f"Updated inventory for '{unit.display_name}': {quantity_change:+d} "
                          f"(new total: {new_count})")
                return unit

        except SQLAlchemyError as e:
            logger.error(f"Database error updating inventory for FinishedUnit ID {finished_unit_id}: {e}")
            raise DatabaseError(f"Failed to update inventory: {e}")

    @staticmethod
    def check_availability(finished_unit_id: int, required_quantity: int) -> bool:
        """
        Check if sufficient inventory exists.

        Args:
            finished_unit_id: ID of FinishedUnit to check
            required_quantity: Required quantity

        Returns:
            True if available, False otherwise

        Raises:
            FinishedUnitNotFoundError: If unit doesn't exist
            DatabaseError: If database operation fails

        Performance:
            Must complete in <50ms per contract
        """
        try:
            with get_db_session() as session:
                unit = session.query(FinishedUnit)\
                    .filter(FinishedUnit.id == finished_unit_id)\
                    .first()

                if not unit:
                    raise FinishedUnitNotFoundError(f"FinishedUnit ID {finished_unit_id} not found")

                is_available = unit.inventory_count >= required_quantity
                logger.debug(f"Availability check for '{unit.display_name}': "
                           f"required {required_quantity}, available {unit.inventory_count}, "
                           f"result: {is_available}")

                return is_available

        except SQLAlchemyError as e:
            logger.error(f"Database error checking availability for FinishedUnit ID {finished_unit_id}: {e}")
            raise DatabaseError(f"Failed to check availability: {e}")

    # Cost Calculation

    @staticmethod
    def calculate_unit_cost(finished_unit_id: int) -> Decimal:
        """
        Calculate current unit cost based on recipe and pantry consumption.

        Args:
            finished_unit_id: ID of FinishedUnit

        Returns:
            Calculated unit cost

        Raises:
            FinishedUnitNotFoundError: If unit doesn't exist
            DatabaseError: If database operation fails

        Performance:
            Must complete in <200ms per contract
        """
        try:
            with get_db_session() as session:
                unit = session.query(FinishedUnit)\
                    .options(selectinload(FinishedUnit.recipe))\
                    .filter(FinishedUnit.id == finished_unit_id)\
                    .first()

                if not unit:
                    raise FinishedUnitNotFoundError(f"FinishedUnit ID {finished_unit_id} not found")

                # Calculate cost using the model's method
                calculated_cost = unit.calculate_recipe_cost_per_item()

                logger.debug(f"Calculated unit cost for '{unit.display_name}': {calculated_cost}")
                return calculated_cost

        except SQLAlchemyError as e:
            logger.error(f"Database error calculating unit cost for FinishedUnit ID {finished_unit_id}: {e}")
            raise DatabaseError(f"Failed to calculate unit cost: {e}")

    # Query Operations

    @staticmethod
    def search_finished_units(query: str) -> List[FinishedUnit]:
        """
        Search FinishedUnits by display name or description.

        Args:
            query: String search term

        Returns:
            List of matching FinishedUnit instances

        Performance:
            Must complete in <300ms per contract
        """
        try:
            if not query or not query.strip():
                return []

            search_term = f"%{query.strip().lower()}%"

            with get_db_session() as session:
                units = session.query(FinishedUnit)\
                    .options(selectinload(FinishedUnit.recipe))\
                    .filter(
                        or_(
                            FinishedUnit.display_name.ilike(search_term),
                            FinishedUnit.description.ilike(search_term),
                            FinishedUnit.category.ilike(search_term),
                            FinishedUnit.notes.ilike(search_term)
                        )
                    )\
                    .order_by(FinishedUnit.display_name)\
                    .all()

                logger.debug(f"Search for '{query}' returned {len(units)} FinishedUnits")
                return units

        except SQLAlchemyError as e:
            logger.error(f"Database error searching FinishedUnits with query '{query}': {e}")
            raise DatabaseError(f"Failed to search FinishedUnits: {e}")

    @staticmethod
    def get_units_by_recipe(recipe_id: int) -> List[FinishedUnit]:
        """
        Get all FinishedUnits associated with a specific recipe.

        Args:
            recipe_id: Recipe ID to filter by

        Returns:
            List of FinishedUnit instances

        Performance:
            Must complete in <200ms per contract
        """
        try:
            with get_db_session() as session:
                units = session.query(FinishedUnit)\
                    .options(selectinload(FinishedUnit.recipe))\
                    .filter(FinishedUnit.recipe_id == recipe_id)\
                    .order_by(FinishedUnit.display_name)\
                    .all()

                logger.debug(f"Retrieved {len(units)} FinishedUnits for recipe ID {recipe_id}")
                return units

        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving FinishedUnits for recipe ID {recipe_id}: {e}")
            raise DatabaseError(f"Failed to retrieve FinishedUnits by recipe: {e}")

    # Utility methods

    @staticmethod
    def _generate_slug(display_name: str) -> str:
        """Generate URL-safe slug from display name."""
        if not display_name:
            return "unknown-item"

        # Normalize unicode characters
        slug = unicodedata.normalize('NFKD', display_name)

        # Convert to lowercase and replace spaces/punctuation with hyphens
        slug = re.sub(r'[^\w\s-]', '', slug).strip().lower()
        slug = re.sub(r'[\s_-]+', '-', slug)

        # Remove leading/trailing hyphens
        slug = slug.strip('-')

        # Ensure not empty
        if not slug:
            return "unknown-item"

        # Limit length
        if len(slug) > 90:
            slug = slug[:90].rstrip('-')

        return slug

    @staticmethod
    def _generate_unique_slug(display_name: str, session: Session, exclude_id: Optional[int] = None) -> str:
        """Generate unique slug, adding suffix if needed."""
        base_slug = FinishedUnitService._generate_slug(display_name)

        # Check if base slug is already unique
        query = session.query(FinishedUnit).filter(FinishedUnit.slug == base_slug)
        if exclude_id:
            query = query.filter(FinishedUnit.id != exclude_id)

        if not query.first():
            return base_slug

        # Add numeric suffix for uniqueness
        counter = 2
        while True:
            candidate_slug = f"{base_slug}-{counter}"
            query = session.query(FinishedUnit).filter(FinishedUnit.slug == candidate_slug)
            if exclude_id:
                query = query.filter(FinishedUnit.id != exclude_id)

            if not query.first():
                return candidate_slug

            counter += 1

            # Prevent infinite loop
            if counter > 1000:
                raise ValidationError("Unable to generate unique slug")


# Module-level convenience functions for backward compatibility

def get_finished_unit_count() -> int:
    """Get total count of all FinishedUnits."""
    return FinishedUnitService.get_finished_unit_count()


def get_finished_unit_by_id(finished_unit_id: int) -> Optional[FinishedUnit]:
    """Retrieve a specific FinishedUnit by ID."""
    return FinishedUnitService.get_finished_unit_by_id(finished_unit_id)


def get_finished_unit_by_slug(slug: str) -> Optional[FinishedUnit]:
    """Retrieve a specific FinishedUnit by slug."""
    return FinishedUnitService.get_finished_unit_by_slug(slug)


def get_all_finished_units() -> List[FinishedUnit]:
    """Retrieve all FinishedUnits."""
    return FinishedUnitService.get_all_finished_units()


def create_finished_unit(display_name: str, **kwargs) -> FinishedUnit:
    """Create a new FinishedUnit."""
    return FinishedUnitService.create_finished_unit(display_name, **kwargs)


def update_finished_unit(finished_unit_id: int, **updates) -> FinishedUnit:
    """Update an existing FinishedUnit."""
    return FinishedUnitService.update_finished_unit(finished_unit_id, **updates)


def delete_finished_unit(finished_unit_id: int) -> bool:
    """Delete a FinishedUnit."""
    return FinishedUnitService.delete_finished_unit(finished_unit_id)


def update_inventory(finished_unit_id: int, quantity_change: int) -> FinishedUnit:
    """Adjust inventory count for a FinishedUnit."""
    return FinishedUnitService.update_inventory(finished_unit_id, quantity_change)


def check_availability(finished_unit_id: int, required_quantity: int) -> bool:
    """Check if sufficient inventory exists."""
    return FinishedUnitService.check_availability(finished_unit_id, required_quantity)


def calculate_unit_cost(finished_unit_id: int) -> Decimal:
    """Calculate current unit cost based on recipe and pantry consumption."""
    return FinishedUnitService.calculate_unit_cost(finished_unit_id)


def search_finished_units(query: str) -> List[FinishedUnit]:
    """Search FinishedUnits by display name or description."""
    return FinishedUnitService.search_finished_units(query)


def get_units_by_recipe(recipe_id: int) -> List[FinishedUnit]:
    """Get all FinishedUnits associated with a specific recipe."""
    return FinishedUnitService.get_units_by_recipe(recipe_id)