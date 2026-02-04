"""
FinishedGood Service - Assembly management and hierarchical composition operations.

This service provides comprehensive management for FinishedGood assemblies, implementing
User Story 2: Create Simple Package Assemblies with component tracking, hierarchy
operations, cost calculations, and inventory management.

Key Features:
- Complete assembly CRUD operations with component validation
- Polymorphic component management (FinishedUnit and FinishedGood components)
- Hierarchy traversal with circular reference prevention
- Cost aggregation from component costs
- Assembly production workflows with inventory management
- High-performance operations for complex assembly hierarchies
"""

import logging
from decimal import Decimal
from typing import List, Optional, Dict, Any, Set, Tuple
import re
import unicodedata
from datetime import datetime
from src.utils.datetime_utils import utc_now
from collections import deque

from sqlalchemy import and_, or_, text
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from .database import get_db_session, session_scope
from ..models import FinishedGood, FinishedUnit, Composition, AssemblyType
from ..models.material_unit import MaterialUnit
from ..models.assembly_type import (
    validate_assembly_type_business_rules,
    calculate_packaging_cost,
    get_suggested_retail_price,
)
from . import finished_unit_service
from .exceptions import (
    DatabaseError,
    FinishedGoodNotFoundById,
    FinishedGoodNotFoundBySlug,
    ServiceError,
    ValidationError,
)

logger = logging.getLogger(__name__)


# Custom exceptions for FinishedGood service
class FinishedGoodNotFoundError(ServiceError):
    """Raised when a FinishedGood assembly cannot be found."""

    pass


class CircularReferenceError(ServiceError):
    """Raised when operation would create circular dependency."""

    pass


class InsufficientInventoryError(ServiceError):
    """Raised when components unavailable for assembly."""

    pass


class InvalidComponentError(ServiceError):
    """Raised when component doesn't exist or is invalid."""

    pass


class AssemblyIntegrityError(ServiceError):
    """Raised when assembly state becomes invalid."""

    pass


