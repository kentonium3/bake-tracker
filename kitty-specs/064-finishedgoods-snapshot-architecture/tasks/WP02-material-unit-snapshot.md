---
work_package_id: "WP02"
title: "MaterialUnitSnapshot Model + Service"
phase: "Phase 1 - Foundation"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
dependencies: []
subtasks:
  - "T006"
  - "T007"
  - "T008"
  - "T009"
  - "T010"
history:
  - timestamp: "2025-01-24T05:30:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP02 – MaterialUnitSnapshot Model + Service

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

Create the MaterialUnitSnapshot model and service primitive following the identical pattern as WP01:

- **MaterialUnitSnapshot model** with JSON Text column for definition_data
- **Service functions** for creating and querying snapshots
- **Unit tests** validating creation, retrieval, and data integrity

**Success Criteria**:
- [ ] MaterialUnitSnapshot model matches data-model.md specification exactly
- [ ] `create_material_unit_snapshot()` returns dict with snapshot id and definition_data
- [ ] Snapshot captures all MaterialUnit fields plus denormalized material name/category
- [ ] Session management follows wrapper/impl pattern
- [ ] Unit tests pass with >70% coverage of new code

## Context & Constraints

**Reference Documents**:
- `kitty-specs/064-finishedgoods-snapshot-architecture/data-model.md` - Entity definitions
- `kitty-specs/064-finishedgoods-snapshot-architecture/research.md` - Field mappings
- `src/models/recipe_snapshot.py` - Model pattern to copy
- `src/models/material_unit.py` - Source entity fields
- WP01 implementation - Identical pattern to follow

**Constraints**:
- Identical pattern to WP01 - different source entity (MaterialUnit vs FinishedUnit)
- Use `ondelete="RESTRICT"` for source FK
- Use `ondelete="CASCADE"` for context FKs
- Return dict from service functions, not ORM objects

**Implementation Command**:
```bash
spec-kitty implement WP02
```

**Parallel Execution**: WP02 can run in parallel with WP01 - no dependencies between them.

## Subtasks & Detailed Guidance

### Subtask T006 – Create MaterialUnitSnapshot model

**Purpose**: Define the SQLAlchemy model for immutable MaterialUnit definition snapshots.

**File**: `src/models/material_unit_snapshot.py`

**Steps**:

1. Create new file with module docstring:
   ```python
   """
   MaterialUnitSnapshot model for immutable capture of MaterialUnit definitions.

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
   class MaterialUnitSnapshot(BaseModel):
       __tablename__ = "material_unit_snapshots"

       # Source reference (RESTRICT: can't delete catalog item with snapshots)
       material_unit_id = Column(
           Integer,
           ForeignKey("material_units.id", ondelete="RESTRICT"),
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
       material_unit = relationship("MaterialUnit")
       planning_snapshot = relationship(
           "PlanningSnapshot",
           back_populates="material_unit_snapshots"
       )
   ```

5. Add table args with indexes:
   ```python
       __table_args__ = (
           Index("idx_mu_snapshot_unit", "material_unit_id"),
           Index("idx_mu_snapshot_planning", "planning_snapshot_id"),
           Index("idx_mu_snapshot_assembly", "assembly_run_id"),
           Index("idx_mu_snapshot_date", "snapshot_date"),
       )
   ```

6. Add helper methods:
   ```python
       def get_definition_data(self) -> dict:
           """Parse and return definition_data JSON."""
           return json.loads(self.definition_data) if self.definition_data else {}

       def __repr__(self) -> str:
           return f"MaterialUnitSnapshot(id={self.id}, material_unit_id={self.material_unit_id})"
   ```

**Validation**:
- [ ] All columns match data-model.md specification
- [ ] FK ondelete behaviors correct
- [ ] All indexes present

---

### Subtask T007 – Add to models `__init__.py`

**Purpose**: Export MaterialUnitSnapshot so it can be imported from `src.models`.

**File**: `src/models/__init__.py`

**Steps**:

1. Add import:
   ```python
   from .material_unit_snapshot import MaterialUnitSnapshot
   ```

2. Add to `__all__` list (if present):
   ```python
   __all__ = [
       # ... existing exports
       "MaterialUnitSnapshot",
   ]
   ```

**Parallel?**: Yes - can run alongside T006 once file exists

---

### Subtask T008 – Create `create_material_unit_snapshot()` service function

**Purpose**: Implement the snapshot creation primitive.

**File**: `src/services/material_unit_service.py`

**Steps**:

1. Add imports at top of file:
   ```python
   import json
   from sqlalchemy.orm import Session
   from sqlalchemy.exc import SQLAlchemyError
   from src.models import MaterialUnitSnapshot
   ```

2. Add custom exception (or import from shared location):
   ```python
   class SnapshotCreationError(Exception):
       """Raised when snapshot creation fails."""
       pass
   ```

