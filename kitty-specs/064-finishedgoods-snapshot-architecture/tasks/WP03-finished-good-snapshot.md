---
work_package_id: WP03
title: FinishedGoodSnapshot Model + Service
lane: "done"
dependencies:
- WP01
subtasks:
- T011
- T012
- T013
- T014
- T015
- T016
- T017
- T018
phase: Phase 2 - Core Logic
assignee: ''
agent: "claude-opus"
shell_pid: "58308"
review_status: "approved"
reviewed_by: "Kent Gale"
history:
- timestamp: '2025-01-24T05:30:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP03 – FinishedGoodSnapshot Model + Service

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

Create the FinishedGoodSnapshot model and recursive snapshot service with circular reference detection:

- **FinishedGoodSnapshot model** with JSON Text column for definition_data (includes components)
- **Recursive snapshot creation** that orchestrates WP01 and WP02 primitives for components
- **Circular reference detection** using visited_ids set tracking
- **Max depth enforcement** (10 levels)
- **Unit tests** including edge cases for circular references and deep nesting

**Success Criteria**:
- [ ] FinishedGoodSnapshot model matches data-model.md specification
- [ ] `create_finished_good_snapshot()` recursively creates snapshots for all component types
- [ ] Circular references raise `CircularReferenceError` with descriptive message
- [ ] Nesting >10 levels raises `MaxDepthExceededError`
- [ ] All component snapshots created in single transaction (atomicity)
- [ ] Performance: <5 seconds for FinishedGood with 50 components

## Context & Constraints

**Reference Documents**:
- `kitty-specs/064-finishedgoods-snapshot-architecture/data-model.md` - Entity definitions
- `kitty-specs/064-finishedgoods-snapshot-architecture/research.md` - Circular reference approach
- `src/models/finished_good.py` - Source entity with components relationship
- `src/models/composition.py` - Polymorphic component references

**Dependencies**:
- **WP01**: `create_finished_unit_snapshot()` must be available
- **WP02**: `create_material_unit_snapshot()` must be available

**Component Type Handling** (from Composition model):
- `finished_unit_id` → call `create_finished_unit_snapshot()`, store snapshot_id
- `finished_good_id` → recurse `create_finished_good_snapshot()`, store snapshot_id
- `material_unit_id` → call `create_material_unit_snapshot()`, store snapshot_id
- `material_id` (is_generic=True) → store placeholder data, snapshot_id=null
- `packaging_product_id` → skip (out of scope per spec)

**Implementation Command**:
```bash
spec-kitty implement WP03 --base WP02
```
(Note: Assumes WP01 and WP02 are both merged. Use the latest merged WP as base.)

## Subtasks & Detailed Guidance

### Subtask T011 – Create FinishedGoodSnapshot model

**Purpose**: Define the SQLAlchemy model for immutable FinishedGood definition snapshots.

**File**: `src/models/finished_good_snapshot.py`

**Steps**:

1. Create new file with module docstring:
   ```python
   """
   FinishedGoodSnapshot model for immutable capture of FinishedGood definitions.

   Includes full component hierarchy in definition_data JSON. Component snapshots
   are created recursively and their IDs stored in the components array.
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
   class FinishedGoodSnapshot(BaseModel):
       __tablename__ = "finished_good_snapshots"

       # Source reference (RESTRICT: can't delete catalog item with snapshots)
       finished_good_id = Column(
           Integer,
           ForeignKey("finished_goods.id", ondelete="RESTRICT"),
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

       # Denormalized definition data (JSON) - includes components array
       definition_data = Column(Text, nullable=False)

       # Relationships
       finished_good = relationship("FinishedGood")
       planning_snapshot = relationship(
           "PlanningSnapshot",
           back_populates="finished_good_snapshots"
       )

       __table_args__ = (
           Index("idx_fg_snapshot_good", "finished_good_id"),
           Index("idx_fg_snapshot_planning", "planning_snapshot_id"),
           Index("idx_fg_snapshot_assembly", "assembly_run_id"),
           Index("idx_fg_snapshot_date", "snapshot_date"),
       )

       def get_definition_data(self) -> dict:
           """Parse and return definition_data JSON."""
           return json.loads(self.definition_data) if self.definition_data else {}

       def __repr__(self) -> str:
           return f"FinishedGoodSnapshot(id={self.id}, finished_good_id={self.finished_good_id})"
   ```

