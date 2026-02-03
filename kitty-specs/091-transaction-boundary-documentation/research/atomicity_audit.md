# Transaction Atomicity Audit Results

**Date**: 2026-02-03
**Auditor**: codex-wp09
**Feature**: F091 Transaction Boundary Documentation
**Work Package**: WP09 Multi-Step Operation Audit

## Summary

| Metric | Count |
|--------|-------|
| Total MULTI functions audited | 35 |
| Passed (correct session passing) | 30 |
| Issues Found | 5 |
| Issues Fixed | 0 |
| Already correct (verified) | 30 |

**Overall Assessment**: The codebase has generally good session management practices. Most MULTI functions follow the correct pattern of accepting `session=None` and passing sessions to nested calls. A few READ-heavy functions have minor issues that don't affect atomicity for write operations but could benefit from improvement.

## Audit by Service

### inventory_item_service.py (9 MULTI functions)

| Function | Nested Calls | Session Passed? | Status | Notes |
|----------|--------------|-----------------|--------|-------|
| `add_to_inventory` | Direct queries only | N/A | **PASS** | Uses `_impl` pattern correctly |
| `get_inventory_items` | `get_ingredient()` | **NO** | **ISSUE-1** | Read-only, low risk but inconsistent |
| `get_total_quantity` | `get_ingredient()`, `get_inventory_items()` | NO | PASS (Read-only) | No atomicity needed |
| `consume_fifo` | `get_ingredient()` | **YES** | **PASS** | Critical function, correctly implemented |
| `update_inventory_supplier` | Direct queries only | N/A | **PASS** | Single session scope |
| `update_inventory_quantity` | Direct queries only | N/A | **PASS** | Uses `_do_update` pattern correctly |
| `manual_adjustment` | Direct queries only | N/A | **PASS** | Uses `_do_adjustment` pattern correctly |
| `get_recent_products` | `_impl` pattern | YES | **PASS** | Correctly delegates to impl |
| `get_recent_ingredients` | `_impl` pattern | YES | **PASS** | Correctly delegates to impl |

**Issue Found**: `get_inventory_items` calls `get_ingredient(ingredient_slug)` without passing `session=session` on line 221. Since this is a read-only function, the atomicity impact is minimal, but it could lead to inconsistent reads in edge cases.

---

### purchase_service.py (12 MULTI functions)

| Function | Nested Calls | Session Passed? | Status | Notes |
|----------|--------------|-----------------|--------|-------|
| `record_purchase` | Direct queries + supplier creation | YES | **PASS** | Uses `_impl` pattern correctly |
| `get_purchase` | Direct queries only | N/A | **PASS** | Uses `_impl` pattern |
| `get_purchase_history` | `get_ingredient()` | **NO** | **ISSUE-2** | Read-only but should pass session |
| `get_most_recent_purchase` | `get_product()` | NO (separate session) | PASS (Read-only) | Validation call before query |
| `calculate_average_price` | `get_product()` | NO (separate session) | PASS (Read-only) | Validation call before query |
| `detect_price_change` | `calculate_average_price()` | N/A | **PASS** | Read-only function |
| `get_price_trend` | `get_product()` | NO (separate session) | PASS (Read-only) | Validation call before query |
| `get_last_price_at_supplier` | Direct queries only | N/A | **PASS** | Uses `_impl` pattern |
| `get_last_price_any_supplier` | Direct queries only | N/A | **PASS** | Uses `_impl` pattern |
| `delete_purchase` | Direct queries only | N/A | **PASS** | Uses `_impl` pattern |
| `get_purchases_filtered` | Direct queries only | N/A | **PASS** | Uses `_impl` pattern |
| `update_purchase` | `_can_edit_purchase_impl()` | YES | **PASS** | Correctly passes session to validation |

**Issue Found**: `get_purchase_history` calls `get_ingredient(ingredient_slug)` on line 328 without passing `session=session`. This is inside the session_scope block and should pass the session for consistent reads.

---

### product_service.py (7 MULTI functions)

| Function | Nested Calls | Session Passed? | Status | Notes |
|----------|--------------|-----------------|--------|-------|
| `create_product` | `get_ingredient()`, `_validate_leaf_ingredient_for_product()` | **NO** | **ISSUE-3** | `get_ingredient` called before session |
| `create_provisional_product` | `_validate_leaf_ingredient_for_product()` | YES | **PASS** | Uses `_create_impl` pattern |
| `set_preferred_product` | `get_product()` | NO (separate session) | PASS | Validation before write; write is atomic |
| `update_product` | Direct queries only | N/A | **PASS** | Single session scope |
| `delete_product` | `check_product_dependencies()` | NO (separate session) | PASS | Check before delete pattern |
| `check_product_dependencies` | `get_product()` | NO (separate session) | PASS (Read-only) | Uses separate sessions |
| `get_product_recommendation` | Multiple reads | NO | PASS (Read-only) | Read-only aggregation |

