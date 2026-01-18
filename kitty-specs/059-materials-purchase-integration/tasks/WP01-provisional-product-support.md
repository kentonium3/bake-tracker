---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
  - "T003"
  - "T004"
  - "T005"
title: "Service Layer - Provisional Product Support"
phase: "Phase 0 - Foundation"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
dependencies: []
history:
  - timestamp: "2026-01-18T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 - Service Layer - Provisional Product Support

## Important: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Implementation Command

```bash
# No dependencies - start from main branch
spec-kitty implement WP01
```

---

## Objectives & Success Criteria

Add provisional product lifecycle support to MaterialCatalogService. This enables:
- CLI purchases to create "provisional" products with minimal metadata
- Later enrichment through the UI to complete product information
- Automatic promotion from provisional to complete when all required fields are filled

**Success Criteria**:
- [ ] Provisional products can be created with is_provisional=True
- [ ] Completeness check identifies missing required fields
- [ ] Products auto-promote to non-provisional when complete
- [ ] All tests pass with >70% coverage for new code

---

## Context & Constraints

**Feature**: F059 - Materials Purchase Integration & Workflows
**Reference Documents**:
- Spec: `kitty-specs/059-materials-purchase-integration/spec.md`
- Plan: `kitty-specs/059-materials-purchase-integration/plan.md`
- Data Model: `kitty-specs/059-materials-purchase-integration/data-model.md`
- Constitution: `.kittify/memory/constitution.md`

**Key Clarification** (from spec):
> Required fields for completeness: name, brand, slug (if exposed in UI), purchase unit, package size, and linked material/ingredient. When all present, is_provisional=False.

**Session Management Pattern** (from CLAUDE.md):
All service methods that may be called from other services MUST accept `session=None` parameter.

```python
def some_function(..., session=None):
    if session is not None:
        return _impl(..., session)
    with session_scope() as session:
        return _impl(..., session)
```

---

## Subtasks & Detailed Guidance

### Subtask T001 - Verify is_provisional Column Exists

**Purpose**: Ensure MaterialProduct model has the is_provisional field. F058 may or may not have added this.

**Steps**:
1. Open `src/models/material_product.py`
2. Check if `is_provisional` column exists
3. If missing, add:
   ```python
   is_provisional = Column(Boolean, nullable=False, default=False, index=True)
   ```
4. If adding, also add index:
   ```python
   Index("idx_material_product_provisional", "is_provisional"),
   ```

**Files**:
- `src/models/material_product.py` (check/modify)

**Validation**:
- [ ] Column exists with correct type (Boolean, default=False)
- [ ] Column is indexed for query performance

---

### Subtask T002 - Update create_product() for is_provisional Parameter

**Purpose**: Allow MaterialCatalogService.create_product() to accept is_provisional flag.

**Steps**:
1. Open `src/services/material_catalog_service.py`
2. Find `create_product()` function (or `_create_product_impl`)
3. Add `is_provisional: bool = False` parameter
4. Pass to model creation:
   ```python
   product = MaterialProduct(
       name=name,
       material_id=material_id,
       # ... existing fields
       is_provisional=is_provisional,
   )
   ```

**Files**:
- `src/services/material_catalog_service.py` (modify)

**Validation**:
- [ ] Function signature includes is_provisional parameter with default False
- [ ] Parameter is passed to MaterialProduct constructor
- [ ] Existing callers (without parameter) continue to work (backward compatible)

---

### Subtask T003 - Add check_provisional_completeness() Method

**Purpose**: Check if a provisional product has all required fields to become complete.

**Steps**:
1. Add new function to `material_catalog_service.py`:
   ```python
   def check_provisional_completeness(
       product_id: int,
       session: Optional[Session] = None
   ) -> Tuple[bool, List[str]]:
       """Check if product has all required fields for completeness.

       Args:
           product_id: The MaterialProduct ID to check
           session: Optional database session

       Returns:
           Tuple of (is_complete, missing_fields)
           - is_complete: True if all required fields are present
           - missing_fields: List of field names that are missing/empty
       """
   ```

2. Required fields per clarification:
   - name (non-empty string)
   - brand (non-empty string)
   - slug (non-empty string)
   - package_quantity (> 0)
   - package_unit (non-empty string)
   - material_id (not None)

3. Implementation:
   ```python
   def _check_provisional_completeness_impl(product_id: int, session: Session) -> Tuple[bool, List[str]]:
       product = session.query(MaterialProduct).filter_by(id=product_id).first()
       if not product:
           raise MaterialProductNotFoundError(f"Product {product_id} not found")

       missing = []
       if not product.name or not product.name.strip():
           missing.append("name")
       if not product.brand or not product.brand.strip():
           missing.append("brand")
       if not product.slug or not product.slug.strip():
           missing.append("slug")
       if not product.package_quantity or product.package_quantity <= 0:
           missing.append("package_quantity")
       if not product.package_unit or not product.package_unit.strip():
           missing.append("package_unit")
       if not product.material_id:
           missing.append("material_id")

       return (len(missing) == 0, missing)
   ```

