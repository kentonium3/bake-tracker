# Implementation Plan: F092 Service Boundary Compliance

**Branch**: `092-service-boundary-compliance` | **Date**: 2026-02-03 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/kitty-specs/092-service-boundary-compliance/spec.md`

## Summary

Refactor `purchase_service.record_purchase()` to delegate Product and Supplier operations to their respective owning services (`product_service` and `supplier_service`), eliminating direct model queries and inline entity creation. This implements proper service boundary compliance following F091 transaction boundary patterns.

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: SQLAlchemy 2.x, CustomTkinter (UI - unaffected)
**Storage**: SQLite with WAL mode
**Testing**: pytest with session fixtures
**Target Platform**: Desktop (macOS/Windows/Linux)
**Project Type**: Single desktop application
**Performance Goals**: N/A (code quality refactor)
**Constraints**: Preserve exact behavior (backward compatible)
**Scale/Scope**: 3 service files modified, ~50 lines changed

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| VI.C.1: Dependency Injection | FIXING | Currently violated by direct model queries |
| VI.C.2: Transaction Boundaries | COMPLIANT | Will add session parameter per F091 |
| Layered Architecture | FIXING | Services will coordinate through proper delegation |
| F091: Session Composition | IMPLEMENTING | All nested calls will receive session parameter |

**Gate Status**: PASS (feature fixes existing violations)

## Project Structure

### Documentation (this feature)

```
kitty-specs/092-service-boundary-compliance/
├── spec.md              # Feature specification
├── plan.md              # This file
├── meta.json            # Feature metadata
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks/               # Work packages (created by /spec-kitty.tasks)
```

### Source Code (repository root)

```
src/
├── services/
│   ├── product_service.py      # Add session param to get_product()
│   ├── supplier_service.py     # Add get_or_create_supplier()
│   └── purchase_service.py     # Delegate to above services
└── tests/
    ├── test_purchase_service.py        # Update delegation tests
    └── services/
        └── test_supplier_service.py    # Add get_or_create tests
```

**Structure Decision**: Single project layout - backend services only modification, no UI changes.

---

## Current Implementation Analysis

### purchase_service._record_purchase_impl() (lines 141-244)

**Violation 1 - Direct Product Query (lines 158-161)**:
```python
# CURRENT (violates service boundary)
product = session.query(Product).filter_by(id=product_id).first()
if not product:
    raise ProductNotFound(product_id)
```

**Violation 2 - Inline Supplier Creation (lines 175-188)**:
```python
# CURRENT (violates service boundary)
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

### Service Interface Analysis

1. **product_service.get_product()** (line 406):
   - Returns `Product` model object
   - **Does NOT accept session parameter** - needs update
   - Uses own `session_scope()` internally
   - Raises `ProductNotFound` on missing

2. **supplier_service**:
   - Has comprehensive CRUD functions
   - **Missing `get_or_create_supplier()`** - needs creation
   - All existing functions accept `session: Optional[Session] = None`

---

## Implementation Approach

### Phase 1: Update product_service.get_product()

**File**: `src/services/product_service.py`

Add optional session parameter following F091 pattern:

```python
def get_product(
    product_id: int,
    session: Optional[Session] = None,
) -> Product:
    """Retrieve product by ID.

    Transaction boundary: Read-only, no transaction needed.
    If session provided, query executes within caller's transaction.
    If session is None, creates own session_scope().
    """
    if session is not None:
        return _get_product_impl(product_id, session)
    with session_scope() as sess:
        return _get_product_impl(product_id, sess)


def _get_product_impl(product_id: int, session: Session) -> Product:
    """Implementation of get_product.

    Transaction boundary: Inherits session from caller.
    """
    product = (
        session.query(Product)
        .options(
            joinedload(Product.ingredient),
            joinedload(Product.purchases),
            joinedload(Product.inventory_items),
        )
        .filter_by(id=product_id)
        .first()
    )
    if not product:
        raise ProductNotFound(product_id)
    return product
```

