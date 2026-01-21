# Session Ownership Pattern

**Version:** 1.0
**Date:** 2026-01-20
**Status:** ACTIVE
**Feature:** F060 - Architecture Hardening: Service Boundaries

---

## Problem Statement

### The Detached Object Issue

When service functions nest `session_scope()` calls, SQLAlchemy objects can become **detached** from their session. Detached objects are no longer tracked by any session, and modifications to them are silently ignored on commit.

### The Anti-Pattern

```python
# ANTI-PATTERN - DO NOT DO THIS
def outer_service_method():
    with session_scope() as session:
        # Query an object
        item = session.query(InventoryItem).first()
        original_qty = item.quantity  # 10.0

        # Inner service creates its own session
        inner_service_method()  # <-- Creates nested session_scope!

        # Modify the object (may be detached!)
        item.quantity -= 1.0
        # Commit happens, but change may be LOST

def inner_service_method():
    with session_scope() as session:  # <-- Problem: new session_scope
        # Does something
        pass  # Commits on exit, potentially detaching outer objects
```

**Why this fails:**
1. Inner `session_scope()` commits independently
2. Objects from outer session may become detached (depending on session factory config)
3. Even if not detached, the two sessions are separate transactions
4. No atomicity - inner commit is permanent even if outer fails

### Reference

See `docs/design/spec_session_management_remediation.md` for the original bug discovery and remediation history.

---

## The Session Ownership Pattern

All service methods that perform database operations MUST follow this pattern:

```python
from contextlib import nullcontext
from src.services.database import session_scope

def service_method(param1, param2, ..., session=None):
    """
    Perform a service operation.

    Args:
        param1: First parameter
        param2: Second parameter
        session: Optional SQLAlchemy session. If provided, all operations
                 use this session and caller controls commit/rollback.
                 If None, method manages its own transaction.

    Returns:
        Result of the operation
    """
    cm = nullcontext(session) if session is not None else session_scope()
    with cm as session:
        # All database operations use this session
        result = session.query(Model).filter(...).first()

        # Pass session to ALL downstream service calls
        downstream_result = other_service.method(..., session=session)

        # Modify objects
        result.field = new_value

        # NO explicit commit when session provided - caller controls transaction
        return result
```

---

## The Five Rules

### Rule 1: All Public Service Methods MUST Accept `session=None`

Every public method in the services layer that touches the database must have an optional session parameter:

```python
# CORRECT
def get_aggregated_ingredients(recipe_id: int, multiplier: float = 1.0, session=None):
    ...

# WRONG - missing session parameter
def get_aggregated_ingredients(recipe_id: int, multiplier: float = 1.0):
    ...
```

### Rule 2: Use Conditional Session Handling

Use the `nullcontext` pattern to handle both cases (session provided vs. not provided):

```python
# CORRECT - nullcontext pattern
cm = nullcontext(session) if session is not None else session_scope()
with cm as session:
    # Use session for all operations

# ALSO ACCEPTABLE - explicit if/else
if session is not None:
    return _impl(session)
with session_scope() as session:
    return _impl(session)
```

### Rule 3: Pass Session to ALL Downstream Calls

When calling other service functions within your transaction, ALWAYS pass the session:

```python
# CORRECT
def record_batch_production(recipe_id, ..., session=None):
    cm = nullcontext(session) if session is not None else session_scope()
    with cm as session:
        # Pass session to downstream services
        ingredients = recipe_service.get_aggregated_ingredients(recipe_id, session=session)
        consume_result = inventory_item_service.consume_fifo(..., session=session)

# WRONG - forgot to pass session
def record_batch_production(recipe_id, ..., session=None):
    cm = nullcontext(session) if session is not None else session_scope()
    with cm as session:
        ingredients = recipe_service.get_aggregated_ingredients(recipe_id)  # <-- Missing session!
```

### Rule 4: Do NOT Commit When Session Provided

When a caller provides a session, they control the transaction boundary. The service method must not commit:

```python
# The nullcontext pattern handles this automatically:
# - nullcontext(session) does NOT commit on exit
# - session_scope() DOES commit on exit

# WRONG - explicit commit when session provided
def some_method(..., session=None):
    cm = nullcontext(session) if session is not None else session_scope()
    with cm as session:
        session.add(obj)
        session.commit()  # <-- WRONG when session was provided!
```

### Rule 5: Backward Compatibility - Own Session When Not Provided