**Validation**:
- [ ] All columns match data-model.md specification
- [ ] FK ondelete behaviors correct
- [ ] All indexes present

---

### Subtask T012 – Add to models `__init__.py`

**Purpose**: Export FinishedGoodSnapshot so it can be imported from `src.models`.

**File**: `src/models/__init__.py`

**Steps**:

1. Add import:
   ```python
   from .finished_good_snapshot import FinishedGoodSnapshot
   ```

2. Add to `__all__` list (if present)

**Parallel?**: Yes - can run alongside T011

---

### Subtask T013 – Create custom exception classes

**Purpose**: Define exceptions for circular reference and max depth errors.

**File**: `src/services/finished_good_service.py` (or `src/services/exceptions.py` if exists)

**Steps**:

1. Add exception classes:
   ```python
   class SnapshotCreationError(Exception):
       """Raised when snapshot creation fails."""
       pass


   class CircularReferenceError(Exception):
       """Raised when circular reference detected in FinishedGood hierarchy.

       Attributes:
           finished_good_id: The ID that caused the circular reference
           path: List of IDs showing the reference chain
       """
       def __init__(self, finished_good_id: int, path: list[int]):
           self.finished_good_id = finished_good_id
           self.path = path
           path_str = " -> ".join(str(id) for id in path)
           super().__init__(
               f"Circular reference detected: FinishedGood {finished_good_id} "
               f"already in hierarchy path: {path_str}"
           )


   class MaxDepthExceededError(Exception):
       """Raised when FinishedGood nesting exceeds maximum depth.

       Attributes:
           depth: Current depth when limit was hit
           max_depth: The configured maximum depth (10)
       """
       def __init__(self, depth: int, max_depth: int = 10):
           self.depth = depth
           self.max_depth = max_depth
           super().__init__(
               f"Maximum nesting depth exceeded: {depth} levels "
               f"(max: {max_depth})"
           )
   ```

**Parallel?**: Yes - can run alongside T011, T012

---

### Subtask T014 – Implement `create_finished_good_snapshot()` with recursive logic

**Purpose**: Create the main snapshot function that orchestrates component snapshot creation.

**File**: `src/services/finished_good_service.py`

**Steps**:

1. Add imports:
   ```python
   import json
   from typing import Optional
   from sqlalchemy.orm import Session
   from sqlalchemy.exc import SQLAlchemyError
   from src.models import FinishedGood, FinishedGoodSnapshot
   from src.services.finished_unit_service import create_finished_unit_snapshot
   from src.services.material_unit_service import create_material_unit_snapshot
   ```

2. Add public wrapper function:
   ```python
   MAX_NESTING_DEPTH = 10


   def create_finished_good_snapshot(
       finished_good_id: int,
       planning_snapshot_id: int = None,
       assembly_run_id: int = None,
       session: Session = None,
       _visited_ids: set[int] = None,
       _depth: int = 0
   ) -> dict:
       """
       Create immutable snapshot of FinishedGood definition with all components.

       Recursively creates snapshots for all FinishedUnit, MaterialUnit,
       and nested FinishedGood components. All snapshots are created in the
       same transaction for atomicity.

       Args:
           finished_good_id: Source FinishedGood ID
           planning_snapshot_id: Optional planning context
           assembly_run_id: Optional assembly context
           session: Optional session for transaction sharing
           _visited_ids: Internal - tracked IDs for circular reference detection
           _depth: Internal - current recursion depth

       Returns:
           dict with snapshot id and definition_data (including component snapshot IDs)

       Raises:
           SnapshotCreationError: If FinishedGood not found or creation fails
           CircularReferenceError: If circular reference detected in hierarchy
           MaxDepthExceededError: If nesting depth exceeds 10 levels
       """
       # Initialize visited set for top-level call
       if _visited_ids is None:
           _visited_ids = set()

       if session is not None:
           return _create_finished_good_snapshot_impl(
               finished_good_id, planning_snapshot_id, assembly_run_id,
               session, _visited_ids, _depth
           )

       try:
           with session_scope() as session:
               return _create_finished_good_snapshot_impl(
                   finished_good_id, planning_snapshot_id, assembly_run_id,
                   session, _visited_ids, _depth
               )
       except SQLAlchemyError as e:
           raise SnapshotCreationError(f"Database error creating snapshot: {e}")
   ```

