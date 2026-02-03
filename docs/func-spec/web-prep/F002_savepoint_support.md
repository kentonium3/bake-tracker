# F002: Savepoint Support for Nested Transactions

**Version**: 1.0
**Priority**: PARKED (implement when use case emerges)
**Type**: Architecture Enhancement
**Status**: Ready for implementation when needed
**Location**: web-prep/ (parked until needed)
**Estimated Effort**: 2-3 hours

---

## Executive Summary

**Status: This feature is PARKED until a concrete use case emerges.**

SQLAlchemy already provides savepoint support via `session.begin_nested()`. This spec documents how to implement a convenience wrapper IF and WHEN partial rollback scenarios are needed.

Current status:
- ✅ All multi-step operations are correctly atomic (all-or-nothing)
- ✅ No use cases exist for partial rollback
- ✅ SQLAlchemy provides `begin_nested()` if needed
- ⏸️ No custom savepoint infrastructure needed currently

**Estimated implementation time when needed:** 30 minutes - 2 hours

---

## Why This is Parked (Not Implemented Now)

**Current operations are correctly all-or-nothing:**
1. ✅ Batch production: All steps succeed OR entire operation rolls back
2. ✅ Assembly: All components consumed OR none consumed
3. ✅ Recipe operations: Ingredients added OR recipe creation fails
4. ✅ No "optional components that can fail independently" scenarios

**No use cases for partial rollback:**
- ❌ No batch processing (skip bad records, process rest)
- ❌ No optional features (main succeeds, extras can fail)
- ❌ No complex multi-stage pipelines (checkpoint intermediate states)

**SQLAlchemy already has this feature:**
```python
# Built-in savepoint support (no wrapper needed)
nested = session.begin_nested()  # Creates savepoint
try:
    # Operations...
    nested.commit()  # Commits savepoint
except:
    nested.rollback()  # Rolls back to savepoint
```

**YAGNI Principle:**
- Don't build infrastructure for hypothetical scenarios
- Implement when actual use case emerges
- Takes 30 minutes when needed

---

## When to Implement This Feature

**Implement when ANY of these scenarios emerge:**

✅ **Batch Processing Added**
- Processing multiple records where some may fail
- Want to skip bad records but continue processing
- Example: "Import 100 ingredients, skip invalid ones"

✅ **Optional Feature Pattern**
- Main operation must succeed even if extras fail
- Example: "Create recipe with optional image upload"
- Example: "Record production with optional quality check"

✅ **Complex Multi-Stage Workflow**
- Checkpoint intermediate states
- Allow partial progress in long operations
- Example: "Multi-step wizard with save-and-continue"

✅ **Audit/Compliance Requirement**
- Need to record attempt even if operation fails
- Partial data capture for debugging
- Example: "Log failed operation details before rollback"

**Current status:** None of these scenarios exist → PARKED

---

## Problem Statement

**Hypothetical Future Scenario (NOT current state):**

```python
# Hypothetical: Recipe creation with optional image processing
def create_recipe_with_media(recipe_data, image_file=None, session=None):
    """
    Create recipe, optionally process image.

    Desired behavior:
    - Recipe MUST be created (core operation)
    - Image processing can fail (optional enhancement)
    - If image fails, log warning but continue
    """
    # This pattern doesn't exist yet in codebase
```

**Current approach (all-or-nothing):**
```python
# Current pattern: All steps succeed or all fail
def record_batch_production(..., session=None):
    """
    ALL operations atomic:
    1. Create snapshot
    2. Consume inventory
    3. Update counts
    4. Create records

    If ANY step fails, ENTIRE operation rolls back.
    """
    # This is correct for batch production!
```

**When savepoint would be useful:**
```python
# Hypothetical future: Partial rollback
def create_recipe_with_optional_image(recipe_data, image_file=None):
    with session_scope() as session:
        # Core operation (must succeed)
        recipe = create_recipe(recipe_data, session=session)

        # Optional enhancement (can fail independently)
        try:
            with savepoint(session):
                process_and_attach_image(recipe.id, image_file, session=session)
        except ImageProcessingError as e:
            # Recipe still created, just log warning
            logger.warning(f"Image processing failed: {e}")

        return recipe
```

---

## Implementation Guide (When Needed)

### Approach 1: Simple Context Manager (30 minutes)

**Minimal wrapper around SQLAlchemy's begin_nested():**

```python
# src/services/database.py
from contextlib import contextmanager
from sqlalchemy.orm import Session

@contextmanager
def savepoint(session: Session, name: str = "sp"):
    """
    Create a savepoint for nested transaction with partial rollback.

    Allows operations within the savepoint to roll back independently
    while preserving the outer transaction.

    Args:
        session: Active SQLAlchemy session
        name: Savepoint name (for debugging, optional)

    Yields:
        Nested transaction object

    Example:
        with session_scope() as session:
            # Main operation (must succeed)
            create_recipe(data, session=session)

            # Optional operation (can fail independently)
            try:
                with savepoint(session):
                    add_optional_components(recipe_id, session=session)
            except ValidationError:
                # Main operation preserved, optional rolled back
                logger.warning("Optional components skipped")

    Note:
        SQLite supports savepoints but has limitations:
        - No concurrent writers (not an issue for desktop)
        - Savepoints nested within savepoints (works but limited)
        PostgreSQL has full savepoint support.
    """
    nested = session.begin_nested()
    try:
        yield nested
    except Exception:
        nested.rollback()
        raise
    # No explicit commit needed - nested transaction commits on context exit
```