**Files**:
- `src/services/material_catalog_service.py` (add function)

**Validation**:
- [ ] Function returns (True, []) for complete products
- [ ] Function returns (False, ["brand", ...]) for incomplete products
- [ ] Handles non-existent product_id gracefully

---

### Subtask T004 - Auto-clear is_provisional on Enrichment

**Purpose**: When update_product() is called and the product becomes complete, auto-clear is_provisional.

**Steps**:
1. Find `update_product()` function in `material_catalog_service.py`
2. After updating fields, check completeness:
   ```python
   # After all field updates are applied to the product...

   # Auto-promote provisional products when complete
   if product.is_provisional:
       is_complete, _ = _check_provisional_completeness_impl(product.id, session)
       if is_complete:
           product.is_provisional = False
   ```

3. Ensure the check happens AFTER all field updates are applied

**Files**:
- `src/services/material_catalog_service.py` (modify update_product)

**Validation**:
- [ ] Updating a provisional product with all required fields clears is_provisional
- [ ] Updating a provisional product with incomplete fields keeps is_provisional=True
- [ ] Non-provisional products are not affected by this logic

---

### Subtask T005 - Write Unit Tests for Provisional Lifecycle

**Purpose**: Ensure provisional product functionality works correctly.

**Steps**:
1. Create or extend test file: `src/tests/services/test_material_catalog_service.py`
2. Add tests for:

```python
class TestProvisionalProductLifecycle:
    """Tests for provisional product creation and enrichment."""

    def test_create_provisional_product(self, session):
        """Test creating a product with is_provisional=True."""
        product = create_product(
            material_id=material.id,
            name="Test Bags",
            package_quantity=Decimal("100"),
            package_unit="each",
            is_provisional=True,
            session=session
        )
        assert product["is_provisional"] is True

    def test_create_non_provisional_product_default(self, session):
        """Test that is_provisional defaults to False."""
        product = create_product(
            material_id=material.id,
            name="Test Bags",
            brand="TestBrand",
            package_quantity=Decimal("100"),
            package_unit="each",
            session=session
        )
        assert product["is_provisional"] is False

    def test_check_completeness_complete_product(self, session):
        """Test completeness check for complete product."""
        # Create with all required fields
        is_complete, missing = check_provisional_completeness(product_id, session=session)
        assert is_complete is True
        assert missing == []

    def test_check_completeness_missing_brand(self, session):
        """Test completeness check when brand is missing."""
        # Create provisional without brand
        is_complete, missing = check_provisional_completeness(product_id, session=session)
        assert is_complete is False
        assert "brand" in missing

    def test_auto_promote_on_enrichment(self, session):
        """Test that provisional product auto-promotes when enriched."""
        # Create provisional without brand
        product = create_product(..., is_provisional=True, session=session)
        assert product["is_provisional"] is True

        # Update with brand (completing the product)
        updated = update_product(product["id"], brand="TestBrand", session=session)
        assert updated["is_provisional"] is False

    def test_no_auto_promote_if_still_incomplete(self, session):
        """Test that provisional stays provisional if still incomplete."""
        # Create provisional without brand and sku
        # Update with only notes (not completing)
        # Assert still provisional
```

**Files**:
- `src/tests/services/test_material_catalog_service.py` (add/extend)

**Parallel?**: Yes - can be written alongside implementation

**Validation**:
- [ ] All tests pass
- [ ] Coverage for new code >70%

---

## Test Strategy

Run tests with:
```bash
./run-tests.sh src/tests/services/test_material_catalog_service.py -v
./run-tests.sh src/tests/services/test_material_catalog_service.py -v --cov=src/services/material_catalog_service
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| is_provisional column missing | Check first; add with migration-safe approach |
| Breaking existing callers | Use default parameter value (backward compatible) |
| Completeness criteria unclear | Follow clarification exactly: name, brand, slug, package_qty, package_unit, material_id |

---

## Definition of Done Checklist

- [ ] T001: is_provisional column verified/added
- [ ] T002: create_product() accepts is_provisional parameter
- [ ] T003: check_provisional_completeness() method added
- [ ] T004: update_product() auto-clears is_provisional when complete
- [ ] T005: All tests written and passing
- [ ] Code follows session management pattern
- [ ] No regressions in existing tests
- [ ] tasks.md updated with status change

---

## Review Guidance

- Verify completeness criteria matches clarification exactly
- Check session pattern is followed correctly
- Ensure backward compatibility with existing callers
- Verify test coverage meets >70% threshold

---

## Activity Log

- 2026-01-18T00:00:00Z - system - lane=planned - Prompt created.
