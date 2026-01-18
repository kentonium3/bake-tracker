---
work_package_id: WP04
title: Export/Import Integration
lane: "doing"
dependencies: []
subtasks: [T018, T019, T020, T021, T022]
agent: "claude"
history:
- date: '2026-01-17'
  action: created
  agent: claude
estimated_lines: 400
priority: P3
---

# WP04: Export/Import Integration

**Feature**: F057 Purchase Management with Provisional Products
**Objective**: Extend coordinated_export_service to handle `is_provisional` field and create provisional products for unknown items during import.

## Implementation Command

```bash
spec-kitty implement WP04 --base WP01
```

## Context

This work package implements User Story 3: Import Purchases from JSON File. The export/import system needs to:
1. Include `is_provisional` in product exports
2. Handle missing `is_provisional` field during import (default to False)
3. Create provisional products for unknown items during transaction import

**Reference File**: `src/services/coordinated_export_service.py`

The service handles full backup/restore with entity ordering for foreign key resolution. Products are exported as part of the catalog data.

**Key Design Decisions** (from plan.md):
- Backward compatible: missing field defaults to `False`
- Unknown products created as provisional with minimal fields
- Import results include count of provisional products created

## Subtasks

### T018: Update export to include `is_provisional` field in product records

**Purpose**: Ensure exported backups include the provisional flag for complete data preservation.

**File**: `src/services/coordinated_export_service.py`

**Steps**:

1. Locate the product export section in `_export_entity_records()`:
```python
# Find the section that handles Product export (around line 500-600)
elif entity_type == "products":
    records = session.query(Product).all()
    for obj in records:
        record = {
            "ingredient_id": obj.ingredient_id,
            "brand": obj.brand,
            "product_name": obj.product_name,
            # ... other fields ...
        }
```

2. Add `is_provisional` to the exported fields:
```python
record = {
    "ingredient_id": obj.ingredient_id,
    "brand": obj.brand,
    "product_name": obj.product_name,
    "package_unit": obj.package_unit,
    "package_unit_quantity": obj.package_unit_quantity,
    "package_size": obj.package_size,
    "package_type": obj.package_type,
    "upc_code": obj.upc_code,
    "gtin": obj.gtin,
    "is_hidden": obj.is_hidden,
    "is_provisional": obj.is_provisional,  # F057: Add provisional flag
    "preferred": obj.preferred,
    "preferred_supplier_id": obj.preferred_supplier_id,
    # ... rest of fields ...
}
```

**Validation**:
- [ ] Export JSON includes `is_provisional` field for each product
- [ ] Regular products show `is_provisional: false`
- [ ] Provisional products show `is_provisional: true`
- [ ] Export still completes successfully

---

### T019: Update import to handle missing `is_provisional` field (default False)

**Purpose**: Ensure backward compatibility with existing backup files that don't have the field.

**File**: `src/services/coordinated_export_service.py`

**Steps**:

1. Locate the product import section in `_import_entity_records()`:
```python
# Find the section that handles Product import (around line 1000-1100)
elif entity_type == "products":
    for record in records:
        product = Product(
            ingredient_id=record.get("ingredient_id"),
            brand=record.get("brand"),
            # ... other fields ...
        )
```

2. Add handling for `is_provisional` with default:
```python
for record in records:
    product = Product(
        ingredient_id=record.get("ingredient_id"),
        brand=record.get("brand"),
        product_name=record.get("product_name"),
        package_unit=record.get("package_unit"),
        package_unit_quantity=record.get("package_unit_quantity"),
        package_size=record.get("package_size"),
        package_type=record.get("package_type"),
        upc_code=record.get("upc_code"),
        gtin=record.get("gtin"),
        is_hidden=record.get("is_hidden", False),
        is_provisional=record.get("is_provisional", False),  # F057: Default False
        preferred=record.get("preferred", False),
        preferred_supplier_id=record.get("preferred_supplier_id"),
        # ... rest of fields ...
    )
```

**Validation**:
- [ ] Import with `is_provisional: true` preserves the flag
- [ ] Import with `is_provisional: false` sets flag to False
- [ ] Import without `is_provisional` field defaults to False
- [ ] Existing backup files import successfully

---

### T020: Add unknown product detection during transaction import

**Purpose**: Identify purchases that reference products not in the catalog.

**File**: `src/services/coordinated_export_service.py` or `src/services/transaction_import_service.py`

