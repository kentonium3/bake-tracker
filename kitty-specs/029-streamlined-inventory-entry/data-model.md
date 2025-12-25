# Data Model: Streamlined Inventory Entry

**Feature**: 029-streamlined-inventory-entry
**Created**: 2025-12-24
**Status**: Complete

## Overview

This feature introduces **no new database entities**. All new structures are runtime/in-memory only, supporting the UI workflow without schema changes.

## New Runtime Entities

### SessionState (In-Memory Singleton)

**Purpose**: Store user's last selections to reduce repetitive data entry during bulk inventory addition.

**Location**: `src/ui/session_state.py`

**Attributes**:

| Attribute | Type | Description |
|-----------|------|-------------|
| `last_supplier_id` | `Optional[int]` | ID of last supplier selected (None if not set) |
| `last_category` | `Optional[str]` | Last category selected (None if not set) |

**Lifecycle**:
- Created on first access (singleton pattern)
- Updated on successful inventory Add only
- Cleared on application restart
- Never persisted to database

**Methods**:
```
update_supplier(supplier_id: int) -> None
update_category(category: str) -> None
get_last_supplier_id() -> Optional[int]
get_last_category() -> Optional[str]
reset() -> None
```

---

### RecencyData (Query Result DTO)

**Purpose**: Represent products/ingredients that meet recency criteria for UI sorting.

**Location**: Inline in service methods (no separate class needed)

**Attributes**:

| Attribute | Type | Description |
|-----------|------|-------------|
| `id` | `int` | Product or Ingredient ID |
| `last_addition` | `date` | Most recent addition date |

**Recency Criteria**:
- Temporal: Added within last 30 days
- Frequency: Added 3+ times in last 90 days
- An item is "recent" if it meets EITHER criterion

**Query Pattern**:
```python
def get_recent_products(ingredient_id: int, ...) -> List[int]:
    """Returns list of product IDs meeting recency criteria, sorted by last_addition DESC"""
```

---

### CategoryUnitDefaults (Configuration)

**Purpose**: Map ingredient categories to default package units for smart pre-filling.

**Location**: `src/utils/category_defaults.py`

**Structure**:
```python
CATEGORY_DEFAULT_UNITS: Dict[str, str] = {
    'Baking': 'lb',
    'Chocolate': 'oz',
    'Dairy': 'lb',
    'Spices': 'oz',
    'Liquids': 'fl oz',
    'Nuts': 'lb',
    'Fruits': 'lb',
    'Sweeteners': 'lb',
    'Leavening': 'oz',
    'Oils': 'fl oz',
    'Grains': 'lb',
}
```

**Fallback**: Returns `'lb'` for unknown categories

---

## Existing Entity Usage

### InventoryItem (Read for Recency)

**Table**: `inventory_items`

**Used For**:
- Querying addition dates for recency calculation
- Filtering by ingredient_id and product_id

**Key Fields Used**:
| Field | Usage |
|-------|-------|
| `product_id` | Filter products for recency |
| `ingredient_id` | Filter ingredients for recency |
| `addition_date` | Calculate temporal recency |

---

### Product (Read for Dropdowns)

**Table**: `products`

**Used For**:
- Populating product dropdowns filtered by ingredient
- Creating new products inline

**Key Fields Used**:
| Field | Usage |
|-------|-------|
| `id` | Dropdown value mapping |
| `name` | Display in dropdown |
| `ingredient_id` | Filter by selected ingredient |
| `is_hidden` | Exclude hidden products |
| `package_unit` | Quantity validation |

---

### Ingredient (Read for Dropdowns)

**Table**: `ingredients`

**Used For**:
- Populating ingredient dropdowns filtered by category
- Getting category for smart unit defaults

**Key Fields Used**:
| Field | Usage |
|-------|-------|
| `id` | Dropdown value mapping |
| `display_name` | Display in dropdown |
| `category` | Filter and smart defaults |

---

### Supplier (Read for Dropdowns)

**Table**: `suppliers`

**Used For**:
- Populating supplier dropdown
- Session memory (last supplier ID)

**Key Fields Used**:
| Field | Usage |
|-------|-------|
| `id` | Session memory storage |
| `name`, `city`, `state` | Display name composition |

---

### Purchase (Read for Price Suggestions)

**Table**: `purchases` (from F028)

**Used For**:
- Price suggestion queries
- Purchase history hints

