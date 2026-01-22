# Quickstart: Finished Goods Inventory Service

**Feature**: 061-finished-goods-inventory-service

## Overview

This feature adds a service layer for managing finished goods inventory (FinishedUnit and FinishedGood models). The service provides session-aware primitives for queries, validation, and adjustments.

## Key Files

| File | Purpose |
|------|---------|
| `src/services/finished_goods_inventory_service.py` | New service (to be created) |
| `src/models/finished_goods_adjustment.py` | New audit trail model |
| `src/models/finished_unit.py` | Remove business logic methods |
| `src/models/finished_good.py` | Remove business logic methods |
| `src/services/assembly_service.py` | Update to use new service |
| `src/services/batch_production_service.py` | Update to use new service |
| `src/utils/constants.py` | Add threshold constant |

## Service API Summary

```python
from src.services import finished_goods_inventory_service as fg_inv

# Query current inventory
status = fg_inv.get_inventory_status(item_type="finished_unit", session=session)

# Check if quantity is available
result = fg_inv.check_availability("finished_good", good_id, quantity=5, session=session)
# Returns: {"available": True, "current_count": 10} or {"available": False, "shortage": 3, ...}

# Adjust inventory (creates audit record)
result = fg_inv.adjust_inventory(
    item_type="finished_unit",
    item_id=unit_id,
    quantity=+10,  # Positive for add, negative for consume
    reason="production",
    notes="Production run #123",
    session=session
)
# Returns: {"previous_count": 5, "new_count": 15, "adjustment_id": 42}

# Get low stock items
low_stock = fg_inv.get_low_stock_items(threshold=5, session=session)

# Calculate total inventory value
value = fg_inv.get_total_inventory_value(session=session)
```

## Session Pattern

All methods accept optional `session` parameter:

```python
# Standalone (owns transaction)
result = fg_inv.adjust_inventory("finished_unit", id, 5, "production")

# Within caller's transaction
with session_scope() as session:
    # Multiple operations, same transaction
    fg_inv.adjust_inventory("finished_unit", id1, -2, "assembly", session=session)
    fg_inv.adjust_inventory("finished_good", id2, +1, "assembly", session=session)
    # Commit happens on scope exit
```

## Testing

```bash
# Run service tests
./run-tests.sh src/tests/services/test_finished_goods_inventory_service.py -v

# Run integration tests
./run-tests.sh src/tests/integration/test_finished_goods_inventory_integration.py -v
```

## Migration Steps

1. Add new model (`FinishedGoodsAdjustment`)
2. Export data (existing inventory_count preserved)
3. Reset database / recreate schema
4. Import data
5. Historical adjustments start fresh (no backfill)
