"""
Package Service - Business logic for packages.

This service provides CRUD operations for:
- Packages (gift packages containing FinishedGood assemblies)
- PackageFinishedGood relationships (FinishedGoods within packages)

Architecture Note (Feature 006):
- Bundle concept eliminated per research decision D1
- Package now references FinishedGood assemblies directly via PackageFinishedGood
- Cost calculation chains to FinishedGood.total_cost for FIFO accuracy
"""

from decimal import Decimal
from typing import List, Optional, Dict, Any
from datetime import datetime

from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload

from src.models import (
    Package,
    PackageFinishedGood,
    FinishedGood,
    EventRecipientPackage,
)
from src.services.database import session_scope
from src.services.exceptions import (
    DatabaseError,
    ValidationError,
)


# ============================================================================
# Custom Exceptions
# ============================================================================


class PackageNotFoundError(Exception):
    """Raised when a package is not found."""

    def __init__(self, package_id: int):
        self.package_id = package_id
        super().__init__(f"Package with ID {package_id} not found")


class PackageInUseError(Exception):
    """Raised when trying to delete a package that's used in events."""

    def __init__(self, package_id: int, event_count: int):
        self.package_id = package_id
        self.event_count = event_count
        super().__init__(
            f"Package {package_id} is assigned to {event_count} event(s)"
        )


class InvalidFinishedGoodError(Exception):
    """Raised when a FinishedGood is not found."""

    def __init__(self, finished_good_id: int):
        self.finished_good_id = finished_good_id
        super().__init__(f"FinishedGood with ID {finished_good_id} not found")


class DuplicatePackageNameError(Exception):
    """Raised when a package with the same name already exists."""

    def __init__(self, name: str):
        self.name = name
        super().__init__(f"Package with name '{name}' already exists")


class PackageFinishedGoodNotFoundError(Exception):
    """Raised when a PackageFinishedGood junction is not found."""

    def __init__(self, package_id: int, finished_good_id: int):
        self.package_id = package_id
        self.finished_good_id = finished_good_id
        super().__init__(
            f"FinishedGood {finished_good_id} not found in Package {package_id}"
        )


# ============================================================================
# Package CRUD Operations
# ============================================================================


def create_package(
    name: str,
    is_template: bool = False,
    description: Optional[str] = None,
    notes: Optional[str] = None,
) -> Package:
    """
    Create a new package.

    Args:
        name: Package name (required)
        is_template: Whether this is a template for reuse
        description: Optional description
        notes: Optional notes

    Returns:
        Created Package instance

    Raises:
        ValidationError: If name is empty
        DatabaseError: If database operation fails
    """
    if not name or not name.strip():
        raise ValidationError(["Package name is required"])

    try:
        with session_scope() as session:
            package = Package(
                name=name.strip(),
                description=description,
                is_template=is_template,
                notes=notes,
            )
            session.add(package)
            session.flush()

            # Reload with relationships
            package = (
                session.query(Package)
                .options(
                    joinedload(Package.package_finished_goods).joinedload(
                        PackageFinishedGood.finished_good
                    )
                )
                .filter(Package.id == package.id)
                .one()
            )

            return package

    except ValidationError:
        raise
    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to create package: {str(e)}")


def get_package_by_id(package_id: int) -> Optional[Package]:
    """
    Get a package by ID.

    Args:
        package_id: Package ID

    Returns:
        Package instance or None if not found
    """
    try:
        with session_scope() as session:
            package = (
                session.query(Package)
                .options(
                    joinedload(Package.package_finished_goods).joinedload(
                        PackageFinishedGood.finished_good
                    )
                )
                .filter(Package.id == package_id)
                .first()
            )
            return package

    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to get package: {str(e)}")


def get_package_by_name(name: str) -> Optional[Package]:
    """
    Get a package by exact name match.

    Args:
        name: Package name

    Returns:
        Package instance or None if not found
    """
    try:
        with session_scope() as session:
            package = (
                session.query(Package)
                .options(
                    joinedload(Package.package_finished_goods).joinedload(
                        PackageFinishedGood.finished_good
                    )
                )
                .filter(Package.name == name)
                .first()
            )
            return package

    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to get package by name: {str(e)}")


def get_all_packages(include_templates: bool = True) -> List[Package]:
    """
    Get all packages with optional template filter.

    Args:
        include_templates: If False, exclude templates from results

    Returns:
        List of Package instances
    """
    try:
        with session_scope() as session:
            query = session.query(Package).options(
                joinedload(Package.package_finished_goods).joinedload(
                    PackageFinishedGood.finished_good
                )
            )

            if not include_templates:
                query = query.filter(Package.is_template == False)

            query = query.order_by(Package.name)
            return query.all()

    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to get packages: {str(e)}")


