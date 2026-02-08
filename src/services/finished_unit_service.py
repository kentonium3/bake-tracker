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

import json
import logging
from decimal import Decimal
from typing import List, Optional, Dict, Any
import re
import unicodedata
from datetime import datetime
from src.utils.datetime_utils import utc_now

from sqlalchemy import and_, func, or_, text
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from .database import get_db_session, session_scope
from ..models import FinishedUnit, FinishedUnitSnapshot, Recipe, Composition, InventoryItem
from ..models.finished_unit import YieldMode
from .exceptions import (
    DatabaseError,
    FinishedUnitNotFoundById,
    FinishedUnitNotFoundBySlug,
    ServiceError,
    ValidationError,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Feature 083: Yield Type Validation
# =============================================================================

# Valid yield type values
VALID_YIELD_TYPES = {"EA", "SERVING"}


def validate_yield_type(yield_type: str) -> List[str]:
    """Validate yield_type value.

    Transaction boundary: Pure computation (no database access).
    Validates yield_type against allowed values.

    Feature 083: Dual-Yield Support

    Args:
        yield_type: The yield type to validate ('EA' or 'SERVING')

    Returns:
        List of error messages (empty if valid)
    """
    errors = []
    if not yield_type:
        errors.append("yield_type is required")
    elif yield_type not in VALID_YIELD_TYPES:
        errors.append(f"yield_type must be 'EA' or 'SERVING', got '{yield_type}'")
    return errors


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


class SnapshotCreationError(ServiceError):
    """Raised when snapshot creation fails."""

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

        Transaction boundary: Read-only operation.
        Queries FinishedUnit count.

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
    def get_finished_unit_by_id(finished_unit_id: int) -> FinishedUnit:
        """
        Retrieve a specific FinishedUnit by ID.

        Transaction boundary: Read-only operation.
        Queries FinishedUnit with recipe eager loaded.

        Args:
            finished_unit_id: Integer ID of the FinishedUnit

        Returns:
            FinishedUnit instance

        Raises:
            FinishedUnitNotFoundById: If finished unit doesn't exist

        Performance:
            Must complete in <50ms per contract
        """
        try:
            with get_db_session() as session:
                unit = (
                    session.query(FinishedUnit)
                    .options(selectinload(FinishedUnit.recipe))
                    .filter(FinishedUnit.id == finished_unit_id)
                    .first()
                )

                if unit:
                    logger.debug(
                        f"Retrieved FinishedUnit by ID {finished_unit_id}: {unit.display_name}"
                    )
                    return unit
                else:
                    logger.debug(f"FinishedUnit not found for ID {finished_unit_id}")
                    raise FinishedUnitNotFoundById(finished_unit_id)

        except FinishedUnitNotFoundById:
            raise
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving FinishedUnit ID {finished_unit_id}: {e}")
            raise DatabaseError(f"Failed to retrieve FinishedUnit by ID: {e}")

    @staticmethod
    def get_finished_unit_by_slug(slug: str) -> FinishedUnit:
        """
        Retrieve a specific FinishedUnit by slug identifier.

        Transaction boundary: Read-only operation.
        Queries FinishedUnit with indexed slug lookup.

        Args:
            slug: String slug identifier

        Returns:
            FinishedUnit instance

        Raises:
            FinishedUnitNotFoundBySlug: If finished unit doesn't exist

        Performance:
            Must complete in <50ms per contract (indexed lookup)
        """
        try:
            with get_db_session() as session:
                unit = (
                    session.query(FinishedUnit)
                    .options(selectinload(FinishedUnit.recipe))
                    .filter(FinishedUnit.slug == slug)
                    .first()
                )

                if unit:
                    logger.debug(f"Retrieved FinishedUnit by slug '{slug}': {unit.display_name}")
                    return unit
                else:
                    logger.debug(f"FinishedUnit not found for slug '{slug}'")
                    raise FinishedUnitNotFoundBySlug(slug)

        except FinishedUnitNotFoundBySlug:
            raise
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving FinishedUnit slug '{slug}': {e}")
            raise DatabaseError(f"Failed to retrieve FinishedUnit by slug: {e}")

    @staticmethod
    def get_all_finished_units(
        name_search: Optional[str] = None,
        category: Optional[str] = None,
        recipe_id: Optional[int] = None,
    ) -> List[FinishedUnit]:
        """
        Retrieve all FinishedUnits with optional filtering.

        Transaction boundary: Read-only operation.
        Queries FinishedUnit with optional filters.

        Args:
            name_search: Optional name filter (case-insensitive partial match)
            category: Optional category filter (exact match)
            recipe_id: Optional recipe ID filter

        Returns:
            List of FinishedUnit instances matching filters

        Performance:
            Must complete in <200ms for up to 10k records per contract
        """
        try:
            with get_db_session() as session:
                query = session.query(FinishedUnit).options(selectinload(FinishedUnit.recipe))

                # Apply filters
                if recipe_id:
                    query = query.filter(FinishedUnit.recipe_id == recipe_id)

                if category:
                    query = query.filter(FinishedUnit.category == category)

                if name_search:
                    query = query.filter(FinishedUnit.display_name.ilike(f"%{name_search}%"))

                units = query.order_by(FinishedUnit.display_name).all()

                logger.debug(
                    f"Retrieved {len(units)} FinishedUnits with filters: "
                    f"name_search={name_search}, category={category}, recipe_id={recipe_id}"
                )
                return units

        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving FinishedUnits: {e}")
            raise DatabaseError(f"Failed to retrieve FinishedUnits: {e}")

    @staticmethod
    def create_finished_unit(
        display_name: str, recipe_id: int, session: Optional[Session] = None, **kwargs
    ) -> FinishedUnit:
        """
        Create a new FinishedUnit.

        Transaction boundary: Uses provided session or creates new session_scope.
        When session is provided, all operations execute within the caller's transaction.
        Atomicity guarantee: Either ALL steps succeed OR entire operation rolls back.
        Steps executed atomically:
            1. Validate display_name and recipe_id
            2. Validate yield_type
            3. Generate unique slug
            4. Validate recipe reference exists
            5. Validate name unique within recipe
            6. Create FinishedUnit record

        Args:
            display_name: Required string name
            recipe_id: Required Recipe ID reference (cannot be None)
            session: Optional session for transaction composition
            **kwargs: Additional optional fields

        Returns:
            Created FinishedUnit instance

        Raises:
            ValidationError: If validation fails
            DuplicateSlugError: If slug already exists
            DatabaseError: If database operation fails

        Performance:
            Must complete in <500ms per contract

        Note:
            Feature 045: unit_cost removed from FinishedUnit model.
            Costs are now tracked on ProductionRun instances.
        """
        # Validate required fields (before session — pure validation)
        if not display_name or not display_name.strip():
            raise ValidationError(["Display name is required and cannot be empty"])

        if recipe_id is None:
            raise ValidationError(["Recipe ID is required and cannot be None"])

        # Feature 083: Validate yield_type (default to 'SERVING' for backward compatibility)
        yield_type = kwargs.pop("yield_type", "SERVING")
        yield_type_errors = validate_yield_type(yield_type)
        if yield_type_errors:
            raise ValueError(f"Invalid yield_type: {'; '.join(yield_type_errors)}")

        if session is not None:
            return FinishedUnitService._create_finished_unit_impl(
                display_name, recipe_id, session, yield_type, **kwargs
            )

        # Retry logic for handling race conditions in slug generation
        max_retries = 3
        for attempt in range(max_retries):
            try:
                with session_scope() as sess:
                    return FinishedUnitService._create_finished_unit_impl(
                        display_name, recipe_id, sess, yield_type, **kwargs
                    )

            except IntegrityError as e:
                if "uq_finished_unit_slug" in str(e) and attempt < max_retries - 1:
                    # Race condition detected, retry with new slug
                    logger.warning(f"Slug collision detected on attempt {attempt + 1}, retrying...")
                    continue
                else:
                    # Final attempt failed or different integrity error
                    logger.error(f"Integrity error creating FinishedUnit: {e}")
                    if "uq_finished_unit_slug" in str(e):
                        raise DuplicateSlugError(
                            f"Unable to generate unique slug after {max_retries} attempts"
                        )
                    else:
                        raise DatabaseError(f"Database integrity error: {e}")

            except SQLAlchemyError as e:
                logger.error(f"Database error creating FinishedUnit: {e}")
                raise DatabaseError(f"Failed to create FinishedUnit: {e}")

    @staticmethod
    def _create_finished_unit_impl(
        display_name: str,
        recipe_id: int,
        session: Session,
        yield_type: str,
        **kwargs,
    ) -> FinishedUnit:
        """Internal implementation of FinishedUnit creation.

        Transaction boundary: Inherits session from caller.
        All operations execute within the caller's transaction scope.
        """
        # Generate unique slug (more robust against race conditions)
        slug = FinishedUnitService._generate_unique_slug(display_name.strip(), session)

        # Validate recipe reference (required)
        recipe = session.query(Recipe).filter(Recipe.id == recipe_id).first()
        if not recipe:
            raise ValidationError([f"Recipe ID {recipe_id} does not exist"])

        # Validate name uniqueness within recipe (per yield_type)
        FinishedUnitService._validate_name_unique_in_recipe(
            display_name.strip(), recipe_id, session, yield_type
        )

        # Create FinishedUnit with validated data
        # Feature 045: unit_cost removed from FinishedUnit model
        # Feature 083: yield_type added for dual-yield support
        unit_data = {
            "slug": slug,
            "display_name": display_name.strip(),
            "recipe_id": recipe_id,
            "inventory_count": kwargs.get("inventory_count", 0),
            "yield_mode": kwargs.get("yield_mode"),
            "yield_type": yield_type,  # Feature 083: Dual-yield support
            "items_per_batch": kwargs.get("items_per_batch"),
            "item_unit": kwargs.get("item_unit"),
            "batch_percentage": kwargs.get("batch_percentage"),
            "portion_description": kwargs.get("portion_description"),
            "category": kwargs.get("category") or recipe.category,
            "production_notes": kwargs.get("production_notes"),
            "notes": kwargs.get("notes"),
        }

        # Remove None values
        unit_data = {k: v for k, v in unit_data.items() if v is not None}

        finished_unit = FinishedUnit(**unit_data)
        session.add(finished_unit)
        session.flush()  # Get the ID

        logger.info(
            f"Created FinishedUnit: {finished_unit.display_name} (ID: {finished_unit.id})"
        )
        return finished_unit

    @staticmethod
    def update_finished_unit(
        finished_unit_id: int, session: Optional[Session] = None, **updates
    ) -> FinishedUnit:
        """
        Update an existing FinishedUnit.

        Transaction boundary: Uses provided session or creates new session_scope.
        When session is provided, all operations execute within the caller's transaction.
        Atomicity guarantee: Either ALL steps succeed OR entire operation rolls back.
        Steps executed atomically:
            1. Query existing FinishedUnit
            2. Validate update values
            3. Regenerate slug if display_name changed
            4. Apply updates
            5. Update timestamps

        Args:
            finished_unit_id: ID of FinishedUnit to update
            session: Optional session for transaction composition
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
        if session is not None:
            return FinishedUnitService._update_finished_unit_impl(
                finished_unit_id, session, **updates
            )

        try:
            with session_scope() as sess:
                return FinishedUnitService._update_finished_unit_impl(
                    finished_unit_id, sess, **updates
                )

        except SQLAlchemyError as e:
            logger.error(f"Database error updating FinishedUnit ID {finished_unit_id}: {e}")
            raise DatabaseError(f"Failed to update FinishedUnit: {e}")

    @staticmethod
    def _update_finished_unit_impl(
        finished_unit_id: int, session: Session, **updates
    ) -> FinishedUnit:
        """Internal implementation of FinishedUnit update.

        Transaction boundary: Inherits session from caller.
        All operations execute within the caller's transaction scope.
        """
        unit = (
            session.query(FinishedUnit).filter(FinishedUnit.id == finished_unit_id).first()
        )

        if not unit:
            raise FinishedUnitNotFoundError(f"FinishedUnit ID {finished_unit_id} not found")

        # Validate updates
        if "display_name" in updates:
            display_name = updates["display_name"]
            if not display_name or not display_name.strip():
                raise ValidationError(["Display name cannot be empty"])

            # Update slug if display name changed
            if display_name.strip() != unit.display_name:
                new_slug = FinishedUnitService._generate_unique_slug(
                    display_name.strip(), session, unit.id
                )
                updates["slug"] = new_slug

        # Feature 045: unit_cost validation removed (field no longer exists)

        # Feature 083: Validate yield_type if being updated
        if "yield_type" in updates:
            yield_type = updates["yield_type"]
            yield_type_errors = validate_yield_type(yield_type)
            if yield_type_errors:
                raise ValueError(f"Invalid yield_type: {'; '.join(yield_type_errors)}")

        if "inventory_count" in updates and updates["inventory_count"] < 0:
            raise ValidationError(["Inventory count must be non-negative"])

        if "recipe_id" in updates and updates["recipe_id"] is not None:
            recipe = session.query(Recipe).filter(Recipe.id == updates["recipe_id"]).first()
            if not recipe:
                raise ValidationError([f"Recipe ID {updates['recipe_id']} does not exist"])

        # Validate name uniqueness within recipe for renames or recipe changes
        # Get the effective values after update
        effective_name = updates.get("display_name", unit.display_name)
        if effective_name:
            effective_name = effective_name.strip()
        effective_recipe_id = updates.get("recipe_id", unit.recipe_id)
        effective_yield_type = updates.get("yield_type", unit.yield_type or "SERVING")

        # Check if name, recipe, or yield_type is changing
        name_changing = "display_name" in updates and effective_name != unit.display_name
        recipe_changing = "recipe_id" in updates and effective_recipe_id != unit.recipe_id
        yield_type_changing = "yield_type" in updates and effective_yield_type != unit.yield_type

        if name_changing or recipe_changing or yield_type_changing:
            FinishedUnitService._validate_name_unique_in_recipe(
                effective_name,
                effective_recipe_id,
                session,
                effective_yield_type,
                exclude_id=finished_unit_id,
            )

        # Apply updates
        for field, value in updates.items():
            if hasattr(unit, field):
                setattr(unit, field, value)

        unit.updated_at = utc_now()
        session.flush()

        logger.info(f"Updated FinishedUnit ID {finished_unit_id}: {unit.display_name}")
        return unit

    @staticmethod
    def delete_finished_unit(finished_unit_id: int, session: Optional[Session] = None) -> bool:
        """
        Delete a FinishedUnit.

        Transaction boundary: Uses provided session or creates new session_scope.
        When session is provided, all operations execute within the caller's transaction.
        Atomicity guarantee: Either ALL steps succeed OR entire operation rolls back.
        Steps executed atomically:
            1. Query FinishedUnit
            2. Check for composition references
            3. Delete FinishedUnit

        Args:
            finished_unit_id: ID of FinishedUnit to delete
            session: Optional session for transaction composition

        Returns:
            True if deleted, False if not found

        Raises:
            ReferencedUnitError: If unit is used in compositions
            DatabaseError: If database operation fails

        Performance:
            Must complete in <500ms per contract
        """
        if session is not None:
            return FinishedUnitService._delete_finished_unit_impl(
                finished_unit_id, session
            )

        try:
            with session_scope() as sess:
                return FinishedUnitService._delete_finished_unit_impl(
                    finished_unit_id, sess
                )

        except SQLAlchemyError as e:
            logger.error(f"Database error deleting FinishedUnit ID {finished_unit_id}: {e}")
            raise DatabaseError(f"Failed to delete FinishedUnit: {e}")

    @staticmethod
    def _delete_finished_unit_impl(finished_unit_id: int, session: Session) -> bool:
        """Internal implementation of FinishedUnit deletion.

        Transaction boundary: Inherits session from caller.
        All operations execute within the caller's transaction scope.
        """
        unit = (
            session.query(FinishedUnit).filter(FinishedUnit.id == finished_unit_id).first()
        )

        if not unit:
            logger.debug(f"FinishedUnit ID {finished_unit_id} not found for deletion")
            return False

        # Check for composition references
        composition_count = (
            session.query(Composition)
            .filter(Composition.finished_unit_id == finished_unit_id)
            .count()
        )

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

    # Inventory Management

    @staticmethod
    def update_inventory(finished_unit_id: int, quantity_change: int) -> FinishedUnit:
        """
        Adjust inventory count for a FinishedUnit.

        Transaction boundary: Single-step write.
        Updates FinishedUnit.inventory_count atomically.

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
                unit = (
                    session.query(FinishedUnit).filter(FinishedUnit.id == finished_unit_id).first()
                )

                if not unit:
                    raise FinishedUnitNotFoundError(f"FinishedUnit ID {finished_unit_id} not found")

                new_count = unit.inventory_count + quantity_change

                if new_count < 0:
                    raise InvalidInventoryError(
                        f"Inventory change of {quantity_change} would result in negative inventory "
                        f"(current: {unit.inventory_count}, would be: {new_count})"
                    )

                unit.inventory_count = new_count
                unit.updated_at = utc_now()
                session.flush()

                logger.info(
                    f"Updated inventory for '{unit.display_name}': {quantity_change:+d} "
                    f"(new total: {new_count})"
                )
                return unit

        except SQLAlchemyError as e:
            logger.error(
                f"Database error updating inventory for FinishedUnit ID {finished_unit_id}: {e}"
            )
            raise DatabaseError(f"Failed to update inventory: {e}")

    @staticmethod
    def check_availability(finished_unit_id: int, required_quantity: int) -> bool:
        """
        Check if sufficient inventory exists.

        Transaction boundary: Read-only operation.
        Queries FinishedUnit.inventory_count.

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
                unit = (
                    session.query(FinishedUnit).filter(FinishedUnit.id == finished_unit_id).first()
                )

                if not unit:
                    raise FinishedUnitNotFoundError(f"FinishedUnit ID {finished_unit_id} not found")

                is_available = unit.inventory_count >= required_quantity
                logger.debug(
                    f"Availability check for '{unit.display_name}': "
                    f"required {required_quantity}, available {unit.inventory_count}, "
                    f"result: {is_available}"
                )

                return is_available

        except SQLAlchemyError as e:
            logger.error(
                f"Database error checking availability for FinishedUnit ID {finished_unit_id}: {e}"
            )
            raise DatabaseError(f"Failed to check availability: {e}")

    # Query Operations

    @staticmethod
    def search_finished_units(query: str) -> List[FinishedUnit]:
        """
        Search FinishedUnits by display name, category, and notes.

        Transaction boundary: Read-only operation.
        Queries FinishedUnit with text search filters.

        Note: Description field removed from search for performance (no index on text field).

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

            search_term = f"%{query.strip()}%"  # Remove .lower() - ilike is case-insensitive

            with get_db_session() as session:
                units = (
                    session.query(FinishedUnit)
                    .options(selectinload(FinishedUnit.recipe))
                    .filter(
                        or_(
                            FinishedUnit.display_name.ilike(search_term),
                            FinishedUnit.category.ilike(search_term),
                            FinishedUnit.notes.ilike(search_term),
                        )
                    )
                    .order_by(FinishedUnit.display_name)
                    .all()
                )

                logger.debug(f"Search for '{query}' returned {len(units)} FinishedUnits")
                return units

        except SQLAlchemyError as e:
            logger.error(f"Database error searching FinishedUnits with query '{query}': {e}")
            raise DatabaseError(f"Failed to search FinishedUnits: {e}")

    @staticmethod
    def get_units_by_recipe(
        recipe_id: int, session: Optional[Session] = None
    ) -> List[FinishedUnit]:
        """
        Get all FinishedUnits associated with a specific recipe.

        Transaction boundary: Uses provided session or creates new read-only session.

        Args:
            recipe_id: Recipe ID to filter by
            session: Optional session for transaction composition

        Returns:
            List of FinishedUnit instances

        Performance:
            Must complete in <200ms per contract
        """
        if session is not None:
            return FinishedUnitService._get_units_by_recipe_impl(recipe_id, session)

        try:
            with get_db_session() as sess:
                return FinishedUnitService._get_units_by_recipe_impl(recipe_id, sess)

        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving FinishedUnits for recipe ID {recipe_id}: {e}")
            raise DatabaseError(f"Failed to retrieve FinishedUnits by recipe: {e}")

    @staticmethod
    def _get_units_by_recipe_impl(recipe_id: int, session: Session) -> List[FinishedUnit]:
        """Internal implementation of get_units_by_recipe.

        Transaction boundary: Inherits session from caller.
        """
        units = (
            session.query(FinishedUnit)
            .options(selectinload(FinishedUnit.recipe))
            .filter(FinishedUnit.recipe_id == recipe_id)
            .order_by(FinishedUnit.display_name)
            .all()
        )

        logger.debug(f"Retrieved {len(units)} FinishedUnits for recipe ID {recipe_id}")
        return units

    # Utility methods

    @staticmethod
    def _generate_slug(display_name: str) -> str:
        """Generate URL-safe slug from display name.

        Transaction boundary: Pure computation (no database access).
        """
        if not display_name:
            return "unknown-item"

        # Normalize unicode characters
        slug = unicodedata.normalize("NFKD", display_name)

        # Convert to lowercase and replace spaces/punctuation with hyphens
        slug = re.sub(r"[^\w\s-]", "", slug).strip().lower()
        slug = re.sub(r"[\s_-]+", "-", slug)

        # Remove leading/trailing hyphens
        slug = slug.strip("-")

        # Ensure not empty
        if not slug:
            return "unknown-item"

        # Limit length
        if len(slug) > 90:
            slug = slug[:90].rstrip("-")

        return slug

    @staticmethod
    def _generate_unique_slug(
        display_name: str, session: Session, exclude_id: Optional[int] = None
    ) -> str:
        """Generate unique slug, adding suffix if needed.

        Transaction boundary: Inherits session from caller.
        Read-only queries within the caller's transaction scope.
        """
        base_slug = FinishedUnitService._generate_slug(display_name)

        # Try base slug first with retry on conflict
        max_attempts = 1000
        for attempt in range(max_attempts):
            if attempt == 0:
                candidate_slug = base_slug
            else:
                candidate_slug = f"{base_slug}-{attempt + 1}"

            # Check uniqueness
            query = session.query(FinishedUnit).filter(FinishedUnit.slug == candidate_slug)
            if exclude_id:
                query = query.filter(FinishedUnit.id != exclude_id)

            existing = query.first()

            if not existing:
                return candidate_slug

        raise ValidationError([f"Unable to generate unique slug after {max_attempts} attempts"])

    @staticmethod
    def _validate_name_unique_in_recipe(
        display_name: str,
        recipe_id: int,
        session: Session,
        yield_type: str = "SERVING",
        exclude_id: Optional[int] = None,
    ) -> None:
        """
        Validate that (display_name, yield_type) is unique within a recipe.

        Transaction boundary: Inherits session from caller.
        Read-only validation within the caller's transaction scope.

        Uses case-insensitive comparison to prevent duplicates like
        "Large Cookie" vs "large cookie".

        Feature 083: Allows same display_name with different yield_types,
        e.g., "Large Cake (EA)" and "Large Cake (SERVING)" are both valid.

        Args:
            display_name: The name to validate
            recipe_id: The recipe ID to check within
            session: SQLAlchemy session to use
            yield_type: The yield type (EA or SERVING)
            exclude_id: Optional FinishedUnit ID to exclude (for updates)

        Raises:
            ValidationError: If a duplicate (name, yield_type) exists for this recipe
        """
        query = session.query(FinishedUnit).filter(
            FinishedUnit.recipe_id == recipe_id,
            func.lower(FinishedUnit.display_name) == func.lower(display_name.strip()),
            FinishedUnit.yield_type == yield_type,
        )
        if exclude_id is not None:
            query = query.filter(FinishedUnit.id != exclude_id)

        existing = query.first()
        if existing:
            raise ValidationError(
                [f"A yield type named '{display_name}' with type '{yield_type}' "
                 f"already exists for this recipe"]
            )


# Module-level convenience functions for backward compatibility


def get_finished_unit_count() -> int:
    """Get total count of all FinishedUnits."""
    return FinishedUnitService.get_finished_unit_count()


def get_finished_unit_by_id(finished_unit_id: int) -> FinishedUnit:
    """Retrieve a specific FinishedUnit by ID.

    Raises:
        FinishedUnitNotFoundById: If finished unit doesn't exist
    """
    return FinishedUnitService.get_finished_unit_by_id(finished_unit_id)


def get_finished_unit_by_slug(slug: str) -> FinishedUnit:
    """Retrieve a specific FinishedUnit by slug.

    Raises:
        FinishedUnitNotFoundBySlug: If finished unit doesn't exist
    """
    return FinishedUnitService.get_finished_unit_by_slug(slug)


def get_all_finished_units(
    name_search: Optional[str] = None,
    category: Optional[str] = None,
    recipe_id: Optional[int] = None,
) -> List[FinishedUnit]:
    """Retrieve all FinishedUnits with optional filtering."""
    return FinishedUnitService.get_all_finished_units(
        name_search=name_search,
        category=category,
        recipe_id=recipe_id,
    )


def create_finished_unit(
    display_name: str, recipe_id: int = None, session: Optional[Session] = None, **kwargs
) -> FinishedUnit:
    """Create a new FinishedUnit."""
    return FinishedUnitService.create_finished_unit(
        display_name, recipe_id=recipe_id, session=session, **kwargs
    )


def update_finished_unit(
    finished_unit_id: int, session: Optional[Session] = None, **updates
) -> FinishedUnit:
    """Update an existing FinishedUnit."""
    return FinishedUnitService.update_finished_unit(
        finished_unit_id, session=session, **updates
    )


def delete_finished_unit(
    finished_unit_id: int, session: Optional[Session] = None
) -> bool:
    """Delete a FinishedUnit."""
    return FinishedUnitService.delete_finished_unit(
        finished_unit_id, session=session
    )


def update_inventory(finished_unit_id: int, quantity_change: int) -> FinishedUnit:
    """Adjust inventory count for a FinishedUnit."""
    return FinishedUnitService.update_inventory(finished_unit_id, quantity_change)


def check_availability(finished_unit_id: int, required_quantity: int) -> bool:
    """Check if sufficient inventory exists."""
    return FinishedUnitService.check_availability(finished_unit_id, required_quantity)


def search_finished_units(query: str) -> List[FinishedUnit]:
    """Search FinishedUnits by display name or description."""
    return FinishedUnitService.search_finished_units(query)


def get_units_by_recipe(
    recipe_id: int, session: Optional[Session] = None
) -> List[FinishedUnit]:
    """Get all FinishedUnits associated with a specific recipe."""
    return FinishedUnitService.get_units_by_recipe(recipe_id, session=session)


def propagate_yield_to_variants(recipe_id: int) -> int:
    """
    Propagate yield fields from a base recipe's FinishedUnits to all variant recipes.

    When a base recipe's yield data changes (yield_type, items_per_batch, item_unit,
    yield_mode), this function pushes those changes to all variant recipe FUs.

    Matching strategy: base FUs and variant FUs are matched by ID order, since
    variants are created with the same number of FUs in the same order as the base.

    Args:
        recipe_id: ID of the base recipe whose yield data changed

    Returns:
        Number of variant FinishedUnits updated

    Raises:
        DatabaseError: If database operation fails
    """
    try:
        with session_scope() as session:
            # Check if this recipe is a base recipe (not a variant itself)
            recipe = session.query(Recipe).filter_by(id=recipe_id).first()
            if not recipe or recipe.base_recipe_id is not None:
                return 0

            # Get all variant recipes
            variants = (
                session.query(Recipe)
                .filter_by(base_recipe_id=recipe_id, is_archived=False)
                .all()
            )
            if not variants:
                return 0

            # Get base FUs ordered by ID for stable matching
            base_fus = (
                session.query(FinishedUnit)
                .filter_by(recipe_id=recipe_id)
                .order_by(FinishedUnit.id)
                .all()
            )
            if not base_fus:
                return 0

            updated_count = 0
            yield_fields = [
                "yield_type", "items_per_batch", "item_unit",
                "yield_mode", "batch_percentage", "portion_description",
            ]

            for variant in variants:
                variant_fus = (
                    session.query(FinishedUnit)
                    .filter_by(recipe_id=variant.id)
                    .order_by(FinishedUnit.id)
                    .all()
                )

                if len(variant_fus) != len(base_fus):
                    logger.warning(
                        f"Variant recipe {variant.id} has {len(variant_fus)} FUs "
                        f"but base has {len(base_fus)}; skipping propagation"
                    )
                    continue

                for base_fu, variant_fu in zip(base_fus, variant_fus):
                    changed = False
                    for field in yield_fields:
                        base_val = getattr(base_fu, field)
                        if getattr(variant_fu, field) != base_val:
                            setattr(variant_fu, field, base_val)
                            changed = True
                    if changed:
                        variant_fu.updated_at = utc_now()
                        updated_count += 1

            session.flush()
            if updated_count:
                logger.info(
                    f"Propagated yield changes from recipe {recipe_id} "
                    f"to {updated_count} variant FinishedUnit(s)"
                )
            return updated_count

    except SQLAlchemyError as e:
        logger.error(f"Failed to propagate yield to variants for recipe {recipe_id}: {e}")
        raise DatabaseError(f"Failed to propagate yield to variants: {e}")


# =============================================================================
# Feature 064: FinishedUnitSnapshot Service Functions
# =============================================================================


def create_finished_unit_snapshot(
    finished_unit_id: int,
    planning_snapshot_id: int = None,
    assembly_run_id: int = None,
    session: Optional[Session] = None,
) -> dict:
    """
    Create immutable snapshot of FinishedUnit definition.

    Args:
        finished_unit_id: Source FinishedUnit ID
        planning_snapshot_id: Optional planning context
        assembly_run_id: Optional assembly context
        session: Optional session for transaction sharing

    Returns:
        dict with snapshot id and definition_data

    Raises:
        SnapshotCreationError: If FinishedUnit not found or creation fails
    """
    if session is not None:
        return _create_finished_unit_snapshot_impl(
            finished_unit_id, planning_snapshot_id, assembly_run_id, session
        )

    try:
        with session_scope() as session:
            return _create_finished_unit_snapshot_impl(
                finished_unit_id, planning_snapshot_id, assembly_run_id, session
            )
    except SQLAlchemyError as e:
        raise SnapshotCreationError(f"Database error creating snapshot: {e}")


def _create_finished_unit_snapshot_impl(
    finished_unit_id: int,
    planning_snapshot_id: int,
    assembly_run_id: int,
    session: Session,
) -> dict:
    """Internal implementation of snapshot creation."""
    # Load FinishedUnit with recipe relationship
    fu = session.query(FinishedUnit).filter_by(id=finished_unit_id).first()
    if not fu:
        raise SnapshotCreationError(f"FinishedUnit {finished_unit_id} not found")

    # Eagerly load recipe for denormalization
    recipe = fu.recipe

    # Build definition_data JSON
    definition_data = {
        "slug": fu.slug,
        "display_name": fu.display_name,
        "description": fu.description,
        "recipe_id": fu.recipe_id,
        "recipe_name": recipe.name if recipe else None,
        "recipe_category": recipe.category if recipe else None,
        "yield_mode": fu.yield_mode.value if fu.yield_mode else None,
        "items_per_batch": fu.items_per_batch,
        "item_unit": fu.item_unit,
        "batch_percentage": float(fu.batch_percentage) if fu.batch_percentage else None,
        "portion_description": fu.portion_description,
        "category": fu.category,
        "production_notes": fu.production_notes,
        "notes": fu.notes,
    }

    # Create snapshot
    snapshot = FinishedUnitSnapshot(
        finished_unit_id=finished_unit_id,
        planning_snapshot_id=planning_snapshot_id,
        assembly_run_id=assembly_run_id,
        definition_data=json.dumps(definition_data),
        is_backfilled=False,
    )

    session.add(snapshot)
    session.flush()  # Get ID without committing

    return {
        "id": snapshot.id,
        "finished_unit_id": snapshot.finished_unit_id,
        "planning_snapshot_id": snapshot.planning_snapshot_id,
        "assembly_run_id": snapshot.assembly_run_id,
        "snapshot_date": snapshot.snapshot_date.isoformat(),
        "definition_data": definition_data,
        "is_backfilled": snapshot.is_backfilled,
    }


def get_finished_unit_snapshot(
    snapshot_id: int,
    session: Optional[Session] = None,
) -> dict | None:
    """
    Get a FinishedUnitSnapshot by its ID.

    Args:
        snapshot_id: Snapshot ID
        session: Optional session

    Returns:
        Snapshot dict or None if not found
    """
    if session is not None:
        return _get_finished_unit_snapshot_impl(snapshot_id, session)

    with session_scope() as session:
        return _get_finished_unit_snapshot_impl(snapshot_id, session)


def _get_finished_unit_snapshot_impl(
    snapshot_id: int,
    session: Session,
) -> dict | None:
    """Internal implementation of snapshot retrieval."""
    snapshot = session.query(FinishedUnitSnapshot).filter_by(id=snapshot_id).first()

    if not snapshot:
        return None

    return {
        "id": snapshot.id,
        "finished_unit_id": snapshot.finished_unit_id,
        "planning_snapshot_id": snapshot.planning_snapshot_id,
        "assembly_run_id": snapshot.assembly_run_id,
        "snapshot_date": snapshot.snapshot_date.isoformat(),
        "definition_data": snapshot.get_definition_data(),
        "is_backfilled": snapshot.is_backfilled,
    }


def get_finished_unit_snapshots_by_planning_id(
    planning_snapshot_id: int,
    session: Optional[Session] = None,
) -> list[dict]:
    """
    Get all FinishedUnitSnapshots for a planning snapshot.

    Args:
        planning_snapshot_id: PlanningSnapshot ID
        session: Optional session

    Returns:
        List of snapshot dicts
    """
    if session is not None:
        return _get_fu_snapshots_by_planning_impl(planning_snapshot_id, session)

    with session_scope() as session:
        return _get_fu_snapshots_by_planning_impl(planning_snapshot_id, session)


def _get_fu_snapshots_by_planning_impl(
    planning_snapshot_id: int,
    session: Session,
) -> list[dict]:
    """Internal implementation of planning snapshot query."""
    snapshots = (
        session.query(FinishedUnitSnapshot)
        .filter_by(planning_snapshot_id=planning_snapshot_id)
        .order_by(FinishedUnitSnapshot.snapshot_date.desc())
        .all()
    )

    return [
        {
            "id": s.id,
            "finished_unit_id": s.finished_unit_id,
            "planning_snapshot_id": s.planning_snapshot_id,
            "snapshot_date": s.snapshot_date.isoformat(),
            "definition_data": s.get_definition_data(),
            "is_backfilled": s.is_backfilled,
        }
        for s in snapshots
    ]
