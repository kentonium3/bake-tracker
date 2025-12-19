# Data Model: Product Name Differentiation

**Feature**: 023-product-name-differentiation
**Date**: 2025-12-19

## Entity Changes

### Product (Modified)

**Table**: `products`

#### New Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `product_name` | VARCHAR(200) | YES | NULL | Variant name to differentiate products with same brand/packaging |

#### Column Position

Insert after `brand` column for logical grouping:
```
ingredient_id
brand
product_name    <- NEW
package_size
package_type
...
```

#### Updated Unique Constraint

**Before**: No unique constraint on Product table

**After**:
```sql
UNIQUE (ingredient_id, brand, product_name, package_size, package_unit)
```

**SQLite Behavior**: NULL values are considered distinct, so multiple products with NULL product_name are allowed (matching existing behavior).

#### Updated display_name Property

**Before**:
```python
def display_name(self) -> str:
    parts = []
    if self.brand:
        parts.append(self.brand)
    if self.package_size:
        parts.append(self.package_size)
    if self.package_type:
        parts.append(self.package_type)
    # ...
```

**After**:
```python
def display_name(self) -> str:
    parts = []
    if self.brand:
        parts.append(self.brand)
    if self.product_name:
        parts.append(self.product_name)
    if self.package_size:
        parts.append(self.package_size)
    if self.package_type:
        parts.append(self.package_type)
    # ...
```

**Format**: "Brand ProductName Size Type" (e.g., "Lindt 70% Cacao 3.5 oz bar")

## Validation Rules

### Product Name

| Rule | Description |
|------|-------------|
| Max Length | 200 characters |
| Empty String Handling | Normalize to NULL on save |
| Character Set | UTF-8, no validation against predefined list |

## Relationships

No relationship changes - Product's relationships to Ingredient, Purchase, and InventoryItem remain unchanged.

## Export/Import Schema

### Export Format (v3.5)

```json
{
  "products": [
    {
      "ingredient_slug": "dark-chocolate",
      "brand": "Lindt",
      "product_name": "70% Cacao",  // NEW - optional
      "package_size": "3.5 oz",
      "package_type": "bar",
      "package_unit": "oz",
      "package_unit_quantity": 3.5,
      // ... other fields
    }
  ]
}
```

### Import Backward Compatibility

- `product_name` field is optional in import
- Missing `product_name` defaults to NULL
- Product lookup uses three-part key: (ingredient_slug, brand, product_name)
- If product_name not in import data, lookup uses (ingredient_slug, brand, NULL)

## Migration Strategy

Per Constitution VI (Schema Change Strategy - Desktop Phase):

1. **Export** all data to JSON
2. **Delete** database
3. **Update** Product model with new column and constraint
4. **Recreate** empty database
5. **Transform** JSON if needed (add `product_name: null` to products)
6. **Import** transformed data

Note: No transformation needed - import handles missing fields by defaulting to NULL.