3. Add private implementation:
   ```python
   def _create_finished_good_snapshot_impl(
       finished_good_id: int,
       planning_snapshot_id: int,
       assembly_run_id: int,
       session: Session,
       visited_ids: set[int],
       depth: int
   ) -> dict:
       """Internal implementation of snapshot creation."""

       # Check max depth FIRST
       if depth > MAX_NESTING_DEPTH:
           raise MaxDepthExceededError(depth, MAX_NESTING_DEPTH)

       # Check circular reference
       if finished_good_id in visited_ids:
           raise CircularReferenceError(
               finished_good_id,
               list(visited_ids) + [finished_good_id]
           )

       # Add to visited set BEFORE processing components
       visited_ids.add(finished_good_id)

       # Load FinishedGood with components
       fg = (
           session.query(FinishedGood)
           .filter_by(id=finished_good_id)
           .first()
       )
       if not fg:
           raise SnapshotCreationError(f"FinishedGood {finished_good_id} not found")

       # Process components and create snapshots
       components_data = []
       for composition in fg.components:
           component_data = _snapshot_component(
               composition,
               planning_snapshot_id,
               assembly_run_id,
               session,
               visited_ids,
               depth
           )
           if component_data:  # Skip packaging_product (returns None)
               components_data.append(component_data)

       # Sort components by sort_order
       components_data.sort(key=lambda x: x.get("sort_order", 999))

       # Build definition_data JSON
       definition_data = {
           "slug": fg.slug,
           "display_name": fg.display_name,
           "description": fg.description,
           "assembly_type": fg.assembly_type.value if fg.assembly_type else None,
           "packaging_instructions": fg.packaging_instructions,
           "notes": fg.notes,
           "components": components_data,
       }

       # Create snapshot
       snapshot = FinishedGoodSnapshot(
           finished_good_id=finished_good_id,
           planning_snapshot_id=planning_snapshot_id,
           assembly_run_id=assembly_run_id,
           definition_data=json.dumps(definition_data),
           is_backfilled=False,
       )

       session.add(snapshot)
       session.flush()

       # Remove from visited set after processing (allows same item in different branches)
       # Actually, keep it - we want to prevent ANY duplicate in hierarchy
       # visited_ids.remove(finished_good_id)  # Don't remove

       return {
           "id": snapshot.id,
           "finished_good_id": snapshot.finished_good_id,
           "planning_snapshot_id": snapshot.planning_snapshot_id,
           "assembly_run_id": snapshot.assembly_run_id,
           "snapshot_date": snapshot.snapshot_date.isoformat(),
           "definition_data": definition_data,
           "is_backfilled": snapshot.is_backfilled,
       }
   ```

---

### Subtask T015 – Implement component snapshot helper

**Purpose**: Handle polymorphic component types and create appropriate snapshots.

**File**: `src/services/finished_good_service.py`

**Steps**:

1. Add helper function:
   ```python
   def _snapshot_component(
       composition,
       planning_snapshot_id: int,
       assembly_run_id: int,
       session: Session,
       visited_ids: set[int],
       depth: int
   ) -> dict | None:
       """
       Create snapshot for a single component based on its type.

       Args:
           composition: Composition model instance
           planning_snapshot_id: Planning context
           assembly_run_id: Assembly context
           session: Database session
           visited_ids: Set of visited FinishedGood IDs
           depth: Current recursion depth

       Returns:
           Component data dict with snapshot_id, or None if skipped
       """
       component_type = composition.component_type
       base_data = {
           "component_quantity": composition.component_quantity,
           "component_notes": composition.component_notes,
           "sort_order": composition.sort_order,
           "is_generic": composition.is_generic,
       }

       if composition.finished_unit_id:
           # FinishedUnit component - create snapshot
           fu_snapshot = create_finished_unit_snapshot(
               finished_unit_id=composition.finished_unit_id,
               planning_snapshot_id=planning_snapshot_id,
               assembly_run_id=assembly_run_id,
               session=session,
           )
           return {
               **base_data,
               "component_type": "finished_unit",
               "snapshot_id": fu_snapshot["id"],
               "original_id": composition.finished_unit_id,
               "component_slug": fu_snapshot["definition_data"]["slug"],
               "component_name": fu_snapshot["definition_data"]["display_name"],
           }

       elif composition.finished_good_id:
           # Nested FinishedGood - recurse
           fg_snapshot = _create_finished_good_snapshot_impl(
               finished_good_id=composition.finished_good_id,
               planning_snapshot_id=planning_snapshot_id,
               assembly_run_id=assembly_run_id,
               session=session,
               visited_ids=visited_ids,
               depth=depth + 1,
           )
           return {
               **base_data,
               "component_type": "finished_good",
               "snapshot_id": fg_snapshot["id"],
               "original_id": composition.finished_good_id,
               "component_slug": fg_snapshot["definition_data"]["slug"],
               "component_name": fg_snapshot["definition_data"]["display_name"],
           }

       elif composition.material_unit_id:
           # MaterialUnit component - create snapshot
           mu_snapshot = create_material_unit_snapshot(
               material_unit_id=composition.material_unit_id,
               planning_snapshot_id=planning_snapshot_id,
               assembly_run_id=assembly_run_id,
               session=session,
           )
           return {
               **base_data,
               "component_type": "material_unit",
               "snapshot_id": mu_snapshot["id"],
               "original_id": composition.material_unit_id,
               "component_slug": mu_snapshot["definition_data"]["slug"],
               "component_name": mu_snapshot["definition_data"]["name"],
           }

       elif composition.material_id:
           # Generic material placeholder - no snapshot needed
           material = composition.material_component
           return {
               **base_data,
               "component_type": "material",
               "snapshot_id": None,  # No snapshot for generic placeholder
               "original_id": composition.material_id,
               "component_slug": None,
               "component_name": material.name if material else "Unknown Material",
           }

       elif composition.packaging_product_id:
           # Packaging product - out of scope, skip
           return None

       else:
           # Unknown component type
           return None
   ```

---

### Subtask T016 – Max depth enforcement

**Purpose**: Ensure depth check is at the start of implementation (already done in T014).

**Validation**:
- [ ] MaxDepthExceededError is raised before any processing if depth > 10
- [ ] Depth is incremented when recursing into nested FinishedGood
- [ ] Error message includes current depth and max

---

### Subtask T017 – Add query functions

**Purpose**: Implement snapshot retrieval functions.

**File**: `src/services/finished_good_service.py`

**Steps**:

1. Add `get_finished_good_snapshot()`:
   ```python
   def get_finished_good_snapshot(
       snapshot_id: int,
       session: Session = None
   ) -> dict | None:
       """Get a FinishedGoodSnapshot by its ID."""
       if session is not None:
           return _get_finished_good_snapshot_impl(snapshot_id, session)

       with session_scope() as session:
           return _get_finished_good_snapshot_impl(snapshot_id, session)

   def _get_finished_good_snapshot_impl(
       snapshot_id: int,
       session: Session
   ) -> dict | None:
       snapshot = session.query(FinishedGoodSnapshot).filter_by(id=snapshot_id).first()

       if not snapshot:
           return None

       return {
           "id": snapshot.id,
           "finished_good_id": snapshot.finished_good_id,
           "planning_snapshot_id": snapshot.planning_snapshot_id,
           "assembly_run_id": snapshot.assembly_run_id,
           "snapshot_date": snapshot.snapshot_date.isoformat(),
           "definition_data": snapshot.get_definition_data(),
           "is_backfilled": snapshot.is_backfilled,
       }
   ```