3. Add public wrapper function:
   ```python
   def create_material_unit_snapshot(
       material_unit_id: int,
       planning_snapshot_id: int = None,
       assembly_run_id: int = None,
       session: Session = None
   ) -> dict:
       """
       Create immutable snapshot of MaterialUnit definition.

       Args:
           material_unit_id: Source MaterialUnit ID
           planning_snapshot_id: Optional planning context
           assembly_run_id: Optional assembly context
           session: Optional session for transaction sharing

       Returns:
           dict with snapshot id and definition_data

       Raises:
           SnapshotCreationError: If MaterialUnit not found or creation fails
       """
       if session is not None:
           return _create_material_unit_snapshot_impl(
               material_unit_id, planning_snapshot_id, assembly_run_id, session
           )

       try:
           with session_scope() as session:
               return _create_material_unit_snapshot_impl(
                   material_unit_id, planning_snapshot_id, assembly_run_id, session
               )
       except SQLAlchemyError as e:
           raise SnapshotCreationError(f"Database error creating snapshot: {e}")
   ```

4. Add private implementation:
   ```python
   def _create_material_unit_snapshot_impl(
       material_unit_id: int,
       planning_snapshot_id: int,
       assembly_run_id: int,
       session: Session
   ) -> dict:
       """Internal implementation of snapshot creation."""
       from src.models import MaterialUnit

       # Load MaterialUnit with material relationship
       mu = session.query(MaterialUnit).filter_by(id=material_unit_id).first()
       if not mu:
           raise SnapshotCreationError(f"MaterialUnit {material_unit_id} not found")

       # Eagerly load material for denormalization
       material = mu.material

       # Build definition_data JSON
       definition_data = {
           "slug": mu.slug,
           "name": mu.name,
           "description": mu.description,
           "material_id": mu.material_id,
           "material_name": material.name if material else None,
           "material_category": material.category if material else None,
           "quantity_per_unit": mu.quantity_per_unit,
       }

       # Create snapshot
       snapshot = MaterialUnitSnapshot(
           material_unit_id=material_unit_id,
           planning_snapshot_id=planning_snapshot_id,
           assembly_run_id=assembly_run_id,
           definition_data=json.dumps(definition_data),
           is_backfilled=False,
       )

       session.add(snapshot)
       session.flush()  # Get ID without committing

       return {
           "id": snapshot.id,
           "material_unit_id": snapshot.material_unit_id,
           "planning_snapshot_id": snapshot.planning_snapshot_id,
           "assembly_run_id": snapshot.assembly_run_id,
           "snapshot_date": snapshot.snapshot_date.isoformat(),
           "definition_data": definition_data,
           "is_backfilled": snapshot.is_backfilled,
       }
   ```

**Validation**:
- [ ] Wrapper/impl pattern matches WP01
- [ ] Returns dict, not ORM object
- [ ] definition_data captures all fields from data-model.md

---

### Subtask T009 – Add query functions

**Purpose**: Implement snapshot retrieval functions.

**File**: `src/services/material_unit_service.py`

**Steps**:

1. Add `get_material_unit_snapshot()`:
   ```python
   def get_material_unit_snapshot(
       snapshot_id: int,
       session: Session = None
   ) -> dict | None:
       """
       Get a MaterialUnitSnapshot by its ID.

       Args:
           snapshot_id: Snapshot ID
           session: Optional session

       Returns:
           Snapshot dict or None if not found
       """
       if session is not None:
           return _get_material_unit_snapshot_impl(snapshot_id, session)

       with session_scope() as session:
           return _get_material_unit_snapshot_impl(snapshot_id, session)

   def _get_material_unit_snapshot_impl(
       snapshot_id: int,
       session: Session
   ) -> dict | None:
       snapshot = session.query(MaterialUnitSnapshot).filter_by(id=snapshot_id).first()

       if not snapshot:
           return None

       return {
           "id": snapshot.id,
           "material_unit_id": snapshot.material_unit_id,
           "planning_snapshot_id": snapshot.planning_snapshot_id,
           "assembly_run_id": snapshot.assembly_run_id,
           "snapshot_date": snapshot.snapshot_date.isoformat(),
           "definition_data": snapshot.get_definition_data(),
           "is_backfilled": snapshot.is_backfilled,
       }
   ```

