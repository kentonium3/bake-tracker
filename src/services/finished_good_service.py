"""
Finished Good Service - Business logic for finished goods and bundles.

This service provides CRUD operations for:
- Finished goods (products made from recipes)
- Bundles (grouped finished goods)
"""

from typing import List, Optional, Dict
from datetime import datetime

from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload

from src.models import FinishedGood, Bundle, YieldMode, Recipe
from src.services.database import session_scope
from src.services.exceptions import (
    DatabaseError,
    ValidationError,
)


# ============================================================================
# Custom Exceptions
# ============================================================================


class FinishedGoodNotFound(Exception):
    """Raised when a finished good is not found."""
    def __init__(self, finished_good_id: int):
        self.finished_good_id = finished_good_id
        super().__init__(f"Finished good with ID {finished_good_id} not found")


class BundleNotFound(Exception):
    """Raised when a bundle is not found."""
    def __init__(self, bundle_id: int):
        self.bundle_id = bundle_id
        super().__init__(f"Bundle with ID {bundle_id} not found")


class FinishedGoodInUse(Exception):
    """Raised when trying to delete a finished good that's used in bundles."""
    def __init__(self, finished_good_id: int, bundle_count: int):
        self.finished_good_id = finished_good_id
        self.bundle_count = bundle_count
        super().__init__(
            f"Finished good {finished_good_id} is used in {bundle_count} bundle(s)"
        )


# ============================================================================
# Finished Good CRUD Operations
# ============================================================================


def create_finished_good(data: Dict) -> FinishedGood:
    """
    Create a new finished good.

    Args:
        data: Dictionary with finished good fields

    Returns:
        Created FinishedGood instance

    Raises:
        ValidationError: If data validation fails
        DatabaseError: If database operation fails
    """
    # Validate required fields
    errors = []

    if not data.get("name"):
        errors.append("Name is required")

    if not data.get("recipe_id"):
        errors.append("Recipe is required")

    if not data.get("yield_mode"):
        errors.append("Yield mode is required")

    # Validate yield mode specific fields
    yield_mode = data.get("yield_mode")
    if yield_mode == "discrete_count":
        if not data.get("items_per_batch"):
            errors.append("Items per batch is required for discrete count mode")
        if not data.get("item_unit"):
            errors.append("Item unit is required for discrete count mode")

    elif yield_mode == "batch_portion":
        if not data.get("batch_percentage"):
            errors.append("Batch percentage is required for batch portion mode")

    if errors:
        raise ValidationError(errors)

    try:
        with session_scope() as session:
            # Convert yield_mode string to enum
            if isinstance(data["yield_mode"], str):
                yield_mode_enum = YieldMode(data["yield_mode"])
            else:
                yield_mode_enum = data["yield_mode"]

            finished_good = FinishedGood(
                name=data["name"],
                recipe_id=data["recipe_id"],
                yield_mode=yield_mode_enum,
                items_per_batch=data.get("items_per_batch"),
                item_unit=data.get("item_unit"),
                batch_percentage=data.get("batch_percentage"),
                portion_description=data.get("portion_description"),
                category=data.get("category"),
                notes=data.get("notes"),
            )

            session.add(finished_good)
            session.flush()

            # Eagerly load recipe with all nested relationships
            finished_good = session.query(FinishedGood).options(
                joinedload(FinishedGood.recipe).joinedload(Recipe.recipe_ingredients)
            ).filter(FinishedGood.id == finished_good.id).one()

            # Force load all ingredients
            for ri in finished_good.recipe.recipe_ingredients:
                _ = ri.ingredient

            return finished_good

    except SQLAlchemyError as e:
        raise DatabaseError("Failed to create finished good", e)


def get_finished_good(finished_good_id: int) -> FinishedGood:
    """
    Retrieve a finished good by ID.

    Args:
        finished_good_id: Finished good ID

    Returns:
        FinishedGood instance

    Raises:
        FinishedGoodNotFound: If finished good doesn't exist
        DatabaseError: If database operation fails
    """
    try:
        with session_scope() as session:
            finished_good = session.query(FinishedGood).options(
                joinedload(FinishedGood.recipe).joinedload(Recipe.recipe_ingredients)
            ).filter_by(id=finished_good_id).first()

            if not finished_good:
                raise FinishedGoodNotFound(finished_good_id)

            # Force load all ingredients
            for ri in finished_good.recipe.recipe_ingredients:
                _ = ri.ingredient

            return finished_good

    except FinishedGoodNotFound:
        raise
    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to retrieve finished good {finished_good_id}", e)