class FinishedGoodService:
    """
    Service for FinishedGood assembly operations and hierarchical management.

    Provides comprehensive assembly creation, component management, hierarchy
    traversal, cost calculations, and inventory operations.
    """

    # Core Operations

    @staticmethod
    def get_finished_good_by_id(finished_good_id: int) -> FinishedGood:
        """
        Retrieve a specific FinishedGood assembly by ID.

        Transaction boundary: Read-only operation.
        Queries FinishedGood table with components eager loaded.

        Args:
            finished_good_id: Integer ID of the FinishedGood

        Returns:
            FinishedGood instance

        Raises:
            FinishedGoodNotFoundById: If finished good doesn't exist

        Performance:
            Must complete in <50ms per contract
        """
        try:
            with get_db_session() as session:
                finished_good = (
                    session.query(FinishedGood)
                    .options(selectinload(FinishedGood.components))
                    .filter(FinishedGood.id == finished_good_id)
                    .first()
                )

                if finished_good:
                    logger.debug(
                        f"Retrieved FinishedGood by ID {finished_good_id}: {finished_good.display_name}"
                    )
                    return finished_good
                else:
                    logger.debug(f"FinishedGood not found for ID {finished_good_id}")
                    raise FinishedGoodNotFoundById(finished_good_id)

        except FinishedGoodNotFoundById:
            raise
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving FinishedGood ID {finished_good_id}: {e}")
            raise DatabaseError(f"Failed to retrieve FinishedGood by ID: {e}")

    @staticmethod
    def get_finished_good_by_slug(slug: str) -> FinishedGood:
        """
        Retrieve a specific FinishedGood by slug identifier.

        Transaction boundary: Read-only operation.
        Queries FinishedGood table with indexed slug lookup.

        Args:
            slug: String slug identifier

        Returns:
            FinishedGood instance

        Raises:
            FinishedGoodNotFoundBySlug: If finished good doesn't exist

        Performance:
            Must complete in <50ms per contract (indexed lookup)
        """
        try:
            with get_db_session() as session:
                finished_good = (
                    session.query(FinishedGood)
                    .options(selectinload(FinishedGood.components))
                    .filter(FinishedGood.slug == slug)
                    .first()
                )

                if finished_good:
                    logger.debug(
                        f"Retrieved FinishedGood by slug '{slug}': {finished_good.display_name}"
                    )
                    return finished_good
                else:
                    logger.debug(f"FinishedGood not found for slug '{slug}'")
                    raise FinishedGoodNotFoundBySlug(slug)

        except FinishedGoodNotFoundBySlug:
            raise
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving FinishedGood slug '{slug}': {e}")
            raise DatabaseError(f"Failed to retrieve FinishedGood by slug: {e}")

    @staticmethod
    def get_all_finished_goods() -> List[FinishedGood]:
        """
        Retrieve all FinishedGood assemblies.

        Transaction boundary: Read-only operation.
        Queries FinishedGood table with components eager loaded.

        Returns:
            List of all FinishedGood instances

        Performance:
            Must complete in <300ms for up to 1000 assemblies per contract
        """
        try:
            with get_db_session() as session:
                finished_goods = (
                    session.query(FinishedGood)
                    .options(selectinload(FinishedGood.components))
                    .order_by(FinishedGood.display_name)
                    .all()
                )

                logger.debug(f"Retrieved {len(finished_goods)} FinishedGoods")
                return finished_goods

        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving all FinishedGoods: {e}")
            raise DatabaseError(f"Failed to retrieve all FinishedGoods: {e}")

    @staticmethod
    def create_finished_good(
        display_name: str,
        assembly_type: AssemblyType = AssemblyType.CUSTOM_ORDER,
        components: Optional[List[Dict]] = None,
        session=None,
        **kwargs
    ) -> FinishedGood:
        """
        Create a new assembly package with optional components.

        Transaction boundary: Multi-step operation (atomic).
        Atomicity guarantee: Either ALL steps succeed OR entire operation rolls back.
        Steps executed atomically:
            1. Validate display_name and assembly_type
            2. Generate unique slug
            3. Validate all components exist
            4. Create FinishedGood record
            5. Create Composition records for each component
            6. Validate assembly type business rules

        Args:
            display_name: Required string name
            assembly_type: AssemblyType enum value (default: CUSTOM_ORDER)
            components: Optional list of component specifications with structure:
                [{"type": "finished_unit"|"material_unit"|"finished_good",
                  "id": int, "quantity": int, "notes": str|None, "sort_order": int}]
            session: Optional database session for transaction sharing
            **kwargs: Additional optional fields (description, packaging_instructions,
                     notes, inventory_count)

        Returns:
            Created FinishedGood instance

        Raises:
            ValidationError: If validation fails
            InvalidComponentError: If components are invalid
            CircularReferenceError: If circular references detected

        Performance:
            Must complete in <2s for assemblies with up to 20 components per contract
        """
        # Validate required fields before starting transaction
        if not display_name or not display_name.strip():
            raise ValidationError(["Display name is required and cannot be empty"])

        if not isinstance(assembly_type, AssemblyType):
            raise ValidationError(["Assembly type must be a valid AssemblyType enum"])

        # Use session management pattern
        if session is not None:
            return FinishedGoodService._create_finished_good_impl(
                display_name, assembly_type, components, session, **kwargs
            )

        try:
            with session_scope() as session:
                return FinishedGoodService._create_finished_good_impl(
                    display_name, assembly_type, components, session, **kwargs
                )
        except IntegrityError as e:
            logger.error(f"Integrity error creating FinishedGood: {e}")
            if "uq_finished_good_slug" in str(e):
                raise ValidationError(
                    f"Slug already exists for display name '{display_name}'"
                )
            else:
                raise DatabaseError(f"Database integrity error: {e}")
        except SQLAlchemyError as e:
            logger.error(f"Database error creating FinishedGood: {e}")
            raise DatabaseError(f"Failed to create FinishedGood: {e}")

    @staticmethod
    def _create_finished_good_impl(
        display_name: str,
        assembly_type: AssemblyType,
        components: Optional[List[Dict]],
        session,
        **kwargs
    ) -> FinishedGood:
        """Internal implementation of create_finished_good with session.

        Transaction boundary: Inherits session from caller.
        Multi-step operation within the caller's transaction scope.
        """
        # Generate unique slug
        slug = FinishedGoodService._generate_slug(display_name.strip())

        # Check slug uniqueness
        existing = session.query(FinishedGood).filter(FinishedGood.slug == slug).first()
        if existing:
            # Generate unique slug with suffix
            slug = FinishedGoodService._generate_unique_slug(display_name.strip(), session)

        # Validate components if provided (before creating FinishedGood)
        if components:
            FinishedGoodService._validate_components(components, session)

        # Create FinishedGood with validated data
        assembly_data = {
            "slug": slug,
            "display_name": display_name.strip(),
            "assembly_type": assembly_type,
            "inventory_count": kwargs.get("inventory_count", 0),
            "description": kwargs.get("description"),
            "packaging_instructions": kwargs.get("packaging_instructions"),
            "notes": kwargs.get("notes"),
        }

        # Remove None values
        assembly_data = {k: v for k, v in assembly_data.items() if v is not None}

        finished_good = FinishedGood(**assembly_data)
        session.add(finished_good)
        session.flush()  # Get the ID for compositions

        # Add components if provided (atomically within the same transaction)
        if components:
            for component_spec in components:
                composition = FinishedGoodService._create_composition(
                    finished_good.id, component_spec, session
                )
                session.add(composition)

            # Validate business rules (cost parameter removed in F045)
            component_count = len(components)
            is_valid, errors = validate_assembly_type_business_rules(
                assembly_type, component_count, Decimal("0.0000")
            )
            if not is_valid:
                raise ValidationError(
                    [f"Assembly type validation failed: {'; '.join(errors)}"]
                )
        else:
            # No components provided, validate minimum requirements
            component_count = 0
            is_valid, errors = validate_assembly_type_business_rules(
                assembly_type, component_count, Decimal("0.0000")
            )
            if not is_valid:
                raise ValidationError(
                    [f"Assembly type validation failed: {'; '.join(errors)}"]
                )

        logger.info(
            f"Created FinishedGood assembly: {finished_good.display_name} (ID: {finished_good.id})"
        )
        return finished_good

    @staticmethod
    def update_finished_good(
        finished_good_id: int,
        display_name: Optional[str] = None,
        assembly_type: Optional[AssemblyType] = None,
        components: Optional[List[Dict]] = None,
        packaging_instructions: Optional[str] = None,
        notes: Optional[str] = None,
        session=None,
        **updates
    ) -> FinishedGood:
        """
        Update an existing FinishedGood with optional component replacement.

        Transaction boundary: Multi-step operation (atomic).
        Atomicity guarantee: Either ALL steps succeed OR entire operation rolls back.
        Steps executed atomically:
            1. Query existing FinishedGood
            2. Validate and update scalar fields
            3. If components provided: validate, delete old, create new compositions
            4. Validate assembly type business rules
            5. Update timestamps

        Args:
            finished_good_id: ID of FinishedGood to update
            display_name: Optional new display name
            assembly_type: Optional new assembly type
            components: Optional list of components to replace existing ones atomically.
                Structure: [{"type": "finished_unit"|"material_unit"|"finished_good",
                            "id": int, "quantity": int, "notes": str|None, "sort_order": int}]
                When provided, ALL existing components are deleted and replaced with new ones.
                Use empty list [] to clear all components.
            packaging_instructions: Optional new packaging instructions
            notes: Optional new notes
            session: Optional database session for transaction sharing
            **updates: Additional optional fields (inventory_count, description)

        Returns:
            Updated FinishedGood instance

        Raises:
            FinishedGoodNotFoundError: If assembly doesn't exist
            ValidationError: If validation fails
            InvalidComponentError: If components are invalid
            CircularReferenceError: If circular references detected

        Performance:
            Must complete in <1s per contract
        """
        if session is not None:
            return FinishedGoodService._update_finished_good_impl(
                finished_good_id, display_name, assembly_type, components,
                packaging_instructions, notes, session, **updates
            )

        try:
            with session_scope() as session:
                return FinishedGoodService._update_finished_good_impl(
                    finished_good_id, display_name, assembly_type, components,
                    packaging_instructions, notes, session, **updates
                )
        except IntegrityError as e:
            logger.error(f"Integrity error updating FinishedGood: {e}")
            if "uq_finished_good_slug" in str(e):
                raise ValidationError(
                    f"Slug already exists for display name '{display_name}'"
                )
            else:
                raise DatabaseError(f"Database integrity error: {e}")
        except SQLAlchemyError as e:
            logger.error(f"Database error updating FinishedGood ID {finished_good_id}: {e}")
            raise DatabaseError(f"Failed to update FinishedGood: {e}")

    @staticmethod
    def _update_finished_good_impl(
        finished_good_id: int,
        display_name: Optional[str],
        assembly_type: Optional[AssemblyType],
        components: Optional[List[Dict]],
        packaging_instructions: Optional[str],
        notes: Optional[str],
        session,
        **updates
    ) -> FinishedGood:
        """Internal implementation of update_finished_good with session.

        Transaction boundary: Inherits session from caller.
        Multi-step operation within the caller's transaction scope.
        """
        assembly = (
            session.query(FinishedGood)
            .options(selectinload(FinishedGood.components))
            .filter(FinishedGood.id == finished_good_id)
            .first()
        )

        if not assembly:
            raise FinishedGoodNotFoundError(f"FinishedGood ID {finished_good_id} not found")

        # Validate and update display_name
        if display_name is not None:
            if not display_name or not display_name.strip():
                raise ValidationError("Display name cannot be empty")
            # Update slug if display name changed
            if display_name.strip() != assembly.display_name:
                new_slug = FinishedGoodService._generate_unique_slug(
                    display_name.strip(), session, assembly.id
                )
                assembly.slug = new_slug
            assembly.display_name = display_name.strip()

        # Validate and update assembly_type
        if assembly_type is not None:
            if not isinstance(assembly_type, AssemblyType):
                raise ValidationError(["Assembly type must be a valid AssemblyType enum"])
            assembly.assembly_type = assembly_type

        # Update packaging_instructions
        if packaging_instructions is not None:
            assembly.packaging_instructions = packaging_instructions

        # Update notes
        if notes is not None:
            assembly.notes = notes

        # Handle additional updates from **updates
        if "inventory_count" in updates and updates["inventory_count"] < 0:
            raise ValidationError("Inventory count must be non-negative")

        if "description" in updates:
            assembly.description = updates["description"]

        if "inventory_count" in updates:
            assembly.inventory_count = updates["inventory_count"]

        # Replace components if provided (atomically delete all and create new)
        if components is not None:
            # Validate new components (including circular reference check) BEFORE making changes
            if components:  # Only validate if there are components
                FinishedGoodService._validate_components(components, session)
                FinishedGoodService._validate_no_circular_references(
                    finished_good_id, components, session
                )

            # Delete existing compositions
            session.query(Composition).filter_by(assembly_id=finished_good_id).delete()

            # Create new compositions
            for component_spec in components:
                composition = FinishedGoodService._create_composition(
                    finished_good_id, component_spec, session
                )
                session.add(composition)

            # Validate business rules with new component count
            component_count = len(components)
            is_valid, errors = validate_assembly_type_business_rules(
                assembly.assembly_type, component_count, Decimal("0.0000")
            )
            if not is_valid:
                raise ValidationError(
                    [f"Assembly type validation failed: {'; '.join(errors)}"]
                )

        assembly.updated_at = utc_now()
        session.flush()

        logger.info(f"Updated FinishedGood ID {finished_good_id}: {assembly.display_name}")
        return assembly

    @staticmethod
    def delete_finished_good(finished_good_id: int, session=None) -> bool:
        """
        Delete a FinishedGood assembly.

        Transaction boundary: Multi-step operation (atomic).
        Atomicity guarantee: Either ALL steps succeed OR entire operation rolls back.
        Steps executed atomically:
            1. Query FinishedGood
            2. Check for FinishedGood references (used as component)
            3. Check for event references (used in planning)
            4. Delete FinishedGood (cascade deletes compositions)

        Performs safety checks to prevent deleting FinishedGoods that are:
        - Referenced as components by other FinishedGoods
        - Used in event planning (EventFinishedGood)

        Args:
            finished_good_id: ID of FinishedGood to delete
            session: Optional database session for transaction sharing

        Returns:
            True if deleted, False if not found

        Raises:
            ValueError: If FinishedGood is referenced by other assemblies or events
            DatabaseError: If database operation fails

        Performance:
            Must complete in <1s per contract
        """
        if session is not None:
            return FinishedGoodService._delete_finished_good_impl(finished_good_id, session)

        try:
            with session_scope() as session:
                return FinishedGoodService._delete_finished_good_impl(finished_good_id, session)

        except SQLAlchemyError as e:
            logger.error(f"Database error deleting FinishedGood ID {finished_good_id}: {e}")
            raise DatabaseError(f"Failed to delete FinishedGood: {e}")

    @staticmethod
    def _delete_finished_good_impl(finished_good_id: int, session) -> bool:
        """Internal implementation of delete_finished_good with session.

        Transaction boundary: Inherits session from caller.
        Multi-step operation within the caller's transaction scope.
        """
        assembly = (
            session.query(FinishedGood).filter(FinishedGood.id == finished_good_id).first()
        )

        if not assembly:
            logger.debug(f"FinishedGood ID {finished_good_id} not found for deletion")
            return False

        # Check for FinishedGood references (used as component in other assemblies)
        fg_refs = FinishedGoodService._check_finished_good_references(finished_good_id, session)
        if fg_refs:
            truncated = fg_refs[:3]
            suffix = "..." if len(fg_refs) > 3 else ""
            raise ValueError(
                f"Cannot delete: referenced by {len(fg_refs)} Finished Good(s): "
                f"{', '.join(truncated)}{suffix}"
            )

        # Check for event references (used in event planning)
        event_refs = FinishedGoodService._check_event_references(finished_good_id, session)
        if event_refs:
            truncated = event_refs[:3]
            suffix = "..." if len(event_refs) > 3 else ""
            raise ValueError(
                f"Cannot delete: used in {len(event_refs)} event(s): "
                f"{', '.join(truncated)}{suffix}"
            )

        # Delete the assembly (cascade will handle compositions)
        display_name = assembly.display_name
        session.delete(assembly)

        logger.info(f"Deleted FinishedGood ID {finished_good_id}: {display_name}")
        return True

    @staticmethod
    def _check_finished_good_references(finished_good_id: int, session) -> List[str]:
        """
        Check if this FinishedGood is referenced by other FinishedGoods.

        Transaction boundary: Inherits session from caller.
        Read-only query within the caller's transaction scope.

        Args:
            finished_good_id: ID to check for references
            session: Database session

        Returns:
            List of referencing FinishedGood display names
        """
        refs = session.query(Composition).filter_by(finished_good_id=finished_good_id).all()
        referencing_names = []
        for ref in refs:
            parent = session.get(FinishedGood, ref.assembly_id)
            if parent:
                referencing_names.append(parent.display_name)
        return referencing_names

    @staticmethod
    def _check_event_references(finished_good_id: int, session) -> List[str]:
        """
        Check if this FinishedGood is referenced by events.

        Transaction boundary: Inherits session from caller.
        Read-only query within the caller's transaction scope.

        Args:
            finished_good_id: ID to check for event references
            session: Database session

        Returns:
            List of event names that reference this FinishedGood
        """
        from src.models.event_finished_good import EventFinishedGood
        from src.models.event import Event

        refs = session.query(EventFinishedGood).filter_by(
            finished_good_id=finished_good_id
        ).all()
        event_names = []
        for ref in refs:
            event = session.get(Event, ref.event_id)
            if event:
                event_names.append(event.name)
        return event_names

    @staticmethod
    def _validate_no_circular_references(
        current_fg_id: int, components: List[Dict], session
    ) -> None:
        """
        Validate that adding these components won't create circular references.

        Transaction boundary: Inherits session from caller.
        Read-only validation within the caller's transaction scope.

        A circular reference occurs when:
        1. Component is the current FinishedGood itself (A -> A)
        2. Component contains the current FinishedGood (A -> B where B -> A)
        3. Component's descendants contain current FinishedGood (transitive closure)

        Args:
            current_fg_id: ID of the FinishedGood being updated
            components: List of component specifications to add
            session: Database session

        Raises:
            CircularReferenceError: If adding any component would create a cycle
        """
        # Extract finished_good component IDs
        fg_component_ids = [
            c.get("id") or c.get("component_id")
            for c in components
            if (c.get("type") or c.get("component_type")) == "finished_good"
        ]

        if not fg_component_ids:
            return  # No nested FinishedGoods, no cycle possible

        # Check for self-reference
        if current_fg_id in fg_component_ids:
            raise CircularReferenceError(
                "Cannot add a FinishedGood as a component of itself"
            )

        # Check for cycles using BFS
        for target_id in fg_component_ids:
            if FinishedGoodService._would_create_cycle(current_fg_id, target_id, session):
                target = session.get(FinishedGood, target_id)
                target_name = target.display_name if target else f"ID {target_id}"
                raise CircularReferenceError(
                    f"Cannot add '{target_name}' as component: "
                    f"it would create a circular reference"
                )

    @staticmethod
    def _would_create_cycle(current_fg_id: int, target_fg_id: int, session) -> bool:
        """
        Check if adding target_fg_id as a component of current_fg_id would create a cycle.

        Transaction boundary: Inherits session from caller.
        Read-only BFS traversal within the caller's transaction scope.

        Uses breadth-first search to check if target_fg_id (or any of its descendants)
        contains current_fg_id.

        Args:
            current_fg_id: ID of the FinishedGood being updated
            target_fg_id: ID of the FinishedGood being added as a component
            session: Database session

        Returns:
            True if adding target would create a cycle, False otherwise
        """
        visited = set()
        queue = [target_fg_id]

        while queue:
            fg_id = queue.pop(0)
            if fg_id in visited:
                continue
            visited.add(fg_id)

            # Get all FinishedGood components of this fg
            compositions = session.query(Composition).filter_by(assembly_id=fg_id).all()
            for comp in compositions:
                if comp.finished_good_id is not None:
                    if comp.finished_good_id == current_fg_id:
                        return True  # Cycle detected!
                    queue.append(comp.finished_good_id)

        return False

    # Component Management

    @staticmethod
    def add_component(
        finished_good_id: int, component_type: str, component_id: int, quantity: int, **kwargs
    ) -> bool:
        """
        Add a component to an assembly.

        Transaction boundary: Multi-step operation (atomic).
        Atomicity guarantee: Either ALL steps succeed OR entire operation rolls back.
        Steps executed atomically:
            1. Validate assembly exists
            2. Validate component exists
            3. Check for circular references (if adding FinishedGood)
            4. Check component not already in assembly
            5. Create Composition record
            6. Recalculate assembly cost

        Args:
            finished_good_id: ID of the assembly
            component_type: "finished_unit" or "finished_good"
            component_id: ID of the component to add
            quantity: Quantity of the component
            **kwargs: Additional composition options (notes, sort_order)

        Returns:
            True if added successfully

        Raises:
            FinishedGoodNotFoundError: If assembly doesn't exist
            InvalidComponentError: If component doesn't exist
            CircularReferenceError: If would create circular reference
            ValidationError: If validation fails

        Performance:
            Must complete in <500ms per contract
        """
        try:
            if component_type not in ["finished_unit", "finished_good"]:
                raise ValidationError(["Component type must be 'finished_unit' or 'finished_good'"])

            if quantity <= 0:
                raise ValidationError(["Quantity must be positive"])

            with session_scope() as session:
                # Validate assembly exists
                assembly = (
                    session.query(FinishedGood).filter(FinishedGood.id == finished_good_id).first()
                )

                if not assembly:
                    raise FinishedGoodNotFoundError(f"FinishedGood ID {finished_good_id} not found")

                # Validate component exists
                if component_type == "finished_unit":
                    component = (
                        session.query(FinishedUnit).filter(FinishedUnit.id == component_id).first()
                    )
                    if not component:
                        raise InvalidComponentError(f"FinishedUnit ID {component_id} not found")

                elif component_type == "finished_good":
                    component = (
                        session.query(FinishedGood).filter(FinishedGood.id == component_id).first()
                    )
                    if not component:
                        raise InvalidComponentError(f"FinishedGood ID {component_id} not found")

                    # Check for circular references
                    if not FinishedGoodService.validate_no_circular_references(
                        finished_good_id, component_id, session
                    ):
                        raise CircularReferenceError(
                            f"Adding FinishedGood {component_id} to {finished_good_id} would create circular reference"
                        )

                # Check if component already exists in assembly
                existing_composition = (
                    session.query(Composition)
                    .filter(
                        Composition.assembly_id == finished_good_id,
                        getattr(Composition, f"{component_type}_id") == component_id,
                    )
                    .first()
                )

                if existing_composition:
                    raise ValidationError([f"Component already exists in assembly"])

                # Create composition
                composition_data = {
                    "assembly_id": finished_good_id,
                    "component_quantity": quantity,
                    "component_notes": kwargs.get("notes"),
                    "sort_order": kwargs.get("sort_order", 0),
                }

                if component_type == "finished_unit":
                    composition_data["finished_unit_id"] = component_id
                else:
                    composition_data["finished_good_id"] = component_id

                composition = Composition(**composition_data)
                session.add(composition)
                session.flush()

                # Update assembly total cost
                FinishedGoodService._recalculate_assembly_cost(finished_good_id, session)

                logger.info(
                    f"Added {component_type} {component_id} (qty: {quantity}) to assembly {finished_good_id}"
                )
                return True

        except SQLAlchemyError as e:
            logger.error(
                f"Database error adding component to FinishedGood ID {finished_good_id}: {e}"
            )
            raise DatabaseError(f"Failed to add component: {e}")

    @staticmethod
    def remove_component(finished_good_id: int, composition_id: int) -> bool:
        """
        Remove a component from an assembly.

        Transaction boundary: Multi-step operation (atomic).
        Atomicity guarantee: Either ALL steps succeed OR entire operation rolls back.
        Steps executed atomically:
            1. Validate assembly exists
            2. Find and delete Composition record
            3. Recalculate assembly cost

        Args:
            finished_good_id: ID of the assembly
            composition_id: ID of the composition record to remove

        Returns:
            True if removed successfully

        Performance:
            Must complete in <300ms per contract
        """
        try:
            with session_scope() as session:
                # Validate assembly exists
                assembly = (
                    session.query(FinishedGood).filter(FinishedGood.id == finished_good_id).first()
                )

                if not assembly:
                    raise FinishedGoodNotFoundError(f"FinishedGood ID {finished_good_id} not found")

                # Find and remove composition
                composition = (
                    session.query(Composition)
                    .filter(
                        Composition.id == composition_id,
                        Composition.assembly_id == finished_good_id,
                    )
                    .first()
                )

                if not composition:
                    logger.debug(
                        f"Composition ID {composition_id} not found in assembly {finished_good_id}"
                    )
                    return False

                session.delete(composition)
                session.flush()

                # Update assembly total cost
                FinishedGoodService._recalculate_assembly_cost(finished_good_id, session)

                logger.info(
                    f"Removed composition {composition_id} from assembly {finished_good_id}"
                )
                return True

        except SQLAlchemyError as e:
            logger.error(
                f"Database error removing component from FinishedGood ID {finished_good_id}: {e}"
            )
            raise DatabaseError(f"Failed to remove component: {e}")

    @staticmethod
    def update_component_quantity(composition_id: int, new_quantity: int) -> bool:
        """
        Update quantity of a component in an assembly.

        Transaction boundary: Multi-step operation (atomic).
        Atomicity guarantee: Either ALL steps succeed OR entire operation rolls back.
        Steps executed atomically:
            1. Validate quantity is positive
            2. Update Composition.component_quantity
            3. Recalculate assembly cost

        Args:
            composition_id: ID of the composition record
            new_quantity: New quantity value

        Returns:
            True if updated successfully

        Raises:
            ValidationError: If quantity invalid

        Performance:
            Must complete in <200ms per contract
        """
        try:
            if new_quantity <= 0:
                raise ValidationError(["Quantity must be positive"])

            with session_scope() as session:
                composition = (
                    session.query(Composition).filter(Composition.id == composition_id).first()
                )

                if not composition:
                    logger.debug(f"Composition ID {composition_id} not found")
                    return False

                composition.component_quantity = new_quantity
                session.flush()

                # Update assembly total cost
                FinishedGoodService._recalculate_assembly_cost(composition.assembly_id, session)

                logger.info(f"Updated composition {composition_id} quantity to {new_quantity}")
                return True

        except SQLAlchemyError as e:
            logger.error(f"Database error updating composition quantity {composition_id}: {e}")
            raise DatabaseError(f"Failed to update component quantity: {e}")

    # Hierarchy Operations

    @staticmethod
    def get_all_components(finished_good_id: int, flatten: bool = False) -> List[dict]:
        """
        Get complete component hierarchy for an assembly.

        Transaction boundary: Read-only operation.
        Queries Composition table with BFS hierarchy traversal.

        Args:
            finished_good_id: ID of the assembly
            flatten: If True, returns flattened list; if False, maintains hierarchy

        Returns:
            List of component information with quantities and relationships

        Performance:
            Must complete in <500ms for 5-level hierarchies per contract

        Algorithm:
            Uses iterative breadth-first search pattern
        """
        try:
            with get_db_session() as session:
                assembly = (
                    session.query(FinishedGood).filter(FinishedGood.id == finished_good_id).first()
                )

                if not assembly:
                    raise FinishedGoodNotFoundError(f"FinishedGood ID {finished_good_id} not found")

                if flatten:
                    return FinishedGoodService._get_flattened_components(finished_good_id, session)
                else:
                    return FinishedGoodService._get_hierarchical_components(
                        finished_good_id, session
                    )

        except SQLAlchemyError as e:
            logger.error(
                f"Database error getting components for FinishedGood ID {finished_good_id}: {e}"
            )
            raise DatabaseError(f"Failed to get components: {e}")

    @staticmethod
    def check_assembly_availability(finished_good_id: int, required_quantity: int = 1) -> dict:
        """
        Check if assembly can be created with available components.

        Transaction boundary: Read-only operation.
        Queries FinishedGood and component inventory.

        Args:
            finished_good_id: ID of the assembly
            required_quantity: Number of assemblies needed

        Returns:
            Dictionary with availability status and missing components

        Performance:
            Must complete in <500ms per contract
        """
        try:
            with get_db_session() as session:
                assembly = (
                    session.query(FinishedGood)
                    .options(selectinload(FinishedGood.components))
                    .filter(FinishedGood.id == finished_good_id)
                    .first()
                )

                if not assembly:
                    raise FinishedGoodNotFoundError(f"FinishedGood ID {finished_good_id} not found")

                availability_result = assembly.can_assemble(required_quantity)
                logger.debug(
                    f"Availability check for assembly {finished_good_id}: {availability_result['can_assemble']}"
                )
                return availability_result

        except SQLAlchemyError as e:
            logger.error(
                f"Database error checking availability for FinishedGood ID {finished_good_id}: {e}"
            )
            raise DatabaseError(f"Failed to check assembly availability: {e}")

    # Assembly Production

    @staticmethod
    def create_assembly_from_inventory(finished_good_id: int, quantity: int) -> bool:
        """
        Create assemblies by consuming available component inventory.

        Transaction boundary: Multi-step operation (atomic).
        Atomicity guarantee: Either ALL steps succeed OR entire operation rolls back.
        Steps executed atomically:
            1. Check component availability
            2. For each component: consume from inventory
            3. Update assembly inventory count

        Args:
            finished_good_id: ID of assembly to create
            quantity: Number of assemblies to create

        Returns:
            True if successful

        Raises:
            InsufficientInventoryError: If components unavailable

        Performance:
            Must complete in <1s per contract
        """
        try:
            with session_scope() as session:
                # Check availability first
                availability = FinishedGoodService.check_assembly_availability(
                    finished_good_id, quantity
                )

                if not availability["can_assemble"]:
                    missing_components = availability.get("missing_components", [])
                    raise InsufficientInventoryError(
                        f"Cannot create {quantity} assemblies: {missing_components}"
                    )

                # Consume component inventory
                assembly = (
                    session.query(FinishedGood)
                    .options(selectinload(FinishedGood.components))
                    .filter(FinishedGood.id == finished_good_id)
                    .first()
                )

                for composition in assembly.components:
                    required_qty = composition.component_quantity * quantity

                    if composition.finished_unit_component:
                        # Update FinishedUnit inventory
                        finished_unit_service.update_inventory(
                            composition.finished_unit_id, -required_qty
                        )
                    elif composition.finished_good_component:
                        # Update FinishedGood inventory
                        component_assembly = composition.finished_good_component
                        component_assembly.update_inventory(-required_qty)

                # Increase assembly inventory
                assembly.update_inventory(quantity)
                session.flush()

                logger.info(f"Created {quantity} assemblies of FinishedGood {finished_good_id}")
                return True

        except SQLAlchemyError as e:
            logger.error(f"Database error creating assemblies: {e}")
            raise DatabaseError(f"Failed to create assemblies: {e}")

    @staticmethod
    def disassemble_into_components(finished_good_id: int, quantity: int) -> bool:
        """
        Break down assemblies back into component inventory.

        Transaction boundary: Multi-step operation (atomic).
        Atomicity guarantee: Either ALL steps succeed OR entire operation rolls back.
        Steps executed atomically:
            1. Validate sufficient assembly inventory
            2. For each component: restore to inventory
            3. Decrease assembly inventory count

        Args:
            finished_good_id: ID of assembly to disassemble
            quantity: Number of assemblies to break down

        Returns:
            True if successful

        Performance:
            Must complete in <1s per contract
        """
        try:
            with session_scope() as session:
                assembly = (
                    session.query(FinishedGood)
                    .options(selectinload(FinishedGood.components))
                    .filter(FinishedGood.id == finished_good_id)
                    .first()
                )

                if not assembly:
                    raise FinishedGoodNotFoundError(f"FinishedGood ID {finished_good_id} not found")

                if assembly.inventory_count < quantity:
                    raise InsufficientInventoryError(
                        f"Only {assembly.inventory_count} assemblies available, cannot disassemble {quantity}"
                    )

                # Restore component inventory
                for composition in assembly.components:
                    restored_qty = composition.component_quantity * quantity

                    if composition.finished_unit_component:
                        # Update FinishedUnit inventory
                        finished_unit_service.update_inventory(
                            composition.finished_unit_id, restored_qty
                        )
                    elif composition.finished_good_component:
                        # Update FinishedGood inventory
                        component_assembly = composition.finished_good_component
                        component_assembly.update_inventory(restored_qty)

                # Decrease assembly inventory
                assembly.update_inventory(-quantity)
                session.flush()

                logger.info(
                    f"Disassembled {quantity} assemblies of FinishedGood {finished_good_id}"
                )
                return True

        except SQLAlchemyError as e:
            logger.error(f"Database error disassembling: {e}")
            raise DatabaseError(f"Failed to disassemble: {e}")

    @staticmethod
    def validate_no_circular_references(
        finished_good_id: int, new_component_id: int, session: Optional[Session] = None
    ) -> bool:
        """
        Ensure adding a component won't create circular references.

        Transaction boundary: Read-only operation.
        Uses BFS traversal to detect cycles in component graph.

        Args:
            finished_good_id: ID of the assembly
            new_component_id: ID of component being added (if it's a FinishedGood)

        Returns:
            True if safe to add, False if would create cycle

        Performance:
            Must complete in <200ms per contract
        """
        try:
            use_session = session or get_db_session()

            with use_session if session else use_session() as s:
                # Use breadth-first search to detect cycles
                visited = set()
                queue = deque([new_component_id])

                while queue:
                    current_id = queue.popleft()

                    if current_id in visited:
                        continue

                    if current_id == finished_good_id:
                        return False  # Circular reference detected

                    visited.add(current_id)

                    # Get components of current assembly
                    components = (
                        s.query(Composition).filter(Composition.assembly_id == current_id).all()
                    )

                    for comp in components:
                        if comp.finished_good_id:  # Only check FinishedGood components
                            queue.append(comp.finished_good_id)

                return True  # No circular reference

        except SQLAlchemyError as e:
            logger.error(f"Database error validating circular references: {e}")
            raise DatabaseError(f"Failed to validate circular references: {e}")

    # Query Operations

    @staticmethod
    def search_finished_goods(query: str) -> List[FinishedGood]:
        """
        Search assemblies by name or description.

        Transaction boundary: Read-only operation.
        Queries FinishedGood with text search filters.

        Args:
            query: String search term

        Returns:
            List of matching FinishedGood instances

        Performance:
            Must complete in <300ms per contract
        """
        try:
            if not query or not query.strip():
                return []

            search_term = f"%{query.strip().lower()}%"

            with get_db_session() as session:
                assemblies = (
                    session.query(FinishedGood)
                    .options(selectinload(FinishedGood.components))
                    .filter(
                        or_(
                            FinishedGood.display_name.ilike(search_term),
                            FinishedGood.description.ilike(search_term),
                            FinishedGood.notes.ilike(search_term),
                        )
                    )
                    .order_by(FinishedGood.display_name)
                    .all()
                )

                logger.debug(f"Search for '{query}' returned {len(assemblies)} FinishedGoods")
                return assemblies

        except SQLAlchemyError as e:
            logger.error(f"Database error searching FinishedGoods with query '{query}': {e}")
            raise DatabaseError(f"Failed to search FinishedGoods: {e}")

    @staticmethod
    def get_assemblies_by_type(assembly_type: AssemblyType) -> List[FinishedGood]:
        """
        Get all assemblies of a specific type.

        Transaction boundary: Read-only operation.
        Queries FinishedGood filtered by assembly_type.

        Args:
            assembly_type: AssemblyType enum value

        Returns:
            List of FinishedGood instances

        Performance:
            Must complete in <200ms per contract
        """
        try:
            with get_db_session() as session:
                assemblies = (
                    session.query(FinishedGood)
                    .options(selectinload(FinishedGood.components))
                    .filter(FinishedGood.assembly_type == assembly_type)
                    .order_by(FinishedGood.display_name)
                    .all()
                )

                logger.debug(f"Retrieved {len(assemblies)} FinishedGoods of type {assembly_type}")
                return assemblies

        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving FinishedGoods by type {assembly_type}: {e}")
            raise DatabaseError(f"Failed to retrieve FinishedGoods by type: {e}")

    # Utility Methods

    @staticmethod
    def _generate_slug(display_name: str) -> str:
        """Generate URL-safe slug from display name.

        Transaction boundary: Pure computation (no database access).
        """
        if not display_name:
            return "unknown-assembly"

        # Normalize unicode characters
        slug = unicodedata.normalize("NFKD", display_name)

        # Convert to lowercase and replace spaces/punctuation with hyphens
        slug = re.sub(r"[^\w\s-]", "", slug).strip().lower()
        slug = re.sub(r"[\s_-]+", "-", slug)

        # Remove leading/trailing hyphens
        slug = slug.strip("-")

        # Ensure not empty
        if not slug:
            return "unknown-assembly"

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
        base_slug = FinishedGoodService._generate_slug(display_name)

        # Check if base slug is already unique
        query = session.query(FinishedGood).filter(FinishedGood.slug == base_slug)
        if exclude_id:
            query = query.filter(FinishedGood.id != exclude_id)

        if not query.first():
            return base_slug

        # Add numeric suffix for uniqueness
        counter = 2
        while True:
            candidate_slug = f"{base_slug}-{counter}"
            query = session.query(FinishedGood).filter(FinishedGood.slug == candidate_slug)
            if exclude_id:
                query = query.filter(FinishedGood.id != exclude_id)

            if not query.first():
                return candidate_slug

            counter += 1

            # Prevent infinite loop
            if counter > 1000:
                raise ValidationError("Unable to generate unique slug")

    @staticmethod
    def _validate_components(components: List[dict], session: Session) -> None:
        """
        Validate component data structure and references.

        Transaction boundary: Inherits session from caller.
        Read-only validation within the caller's transaction scope.

        Supports both legacy format (component_type/component_id) and new format (type/id).

        Component data structure (new format):
            {"type": "finished_unit"|"material_unit"|"finished_good",
             "id": int, "quantity": int, "notes": str|None, "sort_order": int}

        Args:
            components: List of component specification dictionaries
            session: Database session for reference validation

        Raises:
            ValidationError: If component data structure is invalid
            InvalidComponentError: If referenced component doesn't exist
        """
        if not components:
            return

        valid_types = {"finished_unit", "material_unit", "finished_good"}

        for i, comp in enumerate(components):
            # Support both legacy (component_type/component_id) and new (type/id) keys
            comp_type = comp.get("type") or comp.get("component_type")
            comp_id = comp.get("id") or comp.get("component_id")

            # Check required fields
            if not comp_type:
                raise ValidationError([f"Component {i}: missing 'type' field"])
            if comp_id is None:
                raise ValidationError([f"Component {i}: missing 'id' field"])

            if comp_type not in valid_types:
                raise ValidationError(
                    [f"Component {i}: invalid type '{comp_type}'. "
                     f"Must be one of: {', '.join(valid_types)}"]
                )

            # Validate quantity if present
            quantity = comp.get("quantity", 1)
            if quantity <= 0:
                raise ValidationError([f"Component {i}: quantity must be positive"])

            # Validate reference exists
            FinishedGoodService._validate_component_reference(comp_type, comp_id, session, i)

    @staticmethod
    def _validate_component_reference(
        comp_type: str, comp_id: int, session: Session, index: int
    ) -> None:
        """
        Validate that the referenced component exists in the database.

        Transaction boundary: Inherits session from caller.
        Read-only query within the caller's transaction scope.

        Args:
            comp_type: Component type ("finished_unit", "material_unit", "finished_good")
            comp_id: Component ID
            session: Database session
            index: Component index for error messages

        Raises:
            InvalidComponentError: If referenced component doesn't exist
        """
        if comp_type == "finished_unit":
            exists = session.query(FinishedUnit).filter_by(id=comp_id).first()
            if not exists:
                raise InvalidComponentError(f"Component {index}: FinishedUnit {comp_id} not found")
        elif comp_type == "material_unit":
            exists = session.query(MaterialUnit).filter_by(id=comp_id).first()
            if not exists:
                raise InvalidComponentError(f"Component {index}: MaterialUnit {comp_id} not found")
        elif comp_type == "finished_good":
            exists = session.query(FinishedGood).filter_by(id=comp_id).first()
            if not exists:
                raise InvalidComponentError(f"Component {index}: FinishedGood {comp_id} not found")

    @staticmethod
    def _create_composition(
        assembly_id: int, component_spec: dict, session: Session
    ) -> Composition:
        """
        Create composition from component specification using factory methods.

        Transaction boundary: Pure computation (no database access).
        Creates Composition object but does not persist to database.

        Supports both legacy format (component_type/component_id) and new format (type/id).

        Args:
            assembly_id: Parent FinishedGood ID
            component_spec: Component specification dictionary
            session: Database session (for future use)

        Returns:
            New Composition instance (not yet added to session)

        Raises:
            ValueError: If component type is unknown
        """
        # Support both legacy (component_type/component_id) and new (type/id) keys
        comp_type = component_spec.get("type") or component_spec.get("component_type")
        comp_id = component_spec.get("id") or component_spec.get("component_id")
        quantity = component_spec.get("quantity", 1)
        notes = component_spec.get("notes") or component_spec.get("component_notes")
        sort_order = component_spec.get("sort_order", 0)

        if comp_type == "finished_unit":
            return Composition.create_unit_composition(
                assembly_id=assembly_id,
                finished_unit_id=comp_id,
                quantity=quantity,
                notes=notes,
                sort_order=sort_order,
            )
        elif comp_type == "material_unit":
            return Composition.create_material_unit_composition(
                assembly_id=assembly_id,
                material_unit_id=comp_id,
                quantity=quantity,
                notes=notes,
                sort_order=sort_order,
            )
        elif comp_type == "finished_good":
            return Composition.create_assembly_composition(
                assembly_id=assembly_id,
                finished_good_id=comp_id,
                quantity=quantity,
                notes=notes,
                sort_order=sort_order,
            )
        else:
            raise ValueError(f"Unknown component type: {comp_type}")

    @staticmethod
    def _get_flattened_components(finished_good_id: int, session: Session) -> List[dict]:
        """
        Get all components in a flattened list format.

        Transaction boundary: Inherits session from caller.
        Read-only BFS traversal within the caller's transaction scope.

        Uses breadth-first traversal to flatten the hierarchy and aggregate
        quantities for duplicate components.
        """
        components = {}  # component_key -> total_quantity
        component_details = {}  # component_key -> details
        queue = deque([(finished_good_id, 1)])  # (assembly_id, multiplier)
        visited_assemblies = set()

        while queue:
            current_assembly_id, multiplier = queue.popleft()

            # Prevent circular references in traversal
            if current_assembly_id in visited_assemblies:
                continue
            visited_assemblies.add(current_assembly_id)

            # Get direct components of current assembly
            compositions = (
                session.query(Composition)
                .options(
                    selectinload(Composition.finished_unit_component),
                    selectinload(Composition.finished_good_component),
                )
                .filter(Composition.assembly_id == current_assembly_id)
                .all()
            )

            for comp in compositions:
                effective_quantity = comp.component_quantity * multiplier

                if comp.finished_unit_component:
                    # FinishedUnit component
                    unit = comp.finished_unit_component
                    key = f"finished_unit_{unit.id}"

                    if key in components:
                        components[key] += effective_quantity
                    else:
                        components[key] = effective_quantity
                        component_details[key] = {
                            "component_type": "finished_unit",
                            "component_id": unit.id,
                            "display_name": unit.display_name,
                            "inventory_count": unit.inventory_count,
                            "slug": unit.slug,
                        }

                elif comp.finished_good_component:
                    # FinishedGood component - add to queue for further expansion
                    subassembly = comp.finished_good_component
                    key = f"finished_good_{subassembly.id}"

                    if key in components:
                        components[key] += effective_quantity
                    else:
                        components[key] = effective_quantity
                        component_details[key] = {
                            "component_type": "finished_good",
                            "component_id": subassembly.id,
                            "display_name": subassembly.display_name,
                            "inventory_count": subassembly.inventory_count,
                            "slug": subassembly.slug,
                            "assembly_type": subassembly.assembly_type.value,
                        }

                    # Add to queue for expansion
                    queue.append((subassembly.id, effective_quantity))

        # Convert to final format
        result = []
        for key, total_quantity in components.items():
            detail = component_details[key].copy()
            detail["total_quantity"] = total_quantity
            result.append(detail)

        # Sort by component type and name
        result.sort(key=lambda x: (x["component_type"], x["display_name"]))
        return result

    @staticmethod
    def _get_hierarchical_components(finished_good_id: int, session: Session) -> List[dict]:
        """
        Get components maintaining hierarchical structure.

        Transaction boundary: Inherits session from caller.
        Read-only recursive queries within the caller's transaction scope.

        Returns nested structure showing assembly composition levels.
        """

        def get_assembly_components(assembly_id: int, level: int = 0) -> List[dict]:
            if level > 10:  # Prevent infinite recursion
                logger.warning(f"Maximum hierarchy depth reached for assembly {assembly_id}")
                return []

            compositions = (
                session.query(Composition)
                .options(
                    selectinload(Composition.finished_unit_component),
                    selectinload(Composition.finished_good_component),
                )
                .filter(Composition.assembly_id == assembly_id)
                .order_by(Composition.sort_order, Composition.id)
                .all()
            )

            components = []
            for comp in compositions:
                if comp.finished_unit_component:
                    # FinishedUnit component
                    unit = comp.finished_unit_component
                    component_data = {
                        "composition_id": comp.id,
                        "component_type": "finished_unit",
                        "component_id": unit.id,
                        "display_name": unit.display_name,
                        "slug": unit.slug,
                        "quantity": comp.component_quantity,
                        "inventory_count": unit.inventory_count,
                        "component_notes": comp.component_notes,
                        "sort_order": comp.sort_order,
                        "level": level,
                        "subcomponents": [],  # FinishedUnits have no subcomponents
                    }

                elif comp.finished_good_component:
                    # FinishedGood component
                    subassembly = comp.finished_good_component
                    component_data = {
                        "composition_id": comp.id,
                        "component_type": "finished_good",
                        "component_id": subassembly.id,
                        "display_name": subassembly.display_name,
                        "slug": subassembly.slug,
                        "quantity": comp.component_quantity,
                        "inventory_count": subassembly.inventory_count,
                        "assembly_type": subassembly.assembly_type.value,
                        "component_notes": comp.component_notes,
                        "sort_order": comp.sort_order,
                        "level": level,
                        "subcomponents": get_assembly_components(subassembly.id, level + 1),
                    }

                components.append(component_data)

            return components

        return get_assembly_components(finished_good_id)

    # Assembly Type-Specific Business Logic

    @staticmethod
    def validate_assembly_business_rules(assembly_id: int) -> dict:
        """
        Validate complete business rules for an assembly based on its type.

        Transaction boundary: Read-only operation.
        Queries FinishedGood and validates against business rules.

        Args:
            assembly_id: ID of the assembly to validate

        Returns:
            Dictionary with validation results and any issues found

        Performance:
            Must complete in <300ms per contract
        """
        try:
            with get_db_session() as session:
                assembly = (
                    session.query(FinishedGood)
                    .options(selectinload(FinishedGood.components))
                    .filter(FinishedGood.id == assembly_id)
                    .first()
                )

                if not assembly:
                    raise FinishedGoodNotFoundError(f"FinishedGood ID {assembly_id} not found")

                component_count = len(assembly.components)

                # Cost parameter removed in F045 - pass 0 for backward compatibility
                is_valid, errors = validate_assembly_type_business_rules(
                    assembly.assembly_type, component_count, Decimal("0.0000")
                )

                result = {
                    "assembly_id": assembly_id,
                    "assembly_type": assembly.assembly_type.value,
                    "assembly_type_name": assembly.assembly_type.get_display_name(),
                    "is_valid": is_valid,
                    "errors": errors,
                    "component_count": component_count,
                    "business_rules": assembly.assembly_type.get_business_rules(),
                    "component_limits": assembly.assembly_type.get_component_limits(),
                    "validated_at": utc_now().isoformat(),
                }

                logger.debug(f"Business rule validation for assembly {assembly_id}: {is_valid}")
                return result

        except SQLAlchemyError as e:
            logger.error(f"Database error validating assembly business rules: {e}")
            raise DatabaseError(f"Failed to validate assembly business rules: {e}")

    @staticmethod
    def get_assembly_type_recommendations(assembly_type: AssemblyType) -> dict:
        """
        Get recommendations and guidelines for a specific assembly type.

        Transaction boundary: Pure computation (no database access).
        Retrieves metadata from AssemblyType enum.

        Args:
            assembly_type: AssemblyType enum value

        Returns:
            Dictionary with assembly type recommendations and metadata
        """
        try:
            recommendations = {
                "assembly_type": assembly_type.value,
                "display_name": assembly_type.get_display_name(),
                "description": assembly_type.get_description(),
                "component_limits": assembly_type.get_component_limits(),
                "business_rules": assembly_type.get_business_rules(),
                "is_seasonal": assembly_type.is_seasonal(),
                "packaging_priority": assembly_type.get_packaging_priority(),
                "requires_special_handling": assembly_type.requires_special_handling(),
                "pricing_markup": float(assembly_type.get_pricing_markup()),
                "packaging_notes": assembly_type.get_business_rules().get("packaging_notes", ""),
            }

            logger.debug(f"Retrieved recommendations for assembly type {assembly_type.value}")
            return recommendations

        except Exception as e:
            logger.error(f"Error getting assembly type recommendations: {e}")
            raise ServiceError(f"Failed to get assembly type recommendations: {e}")

    @staticmethod
    def get_assemblies_requiring_attention() -> List[dict]:
        """
        Get assemblies that require attention based on business rules.

        Transaction boundary: Read-only operation.
        Queries all FinishedGoods and validates business rules.

        Returns:
            List of assemblies with issues or recommendations

        Performance:
            Must complete in <1s per contract
        """
        try:
            with get_db_session() as session:
                assemblies = (
                    session.query(FinishedGood).options(selectinload(FinishedGood.components)).all()
                )

                attention_required = []

                for assembly in assemblies:
                    issues = []

                    # Check business rule compliance (cost parameter removed in F045)
                    component_count = len(assembly.components)
                    is_valid, errors = validate_assembly_type_business_rules(
                        assembly.assembly_type, component_count, Decimal("0.0000")
                    )

                    if not is_valid:
                        issues.extend(errors)

                    # Check seasonal assemblies
                    if assembly.assembly_type.is_seasonal():
                        issues.append("Seasonal assembly - verify availability and timing")

                    # Check special handling requirements
                    if assembly.assembly_type.requires_special_handling():
                        issues.append("Requires special handling - review packaging instructions")

                    if issues:
                        attention_required.append(
                            {
                                "assembly_id": assembly.id,
                                "display_name": assembly.display_name,
                                "assembly_type": assembly.assembly_type.value,
                                "assembly_type_name": assembly.assembly_type.get_display_name(),
                                "issues": issues,
                                "component_count": component_count,
                                "last_updated": (
                                    assembly.updated_at.isoformat() if assembly.updated_at else None
                                ),
                            }
                        )

                logger.debug(f"Found {len(attention_required)} assemblies requiring attention")
                return attention_required

        except SQLAlchemyError as e:
            logger.error(f"Database error getting assemblies requiring attention: {e}")
            raise DatabaseError(f"Failed to get assemblies requiring attention: {e}")


