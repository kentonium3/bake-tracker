---
work_package_id: "WP08"
subtasks:
  - "T065"
  - "T066"
  - "T067"
  - "T068"
  - "T069"
  - "T070"
  - "T071"
  - "T072"
  - "T073"
title: "Import/Export Updates"
phase: "Phase 4 - Integration & Migration"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-22T14:35:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP08 – Import/Export Updates

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

**Goal**: Update import_export_service to handle Supplier, Purchase, and modified entities.

**Success Criteria**:
- [ ] Export includes all new entities (Supplier, Purchase)
- [ ] Export includes new Product fields (preferred_supplier_id, is_hidden)
- [ ] Export includes new InventoryAddition field (purchase_id)
- [ ] Import restores all entities in correct order
- [ ] Round-trip test passes (export → reset → import → verify)

## Context & Constraints

**Reference Documents**:
- Existing service: `src/services/import_export_service.py`
- Data model: `kitty-specs/027-product-catalog-management/data-model.md` (Migration section)

**Critical**: Import order matters for FK resolution:
1. Suppliers
2. Products
3. Purchases
4. InventoryAdditions

## Subtasks & Detailed Guidance

### T065 – Update export to include suppliers

**Purpose**: Add suppliers to exported JSON.

**Steps**:
1. Open `src/services/import_export_service.py`
2. In `export_all_to_json_v3()` or equivalent:
```python
# Add suppliers export
suppliers = session.query(Supplier).all()
data["suppliers"] = [s.to_dict() for s in suppliers]
```

**Notes**:
- Export ALL suppliers (including inactive) for data completeness
- Ensure to_dict() includes is_active field

### T066 – Update export to include purchases

**Purpose**: Add purchases to exported JSON.

**Steps**:
```python
# Add purchases export (after suppliers and products)
purchases = session.query(Purchase).all()
data["purchases"] = [p.to_dict() for p in purchases]
```

**Notes**:
- Purchase.to_dict() should include product_id, supplier_id, etc.
- Export all purchases regardless of product hidden status

### T067 – Update export for new Product fields

**Purpose**: Include preferred_supplier_id and is_hidden in product export.

**Steps**:
Verify Product.to_dict() includes:
```python
{
    ...
    "preferred_supplier_id": self.preferred_supplier_id,
    "is_hidden": self.is_hidden,
    ...
}
```

If not already in to_dict(), update the model's to_dict method.

### T068 – Update export for new InventoryAddition field

**Purpose**: Include purchase_id in inventory addition export.

**Steps**:
Verify InventoryAddition.to_dict() includes:
```python
{
    ...
    "purchase_id": self.purchase_id,
    ...
}
```

**Notes**:
- purchase_id may be None for old data during transition
- Still export it (as null in JSON)

### T069 – Update import to handle suppliers

**Purpose**: Import suppliers before dependent entities.

**Steps**:
In `import_all_from_json_v3()`:
```python
# Import suppliers FIRST (before products)
if "suppliers" in data:
    for supplier_data in data["suppliers"]:
        supplier = Supplier(
            id=supplier_data.get("id"),
            uuid=supplier_data.get("uuid"),
            name=supplier_data["name"],
            city=supplier_data["city"],
            state=supplier_data["state"],
            zip_code=supplier_data["zip_code"],
            street_address=supplier_data.get("street_address"),
            notes=supplier_data.get("notes"),
            is_active=supplier_data.get("is_active", True),
            created_at=parse_datetime(supplier_data.get("created_at")),
            updated_at=parse_datetime(supplier_data.get("updated_at"))
        )
        session.add(supplier)
    session.flush()  # Ensure IDs available for FK references
```

**Notes**:
- Import before products (products reference suppliers)
- Preserve original IDs for FK consistency

### T070 – Update import to handle purchases

**Purpose**: Import purchases after products and suppliers.

**Steps**:
```python
# Import purchases AFTER products and suppliers
if "purchases" in data:
    for purchase_data in data["purchases"]:
        purchase = Purchase(
            id=purchase_data.get("id"),
            uuid=purchase_data.get("uuid"),
            product_id=purchase_data["product_id"],
            supplier_id=purchase_data["supplier_id"],
            purchase_date=parse_date(purchase_data["purchase_date"]),
            unit_price=Decimal(str(purchase_data["unit_price"])),
            quantity_purchased=purchase_data["quantity_purchased"],
            notes=purchase_data.get("notes"),
            created_at=parse_datetime(purchase_data.get("created_at"))
        )
        session.add(purchase)
    session.flush()
```

