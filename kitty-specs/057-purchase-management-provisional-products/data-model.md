# Data Model: F057 Purchase Management with Provisional Products

**Date**: 2026-01-17
**Feature**: 057-purchase-management-provisional-products

## Overview

This feature requires a single model change: adding an `is_provisional` boolean field to the Product model. No new models are required.

## Model Changes

### Product Model (`src/models/product.py`)

#### New Field: `is_provisional`

```python
class Product(BaseModel):
    # ... existing fields ...

    # F057: Provisional Product Support
    is_provisional = Column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
        comment="True if product was created during purchase entry and needs review"
    )
```

#### Field Specifications

| Attribute | Value | Rationale |
|-----------|-------|-----------|
| Type | `Boolean` | Simple flag for filtering |
| Default | `False` | Existing products are not provisional |
| Nullable | `False` | Every product has a definite state |
| Indexed | `True` | Enables efficient filtering for review queue |

#### Impact on Existing Fields

No existing fields are modified. The new field is additive.

#### Impact on Relationships

No changes to relationships. Provisional products participate in all existing relationships:
- `ingredient` (many-to-one with Ingredient)
- `purchases` (one-to-many with Purchase)
- `inventory_items` (one-to-many with InventoryItem)
- `preferred_supplier` (many-to-one with Supplier)

## Schema Migration Strategy

Per Constitution VI (Schema Change Strategy for Desktop Phase):

1. **Export**: Full backup using `coordinated_export_service.export_complete()`
2. **Reset**: Delete database file, update model, recreate empty database
3. **Import**: Restore from backup using `coordinated_export_service.import_complete()`

The new `is_provisional` field defaults to `False`, so all imported products will be non-provisional (correct behavior for existing products).

### Export/Import Compatibility

The `coordinated_export_service` should be updated to:

**Export**: Include `is_provisional` field in product records
```json
{
  "name": "King Arthur All-Purpose Flour",
  "brand": "King Arthur",
  "is_provisional": false,
  ...
}
```

**Import**: Handle missing field gracefully (default to `False`)
```python
is_provisional = record.get("is_provisional", False)
```

## Entity Relationships Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                         Product                              │
├─────────────────────────────────────────────────────────────┤
│ id: int (PK)                                                │
│ ingredient_id: int (FK → Ingredient)                        │
│ brand: str                                                  │
│ product_name: str                                           │
│ package_unit: str                                           │
│ package_unit_quantity: float                                │
│ upc_code: str                                               │
│ is_hidden: bool                                             │
│ is_provisional: bool  ← NEW FIELD (F057)                    │
│ preferred: bool                                             │
│ ...                                                         │
├─────────────────────────────────────────────────────────────┤
│ Relationships:                                              │
│   ingredient → Ingredient                                   │
│   purchases → [Purchase]                                    │
│   inventory_items → [InventoryItem]                         │
│   preferred_supplier → Supplier                             │
└─────────────────────────────────────────────────────────────┘
          │
          │ is_provisional=True
          ▼
┌─────────────────────────────────────────────────────────────┐
│              Provisional Product (conceptual)               │
├─────────────────────────────────────────────────────────────┤
│ Same as Product, but:                                       │
│   - is_provisional = True                                   │
│   - May have minimal required fields only                   │
│   - Appears in review queue                                 │
│   - Fully usable for purchases and inventory                │
└─────────────────────────────────────────────────────────────┘
```

## Validation Rules

### Creating Provisional Products

Provisional products have **relaxed validation** compared to regular products:

| Field | Regular Product | Provisional Product |
|-------|-----------------|---------------------|
| `ingredient_id` | Required | Required |
| `brand` | Optional | Optional (can be "Unknown") |
| `product_name` | Optional | Optional |
| `package_unit` | Required | Required |
| `package_unit_quantity` | Required | Required (can be 1.0 default) |
| `upc_code` | Optional | Optional (may have from scan) |
| `package_size` | Optional | Optional |
| `is_provisional` | N/A (False) | True |

### Marking as Reviewed

When marking a product as reviewed (`is_provisional` → `False`), consider requiring:
- All required fields populated
- Or: User explicitly confirms incomplete data is acceptable

**Decision**: No additional validation on review - user can mark reviewed at any time.

## State Transitions

```
                    ┌──────────────────┐
                    │   Non-existent   │
                    └────────┬─────────┘
                             │
           ┌─────────────────┴─────────────────┐
           │                                   │
           ▼                                   ▼
┌──────────────────────┐           ┌──────────────────────┐
│  Regular Creation    │           │  Provisional Creation│
│  (is_provisional=F)  │           │  (is_provisional=T)  │
└──────────────────────┘           └──────────┬───────────┘
           │                                   │
           │                                   │
           │                                   ▼
           │                       ┌──────────────────────┐
           │                       │   Mark as Reviewed   │
           │                       │  (is_provisional=F)  │
           │                       └──────────┬───────────┘
           │                                   │
           └───────────────┬───────────────────┘
                           │
                           ▼
                 ┌──────────────────────┐
                 │   Regular Product    │
                 │  (is_provisional=F)  │
                 └──────────────────────┘
```

## Query Patterns

### Get All Provisional Products

```python
session.query(Product).filter(Product.is_provisional == True).all()
```

### Get Provisional Count (for badge)

```python
session.query(func.count(Product.id)).filter(Product.is_provisional == True).scalar()
```

### Get Products with Provisional Filter

```python
def get_products(include_provisional_only=False, ...):
    query = session.query(Product)
    if include_provisional_only:
        query = query.filter(Product.is_provisional == True)
    return query.all()
```

## Testing Considerations

### Unit Tests

1. **Create provisional product**: Verify `is_provisional=True`
2. **Create regular product**: Verify `is_provisional=False`
3. **Mark as reviewed**: Verify `is_provisional` changes to `False`
4. **Query provisional**: Verify filter returns only provisional products
5. **Count provisional**: Verify count is accurate

### Integration Tests

1. **Purchase with provisional product**: Verify full workflow
2. **Import with provisional creation**: Verify unknown products become provisional
3. **Export/import round-trip**: Verify `is_provisional` preserved

## Backward Compatibility

- Existing products: All have `is_provisional=False` (default)
- Existing imports: Missing field defaults to `False`
- Existing exports: Will include new field after update
- Existing queries: Unaffected (no filter = all products)