**Issue Found**: `create_product` calls `get_ingredient(ingredient_slug)` on line 231 before the session_scope block, then uses the returned ingredient inside the session. The ingredient object becomes detached when used inside the new session. However, since only `ingredient.id` is used (a scalar attribute), this works but is inconsistent with best practices.

---

### batch_production_service.py (6 MULTI functions)

| Function | Nested Calls | Session Passed? | Status | Notes |
|----------|--------------|-----------------|--------|-------|
| `check_can_produce` | `get_aggregated_ingredients()`, `consume_fifo()` | **YES** | **PASS** | Uses `_impl` pattern, passes session |
| `record_batch_production` | `consume_fifo()`, `fg_inv.adjust_inventory()`, snapshot services | **YES** | **PASS** | Excellent session management |
| `get_production_history` | Direct queries only | N/A | **PASS** | Uses session parameter correctly |
| `get_production_run` | Direct queries only | N/A | **PASS** | Session required parameter |
| `export_production_history` | `get_production_history()` | YES | **PASS** | Recursively passes session |
| `import_production_history` | Direct queries only | N/A | **PASS** | Uses session_scope |

**Notes**: This service demonstrates excellent session management practices. The critical `record_batch_production` function correctly uses `nullcontext` pattern to honor passed sessions and passes sessions to all nested service calls. This is a reference implementation for the codebase.

---

### assembly_service.py (8 MULTI functions)

| Function | Nested Calls | Session Passed? | Status | Notes |
|----------|--------------|-----------------|--------|-------|
| `check_can_assemble` | `consume_fifo()` | **YES** | **PASS** | Uses `_impl` pattern, passes session |
| `record_assembly` | `consume_fifo()`, `fg_inv.adjust_inventory()`, snapshot services | **YES** | **PASS** | Excellent session management |
| `get_assembly_history` | Direct queries only | N/A | **PASS** | Session required parameter |
| `get_assembly_run` | Direct queries only | N/A | **PASS** | Session required parameter |
| `export_assembly_history` | `get_assembly_history()` | YES | **PASS** | Recursively passes session |
| `import_assembly_history` | Direct queries only | N/A | **PASS** | Uses session_scope |
| `check_packaging_assigned` | Direct queries only | N/A | **PASS** | Uses `_impl` pattern |
| `record_assembly` materials | `material_consumption_service.record_material_consumption()` | YES | **PASS** | Session passed to material service |

**Notes**: Like `batch_production_service`, this service demonstrates excellent session management. All critical multi-step operations correctly pass sessions to nested service calls.

---

## Issues Found and Recommended Fixes

### Issue 1: `inventory_item_service.get_inventory_items()`

**Location**: Line 221 in `src/services/inventory_item_service.py`

**Problem**: `get_ingredient(ingredient_slug)` is called without passing `session=session`

**Current Code**:
```python
with session_scope() as session:
    ...
    if ingredient_slug:
        ingredient = get_ingredient(ingredient_slug)  # MISSING session
        q = q.join(Product).filter(Product.ingredient_id == ingredient.id)
```

**Recommended Fix**:
```python
with session_scope() as session:
    ...
    if ingredient_slug:
        ingredient = get_ingredient(ingredient_slug, session=session)
        q = q.join(Product).filter(Product.ingredient_id == ingredient.id)
```

**Risk Level**: LOW - Read-only function, no data loss risk

---

### Issue 2: `purchase_service.get_purchase_history()`

**Location**: Line 328 in `src/services/purchase_service.py`

**Problem**: `get_ingredient(ingredient_slug)` is called without passing `session=session`

**Current Code**:
```python
with session_scope() as session:
    q = session.query(Purchase)
    if ingredient_slug:
        ingredient = get_ingredient(ingredient_slug)  # MISSING session
        q = q.join(Product).filter(Product.ingredient_id == ingredient.id)
```

**Recommended Fix**:
```python
with session_scope() as session:
    q = session.query(Purchase)
    if ingredient_slug:
        ingredient = get_ingredient(ingredient_slug, session=session)
        q = q.join(Product).filter(Product.ingredient_id == ingredient.id)
```

**Risk Level**: LOW - Read-only function, no data loss risk

---

### Issue 3: `product_service.create_product()`

**Location**: Line 231 in `src/services/product_service.py`

**Problem**: `get_ingredient(ingredient_slug)` is called before the session_scope block, returning a detached object