**Context**: The transaction import handles purchases and inventory items. When importing purchases, we need to detect if the referenced product doesn't exist.

**Steps**:

1. Locate the purchase import logic. It may be in:
   - `coordinated_export_service.py` - full backup import
   - `transaction_import_service.py` - standalone transaction import

2. Add unknown product detection before creating purchase:
```python
def _import_purchases(self, records: List[Dict], session: Session) -> Dict:
    """Import purchase records, creating provisional products for unknowns."""
    results = {
        "imported": 0,
        "skipped": 0,
        "errors": [],
        "provisional_products_created": 0,  # F057: Track provisional creations
    }

    for record in records:
        product_id = record.get("product_id")

        # Check if product exists
        product = session.query(Product).filter(Product.id == product_id).first()

        if not product:
            # F057: Product doesn't exist - attempt to create provisional
            # This requires product data in the record or ability to infer it
            if self._can_create_provisional(record):
                try:
                    product = self._create_provisional_from_record(record, session)
                    results["provisional_products_created"] += 1
                except Exception as e:
                    results["errors"].append(f"Failed to create provisional: {e}")
                    results["skipped"] += 1
                    continue
            else:
                results["errors"].append(f"Product {product_id} not found, insufficient data for provisional")
                results["skipped"] += 1
                continue

        # Continue with purchase import using product...
```

3. Add helper to check if we have enough data:
```python
def _can_create_provisional(self, record: Dict) -> bool:
    """Check if record has enough data to create provisional product."""
    # Need at minimum: something to identify the product
    has_product_info = any([
        record.get("product_brand"),
        record.get("product_name"),
        record.get("upc_code"),
        record.get("ingredient_name"),
    ])
    return has_product_info
```

**Validation**:
- [ ] Unknown product detected during import
- [ ] Sufficient data check works correctly
- [ ] Skips record when insufficient data
- [ ] Error message helpful for debugging

---

### T021: Create provisional products for unknown items with minimal required fields

**Purpose**: Auto-create provisional products to allow import to complete.

**File**: `src/services/coordinated_export_service.py`

**Steps**:

1. Add helper method to create provisional from import record:
```python
def _create_provisional_from_record(
    self, record: Dict, session: Session
) -> Product:
    """Create provisional product from import record data.

    Attempts to extract or infer required fields from the record.

    Args:
        record: Import record with product-related fields
        session: Database session

    Returns:
        Created provisional Product

    Raises:
        ValueError: If required fields cannot be determined
    """
    from src.services.product_service import create_provisional_product

    # Try to determine ingredient
    ingredient_id = self._resolve_ingredient_id(record, session)
    if not ingredient_id:
        raise ValueError("Cannot determine ingredient for provisional product")

    # Extract available fields
    brand = record.get("product_brand") or record.get("brand") or "Unknown"
    product_name = record.get("product_name")
    upc_code = record.get("upc_code")

    # Package info - use defaults if not available
    package_unit = record.get("package_unit") or "each"
    package_unit_quantity = record.get("package_unit_quantity") or 1.0

    # Create the provisional product
    product = create_provisional_product(
        ingredient_id=ingredient_id,
        brand=brand,
        package_unit=package_unit,
        package_unit_quantity=float(package_unit_quantity),
        product_name=product_name,
        upc_code=upc_code,
        session=session,
    )

    return product

def _resolve_ingredient_id(self, record: Dict, session: Session) -> Optional[int]:
    """Attempt to resolve ingredient ID from record data.

    Tries multiple strategies:
    1. Direct ingredient_id in record
    2. Lookup by ingredient_name
    3. Lookup by ingredient_slug
    """
    from src.models import Ingredient

    # Strategy 1: Direct ID
    if record.get("ingredient_id"):
        ing = session.query(Ingredient).filter(
            Ingredient.id == record["ingredient_id"]
        ).first()
        if ing and ing.hierarchy_level == 2:  # Must be leaf
            return ing.id

    # Strategy 2: By name
    if record.get("ingredient_name"):
        ing = session.query(Ingredient).filter(
            Ingredient.name == record["ingredient_name"]
        ).first()
        if ing and ing.hierarchy_level == 2:
            return ing.id
        # Try display_name
        ing = session.query(Ingredient).filter(
            Ingredient.display_name == record["ingredient_name"]
        ).first()
        if ing and ing.hierarchy_level == 2:
            return ing.id

    # Strategy 3: By slug
    if record.get("ingredient_slug"):
        ing = session.query(Ingredient).filter(
            Ingredient.slug == record["ingredient_slug"]
        ).first()
        if ing and ing.hierarchy_level == 2:
            return ing.id

    return None
```