# Module-level convenience functions for backward compatibility


def get_finished_good_by_id(finished_good_id: int) -> FinishedGood:
    """Retrieve a specific FinishedGood by ID.

    Raises:
        FinishedGoodNotFoundById: If finished good doesn't exist
    """
    return FinishedGoodService.get_finished_good_by_id(finished_good_id)


def get_finished_good_by_slug(slug: str) -> FinishedGood:
    """Retrieve a specific FinishedGood by slug.

    Raises:
        FinishedGoodNotFoundBySlug: If finished good doesn't exist
    """
    return FinishedGoodService.get_finished_good_by_slug(slug)


def get_all_finished_goods() -> List[FinishedGood]:
    """Retrieve all FinishedGoods."""
    return FinishedGoodService.get_all_finished_goods()


def create_finished_good(
    display_name: str,
    assembly_type: AssemblyType = AssemblyType.CUSTOM_ORDER,
    components: Optional[List[Dict]] = None,
    session=None,
    **kwargs
) -> FinishedGood:
    """Create a new FinishedGood assembly with optional components."""
    return FinishedGoodService.create_finished_good(
        display_name, assembly_type, components=components, session=session, **kwargs
    )


def add_component(
    finished_good_id: int, component_type: str, component_id: int, quantity: int
) -> bool:
    """Add a component to an assembly."""
    return FinishedGoodService.add_component(
        finished_good_id, component_type, component_id, quantity
    )


