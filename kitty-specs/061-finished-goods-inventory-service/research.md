# Research: Finished Goods Inventory Service

**Date**: 2026-01-21
**Feature**: 061-finished-goods-inventory-service

## Research Summary

This document consolidates findings from codebase analysis to inform implementation of the finished goods inventory service.

---

## 1. Session Ownership Pattern (F060 Compliance)

**Decision**: Follow helper function pattern used throughout codebase
**Rationale**: Most common pattern in existing services; clear separation of concerns

### Two Approved Patterns

#### Pattern A: Helper Function (Recommended)
```python
def public_function(param, session=None):
    if session is not None:
        return _impl(param, session)
    with session_scope() as session:
        return _impl(param, session)

def _impl(param, session):
    # All operations use session
```

Used by: `inventory_item_service.consume_fifo()`, `assembly_service.check_can_assemble()`, `recipe_service.get_aggregated_ingredients()`

#### Pattern B: nullcontext (Alternative)
```python
from contextlib import nullcontext

def service_method(..., session=None):
    cm = nullcontext(session) if session is not None else session_scope()
    with cm as session:
        return result
```

Used by: `batch_production_service.record_batch_production()`

### Mandatory Rules
1. All public DB methods accept `session=None`
2. Use conditional session handling
3. Pass session to ALL downstream service calls
4. Do NOT commit when session provided
5. Own session when not provided (backward compatibility)

---

## 2. Existing Model Analysis

### FinishedUnit (`src/models/finished_unit.py`)

**Inventory Field**: `inventory_count` (Integer, default=0)

**CHECK Constraint**: `ck_finished_unit_inventory_non_negative: inventory_count >= 0`

**Cost Architecture**: NO stored cost field. Dynamic calculation via `calculate_current_cost()` using weighted average from ProductionRun instances.

**Existing Business Logic Methods to Deprecate**:
- `is_available(quantity=1)` → Returns `self.inventory_count >= quantity`
- `update_inventory(quantity_change)` → Updates count, returns False if would go negative
- `calculate_batches_needed(quantity)` → Recipe batch calculation
- `calculate_current_cost()` → Weighted average from production history

### FinishedGood (`src/models/finished_good.py`)

**Inventory Field**: `inventory_count` (Integer, default=0)

**CHECK Constraint**: `ck_finished_good_inventory_non_negative: inventory_count >= 0`

**Cost Architecture**: NO stored cost field. Dynamic calculation via `calculate_current_cost()` summing component costs recursively.

**Existing Business Logic Methods to Deprecate**:
- `is_available(quantity=1)` → Returns `self.inventory_count >= quantity`
- `update_inventory(quantity_change)` → Updates count (NOTE: does NOT update `updated_at`)
- `can_assemble(quantity=1)` → Returns dict with `can_assemble` bool and missing/sufficient components
- `get_component_breakdown()` → Returns component details
- `calculate_current_cost()` → Sum of component costs

**Potential Bug Noted**: `FinishedGood.update_inventory()` doesn't update `updated_at` timestamp (FinishedUnit does).

---

## 3. Assembly Service Integration Points

**File**: `src/services/assembly_service.py`

### Current Inventory Modification Flow

1. **FinishedUnit consumption** (lines 351-373):
   ```python
   fu.inventory_count -= needed  # Direct modification
   session.flush()
   ```

2. **FinishedGood (nested) consumption** (lines 375-401):
   ```python
   nested_fg.inventory_count -= needed  # Direct modification
   ```

3. **Target FinishedGood creation** (lines 434-435):
   ```python
   finished_good.inventory_count += quantity  # At end of assembly
   ```

### What Assembly Service Needs from Inventory Service

