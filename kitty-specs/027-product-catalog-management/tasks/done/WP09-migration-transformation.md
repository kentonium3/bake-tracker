---
work_package_id: "WP09"
subtasks:
  - "T074"
  - "T075"
  - "T076"
  - "T077"
  - "T078"
  - "T079"
  - "T080"
  - "T081"
  - "T082"
title: "Migration Transformation"
phase: "Phase 4 - Integration & Migration"
lane: "done"
assignee: ""
agent: "claude"
shell_pid: "61416"
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-22T14:35:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP09 – Migration Transformation

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

**Goal**: Create migration script to transform existing data for new schema per Constitution VI.

**Success Criteria**:
- [ ] Backup JSON created before any changes
- [ ] "Unknown" supplier created for historical data
- [ ] All inventory_additions with price_paid get linked Purchase records
- [ ] All products have is_hidden=False
- [ ] Record counts match before/after (no data loss)
- [ ] FK integrity verified post-migration

## Context & Constraints

**Reference Documents**:
- Constitution VI: `docs/constitution.md` (Migration via export/reset/import)
- Data model: `kitty-specs/027-product-catalog-management/data-model.md`
- Import/Export: WP08 must be complete

**Migration Strategy** (per Constitution VI):
1. Export current data to JSON backup
2. Transform JSON to include new entities/fields
3. Delete database file
4. Recreate schema with new models
5. Import transformed data

**Critical**: This is a DESTRUCTIVE operation. Backup is mandatory.

## Subtasks & Detailed Guidance

### T074 – Create migration script

**Purpose**: Establish script structure with safety checks.

**Steps**:
1. Create `scripts/migrate_f027.py`
2. Add argument parsing:
```python
import argparse
import json
import os
from datetime import datetime
from decimal import Decimal

def parse_args():
    parser = argparse.ArgumentParser(description="Migrate database for F027")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would happen without making changes")
    parser.add_argument("--backup-dir", default="backups",
                        help="Directory for backup files")
    parser.add_argument("--db-path", default="data/bake_tracker.db",
                        help="Path to database file")
    return parser.parse_args()

def main():
    args = parse_args()
    print(f"Migration script for F027 - Product Catalog Management")
    print(f"Database: {args.db_path}")
    print(f"Dry run: {args.dry_run}")

    if not os.path.exists(args.db_path):
        print(f"ERROR: Database not found at {args.db_path}")
        return 1

    # Steps will be added in subsequent tasks
    return 0

if __name__ == "__main__":
    exit(main())
```

**Files**: `scripts/migrate_f027.py` (NEW)

### T075 – Export current data to JSON backup

**Purpose**: Create timestamped backup before transformation.

**Steps**:
```python
from src.services import import_export_service

def backup_current_data(args):
    """Export current database to JSON backup."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(
        args.backup_dir,
        f"pre_f027_migration_{timestamp}.json"
    )

    os.makedirs(args.backup_dir, exist_ok=True)

    print(f"Exporting current data to {backup_file}...")
    data = import_export_service.export_all_to_json_v3()

    with open(backup_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, default=str)

    print(f"Backup created: {backup_file}")
    print(f"  Products: {len(data.get('products', []))}")
    print(f"  Inventory Additions: {len(data.get('inventory_additions', []))}")

    return backup_file, data
```

**Notes**:
- Use `default=str` for JSON to handle Decimal/datetime
- Print counts for verification

### T076 – Create "Unknown" supplier for historical data

**Purpose**: Provide FK target for historical purchases without known supplier.

**Steps**:
```python
def create_unknown_supplier(data):
    """Add Unknown supplier to data for historical records."""
    # Per data-model.md specification
    unknown_supplier = {
        "id": 1,  # Reserve ID 1 for Unknown
        "uuid": "00000000-0000-0000-0000-000000000001",
        "name": "Unknown",
        "city": "Unknown",
        "state": "XX",
        "zip_code": "00000",
        "street_address": None,
        "notes": "Auto-created for historical data without supplier info",
        "is_active": True,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }

    # Initialize suppliers list if not present
    if "suppliers" not in data:
        data["suppliers"] = []

    data["suppliers"].insert(0, unknown_supplier)
    print(f"Created Unknown supplier (ID=1)")

    return data
```