def search_finished_goods(query: str) -> List[FinishedGood]:
    """Search assemblies by name or description."""
    return FinishedGoodService.search_finished_goods(query)


def get_assemblies_by_type(assembly_type: AssemblyType) -> List[FinishedGood]:
    """Get all assemblies of a specific type."""
    return FinishedGoodService.get_assemblies_by_type(assembly_type)


def update_finished_good(
    finished_good_id: int,
    display_name: Optional[str] = None,
    assembly_type: Optional[AssemblyType] = None,
    components: Optional[List[Dict]] = None,
    packaging_instructions: Optional[str] = None,
    notes: Optional[str] = None,
    session=None,
    **updates
) -> FinishedGood:
    """Update a FinishedGood assembly with optional component replacement."""
    return FinishedGoodService.update_finished_good(
        finished_good_id,
        display_name=display_name,
        assembly_type=assembly_type,
        components=components,
        packaging_instructions=packaging_instructions,
        notes=notes,
        session=session,
        **updates
    )


def delete_finished_good(finished_good_id: int, session=None) -> bool:
    """Delete a FinishedGood with safety checks for references."""
    return FinishedGoodService.delete_finished_good(finished_good_id, session=session)


# =============================================================================
# Feature 064: FinishedGoodSnapshot Service Functions
# =============================================================================

