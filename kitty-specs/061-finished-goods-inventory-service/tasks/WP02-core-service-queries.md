---
work_package_id: "WP02"
subtasks:
  - "T006"
  - "T007"
  - "T008"
title: "Core Service - Query Functions"
phase: "Phase 2 - Core Service"
lane: "doing"
assignee: ""
agent: "claude-opus"
shell_pid: "3063"
review_status: ""
reviewed_by: ""
dependencies: ["WP01"]
history:
  - timestamp: "2026-01-21T19:33:38Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP02 – Core Service - Query Functions

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.

---

## Review Feedback

> **Populated by `/spec-kitty.review`**

*[This section is empty initially.]*

---

## Implementation Command

```bash
spec-kitty implement WP02 --base WP01
```

Depends on WP01 (model and service skeleton).

---

## Objectives & Success Criteria

- ✅ `get_inventory_status()` returns filtered inventory data with costs and values
- ✅ `get_low_stock_items()` returns items below threshold with configurable threshold
- ✅ `get_total_inventory_value()` returns aggregated value across both item types
- ✅ All functions work with and without session parameter
- ✅ All functions return dicts (not ORM objects) to avoid detachment issues

## Context & Constraints

**Reference Documents**:
- `kitty-specs/061-finished-goods-inventory-service/plan.md` - Return value patterns
- `kitty-specs/061-finished-goods-inventory-service/research.md` - Query patterns from existing services

**Key Constraints**:
- Use helper function session pattern
- Return dicts, not ORM objects
- Use eager loading (joinedload) where appropriate
- Handle null costs as Decimal("0.0000")

---

## Subtasks & Detailed Guidance

### Subtask T006 – Implement get_inventory_status()

**Purpose**: Query current inventory levels for finished units and/or finished goods with optional filtering.

**Steps**:
1. Open `src/services/finished_goods_inventory_service.py`
2. Replace the `_get_inventory_status_impl` stub with full implementation
3. Implement filtering logic:
   - `item_type=None`: Return both FinishedUnit and FinishedGood
   - `item_type="finished_unit"`: Return only FinishedUnits
   - `item_type="finished_good"`: Return only FinishedGoods
   - `item_id`: Filter to specific item (requires item_type)
   - `exclude_zero=True`: Exclude items with inventory_count == 0
4. For each item, build result dict:
   ```python
   {
       "item_type": "finished_unit",  # or "finished_good"
       "id": item.id,
       "slug": item.slug,
       "display_name": item.display_name,
       "inventory_count": item.inventory_count,
       "current_cost": item.calculate_current_cost(),  # Decimal
       "total_value": item.inventory_count * item.calculate_current_cost()
   }
   ```
5. Handle edge cases:
   - Invalid item_type → raise ValueError
   - item_id without item_type → raise ValueError
   - Empty results → return empty list

**Files**:
- `src/services/finished_goods_inventory_service.py` (modify, ~60 lines)

**Return Value Pattern**:
```python
[
    {
        "item_type": "finished_unit",
        "id": 1,
        "slug": "sugar-cookie",
        "display_name": "Sugar Cookie",
        "inventory_count": 24,
        "current_cost": Decimal("1.50"),
        "total_value": Decimal("36.00")
    },
    ...
]
```

**Validation**:
- [ ] Returns list of dicts
- [ ] Filtering by item_type works
- [ ] exclude_zero excludes zero-inventory items
- [ ] Works with and without session

---

### Subtask T007 – Implement get_low_stock_items()

**Purpose**: Identify items with inventory below a configurable threshold.

**Steps**:
1. Implement `_get_low_stock_items_impl`
2. Default threshold to `DEFAULT_LOW_STOCK_THRESHOLD` if not provided
3. Query both item types (or filtered type) where `inventory_count < threshold`
4. Return same dict structure as get_inventory_status
5. Order by inventory_count ascending (lowest first)

**Files**:
- `src/services/finished_goods_inventory_service.py` (modify, ~40 lines)

