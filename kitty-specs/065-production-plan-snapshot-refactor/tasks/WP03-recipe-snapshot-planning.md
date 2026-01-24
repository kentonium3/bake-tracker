---
work_package_id: WP03
title: Recipe Snapshot Service Planning Context
lane: "done"
dependencies: [WP02]
base_branch: 065-production-plan-snapshot-refactor-WP02
base_commit: 77ba3b57119846919c8e1e7a55fa3c38ee273971
created_at: '2026-01-24T20:59:25.017534+00:00'
subtasks:
- T010
- T011
- T012
- T013
phase: Phase 2 - Service Layer - Snapshot Creation
assignee: ''
agent: "claude-opus"
shell_pid: "82445"
review_status: "approved"
reviewed_by: "Kent Gale"
history:
- timestamp: '2026-01-24T19:47:15Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP03 – Recipe Snapshot Service Planning Context

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.

---

## Review Feedback

> **Populated by `/spec-kitty.review`**

*[This section is empty initially.]*

---

## Implementation Command

```bash
# Depends on WP02 (nullable production_run_id)
spec-kitty implement WP03 --base WP02 --feature 065-production-plan-snapshot-refactor
```

---

## Objectives & Success Criteria

Update recipe_snapshot_service to support creating snapshots without a production_run_id (planning context).

**Success Criteria**:
- [ ] create_recipe_snapshot() accepts optional production_run_id parameter
- [ ] create_recipe_snapshot() properly accepts and uses session parameter
- [ ] Snapshots can be created with production_run_id=None (planning context)
- [ ] Existing callers (production context) continue to work unchanged
- [ ] Unit tests verify planning context snapshot creation

## Context & Constraints

**Reference Documents**:
- `kitty-specs/065-production-plan-snapshot-refactor/research.md` - RQ-2 (snapshot patterns), RQ-7 (session management)
- `.kittify/memory/constitution.md` - Principle IV (Test-Driven Development)
- `CLAUDE.md` - Session Management section (CRITICAL)

**Session Management Pattern** (from CLAUDE.md):
```python
def service_function(arg1, arg2, session=None):
    """Accept optional session parameter."""
    if session is not None:
        return _service_function_impl(arg1, arg2, session)
    with session_scope() as session:
        return _service_function_impl(arg1, arg2, session)
```

**Key Constraints**:
- Must maintain backward compatibility (existing production callers)
- Must follow CLAUDE.md session management patterns
- Return dict with snapshot id for linking to targets

## Subtasks & Detailed Guidance

### Subtask T010 – Update create_recipe_snapshot() to accept optional production_run_id

**Purpose**: Currently production_run_id is required. Making it optional allows planning service to create snapshots without a production run.

**Steps**:
1. Open `src/services/recipe_snapshot_service.py`
2. Find create_recipe_snapshot() function signature
3. Change production_run_id parameter to optional with default None:
   ```python
   def create_recipe_snapshot(
       recipe_id: int,
       scale_factor: float = 1.0,
       production_run_id: int = None,  # Optional for planning context
       session=None
   ) -> dict:
   ```
4. Update function docstring:
   ```python
   """Create an immutable snapshot of a recipe.

   Args:
       recipe_id: ID of the recipe to snapshot
       scale_factor: Scaling factor for quantities (default 1.0)
       production_run_id: Optional production run ID (None for planning context)
       session: Optional SQLAlchemy session for transaction management

   Returns:
       dict with 'id', 'recipe_id', 'snapshot_date', etc.

   Context:
       - Production context: production_run_id provided (snapshot created at production time)
       - Planning context: production_run_id=None (snapshot created at plan time,
         linked via EventProductionTarget.recipe_snapshot_id)
   """
   ```

**Files**:
- `src/services/recipe_snapshot_service.py` (modify)

**Parallel?**: No - foundation for T011, T012

**Notes**: Existing callers passing production_run_id continue to work unchanged.

---

### Subtask T011 – Ensure session parameter flows correctly

**Purpose**: Planning service will pass session for transaction atomicity. The snapshot service must use passed session properly.

**Steps**:
1. Verify create_recipe_snapshot() follows CLAUDE.md pattern:
   ```python
   def create_recipe_snapshot(
       recipe_id: int,
       scale_factor: float = 1.0,
       production_run_id: int = None,
       session=None
   ) -> dict:
       if session is not None:
           return _create_recipe_snapshot_impl(
               recipe_id, scale_factor, production_run_id, session
           )
       with session_scope() as session:
           return _create_recipe_snapshot_impl(
               recipe_id, scale_factor, production_run_id, session
           )

   def _create_recipe_snapshot_impl(
       recipe_id: int,
       scale_factor: float,
       production_run_id: int,
       session
   ) -> dict:
       # Actual implementation here
       recipe = session.get(Recipe, recipe_id)
       # ... create snapshot ...
       session.add(snapshot)
       session.flush()  # Get ID before returning
       return {"id": snapshot.id, ...}
   ```

2. Verify session.flush() is called before returning (to get snapshot ID)

3. Verify no nested session_scope() calls in implementation

**Files**:
- `src/services/recipe_snapshot_service.py` (modify)

**Parallel?**: No - builds on T010

**Notes**:
- Using session.flush() instead of session.commit() allows caller to control transaction
- The passed session keeps ORM objects attached (avoids detachment bugs)

---

### Subtask T012 – Add validation for planning context

**Purpose**: Document and optionally validate that planning context snapshots work correctly without production_run_id.

