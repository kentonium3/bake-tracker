# Data Model: Purchases Tab with CRUD Operations

**Feature**: 042-purchases-tab-crud-operations
**Date**: 2026-01-08

## Existing Entities (No Changes)

### Purchase (src/models/purchase.py)

| Field | Type | Notes |
|-------|------|-------|
| id | Integer | Primary key |
| product_id | Integer (FK) | Links to Product |
| supplier_id | Integer (FK) | Links to Supplier |
| purchase_date | Date | When purchased |
| quantity_purchased | Integer | Package count (NOTE: spec now allows 1 decimal) |
| unit_price | Numeric(10,4) | Price per package |
| notes | Text (nullable) | Optional notes |
| created_at | DateTime | Auto-set |
| updated_at | DateTime | Auto-updated |

**Relationships**:
- `product` → Product (many-to-one)
- `supplier` → Supplier (many-to-one)
- `inventory_items` → List[InventoryItem] (one-to-many)

**Computed Property**:
- `total_cost` = quantity_purchased * unit_price

### InventoryItem (src/models/inventory_item.py)

| Field | Type | Notes |
|-------|------|-------|
| id | Integer | Primary key |
| purchase_id | Integer (FK) | Links to Purchase |
| ingredient_id | Integer (FK) | Links to Ingredient |
| current_quantity | Numeric(10,2) | Remaining after FIFO consumption |
| unit | String(50) | Unit of measure |
| unit_cost | Numeric(10,4) | Cost per unit |

**Relationships**:
- `purchase` → Purchase (many-to-one)
- `ingredient` → Ingredient (many-to-one)
- `depletions` → List[InventoryDepletion] (one-to-many)

### InventoryDepletion (tracks FIFO consumption)

| Field | Type | Notes |
|-------|------|-------|
| id | Integer | Primary key |
| inventory_item_id | Integer (FK) | Links to InventoryItem |
| production_run_id | Integer (FK) | Links to ProductionRun |
| quantity_depleted | Numeric(10,2) | Amount consumed (negative) |
| depleted_at | DateTime | When consumed |

## Service Layer Contracts

### New Methods for PurchaseService

#### get_purchases_filtered()

```python
def get_purchases_filtered(
    date_range: str = "last_30_days",  # "last_30_days", "last_90_days", "last_year", "all_time"
    supplier_id: Optional[int] = None,
    search_query: Optional[str] = None,
    session: Optional[Session] = None
) -> List[Dict]:
    """
    Get purchase history with filters.

    Returns list of dicts with:
    - id: int
    - product_name: str
    - supplier_name: str
    - purchase_date: date
    - quantity_purchased: Decimal
    - unit_price: Decimal
    - total_cost: Decimal
    - remaining_inventory: Decimal (from FIFO tracking)
    - notes: Optional[str]

    Ordered by purchase_date DESC.
    """
```

#### get_remaining_inventory()

```python
def get_remaining_inventory(
    purchase_id: int,
    session: Optional[Session] = None
) -> Decimal:
    """
    Calculate remaining inventory from this purchase.

    Sums current_quantity across all linked InventoryItems.
    Returns Decimal("0") if fully consumed or no items.
    """
```

#### can_edit_purchase()

```python
def can_edit_purchase(
    purchase_id: int,
    new_quantity: Decimal,
    session: Optional[Session] = None
) -> Tuple[bool, str]:
    """
    Validate if purchase can be edited with new quantity.

    Returns:
        (True, "") if edit allowed
        (False, "reason") if blocked

    Blocked when new_quantity < total consumed quantity.
    """
```

#### can_delete_purchase()

```python
def can_delete_purchase(
    purchase_id: int,
    session: Optional[Session] = None
) -> Tuple[bool, str]:
    """
    Check if purchase can be deleted.

    Returns:
        (True, "") if no depletions exist
        (False, "Cannot delete - X units already used in: Recipe1, Recipe2")

    Blocked when ANY inventory from purchase has been consumed.
    """
```

#### update_purchase()

```python
def update_purchase(
    purchase_id: int,
    updates: Dict[str, Any],  # Keys: date, quantity, unit_price, supplier_id, notes
    session: Optional[Session] = None
) -> Purchase:
    """
    Update purchase fields and recalculate FIFO costs.

    Updates allowed:
    - purchase_date
    - quantity_purchased (if >= consumed)
    - unit_price (triggers unit_cost recalc)
    - supplier_id
    - notes

    NOT allowed:
    - product_id (raises ValueError)

    If unit_price changes, recalculates unit_cost on linked InventoryItems.
    If quantity changes, adjusts current_quantity on InventoryItems.

    Raises:
        PurchaseNotFound if purchase_id invalid
        ValueError if quantity < consumed
        ValueError if trying to change product_id
    """
```

#### get_purchase_usage_history()

```python
def get_purchase_usage_history(
    purchase_id: int,
    session: Optional[Session] = None
) -> List[Dict]:
    """
    Get consumption history for a purchase.

    Returns list of dicts with:
    - depletion_id: int
    - depleted_at: datetime
    - recipe_name: str
    - quantity_used: Decimal (positive)
    - cost: Decimal (quantity * unit_cost at time of consumption)

    Ordered by depleted_at ASC.
    """
```

## UI Data Flows

### Purchase List View

```
User opens Purchases tab
  → PurchaseService.get_purchases_filtered(date_range="last_30_days")
  → Display in Treeview

User changes filter
  → PurchaseService.get_purchases_filtered(date_range, supplier_id, search)
  → Refresh Treeview
```

### Add Purchase

```
User clicks [Add Purchase]
  → Open AddPurchaseDialog

User selects product
  → PurchaseService.get_last_price_any_supplier(product_id)
  → Auto-fill unit_price

User clicks [Add Purchase]
  → PurchaseService.record_purchase(product_id, quantity, unit_price, ...)
  → Close dialog
  → Refresh list via callback
```

### Edit Purchase

```
User right-clicks → Edit
  → PurchaseService.get_purchase(purchase_id)
  → Open EditPurchaseDialog (pre-filled)

User changes quantity
  → PurchaseService.can_edit_purchase(purchase_id, new_quantity)
  → Show validation result

User clicks [Save]
  → PurchaseService.update_purchase(purchase_id, updates)
  → Close dialog
  → Refresh list via callback
```

### Delete Purchase

```
User right-clicks → Delete
  → PurchaseService.can_delete_purchase(purchase_id)

If blocked:
  → Show error dialog with usage details

If allowed:
  → Show confirmation dialog
  → User confirms
  → PurchaseService.delete_purchase(purchase_id)
  → Refresh list
```

### View Details

```
User right-clicks → View Details
  → PurchaseService.get_purchase(purchase_id)
  → PurchaseService.get_remaining_inventory(purchase_id)
  → PurchaseService.get_purchase_usage_history(purchase_id)
  → Open PurchaseDetailsDialog (read-only)

User clicks [Edit Purchase]
  → Close details dialog
  → Open EditPurchaseDialog
```
