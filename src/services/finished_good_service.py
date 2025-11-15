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
from collections import deque

from sqlalchemy import and_, or_, text
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from ..database import get_db_session, session_scope
from ..models import FinishedGood, FinishedUnit, Composition, AssemblyType
from ..models.assembly_type import (
    validate_assembly_type_business_rules,
    calculate_packaging_cost,
    get_suggested_retail_price
)
from ..services.finished_unit_service import FinishedUnitService
from .exceptions import (
    ServiceError,
    ValidationError,
    DatabaseError
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
    def get_finished_good_by_id(finished_good_id: int) -> Optional[FinishedGood]:
        """
        Retrieve a specific FinishedGood assembly by ID.

        Args:
            finished_good_id: Integer ID of the FinishedGood

        Returns:
            FinishedGood instance or None if not found

        Performance:
            Must complete in <50ms per contract
        """
        try:
            with get_db_session() as session:
                finished_good = session.query(FinishedGood)\
                    .options(selectinload(FinishedGood.components))\
                    .filter(FinishedGood.id == finished_good_id)\
                    .first()

                if finished_good:
                    logger.debug(f"Retrieved FinishedGood by ID {finished_good_id}: {finished_good.display_name}")
                else:
                    logger.debug(f"FinishedGood not found for ID {finished_good_id}")

                return finished_good

        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving FinishedGood ID {finished_good_id}: {e}")
            raise DatabaseError(f"Failed to retrieve FinishedGood by ID: {e}")

    @staticmethod
    def get_finished_good_by_slug(slug: str) -> Optional[FinishedGood]:
        """
        Retrieve a specific FinishedGood by slug identifier.

        Args:
            slug: String slug identifier

        Returns:
            FinishedGood instance or None if not found

        Performance:
            Must complete in <50ms per contract (indexed lookup)
        """
        try:
            with get_db_session() as session:
                finished_good = session.query(FinishedGood)\
                    .options(selectinload(FinishedGood.components))\
                    .filter(FinishedGood.slug == slug)\
                    .first()

                if finished_good:
                    logger.debug(f"Retrieved FinishedGood by slug '{slug}': {finished_good.display_name}")
                else:
                    logger.debug(f"FinishedGood not found for slug '{slug}'")

                return finished_good

        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving FinishedGood slug '{slug}': {e}")
            raise DatabaseError(f"Failed to retrieve FinishedGood by slug: {e}")

    @staticmethod
    def get_all_finished_goods() -> List[FinishedGood]:
        """
        Retrieve all FinishedGood assemblies.

        Returns:
            List of all FinishedGood instances

        Performance:
            Must complete in <300ms for up to 1000 assemblies per contract
        """
        try:
            with get_db_session() as session:
                finished_goods = session.query(FinishedGood)\
                    .options(selectinload(FinishedGood.components))\
                    .order_by(FinishedGood.display_name)\
                    .all()

                logger.debug(f"Retrieved {len(finished_goods)} FinishedGoods")
                return finished_goods

        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving all FinishedGoods: {e}")
            raise DatabaseError(f"Failed to retrieve all FinishedGoods: {e}")

    @staticmethod
    def create_finished_good(
        display_name: str,
        assembly_type: AssemblyType,
        components: List[dict] = None,
        **kwargs
    ) -> FinishedGood:
        """
        Create a new assembly package.

        Args:
            display_name: Required string name
            assembly_type: AssemblyType enum value
            components: List of component specifications with quantities
            **kwargs: Additional optional fields

        Returns:
            Created FinishedGood instance

        Raises:
            ValidationError: If validation fails
            InvalidComponentError: If components are invalid
            InsufficientInventoryError: If components unavailable
            CircularReferenceError: If circular references detected

        Performance:
            Must complete in <2s for assemblies with up to 20 components per contract
        """
        try:
            # Validate required fields
            if not display_name or not display_name.strip():
                raise ValidationError("Display name is required and cannot be empty")

            if not isinstance(assembly_type, AssemblyType):
                raise ValidationError("Assembly type must be a valid AssemblyType enum")

            # Generate unique slug
            slug = FinishedGoodService._generate_slug(display_name.strip())

            # Validate total cost
            total_cost = kwargs.get('total_cost', Decimal('0.0000'))
            if total_cost < 0:
                raise ValidationError("Total cost must be non-negative")

            with session_scope() as session:
                # Check slug uniqueness
                existing = session.query(FinishedGood)\
                    .filter(FinishedGood.slug == slug)\
                    .first()

                if existing:
                    # Generate unique slug with suffix
                    slug = FinishedGoodService._generate_unique_slug(display_name.strip(), session)

                # Validate components if provided
                if components:
                    FinishedGoodService._validate_components(components, session)

                # Create FinishedGood with validated data
                assembly_data = {
                    'slug': slug,
                    'display_name': display_name.strip(),
                    'assembly_type': assembly_type,
                    'total_cost': total_cost,
                    'inventory_count': kwargs.get('inventory_count', 0),
                    'description': kwargs.get('description'),
                    'packaging_instructions': kwargs.get('packaging_instructions'),
                    'notes': kwargs.get('notes'),
                }

                # Remove None values
                assembly_data = {k: v for k, v in assembly_data.items() if v is not None}

                finished_good = FinishedGood(**assembly_data)
                session.add(finished_good)
                session.flush()  # Get the ID

                # Add components if provided
                if components:
                    total_component_cost = Decimal('0.0000')

                    for component_spec in components:
                        composition = FinishedGoodService._create_composition(
                            finished_good.id, component_spec, session
                        )
                        session.add(composition)

                        # Calculate component cost contribution
                        component_cost = FinishedGoodService._get_component_cost(component_spec, session)
                        total_component_cost += component_cost * component_spec['quantity']

                    # Calculate packaging cost and total cost
                    packaging_cost = calculate_packaging_cost(assembly_type, total_component_cost)
                    total_cost_with_packaging = total_component_cost + packaging_cost

                    # Update total cost if not explicitly provided
                    if 'total_cost' not in kwargs:
                        finished_good.total_cost = total_cost_with_packaging

                    # Validate business rules
                    component_count = len(components)
                    is_valid, errors = validate_assembly_type_business_rules(
                        assembly_type, component_count, total_cost_with_packaging
                    )
                    if not is_valid:
                        raise ValidationError(f"Assembly type validation failed: {'; '.join(errors)}")

                elif 'total_cost' not in kwargs:
                    # No components provided, validate minimum requirements
                    component_count = 0
                    is_valid, errors = validate_assembly_type_business_rules(
                        assembly_type, component_count, Decimal('0.0000')
                    )
                    if not is_valid:
                        raise ValidationError(f"Assembly type validation failed: {'; '.join(errors)}")

                logger.info(f"Created FinishedGood assembly: {finished_good.display_name} (ID: {finished_good.id})")
                return finished_good

        except IntegrityError as e:
            logger.error(f"Integrity error creating FinishedGood: {e}")
            if "uq_finished_good_slug" in str(e):
                raise ValidationError(f"Slug '{slug}' already exists")
            else:
                raise DatabaseError(f"Database integrity error: {e}")

        except SQLAlchemyError as e:
            logger.error(f"Database error creating FinishedGood: {e}")
            raise DatabaseError(f"Failed to create FinishedGood: {e}")

    @staticmethod
    def update_finished_good(finished_good_id: int, **updates) -> FinishedGood:
        """
        Update an existing FinishedGood.

        Args:
            finished_good_id: ID of FinishedGood to update
            **updates: Dictionary of fields to update

        Returns:
            Updated FinishedGood instance

        Raises:
            FinishedGoodNotFoundError: If assembly doesn't exist
            ValidationError: If validation fails

        Performance:
            Must complete in <1s per contract
        """
        try:
            with session_scope() as session:
                assembly = session.query(FinishedGood)\
                    .filter(FinishedGood.id == finished_good_id)\
                    .first()

                if not assembly:
                    raise FinishedGoodNotFoundError(f"FinishedGood ID {finished_good_id} not found")

                # Validate updates
                if 'display_name' in updates:
                    display_name = updates['display_name']
                    if not display_name or not display_name.strip():
                        raise ValidationError("Display name cannot be empty")

                    # Update slug if display name changed
                    if display_name.strip() != assembly.display_name:
                        new_slug = FinishedGoodService._generate_unique_slug(
                            display_name.strip(), session, assembly.id
                        )
                        updates['slug'] = new_slug

                if 'total_cost' in updates and updates['total_cost'] < 0:
                    raise ValidationError("Total cost must be non-negative")

                if 'inventory_count' in updates and updates['inventory_count'] < 0:
                    raise ValidationError("Inventory count must be non-negative")

                if 'assembly_type' in updates and not isinstance(updates['assembly_type'], AssemblyType):
                    raise ValidationError("Assembly type must be a valid AssemblyType enum")

                # Apply updates
                for field, value in updates.items():
                    if hasattr(assembly, field):
                        setattr(assembly, field, value)

                assembly.updated_at = datetime.utcnow()
                session.flush()

                logger.info(f"Updated FinishedGood ID {finished_good_id}: {assembly.display_name}")
                return assembly

        except SQLAlchemyError as e:
            logger.error(f"Database error updating FinishedGood ID {finished_good_id}: {e}")
            raise DatabaseError(f"Failed to update FinishedGood: {e}")

    @staticmethod
    def delete_finished_good(finished_good_id: int) -> bool:
        """
        Delete a FinishedGood assembly.

        Args:
            finished_good_id: ID of FinishedGood to delete

        Returns:
            True if deleted, False if not found

        Raises:
            DatabaseError: If database operation fails

        Performance:
            Must complete in <1s per contract
        """
        try:
            with session_scope() as session:
                assembly = session.query(FinishedGood)\
                    .filter(FinishedGood.id == finished_good_id)\
                    .first()

                if not assembly:
                    logger.debug(f"FinishedGood ID {finished_good_id} not found for deletion")
                    return False

                # Check if this assembly is used as a component in other assemblies
                usage_count = session.query(Composition)\
                    .filter(Composition.finished_good_id == finished_good_id)\
                    .count()

                if usage_count > 0:
                    logger.warning(f"FinishedGood '{assembly.display_name}' is used in {usage_count} other assemblies")

                # Delete the assembly (cascade will handle compositions)
                display_name = assembly.display_name
                session.delete(assembly)

                logger.info(f"Deleted FinishedGood ID {finished_good_id}: {display_name}")
                return True

        except SQLAlchemyError as e:
            logger.error(f"Database error deleting FinishedGood ID {finished_good_id}: {e}")
            raise DatabaseError(f"Failed to delete FinishedGood: {e}")

    # Component Management

    @staticmethod
    def add_component(
        finished_good_id: int,
        component_type: str,
        component_id: int,
        quantity: int,
        **kwargs
    ) -> bool:
        """
        Add a component to an assembly.

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
                raise ValidationError("Component type must be 'finished_unit' or 'finished_good'")

            if quantity <= 0:
                raise ValidationError("Quantity must be positive")

            with session_scope() as session:
                # Validate assembly exists
                assembly = session.query(FinishedGood)\
                    .filter(FinishedGood.id == finished_good_id)\
                    .first()

                if not assembly:
                    raise FinishedGoodNotFoundError(f"FinishedGood ID {finished_good_id} not found")

                # Validate component exists
                if component_type == "finished_unit":
                    component = session.query(FinishedUnit)\
                        .filter(FinishedUnit.id == component_id)\
                        .first()
                    if not component:
                        raise InvalidComponentError(f"FinishedUnit ID {component_id} not found")

                elif component_type == "finished_good":
                    component = session.query(FinishedGood)\
                        .filter(FinishedGood.id == component_id)\
                        .first()
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
                existing_composition = session.query(Composition)\
                    .filter(
                        Composition.assembly_id == finished_good_id,
                        getattr(Composition, f"{component_type}_id") == component_id
                    ).first()

                if existing_composition:
                    raise ValidationError(f"Component already exists in assembly")

                # Create composition
                composition_data = {
                    'assembly_id': finished_good_id,
                    'component_quantity': quantity,
                    'component_notes': kwargs.get('notes'),
                    'sort_order': kwargs.get('sort_order', 0)
                }

                if component_type == "finished_unit":
                    composition_data['finished_unit_id'] = component_id
                else:
                    composition_data['finished_good_id'] = component_id

                composition = Composition(**composition_data)
                session.add(composition)
                session.flush()

                # Update assembly total cost
                FinishedGoodService._recalculate_assembly_cost(finished_good_id, session)

                logger.info(f"Added {component_type} {component_id} (qty: {quantity}) to assembly {finished_good_id}")
                return True

        except SQLAlchemyError as e:
            logger.error(f"Database error adding component to FinishedGood ID {finished_good_id}: {e}")
            raise DatabaseError(f"Failed to add component: {e}")

    @staticmethod
    def remove_component(finished_good_id: int, composition_id: int) -> bool:
        """
        Remove a component from an assembly.

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
                assembly = session.query(FinishedGood)\
                    .filter(FinishedGood.id == finished_good_id)\
                    .first()

                if not assembly:
                    raise FinishedGoodNotFoundError(f"FinishedGood ID {finished_good_id} not found")

                # Find and remove composition
                composition = session.query(Composition)\
                    .filter(
                        Composition.id == composition_id,
                        Composition.assembly_id == finished_good_id
                    ).first()

                if not composition:
                    logger.debug(f"Composition ID {composition_id} not found in assembly {finished_good_id}")
                    return False

                session.delete(composition)
                session.flush()

                # Update assembly total cost
                FinishedGoodService._recalculate_assembly_cost(finished_good_id, session)

                logger.info(f"Removed composition {composition_id} from assembly {finished_good_id}")
                return True

        except SQLAlchemyError as e:
            logger.error(f"Database error removing component from FinishedGood ID {finished_good_id}: {e}")
            raise DatabaseError(f"Failed to remove component: {e}")

    @staticmethod
    def update_component_quantity(composition_id: int, new_quantity: int) -> bool:
        """
        Update quantity of a component in an assembly.

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
                raise ValidationError("Quantity must be positive")

            with session_scope() as session:
                composition = session.query(Composition)\
                    .filter(Composition.id == composition_id)\
                    .first()

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
                assembly = session.query(FinishedGood)\
                    .filter(FinishedGood.id == finished_good_id)\
                    .first()

                if not assembly:
                    raise FinishedGoodNotFoundError(f"FinishedGood ID {finished_good_id} not found")

                if flatten:
                    return FinishedGoodService._get_flattened_components(finished_good_id, session)
                else:
                    return FinishedGoodService._get_hierarchical_components(finished_good_id, session)

        except SQLAlchemyError as e:
            logger.error(f"Database error getting components for FinishedGood ID {finished_good_id}: {e}")
            raise DatabaseError(f"Failed to get components: {e}")

    @staticmethod
    def calculate_total_cost(finished_good_id: int) -> Decimal:
        """
        Calculate total cost of assembly including all components.

        Args:
            finished_good_id: ID of the assembly

        Returns:
            Total calculated cost

        Performance:
            Must complete in <500ms for complex hierarchies per contract
        """
        try:
            with get_db_session() as session:
                assembly = session.query(FinishedGood)\
                    .options(selectinload(FinishedGood.components))\
                    .filter(FinishedGood.id == finished_good_id)\
                    .first()

                if not assembly:
                    raise FinishedGoodNotFoundError(f"FinishedGood ID {finished_good_id} not found")

                total_cost = assembly.calculate_component_cost()
                logger.debug(f"Calculated total cost for assembly {finished_good_id}: {total_cost}")
                return total_cost

        except SQLAlchemyError as e:
            logger.error(f"Database error calculating cost for FinishedGood ID {finished_good_id}: {e}")
            raise DatabaseError(f"Failed to calculate total cost: {e}")

    @staticmethod
    def check_assembly_availability(finished_good_id: int, required_quantity: int = 1) -> dict:
        """
        Check if assembly can be created with available components.

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
                assembly = session.query(FinishedGood)\
                    .options(selectinload(FinishedGood.components))\
                    .filter(FinishedGood.id == finished_good_id)\
                    .first()

                if not assembly:
                    raise FinishedGoodNotFoundError(f"FinishedGood ID {finished_good_id} not found")

                availability_result = assembly.can_assemble(required_quantity)
                logger.debug(f"Availability check for assembly {finished_good_id}: {availability_result['can_assemble']}")
                return availability_result

        except SQLAlchemyError as e:
            logger.error(f"Database error checking availability for FinishedGood ID {finished_good_id}: {e}")
            raise DatabaseError(f"Failed to check assembly availability: {e}")

    # Assembly Production

    @staticmethod
    def create_assembly_from_inventory(finished_good_id: int, quantity: int) -> bool:
        """
        Create assemblies by consuming available component inventory.

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
                availability = FinishedGoodService.check_assembly_availability(finished_good_id, quantity)

                if not availability['can_assemble']:
                    missing_components = availability.get('missing_components', [])
                    raise InsufficientInventoryError(
                        f"Cannot create {quantity} assemblies: {missing_components}"
                    )

                # Consume component inventory
                assembly = session.query(FinishedGood)\
                    .options(selectinload(FinishedGood.components))\
                    .filter(FinishedGood.id == finished_good_id)\
                    .first()

                for composition in assembly.components:
                    required_qty = composition.component_quantity * quantity

                    if composition.finished_unit_component:
                        # Update FinishedUnit inventory
                        FinishedUnitService.update_inventory(
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
                assembly = session.query(FinishedGood)\
                    .options(selectinload(FinishedGood.components))\
                    .filter(FinishedGood.id == finished_good_id)\
                    .first()

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
                        FinishedUnitService.update_inventory(
                            composition.finished_unit_id, restored_qty
                        )
                    elif composition.finished_good_component:
                        # Update FinishedGood inventory
                        component_assembly = composition.finished_good_component
                        component_assembly.update_inventory(restored_qty)

                # Decrease assembly inventory
                assembly.update_inventory(-quantity)
                session.flush()

                logger.info(f"Disassembled {quantity} assemblies of FinishedGood {finished_good_id}")
                return True

        except SQLAlchemyError as e:
            logger.error(f"Database error disassembling: {e}")
            raise DatabaseError(f"Failed to disassemble: {e}")

    @staticmethod
    def validate_no_circular_references(
        finished_good_id: int,
        new_component_id: int,
        session: Session = None
    ) -> bool:
        """
        Ensure adding a component won't create circular references.

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

            with (use_session if session else use_session()) as s:
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
                    components = s.query(Composition)\
                        .filter(Composition.assembly_id == current_id)\
                        .all()

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
                assemblies = session.query(FinishedGood)\
                    .options(selectinload(FinishedGood.components))\
                    .filter(
                        or_(
                            FinishedGood.display_name.ilike(search_term),
                            FinishedGood.description.ilike(search_term),
                            FinishedGood.notes.ilike(search_term)
                        )
                    )\
                    .order_by(FinishedGood.display_name)\
                    .all()

                logger.debug(f"Search for '{query}' returned {len(assemblies)} FinishedGoods")
                return assemblies

        except SQLAlchemyError as e:
            logger.error(f"Database error searching FinishedGoods with query '{query}': {e}")
            raise DatabaseError(f"Failed to search FinishedGoods: {e}")

    @staticmethod
    def get_assemblies_by_type(assembly_type: AssemblyType) -> List[FinishedGood]:
        """
        Get all assemblies of a specific type.

        Args:
            assembly_type: AssemblyType enum value

        Returns:
            List of FinishedGood instances

        Performance:
            Must complete in <200ms per contract
        """
        try:
            with get_db_session() as session:
                assemblies = session.query(FinishedGood)\
                    .options(selectinload(FinishedGood.components))\
                    .filter(FinishedGood.assembly_type == assembly_type)\
                    .order_by(FinishedGood.display_name)\
                    .all()

                logger.debug(f"Retrieved {len(assemblies)} FinishedGoods of type {assembly_type}")
                return assemblies

        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving FinishedGoods by type {assembly_type}: {e}")
            raise DatabaseError(f"Failed to retrieve FinishedGoods by type: {e}")

    # Utility Methods

    @staticmethod
    def _generate_slug(display_name: str) -> str:
        """Generate URL-safe slug from display name."""
        if not display_name:
            return "unknown-assembly"

        # Normalize unicode characters
        slug = unicodedata.normalize('NFKD', display_name)

        # Convert to lowercase and replace spaces/punctuation with hyphens
        slug = re.sub(r'[^\w\s-]', '', slug).strip().lower()
        slug = re.sub(r'[\s_-]+', '-', slug)

        # Remove leading/trailing hyphens
        slug = slug.strip('-')

        # Ensure not empty
        if not slug:
            return "unknown-assembly"

        # Limit length
        if len(slug) > 90:
            slug = slug[:90].rstrip('-')

        return slug

    @staticmethod
    def _generate_unique_slug(display_name: str, session: Session, exclude_id: Optional[int] = None) -> str:
        """Generate unique slug, adding suffix if needed."""
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
        """Validate component specifications."""
        for component_spec in components:
            if 'component_type' not in component_spec:
                raise ValidationError("Component must specify 'component_type'")

            if 'component_id' not in component_spec:
                raise ValidationError("Component must specify 'component_id'")

            if 'quantity' not in component_spec or component_spec['quantity'] <= 0:
                raise ValidationError("Component must specify positive quantity")

            component_type = component_spec['component_type']
            component_id = component_spec['component_id']

            if component_type == "finished_unit":
                component = session.query(FinishedUnit).filter(FinishedUnit.id == component_id).first()
                if not component:
                    raise InvalidComponentError(f"FinishedUnit ID {component_id} not found")
            elif component_type == "finished_good":
                component = session.query(FinishedGood).filter(FinishedGood.id == component_id).first()
                if not component:
                    raise InvalidComponentError(f"FinishedGood ID {component_id} not found")
            else:
                raise ValidationError("Component type must be 'finished_unit' or 'finished_good'")

    @staticmethod
    def _create_composition(assembly_id: int, component_spec: dict, session: Session) -> Composition:
        """Create composition from component specification."""
        composition_data = {
            'assembly_id': assembly_id,
            'component_quantity': component_spec['quantity'],
            'component_notes': component_spec.get('notes'),
            'sort_order': component_spec.get('sort_order', 0)
        }

        if component_spec['component_type'] == "finished_unit":
            composition_data['finished_unit_id'] = component_spec['component_id']
        else:
            composition_data['finished_good_id'] = component_spec['component_id']

        return Composition(**composition_data)

    @staticmethod
    def _get_component_cost(component_spec: dict, session: Session) -> Decimal:
        """Get unit cost for a component."""
        component_type = component_spec['component_type']
        component_id = component_spec['component_id']

        if component_type == "finished_unit":
            component = session.query(FinishedUnit).filter(FinishedUnit.id == component_id).first()
            return component.unit_cost if component else Decimal('0.0000')
        elif component_type == "finished_good":
            component = session.query(FinishedGood).filter(FinishedGood.id == component_id).first()
            return component.total_cost if component else Decimal('0.0000')

        return Decimal('0.0000')

    @staticmethod
    def _recalculate_assembly_cost(assembly_id: int, session: Session) -> None:
        """Recalculate and update assembly total cost."""
        assembly = session.query(FinishedGood)\
            .options(selectinload(FinishedGood.components))\
            .filter(FinishedGood.id == assembly_id)\
            .first()

        if assembly:
            assembly.update_total_cost_from_components()
            session.flush()

    @staticmethod
    def _get_flattened_components(finished_good_id: int, session: Session) -> List[dict]:
        """
        Get all components in a flattened list format.

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
            compositions = session.query(Composition)\
                .options(
                    selectinload(Composition.finished_unit_component),
                    selectinload(Composition.finished_good_component)
                )\
                .filter(Composition.assembly_id == current_assembly_id)\
                .all()

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
                            'component_type': 'finished_unit',
                            'component_id': unit.id,
                            'display_name': unit.display_name,
                            'unit_cost': float(unit.unit_cost),
                            'inventory_count': unit.inventory_count,
                            'slug': unit.slug
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
                            'component_type': 'finished_good',
                            'component_id': subassembly.id,
                            'display_name': subassembly.display_name,
                            'unit_cost': float(subassembly.total_cost),
                            'inventory_count': subassembly.inventory_count,
                            'slug': subassembly.slug,
                            'assembly_type': subassembly.assembly_type.value
                        }

                    # Add to queue for expansion
                    queue.append((subassembly.id, effective_quantity))

        # Convert to final format
        result = []
        for key, total_quantity in components.items():
            detail = component_details[key].copy()
            detail['total_quantity'] = total_quantity
            detail['total_cost'] = detail['unit_cost'] * total_quantity
            result.append(detail)

        # Sort by component type and name
        result.sort(key=lambda x: (x['component_type'], x['display_name']))
        return result

    @staticmethod
    def _get_hierarchical_components(finished_good_id: int, session: Session) -> List[dict]:
        """
        Get components maintaining hierarchical structure.

        Returns nested structure showing assembly composition levels.
        """
        def get_assembly_components(assembly_id: int, level: int = 0) -> List[dict]:
            if level > 10:  # Prevent infinite recursion
                logger.warning(f"Maximum hierarchy depth reached for assembly {assembly_id}")
                return []

            compositions = session.query(Composition)\
                .options(
                    selectinload(Composition.finished_unit_component),
                    selectinload(Composition.finished_good_component)
                )\
                .filter(Composition.assembly_id == assembly_id)\
                .order_by(Composition.sort_order, Composition.id)\
                .all()

            components = []
            for comp in compositions:
                if comp.finished_unit_component:
                    # FinishedUnit component
                    unit = comp.finished_unit_component
                    component_data = {
                        'composition_id': comp.id,
                        'component_type': 'finished_unit',
                        'component_id': unit.id,
                        'display_name': unit.display_name,
                        'slug': unit.slug,
                        'quantity': comp.component_quantity,
                        'unit_cost': float(unit.unit_cost),
                        'total_cost': float(unit.unit_cost * comp.component_quantity),
                        'inventory_count': unit.inventory_count,
                        'component_notes': comp.component_notes,
                        'sort_order': comp.sort_order,
                        'level': level,
                        'subcomponents': []  # FinishedUnits have no subcomponents
                    }

                elif comp.finished_good_component:
                    # FinishedGood component
                    subassembly = comp.finished_good_component
                    component_data = {
                        'composition_id': comp.id,
                        'component_type': 'finished_good',
                        'component_id': subassembly.id,
                        'display_name': subassembly.display_name,
                        'slug': subassembly.slug,
                        'quantity': comp.component_quantity,
                        'unit_cost': float(subassembly.total_cost),
                        'total_cost': float(subassembly.total_cost * comp.component_quantity),
                        'inventory_count': subassembly.inventory_count,
                        'assembly_type': subassembly.assembly_type.value,
                        'component_notes': comp.component_notes,
                        'sort_order': comp.sort_order,
                        'level': level,
                        'subcomponents': get_assembly_components(subassembly.id, level + 1)
                    }

                components.append(component_data)

            return components

        return get_assembly_components(finished_good_id)

    # Assembly Type-Specific Business Logic

    @staticmethod
    def validate_assembly_business_rules(assembly_id: int) -> dict:
        """
        Validate complete business rules for an assembly based on its type.

        Args:
            assembly_id: ID of the assembly to validate

        Returns:
            Dictionary with validation results and any issues found

        Performance:
            Must complete in <300ms per contract
        """
        try:
            with get_db_session() as session:
                assembly = session.query(FinishedGood)\
                    .options(selectinload(FinishedGood.components))\
                    .filter(FinishedGood.id == assembly_id)\
                    .first()

                if not assembly:
                    raise FinishedGoodNotFoundError(f"FinishedGood ID {assembly_id} not found")

                component_count = len(assembly.components)
                total_cost = assembly.total_cost

                is_valid, errors = validate_assembly_type_business_rules(
                    assembly.assembly_type, component_count, total_cost
                )

                result = {
                    'assembly_id': assembly_id,
                    'assembly_type': assembly.assembly_type.value,
                    'assembly_type_name': assembly.assembly_type.get_display_name(),
                    'is_valid': is_valid,
                    'errors': errors,
                    'component_count': component_count,
                    'total_cost': float(total_cost),
                    'business_rules': assembly.assembly_type.get_business_rules(),
                    'component_limits': assembly.assembly_type.get_component_limits(),
                    'validated_at': datetime.utcnow().isoformat()
                }

                logger.debug(f"Business rule validation for assembly {assembly_id}: {is_valid}")
                return result

        except SQLAlchemyError as e:
            logger.error(f"Database error validating assembly business rules: {e}")
            raise DatabaseError(f"Failed to validate assembly business rules: {e}")

    @staticmethod
    def calculate_suggested_pricing(assembly_id: int) -> dict:
        """
        Calculate suggested pricing based on assembly type markup rules.

        Args:
            assembly_id: ID of the assembly

        Returns:
            Dictionary with pricing breakdown and suggestions

        Performance:
            Must complete in <200ms per contract
        """
        try:
            with get_db_session() as session:
                assembly = session.query(FinishedGood)\
                    .filter(FinishedGood.id == assembly_id)\
                    .first()

                if not assembly:
                    raise FinishedGoodNotFoundError(f"FinishedGood ID {assembly_id} not found")

                # Calculate component cost breakdown
                cost_breakdown = FinishedGoodService.calculate_total_cost(assembly_id)

                # Get packaging cost
                packaging_cost = calculate_packaging_cost(assembly.assembly_type, cost_breakdown)

                # Calculate suggested retail price
                suggested_price = get_suggested_retail_price(assembly.assembly_type, assembly.total_cost)

                pricing_info = {
                    'assembly_id': assembly_id,
                    'assembly_type': assembly.assembly_type.value,
                    'assembly_type_name': assembly.assembly_type.get_display_name(),
                    'component_cost': float(cost_breakdown),
                    'packaging_cost': float(packaging_cost),
                    'total_cost': float(assembly.total_cost),
                    'markup_percentage': float(assembly.assembly_type.get_pricing_markup() * 100),
                    'suggested_retail_price': float(suggested_price),
                    'profit_margin': float(suggested_price - assembly.total_cost),
                    'profit_margin_percentage': float(((suggested_price - assembly.total_cost) / suggested_price) * 100),
                    'calculated_at': datetime.utcnow().isoformat()
                }

                logger.debug(f"Calculated pricing for assembly {assembly_id}: ${suggested_price}")
                return pricing_info

        except SQLAlchemyError as e:
            logger.error(f"Database error calculating suggested pricing: {e}")
            raise DatabaseError(f"Failed to calculate suggested pricing: {e}")

    @staticmethod
    def get_assembly_type_recommendations(assembly_type: AssemblyType) -> dict:
        """
        Get recommendations and guidelines for a specific assembly type.

        Args:
            assembly_type: AssemblyType enum value

        Returns:
            Dictionary with assembly type recommendations and metadata
        """
        try:
            recommendations = {
                'assembly_type': assembly_type.value,
                'display_name': assembly_type.get_display_name(),
                'description': assembly_type.get_description(),
                'component_limits': assembly_type.get_component_limits(),
                'business_rules': assembly_type.get_business_rules(),
                'is_seasonal': assembly_type.is_seasonal(),
                'packaging_priority': assembly_type.get_packaging_priority(),
                'requires_special_handling': assembly_type.requires_special_handling(),
                'pricing_markup': float(assembly_type.get_pricing_markup()),
                'packaging_notes': assembly_type.get_business_rules().get('packaging_notes', '')
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

        Returns:
            List of assemblies with issues or recommendations

        Performance:
            Must complete in <1s per contract
        """
        try:
            with get_db_session() as session:
                assemblies = session.query(FinishedGood)\
                    .options(selectinload(FinishedGood.components))\
                    .all()

                attention_required = []

                for assembly in assemblies:
                    issues = []

                    # Check business rule compliance
                    component_count = len(assembly.components)
                    is_valid, errors = validate_assembly_type_business_rules(
                        assembly.assembly_type, component_count, assembly.total_cost
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
                        attention_required.append({
                            'assembly_id': assembly.id,
                            'display_name': assembly.display_name,
                            'assembly_type': assembly.assembly_type.value,
                            'assembly_type_name': assembly.assembly_type.get_display_name(),
                            'issues': issues,
                            'component_count': component_count,
                            'total_cost': float(assembly.total_cost),
                            'last_updated': assembly.updated_at.isoformat() if assembly.updated_at else None
                        })

                logger.debug(f"Found {len(attention_required)} assemblies requiring attention")
                return attention_required

        except SQLAlchemyError as e:
            logger.error(f"Database error getting assemblies requiring attention: {e}")
            raise DatabaseError(f"Failed to get assemblies requiring attention: {e}")


# Module-level convenience functions for backward compatibility

def get_finished_good_by_id(finished_good_id: int) -> Optional[FinishedGood]:
    """Retrieve a specific FinishedGood by ID."""
    return FinishedGoodService.get_finished_good_by_id(finished_good_id)


def get_finished_good_by_slug(slug: str) -> Optional[FinishedGood]:
    """Retrieve a specific FinishedGood by slug."""
    return FinishedGoodService.get_finished_good_by_slug(slug)


def get_all_finished_goods() -> List[FinishedGood]:
    """Retrieve all FinishedGoods."""
    return FinishedGoodService.get_all_finished_goods()


def create_finished_good(display_name: str, assembly_type: AssemblyType, **kwargs) -> FinishedGood:
    """Create a new FinishedGood assembly."""
    return FinishedGoodService.create_finished_good(display_name, assembly_type, **kwargs)


def add_component(finished_good_id: int, component_type: str, component_id: int, quantity: int) -> bool:
    """Add a component to an assembly."""
    return FinishedGoodService.add_component(finished_good_id, component_type, component_id, quantity)


def search_finished_goods(query: str) -> List[FinishedGood]:
    """Search assemblies by name or description."""
    return FinishedGoodService.search_finished_goods(query)


def get_assemblies_by_type(assembly_type: AssemblyType) -> List[FinishedGood]:
    """Get all assemblies of a specific type."""
    return FinishedGoodService.get_assemblies_by_type(assembly_type)