**Steps**:
1. In _create_recipe_snapshot_impl(), handle production_run_id=None:
   ```python
   def _create_recipe_snapshot_impl(
       recipe_id: int,
       scale_factor: float,
       production_run_id: int,
       session
   ) -> dict:
       recipe = session.get(Recipe, recipe_id)
       if not recipe:
           raise ValueError(f"Recipe {recipe_id} not found")

       # Create snapshot - production_run_id can be None for planning context
       snapshot = RecipeSnapshot(
           recipe_id=recipe_id,
           production_run_id=production_run_id,  # May be None
           scale_factor=scale_factor,
           snapshot_date=datetime.utcnow(),
           recipe_data=json.dumps(recipe.to_dict()),
           ingredients_data=json.dumps([ing.to_dict() for ing in recipe.ingredients]),
           is_backfilled=False
       )
       session.add(snapshot)
       session.flush()

       return {
           "id": snapshot.id,
           "recipe_id": snapshot.recipe_id,
           "production_run_id": snapshot.production_run_id,
           "scale_factor": snapshot.scale_factor,
           "snapshot_date": snapshot.snapshot_date.isoformat()
       }
   ```

2. Ensure RecipeSnapshot model accepts production_run_id=None (verified in WP02)

**Files**:
- `src/services/recipe_snapshot_service.py` (modify)

**Parallel?**: No - builds on T010, T011

**Notes**: The key change is simply allowing production_run_id=None to pass through to the model.

---

### Subtask T013 – Unit tests for planning context snapshot creation

**Purpose**: Verify snapshot creation works in planning context (no production_run_id).

**Steps**:
1. Find or create test file: `src/tests/unit/test_recipe_snapshot_service.py`

2. Add test for planning context:
   ```python
   def test_create_recipe_snapshot_planning_context(db_session):
       """Test creating snapshot for planning (no production_run_id)."""
       # Setup: create a recipe
       recipe = Recipe(name="Test Recipe", ...)
       db_session.add(recipe)
       db_session.flush()

       # Act: create snapshot without production_run_id
       result = create_recipe_snapshot(
           recipe_id=recipe.id,
           scale_factor=1.0,
           production_run_id=None,  # Planning context
           session=db_session
       )

       # Assert
       assert result["id"] is not None
       assert result["recipe_id"] == recipe.id
       assert result["production_run_id"] is None
       assert result["scale_factor"] == 1.0

       # Verify in database
       snapshot = db_session.get(RecipeSnapshot, result["id"])
       assert snapshot is not None
       assert snapshot.production_run_id is None
   ```

3. Add test for production context (backward compatibility):
   ```python
   def test_create_recipe_snapshot_production_context(db_session):
       """Test creating snapshot with production_run_id (existing behavior)."""
       # Setup
       recipe = Recipe(...)
       production_run = ProductionRun(...)
       db_session.add_all([recipe, production_run])
       db_session.flush()

       # Act
       result = create_recipe_snapshot(
           recipe_id=recipe.id,
           scale_factor=2.0,
           production_run_id=production_run.id,
           session=db_session
       )

       # Assert
       assert result["production_run_id"] == production_run.id
   ```

4. Add test for session parameter:
   ```python
   def test_create_recipe_snapshot_uses_passed_session(db_session):
       """Test that passed session is used (not a new one)."""
       recipe = Recipe(...)
       db_session.add(recipe)
       db_session.flush()

       # Create snapshot with explicit session
       result = create_recipe_snapshot(
           recipe_id=recipe.id,
           session=db_session
       )

       # Object should still be attached to passed session
       snapshot = db_session.get(RecipeSnapshot, result["id"])
       assert snapshot in db_session  # Attached, not detached
   ```

**Files**:
- `src/tests/unit/test_recipe_snapshot_service.py` (create or modify)

**Parallel?**: No - requires T010-T012 complete

**Notes**: Run tests with: `./run-tests.sh src/tests/unit/test_recipe_snapshot_service.py -v`

---

## Test Strategy

**Run Tests**:
```bash
# Run specific test file
./run-tests.sh src/tests/unit/test_recipe_snapshot_service.py -v

# Run with coverage
./run-tests.sh src/tests/unit/test_recipe_snapshot_service.py -v --cov=src/services/recipe_snapshot_service
```

**Expected Coverage**: >70% for recipe_snapshot_service.py

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Session detachment | Follow CLAUDE.md patterns exactly; use flush() not commit() |
| Breaking existing callers | production_run_id has default=None, existing callers unchanged |
| Test fixtures missing | Use existing test patterns from other service tests |

## Definition of Done Checklist

- [ ] create_recipe_snapshot() accepts production_run_id=None
- [ ] Session parameter properly implemented per CLAUDE.md
- [ ] Planning context creates valid snapshot (production_run_id=None)
- [ ] Production context still works (backward compatibility)
- [ ] Unit tests pass for both contexts
- [ ] Test coverage >70% for recipe_snapshot_service.py
- [ ] Activity log entry added

## Review Guidance

Reviewers should verify:
1. Session management follows CLAUDE.md pattern exactly
2. Backward compatibility maintained
3. Tests cover both planning and production contexts
4. No nested session_scope() calls

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

- 2026-01-24T19:47:15Z – system – lane=planned – Prompt created.
- 2026-01-24T21:12:05Z – unknown – shell_pid=80145 – lane=for_review – Ready for review: production_run_id now optional with planning context tests
- 2026-01-24T21:18:05Z – claude-opus – shell_pid=82445 – lane=doing – Started review via workflow command
- 2026-01-24T21:18:38Z – claude-opus – shell_pid=82445 – lane=done – Review passed: production_run_id optional, session pattern correct, 4 planning context tests added, backward compatible
