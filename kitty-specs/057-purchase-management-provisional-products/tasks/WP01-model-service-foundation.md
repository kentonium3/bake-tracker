---
work_package_id: "WP01"
title: "Model & Service Foundation"
lane: "doing"
dependencies: []
subtasks: ["T001", "T002", "T003", "T004", "T005", "T006"]
priority: "P0"
estimated_lines: 350
agent: "claude"
shell_pid: "25909"
history:
  - date: "2026-01-17"
    action: "created"
    agent: "claude"
---

# WP01: Model & Service Foundation

**Feature**: F057 Purchase Management with Provisional Products
**Objective**: Add `is_provisional` field to Product model and extend services with provisional product support.

## Implementation Command

```bash
spec-kitty implement WP01
```

## Context

This work package establishes the foundation for provisional product support. The key change is adding an `is_provisional` boolean field to the Product model, which allows products created during purchase entry to be flagged for later review while remaining fully functional.

**Key Design Decisions** (from plan.md):
- Field name: `is_provisional` (not `needs_review`) for clearer semantics
- Default: `False` - existing products unaffected
- Indexed: `True` - enables efficient filtering for review queue

**Schema Change Strategy** (per Constitution VI):
This feature requires a schema change. Per the project's desktop phase strategy:
1. Export full backup using app's export function
2. Stop app, delete database file
3. Restart app (creates fresh DB with new schema)
4. Import backup (new field defaults to `False`)

## Subtasks

### T001: Add `is_provisional` field to Product model

**Purpose**: Add the boolean field that identifies products needing review.

**File**: `src/models/product.py`

**Steps**:
1. Add the field definition after `is_hidden`:
```python
# F057: Provisional Product Support
is_provisional = Column(
    Boolean,
    default=False,
    nullable=False,
    index=True,
    comment="True if product was created during purchase entry and needs review"
)
```

2. Add index to `__table_args__`:
```python
Index("idx_product_provisional", "is_provisional"),
```

**Validation**:
- [ ] Field added with correct type, default, and nullable settings
- [ ] Index defined for efficient filtering
- [ ] Model imports Column, Boolean, Index if not already present

---

### T002: Add `create_provisional_product()` to product_service

**Purpose**: Create a method that creates products with `is_provisional=True` and relaxed validation.

**File**: `src/services/product_service.py`

**Steps**:
1. Add new function after existing `create_product()`:

```python
def create_provisional_product(
    ingredient_id: int,
    brand: str,
    package_unit: str,
    package_unit_quantity: float,
    product_name: Optional[str] = None,
    upc_code: Optional[str] = None,
    session: Optional[Session] = None,
) -> Product:
    """Create a provisional product for immediate use during purchase entry.

    Provisional products are created with is_provisional=True, indicating they
    need review to complete missing information. They are fully functional for
    purchases and inventory tracking.

    Args:
        ingredient_id: ID of the parent ingredient (required, must be leaf level)
        brand: Brand name (required, can be "Unknown")
        package_unit: Unit the package contains, e.g., "lb", "oz" (required)
        package_unit_quantity: Quantity per package (required)
        product_name: Optional variant name
        upc_code: Optional UPC/barcode (may have from scanning)
        session: Optional database session for transaction composability

    Returns:
        Product: Created product with is_provisional=True

    Raises:
        ValidationError: If ingredient_id invalid or not a leaf ingredient
        DatabaseError: If database operation fails

    Example:
        >>> product = create_provisional_product(
        ...     ingredient_id=42,
        ...     brand="King Arthur",
        ...     package_unit="lb",
        ...     package_unit_quantity=5.0,
        ... )
        >>> product.is_provisional
        True
    """
```

2. Implementation should:
   - Validate ingredient exists and is leaf (hierarchy_level == 2)
   - Create Product with `is_provisional=True`
   - Auto-generate display_name from available fields
   - Follow session pattern from CLAUDE.md

**Reference**: See existing `create_product()` at line 103-200 for patterns.