**That's it.** 15 lines of code.

---

### Approach 2: Enhanced with Logging (2 hours)

**If you want observability and debugging support:**

```python
# src/services/database.py
import logging
from contextlib import contextmanager
from typing import Optional
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

@contextmanager
def savepoint(
    session: Session,
    name: str = "sp",
    log_rollback: bool = True,
    correlation_id: Optional[str] = None
):
    """
    Create a savepoint with optional logging and observability.

    Args:
        session: Active SQLAlchemy session
        name: Savepoint name (for debugging)
        log_rollback: Log rollback events (default True)
        correlation_id: Optional correlation ID for tracing

    Yields:
        Nested transaction object
    """
    from src.services.context import get_correlation_id

    corr_id = correlation_id or get_correlation_id()

    logger.debug(f"[{corr_id}] Creating savepoint '{name}'")
    nested = session.begin_nested()

    try:
        yield nested
        logger.debug(f"[{corr_id}] Savepoint '{name}' committed")
    except Exception as e:
        nested.rollback()
        if log_rollback:
            logger.warning(
                f"[{corr_id}] Savepoint '{name}' rolled back: {type(e).__name__}: {e}"
            )
        raise
```

**Additional features:**
- Correlation ID tracking
- Debug logging for savepoint lifecycle
- Rollback reason logging

---

## Usage Patterns (When Implemented)

### Pattern 1: Optional Feature Enhancement

**Scenario:** Main operation must succeed, enhancement can fail

```python
def create_recipe_with_enhancements(
    recipe_data: RecipeCreate,
    optional_image: Optional[bytes] = None,
    session: Optional[Session] = None
) -> Recipe:
    """
    Create recipe with optional image processing.

    Transaction boundary: Recipe creation is atomic (must succeed).
    Image processing can fail independently (savepoint rollback).

    Args:
        recipe_data: Core recipe data (required)
        optional_image: Optional image file (can fail)
        session: Optional session

    Returns:
        Created recipe (even if image processing fails)
    """
    def _impl(sess: Session) -> Recipe:
        # Core operation (must succeed)
        recipe = Recipe(**recipe_data.dict())
        sess.add(recipe)
        sess.flush()  # Get recipe.id

        # Optional enhancement (can fail)
        if optional_image:
            try:
                with savepoint(sess, name="image_processing"):
                    process_image(recipe.id, optional_image, session=sess)
                    logger.info(f"Image processed for recipe {recipe.id}")
            except ImageProcessingError as e:
                # Recipe still created, just log warning
                logger.warning(f"Image processing failed for recipe {recipe.id}: {e}")

        return recipe

    if session is not None:
        return _impl(session)
    with session_scope() as sess:
        return _impl(sess)
```

### Pattern 2: Batch Processing with Partial Success

**Scenario:** Process multiple items, skip failures

```python
def import_ingredients_batch(
    ingredients_data: List[IngredientCreate],
    session: Optional[Session] = None
) -> Dict[str, Any]:
    """
    Import multiple ingredients, skipping invalid ones.

    Transaction boundary: Each ingredient is a savepoint.
    Invalid ingredients are skipped (logged), valid ones committed.

    Returns:
        Success/failure counts and details
    """
    def _impl(sess: Session) -> Dict[str, Any]:
        results = {"success": 0, "failed": 0, "errors": []}

        for idx, ingredient_data in enumerate(ingredients_data):
            try:
                with savepoint(sess, name=f"ingredient_{idx}"):
                    ingredient = create_ingredient(ingredient_data, session=sess)
                    results["success"] += 1
            except ValidationError as e:
                results["failed"] += 1
                results["errors"].append({
                    "index": idx,
                    "name": ingredient_data.display_name,
                    "error": str(e)
                })
                logger.warning(f"Ingredient {idx} failed validation: {e}")

        return results

    if session is not None:
        return _impl(session)
    with session_scope() as sess:
        return _impl(sess)
```

### Pattern 3: Audit Trail for Failed Operations

**Scenario:** Record attempt even if operation fails

