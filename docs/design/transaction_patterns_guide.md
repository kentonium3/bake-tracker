# Transaction Patterns Guide

**Version**: 1.0
**Purpose**: Document transaction boundary patterns for Bake Tracker service layer
**Audience**: Developers and AI agents working on the codebase

---

## Quick Reference

| Pattern | When to Use | Session Handling | Transaction Scope |
|---------|-------------|------------------|-------------------|
| **Pattern A (Read-Only)** | `get_*()`, `list_*()`, `search_*()` | Optional session | No commit needed |
| **Pattern B (Single-Step Write)** | Simple CRUD without nested calls | Optional session | Auto-commit or caller-controlled |
| **Pattern C (Multi-Step Atomic)** | Operations calling other services | Optional session | ALL steps in single session |

---

## Introduction

### Purpose of Transaction Documentation

This guide documents the transaction patterns used throughout the Bake Tracker service layer. Clear transaction documentation:

1. **Prevents bugs**: Developers know what operations are atomic
2. **Enables debugging**: Transaction scope is explicit, not inferred
3. **Supports code review**: Reviewers can verify atomicity from docstrings
4. **Guides AI agents**: Clear patterns enable consistent code generation

### How to Read "Transaction boundary:" Sections

Every service function includes a "Transaction boundary:" section in its docstring. These sections specify:

- **Transaction scope**: Read-only, single operation, or multi-step atomic
- **Atomicity guarantee**: What succeeds or fails together
- **Session parameter usage**: When and why to pass a session

### When Transactions Matter vs Don't Matter

**Transactions matter when:**
- Multiple database operations must succeed or fail together
- Data consistency depends on all steps completing
- Concurrent access could cause inconsistent reads

**Transactions don't matter when:**
- Single read operations (query only)
- No side effects on database state
- Operations are truly independent

---

## Pattern Catalog

### Pattern A: Read-Only Operations

**Description**: Operations that only read data and have no side effects.

**When to use**:
- `get_*()` functions that retrieve single records
- `list_*()` functions that query collections
- `search_*()` functions with filtering
- Validation functions that check existence

**Transaction scope**: No transaction needed for reads, but accepting a session parameter enables consistent reads across multiple queries.

**Template**:
```python
def get_something(identifier: str, session=None) -> SomeModel:
    """Retrieve something by identifier.

    Transaction boundary: Read-only, no transaction needed.
    Safe to call without session - uses temporary session for query.
    If session provided, query executes within caller's transaction for
    consistent reads across multiple queries.

    Args:
        identifier: Unique identifier
        session: Optional database session. If provided, uses this session instead
                 of creating a new one. Important for transactional consistency
                 when called from within another session_scope block.

    Returns:
        SomeModel: Retrieved object

    Raises:
        SomeNotFoundError: If identifier doesn't exist
    """
    if session is not None:
        result = session.query(SomeModel).filter_by(id=identifier).first()
        if not result:
            raise SomeNotFoundError(identifier)
        return result

    with session_scope() as session:
        result = session.query(SomeModel).filter_by(id=identifier).first()
        if not result:
            raise SomeNotFoundError(identifier)
        return result
```

**Real Example from Codebase** (`src/services/ingredient_service.py`):

```python
def get_ingredient(slug: str, session=None) -> Ingredient:
    """Retrieve ingredient by slug.

    Transaction boundary: Read-only, no transaction needed.
    Safe to call without session - uses temporary session for query.
    If session provided, query executes within caller's transaction for
    consistent reads across multiple queries.

    Args:
        slug: Unique ingredient identifier (e.g., "all_purpose_flour")
        session: Optional database session. If provided, uses this session instead
                 of creating a new one. This is important for maintaining transactional
                 atomicity when called from within another session_scope block.

    Returns:
        Ingredient: Ingredient object with relationships eager-loaded

    Raises:
        IngredientNotFoundBySlug: If slug doesn't exist
    """
    if session is not None:
        ingredient = session.query(Ingredient).filter_by(slug=slug).first()
        if not ingredient:
            raise IngredientNotFoundBySlug(slug)
        return ingredient

    with session_scope() as session:
        ingredient = session.query(Ingredient).filter_by(slug=slug).first()
        if not ingredient:
            raise IngredientNotFoundBySlug(slug)
        return ingredient
```