import json
from src.models import FinishedGoodSnapshot, PlanningSnapshot
from .finished_unit_service import create_finished_unit_snapshot
from .material_unit_service import create_material_unit_snapshot


# Snapshot-specific exceptions
class SnapshotCreationError(ServiceError):
    """Raised when snapshot creation fails."""

    pass


class SnapshotCircularReferenceError(ServiceError):
    """Raised when circular reference detected in FinishedGood hierarchy during snapshot.

    Attributes:
        finished_good_id: The ID that caused the circular reference
        path: List of IDs showing the reference chain
    """

    def __init__(self, finished_good_id: int, path: list):
        self.finished_good_id = finished_good_id
        self.path = path
        path_str = " -> ".join(str(id) for id in path)
        super().__init__(
            f"Circular reference detected: FinishedGood {finished_good_id} "
            f"already in hierarchy path: {path_str}"
        )


class MaxDepthExceededError(ServiceError):
    """Raised when FinishedGood nesting exceeds maximum depth.

    Attributes:
        depth: Current depth when limit was hit
        max_depth: The configured maximum depth (10)
    """

    def __init__(self, depth: int, max_depth: int = 10):
        self.depth = depth
        self.max_depth = max_depth
        super().__init__(
            f"Maximum nesting depth exceeded: {depth} levels (max: {max_depth})"
        )


