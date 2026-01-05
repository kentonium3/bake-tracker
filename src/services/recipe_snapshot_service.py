"""
Recipe Snapshot Service for F037 Template & Snapshot System.

Provides immutable snapshot creation and retrieval. NO UPDATE METHODS.
Snapshots capture the complete recipe state at production time for
historical cost accuracy.

Session Management Pattern (from CLAUDE.md):
- All public functions accept session=None parameter
- If session provided, use it directly
- If session is None, create a new session via session_scope()
"""

import json
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from src.models import Recipe, RecipeIngredient, RecipeSnapshot
from src.services.database import session_scope
from src.utils.datetime_utils import utc_now


class SnapshotCreationError(Exception):
    """Raised when snapshot creation fails."""
    pass


def create_recipe_snapshot(
    recipe_id: int,
    scale_factor: float,
    production_run_id: int,
    session: Session = None
) -> dict:
    """
    Create an immutable snapshot of recipe state at production time.

    Args:
        recipe_id: Source recipe ID
        scale_factor: Size multiplier for this production (default 1.0)
        production_run_id: The production run this snapshot is for (1:1)
        session: Optional SQLAlchemy session for transaction sharing

    Returns:
        dict with snapshot data including id

    Raises:
        SnapshotCreationError: If recipe not found or creation fails
    """
    if session is not None:
        return _create_recipe_snapshot_impl(recipe_id, scale_factor, production_run_id, session)

    try:
        with session_scope() as session:
            return _create_recipe_snapshot_impl(recipe_id, scale_factor, production_run_id, session)
    except SQLAlchemyError as e:
        raise SnapshotCreationError(f"Database error creating snapshot: {e}")


def _create_recipe_snapshot_impl(
    recipe_id: int,
    scale_factor: float,
    production_run_id: int,
    session: Session
) -> dict:
    """Internal implementation of snapshot creation."""
    # Load recipe with relationships
    recipe = session.query(Recipe).filter_by(id=recipe_id).first()
    if not recipe:
        raise SnapshotCreationError(f"Recipe {recipe_id} not found")

    # Eagerly load ingredients to avoid lazy loading issues
    _ = recipe.recipe_ingredients
    for ri in recipe.recipe_ingredients:
        _ = ri.ingredient

    # Build recipe_data JSON
    recipe_data = {
        "name": recipe.name,
        "category": recipe.category,
        "source": recipe.source,
        "yield_quantity": recipe.yield_quantity,
        "yield_unit": recipe.yield_unit,
        "yield_description": recipe.yield_description,
        "estimated_time_minutes": recipe.estimated_time_minutes,
        "notes": recipe.notes,
        "variant_name": getattr(recipe, "variant_name", None),
        "is_production_ready": getattr(recipe, "is_production_ready", False),
    }

    # Build ingredients_data JSON
    ingredients_data = []
    for ri in recipe.recipe_ingredients:
        ing_data = {
            "ingredient_id": ri.ingredient_id,
            "ingredient_name": ri.ingredient.display_name if ri.ingredient else "Unknown",
            "ingredient_slug": ri.ingredient.slug if ri.ingredient else "",
            "quantity": float(ri.quantity),
            "unit": ri.unit,
            "notes": ri.notes,
        }
        ingredients_data.append(ing_data)

    # Create snapshot
    snapshot = RecipeSnapshot(
        recipe_id=recipe_id,
        production_run_id=production_run_id,
        scale_factor=scale_factor,
        snapshot_date=utc_now(),
        recipe_data=json.dumps(recipe_data),
        ingredients_data=json.dumps(ingredients_data),
        is_backfilled=False
    )

    session.add(snapshot)
    session.flush()  # Get ID without committing

    return {
        "id": snapshot.id,
        "recipe_id": snapshot.recipe_id,
        "production_run_id": snapshot.production_run_id,
        "scale_factor": snapshot.scale_factor,
        "snapshot_date": snapshot.snapshot_date.isoformat(),
        "recipe_data": recipe_data,
        "ingredients_data": ingredients_data,
        "is_backfilled": snapshot.is_backfilled
    }


def get_recipe_snapshots(recipe_id: int, session: Session = None) -> list:
    """
    Get all snapshots for a recipe, ordered by date (newest first).

    Args:
        recipe_id: Recipe to get history for
        session: Optional session

    Returns:
        List of snapshot dicts
    """
    if session is not None:
        return _get_recipe_snapshots_impl(recipe_id, session)

    with session_scope() as session:
        return _get_recipe_snapshots_impl(recipe_id, session)


def _get_recipe_snapshots_impl(recipe_id: int, session: Session) -> list:
    """Internal implementation of get_recipe_snapshots."""
    snapshots = (
        session.query(RecipeSnapshot)
        .filter_by(recipe_id=recipe_id)
        .order_by(RecipeSnapshot.snapshot_date.desc())
        .all()
    )

    return [
        {
            "id": s.id,
            "recipe_id": s.recipe_id,
            "production_run_id": s.production_run_id,
            "scale_factor": s.scale_factor,
            "snapshot_date": s.snapshot_date.isoformat(),
            "recipe_data": s.get_recipe_data(),
            "ingredients_data": s.get_ingredients_data(),
            "is_backfilled": s.is_backfilled
        }
        for s in snapshots
    ]