def get_all_finished_goods(
    recipe_id: Optional[int] = None,
    category: Optional[str] = None,
    name_search: Optional[str] = None,
) -> List[FinishedGood]:
    """
    Retrieve all finished goods with optional filtering.

    Args:
        recipe_id: Filter by recipe ID
        category: Filter by category
        name_search: Filter by name (case-insensitive partial match)

    Returns:
        List of FinishedGood instances

    Raises:
        DatabaseError: If database operation fails
    """
    try:
        with session_scope() as session:
            query = session.query(FinishedGood).options(
                joinedload(FinishedGood.recipe).joinedload(Recipe.recipe_ingredients)
            )

            # Apply filters
            if recipe_id:
                query = query.filter(FinishedGood.recipe_id == recipe_id)

            if category:
                query = query.filter(FinishedGood.category == category)

            if name_search:
                query = query.filter(FinishedGood.name.ilike(f"%{name_search}%"))

            # Order by name
            query = query.order_by(FinishedGood.name)

            finished_goods = query.all()

            # Force load all ingredients
            for fg in finished_goods:
                for ri in fg.recipe.recipe_ingredients:
                    _ = ri.ingredient

            return finished_goods

    except SQLAlchemyError as e:
        raise DatabaseError("Failed to retrieve finished goods", e)


def update_finished_good(finished_good_id: int, data: Dict) -> FinishedGood:
    """
    Update a finished good.

    Args:
        finished_good_id: Finished good ID
        data: Dictionary with fields to update

    Returns:
        Updated FinishedGood instance

    Raises:
        FinishedGoodNotFound: If finished good doesn't exist
        ValidationError: If data validation fails
        DatabaseError: If database operation fails
    """
    try:
        with session_scope() as session:
            finished_good = session.query(FinishedGood).filter_by(id=finished_good_id).first()

            if not finished_good:
                raise FinishedGoodNotFound(finished_good_id)

            # Update fields
            for field, value in data.items():
                if field == "yield_mode" and isinstance(value, str):
                    value = YieldMode(value)
                if hasattr(finished_good, field):
                    setattr(finished_good, field, value)

            # Update timestamp
            finished_good.last_modified = datetime.utcnow()

            session.flush()

            # Eagerly load recipe with all nested relationships
            finished_good = session.query(FinishedGood).options(
                joinedload(FinishedGood.recipe).joinedload(Recipe.recipe_ingredients)
            ).filter(FinishedGood.id == finished_good_id).one()

            # Force load all ingredients
            for ri in finished_good.recipe.recipe_ingredients:
                _ = ri.ingredient

            return finished_good

    except (FinishedGoodNotFound, ValidationError):
        raise
    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to update finished good {finished_good_id}", e)


def delete_finished_good(finished_good_id: int, force: bool = False) -> bool:
    """
    Delete a finished good.

    Args:
        finished_good_id: Finished good ID
        force: If True, delete even if used in bundles (NOT RECOMMENDED)

    Returns:
        True if deleted successfully

    Raises:
        FinishedGoodNotFound: If finished good doesn't exist
        FinishedGoodInUse: If finished good is used in bundles and force=False
        DatabaseError: If database operation fails
    """
    try:
        with session_scope() as session:
            finished_good = session.query(FinishedGood).filter_by(id=finished_good_id).first()

            if not finished_good:
                raise FinishedGoodNotFound(finished_good_id)

            # Check if finished good is used in bundles
            bundle_count = session.query(Bundle).filter_by(finished_good_id=finished_good_id).count()

            if bundle_count > 0:
                if not force:
                    raise FinishedGoodInUse(finished_good_id, bundle_count)
                else:
                    # Force delete: remove all bundles first
                    session.query(Bundle).filter_by(finished_good_id=finished_good_id).delete()

            # Delete finished good
            session.delete(finished_good)

            return True

    except (FinishedGoodNotFound, FinishedGoodInUse):
        raise
    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to delete finished good {finished_good_id}", e)


# ============================================================================
# Bundle CRUD Operations
# ============================================================================


def create_bundle(data: Dict) -> Bundle:
    """
    Create a new bundle.

    Args:
        data: Dictionary with bundle fields

    Returns:
        Created Bundle instance

    Raises:
        ValidationError: If data validation fails
        DatabaseError: If database operation fails
    """
    # Validate required fields
    errors = []

    if not data.get("name"):
        errors.append("Name is required")

    if not data.get("finished_good_id"):
        errors.append("Finished good is required")

    if not data.get("quantity"):
        errors.append("Quantity is required")
    elif data.get("quantity", 0) <= 0:
        errors.append("Quantity must be greater than zero")

    if errors:
        raise ValidationError(errors)

    try:
        with session_scope() as session:
            bundle = Bundle(
                name=data["name"],
                finished_good_id=data["finished_good_id"],
                quantity=data["quantity"],
                packaging_notes=data.get("packaging_notes"),
            )

            session.add(bundle)
            session.flush()

            # Eagerly load finished good with all nested relationships
            bundle = session.query(Bundle).options(
                joinedload(Bundle.finished_good).joinedload(FinishedGood.recipe).joinedload(Recipe.recipe_ingredients)
            ).filter(Bundle.id == bundle.id).one()

            # Force load all ingredients
            for ri in bundle.finished_good.recipe.recipe_ingredients:
                _ = ri.ingredient

            return bundle

    except SQLAlchemyError as e:
        raise DatabaseError("Failed to create bundle", e)