2. Add `get_finished_good_snapshots_by_planning_id()` (similar pattern)

---

### Subtask T018 – Create comprehensive unit tests

**Purpose**: Validate all scenarios including edge cases.

**File**: `src/tests/test_finished_good_snapshot.py`

**Steps**:

1. Create test file with fixtures for:
   - Simple FinishedGood with FinishedUnit components
   - FinishedGood with MaterialUnit components
   - Nested FinishedGood hierarchy (2-3 levels)
   - Circular reference setup (A contains B, B contains A)
   - Deep nesting (11 levels) for max depth test
   - FinishedGood with generic material placeholder

2. Test cases:
   ```python
   class TestCreateFinishedGoodSnapshot:
       def test_creates_snapshot_with_finished_unit_components(self, ...):
           """Snapshot includes FinishedUnit component snapshots."""

       def test_creates_snapshot_with_material_unit_components(self, ...):
           """Snapshot includes MaterialUnit component snapshots."""

       def test_recursively_snapshots_nested_finished_goods(self, ...):
           """Nested FinishedGood components are snapshotted recursively."""

       def test_detects_circular_reference(self, ...):
           """CircularReferenceError raised for A->B->A pattern."""

       def test_detects_indirect_circular_reference(self, ...):
           """CircularReferenceError raised for A->B->C->A pattern."""

       def test_max_depth_exceeded(self, ...):
           """MaxDepthExceededError raised at 11 levels."""

       def test_handles_generic_material_placeholder(self, ...):
           """Generic material stored with is_generic=True, no snapshot."""

       def test_skips_packaging_product(self, ...):
           """Packaging products are skipped (out of scope)."""

       def test_atomicity_on_failure(self, ...):
           """All snapshots rolled back if any creation fails."""

       def test_performance_50_components(self, ...):
           """Snapshot creation <5 seconds for 50 components."""
   ```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Circular reference not detected | Test with deliberately circular fixtures |
| Transaction not atomic | All operations share same session |
| Performance degradation | Test with 50+ components, optimize if needed |
| Component type not handled | Exhaustive switch on composition.component_type |
| Session detachment | Pass session to all nested calls |

## Definition of Done Checklist

- [ ] T011: FinishedGoodSnapshot model created
- [ ] T012: Model exported from src/models/__init__.py
- [ ] T013: Exception classes defined
- [ ] T014: create_finished_good_snapshot() implemented
- [ ] T015: Component snapshot helper implemented
- [ ] T016: Max depth enforcement validated
- [ ] T017: Query functions implemented
- [ ] T018: All unit tests pass including edge cases
- [ ] CircularReferenceError message includes path
- [ ] Performance <5s for 50 components
- [ ] `tasks.md` updated with status change

## Review Guidance

**Reviewer Checklist**:
- [ ] Circular reference detection works (test with fixtures)
- [ ] Max depth raised at 11 levels
- [ ] All component types handled correctly
- [ ] Session passed through all nested calls
- [ ] Transaction atomicity maintained
- [ ] Error messages are descriptive

## Activity Log

- 2025-01-24T05:30:00Z – system – lane=planned – Prompt generated via /spec-kitty.tasks
- 2026-01-24T17:49:52Z – claude-opus – lane=doing – Moved to doing
- 2026-01-24T17:58:46Z – claude-opus – lane=for_review – All 19 tests pass. Recursive snapshot with circular reference and max depth protection implemented.
- 2026-01-24T17:59:35Z – claude-opus – shell_pid=58308 – lane=doing – Started review via workflow command
- 2026-01-24T18:00:33Z – claude-opus – shell_pid=58308 – lane=done – Review passed: Model matches spec, recursive snapshot with circular reference and max depth protection implemented correctly, all 19 tests pass, session handling correct for atomicity
