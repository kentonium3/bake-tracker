---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
  - "T003"
  - "T004"
  - "T005"
  - "T006"
title: "Service Boundary Compliance Implementation"
phase: "Phase 1 - Implementation"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
dependencies: []
history:
  - timestamp: "2026-02-03T12:18:25Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 – Service Boundary Compliance Implementation

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you understand the feedback, update `review_status: acknowledged`.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

Refactor `purchase_service.record_purchase()` to eliminate service boundary violations by delegating Product and Supplier operations to their respective owning services.

**Success Criteria**:
- [ ] `product_service.get_product()` accepts optional `session` parameter
- [ ] `supplier_service.get_or_create_supplier()` function created
- [ ] `purchase_service._record_purchase_impl()` uses service delegation (no direct model queries)
- [ ] Session parameter passed to all nested service calls
- [ ] All existing tests pass (behavior preserved)
- [ ] New tests for `get_or_create_supplier()` added and passing
- [ ] Docstrings document transaction boundaries per F091 pattern

---

## Context & Constraints

### Related Documents
- **Spec**: `kitty-specs/092-service-boundary-compliance/spec.md`
- **Plan**: `kitty-specs/092-service-boundary-compliance/plan.md`
- **F091 Patterns**: `docs/design/transaction_patterns_guide.md`
- **Constitution**: `.kittify/memory/constitution.md` (Principle VI.C.1, VI.C.2)

### Architectural Constraints
- Services must delegate entity operations to the owning service
- Never query models directly from coordinating services
- All nested service calls must receive the session parameter
- Preserve exact behavior (defaults must match current values)

### Key Files
- `src/services/product_service.py` - Add session param to get_product()
- `src/services/supplier_service.py` - Add get_or_create_supplier()
- `src/services/purchase_service.py` - Update delegation
- `src/tests/services/test_supplier_service.py` - Add tests
- `src/tests/test_purchase_service.py` - Verify delegation

---

## Subtasks & Detailed Guidance

### Subtask T001 – Add session param to product_service.get_product()

**Purpose**: Enable transaction composition by allowing callers to pass their session to get_product().

**Steps**:
1. Open `src/services/product_service.py`
2. Find `get_product()` function (around line 406)
3. Add `session: Optional[Session] = None` parameter
4. Extract current implementation to `_get_product_impl(product_id, session)`
5. Update `get_product()` to follow F091 pattern:
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
   ```
6. Create `_get_product_impl()` with the existing query logic

**Files**: `src/services/product_service.py`

**Notes**:
- Session param is optional with default None (backward compatible)
- All existing callers continue to work unchanged
- Import `Optional` from typing and `Session` from sqlalchemy.orm if not already imported

---

### Subtask T002 – Create supplier_service.get_or_create_supplier()

**Purpose**: Centralize supplier get-or-create logic currently duplicated in purchase_service.

**Steps**:
1. Open `src/services/supplier_service.py`
2. Add new function after `get_supplier_or_raise()` (around line 735):
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

       Example:
           >>> supplier = get_or_create_supplier("Costco", session=session)
           >>> supplier.id
           42
       """
       if session is not None:
           return _get_or_create_supplier_impl(name, city, state, zip_code, session)
       with session_scope() as sess:
           return _get_or_create_supplier_impl(name, city, state, zip_code, sess)


   def _get_or_create_supplier_impl(
       name: str,
       city: str,
       state: str,
       zip_code: str,
       session: Session,
   ) -> Supplier:
       """Implementation of get_or_create_supplier.

       Transaction boundary: Inherits session from caller.
       """
       # Try to find existing supplier by name
       supplier = session.query(Supplier).filter(Supplier.name == name).first()

       if supplier:
           return supplier

       # Create new supplier with defaults
       supplier = Supplier(
           name=name,
           city=city,
           state=state,
           zip_code=zip_code,
           # Future: slug=generate_supplier_slug(...) when TD-009 implemented
       )
       session.add(supplier)
       session.flush()  # Get ID for return
       return supplier
   ```

**Files**: `src/services/supplier_service.py`

**Notes**:
- Returns Supplier MODEL object (not dict) for direct `.id` access
- Defaults MUST match current values in purchase_service: "Unknown", "XX", "00000"
- Name-only lookup (preserves current behavior)

---

### Subtask T003 – Update purchase_service to delegate to services

