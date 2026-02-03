# Transaction Boundary Docstring Templates

**Feature**: F091 - Transaction Boundary Documentation
**Created**: 2026-02-03
**Purpose**: Copy-paste templates for consistent transaction boundary documentation

## Overview

Every public service function should include a "Transaction boundary:" section in its docstring that documents:
1. Whether the function reads or writes data
2. Whether atomicity guarantees apply
3. How the session parameter affects behavior (if applicable)

## Pattern A: Read-Only Operation

Use for functions that only query data without modifications.

```python
def get_ingredient(slug: str, session=None) -> Ingredient:
    """Retrieve ingredient by slug.

    Transaction boundary: Read-only, no transaction needed.
    Safe to call without session - uses temporary session for query.
    If session provided, query executes within caller's transaction for
    consistent reads across multiple queries.

    Args:
        slug: Unique ingredient identifier (e.g., "all_purpose_flour")
        session: Optional database session for transactional composition

    Returns:
        Ingredient: Ingredient object

    Raises:
        IngredientNotFoundBySlug: If slug doesn't exist
    """
```

### Pattern A Variations

**Without session parameter:**
```python
def list_ingredients(category: Optional[str] = None) -> List[Ingredient]:
    """List all ingredients with optional filtering.

    Transaction boundary: Read-only, no transaction needed.
    Uses session_scope() internally for isolated query.

    Args:
        category: Optional category filter

    Returns:
        List[Ingredient]: Matching ingredients
    """
```

**Complex read with calculations:**
```python
def calculate_recipe_cost(recipe_id: int, session=None) -> Decimal:
    """Calculate total cost for a recipe.

    Transaction boundary: Read-only, no transaction needed.
    Performs multiple queries and aggregations but does not modify data.
    Pass session for consistent reads when called during production planning.

    Args:
        recipe_id: Recipe identifier
        session: Optional session for read consistency

    Returns:
        Decimal: Total calculated cost
    """
```

## Pattern B: Single-Step Write

Use for functions that perform ONE database write operation.

```python
def create_ingredient(ingredient_data: Dict[str, Any]) -> Ingredient:
    """Create a new ingredient with auto-generated slug.

    Transaction boundary: Single operation, automatically atomic.
    Uses session_scope() which commits on success or rolls back on error.
    No session parameter needed - standalone operation.

    Args:
        ingredient_data: Dictionary containing ingredient fields

    Returns:
        Ingredient: Created ingredient object with ID

    Raises:
        ValidationError: If required fields missing or invalid
        SlugAlreadyExists: If generated slug conflicts
        DatabaseError: If database operation fails
    """
```

### Pattern B Variations

**With session parameter for composition:**
```python
def update_inventory_quantity(
    inventory_item_id: int,
    new_quantity: Decimal,
    session: Optional[Session] = None,
) -> InventoryItem:
    """Update inventory item quantity.

    Transaction boundary: Single operation, automatically atomic.
    If session provided, caller controls transaction commit/rollback.
    If session not provided, uses session_scope() (auto-commit on success).

    Args:
        inventory_item_id: Inventory item identifier
        new_quantity: New quantity value
        session: Optional session for transactional composition

    Returns:
        InventoryItem: Updated inventory item

    Raises:
        InventoryItemNotFound: If item doesn't exist
        ValidationError: If quantity invalid
    """
```

**UPSERT operation:**
```python
def set_preference(key: str, value: Any) -> None:
    """Set a user preference (creates or updates).

    Transaction boundary: Single UPSERT operation, automatically atomic.
    Uses session_scope() internally with auto-commit.

    Args:
        key: Preference key
        value: Preference value (JSON-serializable)
    """
```

## Pattern C: Multi-Step Atomic Operation

Use for functions that perform multiple related operations that must succeed or fail together.

