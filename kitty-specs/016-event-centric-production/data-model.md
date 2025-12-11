# Data Model: Event-Centric Production Model

**Feature**: 016-event-centric-production
**Date**: 2025-12-10
**Status**: Complete

---

## Entity Changes Summary

| Entity | Change Type | Description |
|--------|-------------|-------------|
| ProductionRun | MODIFY | Add `event_id` FK (nullable) |
| AssemblyRun | MODIFY | Add `event_id` FK (nullable) |
| Event | MODIFY | Add relationships for production linkage |
| EventRecipientPackage | MODIFY | Add `fulfillment_status` column |
| EventProductionTarget | NEW | Recipe batch targets per event |
| EventAssemblyTarget | NEW | Finished good quantity targets per event |
| FulfillmentStatus | NEW | Enum for package workflow states |

---

## 1. Modified Entities

### 1.1 ProductionRun

**File**: `src/models/production_run.py`

**New Column**:
```
event_id: Integer, FK → Event(id), NULLABLE, INDEX
```

**New Relationship**:
```
event: Event (back_populates="production_runs")
```

**Cascade Behavior**:
- ON DELETE RESTRICT (cannot delete event with attributed production)

**to_dict() Update**:
- Include `event_id` field
- Include `event_name` when `include_relationships=True`

---

### 1.2 AssemblyRun

**File**: `src/models/assembly_run.py`

**New Column**:
```
event_id: Integer, FK → Event(id), NULLABLE, INDEX
```

**New Relationship**:
```
event: Event (back_populates="assembly_runs")
```

**Cascade Behavior**:
- ON DELETE RESTRICT (cannot delete event with attributed assembly)

**to_dict() Update**:
- Include `event_id` field
- Include `event_name` when `include_relationships=True`

---

### 1.3 Event

**File**: `src/models/event.py`

**New Relationships**:
```
production_runs: List[ProductionRun] (back_populates="event")
assembly_runs: List[AssemblyRun] (back_populates="event")
production_targets: List[EventProductionTarget] (back_populates="event", cascade="all, delete-orphan")
assembly_targets: List[EventAssemblyTarget] (back_populates="event", cascade="all, delete-orphan")
```

---

### 1.4 EventRecipientPackage

**File**: `src/models/event.py`

**New Column**:
```
fulfillment_status: String(20), NOT NULL, DEFAULT 'pending'
```

**Valid Values**: 'pending', 'ready', 'delivered'

**State Transitions** (enforced by service layer):
- pending → ready (only)
- ready → delivered (only)
- delivered → (terminal)

---

## 2. New Entities

### 2.1 FulfillmentStatus (Enum)

**File**: `src/models/event.py`

```python
class FulfillmentStatus(str, Enum):
    PENDING = "pending"      # Not yet assembled
    READY = "ready"          # Assembled, awaiting delivery
    DELIVERED = "delivered"  # Given to recipient
```

---

### 2.2 EventProductionTarget

**File**: `src/models/event.py`

**Purpose**: Define explicit production targets for an event (how many batches of each recipe to make).

**Columns**:

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | Integer | PK, Auto | Unique identifier |
| uuid | String | | UUID for distributed scenarios |
| event_id | Integer | FK → Event, NOT NULL, CASCADE | Which event |
| recipe_id | Integer | FK → Recipe, NOT NULL, RESTRICT | Which recipe |
| target_batches | Integer | NOT NULL, CHECK > 0 | How many batches to produce |
| notes | Text | | Planning notes |
| created_at | DateTime | NOT NULL | When created |
| updated_at | DateTime | NOT NULL | When last modified |

**Table Constraints**:
- UNIQUE(event_id, recipe_id) - one target per recipe per event
- CHECK(target_batches > 0)

**Relationships**:
- event: Event (back_populates="production_targets")
- recipe: Recipe

**Cascade Behavior**:
- Delete Event → CASCADE delete targets
- Delete Recipe → RESTRICT (must remove target first)

---

### 2.3 EventAssemblyTarget

**File**: `src/models/event.py`

**Purpose**: Define explicit assembly targets for an event (how many of each finished good to assemble).

**Columns**:

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | Integer | PK, Auto | Unique identifier |
| uuid | String | | UUID for distributed scenarios |
| event_id | Integer | FK → Event, NOT NULL, CASCADE | Which event |
| finished_good_id | Integer | FK → FinishedGood, NOT NULL, RESTRICT | Which finished good |
| target_quantity | Integer | NOT NULL, CHECK > 0 | How many units to assemble |
| notes | Text | | Planning notes |
| created_at | DateTime | NOT NULL | When created |
| updated_at | DateTime | NOT NULL | When last modified |

