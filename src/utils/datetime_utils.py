"""Datetime utilities for timezone-aware UTC timestamps.

This module provides a replacement for the deprecated datetime.utcnow()
function. Python 3.12+ deprecates utcnow() in favor of timezone-aware
datetime objects.

Usage:
    from src.utils.datetime_utils import utc_now

    # Instead of datetime.utcnow()
    timestamp = utc_now()

    # For SQLAlchemy Column defaults
    created_at = Column(DateTime, default=utc_now)
"""

from datetime import datetime, timezone


def utc_now() -> datetime:
    """Return current UTC time as timezone-aware datetime.

    This is the replacement for the deprecated datetime.utcnow().

    Returns:
        Current UTC datetime with timezone info
    """
    return datetime.now(timezone.utc)