**Notes**:
- Parse unit_price as Decimal for precision
- Parse purchase_date as date object
- No updated_at for Purchase (immutable)

### T071 – Update import for new Product/InventoryAddition fields

**Purpose**: Handle new fields during product and inventory import.

**Steps**:
Update product import:
```python
product = Product(
    ...
    preferred_supplier_id=product_data.get("preferred_supplier_id"),
    is_hidden=product_data.get("is_hidden", False),
    ...
)
```

Update inventory addition import:
```python
inventory_addition = InventoryAddition(
    ...
    purchase_id=inventory_data.get("purchase_id"),
    ...
)
```

**Notes**:
- Handle None/missing values gracefully
- is_hidden defaults to False if not present (backward compat)

### T072 – Ensure import order

**Purpose**: Import entities in FK-safe order.

**Steps**:
Verify/update import function to follow this order:
```python
def import_all_from_json_v3(data, session=None):
    # Order is critical for FK resolution!
    # 1. Base entities (no FKs)
    _import_categories(data, session)
    _import_suppliers(data, session)  # NEW
    _import_ingredients(data, session)

    # 2. Entities with FKs to base
    _import_recipes(data, session)
    _import_products(data, session)  # References suppliers, ingredients

    # 3. Entities with FKs to products
    _import_purchases(data, session)  # NEW - References products, suppliers
    _import_inventory_items(data, session)
    _import_inventory_additions(data, session)  # References purchases

    # 4. Junction tables and events...
```

### T073 – Write integration tests

**Purpose**: Verify round-trip export/import.

**Steps**:
Create/update `src/tests/integration/test_product_catalog.py`:
```python
def test_export_includes_suppliers():
    """Verify suppliers appear in export."""
    ...

def test_export_includes_purchases():
    """Verify purchases appear in export."""
    ...

def test_export_includes_product_new_fields():
    """Verify preferred_supplier_id and is_hidden in export."""
    ...

def test_import_suppliers():
    """Verify suppliers import correctly."""
    ...

def test_import_purchases():
    """Verify purchases import correctly."""
    ...

def test_round_trip_with_new_entities():
    """Full round-trip: create data, export, clear, import, verify."""
    # Create test data
    supplier = supplier_service.create_supplier(...)
    product = product_catalog_service.create_product(..., preferred_supplier_id=supplier["id"])
    purchase = product_catalog_service.create_purchase(...)

    # Export
    data = import_export_service.export_all_to_json_v3()

    # Clear database (or use fresh test DB)
    ...

    # Import
    import_export_service.import_all_from_json_v3(data)

    # Verify
    imported_supplier = supplier_service.get_supplier(supplier["id"])
    assert imported_supplier["name"] == supplier["name"]
    ...
```

**Files**: `src/tests/integration/test_product_catalog.py` (NEW/MODIFY)

## Test Strategy

**Integration Tests** (T073):
- Export format verification
- Import order verification
- Round-trip data integrity

**Commands**:
```bash
pytest src/tests/integration/test_product_catalog.py -v
```

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Import order breaks FKs | Explicit ordering in T072 |
| Decimal precision loss | Use str(value) when parsing |
| Missing fields in old exports | Default values for new fields |
| ID conflicts | Preserve original IDs during import |

## Definition of Done Checklist

- [ ] Export includes suppliers
- [ ] Export includes purchases
- [ ] Export includes Product.preferred_supplier_id
- [ ] Export includes Product.is_hidden
- [ ] Export includes InventoryAddition.purchase_id
- [ ] Import handles suppliers (before products)
- [ ] Import handles purchases (after products)
- [ ] Import handles new Product fields
- [ ] Import handles new InventoryAddition fields
- [ ] Import order is FK-safe
- [ ] Round-trip integration test passes

## Review Guidance

**Key Checkpoints**:
1. Export JSON includes "suppliers" and "purchases" keys
2. Import order: suppliers → products → purchases → inventory
3. Decimal values preserve precision
4. Date parsing works correctly
5. Round-trip test creates, exports, clears, imports, verifies

## Activity Log

- 2025-12-22T14:35:00Z – system – lane=planned – Prompt created via /spec-kitty.tasks
