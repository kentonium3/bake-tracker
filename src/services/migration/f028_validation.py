"""
F028 Validation: Verify migration success.

Usage:
    from src.services.migration.f028_validation import validate_migration
    success, report = validate_migration()
"""

import logging
from typing import Tuple, Dict, Any, Optional

from sqlalchemy.orm import Session

from src.models import InventoryItem, Purchase, Supplier
from src.services.database import session_scope

logger = logging.getLogger(__name__)


def validate_migration(session: Optional[Session] = None) -> Tuple[bool, Dict[str, Any]]:
    """
    Validate F028 migration success.

    Args:
        session: Optional database session (creates new if not provided)

    Returns:
        Tuple of (success: bool, report: dict)
    """
    if session is not None:
        return _validate_impl(session)

    with session_scope() as session:
        return _validate_impl(session)


def _validate_impl(session: Session) -> Tuple[bool, Dict[str, Any]]:
    """Implementation of validation."""
    report: Dict[str, Any] = {
        "checks": [],
        "errors": [],
        "warnings": [],
    }

    # Check 1: No NULL purchase_id
    null_purchase_count = (
        session.query(InventoryItem).filter(InventoryItem.purchase_id == None).count()  # noqa: E711
    )
    if null_purchase_count > 0:
        report["errors"].append(f"FAIL: {null_purchase_count} InventoryItems have NULL purchase_id")
    else:
        report["checks"].append("PASS: All InventoryItems have purchase_id")

    # Check 2: All linked Purchases exist
    orphaned = (
        session.query(InventoryItem)
        .filter(InventoryItem.purchase_id != None)  # noqa: E711
        .filter(~InventoryItem.purchase.has())
        .count()
    )
    if orphaned > 0:
        report["errors"].append(f"FAIL: {orphaned} InventoryItems reference non-existent Purchases")
    else:
        report["checks"].append("PASS: All purchase_id references are valid")

    # Check 3: Product IDs match
    mismatched = 0
    items_with_purchase = (
        session.query(InventoryItem).filter(InventoryItem.purchase_id != None).all()  # noqa: E711
    )
    for item in items_with_purchase:
        if item.purchase and item.product_id != item.purchase.product_id:
            mismatched += 1

    if mismatched > 0:
        report["errors"].append(f"FAIL: {mismatched} items have product_id mismatch with Purchase")
    else:
        report["checks"].append("PASS: All product_id values match")

    # Check 4: unit_cost populated
    null_unit_cost = (
        session.query(InventoryItem).filter(InventoryItem.unit_cost == None).count()  # noqa: E711
    )
    if null_unit_cost > 0:
        report["warnings"].append(f"WARNING: {null_unit_cost} InventoryItems have NULL unit_cost")
    else:
        report["checks"].append("PASS: All InventoryItems have unit_cost")

    # Summary
    success = len(report["errors"]) == 0
    total_items = session.query(InventoryItem).count()
    total_purchases = session.query(Purchase).count()

    report["summary"] = {
        "success": success,
        "total_inventory_items": total_items,
        "total_purchases": total_purchases,
        "checks_passed": len(report["checks"]),
        "errors": len(report["errors"]),
        "warnings": len(report["warnings"]),
    }

    return (success, report)


def print_validation_report(report: Dict[str, Any]) -> None:
    """Print formatted validation report."""
    print("\n" + "=" * 50)
    print("F028 Migration Validation Report")
    print("=" * 50)

    for check in report["checks"]:
        print(f"  {check}")

    for error in report["errors"]:
        print(f"  {error}")

    for warning in report["warnings"]:
        print(f"  {warning}")

    print("-" * 50)
    summary = report["summary"]
    print(f"Total InventoryItems: {summary['total_inventory_items']}")
    print(f"Total Purchases: {summary['total_purchases']}")
    print(f"Status: {'PASSED' if summary['success'] else 'FAILED'}")
    print("=" * 50 + "\n")
