---
work_package_id: "WP11"
subtasks:
  - "T075"
  - "T076"
  - "T077"
  - "T078"
  - "T079"
  - "T080"
  - "T081"
  - "T082"
  - "T083"
title: "Integration Testing & Polish"
phase: "Phase 4 - Polish"
lane: "doing"
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

# Work Package Prompt: WP11 – Integration Testing & Polish

## Objectives & Success Criteria

**Goal**: Comprehensive integration testing and final polish.

**Success Criteria**:
- [ ] Complete 10-item entry workflow in under 5 minutes
- [ ] All existing tests still pass (regression check)
- [ ] Recency queries perform under 200ms
- [ ] Tab navigation works through all fields
- [ ] User acceptance testing passed
- [ ] All integration tests pass

## Context & Constraints

**References**:
- Spec: `kitty-specs/029-streamlined-inventory-entry/spec.md` (Success Criteria section)
- Quickstart: `kitty-specs/029-streamlined-inventory-entry/quickstart.md`

**Constraints**:
- Depends on all previous work packages (WP01-WP10)
- Must not introduce regressions
- Performance target: <200ms for recency queries

## Subtasks & Detailed Guidance

### Subtask T075 – Create integration test file

**Purpose**: Centralized integration tests for dialog.

**Steps**:
1. Create `src/tests/integration/test_add_inventory_dialog.py`
2. Add fixtures for dialog setup
3. Add helper functions for common operations

**Files**: `src/tests/integration/test_add_inventory_dialog.py` (NEW)

### Subtask T076 – Test type-ahead workflow [P]

**Purpose**: Verify type-ahead filtering end-to-end.

**Test Cases**:
```python
def test_category_typeahead_filters(dialog):
    """Typing in category should filter options."""
    # Simulate typing 'bak'
    dialog.category_combo._entry.insert(0, 'bak')
    dialog.category_combo._on_key_release(MockEvent(keysym='k'))

    values = dialog.category_combo._combobox.cget('values')
    assert 'Baking' in values
    assert len(values) < 20  # Filtered

def test_ingredient_filtered_by_category(dialog):
    """Ingredient dropdown should only show category items."""
    dialog.category_combo.set('Baking')
    dialog._on_category_selected('Baking')

    values = dialog.ingredient_combo._combobox.cget('values')
    # All values should be Baking ingredients
    # (verify by checking against DB)

def test_product_filtered_by_ingredient(dialog):
    """Product dropdown should only show ingredient products."""
    dialog._on_ingredient_selected('All-Purpose Flour')

    values = dialog.product_combo._combobox.cget('values')
    # All values should be AP Flour products
```

### Subtask T077 – Test session persistence [P]

**Purpose**: Verify session state across dialog opens.

**Test Cases**:
```python
def test_session_persists_across_dialogs(app, reset_session):
    """Session should persist between dialog opens."""
    # First dialog: add item with Costco
    dialog1 = create_dialog(app)
    dialog1.supplier_combo.set('Costco Waltham MA')
    dialog1.category_combo.set('Baking')
    # Complete add...
    dialog1._add_inventory()
    dialog1.destroy()

    # Second dialog: should pre-select Costco and Baking
    dialog2 = create_dialog(app)
    dialog2._load_initial_data()

    assert 'Costco' in dialog2.supplier_combo.get()
    assert 'Baking' in dialog2.category_combo.get()
```

### Subtask T078 – Test inline creation [P]

**Purpose**: Verify inline product creation full workflow.

**Test Cases**:
```python
def test_inline_creation_full_workflow(dialog, mock_product_service):
    """Complete inline creation should work."""
    # Select ingredient
    dialog._on_ingredient_selected('All-Purpose Flour')

    # Expand inline form
    dialog._toggle_inline_create()
    assert dialog.inline_create_expanded

    # Fill form
    dialog.inline_name_entry.insert(0, 'Test Flour 10lb')
    dialog.inline_unit_combo.set('lb')
    dialog.inline_qty_entry.insert(0, '10')

    # Create
    dialog._create_product_inline()

    # Verify
    assert not dialog.inline_create_expanded
    assert 'Test Flour 10lb' in dialog.product_combo.get()
```

### Subtask T079 – Test price suggestions [P]

**Purpose**: Verify price suggestion scenarios.

**Test Cases**:
```python
def test_price_suggestion_workflow(dialog, populated_purchases):
    """Price should suggest from purchase history."""
    dialog._on_ingredient_selected('All-Purpose Flour')
    dialog._on_product_selected('Gold Medal AP 10lb')
    dialog.supplier_combo.set('Costco Waltham MA')

    # Price should be pre-filled
    price = dialog.price_entry.get()
    assert price != ''

    # Hint should be displayed
    hint = dialog.price_hint_label.cget('text')
    assert 'last paid' in hint
```