When no session is provided, the method manages its own transaction. This maintains backward compatibility with existing callers:

```python
# Both of these work:

# Standalone call - method manages own transaction
result = inventory_item_service.consume_fifo(slug, qty, unit)

# Shared session - caller controls transaction
with session_scope() as session:
    result1 = inventory_item_service.consume_fifo(slug, qty, unit, session=session)
    result2 = other_service.method(..., session=session)
    # All changes commit together at end of with block
```

---

## Good vs Bad Examples

### Example 1: Multi-Service Operation

**BAD** - No session passthrough, no atomicity:
```python
def process_order(order_id):
    with session_scope() as session:
        order = session.query(Order).get(order_id)

        # These create their own sessions - NOT atomic with order update!
        inventory_service.reserve_items(order.items)
        payment_service.charge_customer(order.customer_id, order.total)

        order.status = "processed"
```

**GOOD** - Session passthrough, full atomicity:
```python
def process_order(order_id, session=None):
    cm = nullcontext(session) if session is not None else session_scope()
    with cm as session:
        order = session.query(Order).get(order_id)

        # All operations share session - atomic!
        inventory_service.reserve_items(order.items, session=session)
        payment_service.charge_customer(order.customer_id, order.total, session=session)

        order.status = "processed"
        # If any operation fails, everything rolls back
```

### Example 2: Read-Then-Modify Operation

**BAD** - Object may become stale:
```python
def update_inventory(product_id, delta):
    with session_scope() as session:
        item = session.query(InventoryItem).filter_by(product_id=product_id).first()

        # Another function that uses session_scope
        log_change(product_id, delta)  # <-- Potential staleness!

        item.quantity += delta  # May be working with stale object
```

**GOOD** - Object stays tracked:
```python
def update_inventory(product_id, delta, session=None):
    cm = nullcontext(session) if session is not None else session_scope()
    with cm as session:
        item = session.query(InventoryItem).filter_by(product_id=product_id).first()

        # Pass session to maintain object tracking
        log_change(product_id, delta, session=session)

        item.quantity += delta  # Object guaranteed to be tracked
```

---

## Reference Implementation

The gold standard implementation is in `batch_production_service.py`:

**File:** `src/services/batch_production_service.py`
**Lines:** 279-281 (nullcontext pattern)

```python
def record_batch_production(
    recipe_id: int,
    finished_unit_id: int,
    num_batches: int,
    actual_yield: int,
    event_id: int = None,
    session=None,
) -> dict:
    """Record a batch production run with inventory consumption."""
    cm = nullcontext(session) if session is not None else session_scope()
    with cm as session:
        # All operations use same session...
        result = inventory_item_service.consume_fifo(
            ingredient_slug=ing["slug"],
            quantity_needed=qty_needed,
            target_unit=ing["unit"],
            dry_run=False,
            session=session,  # <-- Session passed downstream
        )
        # ... no explicit commit
```

---

## Testing Session Atomicity

Test infrastructure for verifying session atomicity is in:

**File:** `src/tests/services/test_session_atomicity.py`

Key test cases:
- `test_shared_session_sees_uncommitted_changes` - Verifies visibility within shared session
- `test_multi_service_rollback_on_failure` - Verifies rollback cascades to all changes
- `test_session_passthrough_to_downstream_services` - Verifies downstream services use shared session
- `test_nested_session_scope_independent_commits` - Documents the anti-pattern

---

## Compliant Services

The following services have been audited and confirmed compliant with this pattern (WP01, T003):

| Service | Methods | Status |
|---------|---------|--------|
| `batch_production_service.py` | `check_can_produce()`, `record_batch_production()` | COMPLIANT (Gold Standard) |
| `assembly_service.py` | `check_can_assemble()`, `record_assembly()` | COMPLIANT |
| `recipe_service.py` | `get_aggregated_ingredients()` | COMPLIANT |
| `ingredient_service.py` | `get_ingredient()` | COMPLIANT |
| `inventory_item_service.py` | `consume_fifo()` | COMPLIANT |

See `src/tests/services/test_session_atomicity.py` for the detailed audit results.

---

## Related Documents

- **Remediation History:** `docs/design/spec_session_management_remediation.md`
- **Architecture Overview:** `docs/design/architecture.md`
- **CLAUDE.md:** Session Management section
- **Test Infrastructure:** `src/tests/services/test_session_atomicity.py`