def update_package(package_id: int, **updates) -> Package:
    """
    Update an existing package.

    Args:
        package_id: Package ID to update
        **updates: Field updates (name, description, is_template, notes)

    Returns:
        Updated Package instance

    Raises:
        PackageNotFoundError: If package not found
        ValidationError: If data validation fails
        DatabaseError: If database operation fails
    """
    try:
        with session_scope() as session:
            package = session.query(Package).filter(Package.id == package_id).first()
            if not package:
                raise PackageNotFoundError(package_id)

            # Update fields
            if "name" in updates:
                name = updates["name"]
                if not name or not name.strip():
                    raise ValidationError(["Package name is required"])
                package.name = name.strip()

            if "description" in updates:
                package.description = updates["description"]

            if "is_template" in updates:
                package.is_template = updates["is_template"]

            if "notes" in updates:
                package.notes = updates["notes"]

            package.last_modified = datetime.utcnow()
            session.flush()

            # Reload with relationships
            package = (
                session.query(Package)
                .options(
                    joinedload(Package.package_finished_goods).joinedload(
                        PackageFinishedGood.finished_good
                    )
                )
                .filter(Package.id == package.id)
                .one()
            )

            return package

    except (PackageNotFoundError, ValidationError):
        raise
    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to update package: {str(e)}")


def delete_package(package_id: int) -> bool:
    """
    Delete a package.

    Args:
        package_id: Package ID to delete

    Returns:
        True if deleted successfully

    Raises:
        PackageNotFoundError: If package not found
        PackageInUseError: If package is used in events (FR-015)
        DatabaseError: If database operation fails
    """
    try:
        with session_scope() as session:
            package = session.query(Package).filter(Package.id == package_id).first()
            if not package:
                raise PackageNotFoundError(package_id)

            # Check for event assignments (FR-015)
            event_count = (
                session.query(EventRecipientPackage)
                .filter(EventRecipientPackage.package_id == package_id)
                .count()
            )
            if event_count > 0:
                raise PackageInUseError(package_id, event_count)

            # Delete package (cascade will delete PackageFinishedGood records)
            session.delete(package)
            return True

    except (PackageNotFoundError, PackageInUseError):
        raise
    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to delete package: {str(e)}")


# ============================================================================
# Package Content Management (FinishedGood operations)
# ============================================================================


def add_finished_good_to_package(
    package_id: int, finished_good_id: int, quantity: int = 1
) -> PackageFinishedGood:
    """
    Add a FinishedGood to a package.

    Args:
        package_id: Package ID
        finished_good_id: FinishedGood ID to add
        quantity: Quantity (default 1)

    Returns:
        Created PackageFinishedGood junction

    Raises:
        PackageNotFoundError: If package not found
        InvalidFinishedGoodError: If FinishedGood not found
        ValidationError: If quantity < 1
        DatabaseError: If database operation fails
    """
    if quantity < 1:
        raise ValidationError(["Quantity must be at least 1"])

    try:
        with session_scope() as session:
            # Verify package exists
            package = session.query(Package).filter(Package.id == package_id).first()
            if not package:
                raise PackageNotFoundError(package_id)

            # Verify FinishedGood exists
            fg = (
                session.query(FinishedGood)
                .filter(FinishedGood.id == finished_good_id)
                .first()
            )
            if not fg:
                raise InvalidFinishedGoodError(finished_good_id)

            # Check if already in package - update quantity instead
            existing = (
                session.query(PackageFinishedGood)
                .filter(
                    PackageFinishedGood.package_id == package_id,
                    PackageFinishedGood.finished_good_id == finished_good_id,
                )
                .first()
            )

            if existing:
                existing.quantity += quantity
                session.flush()
                return existing

            # Create new junction
            pfg = PackageFinishedGood(
                package_id=package_id,
                finished_good_id=finished_good_id,
                quantity=quantity,
            )
            session.add(pfg)
            session.flush()

            # Update package last_modified
            package.last_modified = datetime.utcnow()

            return pfg

    except (PackageNotFoundError, InvalidFinishedGoodError, ValidationError):
        raise
    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to add FinishedGood to package: {str(e)}")


