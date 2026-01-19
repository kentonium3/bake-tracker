"""Unit Service - Query functions for the unit reference table.

This module provides helper functions for querying units from the reference table
and formatting them for UI dropdowns.

All functions accept an optional session parameter to support being called from
other service functions that need to maintain transactional atomicity.

Example Usage:
    >>> from src.services.unit_service import get_all_units, get_units_by_category
    >>>
    >>> # Get all units
    >>> units = get_all_units()
    >>> len(units)
    27
    >>>
    >>> # Get units for a specific category
    >>> weight_units = get_units_by_category('weight')
    >>> [u.code for u in weight_units]
    ['oz', 'lb', 'g', 'kg']
    >>>
    >>> # Get formatted list for dropdown
    >>> dropdown_values = get_units_for_dropdown(['weight', 'volume'])
    >>> dropdown_values[:5]
    ['-- Weight --', 'oz', 'lb', 'g', 'kg']
"""

import logging
from typing import List, Optional

from sqlalchemy.orm import Session

from ..models.unit import Unit
from .database import session_scope

# Configure logging
logger = logging.getLogger(__name__)


def get_all_units(session: Optional[Session] = None) -> List[Unit]:
    """Get all units ordered by category and sort_order.

    Args:
        session: Optional database session. If None, creates a new session.

    Returns:
        List of Unit objects ordered by category then sort_order.
    """

    def _impl(sess: Session) -> List[Unit]:
        return sess.query(Unit).order_by(Unit.category, Unit.sort_order).all()

    if session is not None:
        return _impl(session)
    with session_scope() as sess:
        return _impl(sess)


def get_units_by_category(category: str, session: Optional[Session] = None) -> List[Unit]:
    """Get units filtered by a specific category.

    Args:
        category: The unit category to filter by ('weight', 'volume', 'count', 'package').
        session: Optional database session. If None, creates a new session.

    Returns:
        List of Unit objects in the specified category, ordered by sort_order.
    """

    def _impl(sess: Session) -> List[Unit]:
        return sess.query(Unit).filter(Unit.category == category).order_by(Unit.sort_order).all()

    if session is not None:
        return _impl(session)
    with session_scope() as sess:
        return _impl(sess)


def get_units_for_dropdown(categories: List[str], session: Optional[Session] = None) -> List[str]:
    """Get units formatted for CTkComboBox dropdown with category headers.

    Returns a list of strings where category headers are formatted as
    "-- Category --" and unit values are the unit codes. The UI layer
    should treat items starting with "--" as non-selectable headers.

    Args:
        categories: List of categories to include (e.g., ['weight', 'volume']).
        session: Optional database session. If None, creates a new session.

    Returns:
        List of strings formatted for dropdown display.

    Example:
        >>> get_units_for_dropdown(['weight', 'volume'])
        ['-- Weight --', 'oz', 'lb', 'g', 'kg', '-- Volume --', 'tsp', 'tbsp', ...]
    """

    def _impl(sess: Session) -> List[str]:
        result = []
        for category in categories:
            # Add category header
            result.append(f"-- {category.title()} --")
            # Add unit codes for this category
            units = (
                sess.query(Unit).filter(Unit.category == category).order_by(Unit.sort_order).all()
            )
            for unit in units:
                result.append(unit.code)
        return result

    if session is not None:
        return _impl(session)
    with session_scope() as sess:
        return _impl(sess)


def get_unit_by_code(code: str, session: Optional[Session] = None) -> Optional[Unit]:
    """Get a unit by its code.

    Args:
        code: The unit code to look up (e.g., 'oz', 'cup').
        session: Optional database session. If None, creates a new session.

    Returns:
        Unit object if found, None otherwise.
    """

    def _impl(sess: Session) -> Optional[Unit]:
        return sess.query(Unit).filter(Unit.code == code).first()

    if session is not None:
        return _impl(session)
    with session_scope() as sess:
        return _impl(sess)


def is_valid_unit(code: str, session: Optional[Session] = None) -> bool:
    """Check if a unit code is valid (exists in the reference table).

    Args:
        code: The unit code to validate.
        session: Optional database session. If None, creates a new session.

    Returns:
        True if the unit exists, False otherwise.
    """
    return get_unit_by_code(code, session=session) is not None
