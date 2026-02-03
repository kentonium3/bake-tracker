# F092: Service Boundary Compliance - Purchase Service

**Version**: 1.0
**Priority**: HIGH
**Type**: Architecture Compliance + Code Quality
**Estimated Effort**: 2.5-3 hours

---

## Executive Summary

The `purchase_service.record_purchase()` function violates service boundary principles by directly querying models and creating entities inline instead of delegating to the appropriate services.

Current violations:
- ❌ Direct `Product` model queries (bypasses `product_catalog_service`)
- ❌ Inline `Supplier` creation (bypasses `supplier_service`)
- ❌ No service delegation for entity lookup/creation
- ❌ Hardcoded placeholder values scattered in code

This spec fixes these violations by implementing proper service delegation, ensuring the purchase service follows the documented transaction boundary patterns (F091) and prepares for API standardization (F094).

**Related:**
- F091: Transaction Boundary Documentation (documents the patterns)
- F094: Core API Standardization (exception handling, type hints)
- TD-009: Supplier slug support (deferred - will use `get_or_create_supplier()`)

---

## Problem Statement

**Current State (Service Boundary Violations):**
```
purchase_service.record_purchase()
├─ ❌ Queries Product model directly
│  └─ Bypasses product_catalog_service validation/logic
├─ ❌ Queries/creates Supplier inline
│  └─ Bypasses supplier_service (no slug generation, no validation)
├─ ❌ Hardcoded defaults ("Unknown", "XX", "00000")
│  └─ Should be centralized in supplier_service
└─ ❌ Name-only supplier lookup
   └─ Could match wrong supplier (same name, different city)

Impact
├─ 🐛 Cross-cutting concerns bypassed (audit, cache, provisional)
├─ 🐛 Validation rules bypassed
├─ 🐛 No slug generation for suppliers (when TD-009 implemented)
└─ 📝 Duplicated logic (supplier creation)
```

**Target State (Proper Service Delegation):**
```
purchase_service.record_purchase()
├─ ✅ Delegates to product_catalog_service.get_product()
│  └─ Benefits from service validation/logic
├─ ✅ Delegates to supplier_service.get_or_create_supplier()
│  └─ Centralized supplier creation logic
├─ ✅ Session parameter passed for composition
│  └─ Transaction atomicity guaranteed
└─ ✅ Clean separation of concerns
   └─ Each service owns its entity domain
```

---

## Architecture Principles

### Service Boundary Principle

**Services must delegate entity operations to the owning service:**
- Product operations → `product_catalog_service`
- Supplier operations → `supplier_service`
- Purchase operations → `purchase_service` (coordinates only)

**Never:**
- ❌ Query models directly from coordinating services
- ❌ Create entities inline (bypasses validation)
- ❌ Duplicate entity creation logic

### Session Composition Pattern (F091)

**When service A calls service B within a transaction:**
```python
def service_a_operation(..., session: Optional[Session] = None):
    def _impl(sess: Session):
        # Call service B with same session
        entity = service_b.get_entity(..., session=sess)  # ✅ Pass session
        # Continue with transaction
        return result

    if session is not None:
        return _impl(session)
    with session_scope() as sess:
        return _impl(sess)
```

---

## Current Implementation Analysis

### Violation 1: Direct Product Query

**Location:** `src/services/purchase_service.py:143-145`

```python
# CURRENT (ANTI-PATTERN)
def _record_purchase_impl(purchase_data: dict, session: Session) -> Purchase:
    product_id = purchase_data["product_id"]

    # ❌ Direct model query
    product = session.query(Product).filter_by(id=product_id).first()
    if not product:
        raise ProductNotFound(product_id)
```

**Problems:**
- Bypasses `product_catalog_service` validation
- Provisional product logic (if any) won't apply
- Future product-level concerns won't apply to purchases

**Should be:**
```python
# CORRECT PATTERN
from src.services import product_catalog_service

def _record_purchase_impl(purchase_data: dict, session: Session) -> Purchase:
    product_id = purchase_data["product_id"]

    # ✅ Delegate to service
    product = product_catalog_service.get_product(product_id, session=session)
    # No need to check None - service raises ProductNotFound
```

---

### Violation 2: Inline Supplier Creation

**Location:** `src/services/purchase_service.py:159-171`

```python
# CURRENT (ANTI-PATTERN)
def _record_purchase_impl(purchase_data: dict, session: Session) -> Purchase:
    store = purchase_data.get("store")
    store_name = store if store else "Unknown"

    # ❌ Direct model query + inline creation
    supplier = session.query(Supplier).filter(Supplier.name == store_name).first()
    if not supplier:
        supplier = Supplier(
            name=store_name,
            city="Unknown",      # ❌ Hardcoded
            state="XX",          # ❌ Hardcoded
            zip_code="00000",    # ❌ Hardcoded
        )
        session.add(supplier)
        session.flush()
```

