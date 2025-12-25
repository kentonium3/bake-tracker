---
work_package_id: "WP03"
subtasks:
  - "T012"
  - "T013"
  - "T014"
  - "T015"
  - "T016"
  - "T017"
  - "T018"
title: "Recency Query Service Methods"
phase: "Phase 0 - Foundation"
lane: "for_review"
assignee: ""
agent: "claude"
shell_pid: "33920"
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-24T23:15:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP03 – Recency Query Service Methods

## Objectives & Success Criteria

**Goal**: Add recency intelligence queries to inventory_item_service for identifying recently-used products/ingredients.

**Success Criteria**:
- [ ] `get_recent_products(ingredient_id)` returns product IDs from last 30 days
- [ ] `get_recent_products(ingredient_id)` returns product IDs with 3+ uses in 90 days
- [ ] Hybrid OR logic: products meeting EITHER criterion are included
- [ ] Results sorted by most recent addition date
- [ ] `get_recent_ingredients(category)` works similarly
- [ ] All methods follow session parameter pattern
- [ ] All unit tests pass

## Context & Constraints

**References**:
- Plan: `kitty-specs/029-streamlined-inventory-entry/plan.md` (PD-003: Recency Query Location)
- Research: `kitty-specs/029-streamlined-inventory-entry/research.md` (RQ-003, RQ-004)
- Data Model: `kitty-specs/029-streamlined-inventory-entry/data-model.md` (Recency queries section)
- CLAUDE.md: Session Management section (CRITICAL - follow pattern)

**Constraints**:
- Must follow session parameter pattern per CLAUDE.md
- Queries target InventoryItem table (existing)
- Limit results to 20 by default
- Must be performant (<200ms for typical data volumes)

## Subtasks & Detailed Guidance

### Subtask T012 – Add get_recent_products() method

**Purpose**: Main recency query for products within an ingredient.

**Steps**:
1. Open `src/services/inventory_item_service.py`
2. Add imports: `from datetime import date, timedelta`
3. Add function signature with parameters

**Signature**:
```python
def get_recent_products(
    ingredient_id: int,
    days: int = 30,
    min_frequency: int = 3,
    frequency_days: int = 90,
    limit: int = 20,
    session: Optional[Session] = None
) -> List[int]:
    """
    Get product IDs that are "recent" for an ingredient.

    Recency definition (hybrid):
    - Temporal: Added within last 'days' days
    - Frequency: Added 'min_frequency' or more times in last 'frequency_days' days
    - Product is recent if EITHER condition true

    Returns:
        List of product IDs sorted by most recent addition date
    """
```

**Files**: `src/services/inventory_item_service.py` (MODIFY)

### Subtask T013 – Implement temporal recency check

**Purpose**: Find products added within last N days.

**Steps**:
1. Calculate temporal cutoff: `today - timedelta(days=days)`
2. Query InventoryItem where addition_date >= cutoff
3. Group by product_id, get max(addition_date)

**Query Pattern**:
```python
temporal_cutoff = date.today() - timedelta(days=days)

temporal_query = session.query(
    InventoryItem.product_id,
    func.max(InventoryItem.addition_date).label('last_addition')
).filter(
    and_(
        InventoryItem.ingredient_id == ingredient_id,
        InventoryItem.product_id.isnot(None),
        InventoryItem.addition_date >= temporal_cutoff
    )
).group_by(InventoryItem.product_id)
```

### Subtask T014 – Implement frequency recency check

**Purpose**: Find products added 3+ times in last 90 days.

**Steps**:
1. Calculate frequency cutoff: `today - timedelta(days=frequency_days)`
2. Query with HAVING count >= min_frequency
3. Group by product_id

**Query Pattern**:
```python
frequency_cutoff = date.today() - timedelta(days=frequency_days)

frequency_query = session.query(
    InventoryItem.product_id,
    func.max(InventoryItem.addition_date).label('last_addition')
).filter(
    and_(
        InventoryItem.ingredient_id == ingredient_id,
        InventoryItem.product_id.isnot(None),
        InventoryItem.addition_date >= frequency_cutoff
    )
).group_by(InventoryItem.product_id).having(
    func.count(InventoryItem.id) >= min_frequency
)
```

### Subtask T015 – Implement hybrid OR logic

**Purpose**: Combine temporal and frequency results.

**Steps**:
1. Execute both queries
2. Merge results using Python dict (keep max date for each product)
3. Sort by date descending
4. Return limited list of IDs

**Code Pattern**:
```python
# Execute queries
temporal_results = {row.product_id: row.last_addition for row in temporal_query.all()}
frequency_results = {row.product_id: row.last_addition for row in frequency_query.all()}

# Merge with max date
merged = {}
for pid, dt in temporal_results.items():
    merged[pid] = dt
for pid, dt in frequency_results.items():
    if pid in merged:
        merged[pid] = max(merged[pid], dt)
    else:
        merged[pid] = dt

# Sort by date descending, limit
sorted_products = sorted(merged.items(), key=lambda x: x[1], reverse=True)
return [pid for pid, _ in sorted_products[:limit]]
```

### Subtask T016 – Add get_recent_ingredients() method

**Purpose**: Recency query for ingredients within a category.

**Steps**:
1. Similar structure to get_recent_products()
2. Filter by category instead of ingredient_id
3. Return ingredient IDs

