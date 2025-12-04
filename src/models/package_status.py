"""
Package status enum for production lifecycle tracking.

This enum defines the three-state lifecycle for packages during
production and delivery tracking.
"""

import enum


class PackageStatus(enum.Enum):
    """
    Package lifecycle status for EventRecipientPackage.

    Status transitions:
        PENDING -> ASSEMBLED (when all required recipes produced)
        ASSEMBLED -> DELIVERED (when given to recipient)

    Invalid transitions:
        PENDING -> DELIVERED (must assemble first)
        ASSEMBLED -> PENDING (no rollback)
        DELIVERED -> * (no rollback from delivered)
    """

    PENDING = "pending"  # Not yet assembled
    ASSEMBLED = "assembled"  # All components produced, package ready
    DELIVERED = "delivered"  # Given to recipient
