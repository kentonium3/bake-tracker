---
work_package_id: "WP04"
subtasks:
  - "T015"
  - "T016"
  - "T017"
  - "T018"
  - "T019"
title: "Migration and Validation Scripts"
phase: "Phase 3 - Migration"
lane: "for_review"
assignee: ""
agent: "system"
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-22T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP04 - Migration and Validation Scripts

## Review Feedback

> **Populated by `/spec-kitty.review`** - Reviewers add detailed feedback here when work needs changes.

*[This section is empty initially.]*

---

## Objectives & Success Criteria

**Goal**: Create migration script to link existing InventoryItems to Purchase records, plus validation script to verify migration success.

**Success Criteria**:
- Migration script creates Purchase records for all InventoryItems with NULL purchase_id
- All migrated Purchases assigned to "Unknown" supplier
- InventoryItem.purchase_id and unit_cost populated correctly
- Validation script confirms 100% linkage
- Zero data loss (record counts match)
- All existing tests continue to pass

**User Story**: US5 (Data Migration from Existing Inventory)
**Functional Requirements**: FR-011, FR-012

---

## Context & Constraints

**Reference Documents**:
- `kitty-specs/028-purchase-tracking-enhanced/spec.md` - FR-011, FR-012
- `kitty-specs/028-purchase-tracking-enhanced/plan.md` - Section 3
- `docs/design/F027_product_catalog_management.md` - Unknown supplier details
- `.kittify/memory/constitution.md` - Principle VI (export/reset/import)

**Unknown Supplier** (from F027):
- name: "Unknown"
- city: "Unknown"
- state: "XX"
- zip_code: "00000"

**Constraints**:
- Uses export/reset/import pattern per Constitution VI
- Must handle NULL unit_cost (use 0.00 fallback)
- Must log warnings for edge cases
- Single transaction for atomicity

---

## Subtasks & Detailed Guidance

### Subtask T015 - Create Migration Script

**Purpose**: Create the main migration script file with structure.

**Steps**:
1. Create `src/services/migration/` directory if needed
2. Create `src/services/migration/__init__.py`
3. Create `src/services/migration/f028_migration.py`
4. Define main migration function structure

**File Structure**:
```python
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


def run_migration(dry_run: bool = False) -> Tuple[int, int]:
    """
    Run F028 migration to link InventoryItems to Purchase records.

    Args:
        dry_run: If True, report what would be done without making changes

    Returns:
        Tuple of (items_processed, purchases_created)
    """
    with session_scope() as session:
        return _run_migration_impl(session, dry_run)


def _run_migration_impl(session: Session, dry_run: bool) -> Tuple[int, int]:
    """Implementation of migration."""
    # Implementation in T016 and T017
    pass
```

**Files**: `src/services/migration/f028_migration.py`
**Parallel?**: No - foundation for T016, T017

---

### Subtask T016 - Implement Find/Create Unknown Supplier

**Purpose**: Locate or create the Unknown supplier for migration fallback.

**Steps**:
1. Query for supplier with name="Unknown"
2. If not found, create with F027 defaults
3. Log action taken

**Implementation**:
```python
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
```

**Files**: `src/services/migration/f028_migration.py`
**Parallel?**: No - sequential after T015

---

### Subtask T017 - Implement Linking Logic

**Purpose**: Create Purchase records and link to existing InventoryItems.

**Steps**:
1. Query InventoryItems where purchase_id IS NULL
2. For each item, create Purchase record
3. Set purchase_id on InventoryItem
4. Set unit_cost if NULL (fallback to 0.00)
5. Log progress and warnings