**Notes**:
- State "XX" is intentionally invalid to flag Unknown entries
- Reserved ID=1 ensures consistency across environments

### T077 – Transform inventory_additions to Purchase records

**Purpose**: Create Purchase record for each inventory addition with price.

**Steps**:
```python
def transform_inventory_to_purchases(data):
    """Create Purchase records from inventory_additions price_paid."""
    purchases = []
    purchase_id = 1
    unknown_supplier_id = 1  # Created in T076

    additions = data.get("inventory_additions", [])
    warnings = []

    for addition in additions:
        price_paid = addition.get("price_paid")

        # Skip if no price (nothing to record)
        if price_paid is None:
            warnings.append(f"Addition {addition.get('id')}: No price_paid, skipping purchase")
            continue

        # Handle zero/negative prices
        if float(price_paid) <= 0:
            warnings.append(f"Addition {addition.get('id')}: price_paid={price_paid}, using 0.00")
            price_paid = "0.00"

        purchase = {
            "id": purchase_id,
            "uuid": f"purchase-from-addition-{addition.get('id')}",
            "product_id": addition.get("product_id"),
            "supplier_id": unknown_supplier_id,  # Historical = Unknown
            "purchase_date": addition.get("addition_date"),
            "unit_price": str(price_paid),  # Decimal as string
            "quantity_purchased": 1,  # Each addition = 1 purchase
            "notes": f"Migrated from inventory_addition {addition.get('id')}",
            "created_at": datetime.now().isoformat()
        }
        purchases.append(purchase)
        purchase_id += 1

    data["purchases"] = purchases

    print(f"Created {len(purchases)} Purchase records from inventory_additions")
    if warnings:
        print(f"Warnings ({len(warnings)}):")
        for w in warnings[:5]:  # Show first 5
            print(f"  - {w}")
        if len(warnings) > 5:
            print(f"  ... and {len(warnings) - 5} more")

    return data, purchases
```

**Notes**:
- Each inventory_addition becomes one Purchase
- price_paid → unit_price, addition_date → purchase_date
- quantity_purchased = 1 (one package per addition)

### T078 – Link inventory_additions to new Purchase records

**Purpose**: Set purchase_id FK on transformed inventory_additions.

**Steps**:
```python
def link_additions_to_purchases(data, purchases):
    """Add purchase_id to inventory_additions."""
    # Build mapping: addition_id → purchase_id
    addition_to_purchase = {}
    for purchase in purchases:
        # Extract addition ID from notes
        notes = purchase.get("notes", "")
        if "inventory_addition" in notes:
            try:
                addition_id = int(notes.split("inventory_addition ")[-1])
                addition_to_purchase[addition_id] = purchase["id"]
            except (ValueError, IndexError):
                pass

    linked = 0
    for addition in data.get("inventory_additions", []):
        addition_id = addition.get("id")
        if addition_id in addition_to_purchase:
            addition["purchase_id"] = addition_to_purchase[addition_id]
            linked += 1
        else:
            # No purchase (no price_paid) - leave null
            addition["purchase_id"] = None

    print(f"Linked {linked} inventory_additions to Purchase records")
    return data
```

### T079 – Add is_hidden to all products

**Purpose**: Initialize is_hidden=False for all existing products.

**Steps**:
```python
def initialize_product_fields(data):
    """Add new fields to products."""
    products = data.get("products", [])

    for product in products:
        # is_hidden: default False (visible)
        if "is_hidden" not in product:
            product["is_hidden"] = False

        # preferred_supplier_id: default None (no preferred supplier)
        if "preferred_supplier_id" not in product:
            product["preferred_supplier_id"] = None

    print(f"Initialized new fields for {len(products)} products")
    return data
```

### T080 – Validate transformation

