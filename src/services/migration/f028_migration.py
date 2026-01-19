"""
F028 Migration: Link existing InventoryItems to Purchase records.

This migration creates Purchase records for any InventoryItem that lacks
a purchase_id link, using "Unknown" supplier as fallback.

Usage:
    from src.services.migration.f028_migration import run_migration
    run_migration()  # Or run_migration(dry_run=True) to preview
"""

import logging
from datetime import date
from decimal import Decimal
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from src.models import InventoryItem, Purchase, Supplier
from src.services.database import session_scope

logger = logging.getLogger(__name__)


def run_migration(dry_run: bool = False, session: Optional[Session] = None) -> Tuple[int, int]:
    """
    Run F028 migration to link InventoryItems to Purchase records.

    Args:
        dry_run: If True, report what would be done without making changes
        session: Optional database session (creates new if not provided)

    Returns:
        Tuple of (items_processed, purchases_created)
    """
    if session is not None:
        return _run_migration_impl(session, dry_run)

    with session_scope() as session:
        return _run_migration_impl(session, dry_run)


def _get_or_create_unknown_supplier(session: Session) -> Supplier:
    """
    Get the Unknown supplier, creating if necessary.

    Returns:
        Supplier instance for "Unknown" supplier
    """
    unknown = session.query(Supplier).filter(Supplier.name == "Unknown").first()

    if unknown:
        logger.info(f"Found existing Unknown supplier (id={unknown.id})")
        return unknown

    # Create Unknown supplier with F027 defaults
    logger.warning("Unknown supplier not found - creating with defaults")
    unknown = Supplier(
        name="Unknown",
        city="Unknown",
        state="XX",
        zip_code="00000",
        street_address=None,
        notes="Default supplier for migrated inventory additions (F028)",
        is_active=True,
    )
    session.add(unknown)
    session.flush()
    logger.info(f"Created Unknown supplier (id={unknown.id})")
    return unknown


def _run_migration_impl(session: Session, dry_run: bool) -> Tuple[int, int]:
    """
    Implementation of F028 migration.

    For each InventoryItem without a purchase_id:
    1. Creates a Purchase record with Unknown supplier
    2. Sets purchase.unit_price from item.unit_cost (or $0.00)
    3. Links item.purchase_id to the new Purchase
    4. Ensures item.unit_cost is populated

    Args:
        session: Database session
        dry_run: If True, count items but don't modify

    Returns:
        Tuple of (items_processed, purchases_created)
    """
    # Get Unknown supplier
    unknown_supplier = _get_or_create_unknown_supplier(session)

    # Find items needing migration
    items_to_migrate = (
        session.query(InventoryItem).filter(InventoryItem.purchase_id == None).all()  # noqa: E711
    )

    if not items_to_migrate:
        logger.info("No InventoryItems need migration")
        return (0, 0)

    logger.info(f"Found {len(items_to_migrate)} InventoryItems to migrate")

    if dry_run:
        logger.info("DRY RUN - no changes made")
        return (len(items_to_migrate), 0)

    purchases_created = 0
    warnings = 0

    for item in items_to_migrate:
        # Determine unit_price from unit_cost
        if item.unit_cost is not None:
            unit_price = Decimal(str(item.unit_cost))
        else:
            unit_price = Decimal("0.00")
            logger.warning(f"InventoryItem {item.id} has NULL unit_cost - using $0.00")
            warnings += 1

        # Determine purchase_date from existing purchase_date
        purchase_date_val = item.purchase_date or date.today()

        # Create Purchase record
        purchase = Purchase(
            product_id=item.product_id,
            supplier_id=unknown_supplier.id,
            purchase_date=purchase_date_val,
            unit_price=unit_price,
            quantity_purchased=max(1, int(item.quantity)) if item.quantity else 1,
            notes=None,  # Notes stay on InventoryItem per FR-014
        )
        session.add(purchase)
        session.flush()  # Get purchase.id

        # Link InventoryItem to Purchase
        item.purchase_id = purchase.id

        # Ensure unit_cost is set
        if item.unit_cost is None:
            item.unit_cost = float(unit_price)

        purchases_created += 1

        if purchases_created % 100 == 0:
            logger.info(f"Processed {purchases_created} items...")

    logger.info(f"Migration complete: {purchases_created} purchases created")
    if warnings > 0:
        logger.warning(f"{warnings} items had NULL unit_cost (set to $0.00)")

    return (len(items_to_migrate), purchases_created)
