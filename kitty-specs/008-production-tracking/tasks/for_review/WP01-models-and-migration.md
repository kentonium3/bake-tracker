---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
  - "T003"
  - "T004"
  - "T005"
  - "T006"
title: "Models & Database Migration"
phase: "Phase 1 - Foundation"
lane: "for_review"
assignee: ""
agent: "claude"
shell_pid: "58999"
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-04T12:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 - Models & Database Migration

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

- Create `PackageStatus` enum for package lifecycle tracking
- Create `ProductionRecord` model for tracking recipe production with FIFO costs
- Add `status` and `delivered_to` fields to existing `EventRecipientPackage` model
- Add `production_records` relationship to `Event` model
- Update model exports in `__init__.py`
- Create and run database migration successfully
- All models import without errors
- Database schema matches data-model.md specification

## Context & Constraints

**Reference Documents**:
- Constitution: `.kittify/memory/constitution.md` (Principle VI: Migration Safety)
- Plan: `kitty-specs/008-production-tracking/plan.md`
- Data Model: `kitty-specs/008-production-tracking/data-model.md`
- Spec: `kitty-specs/008-production-tracking/spec.md`

**Architecture Constraints**:
- Models layer defines schema and relationships only (no business logic)
- Use SQLAlchemy 2.x patterns consistent with existing models
- Follow existing BaseModel inheritance pattern
- Migration must support rollback

**Existing Patterns** (reference these files):
- `src/models/event.py` - EventRecipientPackage model to modify
- `src/models/finished_good.py` - Example of enum usage with SQLAlchemy
- `src/models/base.py` - BaseModel inheritance

---

## Subtasks & Detailed Guidance

### Subtask T001 - Create PackageStatus Enum [P]

**Purpose**: Define the three-state lifecycle enum for package status.

**Steps**:
1. Create new file `src/models/package_status.py`
2. Import `enum` module
3. Define `PackageStatus(enum.Enum)` with values:
   - `PENDING = "pending"`
   - `ASSEMBLED = "assembled"`
   - `DELIVERED = "delivered"`
4. Add docstring explaining the enum purpose

**Files**: `src/models/package_status.py` (NEW)

**Parallel?**: Yes - no dependencies on other subtasks

**Code Template**:
```python
"""
Package status enum for production lifecycle tracking.
"""
import enum


class PackageStatus(enum.Enum):
    """Package lifecycle status for EventRecipientPackage."""
    PENDING = "pending"      # Not yet assembled
    ASSEMBLED = "assembled"  # All components produced, package ready
    DELIVERED = "delivered"  # Given to recipient
```

---

### Subtask T002 - Create ProductionRecord Model [P]

**Purpose**: Model for tracking recipe production with actual FIFO costs.

**Steps**:
1. Create new file `src/models/production_record.py`
2. Import required modules (datetime, Decimal, SQLAlchemy components, BaseModel)
3. Define `ProductionRecord(BaseModel)` with:
   - `__tablename__ = "production_records"`
   - Foreign keys: `event_id`, `recipe_id`
   - Fields: `batches`, `actual_cost`, `produced_at`, `notes`
   - Timestamps: `created_at`, `updated_at`
   - Relationships: `event`, `recipe`
   - Constraints and indexes per data-model.md
4. Add comprehensive docstring

**Files**: `src/models/production_record.py` (NEW)

**Parallel?**: Yes - no dependencies on T001

**Key Constraints**:
- `batches > 0` (CHECK constraint)
- `actual_cost >= 0` (CHECK constraint)
- `event_id` FK with CASCADE delete
- `recipe_id` FK with RESTRICT delete

**Reference**: See `data-model.md` for exact SQLAlchemy code template.

---

### Subtask T003 - Add Status Fields to EventRecipientPackage

**Purpose**: Extend existing model with production status tracking.

**Steps**:
1. Open `src/models/event.py`
2. Import `PackageStatus` from `package_status.py`
3. Import `Enum as SQLEnum` from sqlalchemy
4. Add to `EventRecipientPackage` class:
   - `status = Column(SQLEnum(PackageStatus), nullable=False, default=PackageStatus.PENDING)`
   - `delivered_to = Column(String(500), nullable=True)`
5. Add index in `__table_args__`: `Index("idx_erp_status", "status")`

