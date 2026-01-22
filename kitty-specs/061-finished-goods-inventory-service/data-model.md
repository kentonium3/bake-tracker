# Data Model: Finished Goods Inventory Service

**Date**: 2026-01-21
**Feature**: 061-finished-goods-inventory-service

## Overview

This feature adds one new model (`FinishedGoodsAdjustment`) and updates two existing models (`FinishedUnit`, `FinishedGood`) to add relationship back-references.

---

## New Model: FinishedGoodsAdjustment

**Purpose**: Audit trail for all inventory changes to finished units and finished goods.

**File**: `src/models/finished_goods_adjustment.py`

### Schema Definition

```python
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey, CheckConstraint
)
from sqlalchemy.orm import relationship
from .base_model import BaseModel
from ..utils.datetime_utils import utc_now


class FinishedGoodsAdjustment(BaseModel):
    """
    Audit record for finished goods inventory adjustments.

    Every change to inventory_count on FinishedUnit or FinishedGood
    creates a corresponding adjustment record for traceability.

    Supports polymorphic tracking - exactly one of finished_unit_id
    or finished_good_id must be set (enforced by CHECK constraint).
    """
    __tablename__ = "finished_goods_adjustments"

    # Polymorphic target (XOR - exactly one must be set)
    finished_unit_id = Column(
        Integer,
        ForeignKey("finished_units.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    finished_good_id = Column(
        Integer,
        ForeignKey("finished_goods.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )

    # Adjustment details
    quantity_change = Column(Integer, nullable=False)
    previous_count = Column(Integer, nullable=False)
    new_count = Column(Integer, nullable=False)

    # Tracking
    reason = Column(String(50), nullable=False)
    notes = Column(Text, nullable=True)
    adjusted_at = Column(DateTime, nullable=False, default=utc_now)

    # Relationships
    finished_unit = relationship(
        "FinishedUnit",
        back_populates="inventory_adjustments",
        lazy="joined"
    )
    finished_good = relationship(
        "FinishedGood",
        back_populates="inventory_adjustments",
        lazy="joined"
    )

    __table_args__ = (
        # XOR constraint: exactly one target must be set
        CheckConstraint(
            "(finished_unit_id IS NOT NULL AND finished_good_id IS NULL) OR "
            "(finished_unit_id IS NULL AND finished_good_id IS NOT NULL)",
            name="ck_adjustment_target_xor"
        ),
        # Validate new_count matches calculation
        CheckConstraint(
            "new_count = previous_count + quantity_change",
            name="ck_adjustment_count_consistency"
        ),
        # Non-negative result
        CheckConstraint(
            "new_count >= 0",
            name="ck_adjustment_new_count_non_negative"
        ),
    )

    @property
    def item_type(self) -> str:
        """Return 'finished_unit' or 'finished_good' based on which FK is set."""
        if self.finished_unit_id is not None:
            return "finished_unit"
        return "finished_good"

    @property
    def item_name(self) -> str:
        """Return display name of the adjusted item."""
        if self.finished_unit:
            return self.finished_unit.display_name
        if self.finished_good:
            return self.finished_good.display_name
        return "Unknown"

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "uuid": str(self.uuid) if self.uuid else None,
            "item_type": self.item_type,
            "finished_unit_id": self.finished_unit_id,
            "finished_good_id": self.finished_good_id,
            "item_name": self.item_name,
            "quantity_change": self.quantity_change,
            "previous_count": self.previous_count,
            "new_count": self.new_count,
            "reason": self.reason,
            "notes": self.notes,
            "adjusted_at": self.adjusted_at.isoformat() if self.adjusted_at else None,
        }
```

### Field Definitions

| Field | Type | Nullable | Default | Notes |
|-------|------|----------|---------|-------|
| `finished_unit_id` | Integer (FK) | Yes | None | FK to finished_units.id, CASCADE delete |
| `finished_good_id` | Integer (FK) | Yes | None | FK to finished_goods.id, CASCADE delete |
| `quantity_change` | Integer | No | N/A | Positive (add) or negative (consume) |
| `previous_count` | Integer | No | N/A | Inventory before adjustment |
| `new_count` | Integer | No | N/A | Inventory after adjustment |
| `reason` | String(50) | No | N/A | See Reason Values below |
| `notes` | Text | Yes | None | Optional context |
| `adjusted_at` | DateTime | No | utc_now() | Timestamp of adjustment |