**Purpose**: Replace direct model queries with proper service delegation.

**Steps**:
1. Open `src/services/purchase_service.py`

2. Add import for supplier_service (near top):
   ```python
   from . import supplier_service
   ```
   Note: `get_product` is already imported from `product_service` at line 58

3. In `_record_purchase_impl()` (lines 141-244), replace direct Product query (lines 158-161):

   **BEFORE**:
   ```python
   # Validate product exists - need to query within session
   product = session.query(Product).filter_by(id=product_id).first()
   if not product:
       raise ProductNotFound(product_id)
   ```

   **AFTER**:
   ```python
   # FR-1: Delegate product lookup to product_service
   product = get_product(product_id, session=session)
   # No need to check None - service raises ProductNotFound
   ```

4. Replace inline Supplier logic (lines 175-188):

   **BEFORE**:
   ```python
   # Find or create supplier from store name
   store_name = store if store else "Unknown"
   supplier = session.query(Supplier).filter(Supplier.name == store_name).first()
   if not supplier:
       # Create a minimal supplier record with required fields
       supplier = Supplier(
           name=store_name,
           city="Unknown",
           state="XX",
           zip_code="00000",
       )
       session.add(supplier)
       session.flush()
   supplier_id = supplier.id
   ```

   **AFTER**:
   ```python
   # FR-3: Delegate supplier get-or-create to supplier_service
   store_name = store if store else "Unknown"
   supplier = supplier_service.get_or_create_supplier(
       name=store_name,
       session=session
   )
   supplier_id = supplier.id
   ```

5. Remove the `Supplier` model import from line 47 (no longer directly used):
   ```python
   # BEFORE
   from ..models import Purchase, Product, Supplier

   # AFTER
   from ..models import Purchase, Product
   ```
   Note: Keep `Supplier` if it's used elsewhere in the file (check first)

**Files**: `src/services/purchase_service.py`

**Notes**:
- Verify Supplier import is only used in the removed code before removing it
- Test after changes to ensure behavior is preserved

---

### Subtask T004 – Add tests for get_or_create_supplier()

**Purpose**: Verify the new supplier service function works correctly.

**Steps**:
1. Open or create `src/tests/services/test_supplier_service.py`

2. Add test functions:
   ```python
   def test_get_or_create_supplier_creates_new(session):
       """Creates new supplier when not found."""
       from src.services import supplier_service

       # Ensure no supplier with this name exists
       assert session.query(Supplier).filter(Supplier.name == "New Test Store").first() is None

       # Get or create should create
       supplier = supplier_service.get_or_create_supplier(
           name="New Test Store",
           session=session
       )

       assert supplier is not None
       assert supplier.name == "New Test Store"
       assert supplier.city == "Unknown"  # Default
       assert supplier.state == "XX"  # Default
       assert supplier.zip_code == "00000"  # Default
       assert supplier.id is not None


   def test_get_or_create_supplier_returns_existing(session):
       """Returns existing supplier when found by name."""
       from src.services import supplier_service

       # Create a supplier first
       existing = Supplier(
           name="Existing Store",
           city="Boston",
           state="MA",
           zip_code="02101"
       )
       session.add(existing)
       session.flush()
       existing_id = existing.id

       # Get or create should return the existing one
       supplier = supplier_service.get_or_create_supplier(
           name="Existing Store",
           session=session
       )

       assert supplier.id == existing_id
       assert supplier.city == "Boston"  # Original values preserved


   def test_get_or_create_supplier_with_custom_defaults(session):
       """Uses custom city/state/zip when provided for new supplier."""
       from src.services import supplier_service

       supplier = supplier_service.get_or_create_supplier(
           name="Custom Store",
           city="Seattle",
           state="WA",
           zip_code="98101",
           session=session
       )

       assert supplier.name == "Custom Store"
       assert supplier.city == "Seattle"
       assert supplier.state == "WA"
       assert supplier.zip_code == "98101"


   def test_get_or_create_supplier_without_session():
       """Works correctly when session is NOT passed (creates own)."""
       from src.services import supplier_service

       # Should work without session parameter
       supplier = supplier_service.get_or_create_supplier(
           name="No Session Store"
       )

       assert supplier is not None
       assert supplier.name == "No Session Store"
   ```

**Files**: `src/tests/services/test_supplier_service.py`

