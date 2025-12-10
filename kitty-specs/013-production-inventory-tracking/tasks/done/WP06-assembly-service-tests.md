---
work_package_id: "WP06"
subtasks:
  - "T028"
  - "T029"
  - "T030"
  - "T031"
  - "T032"
  - "T033"
  - "T034"
  - "T035"
title: "Assembly Service - Tests"
phase: "Phase 3 - Assembly"
lane: "done"
assignee: ""
agent: "claude-reviewer"
shell_pid: "17214"
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-09T17:30:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP06 - Assembly Service - Tests

## Objectives & Success Criteria

Achieve >70% test coverage for AssemblyService with comprehensive test scenarios covering:
- Happy path for check_can_assemble and record_assembly
- Component availability: FinishedUnit, packaging, nested FinishedGood
- Error cases: insufficient inventory, FinishedGood not found
- Rollback on failure

**Success Criteria**:
- [ ] All tests pass
- [ ] Coverage >= 70% for assembly_service.py
- [ ] Tests verify all component types handled correctly
- [ ] Tests verify inventory changes
- [ ] Tests verify rollback on failure

## Context & Constraints

**Reference Documents**:
- `kitty-specs/013-production-inventory-tracking/spec.md` - User Story 3 & 4 acceptance scenarios
- `src/models/composition.py` - Composition model for fixtures

**Test Requirements from spec.md**:
1. Sufficient FU and packaging -> can_assemble=True
2. Insufficient FU -> can_assemble=False with details
3. Insufficient packaging -> can_assemble=False with details
4. Record assembly -> FU decremented, packaging consumed via FIFO, FG incremented
5. Nested FG components -> handled correctly
6. Insufficient during record -> rollback

## Subtasks & Detailed Guidance

### Subtask T028 - Create test file structure
- **Purpose**: Set up test file with fixtures
- **File**: `src/tests/test_assembly_service.py`
- **Parallel?**: No (prerequisite)

**Fixtures Needed**:
```python
@pytest.fixture
def finished_unit_cookie(db_session, recipe_cookies):
    """FinishedUnit with inventory."""
    fu = FinishedUnit(
        recipe=recipe_cookies,
        display_name="Sugar Cookie",
        inventory_count=100,
        unit_cost=Decimal("0.25"),
        ...
    )
    db_session.add(fu)
    db_session.commit()
    return fu

@pytest.fixture
def packaging_product(db_session, ingredient_cellophane):
    """Packaging product with inventory."""
    product = Product(name="Cellophane Bags", ingredient=ingredient_cellophane, ...)
    db_session.add(product)
    inv = InventoryItem(product=product, quantity=Decimal("50.0"), ...)
    db_session.add(inv)
    db_session.commit()
    return product

@pytest.fixture
def finished_good_gift_bag(db_session, finished_unit_cookie, packaging_product):
    """FinishedGood with composition: 12 cookies + 1 bag."""
    fg = FinishedGood(
        name="Cookie Gift Bag",
        inventory_count=0,
        ...
    )
    db_session.add(fg)
    db_session.flush()

    # Add FinishedUnit component
    comp1 = Composition(
        assembly_id=fg.id,
        finished_unit_id=finished_unit_cookie.id,
        component_quantity=12
    )
    # Add packaging component
    comp2 = Composition(
        assembly_id=fg.id,
        packaging_product_id=packaging_product.id,
        component_quantity=1
    )
    db_session.add_all([comp1, comp2])
    db_session.commit()
    return fg
```

### Subtask T029 - Test check_can_assemble - sufficient components
- **Purpose**: Verify availability check with all components available
- **Parallel?**: Yes

**Test**:
```python
def test_check_can_assemble_sufficient(finished_good_gift_bag, finished_unit_cookie, packaging_product):
    """Sufficient FU and packaging returns can_assemble=True."""
    result = assembly_service.check_can_assemble(
        finished_good_id=finished_good_gift_bag.id,
        quantity=5  # Needs 60 cookies (have 100), 5 bags (have 50)
    )
    assert result["can_assemble"] is True
    assert result["missing"] == []
```

### Subtask T030 - Test check_can_assemble - insufficient FinishedUnit
- **Purpose**: Verify missing FinishedUnit reported correctly
- **Parallel?**: Yes

**Test**:
```python
def test_check_can_assemble_insufficient_fu(finished_good_gift_bag, finished_unit_cookie):
    """Insufficient FinishedUnit returns missing details."""
    result = assembly_service.check_can_assemble(
        finished_good_id=finished_good_gift_bag.id,
        quantity=10  # Needs 120 cookies, have 100
    )
    assert result["can_assemble"] is False
    assert any(m["component_type"] == "finished_unit" for m in result["missing"])
    fu_missing = next(m for m in result["missing"] if m["component_type"] == "finished_unit")
    assert fu_missing["needed"] == 120
    assert fu_missing["available"] == 100
```

### Subtask T031 - Test check_can_assemble - insufficient packaging
- **Purpose**: Verify missing packaging reported correctly
- **Parallel?**: Yes

**Test**:
```python
def test_check_can_assemble_insufficient_packaging(finished_good_gift_bag, packaging_product, db_session):
    """Insufficient packaging returns missing details."""
    # Reduce packaging inventory
    inv = db_session.query(InventoryItem).filter_by(product_id=packaging_product.id).first()
    inv.quantity = Decimal("3.0")  # Only 3 bags
    db_session.commit()

    result = assembly_service.check_can_assemble(
        finished_good_id=finished_good_gift_bag.id,
        quantity=5  # Needs 5 bags, have 3
    )
    assert result["can_assemble"] is False
    assert any(m["component_type"] == "packaging" for m in result["missing"])
```

