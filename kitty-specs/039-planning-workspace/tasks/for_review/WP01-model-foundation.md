---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
  - "T003"
  - "T004"
  - "T005"
  - "T006"
title: "Model Foundation"
phase: "Phase 1 - Foundation"
lane: "for_review"
assignee: ""
agent: "claude"
shell_pid: "57515"
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-06T03:09:20Z"
    lane: "planned"
    agent: "claude"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 - Model Foundation

## Review Feedback

> **Populated by `/spec-kitty.review`** - Reviewers add detailed feedback here when work needs changes. Implementation must address every item listed below before returning for re-review.

*[This section is empty initially. Reviewers will populate it if the work is returned from review. If you see feedback here, treat each item as a must-do before completion.]*

---

## Objectives & Success Criteria

- Add `OutputMode` enum to Event model supporting BUNDLED and BULK_COUNT modes
- Create `ProductionPlanSnapshot` model for persisting calculated plans
- Establish relationships between Event and ProductionPlanSnapshot
- All models import correctly and tests pass

**Success Metrics:**
- New tables created in database
- `Event.output_mode` field is accessible and accepts enum values
- `ProductionPlanSnapshot` can store JSON calculation results
- Unit tests achieve 100% coverage on new model

---

## Context & Constraints

### Reference Documents
- **Constitution**: `.kittify/memory/constitution.md` - Principle III (Future-Proof Schema), Principle VI (Schema Change Strategy)
- **Plan**: `kitty-specs/039-planning-workspace/plan.md` - Project structure, engineering decisions
- **Data Model**: `kitty-specs/039-planning-workspace/data-model.md` - Full schema definitions
- **Research**: `kitty-specs/039-planning-workspace/research.md` - Timestamp field naming differences

### Key Constraints
- Event uses `date_added`/`last_modified` (not standard `created_at`/`updated_at`)
- ProductionPlanSnapshot must use BaseModel for standard timestamps
- Schema change follows export/reset/import pattern per constitution
- SQLite with WAL mode for local desktop database

### Architectural Notes
- Models must NOT contain business logic (per layered architecture)
- Use SQLAlchemy 2.x ORM patterns
- ProductionPlanSnapshot.calculation_results is JSON blob for flexibility

---

## Subtasks & Detailed Guidance

### Subtask T001 - Add OutputMode enum

- **Purpose**: Define the enum for event requirement modes
- **Steps**:
  1. Open `src/models/event.py`
  2. Import `enum` module if not present
  3. Add OutputMode enum class before Event class:
     ```python
     class OutputMode(enum.Enum):
         BULK_COUNT = "bulk_count"   # Direct FinishedUnit quantities
         BUNDLED = "bundled"         # FinishedGood/bundle quantities
     ```
- **Files**: `src/models/event.py`
- **Notes**: Enum values are strings for database portability

### Subtask T002 - Add output_mode field to Event

- **Purpose**: Store the event's requirement input mode
- **Steps**:
  1. Import `Enum` from sqlalchemy if not present
  2. Add field to Event class after existing fields:
     ```python
     output_mode = Column(Enum(OutputMode), nullable=True, index=True)
     ```
  3. Nullable because existing events won't have a value
- **Files**: `src/models/event.py`
- **Notes**: Default to None; UI will prompt user to select mode before planning

### Subtask T003 - Create ProductionPlanSnapshot model

- **Purpose**: Persist calculated production plans for staleness detection
- **Steps**:
  1. Create new file `src/models/production_plan_snapshot.py`
  2. Import BaseModel from `src/models/base`
  3. Implement model per data-model.md schema:
     - `event_id` (FK to events.id, CASCADE delete)
     - `calculated_at` (DateTime, default=utc_now)
     - `input_hash` (String(64), nullable) - optional backup for staleness
     - `requirements_updated_at` (DateTime)
     - `recipes_updated_at` (DateTime)
     - `bundles_updated_at` (DateTime)
     - `calculation_results` (JSON)
     - `is_stale` (Boolean, default=False)
     - `stale_reason` (String(200), nullable)
     - `shopping_complete` (Boolean, default=False)
     - `shopping_completed_at` (DateTime, nullable)
  4. Add helper methods: `check_staleness()`, `mark_stale()`, `get_recipe_batches()`, `get_shopping_list()`
- **Files**: `src/models/production_plan_snapshot.py`
- **Notes**: JSON schema defined in data-model.md

### Subtask T004 - Add ProductionPlanSnapshot relationship to Event

- **Purpose**: Enable Event -> ProductionPlanSnapshot navigation
- **Steps**:
  1. In `src/models/event.py`, add relationship:
     ```python
     production_plan_snapshots = relationship(
         "ProductionPlanSnapshot",
         back_populates="event",
         cascade="all, delete-orphan"
     )
     ```
  2. Ensure back_populates matches relationship in ProductionPlanSnapshot
- **Files**: `src/models/event.py`
- **Notes**: Use cascade delete so plans are removed when event is deleted

### Subtask T005 - Export ProductionPlanSnapshot from __init__.py

- **Purpose**: Make new model accessible via standard import
- **Steps**:
  1. Open `src/models/__init__.py`
  2. Add import: `from .production_plan_snapshot import ProductionPlanSnapshot`
  3. Add to `__all__` list if present
  4. Also export `OutputMode` from event
- **Files**: `src/models/__init__.py`
- **Notes**: Follow existing export pattern in file

### Subtask T006 - Write unit tests for new model

- **Purpose**: Verify model behavior and JSON storage
- **Steps**:
  1. Create `src/tests/models/test_production_plan_snapshot.py`
  2. Test cases:
     - Create snapshot with valid calculation_results JSON
     - Verify JSON retrieval via `get_recipe_batches()` and `get_shopping_list()`
     - Test `mark_stale()` sets is_stale and stale_reason
     - Test cascade delete (delete event -> snapshot deleted)
     - Test Event.output_mode accepts enum values
  3. Use pytest fixtures for database session
- **Files**: `src/tests/models/test_production_plan_snapshot.py`
- **Notes**: Follow existing test patterns in `src/tests/models/`

---

## Test Strategy

**Unit Tests Required:**
- `src/tests/models/test_production_plan_snapshot.py`

**Run with:**
```bash
pytest src/tests/models/test_production_plan_snapshot.py -v
```

**Fixtures needed:**
- Database session with test database
- Sample Event for FK relationship

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Schema change breaks existing data | Use export/reset/import cycle; existing events have NULL output_mode |
| JSON blob unstructured | Define clear schema in data-model.md; validate in tests |
| Circular import | Import ProductionPlanSnapshot lazily if needed |

---

## Definition of Done Checklist

- [ ] OutputMode enum exists in event.py
- [ ] Event.output_mode field added and accessible
- [ ] ProductionPlanSnapshot model created with all fields
- [ ] Relationship between Event and ProductionPlanSnapshot works
- [ ] Models exported from __init__.py
- [ ] Unit tests pass with 100% coverage on new model
- [ ] `tasks.md` updated with status change

---

## Review Guidance

- Verify schema matches data-model.md exactly
- Check JSON structure follows defined schema
- Ensure proper cascade behavior on delete
- Validate nullable fields are correct

---

## Activity Log

> Append entries when the work package changes lanes.

- 2026-01-06T03:09:20Z - claude - lane=planned - Prompt created.
- 2026-01-06T12:53:06Z – claude – shell_pid=56331 – lane=doing – Started implementation
- 2026-01-06T12:57:57Z – claude – shell_pid=57515 – lane=for_review – Ready for review - all 20 tests pass