**Validation**:
- [ ] Function accepts all required parameters
- [ ] Validates ingredient is leaf level (use `_validate_leaf_ingredient_for_product`)
- [ ] Creates product with `is_provisional=True`
- [ ] Follows `session: Optional[Session] = None` pattern

---

### T003: Add `get_provisional_products()` to product_catalog_service

**Purpose**: Query method for retrieving all products awaiting review.

**File**: `src/services/product_catalog_service.py`

**Steps**:
1. Add new function:

```python
def get_provisional_products(
    session: Optional[Session] = None,
) -> List[Dict[str, Any]]:
    """Get all products where is_provisional=True.

    Returns products that were created during purchase entry and need
    review to complete their information.

    Args:
        session: Optional database session

    Returns:
        List[Dict[str, Any]]: Provisional products with enriched data
            (same format as get_products())

    Example:
        >>> products = get_provisional_products()
        >>> len(products)
        3
        >>> products[0]["is_provisional"]
        True
    """
```

2. Implementation should:
   - Query `Product` with filter `Product.is_provisional == True`
   - Exclude hidden products (`Product.is_hidden == False`)
   - Enrich with ingredient_name, last_price (same as `_get_products_impl`)
   - Order by date_added DESC (most recent first)

**Reference**: See `get_products()` at line 41-135 for pattern.

**Validation**:
- [ ] Returns only products where `is_provisional == True`
- [ ] Returns dict format consistent with `get_products()`
- [ ] Follows session pattern

---

### T004: Add `get_provisional_count()` to product_catalog_service

**Purpose**: Efficient count query for badge display.

**File**: `src/services/product_catalog_service.py`

**Steps**:
1. Add new function:

```python
def get_provisional_count(
    session: Optional[Session] = None,
) -> int:
    """Get count of provisional products for badge display.

    Efficient count-only query for UI badge that shows number of
    products needing review.

    Args:
        session: Optional database session

    Returns:
        int: Count of products where is_provisional=True

    Example:
        >>> count = get_provisional_count()
        >>> count
        3
    """
```

2. Implementation should:
   - Use `func.count(Product.id)` for efficiency
   - Filter `is_provisional == True` and `is_hidden == False`
   - Return scalar integer

**Validation**:
- [ ] Returns integer count
- [ ] Uses efficient count query (not loading all records)
- [ ] Excludes hidden products from count

---

### T005: Add `mark_product_reviewed()` to product_catalog_service

**Purpose**: Clear the provisional flag when user completes product review.

**File**: `src/services/product_catalog_service.py`

**Steps**:
1. Add new function:

```python
def mark_product_reviewed(
    product_id: int,
    session: Optional[Session] = None,
) -> Dict[str, Any]:
    """Clear is_provisional flag after user completes product details.

    Marks a provisional product as reviewed, removing it from the
    review queue. Does not validate that all fields are complete -
    user decides when product info is sufficient.

    Args:
        product_id: Product ID to mark as reviewed
        session: Optional database session

    Returns:
        Dict[str, Any]: Updated product as dictionary

    Raises:
        ProductNotFound: If product_id doesn't exist

    Example:
        >>> product = mark_product_reviewed(123)
        >>> product["is_provisional"]
        False
    """
```

2. Implementation should:
   - Query product by ID
   - Set `is_provisional = False`
   - Flush and return updated product dict

**Reference**: See `hide_product()` at line 419-454 for similar pattern.

**Validation**:
- [ ] Sets `is_provisional` to `False`
- [ ] Returns updated product dict
- [ ] Raises `ProductNotFound` for invalid ID

---

### T006: Write unit tests for all new service methods

**Purpose**: Ensure service methods work correctly and catch regressions.

**Files**:
- `src/tests/services/test_product_service.py` (extend existing)
- `src/tests/services/test_product_catalog_service.py` (extend existing)

**Steps**:

1. In `test_product_service.py`, add tests:

```python
class TestCreateProvisionalProduct:
    """Tests for create_provisional_product()."""

    def test_creates_product_with_provisional_flag(self, session, leaf_ingredient):
        """Provisional product should have is_provisional=True."""
        product = create_provisional_product(
            ingredient_id=leaf_ingredient.id,
            brand="Test Brand",
            package_unit="lb",
            package_unit_quantity=5.0,
            session=session,
        )
        assert product.is_provisional is True

    def test_requires_leaf_ingredient(self, session, category_ingredient):
        """Should reject non-leaf ingredients."""
        with pytest.raises(NonLeafIngredientError):
            create_provisional_product(
                ingredient_id=category_ingredient.id,
                brand="Test",
                package_unit="lb",
                package_unit_quantity=1.0,
                session=session,
            )

    def test_minimal_fields_sufficient(self, session, leaf_ingredient):
        """Should create with only required fields."""
        product = create_provisional_product(
            ingredient_id=leaf_ingredient.id,
            brand="Unknown",
            package_unit="each",
            package_unit_quantity=1.0,
            session=session,
        )
        assert product.id is not None
```

2. In `test_product_catalog_service.py`, add tests:

```python
class TestProvisionalProducts:
    """Tests for provisional product methods."""

    def test_get_provisional_products_returns_only_provisional(
        self, session, provisional_product, regular_product
    ):
        """Should return only products with is_provisional=True."""
        results = get_provisional_products(session=session)
        ids = [p["id"] for p in results]
        assert provisional_product.id in ids
        assert regular_product.id not in ids

    def test_get_provisional_count(self, session, provisional_product):
        """Should return accurate count."""
        count = get_provisional_count(session=session)
        assert count >= 1

    def test_mark_product_reviewed_clears_flag(self, session, provisional_product):
        """Should set is_provisional to False."""
        result = mark_product_reviewed(provisional_product.id, session=session)
        assert result["is_provisional"] is False

        # Verify no longer in provisional list
        provisionals = get_provisional_products(session=session)
        ids = [p["id"] for p in provisionals]
        assert provisional_product.id not in ids
```

3. Add pytest fixtures for test data:

```python
@pytest.fixture
def provisional_product(session, leaf_ingredient):
    """Create a provisional product for testing."""
    from src.models import Product
    product = Product(
        ingredient_id=leaf_ingredient.id,
        brand="Test Provisional",
        package_unit="oz",
        package_unit_quantity=8.0,
        is_provisional=True,
    )
    session.add(product)
    session.flush()
    return product
```

**Validation**:
- [ ] All tests pass with `./run-tests.sh src/tests/services/test_product_service.py -v`
- [ ] All tests pass with `./run-tests.sh src/tests/services/test_product_catalog_service.py -v`
- [ ] Tests cover happy path and error cases
- [ ] Fixtures properly set up test data

---

## Definition of Done

- [ ] All 6 subtasks completed
- [ ] `is_provisional` field added to Product model with index
- [ ] `create_provisional_product()` implemented and tested
- [ ] `get_provisional_products()` implemented and tested
- [ ] `get_provisional_count()` implemented and tested
- [ ] `mark_product_reviewed()` implemented and tested
- [ ] All existing tests still pass (`./run-tests.sh -v`)
- [ ] Code follows session management pattern from CLAUDE.md

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Schema change breaks existing data | Document export/import procedure; default value preserves data |
| Performance of provisional query | Index on `is_provisional` field |
| Nested session issues | All methods follow `session: Optional[Session] = None` pattern |

## Reviewer Notes

When reviewing this WP:
1. Verify new field has proper index definition
2. Confirm all methods accept session parameter
3. Check that `create_provisional_product` validates leaf ingredients
4. Ensure tests use fixtures, not hardcoded IDs
5. Run full test suite to catch regressions

## Activity Log

- 2026-01-18T01:43:33Z – claude – shell_pid=5204 – lane=doing – Started implementation via workflow command
- 2026-01-18T01:57:28Z – claude – shell_pid=5204 – lane=for_review – Ready for review: Added is_provisional field to Product model, implemented create_provisional_product() in product_service, and get_provisional_products(), get_provisional_count(), mark_product_reviewed() in product_catalog_service. All 16 new tests pass, full test suite (2380 tests) passes.
- 2026-01-18T03:33:56Z – claude – shell_pid=25909 – lane=doing – Started review via workflow command