MAX_NESTING_DEPTH = 10


def create_finished_good_snapshot(
    finished_good_id: int,
    planning_snapshot_id: int = None,
    assembly_run_id: int = None,
    session: Optional[Session] = None,
    _visited_ids: set = None,
    _depth: int = 0,
) -> dict:
    """
    Create immutable snapshot of FinishedGood definition with all components.

    Transaction boundary: Multi-step operation (atomic).
    Atomicity guarantee: Either ALL steps succeed OR entire operation rolls back.
    Steps executed atomically:
        1. Load FinishedGood with components
        2. For each component: create FinishedUnit/MaterialUnit/FinishedGood snapshot
        3. Create FinishedGoodSnapshot record with component references

    CRITICAL: Session parameter is passed to all nested snapshot calls to ensure
    atomicity across the entire component hierarchy.

    Recursively creates snapshots for all FinishedUnit, MaterialUnit,
    and nested FinishedGood components. All snapshots are created in the
    same transaction for atomicity.

    Args:
        finished_good_id: Source FinishedGood ID
        planning_snapshot_id: Optional planning context
        assembly_run_id: Optional assembly context
        session: Optional session for transaction sharing
        _visited_ids: Internal - tracked IDs for circular reference detection
        _depth: Internal - current recursion depth

    Returns:
        dict with snapshot id and definition_data (including component snapshot IDs)

    Raises:
        SnapshotCreationError: If FinishedGood not found or creation fails
        SnapshotCircularReferenceError: If circular reference detected in hierarchy
        MaxDepthExceededError: If nesting depth exceeds 10 levels
    """
    # Initialize visited set for top-level call
    if _visited_ids is None:
        _visited_ids = set()

    if session is not None:
        return _create_finished_good_snapshot_impl(
            finished_good_id,
            planning_snapshot_id,
            assembly_run_id,
            session,
            _visited_ids,
            _depth,
        )

    try:
        with session_scope() as session:
            return _create_finished_good_snapshot_impl(
                finished_good_id,
                planning_snapshot_id,
                assembly_run_id,
                session,
                _visited_ids,
                _depth,
            )
    except SQLAlchemyError as e:
        raise SnapshotCreationError(f"Database error creating snapshot: {e}")