**Parallel?**: Yes [P] - Can run after T002 is complete

**Notes**:
- Use existing test fixtures for session if available
- Check how other service tests set up their fixtures

---

### Subtask T005 – Verify existing purchase_service tests pass

**Purpose**: Ensure the refactor preserves existing behavior.

**Steps**:
1. Run the purchase service tests:
   ```bash
   ./run-tests.sh src/tests/test_purchase_service.py -v
   ```

2. If any tests fail, investigate:
   - Check if the failure is due to the refactor or pre-existing
   - Ensure defaults match exactly
   - Verify exception types are preserved

3. Run full test suite to check for regressions:
   ```bash
   ./run-tests.sh src/tests/ -v -k "purchase"
   ```

**Files**: `src/tests/test_purchase_service.py`

**Notes**:
- All existing tests should pass unchanged
- If a test fails, the refactor may have changed behavior - investigate before proceeding

---

### Subtask T006 – Update docstrings with F091 transaction boundaries

**Purpose**: Document transaction boundaries per F091 pattern.

**Steps**:
1. Update `product_service.get_product()` docstring (done in T001)

2. Update `supplier_service.get_or_create_supplier()` docstring (done in T002)

3. Update `purchase_service._record_purchase_impl()` docstring to reflect service delegation:
   ```python
   def _record_purchase_impl(...) -> Purchase:
       """Implementation for record_purchase.

       Transaction boundary: Inherits session from caller.
       All operations execute within the caller's transaction boundary:
       1. Validate product exists (delegates to product_service.get_product)
       2. Get or create supplier (delegates to supplier_service.get_or_create_supplier)
       3. Create Purchase record
       4. Create linked InventoryItem record

       CRITICAL: All nested service calls receive session parameter to ensure
       atomicity. This function MUST be called with an active session.
       """
   ```

4. Verify the main `record_purchase()` docstring already has proper F091 documentation (it does)

**Files**:
- `src/services/product_service.py`
- `src/services/supplier_service.py`
- `src/services/purchase_service.py`

**Parallel?**: Yes [P] - Can run after T001, T002, T003 are complete

---

## Test Strategy

### Required Tests
1. **Unit tests** for `get_or_create_supplier()` (T004):
   - Creates new supplier when not found
   - Returns existing supplier when found
   - Uses custom defaults when provided
   - Works with and without session parameter

2. **Regression tests** for purchase service (T005):
   - Run existing test suite
   - All tests should pass unchanged

### Test Commands
```bash
# Run supplier service tests
./run-tests.sh src/tests/services/test_supplier_service.py -v

# Run purchase service tests
./run-tests.sh src/tests/test_purchase_service.py -v

# Run all tests to check for regressions
./run-tests.sh -v
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Breaking existing get_product() callers | Session param optional with default None |
| Breaking purchase flow | Preserve exact defaults (Unknown/XX/00000) |
| Supplier import removal breaking other code | Check all usages before removing import |
| Transaction isolation issues | Pass session to all nested calls per F091 |

---

## Definition of Done Checklist

- [ ] T001: product_service.get_product() accepts session parameter
- [ ] T002: supplier_service.get_or_create_supplier() created
- [ ] T003: purchase_service delegates to both services
- [ ] T004: New tests for get_or_create_supplier() passing
- [ ] T005: All existing purchase_service tests passing
- [ ] T006: Docstrings updated with F091 transaction boundaries
- [ ] No direct Product/Supplier model queries in purchase_service._record_purchase_impl()
- [ ] Session parameter passed to all nested service calls

---

## Review Guidance

**Reviewers should verify**:
1. `get_product()` signature includes `session: Optional[Session] = None`
2. `get_or_create_supplier()` returns Supplier MODEL (not dict)
3. Defaults in `get_or_create_supplier()` match: "Unknown", "XX", "00000"
4. `purchase_service._record_purchase_impl()` has no direct model queries for Product/Supplier
5. All service calls pass `session=session`
6. Docstrings follow F091 pattern
7. All tests pass

---

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

- 2026-02-03T12:18:25Z – system – lane=planned – Prompt generated via /spec-kitty.tasks

---

### Updating Lane Status

To change this work package's lane:
```bash
spec-kitty agent tasks move-task WP01 --to doing --note "Starting implementation"
```

**Valid lanes**: `planned`, `doing`, `for_review`, `done`