**Table Constraints**:
- UNIQUE(event_id, finished_good_id) - one target per finished good per event
- CHECK(target_quantity > 0)

**Relationships**:
- event: Event (back_populates="assembly_targets")
- finished_good: FinishedGood

**Cascade Behavior**:
- Delete Event → CASCADE delete targets
- Delete FinishedGood → RESTRICT (must remove target first)

---

## 3. Entity Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           EVENT PLANNING LAYER                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                              EVENT                                    │   │
│  │  • id, uuid, name, year, event_date, notes                           │   │
│  └───────┬──────────────┬──────────────┬──────────────┬─────────────────┘   │
│          │              │              │              │                      │
│          │ 1:N          │ 1:N          │ 1:N          │ 1:N                  │
│          ▼              ▼              ▼              ▼                      │
│  ┌───────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐  │
│  │EventRecipient │ │EventProduc- │ │EventAssemb- │ │   ProductionRun &   │  │
│  │Package        │ │tionTarget   │ │lyTarget     │ │   AssemblyRun       │  │
│  │               │ │             │ │             │ │   (via event_id FK) │  │
│  │• event_id     │ │• event_id   │ │• event_id   │ │                     │  │
│  │• recipient_id │ │• recipe_id  │ │• finished_  │ │   event_id: nullable│  │
│  │• package_id   │ │• target_    │ │  good_id    │ │   ON DELETE RESTRICT│  │
│  │• quantity     │ │  batches    │ │• target_    │ │                     │  │
│  │• fulfillment_ │ │• notes      │ │  quantity   │ │                     │  │
│  │  status  [NEW]│ │             │ │• notes      │ │                     │  │
│  └───────┬───────┘ └──────┬──────┘ └──────┬──────┘ └─────────────────────┘  │
│          │                │                │                                  │
│          │ N:1            │ N:1            │ N:1                              │
│          ▼                ▼                ▼                                  │
│     Recipient          Recipe        FinishedGood                            │
│       [NEW]            [NEW]             [NEW]                               │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

Cascade/Restrict Summary:
─────────────────────────
Event → EventProductionTarget:  CASCADE (delete targets with event)
Event → EventAssemblyTarget:    CASCADE (delete targets with event)
Event → ProductionRun:          RESTRICT (cannot delete event with runs)
Event → AssemblyRun:            RESTRICT (cannot delete event with runs)
Recipe → EventProductionTarget: RESTRICT (cannot delete recipe with targets)
FinishedGood → EventAssemblyTarget: RESTRICT (cannot delete FG with targets)
```

---

## 4. Service Method Contracts

### 4.1 BatchProductionService Changes

**Method**: `record_batch_production()`

**Current Signature**:
```python
def record_batch_production(
    recipe_id: int,
    num_batches: int,
    actual_yield: int,
    notes: str = None,
    session: Session = None
) -> ProductionRun
```

**New Signature**:
```python
def record_batch_production(
    recipe_id: int,
    num_batches: int,
    actual_yield: int,
    notes: str = None,
    session: Session = None,
    event_id: int = None  # NEW
) -> ProductionRun
```

---

### 4.2 AssemblyService Changes

**Method**: `record_assembly()`

**Current Signature**:
```python
def record_assembly(
    finished_good_id: int,
    quantity: int,
    *,
    assembled_at: Optional[datetime] = None,
    notes: Optional[str] = None,
    session=None
) -> Dict[str, Any]
```

**New Signature**:
```python
def record_assembly(
    finished_good_id: int,
    quantity: int,
    *,
    event_id: int = None,  # NEW
    assembled_at: Optional[datetime] = None,
    notes: Optional[str] = None,
    session=None
) -> Dict[str, Any]
```

---

### 4.3 New EventService Methods

#### Target Management

```python
def set_production_target(
    event_id: int,
    recipe_id: int,
    target_batches: int,
    notes: str = None
) -> EventProductionTarget
"""Create or update production target for a recipe in an event."""

def set_assembly_target(
    event_id: int,
    finished_good_id: int,
    target_quantity: int,
    notes: str = None
) -> EventAssemblyTarget
"""Create or update assembly target for a finished good in an event."""