```python
def consume_fifo(
    ingredient_slug: str,
    quantity_needed: Decimal,
    target_unit: str,
    dry_run: bool = False,
    session=None,
) -> Dict[str, Any]:
    """Consume inventory using FIFO (First In, First Out) logic.

    Transaction boundary: ALL operations in single session (atomic).
    Atomicity guarantee: Either ALL lot updates succeed OR entire operation rolls back.
    Steps executed atomically:
    1. Query all lots for ingredient ordered by purchase_date (oldest first)
    2. Iterate through lots, consuming from each until quantity satisfied
    3. Convert between units as needed
    4. Update lot quantities
    5. Calculate total FIFO cost

    CRITICAL: All nested service calls receive session parameter to ensure
    atomicity. Never create new session_scope() within this function.

    When dry_run=True, simulates consumption without database modifications.
    Returns cost data for recipe costing calculations.

    Args:
        ingredient_slug: Ingredient to consume from
        quantity_needed: Amount to consume in target_unit
        target_unit: Unit for quantity_needed (from recipe)
        dry_run: If True, simulate only (no database changes)
        session: Optional session. If provided, caller owns transaction.

    Returns:
        Dict with keys:
            - consumed: Amount actually consumed
            - breakdown: Per-lot consumption details
            - shortfall: Amount not available (0 if satisfied)
            - satisfied: True if fully consumed
            - total_cost: FIFO cost of consumed inventory

    Raises:
        IngredientNotFoundBySlug: If ingredient doesn't exist
        DatabaseError: If database operation fails
    """
```

### Pattern C - Production Recording Example

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
    session=None,
) -> Dict[str, Any]:
    """Record a batch production run with FIFO consumption.

    Transaction boundary: ALL operations in single session (atomic).
    Atomicity guarantee: Either ALL steps succeed OR entire operation rolls back.
    Steps executed atomically:
    1. Validate recipe and finished unit exist
    2. Validate event exists (if provided)
    3. Create recipe snapshot
    4. Validate actual_yield <= expected_yield
    5. Consume ingredients via FIFO (calls consume_fifo with session)
    6. Increment FinishedUnit.inventory_count
    7. Create ProductionRun record
    8. Create ProductionLoss record (if loss occurred)
    9. Calculate per-unit cost

    CRITICAL: All nested service calls receive session parameter to ensure
    atomicity. The consume_fifo call MUST receive the session to prevent
    partial consumption on validation failures.

    If ANY step fails (validation, insufficient inventory, database error),
    the entire operation rolls back - no partial production is recorded,
    no inventory is consumed.

    Args:
        recipe_id: ID of recipe being produced
        finished_unit_id: ID of FinishedUnit being produced
        num_batches: Number of recipe batches made
        actual_yield: Actual units produced
        produced_at: Production timestamp (defaults to now)
        notes: Optional production notes
        event_id: Optional event ID to link production to
        session: Optional session. If provided, caller owns transaction.

    Returns:
        Dict with production details including costs and consumption ledger

    Raises:
        RecipeNotFoundError: If recipe doesn't exist
        FinishedUnitNotFoundError: If finished unit doesn't exist
        InsufficientInventoryError: If ingredients unavailable
        ActualYieldExceedsExpectedError: If actual > expected yield
    """
```

### Pattern C - Import/Export Example

```python
def import_all_data(data: dict, session: Optional[Session] = None) -> ImportResult:
    """Import complete data set from JSON.

    Transaction boundary: ALL operations in single session (atomic).
    Atomicity guarantee: Either ALL tables import successfully OR entire import rolls back.
    Steps executed atomically:
    1. Validate import data structure and version
    2. Clear existing data (if replace mode)
    3. Import each table in dependency order:
       - Categories, Units, Suppliers (no dependencies)
       - Ingredients (depends on categories)
       - Products (depends on ingredients, suppliers)
       - Recipes (depends on ingredients)
       - ... remaining tables
    4. Resolve foreign key references
    5. Validate referential integrity

    CRITICAL: All nested service calls receive session parameter to ensure
    atomicity. Never create new session_scope() within this function.
    Any validation failure in step 5 triggers complete rollback of all imports.

    Args:
        data: Complete JSON data structure to import
        session: Optional session for transactional composition

    Returns:
        ImportResult with counts and any warnings

    Raises:
        ValidationError: If data structure invalid
        ImportError: If referential integrity check fails
    """