---

### Pattern B: Single-Step Write Operations

**Description**: Operations that perform a single database write without calling other service functions.

**When to use**:
- Simple `create_*()` functions
- Direct `update_*()` with no nested service calls
- `delete_*()` operations without cascading business logic

**Transaction scope**: Single operation, automatically atomic. The operation either succeeds completely or rolls back.

**Template**:
```python
def create_something(data: Dict[str, Any], session=None) -> SomeModel:
    """Create a new record.

    Transaction boundary: Single operation, automatically atomic.
    If session provided, caller controls transaction commit/rollback.
    If session not provided, uses session_scope() (auto-commit on success).

    Args:
        data: Dictionary with fields for new record
        session: Optional session for transactional composition

    Returns:
        SomeModel: Created object

    Raises:
        ValidationError: If data invalid
        DatabaseError: If database operation fails
    """
    def _impl(sess: Session) -> SomeModel:
        # Validation
        is_valid, errors = validate_data(data)
        if not is_valid:
            raise ValidationError(errors)

        # Create record
        record = SomeModel(**data)
        sess.add(record)
        sess.flush()  # Get ID before commit
        return record

    if session is not None:
        return _impl(session)
    with session_scope() as sess:
        return _impl(sess)
```

**Real Example Pattern from Codebase**:

Single-step writes in this codebase typically use the `_impl` function pattern to keep session handling separate from business logic. The key characteristic is that there are no calls to other service functions within the session scope.

```python
def create_supplier(supplier_data: Dict[str, Any]) -> Supplier:
    """Create a new supplier.

    Transaction boundary: Single operation, automatically atomic.
    If session not provided, uses session_scope() (auto-commit on success).

    Args:
        supplier_data: Dictionary with supplier fields

    Returns:
        Supplier: Created supplier object
    """
    with session_scope() as session:
        supplier = Supplier(
            slug=create_slug(supplier_data["name"]),
            name=supplier_data["name"],
            contact_info=supplier_data.get("contact_info"),
        )
        session.add(supplier)
        session.flush()
        return supplier
```

---

### Pattern C: Multi-Step Atomic Operations

**Description**: Operations that call multiple service functions and must succeed or fail as a unit.

**When to use**:
- Production recording (consume ingredients + create production run)
- Assembly operations (consume finished goods + create assembly)
- Complex business transactions involving multiple entities
- Any operation calling 2+ other service functions

**Transaction scope**: ALL operations execute in a single session. Either all steps succeed OR the entire operation rolls back.

**Template**:
```python
def complex_operation(
    entity_id: int,
    quantity: int,
    *,
    session=None,
) -> Dict[str, Any]:
    """Perform multi-step operation atomically.

    Transaction boundary: ALL operations in single session (atomic).
    Atomicity guarantee: Either ALL steps succeed OR entire operation rolls back.
    Steps executed atomically:
    1. Validate inputs and load entities
    2. Perform first nested operation (e.g., consume inventory)
    3. Perform second nested operation (e.g., create record)
    4. Update related entities

    CRITICAL: All nested service calls receive session parameter to ensure
    atomicity. Never create new session_scope() within this function.

    Args:
        entity_id: ID of the primary entity
        quantity: Operation quantity
        session: Optional session for transactional composition

    Returns:
        Dict with operation results

    Raises:
        EntityNotFoundError: If entity doesn't exist
        BusinessRuleError: If business rules violated
    """
    # Use nullcontext to honor passed session per CLAUDE.md pattern
    cm = nullcontext(session) if session is not None else session_scope()
    with cm as session:
        # Step 1: Validate and load
        entity = session.query(Entity).filter_by(id=entity_id).first()
        if not entity:
            raise EntityNotFoundError(entity_id)

        # Step 2: Nested call - PASS SESSION
        first_result = first_service_call(..., session=session)

        # Step 3: Nested call - PASS SESSION
        second_result = second_service_call(..., session=session)

        # Step 4: Final updates
        entity.updated_field = new_value
        session.flush()

        return {
            "entity_id": entity_id,
            "first_result": first_result,
            "second_result": second_result,
        }
```