**Implementation**:
```python
def _run_migration_impl(session: Session, dry_run: bool) -> Tuple[int, int]:
    """Implementation of migration."""
    # Get Unknown supplier
    unknown_supplier = _get_or_create_unknown_supplier(session)

    # Find items needing migration
    items_to_migrate = (
        session.query(InventoryItem)
        .filter(InventoryItem.purchase_id == None)
        .all()
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
            logger.warning(
                f"InventoryItem {item.id} has NULL unit_cost - using $0.00"
            )
            warnings += 1

        # Determine purchase_date from added_date
        purchase_date = item.added_date or date.today()

        # Create Purchase record
        purchase = Purchase(
            product_id=item.product_id,
            supplier_id=unknown_supplier.id,
            purchase_date=purchase_date,
            unit_price=unit_price,
            quantity_purchased=int(item.quantity) if item.quantity else 1,
            notes=None,  # Notes stay on InventoryItem
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
```

**Files**: `src/services/migration/f028_migration.py`
**Parallel?**: No - sequential after T016

---

### Subtask T018 - Create Validation Script

**Purpose**: Verify migration success with comprehensive checks.

**Steps**:
1. Create `src/services/migration/f028_validation.py`
2. Implement validation checks
3. Return pass/fail with details

**Implementation**:
```python
"""
F028 Validation: Verify migration success.

Usage:
    from src.services.migration.f028_validation import validate_migration
    success, report = validate_migration()
"""

import logging
from typing import Tuple, Dict, Any

from sqlalchemy.orm import Session

from src.models import InventoryItem, Purchase, Supplier
from src.services.database import session_scope

logger = logging.getLogger(__name__)


def validate_migration() -> Tuple[bool, Dict[str, Any]]:
    """
    Validate F028 migration success.

    Returns:
        Tuple of (success: bool, report: dict)
    """
    with session_scope() as session:
        return _validate_impl(session)


def _validate_impl(session: Session) -> Tuple[bool, Dict[str, Any]]:
    """Implementation of validation."""
    report = {
        "checks": [],
        "errors": [],
        "warnings": [],
    }

    # Check 1: No NULL purchase_id
    null_purchase_count = (
        session.query(InventoryItem)
        .filter(InventoryItem.purchase_id == None)
        .count()
    )
    if null_purchase_count > 0:
        report["errors"].append(
            f"FAIL: {null_purchase_count} InventoryItems have NULL purchase_id"
        )
    else:
        report["checks"].append("PASS: All InventoryItems have purchase_id")

    # Check 2: All linked Purchases exist
    orphaned = (
        session.query(InventoryItem)
        .filter(InventoryItem.purchase_id != None)
        .filter(~InventoryItem.purchase.has())
        .count()
    )
    if orphaned > 0:
        report["errors"].append(
            f"FAIL: {orphaned} InventoryItems reference non-existent Purchases"
        )
    else:
        report["checks"].append("PASS: All purchase_id references are valid")

    # Check 3: Product IDs match
    mismatched = 0
    items_with_purchase = (
        session.query(InventoryItem)
        .filter(InventoryItem.purchase_id != None)
        .all()
    )
    for item in items_with_purchase:
        if item.purchase and item.product_id != item.purchase.product_id:
            mismatched += 1

    if mismatched > 0:
        report["errors"].append(
            f"FAIL: {mismatched} items have product_id mismatch with Purchase"
        )
    else:
        report["checks"].append("PASS: All product_id values match")

    # Check 4: unit_cost populated
    null_unit_cost = (
        session.query(InventoryItem)
        .filter(InventoryItem.unit_cost == None)
        .count()
    )
    if null_unit_cost > 0:
        report["warnings"].append(
            f"WARNING: {null_unit_cost} InventoryItems have NULL unit_cost"
        )
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


def print_validation_report(report: Dict[str, Any]):
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
```

**Files**: `src/services/migration/f028_validation.py`
**Parallel?**: No - depends on migration structure

---

### Subtask T019 - Write Tests for Migration

**Purpose**: Verify migration scripts work correctly.

**Test Cases** (`src/tests/services/test_f028_migration.py`):