```python
def record_production_with_audit(
    recipe_id: int,
    quantity: int,
    session: Optional[Session] = None
) -> ProductionRun:
    """
    Record production with audit trail for failures.

    Transaction boundary: Audit log committed even if production fails.
    """
    def _impl(sess: Session) -> ProductionRun:
        # Create audit entry (will be committed even if production fails)
        audit = ProductionAuditLog(
            recipe_id=recipe_id,
            quantity=quantity,
            attempted_at=utc_now(),
            status="attempting"
        )
        sess.add(audit)
        sess.flush()

        # Attempt production (can fail)
        try:
            with savepoint(sess, name="production"):
                production = record_batch_production(
                    recipe_id, quantity, session=sess
                )
                audit.status = "success"
                audit.production_run_id = production.id
                return production
        except InsufficientInventoryError as e:
            # Audit entry committed with failure status
            audit.status = "failed"
            audit.failure_reason = str(e)
            raise

    if session is not None:
        return _impl(session)
    with session_scope() as sess:
        return _impl(sess)
```

---

## Out of Scope (NOT Implemented)

**This parked spec explicitly DOES NOT include:**

- ❌ Implementing savepoint now (no use case)
- ❌ Refactoring existing operations to use savepoints (not needed)
- ❌ Complex nested savepoint hierarchies (YAGNI)
- ❌ Savepoint naming strategies (keep simple)
- ❌ Savepoint performance optimization (not a bottleneck)

---

## Success Criteria (When Implementing)

**Implement when use case emerges, complete when:**

### Implementation
- [ ] `savepoint()` context manager exists in `database.py`
- [ ] Docstring documents usage pattern
- [ ] Example provided in docstring or guide

### Testing
- [ ] Unit test: savepoint commits on success
- [ ] Unit test: savepoint rolls back on exception
- [ ] Unit test: outer transaction preserved after savepoint rollback
- [ ] Integration test: actual use case (batch processing, optional feature, etc.)

### Documentation
- [ ] Usage pattern documented in transaction patterns guide
- [ ] Example added to CLAUDE.md
- [ ] When to use savepoints vs all-or-nothing documented

**Total implementation time:** 30 minutes (simple) to 2 hours (enhanced)

---

## Constitutional Compliance

✅ **YAGNI Principle**
- Not implementing until concrete use case exists
- Can implement quickly when needed
- No premature optimization

✅ **Principle VI.C.2: Transaction Boundaries**
- Savepoints are explicit transaction boundaries
- Usage patterns clearly documented
- No implicit behavior

✅ **Principle VI.E: Observability**
- Enhanced approach includes logging
- Savepoint rollbacks visible in logs
- Correlation IDs supported

---

## Risk Mitigation

### Risk: Savepoint Misuse

**Problem:** Developer uses savepoint when all-or-nothing is correct

**Mitigation:**
- Document when to use savepoints (rare scenarios)
- Code review checks: "Why is savepoint needed here?"
- Default to all-or-nothing (current pattern)

### Risk: Nested Savepoint Complexity

**Problem:** Savepoints within savepoints get confusing

**Mitigation:**
- Keep savepoint usage shallow (1-2 levels max)
- Document nested savepoint limitations
- SQLite has limited nested savepoint support

### Risk: SQLite Limitations

**Problem:** SQLite savepoints have edge cases

**Mitigation:**
- Test savepoint behavior thoroughly
- Document SQLite-specific limitations
- PostgreSQL migration will improve support

---

## Decision: Why Park This Feature

**Reasons to defer until needed:**

1. **No Current Use Cases**
   - All operations correctly atomic (all-or-nothing)
   - No batch processing scenarios
   - No optional feature patterns
   - No complex multi-stage workflows

2. **SQLAlchemy Already Provides This**
   - `session.begin_nested()` works
   - Wrapper adds minimal value
   - Can implement in 30 minutes when needed

3. **YAGNI Principle**
   - Building infrastructure for hypothetical needs
   - Adds complexity without solving problems
   - Quick to add when actually needed

4. **Focus on Current Gaps**
   - F091 (transaction documentation) is higher priority
   - Transaction boundaries need documentation first
   - Savepoints are advanced feature (document basic patterns first)

**Implementing now would be premature optimization.**

---

## When to Un-Park This Feature

**Un-park and implement when:**

✅ **Concrete use case emerges** (batch processing, optional features, etc.)
✅ **Multiple developers ask "how do I do partial rollback?"**
✅ **Code review reveals pattern needing savepoints**
✅ **Audit/compliance requires partial transaction logging**

**Don't un-park for:**
❌ "It might be useful someday"
❌ "Let's prepare for future needs"
❌ "Other frameworks have this feature"

**Current status:** No use cases exist → REMAINS PARKED

---

## Reference Documentation

**Study these when implementing:**

1. **SQLAlchemy Nested Transactions:**
   - https://docs.sqlalchemy.org/en/20/orm/session_transaction.html#using-savepoint
   - `Session.begin_nested()` documentation

2. **SQLite Savepoint Support:**
   - https://www.sqlite.org/lang_savepoint.html
   - Limitations and edge cases

3. **PostgreSQL Savepoint Support:**
   - https://www.postgresql.org/docs/current/sql-savepoint.html
   - Full savepoint support when migrating

4. **Current Transaction Patterns (F091):**
   - Transaction boundary documentation
   - Session parameter pattern
   - Multi-step atomic operations

---

**END OF PARKED SPECIFICATION**
