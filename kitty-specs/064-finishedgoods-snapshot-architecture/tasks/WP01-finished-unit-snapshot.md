---
work_package_id: "WP01"
title: "FinishedUnitSnapshot Model + Service"
phase: "Phase 1 - Foundation"
lane: "doing"
assignee: ""
agent: "claude-opus"
shell_pid: "47917"
review_status: ""
reviewed_by: ""
dependencies: []
subtasks:
  - "T001"
  - "T002"
  - "T003"
  - "T004"
  - "T005"
history:
  - timestamp: "2025-01-24T05:30:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 – FinishedUnitSnapshot Model + Service

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you understand the feedback, update `review_status: acknowledged` in the frontmatter.

---

## Review Feedback

> **Populated by `/spec-kitty.review`** – Reviewers add detailed feedback here when work needs changes.

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

Create the FinishedUnitSnapshot model and service primitive following the RecipeSnapshot pattern exactly:

- **FinishedUnitSnapshot model** with JSON Text column for definition_data
- **Service functions** for creating and querying snapshots
- **Unit tests** validating creation, retrieval, and data integrity

**Success Criteria**:
- [ ] FinishedUnitSnapshot model matches data-model.md specification exactly
- [ ] `create_finished_unit_snapshot()` returns dict with snapshot id and definition_data
- [ ] Snapshot captures all FinishedUnit fields plus denormalized recipe name/category
- [ ] Session management follows wrapper/impl pattern (accepts optional session parameter)
- [ ] Unit tests pass with >70% coverage of new code

## Context & Constraints

**Reference Documents**:
- `kitty-specs/064-finishedgoods-snapshot-architecture/data-model.md` - Entity definitions
- `kitty-specs/064-finishedgoods-snapshot-architecture/research.md` - Field mappings
- `src/models/recipe_snapshot.py` - Model pattern to copy
- `src/services/recipe_snapshot_service.py` - Service pattern to copy
- `src/models/finished_unit.py` - Source entity fields