### Subtask T080 – Test tab navigation [P]

**Purpose**: Verify keyboard navigation.

**Test Cases**:
```python
def test_tab_order(dialog):
    """Tab should navigate through fields in order."""
    expected_order = [
        'category_combo',
        'ingredient_combo',
        'product_combo',
        'supplier_combo',
        'price_entry',
        'quantity_entry',
        'notes_entry'
    ]

    # Get widgets in tab order
    # Note: This may require Tk-specific testing approach
```

### Subtask T081 – Regression check

**Purpose**: Verify no existing tests broken.

**Steps**:
1. Run full test suite
2. Ensure all tests pass
3. Document any intentional changes to existing behavior

**Command**:
```bash
pytest src/tests -v --tb=short
```

### Subtask T082 – Performance validation

**Purpose**: Verify recency queries are fast.

**Steps**:
1. Run recency queries with realistic data
2. Measure execution time
3. Target: <200ms

**Test**:
```python
import time

def test_recency_query_performance(session, populated_inventory):
    """Recency queries should complete in <200ms."""
    start = time.time()

    get_recent_products(
        ingredient_id=populated_inventory['ingredient'].id,
        session=session
    )

    elapsed = (time.time() - start) * 1000  # ms
    assert elapsed < 200, f"Query took {elapsed}ms, expected <200ms"
```

### Subtask T083 – User acceptance testing

**Purpose**: Manual validation with real user.

**UAT Checklist**:
```markdown
## UAT Checklist - Streamlined Inventory Entry

### Setup
- [ ] Application starts successfully
- [ ] Navigate to Inventory tab
- [ ] Click "Add Inventory" button

### Type-Ahead (User Story 2)
- [ ] Type "bak" in Category - filters to Baking
- [ ] Type "ap" in Ingredient - shows All-Purpose Flour first
- [ ] Type "gold" in Product - filters to Gold Medal products
- [ ] Word boundary matching works (AP matches All-Purpose)

### Session Memory (User Story 1)
- [ ] Add item with Costco supplier
- [ ] Close and reopen dialog - Costco pre-selected with ⭐
- [ ] Add item with Baking category
- [ ] Close and reopen - Baking pre-selected
- [ ] Cancel dialog - session NOT updated
- [ ] After Add, fields clear except category/supplier

### Recency (User Story 3)
- [ ] Recent products appear with ⭐ at top of dropdown
- [ ] Recent ingredients appear with ⭐ at top
- [ ] Separator visible between recent and non-recent

### Inline Creation (User Story 4)
- [ ] Click [+ New Product] - form expands
- [ ] Ingredient pre-filled (read-only)
- [ ] Supplier pre-filled from session
- [ ] Unit pre-filled based on category
- [ ] Create product - appears in dropdown, selected
- [ ] Cancel - form collapses, no product created

### Price Suggestions (User Story 5)
- [ ] Select product with history - price pre-fills
- [ ] Hint shows "(last paid: $X.XX on MM/DD)"
- [ ] Select different supplier - fallback hint with supplier name
- [ ] No history - shows "(no purchase history)"
- [ ] Type in price - hint clears

### Validation (User Story 6)
- [ ] Enter $150 - confirmation dialog appears
- [ ] Confirm - price accepted
- [ ] Reject - focus returns to price field
- [ ] Enter -5.00 - error message, blocked
- [ ] Enter 1.5 for "bag" unit - warning appears

### Performance
- [ ] Dialog opens quickly (<1 second)
- [ ] Type-ahead filtering is instant
- [ ] No noticeable lag on any operation

### Complete Workflow
- [ ] Add 10 items from same supplier
- [ ] Measure time - should be under 5 minutes
- [ ] All items added correctly
```

## Test Strategy

Run tests with:
```bash
# All tests
pytest src/tests -v

# Integration tests only
pytest src/tests/integration -v

# With coverage
pytest src/tests -v --cov=src
```

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Flaky UI tests | Use proper waits |
| Performance regression | Baseline metrics |
| UAT failures | Iterate on feedback |

## Definition of Done Checklist

- [ ] Integration test file created
- [ ] Type-ahead workflow tested
- [ ] Session persistence tested
- [ ] Inline creation tested
- [ ] Price suggestions tested
- [ ] Tab navigation tested
- [ ] All existing tests pass (regression)
- [ ] Recency queries under 200ms
- [ ] UAT completed and passed

## Review Guidance

**Reviewers should verify**:
1. Integration tests cover all user stories
2. No regressions in existing functionality
3. Performance meets targets
4. UAT checklist completed

## Activity Log

- 2025-12-24T23:15:00Z – system – lane=planned – Prompt created.
- 2025-12-25T05:41:56Z – claude – shell_pid=33920 – lane=doing – Starting integration testing and polish