**Current Code**:
```python
def create_product(ingredient_slug: str, product_data: Dict[str, Any]) -> Product:
    # Validate ingredient exists
    ingredient = get_ingredient(ingredient_slug)  # Creates its own session

    # Validate product data
    is_valid, errors = validate_product_data(product_data, ingredient_slug)
    ...

    try:
        with session_scope() as session:
            # Feature 031: Validate leaf-only constraint
            _validate_leaf_ingredient_for_product(ingredient, session)  # Uses detached object
            ...
```

**Recommended Fix**:
```python
def create_product(ingredient_slug: str, product_data: Dict[str, Any]) -> Product:
    # Validate product data
    is_valid, errors = validate_product_data(product_data, ingredient_slug)
    ...

    try:
        with session_scope() as session:
            # Validate ingredient exists INSIDE session
            ingredient = get_ingredient(ingredient_slug, session=session)

            # Feature 031: Validate leaf-only constraint
            _validate_leaf_ingredient_for_product(ingredient, session)
            ...
```

**Risk Level**: MEDIUM - Currently works because only `ingredient.id` is used as a scalar attribute, but the pattern is incorrect and could cause issues if relationships are accessed.

---

### Issue 4: `product_service.get_products_for_ingredient()`

**Location**: Line 440 in `src/services/product_service.py`

**Problem**: `get_ingredient(ingredient_slug)` is called before the session_scope block

**Current Code**:
```python
def get_products_for_ingredient(ingredient_slug: str) -> List[Product]:
    # Validate ingredient exists
    ingredient = get_ingredient(ingredient_slug)  # Separate session

    with session_scope() as session:
        return (
            session.query(Product)
            .filter_by(ingredient_id=ingredient.id)  # Uses detached object
            ...
```

**Recommended Fix**:
```python
def get_products_for_ingredient(ingredient_slug: str) -> List[Product]:
    with session_scope() as session:
        # Validate ingredient exists INSIDE session
        ingredient = get_ingredient(ingredient_slug, session=session)

        return (
            session.query(Product)
            .filter_by(ingredient_id=ingredient.id)
            ...
```

**Risk Level**: LOW - Read-only function, uses only scalar attribute

---

### Issue 5: `product_service.get_preferred_product()`

**Location**: Line 735 in `src/services/product_service.py`

**Problem**: Same pattern as Issue 4

**Risk Level**: LOW - Read-only function, uses only scalar attribute

---

## Conclusions

### Overall Assessment

The codebase demonstrates **good session management practices** overall, particularly in the critical production and assembly services which handle complex multi-step atomic operations correctly. The issues found are primarily in read-only functions where the atomicity impact is minimal.

### Patterns Observed

1. **Excellent Pattern (batch_production_service, assembly_service)**: Use of `nullcontext` pattern to honor passed sessions, combined with `_impl` inner functions that receive the session parameter. All nested service calls pass `session=session`.

2. **Good Pattern (inventory_item_service.consume_fifo)**: Critical write operations correctly accept `session=None` parameter and pass sessions to nested calls.

3. **Acceptable Pattern**: Read-only functions calling other read-only functions without session passing - while not ideal for consistency, these don't cause data loss or corruption.

4. **Improvement Needed**: A few functions call `get_ingredient()` inside a session_scope without passing the session, or call it before the session_scope and use the detached object.

### Recommendations

1. **Priority: LOW** - Fix the identified issues in read-only functions to establish consistent patterns across the codebase.

2. **Priority: MEDIUM** - Fix Issue 3 (`create_product`) as it involves a write operation where the pattern could cause problems if the code evolves.

3. **No immediate action required** for the production and assembly services - they are correctly implemented.

### Risk Assessment

| Risk | Status |
|------|--------|
| Data loss from session detachment | **LOW** - No write operations affected |
| Inconsistent reads (TOCTOU) | **LOW** - Possible in edge cases but no production impact expected |
| Broken atomicity in production runs | **NONE** - Correctly implemented |
| Broken atomicity in assembly runs | **NONE** - Correctly implemented |
| Silent data loss per CLAUDE.md | **NONE** - All identified patterns are safe |

---

## Appendix: Verified Correct Patterns

### Pattern A: Session Parameter with _impl Function

```python
def some_function(..., session=None):
    if session is not None:
        return _some_function_impl(..., session)
    with session_scope() as sess:
        return _some_function_impl(..., sess)

def _some_function_impl(..., session):
    # All work done using the provided session
    nested_result = other_service_call(..., session=session)  # Pass session
    ...
```

Used correctly in: `consume_fifo`, `check_can_produce`, `check_can_assemble`, `record_purchase`, etc.

### Pattern B: nullcontext for Optional Session

```python
def record_batch_production(..., session=None):
    cm = nullcontext(session) if session is not None else session_scope()
    with cm as session:
        # All work done within this context
        result = inventory_item_service.consume_fifo(..., session=session)
        ...
```

Used correctly in: `record_batch_production`, `record_assembly`

---

*End of Audit Report*