def remove_finished_good_from_package(
    package_id: int, finished_good_id: int
) -> bool:
    """
    Remove a FinishedGood from a package.

    Args:
        package_id: Package ID
        finished_good_id: FinishedGood ID to remove

    Returns:
        True if removed successfully

    Raises:
        PackageNotFoundError: If package not found
        PackageFinishedGoodNotFoundError: If FinishedGood not in package
        DatabaseError: If database operation fails
    """
    try:
        with session_scope() as session:
            # Verify package exists
            package = session.query(Package).filter(Package.id == package_id).first()
            if not package:
                raise PackageNotFoundError(package_id)

            # Find junction
            pfg = (
                session.query(PackageFinishedGood)
                .filter(
                    PackageFinishedGood.package_id == package_id,
                    PackageFinishedGood.finished_good_id == finished_good_id,
                )
                .first()
            )

            if not pfg:
                raise PackageFinishedGoodNotFoundError(package_id, finished_good_id)

            session.delete(pfg)
            package.last_modified = datetime.utcnow()
            return True

    except (PackageNotFoundError, PackageFinishedGoodNotFoundError):
        raise
    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to remove FinishedGood from package: {str(e)}")


def update_finished_good_quantity(
    package_id: int, finished_good_id: int, quantity: int
) -> PackageFinishedGood:
    """
    Update the quantity of a FinishedGood in a package.

    Args:
        package_id: Package ID
        finished_good_id: FinishedGood ID
        quantity: New quantity

    Returns:
        Updated PackageFinishedGood junction

    Raises:
        PackageNotFoundError: If package not found
        PackageFinishedGoodNotFoundError: If FinishedGood not in package
        ValidationError: If quantity < 1
        DatabaseError: If database operation fails
    """
    if quantity < 1:
        raise ValidationError(["Quantity must be at least 1"])

    try:
        with session_scope() as session:
            # Verify package exists
            package = session.query(Package).filter(Package.id == package_id).first()
            if not package:
                raise PackageNotFoundError(package_id)

            # Find junction
            pfg = (
                session.query(PackageFinishedGood)
                .filter(
                    PackageFinishedGood.package_id == package_id,
                    PackageFinishedGood.finished_good_id == finished_good_id,
                )
                .first()
            )

            if not pfg:
                raise PackageFinishedGoodNotFoundError(package_id, finished_good_id)

            pfg.quantity = quantity
            package.last_modified = datetime.utcnow()
            session.flush()
            return pfg

    except (PackageNotFoundError, PackageFinishedGoodNotFoundError, ValidationError):
        raise
    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to update quantity: {str(e)}")


def get_package_contents(package_id: int) -> List[Dict[str, Any]]:
    """
    Get contents of a package with cost details.

    Args:
        package_id: Package ID

    Returns:
        List of dicts with finished_good, quantity, item_cost, line_total

    Raises:
        PackageNotFoundError: If package not found
        DatabaseError: If database operation fails
    """
    try:
        with session_scope() as session:
            package = (
                session.query(Package)
                .options(
                    joinedload(Package.package_finished_goods).joinedload(
                        PackageFinishedGood.finished_good
                    )
                )
                .filter(Package.id == package_id)
                .first()
            )

            if not package:
                raise PackageNotFoundError(package_id)

            result = []
            for pfg in package.package_finished_goods:
                fg = pfg.finished_good
                item_cost = fg.total_cost or Decimal("0.00")
                result.append(
                    {
                        "finished_good_id": fg.id,
                        "finished_good_name": fg.display_name,
                        "finished_good_slug": fg.slug,
                        "quantity": pfg.quantity,
                        "item_cost": item_cost,
                        "line_total": item_cost * Decimal(str(pfg.quantity)),
                    }
                )

            return result

    except PackageNotFoundError:
        raise
    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to get package contents: {str(e)}")


# ============================================================================
# Cost Calculation
# ============================================================================


def calculate_package_cost(package_id: int) -> Decimal:
    """
    Calculate total cost of a package using FIFO-accurate pricing.

    Cost chains through: Package -> PackageFinishedGood -> FinishedGood.total_cost

    Args:
        package_id: Package ID

    Returns:
        Total cost as Decimal

    Raises:
        PackageNotFoundError: If package not found
        DatabaseError: If database operation fails
    """
    try:
        with session_scope() as session:
            package = (
                session.query(Package)
                .options(
                    joinedload(Package.package_finished_goods).joinedload(
                        PackageFinishedGood.finished_good
                    )
                )
                .filter(Package.id == package_id)
                .first()
            )

            if not package:
                raise PackageNotFoundError(package_id)

            return package.calculate_cost()

    except PackageNotFoundError:
        raise
    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to calculate package cost: {str(e)}")


def get_package_cost_breakdown(package_id: int) -> Dict[str, Any]:
    """
    Get detailed cost breakdown for a package.

    Args:
        package_id: Package ID

    Returns:
        Dict with items list and total cost

    Raises:
        PackageNotFoundError: If package not found
        DatabaseError: If database operation fails
    """
    contents = get_package_contents(package_id)
    total = sum(item["line_total"] for item in contents)

    return {"items": contents, "total": total}


