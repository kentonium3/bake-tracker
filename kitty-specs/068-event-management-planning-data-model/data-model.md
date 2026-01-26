# Data Model: Event Management & Planning Data Model

**Feature**: 068-event-management-planning-data-model
**Date**: 2026-01-26
**Status**: Complete

## Entity Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         PLANNING DATA MODEL                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────┐                                                        │
│  │   Event     │ (MODIFIED - add expected_attendees, plan_state)        │
│  │  (exists)   │                                                        │
│  └──────┬──────┘                                                        │
│         │                                                                │
│    ┌────┴────┬──────────────┬──────────────┬──────────────┐            │
│    │         │              │              │              │            │
│    ▼         ▼              ▼              ▼              ▼            │
│ ┌──────┐ ┌──────────┐ ┌───────────┐ ┌───────────┐ ┌────────────┐      │
│ │event_│ │event_    │ │batch_     │ │plan_      │ │planning_   │      │
│ │recipes│ │finished_ │ │decisions  │ │amendments │ │snapshots   │      │
│ │(NEW) │ │goods(NEW)│ │(NEW)      │ │(NEW)      │ │(MODIFIED)  │      │
│ └──┬───┘ └────┬─────┘ └─────┬─────┘ └───────────┘ └────────────┘      │
│    │          │             │                                          │
│    ▼          ▼             ▼                                          │
│ ┌──────┐ ┌──────────┐ ┌───────────┐                                   │
│ │Recipe│ │Finished  │ │recipe_    │                                   │
│ │      │ │Good      │ │yield_opts │                                   │
│ └──────┘ └──────────┘ └───────────┘                                   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Entity Definitions

### Event (MODIFIED)

**Location**: `src/models/event.py`

**New Fields**:

| Field | Type | Nullable | Default | Description |
|-------|------|----------|---------|-------------|
| `expected_attendees` | Integer | Yes | NULL | Expected number of attendees (metadata only, not used in calculations) |
| `plan_state` | Enum(PlanState) | No | 'draft' | Current state of the planning workflow |

**New Enum - PlanState**:
```python
class PlanState(str, Enum):
    DRAFT = "draft"           # Initial state, plan can be edited
    LOCKED = "locked"         # Plan finalized, ready for production
    IN_PRODUCTION = "in_production"  # Production started
    COMPLETED = "completed"   # All production complete
```

**Implementation Notes**:
- Add after `output_mode` column
- `plan_state` uses SQLAlchemy `Enum` type
- Add index on `plan_state` for filtering

---

### EventRecipe (NEW)

**Location**: `src/models/event_recipe.py`

**Purpose**: Many-to-many junction table linking events to selected recipes for planning.

| Field | Type | Nullable | Default | Description |
|-------|------|----------|---------|-------------|
| `event_id` | Integer (FK) | No | - | Reference to events.id (CASCADE delete) |
| `recipe_id` | Integer (FK) | No | - | Reference to recipes.id (RESTRICT delete) |
| `created_at` | DateTime | No | utc_now | When recipe was added to event |

**Constraints**:
- Primary Key: Composite (`event_id`, `recipe_id`) via UniqueConstraint
- `event_id` CASCADE on delete (deleting event removes associations)
- `recipe_id` RESTRICT on delete (cannot delete recipe in use)

**Indexes**:
- `idx_event_recipe_event` on `event_id`
- `idx_event_recipe_recipe` on `recipe_id`

**Relationships**:
- `event`: Back to Event with `back_populates="event_recipes"`
- `recipe`: Back to Recipe (no back_populates needed)

---

### EventFinishedGood (NEW)

**Location**: `src/models/event_finished_good.py`

**Purpose**: Tracks finished good selections with quantities for an event.

| Field | Type | Nullable | Default | Description |
|-------|------|----------|---------|-------------|
| `event_id` | Integer (FK) | No | - | Reference to events.id (CASCADE delete) |
| `finished_good_id` | Integer (FK) | No | - | Reference to finished_goods.id (RESTRICT delete) |
| `quantity` | Integer | No | - | Number of units needed (must be positive) |
| `created_at` | DateTime | No | utc_now | When FG was added |
| `updated_at` | DateTime | No | utc_now | Last modification |

**Constraints**:
- Primary Key: Composite (`event_id`, `finished_good_id`) via UniqueConstraint
- `event_id` CASCADE on delete
- `finished_good_id` RESTRICT on delete
- CheckConstraint: `quantity > 0`

**Indexes**:
- `idx_event_fg_event` on `event_id`
- `idx_event_fg_fg` on `finished_good_id`

**Relationships**:
- `event`: Back to Event with `back_populates="event_finished_goods"`
- `finished_good`: Back to FinishedGood (no back_populates needed)

---

### BatchDecision (NEW)

**Location**: `src/models/batch_decision.py`

**Purpose**: Stores user's batch choice per recipe for an event (floor vs ceil decision).

| Field | Type | Nullable | Default | Description |
|-------|------|----------|---------|-------------|
| `event_id` | Integer (FK) | No | - | Reference to events.id (CASCADE delete) |
| `recipe_id` | Integer (FK) | No | - | Reference to recipes.id (RESTRICT delete) |
| `batches` | Integer | No | - | Number of batches to make (must be positive) |
| `finished_unit_id` | Integer (FK) | Yes | NULL | Reference to finished_units.id (for multi-yield recipes) |
| `created_at` | DateTime | No | utc_now | When decision was made |
| `updated_at` | DateTime | No | utc_now | Last modification |