### Subtask T032 - Test record_assembly - happy path
- **Purpose**: Verify full assembly recording
- **Parallel?**: Yes

**Test**:
```python
def test_record_assembly_happy_path(finished_good_gift_bag, finished_unit_cookie, packaging_product):
    """Record assembly: FU decremented, packaging consumed, FG incremented."""
    initial_fu_count = finished_unit_cookie.inventory_count
    initial_fg_count = finished_good_gift_bag.inventory_count

    result = assembly_service.record_assembly(
        finished_good_id=finished_good_gift_bag.id,
        quantity=5,
        notes="Test assembly"
    )

    assert result["assembly_run_id"] is not None
    assert result["quantity_assembled"] == 5
    assert result["total_component_cost"] > Decimal("0")

    # Verify FinishedUnit decremented (12 * 5 = 60)
    with session_scope() as session:
        fu = session.get(FinishedUnit, finished_unit_cookie.id)
        assert fu.inventory_count == initial_fu_count - 60

    # Verify FinishedGood incremented
    with session_scope() as session:
        fg = session.get(FinishedGood, finished_good_gift_bag.id)
        assert fg.inventory_count == initial_fg_count + 5

    # Verify consumption records created
    with session_scope() as session:
        fu_consumptions = session.query(AssemblyFinishedUnitConsumption).filter_by(
            assembly_run_id=result["assembly_run_id"]
        ).all()
        assert len(fu_consumptions) == 1

        pkg_consumptions = session.query(AssemblyPackagingConsumption).filter_by(
            assembly_run_id=result["assembly_run_id"]
        ).all()
        assert len(pkg_consumptions) == 1
```

### Subtask T033 - Test record_assembly - nested FinishedGood
- **Purpose**: Verify nested FinishedGood components handled
- **Parallel?**: Yes

**Additional Fixtures**:
```python
@pytest.fixture
def nested_finished_good(db_session, finished_good_gift_bag):
    """FinishedGood that contains another FinishedGood."""
    # Give the gift bag some inventory
    finished_good_gift_bag.inventory_count = 10
    db_session.commit()

    parent_fg = FinishedGood(name="Deluxe Gift Box", inventory_count=0, ...)
    db_session.add(parent_fg)
    db_session.flush()

    comp = Composition(
        assembly_id=parent_fg.id,
        finished_good_id=finished_good_gift_bag.id,
        component_quantity=2  # 2 gift bags per box
    )
    db_session.add(comp)
    db_session.commit()
    return parent_fg
```

### Subtask T034 - Test record_assembly - insufficient inventory rollback
- **Purpose**: Verify no partial state on failure
- **Parallel?**: Yes

**Test**:
```python
def test_record_assembly_rollback(finished_good_gift_bag, finished_unit_cookie):
    """Insufficient inventory rolls back entire operation."""
    initial_fu_count = finished_unit_cookie.inventory_count
    initial_fg_count = finished_good_gift_bag.inventory_count

    with pytest.raises(InsufficientFinishedUnitError):
        assembly_service.record_assembly(
            finished_good_id=finished_good_gift_bag.id,
            quantity=100  # Needs 1200 cookies, have 100
        )

    # Verify no state changed
    with session_scope() as session:
        fu = session.get(FinishedUnit, finished_unit_cookie.id)
        assert fu.inventory_count == initial_fu_count

        fg = session.get(FinishedGood, finished_good_gift_bag.id)
        assert fg.inventory_count == initial_fg_count
```

### Subtask T035 - Test record_assembly - FinishedGood not found
- **Purpose**: Verify error when FG doesn't exist
- **Parallel?**: Yes

**Test**:
```python
def test_record_assembly_fg_not_found():
    """Non-existent FinishedGood raises error."""
    with pytest.raises(FinishedGoodNotFoundError):
        assembly_service.record_assembly(
            finished_good_id=99999,
            quantity=1
        )
```

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Composition fixture complexity | Build incrementally, test each component type |
| FIFO mock vs real | Use real consume_fifo for integration testing |
| Nested FG edge cases | Test one level of nesting; deeper is rare |

## Definition of Done Checklist

- [ ] T028: Test file structure with fixtures
- [ ] T029-T035: All test scenarios implemented
- [ ] All tests pass
- [ ] Coverage >= 70%
- [ ] `tasks.md` updated

## Review Guidance

**Reviewer Checklist**:
- [ ] Tests cover all component types (FU, FG, packaging)
- [ ] Tests verify inventory changes after operations
- [ ] Rollback test confirms no partial state
- [ ] Fixtures are reusable and well-documented

## Activity Log

- 2025-12-09T17:30:00Z - system - lane=planned - Prompt created.
- 2025-12-10T03:48:55Z – claude – shell_pid=15592 – lane=doing – Implementation complete - 25 tests for assembly_service
- 2025-12-10T03:48:55Z – claude – shell_pid=15592 – lane=for_review – Ready for review - all 25 tests passing
- 2025-12-10T03:54:06Z – claude-reviewer – shell_pid=17214 – lane=done – Review approved: 25 tests covering happy path, errors, edge cases