**Problems:**
- Bypasses `supplier_service` (which doesn't exist yet!)
- Hardcoded placeholder values scattered in code
- No slug generation (when TD-009 implemented)
- Name-only lookup could match wrong supplier
- Duplicates supplier creation logic

**Should be:**
```python
# CORRECT PATTERN
from src.services import supplier_service

def _record_purchase_impl(purchase_data: dict, session: Session) -> Purchase:
    store = purchase_data.get("store")
    store_name = store if store else "Unknown"

    # ✅ Delegate to service
    supplier = supplier_service.get_or_create_supplier(
        name=store_name,
        session=session
    )
    # Service handles defaults, slug generation, validation
```

---

## Functional Requirements

### FR-1: Delegate Product Lookup to Product Catalog Service

**What it must do:**
- Replace direct `Product` model query with `product_catalog_service.get_product()`
- Pass session parameter for transaction composition
- Rely on service to raise `ProductNotFound` (no manual check needed)

**Implementation:**

```python
# src/services/purchase_service.py
from src.services import product_catalog_service

def _record_purchase_impl(purchase_data: dict, session: Session) -> Purchase:
    """
    Record a purchase transaction.

    Transaction boundary: ALL operations in single session (atomic).
    Steps executed atomically:
    1. Validate product exists (delegates to product_catalog_service)
    2. Get or create supplier (delegates to supplier_service)
    3. Create purchase record
    4. Update product inventory (if applicable)

    Args:
        purchase_data: Purchase details
        session: Database session

    Returns:
        Purchase: Created purchase record

    Raises:
        ProductNotFound: If product_id invalid (from product_catalog_service)
        ValidationError: If purchase_data invalid
    """
    product_id = purchase_data["product_id"]

    # Delegate product lookup
    product = product_catalog_service.get_product(product_id, session=session)

    # ... rest of implementation
```

**Success criteria:**
- [ ] `purchase_service` imports `product_catalog_service`
- [ ] Direct `Product` query removed
- [ ] `session` parameter passed to service call
- [ ] Tests verify delegation works
- [ ] Exception handling preserved (ProductNotFound)

---

### FR-2: Create Supplier Service Get-or-Create Function

**What it must do:**
- Add `get_or_create_supplier()` to `supplier_service`
- Accept optional session parameter for composition
- Centralize default values ("Unknown" city, "XX" state, etc.)
- Support future slug generation (TD-009)

**Implementation:**

```python
# src/services/supplier_service.py
from typing import Optional
from sqlalchemy.orm import Session
from src.models.supplier import Supplier
from src.services.database import session_scope

def get_or_create_supplier(
    name: str,
    city: str = "Unknown",
    state: str = "XX",
    zip_code: str = "00000",
    session: Optional[Session] = None,
) -> Supplier:
    """
    Get existing supplier by name or create with provided defaults.

    Transaction boundary: Single query + possible insert (atomic).

    Args:
        name: Supplier name
        city: City (default: "Unknown")
        state: State code (default: "XX")
        zip_code: ZIP code (default: "00000")
        session: Optional session for transactional composition

    Returns:
        Supplier: Existing or newly created supplier

    Notes:
        - Defaults match legacy purchase service behavior
        - Future: Will generate slug when TD-009 implemented
        - Lookup by name only (city/state not used for matching)
    """
    def _impl(sess: Session) -> Supplier:
        # Try to find existing supplier by name
        supplier = sess.query(Supplier).filter(
            Supplier.name == name
        ).first()

        if supplier:
            return supplier

        # Create new supplier with defaults
        supplier = Supplier(
            name=name,
            city=city,
            state=state,
            zip_code=zip_code,
            # Future: slug=create_slug_for_model(name, Supplier, sess)  # TD-009
        )
        sess.add(supplier)
        sess.flush()  # Get ID for return
        return supplier

    if session is not None:
        return _impl(session)
    with session_scope() as sess:
        return _impl(sess)
```

**Success criteria:**
- [ ] Function added to `supplier_service.py`
- [ ] Accepts optional `session` parameter
- [ ] Defaults match current purchase service behavior
- [ ] Returns existing supplier if name matches
- [ ] Creates new supplier if not found
- [ ] Comment notes future slug generation (TD-009)

---

### FR-3: Update Purchase Service to Delegate Supplier Operations

**What it must do:**
- Replace inline supplier query/creation with `supplier_service.get_or_create_supplier()`
- Pass session parameter for transaction composition
- Remove hardcoded defaults from purchase service

**Implementation:**

```python
# src/services/purchase_service.py
from src.services import product_catalog_service, supplier_service

def _record_purchase_impl(purchase_data: dict, session: Session) -> Purchase:
    """
    Record a purchase transaction.

    Transaction boundary: ALL operations in single session (atomic).
    Steps executed atomically:
    1. Validate product exists (delegates to product_catalog_service)
    2. Get or create supplier (delegates to supplier_service)
    3. Create purchase record
    4. Update product inventory (if applicable)

    CRITICAL: All service calls receive session parameter to ensure
    atomicity. Never create new session_scope() within this function.
    """
    product_id = purchase_data["product_id"]
    store = purchase_data.get("store")

    # FR-1: Delegate product lookup
    product = product_catalog_service.get_product(product_id, session=session)

    # FR-3: Delegate supplier get-or-create
    store_name = store if store else "Unknown"
    supplier = supplier_service.get_or_create_supplier(
        name=store_name,
        session=session
    )

    # Create purchase record (purchase service's core responsibility)
    purchase = Purchase(
        product_id=product.id,
        supplier_id=supplier.id,
        quantity=purchase_data["quantity"],
        unit_price=purchase_data.get("unit_price", 0.0),
        purchase_date=purchase_data.get("purchase_date"),
        # ... other fields
    )
    session.add(purchase)
    session.flush()

    # Update inventory if applicable
    # ...

    return purchase
```

**Success criteria:**
- [ ] `purchase_service` imports `supplier_service`
- [ ] Direct `Supplier` query removed
- [ ] Inline supplier creation removed
- [ ] Hardcoded defaults removed
- [ ] `session` parameter passed to service call
- [ ] Tests verify delegation works

---

## Out of Scope

**Explicitly NOT included:**

- ❌ **Supplier slug generation** — Deferred to TD-009
  - `get_or_create_supplier()` has comment noting future slug support
  - Will be added when TD-009 is implemented

- ❌ **Enhanced supplier matching** — Current name-only lookup preserved
  - Could match wrong supplier (same name, different city)
  - Acceptable for current use case
  - Can improve later if needed

- ❌ **Purchase service transaction optimization** — Only fixing boundaries
  - Other purchase service improvements are separate work
  - Focus is on service delegation, not purchase logic

- ❌ **Product catalog enhancements** — Using service as-is
  - Assumes `get_product()` exists and works
  - No changes to product catalog service

---

## Success Criteria

**Complete when:**

### Service Delegation
- [ ] `product_catalog_service.get_product()` used (no direct Product query)
- [ ] `supplier_service.get_or_create_supplier()` created and used
- [ ] No direct model queries in `purchase_service` (delegates to owning services)
- [ ] Session parameter passed to all service calls

### Transaction Integrity (F091)
- [ ] Transaction boundaries documented per F091 pattern
- [ ] Docstring explains atomicity guarantee
- [ ] All nested service calls receive session parameter
- [ ] No nested `session_scope()` calls

### Code Quality
- [ ] Hardcoded defaults removed from purchase service
- [ ] Supplier creation logic centralized in supplier service
- [ ] Service boundaries clear and documented
- [ ] Follows architecture principles (F091, Code Quality Principles)

### Testing
- [ ] Tests verify product delegation works
- [ ] Tests verify supplier get-or-create works
- [ ] Tests verify new supplier creation
- [ ] Tests verify existing supplier reuse
- [ ] Tests verify transaction atomicity
- [ ] Integration test for full purchase flow

---

## Files to Modify

### Primary Implementation

**1. `src/services/supplier_service.py`**
- Add `get_or_create_supplier()` function (~40 lines)
- Follow session parameter pattern (F091)
- Add docstring with transaction boundary

**2. `src/services/purchase_service.py`**
- Import `product_catalog_service` and `supplier_service`
- Replace direct `Product` query (lines ~143-145)
- Replace direct `Supplier` query/creation (lines ~159-171)
- Update docstring with transaction boundary (F091)
- Remove hardcoded defaults

### Testing

**3. `tests/services/test_supplier_service.py`** (if exists)
- Add `test_get_or_create_supplier_creates_new()`
- Add `test_get_or_create_supplier_returns_existing()`
- Add `test_get_or_create_supplier_with_custom_defaults()`
- Add `test_get_or_create_supplier_with_session()`

**4. `tests/services/test_purchase_service.py`**
- Update tests to verify service delegation
- Add test for product not found (from catalog service)
- Add test for new supplier creation (via supplier service)
- Add test for existing supplier reuse (via supplier service)

---

## Implementation Plan

### Phase 1: Add Supplier Service Function (30-45 min)
1. Create `get_or_create_supplier()` in `supplier_service.py`
2. Follow session parameter pattern from F091
3. Add docstring with transaction boundary
4. Add comment for future slug support (TD-009)

### Phase 2: Update Purchase Service (30 min)
1. Import `product_catalog_service` and `supplier_service`
2. Replace direct `Product` query with service call
3. Replace direct `Supplier` query/creation with service call
4. Update docstring per F091 pattern
5. Remove hardcoded defaults

### Phase 3: Testing (45 min)
1. Add unit tests for `get_or_create_supplier()`
2. Update purchase service tests
3. Verify delegation works
4. Verify transaction atomicity

### Phase 4: Integration Testing (30 min)
1. Test full purchase flow
2. Verify product not found handling
3. Verify supplier creation/reuse
4. Verify transaction rollback on errors

**Total: 2.5-3 hours**

---

## Risk Mitigation

### Risk: Breaking Existing Purchase Flow

**Problem:** Purchase service is core functionality

**Mitigation:**
- Preserve exact behavior (defaults match current values)
- Comprehensive testing before merge
- Service delegation is transparent to callers
- Rollback plan (revert commits)

### Risk: product_catalog_service.get_product() Missing Session Parameter

**Problem:** Service may not accept session parameter

**Mitigation:**
- Verify signature before implementation
- If missing, add session parameter (small change)
- Consistent with F091 patterns (all services should accept)

### Risk: Supplier Matching Logic Change

**Problem:** Name-only lookup might behave differently

**Mitigation:**
- `get_or_create_supplier()` uses same logic (name-only)
- Exact behavior preserved
- Future improvement can add city/state matching

---

## Relationship to Other Work

### F091: Transaction Boundary Documentation

**Provides the patterns this spec implements:**
- Session parameter composition pattern
- Transaction boundary docstring format
- Multi-step operation atomicity

**This spec:**
- Implements F091 patterns in purchase service
- Provides concrete example of service delegation
- Validates F091 patterns work in practice

### F094: Core API Standardization

**Will benefit from this refactor:**
- Exception handling already correct (ProductNotFound)
- Type hints will be added to new functions
- Service signatures will be consistent

**This spec:**
- Prepares purchase service for F094
- Establishes correct delegation pattern
- Removes direct queries (good practice)

### TD-009: Supplier Slug Support (Deferred)

**Future enhancement:**
- `get_or_create_supplier()` includes comment for slug generation
- When TD-009 implemented, add slug generation to this function
- No changes to purchase service needed (delegates to supplier service)

---

## Constitutional Compliance

✅ **Principle VI.C.1: Dependency Injection**
- "Pass dependencies explicitly rather than importing/instantiating within classes"
- Services passed via delegation, not direct model access

✅ **Principle VI.C.2: Transaction Boundaries**
- "Service methods define transaction scope"
- Purchase service maintains transaction, delegates to services with session

✅ **F091: Session Composition Pattern**
- "All nested service calls receive session parameter"
- Implements documented pattern

✅ **Layered Architecture (CLAUDE.md)**
- "Services -> Models -> Database"
- Purchase service coordinates, owning services handle entities

---

## Notes for Implementation

### Key Patterns to Follow

**1. Session Parameter Pattern (F091):**
```python
def service_function(..., session: Optional[Session] = None) -> ReturnType:
    def _impl(sess: Session) -> ReturnType:
        # Implementation here
        pass

    if session is not None:
        return _impl(session)
    with session_scope() as sess:
        return _impl(sess)
```

**2. Service Delegation Pattern:**
```python
# ✅ DO: Delegate to owning service
entity = owning_service.get_entity(id, session=session)

# ❌ DON'T: Query model directly
entity = session.query(Entity).filter_by(id=id).first()
```

**3. Transaction Boundary Docstring (F091):**
```python
"""
[Function description]

Transaction boundary: [Description]
Steps executed atomically:
1. [Step 1]
2. [Step 2]

CRITICAL: All nested service calls receive session parameter.
"""
```

### Verification Checklist

Before committing:
- [ ] No direct model queries in purchase service
- [ ] All service calls pass session parameter
- [ ] Docstrings follow F091 pattern
- [ ] Tests pass (unit + integration)
- [ ] Behavior preserved (defaults match)
- [ ] Code review confirms patterns

---

**END OF SPECIFICATION**