def get_production_targets(event_id: int) -> List[EventProductionTarget]
"""Get all production targets for an event."""

def get_assembly_targets(event_id: int) -> List[EventAssemblyTarget]
"""Get all assembly targets for an event."""

def delete_production_target(event_id: int, recipe_id: int) -> bool
"""Remove a production target. Returns True if deleted."""

def delete_assembly_target(event_id: int, finished_good_id: int) -> bool
"""Remove an assembly target. Returns True if deleted."""
```

#### Progress Tracking

```python
def get_production_progress(event_id: int) -> List[dict]
"""
Get production progress for an event.

Returns list of:
{
    'recipe': Recipe,
    'recipe_name': str,
    'target_batches': int,
    'produced_batches': int,
    'produced_yield': int,
    'progress_pct': float,
    'is_complete': bool
}
"""

def get_assembly_progress(event_id: int) -> List[dict]
"""
Get assembly progress for an event.

Returns list of:
{
    'finished_good': FinishedGood,
    'finished_good_name': str,
    'target_quantity': int,
    'assembled_quantity': int,
    'progress_pct': float,
    'is_complete': bool
}
"""

def get_event_overall_progress(event_id: int) -> dict
"""
Get overall event progress summary.

Returns:
{
    'production_targets_count': int,
    'production_complete_count': int,
    'production_complete': bool,
    'assembly_targets_count': int,
    'assembly_complete_count': int,
    'assembly_complete': bool,
    'packages_pending': int,
    'packages_ready': int,
    'packages_delivered': int,
    'packages_total': int
}
"""
```

#### Fulfillment Status

```python
def update_fulfillment_status(
    event_recipient_package_id: int,
    new_status: FulfillmentStatus
) -> EventRecipientPackage
"""
Update package fulfillment status.
Enforces sequential workflow: pending → ready → delivered.
Raises ValueError if transition is invalid.
"""

def get_packages_by_status(
    event_id: int,
    status: FulfillmentStatus = None
) -> List[EventRecipientPackage]
"""Get packages filtered by fulfillment status (or all if None)."""
```

---

## 5. Import/Export Schema

### 5.1 New Export Entities

**event_production_targets**:
```json
{
  "event_name": "Christmas 2025",
  "recipe_name": "Chocolate Chip Cookies",
  "target_batches": 4,
  "notes": "Need extras for neighbors"
}
```

**event_assembly_targets**:
```json
{
  "event_name": "Christmas 2025",
  "finished_good_name": "Cookie Gift Box",
  "target_quantity": 5,
  "notes": null
}
```

### 5.2 Modified Export Entities

**production_runs** (add event_name):
```json
{
  "recipe_name": "Chocolate Chip Cookies",
  "event_name": "Christmas 2025",  // NEW - nullable
  "num_batches": 2,
  "actual_yield": 96,
  "produced_at": "2025-12-15T10:00:00",
  "notes": "First batch for holiday"
}
```

**assembly_runs** (add event_name):
```json
{
  "finished_good_name": "Cookie Gift Box",
  "event_name": "Christmas 2025",  // NEW - nullable
  "quantity": 3,
  "assembled_at": "2025-12-18T14:00:00",
  "notes": null
}
```

**event_recipient_packages** (add fulfillment_status):
```json
{
  "event_name": "Christmas 2025",
  "recipient_name": "Alice Johnson",
  "package_name": "Deluxe Cookie Box",
  "quantity": 1,
  "fulfillment_status": "ready",  // NEW
  "notes": null
}
```

---

## 6. Validation Rules

### 6.1 Target Constraints

| Rule | Enforcement |
|------|-------------|
| target_batches > 0 | CHECK constraint + service validation |
| target_quantity > 0 | CHECK constraint + service validation |
| One target per recipe per event | UNIQUE constraint |
| One target per finished_good per event | UNIQUE constraint |

### 6.2 Fulfillment Status Transitions

| Current Status | Allowed Transitions |
|----------------|---------------------|
| pending | ready |
| ready | delivered |
| delivered | (none - terminal) |

**Enforcement**: Service layer validates transitions and raises ValueError on invalid attempts.

### 6.3 Delete Restrictions

| Action | Blocked When |
|--------|--------------|
| Delete Event | ProductionRun or AssemblyRun references event |
| Delete Recipe | EventProductionTarget references recipe |
| Delete FinishedGood | EventAssemblyTarget references finished_good |