```python
"""Tests for F028 migration scripts."""

import pytest
from decimal import Decimal

from src.models import InventoryItem, Purchase, Supplier
from src.services.migration.f028_migration import run_migration
from src.services.migration.f028_validation import validate_migration


class TestF028Migration:
    """Test suite for migration scripts."""

    def test_migration_creates_purchases(self, session, inventory_items_without_purchases):
        """Migration creates Purchase for each unlinked InventoryItem."""
        # Setup: items without purchase_id
        initial_count = len(inventory_items_without_purchases)

        # Run migration
        items_processed, purchases_created = run_migration()

        assert items_processed == initial_count
        assert purchases_created == initial_count

    def test_migration_uses_unknown_supplier(self, session, inventory_item_without_purchase):
        """Migrated purchases use Unknown supplier."""
        run_migration()

        item = session.query(InventoryItem).get(inventory_item_without_purchase.id)
        purchase = session.query(Purchase).get(item.purchase_id)

        assert purchase.supplier.name == "Unknown"

    def test_migration_preserves_unit_cost(self, session, inventory_item_with_unit_cost):
        """Migration uses existing unit_cost for Purchase.unit_price."""
        original_cost = inventory_item_with_unit_cost.unit_cost

        run_migration()

        item = session.query(InventoryItem).get(inventory_item_with_unit_cost.id)
        purchase = session.query(Purchase).get(item.purchase_id)

        assert float(purchase.unit_price) == original_cost

    def test_migration_handles_null_unit_cost(self, session, inventory_item_without_unit_cost):
        """Migration handles NULL unit_cost with $0.00 fallback."""
        run_migration()

        item = session.query(InventoryItem).get(inventory_item_without_unit_cost.id)
        purchase = session.query(Purchase).get(item.purchase_id)

        assert purchase.unit_price == Decimal("0.00")
        assert item.unit_cost == 0.0

    def test_migration_dry_run(self, session, inventory_items_without_purchases):
        """Dry run reports but doesn't modify data."""
        items_processed, purchases_created = run_migration(dry_run=True)

        assert items_processed > 0
        assert purchases_created == 0

        # Verify no changes
        null_count = (
            session.query(InventoryItem)
            .filter(InventoryItem.purchase_id == None)
            .count()
        )
        assert null_count == items_processed

    def test_validation_passes_after_migration(self, session, inventory_items_without_purchases):
        """Validation passes after successful migration."""
        run_migration()

        success, report = validate_migration()

        assert success is True
        assert len(report["errors"]) == 0

    def test_validation_fails_with_unlinked_items(self, session, inventory_items_without_purchases):
        """Validation fails when items lack purchase_id."""
        # Don't run migration

        success, report = validate_migration()

        assert success is False
        assert any("NULL purchase_id" in e for e in report["errors"])
```

**Files**: `src/tests/services/test_f028_migration.py`
**Parallel?**: Yes - can be written alongside implementation

---

## Test Strategy

**Run Tests**:
```bash
pytest src/tests/services/test_f028_migration.py -v
```

**Manual Verification**:
1. Export database before migration
2. Run migration on test data
3. Run validation script
4. Verify all checks pass

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Data loss | Export before migration, validation after |
| Unknown supplier missing | Create if not found |
| NULL unit_cost | Use $0.00 fallback with warning |
| Performance on large datasets | Process in batches if needed |

---

## Definition of Done Checklist

- [ ] Migration script creates Purchases for unlinked items
- [ ] Unknown supplier used for all migrated Purchases
- [ ] InventoryItem.purchase_id set correctly
- [ ] NULL unit_cost handled with $0.00 fallback
- [ ] Validation script checks all requirements
- [ ] Tests written and passing
- [ ] Existing application tests still pass

---

## Review Guidance

**Verification Checkpoints**:
1. Migration handles edge cases (NULL unit_cost, missing Unknown supplier)
2. Validation catches all failure modes
3. Dry run works correctly
4. Logging is helpful for debugging
5. Tests cover happy path + edge cases

---

## Activity Log

- 2025-12-22T00:00:00Z - system - lane=planned - Prompt created via /spec-kitty.tasks.
- 2025-12-23T14:40:03Z – system – shell_pid= – lane=doing – Moved to doing
- 2025-12-23T14:45:08Z – system – shell_pid= – lane=for_review – Moved to for_review
