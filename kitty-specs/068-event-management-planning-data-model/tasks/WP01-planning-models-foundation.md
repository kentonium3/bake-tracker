---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
  - "T003"
  - "T004"
  - "T005"
  - "T006"
  - "T007"
title: "Planning Models Foundation"
phase: "Phase 1 - Foundation"
lane: "doing"
assignee: ""
agent: "claude"
shell_pid: "90115"
review_status: ""
reviewed_by: ""
dependencies: []
history:
  - timestamp: "2026-01-26T19:16:03Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 – Planning Models Foundation

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you understand the feedback, update `review_status: acknowledged` in the frontmatter.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Implementation Command

**No dependencies** - Start from main branch:
```bash
spec-kitty implement WP01
```

---

## Objectives & Success Criteria

**Goal**: Create all new planning model files and extend existing Event model with planning fields and relationships.

**Success Criteria**:
- [ ] PlanState enum defined in `src/models/event.py`
- [ ] Event model has `expected_attendees` and `plan_state` fields
- [ ] Event model has 4 new planning relationships
- [ ] EventRecipe, EventFinishedGood, BatchDecision models created
- [ ] All models follow existing SQLAlchemy patterns
- [ ] Models import without circular dependency errors
- [ ] SQLAlchemy can create tables from models

---

## Context & Constraints

**Reference Documents**:
- Data model: `kitty-specs/068-event-management-planning-data-model/data-model.md`
- Research patterns: `kitty-specs/068-event-management-planning-data-model/research.md`
- Constitution: `.kittify/memory/constitution.md` (Principle V: Layered Architecture)

**Key Patterns to Follow**:
- Study `src/models/event.py` for existing Event structure (~503 lines)
- Study `EventProductionTarget` class in event.py for junction table pattern
- All models inherit from `BaseModel` (from `.base`)
- Use `utc_now` from `src.utils.datetime_utils` for timestamps