**Real Example from Codebase** (`src/services/batch_production_service.py`):

```python
def record_batch_production(
    recipe_id: int,
    finished_unit_id: int,
    num_batches: int,
    actual_yield: int,
    *,
    produced_at: Optional[datetime] = None,
    notes: Optional[str] = None,
    event_id: Optional[int] = None,
    scale_factor: float = 1.0,
    session=None,
) -> Dict[str, Any]:
    """
    Record a batch production run with FIFO consumption.

    Transaction boundary: ALL operations in single session (atomic).
    Atomicity guarantee: Either ALL steps succeed OR entire operation rolls back.
    Steps executed atomically:
    1. Validates recipe and finished unit
    2. Validates event if provided
    3. Creates recipe snapshot
    4. Validates actual_yield <= expected_yield
    5. Consumes ingredients from inventory via FIFO
    6. Increments FinishedUnit.inventory_count by actual_yield
    7. Creates ProductionRun record
    8. Creates ProductionLoss record if loss_quantity > 0
    9. Calculates per-unit cost based on actual yield

    CRITICAL: All nested service calls receive session parameter to ensure
    atomicity. Never create new session_scope() within this function.

    Args:
        recipe_id: ID of the recipe being produced
        finished_unit_id: ID of the FinishedUnit being produced
        num_batches: Number of recipe batches made
        actual_yield: Actual number of units produced
        produced_at: Optional production timestamp
        notes: Optional production notes
        event_id: Optional event ID to link production to
        scale_factor: Recipe size multiplier
        session: Optional database session

    Returns:
        Dict with production_run_id, costs, consumptions, etc.

    Raises:
        RecipeNotFoundError: If recipe doesn't exist
        FinishedUnitNotFoundError: If finished unit doesn't exist
        InsufficientInventoryError: If ingredient inventory insufficient
    """
    # Honor passed session per CLAUDE.md session management pattern
    cm = nullcontext(session) if session is not None else session_scope()
    with cm as session:
        # Validate recipe exists
        recipe = session.query(Recipe).filter_by(id=recipe_id).first()
        if not recipe:
            raise RecipeNotFoundError(recipe_id)

        # ... validation steps ...

        # Create recipe snapshot - PASSES SESSION
        snapshot = recipe_snapshot_service.create_snapshot(
            recipe_id, scale_factor=scale_factor, session=session
        )

        # Get aggregated ingredients - PASSES SESSION
        aggregated = get_aggregated_ingredients(
            recipe_id, multiplier=1, session=session
        )

        # Consume inventory via FIFO - PASSES SESSION
        for item in aggregated:
            result = inventory_item_service.consume_fifo(
                item["ingredient"].slug,
                quantity_needed,
                item["unit"],
                dry_run=False,
                session=session,  # CRITICAL: Pass session for atomicity
            )

        # Update finished goods inventory - PASSES SESSION
        fg_inv.adjust_inventory(
            finished_unit_id=finished_unit_id,
            adjustment=actual_yield,
            session=session,  # CRITICAL: Pass session for atomicity
        )

        # Create production run record
        production_run = ProductionRun(...)
        session.add(production_run)
        session.flush()

        return {...}
```

**Why This Pattern Matters**:

The `record_batch_production` function demonstrates the critical multi-step atomic pattern because:

1. **Inventory consumption must match production recording** - If we consume ingredients but fail to record the production run, inventory becomes inaccurate.