def _create_finished_good_snapshot_impl(
    finished_good_id: int,
    planning_snapshot_id: int,
    assembly_run_id: int,
    session: Session,
    visited_ids: set,
    depth: int,
) -> dict:
    """Internal implementation of snapshot creation.

    Transaction boundary: Inherits session from caller.
    Multi-step recursive operation within the caller's transaction scope.
    """
    # Check max depth FIRST
    if depth > MAX_NESTING_DEPTH:
        raise MaxDepthExceededError(depth, MAX_NESTING_DEPTH)

    # Check circular reference
    if finished_good_id in visited_ids:
        raise SnapshotCircularReferenceError(
            finished_good_id, list(visited_ids) + [finished_good_id]
        )

    # Add to visited set BEFORE processing components
    visited_ids.add(finished_good_id)

    # Load FinishedGood with components
    fg = session.query(FinishedGood).filter_by(id=finished_good_id).first()
    if not fg:
        raise SnapshotCreationError(f"FinishedGood {finished_good_id} not found")

    # Process components and create snapshots
    components_data = []
    for composition in fg.components:
        component_data = _snapshot_component(
            composition,
            planning_snapshot_id,
            assembly_run_id,
            session,
            visited_ids,
            depth,
        )
        if component_data:  # Skip packaging_product (returns None)
            components_data.append(component_data)

    # Sort components by sort_order
    components_data.sort(key=lambda x: x.get("sort_order", 999))

    # Build definition_data JSON
    definition_data = {
        "slug": fg.slug,
        "display_name": fg.display_name,
        "description": fg.description,
        "assembly_type": fg.assembly_type.value if fg.assembly_type else None,
        "packaging_instructions": fg.packaging_instructions,
        "notes": fg.notes,
        "components": components_data,
    }

    # Create snapshot
    snapshot = FinishedGoodSnapshot(
        finished_good_id=finished_good_id,
        planning_snapshot_id=planning_snapshot_id,
        assembly_run_id=assembly_run_id,
        definition_data=json.dumps(definition_data),
        is_backfilled=False,
    )

    session.add(snapshot)
    session.flush()

    return {
        "id": snapshot.id,
        "finished_good_id": snapshot.finished_good_id,
        "planning_snapshot_id": snapshot.planning_snapshot_id,
        "assembly_run_id": snapshot.assembly_run_id,
        "snapshot_date": snapshot.snapshot_date.isoformat(),
        "definition_data": definition_data,
        "is_backfilled": snapshot.is_backfilled,
    }