# ============================================================================
# Search and Query Operations
# ============================================================================


def search_packages(query: str) -> List[Package]:
    """
    Search packages by name or description.

    Args:
        query: Search string

    Returns:
        List of matching packages
    """
    try:
        with session_scope() as session:
            packages = (
                session.query(Package)
                .options(
                    joinedload(Package.package_finished_goods).joinedload(
                        PackageFinishedGood.finished_good
                    )
                )
                .filter(
                    or_(
                        Package.name.ilike(f"%{query}%"),
                        Package.description.ilike(f"%{query}%"),
                    )
                )
                .order_by(Package.name)
                .all()
            )
            return packages

    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to search packages: {str(e)}")


def get_template_packages() -> List[Package]:
    """
    Get all template packages.

    Returns:
        List of packages marked as templates
    """
    try:
        with session_scope() as session:
            packages = (
                session.query(Package)
                .options(
                    joinedload(Package.package_finished_goods).joinedload(
                        PackageFinishedGood.finished_good
                    )
                )
                .filter(Package.is_template == True)
                .order_by(Package.name)
                .all()
            )
            return packages

    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to get template packages: {str(e)}")


# ============================================================================
# Dependency Checking
# ============================================================================


def get_packages_containing_finished_good(finished_good_id: int) -> List[Package]:
    """
    Find all packages that contain a specific FinishedGood.

    Useful for dependency checking before FinishedGood deletion.

    Args:
        finished_good_id: FinishedGood ID to search for

    Returns:
        List of packages containing the FinishedGood
    """
    try:
        with session_scope() as session:
            packages = (
                session.query(Package)
                .join(PackageFinishedGood)
                .filter(PackageFinishedGood.finished_good_id == finished_good_id)
                .all()
            )
            return packages

    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to find packages: {str(e)}")


def check_package_has_event_assignments(package_id: int) -> bool:
    """
    Check if a package is assigned to any events.

    Used for deletion protection (FR-015).

    Args:
        package_id: Package ID to check

    Returns:
        True if package has event assignments
    """
    try:
        with session_scope() as session:
            count = (
                session.query(EventRecipientPackage)
                .filter(EventRecipientPackage.package_id == package_id)
                .count()
            )
            return count > 0

    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to check package assignments: {str(e)}")


def get_package_event_assignment_count(package_id: int) -> int:
    """
    Get count of event assignments for a package.

    Args:
        package_id: Package ID to check

    Returns:
        Number of event assignments
    """
    try:
        with session_scope() as session:
            count = (
                session.query(EventRecipientPackage)
                .filter(EventRecipientPackage.package_id == package_id)
                .count()
            )
            return count

    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to count package assignments: {str(e)}")


# ============================================================================
# Duplication
# ============================================================================


def duplicate_package(package_id: int, new_name: str) -> Package:
    """
    Create a copy of a package with all its contents.

    Args:
        package_id: Package ID to duplicate
        new_name: Name for the new package

    Returns:
        New Package instance with copied contents

    Raises:
        PackageNotFoundError: If original package not found
        ValidationError: If new_name is empty
        DatabaseError: If database operation fails
    """
    if not new_name or not new_name.strip():
        raise ValidationError(["New package name is required"])

    try:
        with session_scope() as session:
            # Get original package
            original = (
                session.query(Package)
                .options(
                    joinedload(Package.package_finished_goods).joinedload(
                        PackageFinishedGood.finished_good
                    )
                )
                .filter(Package.id == package_id)
                .first()
            )

            if not original:
                raise PackageNotFoundError(package_id)

            # Create new package
            new_package = Package(
                name=new_name.strip(),
                description=original.description,
                is_template=False,  # Copies are not templates
                notes=original.notes,
            )
            session.add(new_package)
            session.flush()

            # Copy contents
            for pfg in original.package_finished_goods:
                new_pfg = PackageFinishedGood(
                    package_id=new_package.id,
                    finished_good_id=pfg.finished_good_id,
                    quantity=pfg.quantity,
                )
                session.add(new_pfg)

            session.flush()

            # Reload with relationships
            new_package = (
                session.query(Package)
                .options(
                    joinedload(Package.package_finished_goods).joinedload(
                        PackageFinishedGood.finished_good
                    )
                )
                .filter(Package.id == new_package.id)
                .one()
            )

            return new_package

    except (PackageNotFoundError, ValidationError):
        raise
    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to duplicate package: {str(e)}")
