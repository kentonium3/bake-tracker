# TD-010: Purchase Service Bypasses Service Boundaries

**Created**: 2026-01-17
**Status**: Open
**Priority**: Low
**Related Features**: F057 (Provisional Products), F027 (Product Catalog, Suppliers)
**Impact**: Service architecture, maintainability, data consistency
**Discovered During**: F057 code review (Cursor)

---

## Problem Statement

The `purchase_service.record_purchase()` function directly queries models and creates records inline instead of delegating to the appropriate services. This violates the layered architecture's service boundary requirements.

**Spec References**:
- F057 FR-020: "Purchase service MUST delegate product lookup to product_catalog_service"
- F057 FR-023: "Purchase service MUST delegate supplier lookup/creation to supplier_service"

---

## Current Behavior

### Issue 1: Direct Product Query

```python
# src/services/purchase_service.py, lines 143-145
def _record_purchase_impl(...):
    product = session.query(Product).filter_by(id=product_id).first()
    if not product:
        raise ProductNotFound(product_id)
```

Should delegate to `product_catalog_service.get_product()`.

### Issue 2: Inline Supplier Creation

```python
# src/services/purchase_service.py, lines 159-171
def _record_purchase_impl(...):
    store_name = store if store else "Unknown"
    supplier = session.query(Supplier).filter(Supplier.name == store_name).first()
    if not supplier:
        supplier = Supplier(
            name=store_name,
            city="Unknown",
            state="XX",
            zip_code="00000",
        )
        session.add(supplier)
        session.flush()
```

Should delegate to `supplier_service.get_or_create_supplier()`.

---

## Why This Matters

1. **Cross-cutting concerns bypassed**: Audit logging, caching, soft-delete filtering, or provisional product handling in the catalog service won't apply to purchases.

2. **Duplicated logic**: Supplier creation with hardcoded placeholders (`city="Unknown"`, `state="XX"`) is defined inline rather than centralized.

3. **Validation bypass**: Any validation rules added to product_catalog_service or supplier_service won't apply to this code path.

4. **Slug support (TD-009)**: When supplier slugs are added, inline supplier creation won't generate them.

5. **Name-only supplier matching**: Looks up supplier by name alone, ignoring city/state (could match wrong supplier if same store name exists in multiple locations).

---

## Proposed Solution

### Step 1: Ensure Services Accept Session Parameter

Verify `product_catalog_service.get_product()` accepts `session` parameter. Add `get_or_create_supplier()` to `supplier_service`:

```python
# supplier_service.py
def get_or_create_supplier(
    name: str,
    city: str = "Unknown",
    state: str = "XX",
    zip_code: str = "00000",
    session: Optional[Session] = None,
) -> Supplier:
    """Get existing supplier by name or create with provided defaults."""
    # Implementation with session handling pattern
```

### Step 2: Update Purchase Service

```python
# purchase_service.py
from src.services import product_catalog_service, supplier_service

def _record_purchase_impl(...):
    # Delegate product lookup
    product = product_catalog_service.get_product(product_id, session=session)

    # Delegate supplier lookup/creation
    store_name = store if store else "Unknown"
    supplier = supplier_service.get_or_create_supplier(
        name=store_name,
        session=session,
    )
```

---

## Impact Analysis

### Files Affected

| File | Change |
|------|--------|
| `src/services/supplier_service.py` | Add `get_or_create_supplier()` |
| `src/services/purchase_service.py` | Replace direct queries with service calls |
| `src/tests/services/test_supplier_service.py` | Add tests for new function |

### Risk Assessment

- **Low risk**: Straightforward refactoring with clear equivalence
- **Session handling**: Must pass session for transactional integrity
- **Behavior preservation**: Default values match current behavior

---

## Effort Estimate

| Task | Effort |
|------|--------|
| Add get_or_create_supplier to supplier_service | 30-45 min |
| Update purchase_service.py (both issues) | 30 min |
| Add/update tests | 45 min |
| Integration testing | 30 min |
| **Total** | **2.5-3 hours** |

---

## Recommendation

**Priority: Low** - Address alongside TD-009 (supplier slugs) since `get_or_create_supplier()` should include slug generation.

**Rationale:**
- Current code works correctly
- Impact is architectural/maintainability, not functional
- Natural pairing with TD-009 for efficiency
- Pre-existing debt, not introduced by F057

---

## Related Technical Debt

- **TD-009**: Supplier slug support - `get_or_create_supplier()` should generate slugs when implemented

---

**END OF TECHNICAL DEBT DOCUMENT**