**Note**: The func-spec referenced `recipe_yield_options` which doesn't exist in the schema. Yield data is stored on `FinishedUnit` model. The `finished_unit_id` field allows specifying which FinishedUnit's yield to use when a recipe produces multiple output types (e.g., small vs large cookies from same recipe).

**Constraints**:
- Primary Key: Composite (`event_id`, `recipe_id`) via UniqueConstraint
- `event_id` CASCADE on delete
- `recipe_id` RESTRICT on delete
- `finished_unit_id` SET NULL on delete
- CheckConstraint: `batches > 0`

**Indexes**:
- `idx_batch_decision_event` on `event_id`
- `idx_batch_decision_recipe` on `recipe_id`
- `idx_batch_decision_finished_unit` on `finished_unit_id`

**Relationships**:
- `event`: Back to Event with `back_populates="batch_decisions"`
- `recipe`: Back to Recipe (no back_populates needed)
- `finished_unit`: Back to FinishedUnit (no back_populates needed)

---

### PlanAmendment (NEW)

**Location**: `src/models/plan_amendment.py`

**Purpose**: Tracks amendments to locked plans during production (Phase 3 preparation).

| Field | Type | Nullable | Default | Description |
|-------|------|----------|---------|-------------|
| `id` | Integer | No | auto | Primary key |
| `event_id` | Integer (FK) | No | - | Reference to events.id (CASCADE delete) |
| `amendment_type` | Enum(AmendmentType) | No | - | Type of amendment |
| `amendment_data` | JSON | No | - | Type-specific amendment details |
| `reason` | Text | Yes | NULL | User-provided reason for amendment |
| `created_at` | DateTime | No | utc_now | When amendment was made |

**New Enum - AmendmentType**:
```python
class AmendmentType(str, Enum):
    DROP_FG = "drop_fg"           # Remove a finished good from plan
    ADD_FG = "add_fg"             # Add a finished good to plan
    MODIFY_BATCH = "modify_batch" # Change batch count for a recipe
```

**Constraints**:
- Primary Key: `id` (standard auto-increment)
- `event_id` CASCADE on delete

**Indexes**:
- `idx_plan_amendment_event` on `event_id`
- `idx_plan_amendment_type` on `amendment_type`
- `idx_plan_amendment_created` on `created_at`

**amendment_data JSON schemas by type**:
```json
// DROP_FG
{"finished_good_id": 123, "original_quantity": 50}

// ADD_FG
{"finished_good_id": 456, "quantity": 25}

// MODIFY_BATCH
{"recipe_id": 789, "original_batches": 3, "new_batches": 4}
```

**Relationships**:
- `event`: Back to Event with `back_populates="plan_amendments"`

---

### PlanningSnapshot (MODIFIED)

**Location**: `src/models/planning_snapshot.py`

**New Fields**:

| Field | Type | Nullable | Default | Description |
|-------|------|----------|---------|-------------|
| `snapshot_type` | Enum(SnapshotType) | Yes | NULL | ORIGINAL or CURRENT (Phase 3 use) |
| `snapshot_data` | JSON | Yes | NULL | Complete plan state for comparison (Phase 3 use) |

**New Enum - SnapshotType**:
```python
class SnapshotType(str, Enum):
    ORIGINAL = "original"  # Snapshot when plan was locked
    CURRENT = "current"    # Latest snapshot reflecting amendments
```

**Implementation Notes**:
- Fields nullable for backward compatibility with existing records
- Phase 3 (F078-F079) will populate these fields
- Add index on `snapshot_type`

---

## Relationship Summary

### Event Model New Relationships

Add to `src/models/event.py`:

```python
# Planning module relationships (F068)
event_recipes = relationship(
    "EventRecipe",
    back_populates="event",
    cascade="all, delete-orphan",
    lazy="selectin",
)
event_finished_goods = relationship(
    "EventFinishedGood",
    back_populates="event",
    cascade="all, delete-orphan",
    lazy="selectin",
)
batch_decisions = relationship(
    "BatchDecision",
    back_populates="event",
    cascade="all, delete-orphan",
    lazy="selectin",
)
plan_amendments = relationship(
    "PlanAmendment",
    back_populates="event",
    cascade="all, delete-orphan",
    lazy="selectin",
)
```

---

## Import/Export Order

New tables must be added to import/export service in this order (respecting FK dependencies):

**Export order** (after existing tables):
1. `event_recipes` (depends on: events, recipes)
2. `event_finished_goods` (depends on: events, finished_goods)
3. `batch_decisions` (depends on: events, recipes, finished_units)
4. `plan_amendments` (depends on: events)

**Import order**: Same as export (FK targets must exist before FK sources)

---

## Model File Updates

### `src/models/__init__.py`

Add exports:
```python
from .event_recipe import EventRecipe
from .event_finished_good import EventFinishedGood
from .batch_decision import BatchDecision
from .plan_amendment import PlanAmendment, AmendmentType
from .event import PlanState  # New enum
from .planning_snapshot import SnapshotType  # New enum
```

---

## Validation Rules

| Entity | Rule | Implementation |
|--------|------|----------------|
| Event.expected_attendees | Must be positive or NULL | CheckConstraint or service validation |
| Event.plan_state | Valid enum value | SQLAlchemy Enum type enforces |
| EventRecipe | Unique (event_id, recipe_id) | UniqueConstraint |
| EventFinishedGood.quantity | Must be > 0 | CheckConstraint |
| BatchDecision.batches | Must be > 0 | CheckConstraint |
| BatchDecision | Unique (event_id, recipe_id) | UniqueConstraint |