**Key Fields Used**:
| Field | Usage |
|-------|-------|
| `product_id` | Match selected product |
| `supplier_id` | Match selected supplier |
| `unit_price` | Pre-fill price field |
| `purchase_date` | Format hint display |

---

## Entity Relationships Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    Runtime Entities (In-Memory)                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────┐                                           │
│  │   SessionState   │  (singleton)                              │
│  │  ───────────────│                                           │
│  │  last_supplier_id ──────────────┐                            │
│  │  last_category    ──────────┐   │                            │
│  └──────────────────┘          │   │                            │
│                                │   │                            │
│  ┌──────────────────┐          │   │                            │
│  │CategoryUnitDefaults│        │   │                            │
│  │  ───────────────│          │   │                            │
│  │  category → unit │          │   │                            │
│  └──────────────────┘          │   │                            │
│                                │   │                            │
└────────────────────────────────│───│────────────────────────────┘
                                 │   │
┌────────────────────────────────│───│────────────────────────────┐
│                    Database Entities (Existing)                  │
├────────────────────────────────│───│────────────────────────────┤
│                                │   │                            │
│  ┌──────────────┐              │   │     ┌──────────────┐       │
│  │  Ingredient  │◄─────────────┘   └────►│   Supplier   │       │
│  │  ──────────── │                        │  ──────────── │       │
│  │  id           │                        │  id           │       │
│  │  display_name │                        │  name         │       │
│  │  category     │                        │  city, state  │       │
│  └───────┬───────┘                        └───────┬───────┘       │
│          │ 1:N                                    │               │
│          ▼                                        │               │
│  ┌──────────────┐                                │               │
│  │   Product    │                                │               │
│  │  ──────────── │                                │               │
│  │  id           │                                │               │
│  │  name         │                                │               │
│  │  ingredient_id│                                │               │
│  │  package_unit │                                │               │
│  └───────┬───────┘                                │               │
│          │ 1:N                                    │ 1:N           │
│          ▼                                        ▼               │
│  ┌───────────────────────────────────────────────────┐           │
│  │              InventoryItem                        │           │
│  │  ─────────────────────────────────────────────────│           │
│  │  id | product_id | ingredient_id | addition_date  │           │
│  └───────────────────────────────────────────────────┘           │
│          │ N:1                        N:1 │                      │
│          ▼                                ▼                      │
│  ┌───────────────────────────────────────────────────┐           │
│  │                  Purchase (F028)                  │           │
│  │  ─────────────────────────────────────────────────│           │
│  │  id | product_id | supplier_id | unit_price | date│           │
│  └───────────────────────────────────────────────────┘           │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## Query Patterns

### Recency Products Query

```sql
-- Products added within last 30 days
SELECT product_id, MAX(addition_date) as last_addition
FROM inventory_items
WHERE ingredient_id = :ingredient_id
  AND product_id IS NOT NULL
  AND addition_date >= :temporal_cutoff
GROUP BY product_id

UNION

-- Products added 3+ times in last 90 days
SELECT product_id, MAX(addition_date) as last_addition
FROM inventory_items
WHERE ingredient_id = :ingredient_id
  AND product_id IS NOT NULL
  AND addition_date >= :frequency_cutoff
GROUP BY product_id
HAVING COUNT(*) >= 3

ORDER BY last_addition DESC
LIMIT 20
```

### Price Suggestion Query

```sql
-- Last price at specific supplier
SELECT unit_price, purchase_date
FROM purchases
WHERE product_id = :product_id
  AND supplier_id = :supplier_id
ORDER BY purchase_date DESC
LIMIT 1

-- Fallback: Last price at any supplier
SELECT unit_price, purchase_date, supplier_id
FROM purchases
WHERE product_id = :product_id
ORDER BY purchase_date DESC
LIMIT 1
```

---

## Index Recommendations

For recency query performance, ensure these indexes exist:

| Table | Index | Columns |
|-------|-------|---------|
| `inventory_items` | `idx_inventory_addition_date` | `addition_date` |
| `inventory_items` | `idx_inventory_ingredient_product` | `ingredient_id, product_id` |
| `purchases` | `idx_purchases_product_supplier_date` | `product_id, supplier_id, purchase_date DESC` |

---

## No Schema Changes Required

This feature operates entirely on:
1. **Existing tables**: No ALTER TABLE or new tables needed
2. **In-memory state**: SessionState singleton
3. **Configuration**: Static category-to-unit mapping

Database migration is **not required** for this feature.
