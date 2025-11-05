"""
Package Service - Business logic for packages.

This service provides CRUD operations for:
- Packages (gift packages containing bundles)
- PackageBundle relationships (bundles within packages)
"""

from typing import List, Optional, Dict
from datetime import datetime

from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload

from src.models import Package, PackageBundle, Bundle, FinishedGood, Recipe, RecipeIngredient
from src.services.database import session_scope
from src.services.exceptions import (
    DatabaseError,
    ValidationError,
)


# ============================================================================
# Custom Exceptions
# ============================================================================


class PackageNotFound(Exception):
    """Raised when a package is not found."""
    def __init__(self, package_id: int):
        self.package_id = package_id
        super().__init__(f"Package with ID {package_id} not found")


class PackageInUse(Exception):
    """Raised when trying to delete a package that's used in events."""
    def __init__(self, package_id: int, event_count: int):
        self.package_id = package_id
        self.event_count = event_count
        super().__init__(
            f"Package {package_id} is used in {event_count} event(s)"
        )


# ============================================================================
# Package CRUD Operations
# ============================================================================


def create_package(data: Dict, bundle_items: Optional[List[Dict]] = None) -> Package:
    """
    Create a new package with optional bundles.

    Args:
        data: Dictionary with package fields
        bundle_items: List of dictionaries with bundle_id and quantity

    Returns:
        Created Package instance

    Raises:
        ValidationError: If data validation fails
        DatabaseError: If database operation fails
    """
    # Validate required fields
    errors = []

    if not data.get("name"):
        errors.append("Name is required")

    if errors:
        raise ValidationError(errors)

    try:
        with session_scope() as session:
            # Create package
            package = Package(
                name=data["name"],
                description=data.get("description"),
                is_template=data.get("is_template", False),
                notes=data.get("notes"),
            )

            session.add(package)
            session.flush()  # Get package ID

            # Add bundles if provided
            if bundle_items:
                for item in bundle_items:
                    bundle_id = item.get("bundle_id")
                    quantity = item.get("quantity", 1)

                    # Validate bundle exists
                    bundle = session.query(Bundle).filter(Bundle.id == bundle_id).first()
                    if not bundle:
                        raise ValidationError([f"Bundle with ID {bundle_id} not found"])

                    # Create PackageBundle
                    pb = PackageBundle(
                        package_id=package.id,
                        bundle_id=bundle_id,
                        quantity=quantity
                    )
                    session.add(pb)

            session.commit()

            # Reload with all nested relationships eagerly loaded
            package = session.query(Package).options(
                joinedload(Package.package_bundles)
                .joinedload(PackageBundle.bundle)
                .joinedload(Bundle.finished_good)
                .joinedload(FinishedGood.recipe)
                .joinedload(Recipe.recipe_ingredients)
                .joinedload(RecipeIngredient.ingredient)
            ).filter(Package.id == package.id).one()

            return package

    except ValidationError:
        raise
    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to create package: {str(e)}")


def get_package(package_id: int) -> Package:
    """
    Get a package by ID.

    Args:
        package_id: Package ID

    Returns:
        Package instance

    Raises:
        PackageNotFound: If package not found
        DatabaseError: If database operation fails
    """
    try:
        with session_scope() as session:
            package = session.query(Package).options(
                joinedload(Package.package_bundles)
                .joinedload(PackageBundle.bundle)
                .joinedload(Bundle.finished_good)
                .joinedload(FinishedGood.recipe)
                .joinedload(Recipe.recipe_ingredients)
                .joinedload(RecipeIngredient.ingredient)
            ).filter(Package.id == package_id).first()

            if not package:
                raise PackageNotFound(package_id)

            return package

    except PackageNotFound:
        raise
    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to get package: {str(e)}")


def get_all_packages(
    name_search: Optional[str] = None,
    is_template: Optional[bool] = None
) -> List[Package]:
    """
    Get all packages with optional filters.

    Args:
        name_search: Optional name filter (partial match)
        is_template: Optional filter for templates

    Returns:
        List of Package instances

    Raises:
        DatabaseError: If database operation fails
    """
    try:
        with session_scope() as session:
            query = session.query(Package).options(
                joinedload(Package.package_bundles)
                .joinedload(PackageBundle.bundle)
                .joinedload(Bundle.finished_good)
                .joinedload(FinishedGood.recipe)
                .joinedload(Recipe.recipe_ingredients)
                .joinedload(RecipeIngredient.ingredient)
            )

            # Apply filters
            if name_search:
                query = query.filter(Package.name.ilike(f"%{name_search}%"))

            if is_template is not None:
                query = query.filter(Package.is_template == is_template)

            # Order by name
            query = query.order_by(Package.name)

            packages = query.all()

            return packages

    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to get packages: {str(e)}")


def update_package(package_id: int, data: Dict, bundle_items: Optional[List[Dict]] = None) -> Package:
    """
    Update an existing package.

    Args:
        package_id: Package ID to update
        data: Dictionary with updated package fields
        bundle_items: Optional list of dictionaries with bundle_id and quantity

    Returns:
        Updated Package instance

    Raises:
        PackageNotFound: If package not found
        ValidationError: If data validation fails
        DatabaseError: If database operation fails
    """
    # Validate required fields
    errors = []

    if not data.get("name"):
        errors.append("Name is required")

    if errors:
        raise ValidationError(errors)

    try:
        with session_scope() as session:
            # Get existing package
            package = session.query(Package).filter(Package.id == package_id).first()
            if not package:
                raise PackageNotFound(package_id)

            # Update fields
            package.name = data["name"]
            package.description = data.get("description")
            package.is_template = data.get("is_template", False)
            package.notes = data.get("notes")
            package.last_modified = datetime.utcnow()

            # Update bundles if provided
            if bundle_items is not None:
                # Remove existing package bundles
                session.query(PackageBundle).filter(
                    PackageBundle.package_id == package_id
                ).delete()

                # Add new bundles
                for item in bundle_items:
                    bundle_id = item.get("bundle_id")
                    quantity = item.get("quantity", 1)

                    # Validate bundle exists
                    bundle = session.query(Bundle).filter(Bundle.id == bundle_id).first()
                    if not bundle:
                        raise ValidationError([f"Bundle with ID {bundle_id} not found"])

                    # Create PackageBundle
                    pb = PackageBundle(
                        package_id=package.id,
                        bundle_id=bundle_id,
                        quantity=quantity
                    )
                    session.add(pb)

            session.commit()

            # Reload with all nested relationships eagerly loaded
            package = session.query(Package).options(
                joinedload(Package.package_bundles)
                .joinedload(PackageBundle.bundle)
                .joinedload(Bundle.finished_good)
                .joinedload(FinishedGood.recipe)
                .joinedload(Recipe.recipe_ingredients)
                .joinedload(RecipeIngredient.ingredient)
            ).filter(Package.id == package.id).one()

            return package

    except (PackageNotFound, ValidationError):
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
        PackageNotFound: If package not found
        PackageInUse: If package is used in events
        DatabaseError: If database operation fails
    """
    try:
        with session_scope() as session:
            # Get package
            package = session.query(Package).filter(Package.id == package_id).first()
            if not package:
                raise PackageNotFound(package_id)

            # TODO: Check if package is used in events (Phase 3b)
            # For now, just delete

            # Delete package (cascade will delete PackageBundle records)
            session.delete(package)
            session.commit()

            return True

    except PackageNotFound:
        raise
    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to delete package: {str(e)}")