2. Add `get_material_unit_snapshots_by_planning_id()`:
   ```python
   def get_material_unit_snapshots_by_planning_id(
       planning_snapshot_id: int,
       session: Session = None
   ) -> list[dict]:
       """
       Get all MaterialUnitSnapshots for a planning snapshot.

       Args:
           planning_snapshot_id: PlanningSnapshot ID
           session: Optional session

       Returns:
           List of snapshot dicts
       """
       if session is not None:
           return _get_mu_snapshots_by_planning_impl(planning_snapshot_id, session)

       with session_scope() as session:
           return _get_mu_snapshots_by_planning_impl(planning_snapshot_id, session)

   def _get_mu_snapshots_by_planning_impl(
       planning_snapshot_id: int,
       session: Session
   ) -> list[dict]:
       snapshots = (
           session.query(MaterialUnitSnapshot)
           .filter_by(planning_snapshot_id=planning_snapshot_id)
           .order_by(MaterialUnitSnapshot.snapshot_date.desc())
           .all()
       )

       return [
           {
               "id": s.id,
               "material_unit_id": s.material_unit_id,
               "planning_snapshot_id": s.planning_snapshot_id,
               "snapshot_date": s.snapshot_date.isoformat(),
               "definition_data": s.get_definition_data(),
               "is_backfilled": s.is_backfilled,
           }
           for s in snapshots
       ]
   ```

---

### Subtask T010 – Create unit tests

**Purpose**: Validate snapshot creation, retrieval, and edge cases.

**File**: `src/tests/test_material_unit_snapshot.py`

**Steps**:

1. Create test file with fixtures:
   ```python
   """Tests for MaterialUnitSnapshot model and service functions."""
   import pytest
   from src.models import Material, MaterialUnit, MaterialUnitSnapshot
   from src.services.material_unit_service import (
       create_material_unit_snapshot,
       get_material_unit_snapshot,
       get_material_unit_snapshots_by_planning_id,
       SnapshotCreationError,
   )


   @pytest.fixture
   def sample_material(db_session):
       """Create a test material."""
       material = Material(
           name="Red Satin Ribbon",
           category="Ribbons",
           base_unit="inch",
       )
       db_session.add(material)
       db_session.flush()
       return material


   @pytest.fixture
   def sample_material_unit(db_session, sample_material):
       """Create a test MaterialUnit."""
       mu = MaterialUnit(
           slug="6-inch-red-ribbon",
           name="6-inch Red Ribbon",
           material_id=sample_material.id,
           quantity_per_unit=6.0,
       )
       db_session.add(mu)
       db_session.flush()
       return mu
   ```

2. Add test cases:
   ```python
   class TestCreateMaterialUnitSnapshot:
       """Tests for create_material_unit_snapshot()."""

       def test_creates_snapshot_with_all_fields(self, db_session, sample_material_unit):
           """Snapshot captures all MaterialUnit fields."""
           result = create_material_unit_snapshot(
               material_unit_id=sample_material_unit.id,
               session=db_session
           )

           assert result["id"] is not None
           assert result["material_unit_id"] == sample_material_unit.id
           assert result["definition_data"]["slug"] == "6-inch-red-ribbon"
           assert result["definition_data"]["name"] == "6-inch Red Ribbon"
           assert result["definition_data"]["material_name"] == "Red Satin Ribbon"
           assert result["definition_data"]["quantity_per_unit"] == 6.0

       def test_raises_error_for_invalid_id(self, db_session):
           """Raises SnapshotCreationError for non-existent MaterialUnit."""
           with pytest.raises(SnapshotCreationError):
               create_material_unit_snapshot(
                   material_unit_id=99999,
                   session=db_session
               )


   class TestGetMaterialUnitSnapshot:
       """Tests for get_material_unit_snapshot()."""

       def test_returns_snapshot_by_id(self, db_session, sample_material_unit):
           """Can retrieve snapshot by ID."""
           created = create_material_unit_snapshot(
               material_unit_id=sample_material_unit.id,
               session=db_session
           )

           result = get_material_unit_snapshot(created["id"], session=db_session)

           assert result is not None
           assert result["id"] == created["id"]
           assert result["definition_data"]["slug"] == "6-inch-red-ribbon"

       def test_returns_none_for_invalid_id(self, db_session):
           """Returns None for non-existent snapshot."""
           result = get_material_unit_snapshot(99999, session=db_session)
           assert result is None
   ```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| MaterialUnit model structure unknown | Read src/models/material_unit.py before implementing |
| Material relationship missing | Verify MaterialUnit has material relationship |
| Field name mismatches | Cross-reference data-model.md carefully |

## Definition of Done Checklist

- [ ] T006: MaterialUnitSnapshot model created with all columns, indexes
- [ ] T007: Model exported from src/models/__init__.py
- [ ] T008: create_material_unit_snapshot() implemented
- [ ] T009: Query functions implemented
- [ ] T010: Unit tests pass
- [ ] All columns match data-model.md exactly
- [ ] Service functions return dict, not ORM object
- [ ] `tasks.md` updated with status change

## Review Guidance

**Reviewer Checklist**:
- [ ] Model columns match data-model.md specification
- [ ] FK ondelete behaviors correct
- [ ] Service functions follow wrapper/impl session pattern
- [ ] definition_data JSON includes all required fields
- [ ] Tests cover creation, retrieval, and error cases

## Activity Log

- 2025-01-24T05:30:00Z – system – lane=planned – Prompt generated via /spec-kitty.tasks