2. **Finished goods count must update atomically** - If we record consumption but fail to increment finished goods, we've "lost" the produced units.

3. **All or nothing** - A partial failure (e.g., one ingredient depleted mid-consumption) rolls back everything, leaving the database consistent.

---

## Session Parameter Pattern

### Why Every Service Function Accepts `session=None`

The session parameter pattern enables **transactional composition** - the ability to combine multiple service operations into a single atomic transaction.

**Key insight**: The caller decides transaction boundaries, not the callee.

### When to Pass Session

**Pass session when**:
- Composing multiple operations that must succeed together
- Calling a service function from within another service function
- Building complex business transactions
- Consistency across multiple reads matters

**Example** (composing operations):
```python
def complex_business_operation(data):
    with session_scope() as session:
        # These three operations are now atomic
        ingredient = create_ingredient(data["ingredient"], session=session)
        product = create_product(ingredient.slug, data["product"], session=session)
        purchase = record_purchase(product.id, data["purchase"], session=session)
        return {"ingredient": ingredient, "product": product, "purchase": purchase}
```

### When to Omit Session

**Omit session when**:
- Making standalone calls from UI handlers
- Operations are truly independent
- Testing individual service functions
- Simple CRUD operations from the UI layer

**Example** (standalone call from UI):
```python
# In a UI event handler - standalone call
def on_create_ingredient_clicked():
    ingredient = create_ingredient(form_data)  # No session needed
    show_success(f"Created {ingredient.display_name}")
```

### Desktop vs Web Usage

**Desktop Application (Current)**:
- UI handlers make standalone service calls
- No explicit transaction management in UI layer
- `session_scope()` manages transaction lifecycle
- Simple and straightforward

**Web Application (Future)**:
- Request handlers may compose operations
- Session parameter enables request-scoped transactions
- Same service functions work without modification
- Transaction boundaries controlled by API layer

### The Implementation Pattern

```python
def service_function(arg1, arg2, session=None):
    """Function that works standalone or composed."""

    def _impl(sess):
        # All business logic here
        result = sess.query(Model).filter_by(x=arg1).first()
        # ... operations using sess ...
        return result

    # Session decision point
    if session is not None:
        return _impl(session)
    with session_scope() as sess:
        return _impl(sess)
```

**Alternative pattern using `nullcontext`** (preferred for complex functions):
```python
from contextlib import nullcontext

def service_function(arg1, arg2, session=None):
    """Function with nullcontext pattern."""
    cm = nullcontext(session) if session is not None else session_scope()
    with cm as session:
        # Business logic directly here
        result = session.query(Model).filter_by(x=arg1).first()
        # ... operations using session ...
        return result
```

### Benefits

1. **Flexibility**: Same function works standalone or composed
2. **Atomicity**: Callers control transaction boundaries
3. **Testability**: Tests can pass mock sessions
4. **Consistency**: Uniform pattern across all services
5. **Future-proof**: Ready for web migration without code changes

---

## Common Pitfalls

### Pitfall 1: Multiple `session_scope()` Calls

**The Problem**: Calling multiple service functions without passing a session creates independent transactions that can leave data inconsistent.

**WRONG** (non-atomic):
```python
def record_production_wrong(recipe_id, quantity):
    # Each call has its own session - NOT ATOMIC!
    # If consume_inventory fails, production_run is still created
    production_run = create_production_run(recipe_id, quantity)  # Session 1
    consume_inventory(recipe_id, quantity)  # Session 2 - if this fails, run exists
    update_finished_goods(recipe_id, quantity)  # Session 3 - inconsistent state
```

**CORRECT** (atomic):
```python
def record_production_correct(recipe_id, quantity, session=None):
    cm = nullcontext(session) if session is not None else session_scope()
    with cm as session:
        # All operations in single session - ATOMIC
        production_run = create_production_run(recipe_id, quantity, session=session)
        consume_inventory(recipe_id, quantity, session=session)
        update_finished_goods(recipe_id, quantity, session=session)
        # If any fails, ALL roll back
```