**Files**: `src/models/event.py` (MODIFY)

**Parallel?**: No - depends on T001 for PackageStatus import

**Notes**:
- Preserve all existing fields and relationships
- Add new fields after existing `notes` field
- Keep existing `__table_args__` indexes, just add new one

---

### Subtask T004 - Add production_records Relationship to Event

**Purpose**: Enable navigation from Event to its production records.

**Steps**:
1. In `src/models/event.py`, in the `Event` class
2. Add import for ProductionRecord (or use string reference)
3. Add relationship:
```python
production_records = relationship(
    "ProductionRecord",
    back_populates="event",
    cascade="all, delete-orphan",
    lazy="selectin"
)
```

**Files**: `src/models/event.py` (MODIFY)

**Parallel?**: No - depends on T002 for ProductionRecord model

---

### Subtask T005 - Update Model Exports

**Purpose**: Make new models importable from `src.models`.

**Steps**:
1. Open `src/models/__init__.py`
2. Add imports:
   - `from .package_status import PackageStatus`
   - `from .production_record import ProductionRecord`
3. Add to `__all__` list if present

**Files**: `src/models/__init__.py` (MODIFY)

**Parallel?**: No - depends on T001, T002

---

### Subtask T006 - Create and Run Database Migration

**Purpose**: Apply schema changes to database safely.

**Steps**:
1. Check if project uses Alembic or manual migrations
2. For this project (SQLite + manual): Create migration script or use SQLAlchemy create_all
3. If manual migration needed, create SQL:
```sql
-- New table
CREATE TABLE IF NOT EXISTS production_records (
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

CREATE INDEX IF NOT EXISTS idx_production_event_recipe ON production_records(event_id, recipe_id);
CREATE INDEX IF NOT EXISTS idx_production_event ON production_records(event_id);
CREATE INDEX IF NOT EXISTS idx_production_recipe ON production_records(recipe_id);
CREATE INDEX IF NOT EXISTS idx_production_produced_at ON production_records(produced_at);

-- Alter existing table
ALTER TABLE event_recipient_packages ADD COLUMN status TEXT NOT NULL DEFAULT 'pending';
ALTER TABLE event_recipient_packages ADD COLUMN delivered_to TEXT;
CREATE INDEX IF NOT EXISTS idx_erp_status ON event_recipient_packages(status);
```
4. Verify existing data preserved
5. Test rollback capability

**Files**: Migration script or direct schema update

**Parallel?**: No - must be last, depends on all models being defined

**Risk Mitigation**:
- Backup database before migration
- Use transactions
- Test with dry-run if available

---

## Test Strategy

1. **Model Import Test**: Verify all models import without circular dependency errors
2. **Schema Verification**: Check table structure matches specification
3. **Constraint Test**: Verify CHECK constraints work (batches > 0, actual_cost >= 0)
4. **Relationship Test**: Verify Event.production_records and ProductionRecord.event work
5. **Default Test**: Verify EventRecipientPackage.status defaults to PENDING

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Circular import with models | Use string references in relationships |
| ALTER TABLE on existing data | Set sensible defaults (status='pending') |
| SQLite ALTER limitations | May need to recreate table for complex changes |

---

## Definition of Done Checklist

- [ ] PackageStatus enum created and documented
- [ ] ProductionRecord model created with all fields, constraints, indexes
- [ ] EventRecipientPackage has status and delivered_to fields
- [ ] Event has production_records relationship
- [ ] All models exported from __init__.py
- [ ] Database migration applied successfully
- [ ] Existing data preserved (status defaults to 'pending')
- [ ] Models import without errors in Python REPL test
- [ ] `tasks.md` updated with completion status

---

## Review Guidance

- Verify CHECK constraints are properly defined
- Verify relationship back_populates match
- Verify index naming follows existing conventions
- Test that existing EventRecipientPackage data gets status='pending' default

---

## Activity Log

- 2025-12-04T12:00:00Z - system - lane=planned - Prompt created via /spec-kitty.tasks
- 2025-12-04T16:21:42Z – claude – shell_pid=58999 – lane=doing – Started implementation (retroactive recovery)
- 2025-12-04T16:26:46Z – claude – shell_pid=58999 – lane=for_review – Implementation complete, ready for review (retroactive recovery)