def get_snapshot_by_production_run(
    production_run_id: int,
    session: Session = None
) -> Optional[dict]:
    """
    Get the snapshot associated with a production run.

    Args:
        production_run_id: Production run ID
        session: Optional session

    Returns:
        Snapshot dict or None if not found
    """
    if session is not None:
        return _get_snapshot_by_production_run_impl(production_run_id, session)

    with session_scope() as session:
        return _get_snapshot_by_production_run_impl(production_run_id, session)


def _get_snapshot_by_production_run_impl(
    production_run_id: int,
    session: Session
) -> Optional[dict]:
    """Internal implementation of get_snapshot_by_production_run."""
    snapshot = (
        session.query(RecipeSnapshot)
        .filter_by(production_run_id=production_run_id)
        .first()
    )

    if not snapshot:
        return None

    return {
        "id": snapshot.id,
        "recipe_id": snapshot.recipe_id,
        "production_run_id": snapshot.production_run_id,
        "scale_factor": snapshot.scale_factor,
        "snapshot_date": snapshot.snapshot_date.isoformat(),
        "recipe_data": snapshot.get_recipe_data(),
        "ingredients_data": snapshot.get_ingredients_data(),
        "is_backfilled": snapshot.is_backfilled
    }


def get_snapshot_by_id(snapshot_id: int, session: Session = None) -> Optional[dict]:
    """
    Get a snapshot by its ID.

    Args:
        snapshot_id: Snapshot ID
        session: Optional session

    Returns:
        Snapshot dict or None if not found
    """
    if session is not None:
        return _get_snapshot_by_id_impl(snapshot_id, session)

    with session_scope() as session:
        return _get_snapshot_by_id_impl(snapshot_id, session)


def _get_snapshot_by_id_impl(snapshot_id: int, session: Session) -> Optional[dict]:
    """Internal implementation of get_snapshot_by_id."""
    snapshot = session.query(RecipeSnapshot).filter_by(id=snapshot_id).first()

    if not snapshot:
        return None

    return {
        "id": snapshot.id,
        "recipe_id": snapshot.recipe_id,
        "production_run_id": snapshot.production_run_id,
        "scale_factor": snapshot.scale_factor,
        "snapshot_date": snapshot.snapshot_date.isoformat(),
        "recipe_data": snapshot.get_recipe_data(),
        "ingredients_data": snapshot.get_ingredients_data(),
        "is_backfilled": snapshot.is_backfilled
    }


def create_recipe_from_snapshot(snapshot_id: int, session: Session = None) -> dict:
    """
    Create a new recipe from historical snapshot data.

    This restores a recipe from a production snapshot, creating a new recipe
    with the ingredient list as it was captured at production time. The new
    recipe starts as not production-ready (experimental) to allow review.

    Args:
        snapshot_id: Snapshot to restore from
        session: Optional SQLAlchemy session for transaction sharing

    Returns:
        dict with created recipe info: id, name, category

    Raises:
        ValueError: If snapshot not found
        SnapshotCreationError: If recipe creation fails
    """
    if session is not None:
        return _create_recipe_from_snapshot_impl(snapshot_id, session)

    try:
        with session_scope() as session:
            return _create_recipe_from_snapshot_impl(snapshot_id, session)
    except SQLAlchemyError as e:
        raise SnapshotCreationError(f"Database error creating recipe from snapshot: {e}")


def _create_recipe_from_snapshot_impl(snapshot_id: int, session: Session) -> dict:
    """Internal implementation of create_recipe_from_snapshot."""
    # Get snapshot
    snapshot = session.query(RecipeSnapshot).filter_by(id=snapshot_id).first()
    if not snapshot:
        raise ValueError(f"Snapshot {snapshot_id} not found")

    recipe_data = snapshot.get_recipe_data()
    ingredients_data = snapshot.get_ingredients_data()

    # Create new recipe with restored data
    original_name = recipe_data.get("name", "Restored")
    date_str = datetime.now().strftime("%Y-%m-%d")
    new_name = f"{original_name} (restored {date_str})"

    recipe = Recipe(
        name=new_name,
        category=recipe_data.get("category", "Uncategorized"),
        source=recipe_data.get("source"),
        yield_quantity=recipe_data.get("yield_quantity", 1),
        yield_unit=recipe_data.get("yield_unit", "each"),
        yield_description=recipe_data.get("yield_description"),
        estimated_time_minutes=recipe_data.get("estimated_time_minutes"),
        notes=_build_restored_notes(snapshot_id, recipe_data.get("notes", "")),
        is_production_ready=False,  # Restored recipes start experimental
    )

    session.add(recipe)
    session.flush()  # Get recipe ID

    # Restore ingredients - only add those with valid ingredient_id
    for ing in ingredients_data:
        ingredient_id = ing.get("ingredient_id")
        if ingredient_id is None:
            # Skip ingredients without valid ID (ingredient may have been deleted)
            continue

        ri = RecipeIngredient(
            recipe_id=recipe.id,
            ingredient_id=ingredient_id,
            quantity=ing.get("quantity", 0),
            unit=ing.get("unit", ""),
            notes=ing.get("notes"),
        )
        session.add(ri)

    session.flush()  # Flush to get IDs; caller controls commit

    return {
        "id": recipe.id,
        "name": recipe.name,
        "category": recipe.category,
    }


def _build_restored_notes(snapshot_id: int, original_notes: str) -> str:
    """
    Build notes for restored recipe.

    Args:
        snapshot_id: ID of source snapshot
        original_notes: Original recipe notes from snapshot

    Returns:
        Combined notes string
    """
    restoration_note = f"Restored from snapshot {snapshot_id}."
    if original_notes:
        return f"{restoration_note} Original notes: {original_notes}"
    return restoration_note