---

### Pitfall 2: Forgetting to Pass Session

**The Problem**: When composing operations, forgetting to pass the session creates a nested session that detaches objects.

**WRONG** (session not passed):
```python
def outer_function():
    with session_scope() as session:
        obj = session.query(Model).first()
        inner_function()  # WRONG: Creates new session, detaches obj
        obj.field = value  # THIS CHANGE IS SILENTLY LOST!
```

**CORRECT** (session passed):
```python
def outer_function():
    with session_scope() as session:
        obj = session.query(Model).first()
        inner_function(session=session)  # RIGHT: Uses same session
        obj.field = value  # Change persists correctly
```

**How to spot this bug**: Look for any service call inside a `with session_scope()` block that doesn't include `session=session`.

---

### Pitfall 3: Assuming Implicit Transactions

**The Problem**: Assuming that related operations are automatically transactional because they're "close together" in code.

**WRONG** (assuming implicit transaction):
```python
def update_with_validation(slug, data):
    # These are two separate transactions!
    ingredient = get_ingredient(slug)  # Transaction 1
    # Between these calls, another process could modify ingredient
    ingredient.name = data["name"]  # This is a DETACHED object!
    # No save happens - change is lost
```

**CORRECT** (explicit transaction):
```python
def update_with_validation(slug, data, session=None):
    def _impl(sess):
        # Single transaction - object stays attached
        ingredient = get_ingredient(slug, session=sess)
        ingredient.name = data["name"]
        sess.flush()  # Explicit save
        return ingredient

    if session is not None:
        return _impl(session)
    with session_scope() as sess:
        return _impl(sess)
```

---

### Pitfall 4: Detached Object Modification

**The Problem**: Objects become detached when their session scope exits. Modifying detached objects has no effect.

**WRONG** (detached object):
```python
def get_and_modify_wrong(slug):
    with session_scope() as session:
        obj = session.query(Model).filter_by(slug=slug).first()
    # Session closed - obj is DETACHED
    obj.field = "new value"  # NO EFFECT - not tracked by any session
    return obj  # Returned with old value
```

**CORRECT** (keep object attached):
```python
def get_and_modify_correct(slug, new_value, session=None):
    def _impl(sess):
        obj = sess.query(Model).filter_by(slug=slug).first()
        obj.field = new_value  # Object still attached
        sess.flush()  # Changes persisted
        return obj

    if session is not None:
        return _impl(session)
    with session_scope() as sess:
        return _impl(sess)
```

**Alternative**: Return IDs or DTOs instead of ORM objects if they'll be used outside the session.

---

## Code Review Checklist

When reviewing service functions, verify:

### Transaction Boundary Documentation
- [ ] Function has "Transaction boundary:" section in docstring
- [ ] Atomicity guarantee explicitly stated
- [ ] Steps listed for multi-step operations
- [ ] Session parameter usage documented

### Session Parameter Pattern
- [ ] Function accepts `session: Optional[Session] = None`
- [ ] Implements `if session is not None:` / `with session_scope()` pattern
- [ ] Or uses `nullcontext` pattern for complex functions

### Multi-Step Operation Safety
- [ ] All nested service calls include `session=session`
- [ ] No `session_scope()` created inside another `session_scope()`
- [ ] Transactional steps documented in docstring
- [ ] Rollback behavior clear from documentation

### Return Value Safety
- [ ] ORM objects not returned from closed sessions
- [ ] Or objects returned only for immediate read use
- [ ] Or IDs/DTOs returned for cross-session use

---

## Reference Documents

- **CLAUDE.md**: Session Management section - critical rules for service functions
- **Constitution**: Principle VI.C.2 - Transaction Boundaries
- **Func-spec F091**: Transaction Boundary Documentation specification
- **Atomicity Audit**: `kitty-specs/091-transaction-boundary-documentation/research/atomicity_audit.md`

---

## Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-03 | Initial version created per F091 WP10 |