**Implementation**:
```python
def _get_low_stock_items_impl(threshold, item_type, session):
    if threshold is None:
        threshold = DEFAULT_LOW_STOCK_THRESHOLD

    results = []

    if item_type is None or item_type == "finished_unit":
        units = session.query(FinishedUnit).filter(
            FinishedUnit.inventory_count < threshold
        ).order_by(FinishedUnit.inventory_count.asc()).all()
        for unit in units:
            results.append({
                "item_type": "finished_unit",
                "id": unit.id,
                "slug": unit.slug,
                "display_name": unit.display_name,
                "inventory_count": unit.inventory_count,
                "current_cost": unit.calculate_current_cost(),
                "total_value": unit.inventory_count * unit.calculate_current_cost()
            })

    # Same for finished_good...

    return results
```

**Validation**:
- [ ] Default threshold is 5
- [ ] Custom threshold works
- [ ] Results ordered by inventory_count ascending
- [ ] Filtering by item_type works

---

### Subtask T008 – Implement get_total_inventory_value()

**Purpose**: Calculate the total value of all finished goods inventory.

**Steps**:
1. Implement `_get_total_inventory_value_impl`
2. Query all FinishedUnits and FinishedGoods
3. For each, calculate: `inventory_count * calculate_current_cost()`
4. Sum separately for units and goods
5. Return structured result:
   ```python
   {
       "finished_units_value": Decimal("123.45"),
       "finished_goods_value": Decimal("678.90"),
       "total_value": Decimal("802.35"),
       "finished_units_count": 5,   # Number of distinct items
       "finished_goods_count": 3,
       "total_items_count": 8
   }
   ```

**Files**:
- `src/services/finished_goods_inventory_service.py` (modify, ~40 lines)

**Edge Cases**:
- Items with zero inventory contribute 0 to value
- Items with null cost (calculate_current_cost returns 0) contribute 0
- Empty database returns all zeros

**Validation**:
- [ ] Returns dict with all 6 fields
- [ ] Values are Decimal type (for precision)
- [ ] Counts are integers
- [ ] Zero-inventory items handled correctly

---

## Test Strategy

No tests in this WP - tests are in WP07.

Manual validation:
```python
from src.services import finished_goods_inventory_service as fg_inv

# Test queries (assuming some test data exists)
status = fg_inv.get_inventory_status()
print(f"Found {len(status)} items")

low = fg_inv.get_low_stock_items(threshold=10)
print(f"Found {len(low)} low stock items")

value = fg_inv.get_total_inventory_value()
print(f"Total inventory value: ${value['total_value']}")
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| N+1 query problem | Use eager loading if needed; single-user app so acceptable |
| Cost calculation returns None | Models return Decimal("0.0000") for missing costs |
| Large result sets | Not a concern for desktop app scale (dozens of items) |

---

## Definition of Done Checklist

- [ ] T006: get_inventory_status implemented with all filtering options
- [ ] T007: get_low_stock_items implemented with configurable threshold
- [ ] T008: get_total_inventory_value implemented with aggregations
- [ ] All functions work with session=None (own transaction)
- [ ] All functions work with session provided (caller's transaction)
- [ ] All functions return dicts, not ORM objects
- [ ] Code follows helper function session pattern

---

## Review Guidance

**Key checkpoints**:
1. Return values match plan.md patterns exactly
2. Session pattern is correct (helper function approach)
3. Filtering logic handles all combinations
4. Edge cases (empty DB, zero inventory) handled
5. Decimal precision maintained for costs

---

## Activity Log

- 2026-01-21T19:33:38Z – system – lane=planned – Prompt created.
- 2026-01-22T01:26:13Z – claude-opus – shell_pid=97684 – lane=doing – Started implementation via workflow command
- 2026-01-22T01:41:33Z – claude-opus – shell_pid=97684 – lane=for_review – Ready for review: Implemented get_inventory_status, get_low_stock_items, and get_total_inventory_value query functions. Added FinishedGoodsAdjustment to models __init__.py. All 2581 tests pass.
- 2026-01-22T01:46:11Z – claude-opus – shell_pid=3063 – lane=doing – Started review via workflow command
