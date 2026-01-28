# Data Model: Plan Snapshots & Amendments

**Feature**: F078 Plan Snapshots & Amendments
**Date**: 2026-01-27

## Overview

This feature requires one new model (`PlanSnapshot`) and uses an existing model (`PlanAmendment` from F068).

## New Model: PlanSnapshot

### Purpose

Captures complete plan state as JSON when production starts. Provides the baseline for comparing original plan against current (amended) plan.

### Table: `plan_snapshots`

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | Integer | NO | auto | Primary key (inherited from BaseModel) |
| uuid | String(36) | NO | auto | UUID for distributed scenarios (inherited) |
| event_id | Integer | NO | - | FK to events.id (CASCADE delete) |
| snapshot_data | JSON | NO | - | Complete plan state as JSON |
| created_at | DateTime | NO | utc_now | When snapshot was created |

### Constraints

- **Unique**: One snapshot per event (`event_id` unique constraint)
- **FK**: `event_id` references `events.id` with CASCADE delete

### Indexes

- `idx_plan_snapshot_event` on `event_id`

### Relationships

- `event`: Many-to-one with Event (back_populates="plan_snapshot")

### JSON Schema: `snapshot_data`

```json
{
  "snapshot_version": "1.0",
  "created_at": "2026-01-27T15:30:00Z",
  "recipes": [
    {
      "recipe_id": 1,
      "recipe_name": "Chocolate Chip Cookies",
      "recipe_slug": "chocolate-chip-cookies"
    }
  ],
  "finished_goods": [
    {
      "fg_id": 1,
      "fg_name": "Cookie Gift Box",
      "fg_slug": "cookie-gift-box",
      "quantity": 10
    }
  ],
  "batch_decisions": [
    {
      "recipe_id": 1,
      "recipe_name": "Chocolate Chip Cookies",
      "batches": 5,
      "yield_per_batch": 24,
      "total_yield": 120
    }
  ]
}
```

### SQLAlchemy Model

```python
"""
PlanSnapshot model for capturing plan state at production start.

Feature 078: Plan Snapshots & Amendments
"""

from sqlalchemy import (
    Column,
    Integer,
    DateTime,
    ForeignKey,
    Index,
    UniqueConstraint,
)
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import relationship

from .base import BaseModel
from src.utils.datetime_utils import utc_now


class PlanSnapshot(BaseModel):
    """
    Captures complete plan state when production starts.

    Created automatically when start_production() transitions
    an event from LOCKED to IN_PRODUCTION state. Stores the
    original plan as JSON for later comparison.

    Attributes:
        event_id: Foreign key to Event (CASCADE delete)
        snapshot_data: JSON containing recipes, FGs, batch decisions
        created_at: When snapshot was created
    """

    __tablename__ = "plan_snapshots"

    # Foreign keys
    event_id = Column(
        Integer,
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # One snapshot per event
        index=True,
    )

    # Snapshot data
    snapshot_data = Column(JSON, nullable=False)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=utc_now)

    # Relationships
    event = relationship("Event", back_populates="plan_snapshot")

    # Indexes
    __table_args__ = (
        Index("idx_plan_snapshot_event", "event_id"),
        UniqueConstraint("event_id", name="uq_plan_snapshot_event"),
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"PlanSnapshot(id={self.id}, event_id={self.event_id})"
```

## Existing Model: PlanAmendment

### Location

`src/models/plan_amendment.py` (created in F068)

### No Changes Required

The existing model has all required fields:

| Column | Type | Description |
|--------|------|-------------|
| event_id | Integer | FK to events.id |
| amendment_type | Enum(AmendmentType) | DROP_FG, ADD_FG, MODIFY_BATCH |
| amendment_data | JSON | Type-specific data |
| reason | Text | User-provided reason |
| created_at | DateTime | When amendment was made |

### AmendmentType Enum (Existing)

```python
class AmendmentType(str, Enum):
    DROP_FG = "drop_fg"
    ADD_FG = "add_fg"
    MODIFY_BATCH = "modify_batch"
```

### Amendment Data Schemas

**DROP_FG**:
```json
{
  "fg_id": 1,
  "fg_name": "Cookie Gift Box",
  "original_quantity": 10
}
```

**ADD_FG**:
```json
{
  "fg_id": 2,
  "fg_name": "Brownie Box",
  "quantity": 5
}
```

**MODIFY_BATCH**:
```json
{
  "recipe_id": 1,
  "recipe_name": "Chocolate Chip Cookies",
  "old_batches": 5,
  "new_batches": 7
}
```

## Event Model Update

Add relationship to PlanSnapshot in `src/models/event.py`:

```python
# In Event class, add:
plan_snapshot = relationship(
    "PlanSnapshot",
    back_populates="event",
    uselist=False,  # One-to-one
    cascade="all, delete-orphan",
    lazy="selectin",
)
```

## Model Registration

Add to `src/models/__init__.py`:

```python
from .plan_snapshot import PlanSnapshot

__all__ = [
    # ... existing exports ...
    "PlanSnapshot",
]
```

## Migration Notes

Since this is a desktop application using the export/reset/import strategy:
1. New table `plan_snapshots` will be created on next database reset
2. No migration script required
3. Existing events will have no snapshots (created only on future start_production calls)