### Reason Values

| Reason | Description | Typical Quantity |
|--------|-------------|------------------|
| `production` | Production run completed | Positive |
| `assembly` | Assembly run (component consumed or good created) | Both |
| `consumption` | Manual consumption outside assembly | Negative |
| `spoilage` | Item damaged or expired | Negative |
| `gift` | Given away outside normal tracking | Negative |
| `adjustment` | Manual inventory correction | Both |

### Indexes

- `finished_unit_id` - For filtering by finished unit
- `finished_good_id` - For filtering by finished good
- `adjusted_at` - For chronological queries (inherited from BaseModel if applicable)

---

## Model Updates

### FinishedUnit

**File**: `src/models/finished_unit.py`

**Add Relationship**:
```python
# After existing relationships
inventory_adjustments = relationship(
    "FinishedGoodsAdjustment",
    back_populates="finished_unit",
    cascade="all, delete-orphan",
    lazy="dynamic"  # Use dynamic for potentially large collections
)
```

**Remove Business Logic Methods**:
- `is_available(quantity=1)` - Move to service
- `update_inventory(quantity_change)` - Move to service

**Keep**:
- `calculate_current_cost()` - Cost calculation stays on model (data access only)
- `calculate_batches_needed(quantity)` - Recipe calculation stays on model

### FinishedGood

**File**: `src/models/finished_good.py`

**Add Relationship**:
```python
# After existing relationships
inventory_adjustments = relationship(
    "FinishedGoodsAdjustment",
    back_populates="finished_good",
    cascade="all, delete-orphan",
    lazy="dynamic"
)
```

**Remove Business Logic Methods**:
- `is_available(quantity=1)` - Move to service
- `update_inventory(quantity_change)` - Move to service

**Keep** (on model, for now):
- `can_assemble(quantity=1)` - Complex component checking (could move to assembly_service later)
- `get_component_breakdown()` - Data access pattern
- `calculate_current_cost()` - Cost calculation stays on model

---

## Entity Relationships

```
┌─────────────────────┐
│   FinishedUnit      │
│   ─────────────     │
│   inventory_count   │◄─────────┐
│   ...               │          │
└─────────────────────┘          │
                                 │ finished_unit_id (FK)
                                 │
                    ┌────────────┴────────────┐
                    │  FinishedGoodsAdjustment │
                    │  ───────────────────────│
                    │  quantity_change        │
                    │  previous_count         │
                    │  new_count              │
                    │  reason                 │
                    │  notes                  │
                    │  adjusted_at            │
                    └────────────┬────────────┘
                                 │
                                 │ finished_good_id (FK)
┌─────────────────────┐          │
│   FinishedGood      │          │
│   ─────────────     │◄─────────┘
│   inventory_count   │
│   ...               │
└─────────────────────┘
```

---

## Migration Notes

Since this project uses export/reset/import for schema changes (Constitution Principle VI):

1. Export all data before adding the new table
2. The new `FinishedGoodsAdjustment` table starts empty
3. Existing `inventory_count` values are preserved on FinishedUnit/FinishedGood
4. Historical adjustments are not backfilled (only new adjustments tracked)

---

## Constants Addition

**File**: `src/utils/constants.py`

Add to existing file:

```python
# ============================================================================
# Inventory Constants
# ============================================================================

# Default threshold for low stock alerts (finished goods)
DEFAULT_LOW_STOCK_THRESHOLD = 5

# Valid adjustment reasons for finished goods inventory
FINISHED_GOODS_ADJUSTMENT_REASONS = [
    "production",   # Production run completed
    "assembly",     # Assembly operation (consume component or create good)
    "consumption",  # Manual consumption
    "spoilage",     # Damaged or expired
    "gift",         # Given away
    "adjustment",   # Manual correction
]
```

---

## Validation Rules

1. **XOR Constraint**: Exactly one of `finished_unit_id` or `finished_good_id` must be set
2. **Count Consistency**: `new_count` must equal `previous_count + quantity_change`
3. **Non-negative Result**: `new_count` must be >= 0
4. **Valid Reason**: `reason` must be one of the defined values
5. **Required Notes for Adjustment**: When reason is "adjustment", notes should be required (enforced at service level)
