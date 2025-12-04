"""
Composition Service - Junction table operations and relationship management.

This service provides comprehensive management for Composition relationships, implementing
the polymorphic junction table between FinishedGood assemblies and their components
(both FinishedUnit and FinishedGood components).

Key Features:
- Complete composition CRUD operations with validation
- Assembly hierarchy traversal and flattening operations
- Circular reference detection and prevention
- Bulk operations for efficient composition management
- Cost and quantity calculations across component relationships
- High-performance operations for complex assembly hierarchies
"""

import logging
from decimal import Decimal
from typing import List, Optional, Dict, Any, Set, Tuple
from collections import deque
from datetime import datetime
import threading
import time

from sqlalchemy import and_, or_, text, func
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from .database import get_db_session, session_scope
from ..models import Composition, FinishedGood, FinishedUnit
from .exceptions import ServiceError, ValidationError, DatabaseError

logger = logging.getLogger(__name__)


# Hierarchy caching for performance optimization
class HierarchyCache:
    """
    Thread-safe cache for hierarchy operations to improve performance.

    Caches frequently accessed hierarchy structures with TTL (Time To Live)
    to balance performance with data freshness.
    """

    def __init__(self, ttl_seconds: int = 300):  # 5 minute TTL
        self.cache: Dict[str, Tuple[Any, float]] = {}
        self.ttl = ttl_seconds
        self.lock = threading.RLock()

    def get(self, key: str) -> Optional[Any]:
        """Get cached value if not expired."""
        with self.lock:
            if key in self.cache:
                value, timestamp = self.cache[key]
                if time.time() - timestamp < self.ttl:
                    return value
                else:
                    # Expired, remove from cache
                    del self.cache[key]
            return None

    def put(self, key: str, value: Any) -> None:
        """Store value in cache with current timestamp."""
        with self.lock:
            self.cache[key] = (value, time.time())

    def invalidate(self, pattern: str = None) -> None:
        """Remove cache entries, optionally matching pattern."""
        with self.lock:
            if pattern is None:
                self.cache.clear()
            else:
                keys_to_remove = [k for k in self.cache.keys() if pattern in k]
                for key in keys_to_remove:
                    del self.cache[key]

    def size(self) -> int:
        """Get current cache size."""
        with self.lock:
            # Clean expired entries first
            current_time = time.time()
            expired_keys = [
                k
                for k, (_, timestamp) in self.cache.items()
                if current_time - timestamp >= self.ttl
            ]
            for key in expired_keys:
                del self.cache[key]
            return len(self.cache)


# Global hierarchy cache instance
_hierarchy_cache = HierarchyCache()


# Custom exceptions for Composition service
class CompositionNotFoundError(ServiceError):
    """Raised when a Composition cannot be found."""

    pass


class InvalidComponentTypeError(ServiceError):
    """Raised when component type is invalid."""

    pass


class CircularReferenceError(ServiceError):
    """Raised when operation would create circular dependency."""

    pass


class DuplicateCompositionError(ServiceError):
    """Raised when composition already exists."""

    pass


class IntegrityViolationError(ServiceError):
    """Raised when operation would violate referential integrity."""

    pass


