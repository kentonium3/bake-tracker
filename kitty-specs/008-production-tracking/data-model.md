# Data Model: Production Tracking (Feature 008)

**Branch**: `008-production-tracking`
**Date**: 2025-12-04
**Status**: Complete

## Overview

This feature introduces one new model (`ProductionRecord`) and modifies one existing model (`EventRecipientPackage`) to track the production lifecycle.

## New Model: ProductionRecord

Represents a recorded batch of recipe production for an event.

### Entity Definition

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| id | Integer | No | Primary key (inherited from BaseModel) |
| uuid | UUID | No | Unique identifier (inherited from BaseModel) |
| event_id | Integer (FK) | No | Reference to Event being produced for |
| recipe_id | Integer (FK) | No | Reference to Recipe that was produced |
| batches | Integer | No | Number of batches produced (must be > 0) |
| actual_cost | Decimal(10,4) | No | FIFO cost at time of production (snapshot) |
| produced_at | DateTime | No | Timestamp when production was recorded |
| notes | Text | Yes | Optional production notes |
| created_at | DateTime | No | Record creation timestamp |
| updated_at | DateTime | No | Last modification timestamp |

### Relationships

- `event`: Many-to-One with Event (CASCADE on delete)
- `recipe`: Many-to-One with Recipe (RESTRICT on delete)

### Constraints

- `batches > 0` (CHECK constraint)
- `actual_cost >= 0` (CHECK constraint)
- Index on `(event_id, recipe_id)` for production progress queries

### SQLAlchemy Model

```python
class ProductionRecord(BaseModel):
    """
    ProductionRecord model for tracking recipe production.

    Represents batches of a recipe produced for an event,
    with actual FIFO cost captured at production time.
    """
    __tablename__ = "production_records"

    # Foreign keys
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    recipe_id = Column(Integer, ForeignKey("recipes.id", ondelete="RESTRICT"), nullable=False)

    # Production data
    batches = Column(Integer, nullable=False)
    actual_cost = Column(Numeric(10, 4), nullable=False, default=Decimal("0.0000"))
    produced_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    notes = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    event = relationship("Event", back_populates="production_records")
    recipe = relationship("Recipe")

    # Constraints
    __table_args__ = (
        Index("idx_production_event_recipe", "event_id", "recipe_id"),
        Index("idx_production_event", "event_id"),
        Index("idx_production_recipe", "recipe_id"),
        Index("idx_production_produced_at", "produced_at"),
        CheckConstraint("batches > 0", name="ck_production_batches_positive"),
        CheckConstraint("actual_cost >= 0", name="ck_production_cost_non_negative"),
    )
```

---

## Modified Model: EventRecipientPackage

Add production status tracking to existing assignment model.

### New Fields

| Field | Type | Nullable | Default | Description |
|-------|------|----------|---------|-------------|
| status | Enum | No | 'pending' | Package status: pending, assembled, delivered |
| delivered_to | String(500) | Yes | None | Optional delivery note (e.g., "Left with neighbor") |

### Status Enum

```python
class PackageStatus(enum.Enum):
    """Package lifecycle status."""
    PENDING = "pending"      # Not yet assembled
    ASSEMBLED = "assembled"  # All components produced, package ready
    DELIVERED = "delivered"  # Given to recipient
```

### Status Transitions

```
PENDING -> ASSEMBLED (when all required batches produced)
ASSEMBLED -> DELIVERED (when marked as delivered)

Invalid transitions:
- PENDING -> DELIVERED (must assemble first)
- DELIVERED -> ASSEMBLED (no rollback)
- DELIVERED -> PENDING (no rollback)
- ASSEMBLED -> PENDING (no rollback)
```

### Updated SQLAlchemy Model Fragment

```python
# Add to EventRecipientPackage class

from sqlalchemy import Enum as SQLEnum

class PackageStatus(enum.Enum):
    PENDING = "pending"
    ASSEMBLED = "assembled"
    DELIVERED = "delivered"

class EventRecipientPackage(BaseModel):
    # ... existing fields ...

    # New status fields
    status = Column(SQLEnum(PackageStatus), nullable=False, default=PackageStatus.PENDING)
    delivered_to = Column(String(500), nullable=True)

    # Add index for status queries
    __table_args__ = (
        # ... existing indexes ...
        Index("idx_erp_status", "status"),
    )
```

---

## Relationship Updates

### Event Model

Add back_populates for production_records:

```python
class Event(BaseModel):
    # ... existing ...

    production_records = relationship(
        "ProductionRecord",
        back_populates="event",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
```

---

## Migration Requirements

### New Table: production_records

```sql
CREATE TABLE production_records (
    id INTEGER PRIMARY KEY,
    uuid TEXT NOT NULL UNIQUE,
    event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    recipe_id INTEGER NOT NULL REFERENCES recipes(id) ON DELETE RESTRICT,
    batches INTEGER NOT NULL CHECK (batches > 0),
    actual_cost NUMERIC(10, 4) NOT NULL DEFAULT 0.0000 CHECK (actual_cost >= 0),
    produced_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_production_event_recipe ON production_records(event_id, recipe_id);
CREATE INDEX idx_production_event ON production_records(event_id);
CREATE INDEX idx_production_recipe ON production_records(recipe_id);
CREATE INDEX idx_production_produced_at ON production_records(produced_at);
```

### Alter Table: event_recipient_packages

```sql
ALTER TABLE event_recipient_packages
ADD COLUMN status TEXT NOT NULL DEFAULT 'pending'
CHECK (status IN ('pending', 'assembled', 'delivered'));

ALTER TABLE event_recipient_packages
ADD COLUMN delivered_to TEXT;

CREATE INDEX idx_erp_status ON event_recipient_packages(status);
```

---

## Query Patterns

### Get Production Progress for Event

```python
# Sum batches produced per recipe for event
SELECT recipe_id, SUM(batches) as produced
FROM production_records
WHERE event_id = ?
GROUP BY recipe_id;
```

### Get Package Status Summary for Event

```python
# Count packages by status
SELECT status, COUNT(*)
FROM event_recipient_packages
WHERE event_id = ?
GROUP BY status;
```

### Get All Active Events with Progress

```python
# Events with production in progress (not all packages delivered)
SELECT e.*,
       (SELECT COUNT(*) FROM event_recipient_packages WHERE event_id = e.id AND status = 'pending') as pending,
       (SELECT COUNT(*) FROM event_recipient_packages WHERE event_id = e.id AND status = 'assembled') as assembled,
       (SELECT COUNT(*) FROM event_recipient_packages WHERE event_id = e.id AND status = 'delivered') as delivered
FROM events e
WHERE EXISTS (
    SELECT 1 FROM event_recipient_packages
    WHERE event_id = e.id AND status != 'delivered'
);
```