**Purpose**: Verify data integrity before import.

**Steps**:
```python
def validate_transformation(original_data, transformed_data):
    """Validate transformation preserves data and maintains FK integrity."""
    errors = []
    warnings = []

    # Count preservation checks
    orig_products = len(original_data.get("products", []))
    trans_products = len(transformed_data.get("products", []))
    if orig_products != trans_products:
        errors.append(f"Product count mismatch: {orig_products} → {trans_products}")

    orig_additions = len(original_data.get("inventory_additions", []))
    trans_additions = len(transformed_data.get("inventory_additions", []))
    if orig_additions != trans_additions:
        errors.append(f"InventoryAddition count mismatch: {orig_additions} → {trans_additions}")

    # New entities created
    suppliers = len(transformed_data.get("suppliers", []))
    purchases = len(transformed_data.get("purchases", []))
    print(f"New entities: {suppliers} suppliers, {purchases} purchases")

    # FK integrity: all purchases reference valid products
    product_ids = {p["id"] for p in transformed_data.get("products", [])}
    for purchase in transformed_data.get("purchases", []):
        if purchase["product_id"] not in product_ids:
            errors.append(f"Purchase {purchase['id']} references invalid product {purchase['product_id']}")

    # FK integrity: all additions with purchase_id reference valid purchases
    purchase_ids = {p["id"] for p in transformed_data.get("purchases", [])}
    for addition in transformed_data.get("inventory_additions", []):
        pid = addition.get("purchase_id")
        if pid is not None and pid not in purchase_ids:
            errors.append(f"Addition {addition['id']} references invalid purchase {pid}")

    # Validate all products have new fields
    for product in transformed_data.get("products", []):
        if "is_hidden" not in product:
            errors.append(f"Product {product['id']} missing is_hidden field")

    # Report
    print(f"\nValidation Results:")
    print(f"  Products: {orig_products} (preserved)")
    print(f"  Inventory Additions: {orig_additions} (preserved)")
    print(f"  New Purchases: {purchases}")
    print(f"  New Suppliers: {suppliers}")

    if errors:
        print(f"\nERRORS ({len(errors)}):")
        for e in errors:
            print(f"  - {e}")
        return False

    if warnings:
        print(f"\nWarnings ({len(warnings)}):")
        for w in warnings:
            print(f"  - {w}")

    print(f"\nValidation PASSED")
    return True
```

### T081 – Create rollback instructions

**Purpose**: Document recovery procedure in script comments.

**Steps**:
Add to script header:
```python
"""
Migration Script: F027 Product Catalog Management

PURPOSE:
  Transform existing data for new schema including Supplier and Purchase entities.

MIGRATION STRATEGY (per Constitution VI):
  1. Export current data to JSON backup
  2. Transform JSON to include new entities/fields
  3. Delete database file (DESTRUCTIVE)
  4. Recreate schema with new models
  5. Import transformed data

ROLLBACK PROCEDURE:
  If migration fails or produces incorrect results:

  1. Stop the application

  2. Delete the new database:
     rm data/bake_tracker.db

  3. Restore from pre-migration backup:
     - Locate backup in backups/pre_f027_migration_*.json
     - Use import_export_service.import_all_from_json_v3()
     - Or: restore from your own backup if you made one

  4. Verify restoration:
     - Check record counts match original
     - Test application functionality

  5. Report issues before retrying migration

BACKUP LOCATION:
  backups/pre_f027_migration_YYYYMMDD_HHMMSS.json

USAGE:
  # Dry run (recommended first):
  python scripts/migrate_f027.py --dry-run

  # Execute migration:
  python scripts/migrate_f027.py

  # With custom paths:
  python scripts/migrate_f027.py --db-path /path/to/db --backup-dir /path/to/backups
"""
```

### T082 – Write migration validation tests

**Purpose**: Test migration transformation logic.

