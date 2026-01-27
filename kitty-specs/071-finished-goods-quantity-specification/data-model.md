# Data Model: F071 Finished Goods Quantity Specification

**Date**: 2026-01-27
**Feature**: 071-finished-goods-quantity-specification

## Overview

This feature uses existing data models. No schema changes required.

## Existing Entity: EventFinishedGood

**File**: `src/models/event_finished_good.py`
**Status**: Already exists from F068

### Schema

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | Integer | PK, auto-increment | Record identifier |
| event_id | Integer | FK → events.id, CASCADE | Parent event |
| finished_good_id | Integer | FK → finished_goods.id, RESTRICT | Target finished good |
| quantity | Integer | NOT NULL, CHECK > 0 | Production target quantity |
| created_at | DateTime | NOT NULL, default=utc_now | Record creation timestamp |
| updated_at | DateTime | NOT NULL, auto-update | Last modification timestamp |

### Constraints

```sql
UNIQUE (event_id, finished_good_id)  -- One record per FG per event
CHECK (quantity > 0)                  -- Positive integers only
INDEX idx_event_fg_event (event_id)   -- Query by event
INDEX idx_event_fg_fg (finished_good_id)  -- Query by FG
```

### Relationships

```
Event (1) ────────── (*) EventFinishedGood (*) ────────── (1) FinishedGood
         event_id FK                        finished_good_id FK
```

## Service Layer Methods (New)

### get_event_fg_quantities

```python
def get_event_fg_quantities(
    session: Session,
    event_id: int
) -> List[Tuple[FinishedGood, int]]:
    """
    Get all finished goods with quantities for an event.

    Returns:
        List of (FinishedGood, quantity) tuples

    Raises:
        ValidationError: If event not found
    """
```

### set_event_fg_quantities

```python
def set_event_fg_quantities(
    session: Session,
    event_id: int,
    fg_quantities: List[Tuple[int, int]]  # [(fg_id, quantity), ...]
) -> int:
    """
    Replace all FG quantities for an event (delete old, insert new).

    Args:
        session: Database session
        event_id: Target event
        fg_quantities: List of (finished_good_id, quantity) tuples

    Returns:
        Count of records created

    Raises:
        ValidationError: If event not found
        IntegrityError: If invalid fg_id or quantity <= 0

    Notes:
        - Only FGs available to the event are saved (filters invalid IDs)
        - Uses replace pattern: DELETE existing, INSERT new
        - Empty list clears all FG associations
    """
```

### remove_event_fg

```python
def remove_event_fg(
    session: Session,
    event_id: int,
    fg_id: int
) -> bool:
    """
    Remove a single FG from an event.

    Returns:
        True if record deleted, False if not found
    """
```

## Data Flow

### Save Quantities

```
UI (FGSelectionFrame)
    │
    │  get_selected() → [(fg_id, quantity), ...]
    │
    ▼
Planning Tab
    │
    │  set_event_fg_quantities(session, event_id, fg_quantities)
    │
    ▼
Event Service
    │
    │  1. Validate event exists
    │  2. Filter to available FGs only
    │  3. DELETE FROM event_finished_goods WHERE event_id = ?
    │  4. INSERT INTO event_finished_goods (event_id, fg_id, qty) VALUES ...
    │
    ▼
SQLite (CHECK constraint enforces quantity > 0)
```

### Load Quantities

```
Planning Tab
    │
    │  get_event_fg_quantities(session, event_id)
    │
    ▼
Event Service
    │
    │  SELECT fg.*, efg.quantity
    │  FROM event_finished_goods efg
    │  JOIN finished_goods fg ON efg.finished_good_id = fg.id
    │  WHERE efg.event_id = ?
    │
    ▼
UI (FGSelectionFrame)
    │
    │  set_selected([(fg, quantity), ...])
    │
    ▼
Display: Checkboxes checked, quantity fields populated
```

## Validation Layers

| Layer | Validation | Error Handling |
|-------|------------|----------------|
| UI | Empty OK, positive integers only | Orange text feedback |
| Service | Positive integers, valid FG IDs | ValidationError |
| Database | CHECK(quantity > 0), FK constraints | IntegrityError |

## Migration Notes

No migration needed. EventFinishedGood table exists with all required columns.

If table somehow missing quantity column:
1. Export all data via import/export service
2. Reset database
3. Re-import (import service handles schema alignment)