**Signature**:
```python
def get_recent_ingredients(
    category: str,
    days: int = 30,
    min_frequency: int = 3,
    frequency_days: int = 90,
    limit: int = 20,
    session: Optional[Session] = None
) -> List[int]:
    """
    Get ingredient IDs that are "recent" for a category.
    """
```

### Subtask T017 – Follow session parameter pattern

**Purpose**: Ensure proper session handling per CLAUDE.md.

**Steps**:
1. Each function checks if session is provided
2. If provided, use directly
3. If not, create session_scope() and call _impl function

**Pattern**:
```python
def get_recent_products(..., session: Optional[Session] = None) -> List[int]:
    if session is not None:
        return _get_recent_products_impl(..., session)
    with session_scope() as session:
        return _get_recent_products_impl(..., session)

def _get_recent_products_impl(..., session: Session) -> List[int]:
    # Actual query logic here
```

### Subtask T018 – Add recency tests [P]

**Purpose**: Verify recency logic works correctly.

**Steps**:
1. Add tests to `src/tests/services/test_inventory_item_service.py`
2. Create fixtures with specific dates
3. Test all three recency scenarios

**Test Cases**:
```python
@pytest.fixture
def recency_test_data(session):
    """Create inventory items with specific dates for recency testing."""
    today = date.today()

    # Create ingredient
    ingredient = Ingredient(name='test_flour', display_name='Test Flour', category='Baking')
    session.add(ingredient)
    session.flush()

    # Product A: Added yesterday (temporal recent)
    product_a = Product(name='Product A', ingredient_id=ingredient.id)
    session.add(product_a)
    session.flush()
    item_a = InventoryItem(
        ingredient_id=ingredient.id,
        product_id=product_a.id,
        addition_date=today - timedelta(days=1)
    )
    session.add(item_a)

    # Product B: Added 45 days ago, only once (not recent)
    product_b = Product(name='Product B', ingredient_id=ingredient.id)
    session.add(product_b)
    session.flush()
    item_b = InventoryItem(
        ingredient_id=ingredient.id,
        product_id=product_b.id,
        addition_date=today - timedelta(days=45)
    )
    session.add(item_b)

    # Product C: Added 60 days ago but 4 times (frequency recent)
    product_c = Product(name='Product C', ingredient_id=ingredient.id)
    session.add(product_c)
    session.flush()
    for i in range(4):
        item = InventoryItem(
            ingredient_id=ingredient.id,
            product_id=product_c.id,
            addition_date=today - timedelta(days=60 + i)
        )
        session.add(item)

    session.commit()
    return {'ingredient': ingredient, 'product_a': product_a, 'product_b': product_b, 'product_c': product_c}

def test_get_recent_products_temporal(recency_test_data, session):
    """Product A should be recent (temporal)."""
    recent_ids = get_recent_products(
        recency_test_data['ingredient'].id,
        session=session
    )
    assert recency_test_data['product_a'].id in recent_ids

def test_get_recent_products_not_recent(recency_test_data, session):
    """Product B should NOT be recent."""
    recent_ids = get_recent_products(
        recency_test_data['ingredient'].id,
        session=session
    )
    assert recency_test_data['product_b'].id not in recent_ids

def test_get_recent_products_frequency(recency_test_data, session):
    """Product C should be recent (frequency)."""
    recent_ids = get_recent_products(
        recency_test_data['ingredient'].id,
        session=session
    )
    assert recency_test_data['product_c'].id in recent_ids

def test_get_recent_products_sorted_by_date(recency_test_data, session):
    """Results should be sorted by most recent first."""
    recent_ids = get_recent_products(
        recency_test_data['ingredient'].id,
        session=session
    )
    # Product A (yesterday) should come before Product C (60 days ago)
    if recency_test_data['product_a'].id in recent_ids and recency_test_data['product_c'].id in recent_ids:
        a_idx = recent_ids.index(recency_test_data['product_a'].id)
        c_idx = recent_ids.index(recency_test_data['product_c'].id)
        assert a_idx < c_idx
```

**Files**: `src/tests/services/test_inventory_item_service.py` (MODIFY)

**Parallel?**: Yes, can be written alongside implementation

## Test Strategy

Run tests with:
```bash
pytest src/tests/services/test_inventory_item_service.py -v -k recency
```

All recency-related tests must pass.

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Query performance | Add index on addition_date if slow |
| Complex date logic | Use explicit test fixtures with known dates |
| Session management | Follow CLAUDE.md pattern strictly |

## Definition of Done Checklist

- [ ] `get_recent_products()` implemented with hybrid logic
- [ ] `get_recent_ingredients()` implemented
- [ ] Session parameter pattern followed
- [ ] All unit tests pass
- [ ] No linting errors
- [ ] Queries performant (< 200ms typical)

## Review Guidance

**Reviewers should verify**:
1. Session parameter pattern matches CLAUDE.md exactly
2. Hybrid OR logic works (both temporal and frequency paths tested)
3. Results are sorted by date descending
4. Limit parameter respected

## Activity Log

- 2025-12-24T23:15:00Z – system – lane=planned – Prompt created.
- 2025-12-25T04:58:12Z – claude – shell_pid=33920 – lane=doing – Started implementation
- 2025-12-25T05:05:42Z – claude – shell_pid=33920 – lane=for_review – All tests pass. Recency logic implemented.