class CompositionService:
    """
    Service for Composition operations and polymorphic relationship management.

    Provides comprehensive composition creation, hierarchy traversal, validation,
    and bulk operations for assembly component relationships.
    """

    # Core Operations

    @staticmethod
    def create_composition(
        assembly_id: int, component_type: str, component_id: int, quantity: int, **kwargs
    ) -> Composition:
        """
        Create a new composition relationship.

        Args:
            assembly_id: ID of the FinishedGood assembly
            component_type: "finished_unit" or "finished_good"
            component_id: ID of the component
            quantity: Number of this component in the assembly
            **kwargs: Optional fields (notes, sort_order)

        Returns:
            Created Composition instance

        Raises:
            ValidationError: If validation fails
            InvalidComponentTypeError: If component type invalid
            DuplicateCompositionError: If composition already exists
            CircularReferenceError: If circular reference detected

        Performance:
            Must complete in <200ms per contract
        """
        try:
            # Validate component type
            if component_type not in ["finished_unit", "finished_good"]:
                raise InvalidComponentTypeError(
                    "Component type must be 'finished_unit' or 'finished_good'"
                )

            # Validate quantity
            if quantity <= 0:
                raise ValidationError("Quantity must be positive")

            with session_scope() as session:
                # Validate assembly exists
                assembly = (
                    session.query(FinishedGood).filter(FinishedGood.id == assembly_id).first()
                )

                if not assembly:
                    raise ValidationError(f"Assembly ID {assembly_id} not found")

                # Validate component exists
                if not CompositionService.validate_component_exists(
                    component_type, component_id, session
                ):
                    raise ValidationError(f"Component {component_type} ID {component_id} not found")

                # Check for circular references (only for FinishedGood components)
                if component_type == "finished_good":
                    if not CompositionService.validate_no_circular_reference(
                        assembly_id, component_id, session
                    ):
                        raise CircularReferenceError(
                            f"Adding component {component_id} to assembly {assembly_id} would create circular reference"
                        )

                # Check for duplicate composition
                existing = session.query(Composition).filter(Composition.assembly_id == assembly_id)

                if component_type == "finished_unit":
                    existing = existing.filter(Composition.finished_unit_id == component_id)
                else:
                    existing = existing.filter(Composition.finished_good_id == component_id)

                if existing.first():
                    raise DuplicateCompositionError(
                        f"Composition already exists for {component_type} {component_id} in assembly {assembly_id}"
                    )

                # Create composition
                composition_data = {
                    "assembly_id": assembly_id,
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

                # Invalidate hierarchy cache for affected assembly
                _hierarchy_cache.invalidate(f"hierarchy_{assembly_id}_")

                logger.info(
                    f"Created composition: {component_type} {component_id} in assembly {assembly_id}"
                )
                return composition

        except SQLAlchemyError as e:
            logger.error(f"Database error creating composition: {e}")
            raise DatabaseError(f"Failed to create composition: {e}")

    @staticmethod
    def get_composition_by_id(composition_id: int) -> Optional[Composition]:
        """
        Retrieve a specific composition relationship.

        Args:
            composition_id: ID of the composition

        Returns:
            Composition instance or None if not found

        Performance:
            Must complete in <50ms per contract
        """
        try:
            with get_db_session() as session:
                composition = (
                    session.query(Composition)
                    .options(
                        selectinload(Composition.finished_unit_component),
                        selectinload(Composition.finished_good_component),
                        selectinload(Composition.assembly),
                    )
                    .filter(Composition.id == composition_id)
                    .first()
                )

                if composition:
                    logger.debug(f"Retrieved composition ID {composition_id}")
                else:
                    logger.debug(f"Composition ID {composition_id} not found")

                return composition

        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving composition ID {composition_id}: {e}")
            raise DatabaseError(f"Failed to retrieve composition: {e}")

    @staticmethod
    def update_composition(composition_id: int, **updates) -> Composition:
        """
        Update an existing composition relationship.

        Args:
            composition_id: ID of composition to update
            **updates: Dictionary of fields to update

        Returns:
            Updated Composition instance

        Raises:
            CompositionNotFoundError: If composition doesn't exist
            ValidationError: If validation fails

        Performance:
            Must complete in <200ms per contract
        """
        try:
            with session_scope() as session:
                composition = (
                    session.query(Composition).filter(Composition.id == composition_id).first()
                )

                if not composition:
                    raise CompositionNotFoundError(f"Composition ID {composition_id} not found")

                # Validate updates
                if "component_quantity" in updates:
                    quantity = updates["component_quantity"]
                    if quantity <= 0:
                        raise ValidationError("Component quantity must be positive")

                # Apply updates
                for field, value in updates.items():
                    if hasattr(composition, field):
                        setattr(composition, field, value)

                composition.updated_at = datetime.utcnow()
                session.flush()

                logger.info(f"Updated composition ID {composition_id}")
                return composition

        except SQLAlchemyError as e:
            logger.error(f"Database error updating composition ID {composition_id}: {e}")
            raise DatabaseError(f"Failed to update composition: {e}")

    @staticmethod
    def delete_composition(composition_id: int) -> bool:
        """
        Delete a composition relationship.

        Args:
            composition_id: ID of composition to delete

        Returns:
            True if deleted, False if not found

        Performance:
            Must complete in <100ms per contract
        """
        try:
            with session_scope() as session:
                composition = (
                    session.query(Composition).filter(Composition.id == composition_id).first()
                )

                if not composition:
                    logger.debug(f"Composition ID {composition_id} not found for deletion")
                    return False

                assembly_id = composition.assembly_id
                session.delete(composition)

                # Invalidate hierarchy cache for affected assembly
                _hierarchy_cache.invalidate(f"hierarchy_{assembly_id}_")

                logger.info(f"Deleted composition ID {composition_id} from assembly {assembly_id}")
                return True

        except SQLAlchemyError as e:
            logger.error(f"Database error deleting composition ID {composition_id}: {e}")
            raise DatabaseError(f"Failed to delete composition: {e}")

    # Assembly Composition Queries

    @staticmethod
    def get_assembly_components(assembly_id: int, ordered: bool = True) -> List[Composition]:
        """
        Get all direct components of an assembly.

        Args:
            assembly_id: ID of the FinishedGood assembly
            ordered: If True, return in sort_order sequence

        Returns:
            List of Composition instances

        Performance:
            Must complete in <100ms per contract
        """
        try:
            with get_db_session() as session:
                query = (
                    session.query(Composition)
                    .options(
                        selectinload(Composition.finished_unit_component),
                        selectinload(Composition.finished_good_component),
                    )
                    .filter(Composition.assembly_id == assembly_id)
                )

                if ordered:
                    query = query.order_by(Composition.sort_order, Composition.id)

                compositions = query.all()
                logger.debug(f"Retrieved {len(compositions)} components for assembly {assembly_id}")
                return compositions

        except SQLAlchemyError as e:
            logger.error(f"Database error getting assembly components for {assembly_id}: {e}")
            raise DatabaseError(f"Failed to get assembly components: {e}")

    @staticmethod
    def get_component_usages(component_type: str, component_id: int) -> List[Composition]:
        """
        Find all assemblies that use a specific component.

        Args:
            component_type: "finished_unit" or "finished_good"
            component_id: ID of the component

        Returns:
            List of Composition instances

        Raises:
            InvalidComponentTypeError: If component type invalid

        Performance:
            Must complete in <200ms per contract
        """
        try:
            if component_type not in ["finished_unit", "finished_good"]:
                raise InvalidComponentTypeError(
                    "Component type must be 'finished_unit' or 'finished_good'"
                )

            with get_db_session() as session:
                query = session.query(Composition).options(selectinload(Composition.assembly))

                if component_type == "finished_unit":
                    query = query.filter(Composition.finished_unit_id == component_id)
                else:
                    query = query.filter(Composition.finished_good_id == component_id)

                usages = query.all()
                logger.debug(f"Found {len(usages)} usages for {component_type} {component_id}")
                return usages

        except SQLAlchemyError as e:
            logger.error(f"Database error getting component usages: {e}")
            raise DatabaseError(f"Failed to get component usages: {e}")

    @staticmethod
    def get_assembly_hierarchy(assembly_id: int, max_depth: int = 5) -> dict:
        """
        Get complete hierarchy structure for an assembly.

        Args:
            assembly_id: ID of the FinishedGood assembly
            max_depth: Maximum hierarchy levels to traverse

        Returns:
            Nested dictionary representing full component hierarchy

        Performance:
            Must complete in <500ms for maximum depth per contract

        Algorithm:
            Iterative breadth-first search with caching optimization
        """
        try:
            # Check cache first
            cache_key = f"hierarchy_{assembly_id}_{max_depth}"
            cached_result = _hierarchy_cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Retrieved hierarchy from cache for assembly {assembly_id}")
                return cached_result

            with get_db_session() as session:
                # Get root assembly
                assembly = (
                    session.query(FinishedGood).filter(FinishedGood.id == assembly_id).first()
                )

                if not assembly:
                    raise ValidationError(f"Assembly ID {assembly_id} not found")

                def build_hierarchy_level(current_assembly_id: int, depth: int = 0) -> dict:
                    if depth >= max_depth:
                        return {"max_depth_reached": True}

                    # Get direct components
                    compositions = CompositionService.get_assembly_components(current_assembly_id)
                    components = []

                    for comp in compositions:
                        if comp.finished_unit_component:
                            unit = comp.finished_unit_component
                            component_data = {
                                "composition_id": comp.id,
                                "component_type": "finished_unit",
                                "component_id": unit.id,
                                "display_name": unit.display_name,
                                "slug": unit.slug,
                                "quantity": comp.component_quantity,
                                "unit_cost": float(unit.unit_cost),
                                "total_cost": float(unit.unit_cost * comp.component_quantity),
                                "inventory_count": unit.inventory_count,
                                "notes": comp.component_notes,
                                "sort_order": comp.sort_order,
                                "depth": depth,
                                "subcomponents": [],  # FinishedUnits have no subcomponents
                            }
                        elif comp.finished_good_component:
                            subassembly = comp.finished_good_component
                            component_data = {
                                "composition_id": comp.id,
                                "component_type": "finished_good",
                                "component_id": subassembly.id,
                                "display_name": subassembly.display_name,
                                "slug": subassembly.slug,
                                "quantity": comp.component_quantity,
                                "unit_cost": float(subassembly.total_cost),
                                "total_cost": float(
                                    subassembly.total_cost * comp.component_quantity
                                ),
                                "inventory_count": subassembly.inventory_count,
                                "assembly_type": subassembly.assembly_type.value,
                                "notes": comp.component_notes,
                                "sort_order": comp.sort_order,
                                "depth": depth,
                                "subcomponents": build_hierarchy_level(subassembly.id, depth + 1),
                            }

                        components.append(component_data)

                    return components

                hierarchy = {
                    "assembly_id": assembly.id,
                    "assembly_name": assembly.display_name,
                    "assembly_slug": assembly.slug,
                    "assembly_type": assembly.assembly_type.value,
                    "max_depth": max_depth,
                    "components": build_hierarchy_level(assembly_id),
                }

                # Cache the result for future requests
                _hierarchy_cache.put(cache_key, hierarchy)

                logger.debug(
                    f"Built hierarchy for assembly {assembly_id} with max depth {max_depth}"
                )
                return hierarchy

        except SQLAlchemyError as e:
            logger.error(f"Database error building assembly hierarchy: {e}")
            raise DatabaseError(f"Failed to build assembly hierarchy: {e}")

    @staticmethod
    def flatten_assembly_components(assembly_id: int) -> List[dict]:
        """
        Get flattened list of all components at all hierarchy levels.

        Args:
            assembly_id: ID of the FinishedGood assembly

        Returns:
            List of dictionaries with component details and total quantities

        Performance:
            Must complete in <400ms per contract

        Use Case:
            Bill of materials generation
        """
        try:
            with get_db_session() as session:
                components = {}  # component_key -> total_quantity
                component_details = {}  # component_key -> details
                queue = deque([(assembly_id, 1)])  # (assembly_id, multiplier)
                visited_assemblies = set()

                while queue:
                    current_assembly_id, multiplier = queue.popleft()

                    # Prevent circular references in traversal
                    if current_assembly_id in visited_assemblies:
                        continue
                    visited_assemblies.add(current_assembly_id)

                    # Get direct components of current assembly
                    compositions = CompositionService.get_assembly_components(current_assembly_id)

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
                                    "slug": unit.slug,
                                    "unit_cost": float(unit.unit_cost),
                                    "inventory_count": unit.inventory_count,
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
                                    "slug": subassembly.slug,
                                    "unit_cost": float(subassembly.total_cost),
                                    "inventory_count": subassembly.inventory_count,
                                    "assembly_type": subassembly.assembly_type.value,
                                }

                            # Add to queue for expansion
                            queue.append((subassembly.id, effective_quantity))

                # Convert to final format
                result = []
                for key, total_quantity in components.items():
                    detail = component_details[key].copy()
                    detail["total_quantity"] = total_quantity
                    detail["total_cost"] = detail["unit_cost"] * total_quantity
                    result.append(detail)

                # Sort by component type and name
                result.sort(key=lambda x: (x["component_type"], x["display_name"]))
                logger.debug(
                    f"Flattened {len(result)} unique components for assembly {assembly_id}"
                )
                return result

        except SQLAlchemyError as e:
            logger.error(f"Database error flattening assembly components: {e}")
            raise DatabaseError(f"Failed to flatten assembly components: {e}")

    # Validation Operations

    @staticmethod
    def validate_no_circular_reference(
        assembly_id: int, new_component_id: int, session: Session = None
    ) -> bool:
        """
        Check if adding a component would create circular dependency.

        Args:
            assembly_id: ID of assembly to add component to
            new_component_id: ID of component being added (must be FinishedGood)

        Returns:
            True if safe, False if would create cycle

        Algorithm:
            Breadth-first traversal with visited tracking

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

                    if current_id == assembly_id:
                        return False  # Circular reference detected

                    visited.add(current_id)

                    # Get FinishedGood components of current assembly
                    components = (
                        s.query(Composition)
                        .filter(Composition.assembly_id == current_id)
                        .filter(Composition.finished_good_id.isnot(None))
                        .all()
                    )

                    for comp in components:
                        queue.append(comp.finished_good_id)

                return True  # No circular reference

        except SQLAlchemyError as e:
            logger.error(f"Database error validating circular references: {e}")
            raise DatabaseError(f"Failed to validate circular references: {e}")

    @staticmethod
    def validate_component_exists(
        component_type: str, component_id: int, session: Session = None
    ) -> bool:
        """
        Verify that a component exists and is valid.

        Args:
            component_type: "finished_unit" or "finished_good"
            component_id: ID of the component

        Returns:
            True if component exists and is valid

        Performance:
            Must complete in <50ms per contract
        """
        try:
            use_session = session or get_db_session()

            with use_session if session else use_session() as s:
                if component_type == "finished_unit":
                    exists = (
                        s.query(FinishedUnit).filter(FinishedUnit.id == component_id).first()
                        is not None
                    )
                elif component_type == "finished_good":
                    exists = (
                        s.query(FinishedGood).filter(FinishedGood.id == component_id).first()
                        is not None
                    )
                else:
                    return False

                logger.debug(f"Component {component_type} {component_id} exists: {exists}")
                return exists

        except SQLAlchemyError as e:
            logger.error(f"Database error validating component existence: {e}")
            raise DatabaseError(f"Failed to validate component existence: {e}")

    @staticmethod
    def check_composition_integrity(assembly_id: int) -> dict:
        """
        Validate integrity of all compositions for an assembly.

        Args:
            assembly_id: ID of the assembly to check

        Returns:
            Dictionary with validation results and any issues found

        Performance:
            Must complete in <300ms per contract
        """
        try:
            with get_db_session() as session:
                issues = []
                warnings = []

                # Get all compositions for assembly
                compositions = CompositionService.get_assembly_components(assembly_id)

                for comp in compositions:
                    # Check referential integrity
                    if comp.finished_unit_id:
                        if not comp.finished_unit_component:
                            issues.append(
                                f"Composition {comp.id} references missing FinishedUnit {comp.finished_unit_id}"
                            )

                    if comp.finished_good_id:
                        if not comp.finished_good_component:
                            issues.append(
                                f"Composition {comp.id} references missing FinishedGood {comp.finished_good_id}"
                            )

                    # Check quantity validation
                    if comp.component_quantity <= 0:
                        issues.append(
                            f"Composition {comp.id} has invalid quantity {comp.component_quantity}"
                        )

                    # Check for orphaned compositions (both IDs are null)
                    if not comp.finished_unit_id and not comp.finished_good_id:
                        issues.append(f"Composition {comp.id} has no component reference")

                    # Check for duplicate references (both IDs are set)
                    if comp.finished_unit_id and comp.finished_good_id:
                        issues.append(f"Composition {comp.id} has both component types set")

                # Check for circular references in FinishedGood components
                for comp in compositions:
                    if comp.finished_good_id:
                        if not CompositionService.validate_no_circular_reference(
                            assembly_id, comp.finished_good_id, session
                        ):
                            issues.append(
                                f"Circular reference detected with FinishedGood {comp.finished_good_id}"
                            )

                result = {
                    "assembly_id": assembly_id,
                    "is_valid": len(issues) == 0,
                    "issues_count": len(issues),
                    "warnings_count": len(warnings),
                    "issues": issues,
                    "warnings": warnings,
                    "total_compositions": len(compositions),
                    "checked_at": datetime.utcnow().isoformat(),
                }

                logger.debug(
                    f"Integrity check for assembly {assembly_id}: {len(issues)} issues found"
                )
                return result

        except SQLAlchemyError as e:
            logger.error(f"Database error checking composition integrity: {e}")
            raise DatabaseError(f"Failed to check composition integrity: {e}")

    # Bulk Operations

    @staticmethod
    def bulk_create_compositions(compositions: List[dict]) -> List[Composition]:
        """
        Create multiple composition relationships efficiently.

        Args:
            compositions: List of composition specification dictionaries

        Returns:
            List of created Composition instances

        Raises:
            ValidationError: If any composition is invalid

        Performance:
            Must complete in <1s for up to 100 compositions per contract
        """
        try:
            if not compositions:
                return []

            created_compositions = []

            with session_scope() as session:
                # Validate all compositions first
                for comp_spec in compositions:
                    # Validate required fields
                    required_fields = ["assembly_id", "component_type", "component_id", "quantity"]
                    for field in required_fields:
                        if field not in comp_spec:
                            raise ValidationError(
                                f"Missing required field '{field}' in composition spec"
                            )

                    assembly_id = comp_spec["assembly_id"]
                    component_type = comp_spec["component_type"]
                    component_id = comp_spec["component_id"]
                    quantity = comp_spec["quantity"]

                    if component_type not in ["finished_unit", "finished_good"]:
                        raise InvalidComponentTypeError(
                            f"Invalid component_type '{component_type}'"
                        )

                    if quantity <= 0:
                        raise ValidationError("Quantity must be positive")

                    # Validate assembly exists
                    assembly = (
                        session.query(FinishedGood).filter(FinishedGood.id == assembly_id).first()
                    )
                    if not assembly:
                        raise ValidationError(f"Assembly ID {assembly_id} not found")

                    # Validate component exists
                    if not CompositionService.validate_component_exists(
                        component_type, component_id, session
                    ):
                        raise ValidationError(
                            f"Component {component_type} ID {component_id} not found"
                        )

                    # Check circular references for FinishedGood components
                    if component_type == "finished_good":
                        if not CompositionService.validate_no_circular_reference(
                            assembly_id, component_id, session
                        ):
                            raise CircularReferenceError(
                                f"Adding component {component_id} would create circular reference"
                            )

                # Create all compositions
                for comp_spec in compositions:
                    composition_data = {
                        "assembly_id": comp_spec["assembly_id"],
                        "component_quantity": comp_spec["quantity"],
                        "component_notes": comp_spec.get("notes"),
                        "sort_order": comp_spec.get("sort_order", 0),
                    }

                    if comp_spec["component_type"] == "finished_unit":
                        composition_data["finished_unit_id"] = comp_spec["component_id"]
                    else:
                        composition_data["finished_good_id"] = comp_spec["component_id"]

                    composition = Composition(**composition_data)
                    session.add(composition)
                    created_compositions.append(composition)

                session.flush()

                logger.info(f"Bulk created {len(created_compositions)} compositions")
                return created_compositions

        except SQLAlchemyError as e:
            logger.error(f"Database error bulk creating compositions: {e}")
            raise DatabaseError(f"Failed to bulk create compositions: {e}")

    @staticmethod
    def reorder_assembly_components(assembly_id: int, new_order: List[int]) -> bool:
        """
        Update sort order for all components in an assembly.

        Args:
            assembly_id: ID of the assembly
            new_order: List of composition_ids in desired order

        Returns:
            True if reordered successfully

        Performance:
            Must complete in <500ms per contract
        """
        try:
            with session_scope() as session:
                # Get all compositions for the assembly
                compositions = (
                    session.query(Composition).filter(Composition.assembly_id == assembly_id).all()
                )

                composition_dict = {comp.id: comp for comp in compositions}

                # Validate all composition IDs in new_order exist
                for comp_id in new_order:
                    if comp_id not in composition_dict:
                        raise ValidationError(
                            f"Composition ID {comp_id} not found in assembly {assembly_id}"
                        )

                # Check if all compositions are included
                if set(new_order) != set(composition_dict.keys()):
                    raise ValidationError(
                        "new_order must include all composition IDs for the assembly"
                    )

                # Update sort orders
                for index, comp_id in enumerate(new_order):
                    composition_dict[comp_id].sort_order = index

                session.flush()

                logger.info(f"Reordered {len(new_order)} components for assembly {assembly_id}")
                return True

        except SQLAlchemyError as e:
            logger.error(f"Database error reordering assembly components: {e}")
            raise DatabaseError(f"Failed to reorder assembly components: {e}")

    @staticmethod
    def copy_assembly_composition(source_assembly_id: int, target_assembly_id: int) -> bool:
        """
        Copy all component relationships from one assembly to another.

        Args:
            source_assembly_id: ID of assembly to copy from
            target_assembly_id: ID of assembly to copy to

        Returns:
            True if copied successfully

        Raises:
            CircularReferenceError: If copy would create circular references

        Performance:
            Must complete in <1s per contract
        """
        try:
            with session_scope() as session:
                # Validate both assemblies exist
                source_assembly = (
                    session.query(FinishedGood)
                    .filter(FinishedGood.id == source_assembly_id)
                    .first()
                )
                if not source_assembly:
                    raise ValidationError(f"Source assembly ID {source_assembly_id} not found")

                target_assembly = (
                    session.query(FinishedGood)
                    .filter(FinishedGood.id == target_assembly_id)
                    .first()
                )
                if not target_assembly:
                    raise ValidationError(f"Target assembly ID {target_assembly_id} not found")

                # Get source compositions
                source_compositions = CompositionService.get_assembly_components(source_assembly_id)

                # Validate no circular references would be created
                for comp in source_compositions:
                    if comp.finished_good_id:
                        if not CompositionService.validate_no_circular_reference(
                            target_assembly_id, comp.finished_good_id, session
                        ):
                            raise CircularReferenceError(
                                f"Copying component {comp.finished_good_id} would create circular reference"
                            )

                # Copy compositions
                copied_count = 0
                for comp in source_compositions:
                    composition_data = {
                        "assembly_id": target_assembly_id,
                        "component_quantity": comp.component_quantity,
                        "component_notes": comp.component_notes,
                        "sort_order": comp.sort_order,
                    }

                    if comp.finished_unit_id:
                        composition_data["finished_unit_id"] = comp.finished_unit_id
                    elif comp.finished_good_id:
                        composition_data["finished_good_id"] = comp.finished_good_id

                    new_composition = Composition(**composition_data)
                    session.add(new_composition)
                    copied_count += 1

                session.flush()

                logger.info(
                    f"Copied {copied_count} compositions from assembly {source_assembly_id} to {target_assembly_id}"
                )
                return True

        except SQLAlchemyError as e:
            logger.error(f"Database error copying assembly composition: {e}")
            raise DatabaseError(f"Failed to copy assembly composition: {e}")

    # Cost and Quantity Calculations

    @staticmethod
    def calculate_assembly_component_costs(assembly_id: int) -> dict:
        """
        Calculate total cost contribution of each component type.

        Args:
            assembly_id: ID of the assembly

        Returns:
            Dictionary with cost breakdown by component

        Performance:
            Must complete in <400ms per contract
        """
        try:
            with get_db_session() as session:
                compositions = CompositionService.get_assembly_components(assembly_id)

                cost_breakdown = {
                    "finished_unit_costs": [],
                    "finished_good_costs": [],
                    "total_finished_unit_cost": Decimal("0.0000"),
                    "total_finished_good_cost": Decimal("0.0000"),
                    "total_assembly_cost": Decimal("0.0000"),
                }

                for comp in compositions:
                    if comp.finished_unit_component:
                        unit = comp.finished_unit_component
                        component_total = unit.unit_cost * comp.component_quantity

                        cost_breakdown["finished_unit_costs"].append(
                            {
                                "composition_id": comp.id,
                                "component_id": unit.id,
                                "display_name": unit.display_name,
                                "unit_cost": float(unit.unit_cost),
                                "quantity": comp.component_quantity,
                                "total_cost": float(component_total),
                            }
                        )

                        cost_breakdown["total_finished_unit_cost"] += component_total

                    elif comp.finished_good_component:
                        subassembly = comp.finished_good_component
                        component_total = subassembly.total_cost * comp.component_quantity

                        cost_breakdown["finished_good_costs"].append(
                            {
                                "composition_id": comp.id,
                                "component_id": subassembly.id,
                                "display_name": subassembly.display_name,
                                "unit_cost": float(subassembly.total_cost),
                                "quantity": comp.component_quantity,
                                "total_cost": float(component_total),
                            }
                        )

                        cost_breakdown["total_finished_good_cost"] += component_total

                cost_breakdown["total_assembly_cost"] = (
                    cost_breakdown["total_finished_unit_cost"]
                    + cost_breakdown["total_finished_good_cost"]
                )

                # Convert Decimal to float for JSON serialization
                cost_breakdown["total_finished_unit_cost"] = float(
                    cost_breakdown["total_finished_unit_cost"]
                )
                cost_breakdown["total_finished_good_cost"] = float(
                    cost_breakdown["total_finished_good_cost"]
                )
                cost_breakdown["total_assembly_cost"] = float(cost_breakdown["total_assembly_cost"])

                logger.debug(f"Calculated component costs for assembly {assembly_id}")
                return cost_breakdown

        except SQLAlchemyError as e:
            logger.error(f"Database error calculating component costs: {e}")
            raise DatabaseError(f"Failed to calculate component costs: {e}")

    @staticmethod
    def calculate_required_inventory(assembly_id: int, assembly_quantity: int) -> dict:
        """
        Calculate total inventory needed for assembly production.

        Args:
            assembly_id: ID of the assembly
            assembly_quantity: Number of assemblies to produce

        Returns:
            Dictionary of component requirements

        Performance:
            Must complete in <300ms per contract
        """
        try:
            # Use the flattened components to get total requirements
            flattened_components = CompositionService.flatten_assembly_components(assembly_id)

            requirements = {
                "assembly_id": assembly_id,
                "assembly_quantity": assembly_quantity,
                "finished_unit_requirements": [],
                "finished_good_requirements": [],
                "availability_status": "available",
            }

            for component in flattened_components:
                required_quantity = component["total_quantity"] * assembly_quantity
                available_quantity = component["inventory_count"]
                shortage = max(0, required_quantity - available_quantity)

                requirement = {
                    "component_id": component["component_id"],
                    "display_name": component["display_name"],
                    "required_quantity": required_quantity,
                    "available_quantity": available_quantity,
                    "shortage": shortage,
                    "is_sufficient": shortage == 0,
                }

                if component["component_type"] == "finished_unit":
                    requirements["finished_unit_requirements"].append(requirement)
                else:
                    requirements["finished_good_requirements"].append(requirement)

                if shortage > 0:
                    requirements["availability_status"] = "insufficient"

            logger.debug(
                f"Calculated inventory requirements for {assembly_quantity} assemblies of {assembly_id}"
            )
            return requirements

        except SQLAlchemyError as e:
            logger.error(f"Database error calculating inventory requirements: {e}")
            raise DatabaseError(f"Failed to calculate inventory requirements: {e}")

    # Query Utilities

    @staticmethod
    def search_compositions_by_component(search_term: str) -> List[Composition]:
        """
        Find compositions involving components matching search term.

        Args:
            search_term: String to search in component names

        Returns:
            List of matching Composition instances

        Performance:
            Must complete in <400ms per contract
        """
        try:
            if not search_term or not search_term.strip():
                return []

            search_pattern = f"%{search_term.strip().lower()}%"

            with get_db_session() as session:
                # Search in both FinishedUnit and FinishedGood components
                compositions = (
                    session.query(Composition)
                    .options(
                        selectinload(Composition.finished_unit_component),
                        selectinload(Composition.finished_good_component),
                        selectinload(Composition.assembly),
                    )
                    .outerjoin(Composition.finished_unit_component)
                    .outerjoin(Composition.finished_good_component)
                    .filter(
                        or_(
                            FinishedUnit.display_name.ilike(search_pattern),
                            FinishedUnit.description.ilike(search_pattern),
                            FinishedGood.display_name.ilike(search_pattern),
                            FinishedGood.description.ilike(search_pattern),
                        )
                    )
                    .all()
                )

                logger.debug(f"Found {len(compositions)} compositions matching '{search_term}'")
                return compositions

        except SQLAlchemyError as e:
            logger.error(f"Database error searching compositions: {e}")
            raise DatabaseError(f"Failed to search compositions: {e}")

    @staticmethod
    def get_assembly_statistics(assembly_id: int) -> dict:
        """
        Get statistical information about an assembly's composition.

        Args:
            assembly_id: ID of the assembly

        Returns:
            Dictionary with component counts, costs, hierarchy depth, etc.

        Performance:
            Must complete in <200ms per contract
        """
        try:
            with get_db_session() as session:
                # Get direct components
                direct_components = CompositionService.get_assembly_components(assembly_id)

                # Get flattened components for totals
                flattened_components = CompositionService.flatten_assembly_components(assembly_id)

                # Calculate hierarchy depth
                max_depth = 0
                queue = deque([(assembly_id, 0)])
                visited = set()

                while queue:
                    current_id, depth = queue.popleft()

                    if current_id in visited:
                        continue
                    visited.add(current_id)

                    max_depth = max(max_depth, depth)

                    # Get FinishedGood components to continue traversal
                    subassemblies = (
                        session.query(Composition)
                        .filter(
                            Composition.assembly_id == current_id,
                            Composition.finished_good_id.isnot(None),
                        )
                        .all()
                    )

                    for sub in subassemblies:
                        queue.append((sub.finished_good_id, depth + 1))

                # Count component types
                direct_finished_units = sum(
                    1 for comp in direct_components if comp.finished_unit_id
                )
                direct_finished_goods = sum(
                    1 for comp in direct_components if comp.finished_good_id
                )

                total_finished_units = sum(
                    1 for comp in flattened_components if comp["component_type"] == "finished_unit"
                )
                total_finished_goods = sum(
                    1 for comp in flattened_components if comp["component_type"] == "finished_good"
                )

                # Calculate costs
                cost_breakdown = CompositionService.calculate_assembly_component_costs(assembly_id)

                statistics = {
                    "assembly_id": assembly_id,
                    "direct_components_count": len(direct_components),
                    "direct_finished_units": direct_finished_units,
                    "direct_finished_goods": direct_finished_goods,
                    "total_unique_components": len(flattened_components),
                    "total_finished_units": total_finished_units,
                    "total_finished_goods": total_finished_goods,
                    "hierarchy_depth": max_depth,
                    "total_cost": cost_breakdown["total_assembly_cost"],
                    "finished_unit_cost": cost_breakdown["total_finished_unit_cost"],
                    "finished_good_cost": cost_breakdown["total_finished_good_cost"],
                    "calculated_at": datetime.utcnow().isoformat(),
                }

                logger.debug(f"Generated statistics for assembly {assembly_id}")
                return statistics

        except SQLAlchemyError as e:
            logger.error(f"Database error generating assembly statistics: {e}")
            raise DatabaseError(f"Failed to generate assembly statistics: {e}")

    # Cache Management

    @staticmethod
    def get_cache_statistics() -> dict:
        """
        Get statistics about the hierarchy cache for monitoring.

        Returns:
            Dictionary with cache size and hit rate information
        """
        return {
            "cache_size": _hierarchy_cache.size(),
            "cache_ttl_seconds": _hierarchy_cache.ttl,
            "cache_type": "hierarchy_operations",
        }

    @staticmethod
    def clear_hierarchy_cache(assembly_id: Optional[int] = None) -> bool:
        """
        Clear hierarchy cache entries.

        Args:
            assembly_id: If provided, clear only entries for this assembly

        Returns:
            True if cache was cleared
        """
        try:
            if assembly_id is not None:
                _hierarchy_cache.invalidate(f"hierarchy_{assembly_id}_")
                logger.info(f"Cleared hierarchy cache for assembly {assembly_id}")
            else:
                _hierarchy_cache.invalidate()
                logger.info("Cleared all hierarchy cache entries")
            return True
        except Exception as e:
            logger.error(f"Error clearing hierarchy cache: {e}")
            return False


# Module-level convenience functions for backward compatibility


def create_composition(
    assembly_id: int, component_type: str, component_id: int, quantity: int, **kwargs
) -> Composition:
    """Create a new composition relationship."""
    return CompositionService.create_composition(
        assembly_id, component_type, component_id, quantity, **kwargs
    )


def get_composition_by_id(composition_id: int) -> Optional[Composition]:
    """Retrieve a specific composition by ID."""
    return CompositionService.get_composition_by_id(composition_id)


def get_assembly_components(assembly_id: int, ordered: bool = True) -> List[Composition]:
    """Get all direct components of an assembly."""
    return CompositionService.get_assembly_components(assembly_id, ordered)


def get_component_usages(component_type: str, component_id: int) -> List[Composition]:
    """Find all assemblies that use a specific component."""
    return CompositionService.get_component_usages(component_type, component_id)


def validate_no_circular_reference(assembly_id: int, new_component_id: int) -> bool:
    """Check if adding a component would create circular dependency."""
    return CompositionService.validate_no_circular_reference(assembly_id, new_component_id)


def flatten_assembly_components(assembly_id: int) -> List[dict]:
    """Get flattened list of all components at all hierarchy levels."""
    return CompositionService.flatten_assembly_components(assembly_id)