**Validation**:
- [ ] Provisional product created with correct `is_provisional=True`
- [ ] Brand defaults to "Unknown" when not available
- [ ] Package defaults to "1 each" when not available
- [ ] Ingredient resolution tries multiple strategies
- [ ] Raises helpful error when ingredient can't be determined

---

### T022: Return import results with provisional products count

**Purpose**: Inform user about provisional products created during import.

**File**: `src/services/coordinated_export_service.py`

**Steps**:

1. Ensure results dict includes provisional count:
```python
def import_complete(self, backup_path: str) -> Dict[str, Any]:
    """Import complete backup from file.

    Returns:
        Dict with import results:
            - success: bool
            - message: str
            - entity_counts: Dict[str, int] - count per entity type
            - errors: List[str]
            - provisional_products_created: int  # F057: New field
    """
    results = {
        "success": True,
        "message": "",
        "entity_counts": {},
        "errors": [],
        "provisional_products_created": 0,  # F057
    }

    # ... existing import logic ...

    # After importing purchases, add provisional count
    if purchase_results:
        results["provisional_products_created"] = purchase_results.get(
            "provisional_products_created", 0
        )

    return results
```

2. Update the result message to include provisional info:
```python
# In the success path:
if results["provisional_products_created"] > 0:
    results["message"] += (
        f"\n{results['provisional_products_created']} provisional product(s) "
        "created for unknown items. Review these in Products tab."
    )
```

3. Ensure UI displays the provisional count (if import dialog exists):
```python
# In src/ui/import_export_dialog.py or wherever results are shown:
def _show_import_results(self, results: Dict) -> None:
    """Display import results to user."""
    message = results.get("message", "Import complete")

    # F057: Add provisional product info
    provisional_count = results.get("provisional_products_created", 0)
    if provisional_count > 0:
        message += f"\n\n{provisional_count} provisional product(s) created."
        message += "\nVisit Products tab > 'Needs Review' to complete their details."

    messagebox.showinfo("Import Complete", message, parent=self)
```

**Validation**:
- [ ] Results dict includes `provisional_products_created` key
- [ ] Count is accurate
- [ ] User-facing message mentions provisional products
- [ ] Message suggests reviewing in Products tab
- [ ] Zero count doesn't add extra message

---

## Definition of Done

- [ ] All 5 subtasks completed
- [ ] Export includes `is_provisional` field
- [ ] Import handles missing field (defaults to False)
- [ ] Unknown products detected during transaction import
- [ ] Provisional products created with minimal required fields
- [ ] Import results include provisional count
- [ ] Existing backup files still import correctly
- [ ] Manual test: Export, modify to remove is_provisional, import - verify defaults

## Integration Test Scenario

```python
def test_import_with_unknown_products():
    """Test that unknown products become provisional during import."""
    # Setup: Create import file with purchase referencing non-existent product
    import_data = {
        "purchases": [{
            "product_id": 99999,  # Doesn't exist
            "product_brand": "New Brand",
            "ingredient_name": "All-Purpose Flour",
            "package_unit": "lb",
            "quantity_purchased": 2,
            "unit_price": 5.99,
            "purchase_date": "2026-01-15",
            "store": "Test Store",
        }]
    }

    # Execute import
    results = coordinated_export_service.import_complete(import_data)

    # Verify provisional product created
    assert results["provisional_products_created"] == 1

    # Verify product exists and is provisional
    products = product_catalog_service.get_provisional_products()
    assert any(p["brand"] == "New Brand" for p in products)

    # Verify purchase linked to new product
    # ... additional assertions ...
```

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Ingredient not found | Log warning, skip record with helpful error message |
| Duplicate provisional creation | Check for existing product before creating |
| Import performance with many unknowns | Batch provisional creation where possible |
| Breaking existing backup compatibility | Default False for missing field, thorough testing |

## Reviewer Notes

When reviewing this WP:
1. Test with backup files from before this feature
2. Verify provisional products have all required fields populated
3. Check that import errors are logged clearly
4. Test edge cases: empty brand, no ingredient data, duplicate UPC
5. Verify results count accuracy

## Activity Log

- 2026-01-18T02:20:13Z – claude – lane=doing – Starting implementation of JSON Import Integration