**Steps**:
Create `src/tests/migration/test_f027_migration.py`:
```python
import pytest
from datetime import date
from decimal import Decimal

# Import migration functions (adjust path as needed)
# These would be refactored to be importable for testing

class TestF027Migration:
    """Tests for F027 migration transformation."""

    def test_unknown_supplier_created(self):
        """Unknown supplier has required fields."""
        data = {}
        # Call create_unknown_supplier
        # Assert supplier exists with ID=1, state="XX"
        pass

    def test_inventory_addition_to_purchase(self):
        """Each inventory_addition with price becomes a Purchase."""
        data = {
            "inventory_additions": [
                {"id": 1, "product_id": 10, "price_paid": "5.99", "addition_date": "2025-01-01"},
                {"id": 2, "product_id": 10, "price_paid": None, "addition_date": "2025-01-02"},
            ]
        }
        # Transform
        # Assert 1 purchase created (second has no price)
        pass

    def test_purchase_links_to_addition(self):
        """Additions get purchase_id after transformation."""
        # Create test data, transform, verify linkage
        pass

    def test_products_get_new_fields(self):
        """All products have is_hidden and preferred_supplier_id."""
        data = {
            "products": [
                {"id": 1, "product_name": "Test"},
            ]
        }
        # Transform
        # Assert is_hidden=False, preferred_supplier_id=None
        pass

    def test_validation_catches_missing_product(self):
        """Validation fails if purchase references nonexistent product."""
        pass

    def test_record_counts_preserved(self):
        """Original record counts match after transformation."""
        pass

    def test_zero_price_handled(self):
        """Zero/negative prices logged as warning, use 0.00."""
        pass
```

**Files**: `src/tests/migration/test_f027_migration.py` (NEW)

## Test Strategy

**Migration Tests** (T082):
- Unit tests for each transformation function
- Validation logic tests
- Edge case handling (null prices, missing fields)

**Integration Test**:
- Full round-trip: backup → transform → validate
- Use test database, not production

**Commands**:
```bash
# Run migration tests
pytest src/tests/migration/test_f027_migration.py -v

# Dry-run migration
python scripts/migrate_f027.py --dry-run
```

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Data loss during migration | Mandatory backup before any changes |
| FK integrity issues | Validation step before import |
| Null price_paid handling | Default to 0.00 with warning log |
| ID conflicts | Use predictable ID generation |
| Partial migration failure | Transaction-like approach: transform fully before any DB changes |

## Definition of Done Checklist

- [ ] Migration script created with argument parsing
- [ ] Backup exported before transformation
- [ ] Unknown supplier created with reserved ID
- [ ] Purchases created from inventory_additions
- [ ] Additions linked to new purchases
- [ ] Products have is_hidden=False
- [ ] Validation passes (counts, FK integrity)
- [ ] Rollback instructions documented
- [ ] Migration tests written and passing
- [ ] Dry-run mode works correctly

## Review Guidance

**Key Checkpoints**:
1. Backup is created BEFORE any transformation
2. Unknown supplier uses reserved ID=1 and state="XX"
3. Every inventory_addition with price_paid gets a Purchase
4. Validation runs BEFORE any database changes
5. Dry-run shows what would happen without changing anything
6. Rollback instructions are clear and complete

## Activity Log

- 2025-12-22T14:35:00Z – system – lane=planned – Prompt created via /spec-kitty.tasks
- 2025-12-22T23:53:40Z – claude – shell_pid=61416 – lane=doing – Starting implementation
- 2025-12-22T23:59:32Z – claude – shell_pid=61416 – lane=for_review – Implementation complete: migrate_f027.py with 7-step transformation (backup, unknown supplier, inventory-to-purchases, linking, product fields, validation, execution), 27 unit tests passing
- 2025-12-23T00:00:01Z – claude – shell_pid=61416 – lane=for_review – Implementation complete: T074-T082 all done. Migration script with 7-step transformation, 27 unit tests passing.
- 2025-12-23T02:57:23Z – claude – shell_pid=61416 – lane=done – Code review APPROVED: 27 migration tests pass. migrate_f027.py with 7-step transformation, dry-run mode, rollback docs