**Constraints**:
- Do NOT modify EventService in this WP (that's WP02)
- Do NOT create __init__.py exports yet (that's WP02)
- Focus ONLY on model definitions

---

## Subtasks & Detailed Guidance

### Subtask T001 – Add PlanState Enum to event.py [P]

**Purpose**: Define the planning workflow states that events can be in.

**Steps**:
1. Open `src/models/event.py`
2. Add import: `from enum import Enum` (if not present)
3. Add PlanState enum AFTER existing enums (FulfillmentStatus, OutputMode):

```python
class PlanState(str, Enum):
    """
    Planning workflow states for events.

    Workflow is sequential: DRAFT → LOCKED → IN_PRODUCTION → COMPLETED
    State transitions are implemented in F077; F068 just defines the enum.
    """
    DRAFT = "draft"                 # Initial state, plan can be edited
    LOCKED = "locked"               # Plan finalized, ready for production
    IN_PRODUCTION = "in_production" # Production started
    COMPLETED = "completed"         # All production complete
```

**Files**: `src/models/event.py` (modify)
**Parallel?**: Yes - can be done alongside T005-T007
**Validation**: Enum can be imported: `from src.models.event import PlanState`

---

### Subtask T002 – Add expected_attendees Field to Event Model

**Purpose**: Store expected number of attendees (metadata only, not used in calculations).

**Steps**:
1. In `src/models/event.py`, find the Event class columns section
2. Add after `output_mode` column:

```python
# Planning metadata (F068)
expected_attendees = Column(Integer, nullable=True, index=True)
```

**Files**: `src/models/event.py` (modify)
**Parallel?**: No - must follow T001 if adding plan_state import
**Notes**:
- Nullable because it's optional metadata
- Index for potential filtering by attendee count

---

### Subtask T003 – Add plan_state Field to Event Model

**Purpose**: Track the planning workflow state for each event.

**Steps**:
1. In `src/models/event.py`, add the SQLAlchemy Enum import:
   ```python
   from sqlalchemy import ... Enum as SQLEnum ...
   ```
2. Add after `expected_attendees`:

```python
plan_state = Column(
    SQLEnum(PlanState),
    nullable=False,
    default=PlanState.DRAFT,
    index=True,
)
```

3. Add index to `__table_args__`:
```python
Index("idx_event_plan_state", "plan_state"),
```

**Files**: `src/models/event.py` (modify)
**Parallel?**: No - depends on T001 (enum must exist)
**Notes**:
- NOT nullable - always has a state
- Default to DRAFT for new events
- Index for filtering events by planning state

---

### Subtask T004 – Add Planning Relationships to Event Model

**Purpose**: Enable navigation from Event to planning association tables.

**Steps**:
1. In `src/models/event.py`, find the Relationships section
2. Add AFTER existing relationships (after `planning_snapshots` relationship):

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

**Files**: `src/models/event.py` (modify)
**Parallel?**: No - relationships reference models that may not exist yet
**Notes**:
- `cascade="all, delete-orphan"` ensures deleting event removes associations
- `lazy="selectin"` for efficient batch loading
- These will cause import warnings until T005-T007 models are created

---

### Subtask T005 – Create EventRecipe Model [P]

**Purpose**: Many-to-many junction table linking events to selected recipes for planning.

**Steps**:
1. Create new file `src/models/event_recipe.py`
2. Implement the model following this structure:

```python
"""
EventRecipe model for event-recipe planning associations.

Many-to-many junction table linking events to selected recipes.
Feature 068: Event Management & Planning Data Model
"""

from sqlalchemy import (
    Column,
    Integer,
    DateTime,
    ForeignKey,
    Index,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from .base import BaseModel
from src.utils.datetime_utils import utc_now


class EventRecipe(BaseModel):
    """
    Junction table linking events to selected recipes for planning.

    Attributes:
        event_id: Foreign key to Event (CASCADE delete)
        recipe_id: Foreign key to Recipe (RESTRICT delete)
        created_at: When recipe was added to event
    """

    __tablename__ = "event_recipes"

    # Foreign keys
    event_id = Column(
        Integer,
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    recipe_id = Column(
        Integer,
        ForeignKey("recipes.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=utc_now)

    # Relationships
    event = relationship("Event", back_populates="event_recipes")
    recipe = relationship("Recipe")

    # Constraints and indexes
    __table_args__ = (
        UniqueConstraint("event_id", "recipe_id", name="uq_event_recipe"),
        Index("idx_event_recipe_event", "event_id"),
        Index("idx_event_recipe_recipe", "recipe_id"),
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"EventRecipe(event_id={self.event_id}, recipe_id={self.recipe_id})"
```

**Files**: `src/models/event_recipe.py` (new file, ~60 lines)
**Parallel?**: Yes - independent file
**Validation**:
- Model can be imported without error
- SQLAlchemy can create table with correct FK relationships

---

### Subtask T006 – Create EventFinishedGood Model [P]

**Purpose**: Track finished good selections with quantities for an event.

**Steps**:
1. Create new file `src/models/event_finished_good.py`
2. Implement the model:

```python
"""
EventFinishedGood model for event FG planning associations.

Tracks finished good selections with quantities for planning.
Feature 068: Event Management & Planning Data Model
"""

from sqlalchemy import (
    Column,
    Integer,
    DateTime,
    ForeignKey,
    Index,
    UniqueConstraint,
    CheckConstraint,
)
from sqlalchemy.orm import relationship

from .base import BaseModel
from src.utils.datetime_utils import utc_now


class EventFinishedGood(BaseModel):
    """
    Tracks finished good selections with quantities for an event.

    Attributes:
        event_id: Foreign key to Event (CASCADE delete)
        finished_good_id: Foreign key to FinishedGood (RESTRICT delete)
        quantity: Number of units needed (must be positive)
        created_at: When FG was added
        updated_at: Last modification
    """

    __tablename__ = "event_finished_goods"

    # Foreign keys
    event_id = Column(
        Integer,
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    finished_good_id = Column(
        Integer,
        ForeignKey("finished_goods.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # Quantity
    quantity = Column(Integer, nullable=False)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=utc_now)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    # Relationships
    event = relationship("Event", back_populates="event_finished_goods")
    finished_good = relationship("FinishedGood")

    # Constraints and indexes
    __table_args__ = (
        UniqueConstraint("event_id", "finished_good_id", name="uq_event_finished_good"),
        CheckConstraint("quantity > 0", name="ck_event_fg_quantity_positive"),
        Index("idx_event_fg_event", "event_id"),
        Index("idx_event_fg_fg", "finished_good_id"),
    )

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"EventFinishedGood(event_id={self.event_id}, "
            f"finished_good_id={self.finished_good_id}, quantity={self.quantity})"
        )
```

**Files**: `src/models/event_finished_good.py` (new file, ~75 lines)
**Parallel?**: Yes - independent file
**Validation**: CheckConstraint prevents quantity <= 0

---

### Subtask T007 – Create BatchDecision Model [P]

**Purpose**: Store user's batch choice per recipe for an event (floor vs ceil decision).

**Steps**:
1. Create new file `src/models/batch_decision.py`
2. Implement the model:

```python
"""
BatchDecision model for storing user's batch choices.

Records the number of batches chosen for each recipe in an event plan.
Feature 068: Event Management & Planning Data Model
"""

from sqlalchemy import (
    Column,
    Integer,
    DateTime,
    ForeignKey,
    Index,
    UniqueConstraint,
    CheckConstraint,
)
from sqlalchemy.orm import relationship

from .base import BaseModel
from src.utils.datetime_utils import utc_now


class BatchDecision(BaseModel):
    """
    Stores user's batch choice per recipe for an event.

    When planning, users decide how many batches of each recipe to make.
    This table records those decisions, optionally linked to a specific
    FinishedUnit for recipes with multiple yield types.

    Attributes:
        event_id: Foreign key to Event (CASCADE delete)
        recipe_id: Foreign key to Recipe (RESTRICT delete)
        batches: Number of batches to make (must be positive)
        finished_unit_id: Optional FK to FinishedUnit (for multi-yield recipes)
        created_at: When decision was made
        updated_at: Last modification
    """

    __tablename__ = "batch_decisions"

    # Foreign keys
    event_id = Column(
        Integer,
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    recipe_id = Column(
        Integer,
        ForeignKey("recipes.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    finished_unit_id = Column(
        Integer,
        ForeignKey("finished_units.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Batch count
    batches = Column(Integer, nullable=False)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=utc_now)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    # Relationships
    event = relationship("Event", back_populates="batch_decisions")
    recipe = relationship("Recipe")
    finished_unit = relationship("FinishedUnit")

    # Constraints and indexes
    __table_args__ = (
        UniqueConstraint("event_id", "recipe_id", name="uq_batch_decision_event_recipe"),
        CheckConstraint("batches > 0", name="ck_batch_decision_batches_positive"),
        Index("idx_batch_decision_event", "event_id"),
        Index("idx_batch_decision_recipe", "recipe_id"),
        Index("idx_batch_decision_finished_unit", "finished_unit_id"),
    )

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"BatchDecision(event_id={self.event_id}, "
            f"recipe_id={self.recipe_id}, batches={self.batches})"
        )
```

**Files**: `src/models/batch_decision.py` (new file, ~90 lines)
**Parallel?**: Yes - independent file
**Notes**:
- `finished_unit_id` is optional (SET NULL on delete)
- Used when recipe produces multiple FinishedUnit types

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Circular imports | Follow existing pattern: models reference each other by string name in relationships |
| FK ordering issues | SQLAlchemy handles deferred FK resolution; just ensure table names match |
| Relationship warnings | Expected until all models exist; will resolve after WP02 completes |

---

## Definition of Done Checklist

- [ ] PlanState enum defined and importable
- [ ] Event model has expected_attendees field
- [ ] Event model has plan_state field with default DRAFT
- [ ] Event model has 4 new relationships
- [ ] EventRecipe model created with correct constraints
- [ ] EventFinishedGood model created with quantity > 0 constraint
- [ ] BatchDecision model created with batches > 0 constraint
- [ ] All models can be imported without error
- [ ] Code follows existing model patterns exactly

---

## Review Guidance

**Reviewers should verify**:
1. Enum values match data-model.md specification
2. All FK constraints use correct ondelete behavior (CASCADE vs RESTRICT)
3. CheckConstraints prevent invalid data (quantity > 0, batches > 0)
4. UniqueConstraints on composite keys
5. Indexes defined for all FK columns
6. Docstrings present and accurate
7. No business logic in models (that belongs in service layer)

---

## Activity Log

- 2026-01-26T19:16:03Z – system – lane=planned – Prompt created.
- 2026-01-26T19:25:36Z – claude – shell_pid=90115 – lane=doing – Started implementation via workflow command