def _snapshot_component(
    composition,
    planning_snapshot_id: int,
    assembly_run_id: int,
    session: Session,
    visited_ids: set,
    depth: int,
) -> Optional[dict]:
    """
    Create snapshot for a single component based on its type.

    Transaction boundary: Inherits session from caller.
    Delegates to type-specific snapshot functions within caller's transaction.

    Args:
        composition: Composition model instance
        planning_snapshot_id: Planning context
        assembly_run_id: Assembly context
        session: Database session
        visited_ids: Set of visited FinishedGood IDs
        depth: Current recursion depth

    Returns:
        Component data dict with snapshot_id, or None if skipped
    """
    base_data = {
        "component_quantity": composition.component_quantity,
        "component_notes": composition.component_notes,
        "sort_order": composition.sort_order,
        "is_generic": composition.is_generic,
    }

    if composition.finished_unit_id:
        # FinishedUnit component - create snapshot
        fu_snapshot = create_finished_unit_snapshot(
            finished_unit_id=composition.finished_unit_id,
            planning_snapshot_id=planning_snapshot_id,
            assembly_run_id=assembly_run_id,
            session=session,
        )
        return {
            **base_data,
            "component_type": "finished_unit",
            "snapshot_id": fu_snapshot["id"],
            "original_id": composition.finished_unit_id,
            "component_slug": fu_snapshot["definition_data"]["slug"],
            "component_name": fu_snapshot["definition_data"]["display_name"],
        }

    elif composition.finished_good_id:
        # Nested FinishedGood - recurse
        fg_snapshot = _create_finished_good_snapshot_impl(
            finished_good_id=composition.finished_good_id,
            planning_snapshot_id=planning_snapshot_id,
            assembly_run_id=assembly_run_id,
            session=session,
            visited_ids=visited_ids,
            depth=depth + 1,
        )
        return {
            **base_data,
            "component_type": "finished_good",
            "snapshot_id": fg_snapshot["id"],
            "original_id": composition.finished_good_id,
            "component_slug": fg_snapshot["definition_data"]["slug"],
            "component_name": fg_snapshot["definition_data"]["display_name"],
        }

    elif composition.material_unit_id:
        # MaterialUnit component - create snapshot
        mu_snapshot = create_material_unit_snapshot(
            material_unit_id=composition.material_unit_id,
            planning_snapshot_id=planning_snapshot_id,
            assembly_run_id=assembly_run_id,
            session=session,
        )
        return {
            **base_data,
            "component_type": "material_unit",
            "snapshot_id": mu_snapshot["id"],
            "original_id": composition.material_unit_id,
            "component_slug": mu_snapshot["definition_data"]["slug"],
            "component_name": mu_snapshot["definition_data"]["name"],
        }

    elif composition.packaging_product_id:
        # Packaging product - out of scope, skip
        return None

    else:
        # Unknown component type
        return None


def get_finished_good_snapshot(
    snapshot_id: int, session: Optional[Session] = None
) -> Optional[dict]:
    """Get a FinishedGoodSnapshot by its ID.

    Transaction boundary: Read-only operation.
    Queries FinishedGoodSnapshot by ID.
    """
    if session is not None:
        return _get_finished_good_snapshot_impl(snapshot_id, session)

    with session_scope() as session:
        return _get_finished_good_snapshot_impl(snapshot_id, session)


def _get_finished_good_snapshot_impl(
    snapshot_id: int, session: Session
) -> Optional[dict]:
    """Internal implementation of get snapshot.

    Transaction boundary: Inherits session from caller.
    Read-only query within the caller's transaction scope.
    """
    snapshot = session.query(FinishedGoodSnapshot).filter_by(id=snapshot_id).first()

    if not snapshot:
        return None

    return {
        "id": snapshot.id,
        "finished_good_id": snapshot.finished_good_id,
        "planning_snapshot_id": snapshot.planning_snapshot_id,
        "assembly_run_id": snapshot.assembly_run_id,
        "snapshot_date": snapshot.snapshot_date.isoformat(),
        "definition_data": snapshot.get_definition_data(),
        "is_backfilled": snapshot.is_backfilled,
    }


def get_finished_good_snapshots_by_planning_id(
    planning_snapshot_id: int, session: Optional[Session] = None
) -> list:
    """Get all FinishedGoodSnapshots for a planning snapshot.

    Transaction boundary: Read-only operation.
    Queries FinishedGoodSnapshot by planning_snapshot_id.
    """
    if session is not None:
        return _get_fg_snapshots_by_planning_impl(planning_snapshot_id, session)

    with session_scope() as session:
        return _get_fg_snapshots_by_planning_impl(planning_snapshot_id, session)


def _get_fg_snapshots_by_planning_impl(
    planning_snapshot_id: int, session: Session
) -> list:
    """Internal implementation of get snapshots by planning ID.

    Transaction boundary: Inherits session from caller.
    Read-only query within the caller's transaction scope.
    """
    snapshots = (
        session.query(FinishedGoodSnapshot)
        .filter_by(planning_snapshot_id=planning_snapshot_id)
        .all()
    )

    return [
        {
            "id": s.id,
            "finished_good_id": s.finished_good_id,
            "planning_snapshot_id": s.planning_snapshot_id,
            "assembly_run_id": s.assembly_run_id,
            "snapshot_date": s.snapshot_date.isoformat(),
            "definition_data": s.get_definition_data(),
            "is_backfilled": s.is_backfilled,
        }
        for s in snapshots
    ]