def get_bundle(bundle_id: int) -> Bundle:
    """
    Retrieve a bundle by ID.

    Args:
        bundle_id: Bundle ID

    Returns:
        Bundle instance

    Raises:
        BundleNotFound: If bundle doesn't exist
        DatabaseError: If database operation fails
    """
    try:
        with session_scope() as session:
            bundle = session.query(Bundle).options(
                joinedload(Bundle.finished_good).joinedload(FinishedGood.recipe).joinedload(Recipe.recipe_ingredients)
            ).filter_by(id=bundle_id).first()

            if not bundle:
                raise BundleNotFound(bundle_id)

            # Force load all ingredients
            for ri in bundle.finished_good.recipe.recipe_ingredients:
                _ = ri.ingredient

            return bundle

    except BundleNotFound:
        raise
    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to retrieve bundle {bundle_id}", e)


def get_all_bundles(
    finished_good_id: Optional[int] = None,
    name_search: Optional[str] = None,
) -> List[Bundle]:
    """
    Retrieve all bundles with optional filtering.

    Args:
        finished_good_id: Filter by finished good ID
        name_search: Filter by name (case-insensitive partial match)

    Returns:
        List of Bundle instances

    Raises:
        DatabaseError: If database operation fails
    """
    try:
        with session_scope() as session:
            query = session.query(Bundle).options(
                joinedload(Bundle.finished_good).joinedload(FinishedGood.recipe).joinedload(Recipe.recipe_ingredients)
            )

            # Apply filters
            if finished_good_id:
                query = query.filter(Bundle.finished_good_id == finished_good_id)

            if name_search:
                query = query.filter(Bundle.name.ilike(f"%{name_search}%"))

            # Order by name
            query = query.order_by(Bundle.name)

            bundles = query.all()

            # Force load all ingredients
            for bundle in bundles:
                for ri in bundle.finished_good.recipe.recipe_ingredients:
                    _ = ri.ingredient

            return bundles

    except SQLAlchemyError as e:
        raise DatabaseError("Failed to retrieve bundles", e)


def update_bundle(bundle_id: int, data: Dict) -> Bundle:
    """
    Update a bundle.

    Args:
        bundle_id: Bundle ID
        data: Dictionary with fields to update

    Returns:
        Updated Bundle instance

    Raises:
        BundleNotFound: If bundle doesn't exist
        ValidationError: If data validation fails
        DatabaseError: If database operation fails
    """
    try:
        with session_scope() as session:
            bundle = session.query(Bundle).filter_by(id=bundle_id).first()

            if not bundle:
                raise BundleNotFound(bundle_id)

            # Update fields
            for field, value in data.items():
                if hasattr(bundle, field):
                    setattr(bundle, field, value)

            # Update timestamp
            bundle.last_modified = datetime.utcnow()

            session.flush()

            # Eagerly load finished good with all nested relationships
            bundle = session.query(Bundle).options(
                joinedload(Bundle.finished_good).joinedload(FinishedGood.recipe).joinedload(Recipe.recipe_ingredients)
            ).filter(Bundle.id == bundle_id).one()

            # Force load all ingredients
            for ri in bundle.finished_good.recipe.recipe_ingredients:
                _ = ri.ingredient

            return bundle

    except (BundleNotFound, ValidationError):
        raise
    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to update bundle {bundle_id}", e)


def delete_bundle(bundle_id: int) -> bool:
    """
    Delete a bundle.

    Args:
        bundle_id: Bundle ID

    Returns:
        True if deleted successfully

    Raises:
        BundleNotFound: If bundle doesn't exist
        DatabaseError: If database operation fails
    """
    try:
        with session_scope() as session:
            bundle = session.query(Bundle).filter_by(id=bundle_id).first()

            if not bundle:
                raise BundleNotFound(bundle_id)

            # Delete bundle
            session.delete(bundle)

            return True

    except BundleNotFound:
        raise
    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to delete bundle {bundle_id}", e)


# ============================================================================
# Utility Functions
# ============================================================================


def get_finished_good_count() -> int:
    """
    Get total count of finished goods.

    Returns:
        Number of finished goods in database

    Raises:
        DatabaseError: If database operation fails
    """
    try:
        with session_scope() as session:
            return session.query(FinishedGood).count()

    except SQLAlchemyError as e:
        raise DatabaseError("Failed to count finished goods", e)


def get_bundle_count() -> int:
    """
    Get total count of bundles.

    Returns:
        Number of bundles in database

    Raises:
        DatabaseError: If database operation fails
    """
    try:
        with session_scope() as session:
            return session.query(Bundle).count()

    except SQLAlchemyError as e:
        raise DatabaseError("Failed to count bundles", e)