**Backward Compatibility**: Session param is optional with default `None`, so all existing callers work unchanged.

### Phase 2: Create supplier_service.get_or_create_supplier()

**File**: `src/services/supplier_service.py`

New function following F091 pattern:

```python
def get_or_create_supplier(
    name: str,
    city: str = "Unknown",
    state: str = "XX",
    zip_code: str = "00000",
    session: Optional[Session] = None,
) -> Supplier:
    """Get existing supplier by name or create with provided defaults.

    Transaction boundary: Single query + possible insert (atomic).
    If session provided, operates within caller's transaction.
    If session is None, creates own session_scope().

    Args:
        name: Supplier name (required)
        city: City (default: "Unknown")
        state: State code (default: "XX")
        zip_code: ZIP code (default: "00000")
        session: Optional session for transactional composition

    Returns:
        Supplier: Existing or newly created supplier MODEL object

    Notes:
        - Defaults match legacy purchase service behavior
        - Future: Will generate slug when TD-009 implemented
        - Lookup by name only (city/state not used for matching)
    """
```

**Important**: Returns `Supplier` model object (not dict) for use in purchase_service needing `.id` access.

### Phase 3: Update purchase_service._record_purchase_impl()

**File**: `src/services/purchase_service.py`

1. Add imports:
```python
from .product_service import get_product  # Already imported
from . import supplier_service
```

2. Replace direct Product query (lines 158-161):
```python
# BEFORE
product = session.query(Product).filter_by(id=product_id).first()
if not product:
    raise ProductNotFound(product_id)

# AFTER
product = get_product(product_id, session=session)
# No need to check None - service raises ProductNotFound
```

3. Replace inline Supplier logic (lines 175-188):
```python
# BEFORE
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
supplier_id = supplier.id

# AFTER
store_name = store if store else "Unknown"
supplier = supplier_service.get_or_create_supplier(
    name=store_name,
    session=session
)
supplier_id = supplier.id
```

4. Update docstring with F091 transaction boundary documentation.

---

## Testing Strategy

### Unit Tests for get_or_create_supplier()

**File**: `src/tests/services/test_supplier_service.py`

```python
def test_get_or_create_supplier_creates_new():
    """Creates new supplier when not found."""

def test_get_or_create_supplier_returns_existing():
    """Returns existing supplier when found by name."""

def test_get_or_create_supplier_with_custom_defaults():
    """Uses custom city/state/zip when provided."""

def test_get_or_create_supplier_with_session():
    """Works correctly when session is passed."""
```

### Integration Tests for Purchase Flow

**File**: `src/tests/test_purchase_service.py`

- Verify product delegation works (product not found raises correctly)
- Verify supplier get-or-create works (new and existing)
- Verify transaction atomicity (rollback on any failure)
- Verify existing tests still pass (behavior preservation)

---

## Files to Modify

| File | Changes | LOC Est. |
|------|---------|----------|
| `src/services/product_service.py` | Add session param, extract _impl | ~20 |
| `src/services/supplier_service.py` | Add get_or_create_supplier() | ~40 |
| `src/services/purchase_service.py` | Import, delegate, update docstring | ~15 |
| `src/tests/services/test_supplier_service.py` | Add 4 test functions | ~60 |
| `src/tests/test_purchase_service.py` | Verify delegation | ~20 |

**Total**: ~155 lines changed

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Breaking get_product() callers | Session param optional (backward compatible) |
| Breaking purchase flow | Preserve exact defaults (Unknown/XX/00000) |
| Supplier model vs dict confusion | Document that get_or_create returns Model |

---

## Work Package Recommendation

**Single WP** - This is a focused, well-scoped refactor:
- 3 service files modified
- 2 test files updated
- Clear scope (fix 2 service boundary violations)
- Preserves existing behavior
- No UI changes
- Estimated 2-3 hours implementation

---

## Out of Scope

- Supplier slug generation (TD-009 - future)
- Enhanced supplier matching (name + city/state)
- Product catalog enhancements
- Any UI changes
