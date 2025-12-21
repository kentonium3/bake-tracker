# Data Model: Deferred Packaging Decisions

**Feature**: 026-deferred-packaging-decisions
**Date**: 2025-12-21

## Schema Changes Overview

This feature requires:
1. One new column on existing `compositions` table
2. One new junction table for tracking assignments

## Modified Tables

### compositions (existing)

Add column:

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `is_generic` | Boolean | No | False | When True, `packaging_product_id` references a template product whose `product_name` defines the generic requirement |

**Notes**:
- Existing rows get `is_generic=False` (backward compatible)
- Only valid when `packaging_product_id IS NOT NULL`
- When `is_generic=True`, the referenced Product serves as a template - its `product_name` field defines the generic product type

## New Tables

### composition_assignments

Tracks which specific inventory items fulfill a generic packaging requirement.

| Column | Type | Nullable | Constraints | Description |
|--------|------|----------|-------------|-------------|
| `id` | Integer | No | PK | Primary key |
| `uuid` | String(36) | No | Unique | UUID for distributed systems |
| `composition_id` | Integer | No | FK → compositions.id, ON DELETE CASCADE | The generic requirement being fulfilled |
| `inventory_item_id` | Integer | No | FK → inventory_items.id, ON DELETE RESTRICT | Specific material assigned |
| `quantity_assigned` | Float | No | > 0 | Quantity from this inventory item |
| `assigned_at` | DateTime | No | | When assignment was made |
| `created_at` | DateTime | No | | Record creation timestamp |
| `updated_at` | DateTime | No | | Last modification timestamp |

**Indexes**:
- `idx_composition_assignment_composition` on `composition_id`
- `idx_composition_assignment_inventory` on `inventory_item_id`

**Constraints**:
- `ck_assignment_quantity_positive`: `quantity_assigned > 0`
- Unique constraint on `(composition_id, inventory_item_id)` - each inventory item can only be assigned once per composition

**Relationships**:
- `composition`: Many-to-One with Composition
- `inventory_item`: Many-to-One with InventoryItem

## Entity Relationship Diagram

```
┌─────────────────────┐
│    Composition      │
├─────────────────────┤
│ id                  │
│ assembly_id    (FK) │──────┐
│ package_id     (FK) │──────┤
│ packaging_product_id│──┐   │
│ is_generic (NEW)    │  │   │
│ component_quantity  │  │   │
│ ...                 │  │   │
└─────────────────────┘  │   │
         │               │   │
         │ 1:N           │   │
         ▼               │   │
┌─────────────────────┐  │   │      ┌─────────────────────┐
│ CompositionAssignment│  │   └─────►│   FinishedGood      │
├─────────────────────┤  │          │   or Package        │
│ id                  │  │          └─────────────────────┘
│ composition_id (FK) │  │
│ inventory_item_id   │──┼────┐
│ quantity_assigned   │  │    │
│ assigned_at         │  │    │
└─────────────────────┘  │    │
                         │    │
                         ▼    ▼
┌─────────────────────┐  │  ┌─────────────────────┐
│      Product        │◄─┘  │   InventoryItem     │
├─────────────────────┤     ├─────────────────────┤
│ id                  │     │ id                  │
│ ingredient_id  (FK) │     │ product_id     (FK) │─┐
│ product_name        │     │ quantity            │ │
│ brand               │     │ unit_cost           │ │
│ ...                 │     │ ...                 │ │
└─────────────────────┘     └─────────────────────┘ │
         ▲                                          │
         └──────────────────────────────────────────┘
```

## Generic Product Grouping (Virtual)

No new table - generic products are identified by querying:

```sql
SELECT DISTINCT product_name
FROM products p
JOIN ingredients i ON p.ingredient_id = i.id
WHERE i.is_packaging = TRUE
  AND product_name IS NOT NULL
```

For a specific generic product, available inventory is:

```sql
SELECT p.brand, p.id as product_id, SUM(inv.quantity) as available
FROM products p
JOIN ingredients i ON p.ingredient_id = i.id
JOIN inventory_items inv ON inv.product_id = p.id
WHERE i.is_packaging = TRUE
  AND p.product_name = :product_name
  AND inv.quantity > 0
GROUP BY p.brand, p.id
```

## State Transitions

### Composition States

```
                    ┌──────────────────────────────────┐
                    │                                  │
                    ▼                                  │
┌─────────────┐   create    ┌─────────────────────┐   │
│   (none)    │ ──────────► │  is_generic=False   │   │
└─────────────┘             │  (specific product) │   │
                            └─────────────────────┘   │
                                                      │
                    ┌──────────────────────────────────┘
                    │ create with generic=True
                    ▼
            ┌─────────────────────┐
            │  is_generic=True    │
            │  (no assignments)   │
            │  Status: PENDING    │
            └─────────────────────┘
                    │
                    │ assign_materials()
                    ▼
            ┌─────────────────────┐
            │  is_generic=True    │
            │  (has assignments)  │
            │  Status: ASSIGNED   │
            └─────────────────────┘
                    │
                    │ complete_assembly()
                    ▼
            ┌─────────────────────┐
            │  is_generic=True    │
            │  (consumed)         │
            │  Status: COMPLETE   │
            └─────────────────────┘
```

## Validation Rules

### At Planning Time (create generic requirement)
1. `product_name` must match at least one packaging product
2. Quantity must be positive
3. Warn if total available < quantity needed (allow for shopping intent)

### At Assignment Time
1. Sum of `quantity_assigned` across all assignments must equal `component_quantity`
2. Each `quantity_assigned` must not exceed `inventory_item.quantity`
3. All assigned inventory items must have `product.product_name` matching the template

### At Assembly Time
1. If `is_generic=True` and no assignments exist, prompt user
2. Allow bypass with flag for later reconciliation

## Cost Calculation

### Estimated Cost (generic, unassigned)
```python
def get_estimated_cost(product_name: str, quantity: float) -> float:
    # Get average unit cost across all products with this product_name
    products = get_products_by_name(product_name)
    if not products:
        return 0.0

    total_cost = sum(p.get_current_cost_per_unit() for p in products)
    avg_cost = total_cost / len(products)
    return avg_cost * quantity
```

### Actual Cost (assigned)
```python
def get_actual_cost(composition_id: int) -> float:
    assignments = get_assignments(composition_id)
    total = 0.0
    for a in assignments:
        unit_cost = a.inventory_item.unit_cost or a.inventory_item.product.get_current_cost_per_unit()
        total += unit_cost * a.quantity_assigned
    return total
```

## Import/Export Considerations

### Export Format (sample_data.json)

Extend compositions export:
```json
{
  "compositions": [
    {
      "assembly_id": 1,
      "packaging_product_id": 42,
      "component_quantity": 50,
      "is_generic": true,
      "assignments": [
        {"inventory_item_id": 101, "quantity_assigned": 30},
        {"inventory_item_id": 102, "quantity_assigned": 20}
      ]
    }
  ]
}
```

### Import Handling

1. Create composition with `is_generic` flag
2. If `assignments` present and `is_generic=True`:
   - Match inventory items by product characteristics
   - Create CompositionAssignment records
   - Warn if inventory items not found (data from different system)