**Constraints**:
- Follow RecipeSnapshot pattern exactly for consistency
- Use `ondelete="RESTRICT"` for source FK (can't delete FinishedUnit with snapshots)
- Use `ondelete="CASCADE"` for context FKs (planning_snapshot_id, assembly_run_id)
- Return dict from service functions, not ORM objects
- Use `session.flush()` to get ID without committing (caller controls commit)

**Implementation Command**:
```bash
spec-kitty implement WP01
```

## Subtasks & Detailed Guidance

### Subtask T001 – Create FinishedUnitSnapshot model

**Purpose**: Define the SQLAlchemy model for immutable FinishedUnit definition snapshots.

**File**: `src/models/finished_unit_snapshot.py`

**Steps**:

1. Create new file with module docstring:
   ```python
   """
   FinishedUnitSnapshot model for immutable capture of FinishedUnit definitions.

   Follows RecipeSnapshot pattern: JSON Text column stores denormalized definition data,
   dual context FKs support both planning and assembly use cases.
   """
   ```

2. Add imports:
   ```python
   import json
   from sqlalchemy import (
       Column, Integer, Text, DateTime, Boolean, ForeignKey, Index
   )
   from sqlalchemy.orm import relationship
   from .base import BaseModel
   from src.utils.datetime_utils import utc_now
   ```

3. Define model class with columns:
   ```python
   class FinishedUnitSnapshot(BaseModel):
       __tablename__ = "finished_unit_snapshots"

       # Source reference (RESTRICT: can't delete catalog item with snapshots)
       finished_unit_id = Column(
           Integer,
           ForeignKey("finished_units.id", ondelete="RESTRICT"),
           nullable=False,
           index=True
       )

       # Context linkage (exactly one should be set at service layer)
       planning_snapshot_id = Column(
           Integer,
           ForeignKey("planning_snapshots.id", ondelete="CASCADE"),
           nullable=True,
           index=True
       )
       assembly_run_id = Column(
           Integer,
           ForeignKey("assembly_runs.id", ondelete="CASCADE"),
           nullable=True,
           index=True
       )

       # Snapshot metadata
       snapshot_date = Column(DateTime, nullable=False, default=utc_now)
       is_backfilled = Column(Boolean, nullable=False, default=False)

       # Denormalized definition data (JSON)
       definition_data = Column(Text, nullable=False)
   ```

4. Add relationships:
   ```python
       # Relationships
       finished_unit = relationship("FinishedUnit")
       planning_snapshot = relationship(
           "PlanningSnapshot",
           back_populates="finished_unit_snapshots"
       )
   ```

5. Add table args with indexes:
   ```python
       __table_args__ = (
           Index("idx_fu_snapshot_unit", "finished_unit_id"),
           Index("idx_fu_snapshot_planning", "planning_snapshot_id"),
           Index("idx_fu_snapshot_assembly", "assembly_run_id"),
           Index("idx_fu_snapshot_date", "snapshot_date"),
       )
   ```

6. Add helper methods:
   ```python
       def get_definition_data(self) -> dict:
           """Parse and return definition_data JSON."""
           return json.loads(self.definition_data) if self.definition_data else {}

       def __repr__(self) -> str:
           return f"FinishedUnitSnapshot(id={self.id}, finished_unit_id={self.finished_unit_id})"
   ```

**Validation**:
- [ ] All columns match data-model.md specification
- [ ] FK ondelete behaviors correct (RESTRICT for source, CASCADE for context)
- [ ] All indexes present

---

### Subtask T002 – Add to models `__init__.py`

**Purpose**: Export FinishedUnitSnapshot so it can be imported from `src.models`.

**File**: `src/models/__init__.py`

**Steps**:

1. Add import:
   ```python
   from .finished_unit_snapshot import FinishedUnitSnapshot
   ```

2. Add to `__all__` list (if present):
   ```python
   __all__ = [
       # ... existing exports
       "FinishedUnitSnapshot",
   ]
   ```

3. Verify import works:
   ```python
   from src.models import FinishedUnitSnapshot
   ```

**Parallel?**: Yes - can run alongside T001 once file exists

---

### Subtask T003 – Create `create_finished_unit_snapshot()` service function

**Purpose**: Implement the snapshot creation primitive following recipe_snapshot_service pattern.

**File**: `src/services/finished_unit_service.py`

**Steps**:

1. Add imports at top of file:
   ```python
   import json
   from sqlalchemy.orm import Session
   from sqlalchemy.exc import SQLAlchemyError
   from src.models import FinishedUnitSnapshot
   ```

2. Add custom exception (or import from shared location):
   ```python
   class SnapshotCreationError(Exception):
       """Raised when snapshot creation fails."""
       pass
   ```

3. Add public wrapper function:
   ```python
   def create_finished_unit_snapshot(
       finished_unit_id: int,
       planning_snapshot_id: int = None,
       assembly_run_id: int = None,
       session: Session = None
   ) -> dict:
       """
       Create immutable snapshot of FinishedUnit definition.

       Args:
           finished_unit_id: Source FinishedUnit ID
           planning_snapshot_id: Optional planning context
           assembly_run_id: Optional assembly context
           session: Optional session for transaction sharing

       Returns:
           dict with snapshot id and definition_data

       Raises:
           SnapshotCreationError: If FinishedUnit not found or creation fails
       """
       if session is not None:
           return _create_finished_unit_snapshot_impl(
               finished_unit_id, planning_snapshot_id, assembly_run_id, session
           )

       try:
           with session_scope() as session:
               return _create_finished_unit_snapshot_impl(
                   finished_unit_id, planning_snapshot_id, assembly_run_id, session
               )
       except SQLAlchemyError as e:
           raise SnapshotCreationError(f"Database error creating snapshot: {e}")
   ```

4. Add private implementation:
   ```python
   def _create_finished_unit_snapshot_impl(
       finished_unit_id: int,
       planning_snapshot_id: int,
       assembly_run_id: int,
       session: Session
   ) -> dict:
       """Internal implementation of snapshot creation."""
       from src.models import FinishedUnit

       # Load FinishedUnit with recipe relationship
       fu = session.query(FinishedUnit).filter_by(id=finished_unit_id).first()
       if not fu:
           raise SnapshotCreationError(f"FinishedUnit {finished_unit_id} not found")

       # Eagerly load recipe for denormalization
       recipe = fu.recipe

       # Build definition_data JSON
       definition_data = {
           "slug": fu.slug,
           "display_name": fu.display_name,
           "description": fu.description,
           "recipe_id": fu.recipe_id,
           "recipe_name": recipe.name if recipe else None,
           "recipe_category": recipe.category if recipe else None,
           "yield_mode": fu.yield_mode.value if fu.yield_mode else None,
           "items_per_batch": fu.items_per_batch,
           "item_unit": fu.item_unit,
           "batch_percentage": float(fu.batch_percentage) if fu.batch_percentage else None,
           "portion_description": fu.portion_description,
           "category": fu.category,
           "production_notes": fu.production_notes,
           "notes": fu.notes,
       }

       # Create snapshot
       snapshot = FinishedUnitSnapshot(
           finished_unit_id=finished_unit_id,
           planning_snapshot_id=planning_snapshot_id,
           assembly_run_id=assembly_run_id,
           definition_data=json.dumps(definition_data),
           is_backfilled=False,
       )

       session.add(snapshot)
       session.flush()  # Get ID without committing

       return {
           "id": snapshot.id,
           "finished_unit_id": snapshot.finished_unit_id,
           "planning_snapshot_id": snapshot.planning_snapshot_id,
           "assembly_run_id": snapshot.assembly_run_id,
           "snapshot_date": snapshot.snapshot_date.isoformat(),
           "definition_data": definition_data,
           "is_backfilled": snapshot.is_backfilled,
       }
   ```

**Validation**:
- [ ] Wrapper/impl pattern matches recipe_snapshot_service.py
- [ ] Returns dict, not ORM object
- [ ] Session parameter enables transaction sharing
- [ ] definition_data captures all fields from data-model.md

---

### Subtask T004 – Add query functions

**Purpose**: Implement snapshot retrieval functions.

**File**: `src/services/finished_unit_service.py`

**Steps**:

1. Add `get_finished_unit_snapshot()`:
   ```python
   def get_finished_unit_snapshot(
       snapshot_id: int,
       session: Session = None
   ) -> dict | None:
       """
       Get a FinishedUnitSnapshot by its ID.

       Args:
           snapshot_id: Snapshot ID
           session: Optional session

       Returns:
           Snapshot dict or None if not found
       """
       if session is not None:
           return _get_finished_unit_snapshot_impl(snapshot_id, session)

       with session_scope() as session:
           return _get_finished_unit_snapshot_impl(snapshot_id, session)

   def _get_finished_unit_snapshot_impl(
       snapshot_id: int,
       session: Session
   ) -> dict | None:
       snapshot = session.query(FinishedUnitSnapshot).filter_by(id=snapshot_id).first()

       if not snapshot:
           return None

       return {
           "id": snapshot.id,
           "finished_unit_id": snapshot.finished_unit_id,
           "planning_snapshot_id": snapshot.planning_snapshot_id,
           "assembly_run_id": snapshot.assembly_run_id,
           "snapshot_date": snapshot.snapshot_date.isoformat(),
           "definition_data": snapshot.get_definition_data(),
           "is_backfilled": snapshot.is_backfilled,
       }
   ```

2. Add `get_finished_unit_snapshots_by_planning_id()`:
   ```python
   def get_finished_unit_snapshots_by_planning_id(
       planning_snapshot_id: int,
       session: Session = None
   ) -> list[dict]:
       """
       Get all FinishedUnitSnapshots for a planning snapshot.

       Args:
           planning_snapshot_id: PlanningSnapshot ID
           session: Optional session

       Returns:
           List of snapshot dicts
       """
       if session is not None:
           return _get_fu_snapshots_by_planning_impl(planning_snapshot_id, session)

       with session_scope() as session:
           return _get_fu_snapshots_by_planning_impl(planning_snapshot_id, session)

   def _get_fu_snapshots_by_planning_impl(
       planning_snapshot_id: int,
       session: Session
   ) -> list[dict]:
       snapshots = (
           session.query(FinishedUnitSnapshot)
           .filter_by(planning_snapshot_id=planning_snapshot_id)
           .order_by(FinishedUnitSnapshot.snapshot_date.desc())
           .all()
       )

       return [
           {
               "id": s.id,
               "finished_unit_id": s.finished_unit_id,
               "planning_snapshot_id": s.planning_snapshot_id,
               "snapshot_date": s.snapshot_date.isoformat(),
               "definition_data": s.get_definition_data(),
               "is_backfilled": s.is_backfilled,
           }
           for s in snapshots
       ]
   ```

**Validation**:
- [ ] Both functions follow wrapper/impl pattern
- [ ] Returns None/empty list appropriately for not-found cases

---

### Subtask T005 – Create unit tests

**Purpose**: Validate snapshot creation, retrieval, and edge cases.

**File**: `src/tests/test_finished_unit_snapshot.py`

**Steps**:

1. Create test file with fixtures:
   ```python
   """Tests for FinishedUnitSnapshot model and service functions."""
   import pytest
   from src.models import FinishedUnit, FinishedUnitSnapshot, Recipe
   from src.services.finished_unit_service import (
       create_finished_unit_snapshot,
       get_finished_unit_snapshot,
       get_finished_unit_snapshots_by_planning_id,
       SnapshotCreationError,
   )
   from src.services.database import session_scope


   @pytest.fixture
   def sample_recipe(db_session):
       """Create a test recipe."""
       recipe = Recipe(
           name="Test Cookie Recipe",
           category="Cookies",
           source="Test",
       )
       db_session.add(recipe)
       db_session.flush()
       return recipe


   @pytest.fixture
   def sample_finished_unit(db_session, sample_recipe):
       """Create a test FinishedUnit."""
       from src.models.finished_unit import YieldMode
       fu = FinishedUnit(
           slug="test-cookie",
           display_name="Test Cookie",
           recipe_id=sample_recipe.id,
           yield_mode=YieldMode.DISCRETE_COUNT,
           items_per_batch=24,
           item_unit="cookie",
       )
       db_session.add(fu)
       db_session.flush()
       return fu
   ```

2. Add test cases:
   ```python
   class TestCreateFinishedUnitSnapshot:
       """Tests for create_finished_unit_snapshot()."""

       def test_creates_snapshot_with_all_fields(self, db_session, sample_finished_unit):
           """Snapshot captures all FinishedUnit fields."""
           result = create_finished_unit_snapshot(
               finished_unit_id=sample_finished_unit.id,
               session=db_session
           )

           assert result["id"] is not None
           assert result["finished_unit_id"] == sample_finished_unit.id
           assert result["definition_data"]["slug"] == "test-cookie"
           assert result["definition_data"]["display_name"] == "Test Cookie"
           assert result["definition_data"]["recipe_name"] == "Test Cookie Recipe"
           assert result["definition_data"]["yield_mode"] == "discrete_count"

       def test_raises_error_for_invalid_id(self, db_session):
           """Raises SnapshotCreationError for non-existent FinishedUnit."""
           with pytest.raises(SnapshotCreationError):
               create_finished_unit_snapshot(
                   finished_unit_id=99999,
                   session=db_session
               )

       def test_accepts_planning_snapshot_id(self, db_session, sample_finished_unit):
           """Snapshot can be linked to planning context."""
           # Would need PlanningSnapshot fixture in WP04
           result = create_finished_unit_snapshot(
               finished_unit_id=sample_finished_unit.id,
               planning_snapshot_id=None,  # Test nullable context
               session=db_session
           )
           assert result["planning_snapshot_id"] is None


   class TestGetFinishedUnitSnapshot:
       """Tests for get_finished_unit_snapshot()."""

       def test_returns_snapshot_by_id(self, db_session, sample_finished_unit):
           """Can retrieve snapshot by ID."""
           created = create_finished_unit_snapshot(
               finished_unit_id=sample_finished_unit.id,
               session=db_session
           )

           result = get_finished_unit_snapshot(created["id"], session=db_session)

           assert result is not None
           assert result["id"] == created["id"]
           assert result["definition_data"]["slug"] == "test-cookie"

       def test_returns_none_for_invalid_id(self, db_session):
           """Returns None for non-existent snapshot."""
           result = get_finished_unit_snapshot(99999, session=db_session)
           assert result is None
   ```

**Validation**:
- [ ] Tests cover happy path for create/get
- [ ] Tests cover error cases (invalid ID)
- [ ] Tests verify definition_data structure

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Schema mismatch with data-model.md | Cross-reference every column before commit |
| Session management issues | Copy wrapper/impl exactly from recipe_snapshot_service.py |
| Missing relationship back_populates | PlanningSnapshot relationship added in WP04 |
| Import order issues | Use string references for forward-declared relationships |

## Definition of Done Checklist

- [ ] T001: FinishedUnitSnapshot model created with all columns, indexes
- [ ] T002: Model exported from src/models/__init__.py
- [ ] T003: create_finished_unit_snapshot() implemented with wrapper/impl pattern
- [ ] T004: Query functions implemented
- [ ] T005: Unit tests pass
- [ ] All columns match data-model.md exactly
- [ ] Service functions return dict, not ORM object
- [ ] `tasks.md` updated with status change

## Review Guidance

**Reviewer Checklist**:
- [ ] Model columns match data-model.md specification
- [ ] FK ondelete behaviors correct (RESTRICT for source, CASCADE for context)
- [ ] Service functions follow wrapper/impl session pattern
- [ ] definition_data JSON includes all required fields
- [ ] Tests cover creation, retrieval, and error cases
- [ ] No circular import issues

## Activity Log

- 2025-01-24T05:30:00Z – system – lane=planned – Prompt generated via /spec-kitty.tasks
- 2026-01-24T17:08:00Z – claude-opus – shell_pid=47917 – lane=doing – Started implementation via workflow command