1. **Availability validation** (currently uses model's `can_assemble()`):
   - Check FinishedUnit components have sufficient inventory
   - Check nested FinishedGood components have sufficient inventory

2. **Atomic adjustment** within caller's transaction:
   - Decrement component counts
   - Increment assembled good count
   - All operations use same session

### Session Pattern Already Implemented
Assembly service uses helper function pattern with `_record_assembly_impl()` and passes session to downstream calls.

---

## 4. Production Integration Points

**File**: `src/services/batch_production_service.py`

### Current Flow
Production runs create FinishedUnits. The `actual_yield` is recorded on ProductionRun, which is used for cost calculations.

### Where Inventory Update Should Occur
After production completion, `finished_unit.inventory_count` should be incremented by `actual_yield`.

**Current State**: Need to verify if inventory_count is currently updated. Research indicates ProductionRun stores yield but doesn't necessarily update FinishedUnit.inventory_count.

---

## 5. Export/Import Patterns

### Current State
- `inventory_count` IS exported in both denormalized and coordinated formats
- Marked as **readonly** (not in editable_fields list)
- Restored during coordinated import

### Pattern for Export
```python
# In coordinated_export_service.py
"inventory_count": fu.inventory_count,  # Line 684
"inventory_count": g.inventory_count,   # Line 651
```

### No Changes Required
Export/import already handles inventory_count correctly. The new service provides primitives; export continues to read model field directly.

---

## 6. Configuration Pattern for Thresholds

**File**: `src/utils/constants.py`

**Decision**: Add `DEFAULT_LOW_STOCK_THRESHOLD = 5` to constants.py

**Rationale**: Follows existing pattern for numeric constants. Config class is focused on environment/database paths.

**Example Addition**:
```python
# ============================================================================
# Inventory Constants
# ============================================================================

DEFAULT_LOW_STOCK_THRESHOLD = 5  # Units below which item is considered low stock
```

---

## 7. Adjustment History Pattern

**Decision**: Create `FinishedGoodsAdjustment` model (new table)

**Rationale**: User confirmed preference for simple adjustment history table (option C during planning).

### Existing Pattern Reference
`InventoryDepletion` model tracks adjustments for raw ingredients:
- `inventory_item_id` (FK)
- `quantity_depleted`
- `reason` (enum: EXPIRATION, SPOILAGE, USAGE, OTHER)
- `notes`
- `depletion_date`

### New Model Design
```python
class FinishedGoodsAdjustment(BaseModel):
    """Audit trail for finished goods inventory changes."""
    __tablename__ = "finished_goods_adjustments"

    # Polymorphic target (one of these will be set)
    finished_unit_id = Column(Integer, ForeignKey("finished_units.id"), nullable=True)
    finished_good_id = Column(Integer, ForeignKey("finished_goods.id"), nullable=True)

    # Adjustment details
    quantity_change = Column(Integer, nullable=False)  # Positive or negative
    previous_count = Column(Integer, nullable=False)
    new_count = Column(Integer, nullable=False)

    # Tracking
    reason = Column(String(50), nullable=False)  # production, assembly, spoilage, gift, adjustment
    notes = Column(Text, nullable=True)
    adjusted_at = Column(DateTime, nullable=False, default=utc_now)

    # Relationships
    finished_unit = relationship("FinishedUnit", back_populates="adjustments")
    finished_good = relationship("FinishedGood", back_populates="adjustments")
```

---

## 8. Service Interface Design

Based on research, the service interface should be:

```python
finished_goods_inventory_service
  # Queries (all accept session=None)
  ├─ get_inventory_status(item_type=None, item_id=None, exclude_zero=False, session=None)
  ├─ get_low_stock_items(threshold=None, item_type=None, session=None)
  └─ get_total_inventory_value(session=None)

  # Validation (all accept session=None)
  ├─ check_availability(item_type, item_id, quantity, session=None)
  └─ validate_consumption(item_type, item_id, quantity, session=None)

  # Updates (all accept session=None)
  └─ adjust_inventory(item_type, item_id, quantity, reason, notes=None, session=None)
```

**Key Design Decisions**:
- `item_type` parameter: "finished_unit" or "finished_good" (polymorphic dispatch)
- All methods return structured dicts (not ORM objects) to avoid detachment issues
- Adjustment creates audit record in addition to updating model field

---

## 9. Callers to Update

### Model Methods to Remove (per user decision)
- `FinishedUnit.is_available()` → Use `check_availability("finished_unit", id, qty)`
- `FinishedUnit.update_inventory()` → Use `adjust_inventory("finished_unit", id, qty, reason)`
- `FinishedGood.is_available()` → Use `check_availability("finished_good", id, qty)`
- `FinishedGood.update_inventory()` → Use `adjust_inventory("finished_good", id, qty, reason)`
- `FinishedGood.can_assemble()` → Stays in model OR moves to assembly_service (feasibility logic)

### Services to Update
1. **assembly_service.py**:
   - Replace direct `fu.inventory_count -= needed` with `adjust_inventory()` call
   - Replace direct `finished_good.inventory_count += quantity` with `adjust_inventory()` call

2. **batch_production_service.py** (if not already updating):
   - Add `adjust_inventory("finished_unit", fu_id, actual_yield, "production")` after production

### Grep Results Needed
Search for direct `inventory_count` modifications to find all callers.

---

## 10. Alternatives Considered

| Decision | Chosen | Rejected | Why |
|----------|--------|----------|-----|
| Deprecation | Remove methods entirely | Keep as wrappers | Cleaner codebase; no confusion about which to use |
| Audit trail | New table | Log-only | Supports future UI; queryable history |
| Threshold config | constants.py | Database setting | Simpler; no runtime UI needed yet |
| Session pattern | Helper function | nullcontext | More common in codebase; clearer |

---

## References

- `src/services/batch_production_service.py` - Session pattern reference
- `src/services/assembly_service.py` - Integration point
- `src/services/inventory_item_service.py` - Query/adjustment patterns
- `src/models/finished_unit.py` - Existing methods
- `src/models/finished_good.py` - Existing methods
- `CLAUDE.md` - Session management documentation