```

## Session Parameter Pattern

### When to Accept session=None

Functions should accept `session=None` when:
1. They may be called from other service functions as part of a larger transaction
2. They perform database operations (read or write)
3. They need to maintain consistent reads across multiple queries

### Implementation Pattern

```python
def my_service_function(arg1, arg2, session=None):
    """Function description.

    Transaction boundary: [Pattern A/B/C description]

    Args:
        arg1: First argument
        arg2: Second argument
        session: Optional session for transactional composition

    Returns:
        [return description]
    """
    def _impl(sess):
        # Actual implementation using sess
        result = sess.query(Model).filter(...).first()
        # For MULTI operations, pass session to nested calls:
        # other_service.do_something(..., session=sess)
        return result

    # Session pattern: use provided session or create new one
    if session is not None:
        return _impl(session)
    with session_scope() as sess:
        return _impl(sess)
```

### When NOT to Add session Parameter

- Pure functions with no database access
- Functions that only call other services (no direct DB queries)
- Helper functions that are always called with a session

## Common Mistakes to Avoid

### Anti-Pattern 1: Multiple session_scope() Calls

```python
# WRONG - Creates separate transactions
def update_with_validation(id, data):
    # First transaction
    with session_scope() as session:
        item = session.query(Model).get(id)
        if not item:
            raise NotFoundError(id)

    # Second transaction - item is now DETACHED!
    with session_scope() as session:
        # This creates a NEW session, item modifications are LOST
        item.field = data['field']  # SILENT FAILURE
```

```python
# CORRECT - Single transaction
def update_with_validation(id, data, session=None):
    def _impl(sess):
        item = sess.query(Model).get(id)
        if not item:
            raise NotFoundError(id)
        item.field = data['field']  # Change tracked correctly
        return item

    if session is not None:
        return _impl(session)
    with session_scope() as sess:
        return _impl(sess)
```

### Anti-Pattern 2: Forgetting to Pass Session

```python
# WRONG - Nested call creates new transaction
def outer_function(session=None):
    def _impl(sess):
        obj = sess.query(Model).first()
        # WRONG: inner_function will use its own session
        result = inner_function(obj.id)  # Missing session parameter!
        obj.field = result  # May be detached, change lost
        return obj

    if session is not None:
        return _impl(session)
    with session_scope() as sess:
        return _impl(sess)
```

```python
# CORRECT - Pass session to maintain atomicity
def outer_function(session=None):
    def _impl(sess):
        obj = sess.query(Model).first()
        # CORRECT: Pass session to maintain same transaction
        result = inner_function(obj.id, session=sess)
        obj.field = result  # Same session, change tracked
        return obj

    if session is not None:
        return _impl(session)
    with session_scope() as sess:
        return _impl(sess)
```

### Anti-Pattern 3: Assuming Implicit Transactions

```python
# WRONG - No explicit transaction boundary documentation
def complex_operation(data):
    # Unclear what happens on failure
    create_record(data['main'])
    for item in data['items']:
        create_item(item)  # What if this fails?
```

```python
# CORRECT - Clear atomicity guarantee
def complex_operation(data, session=None):
    """Create record with items atomically.

    Transaction boundary: ALL operations in single session (atomic).
    Either all items are created or none are.
    """
    def _impl(sess):
        record = create_record(data['main'], session=sess)
        for item in data['items']:
            create_item(item, session=sess)
        return record

    if session is not None:
        return _impl(session)
    with session_scope() as sess:
        return _impl(sess)
```

## Quick Reference

| Pattern | Transaction boundary line | When to use |
|---------|--------------------------|-------------|
| A | `Transaction boundary: Read-only, no transaction needed.` | Queries only |
| B | `Transaction boundary: Single operation, automatically atomic.` | One INSERT/UPDATE/DELETE |
| C | `Transaction boundary: ALL operations in single session (atomic).` | Multiple related writes |
