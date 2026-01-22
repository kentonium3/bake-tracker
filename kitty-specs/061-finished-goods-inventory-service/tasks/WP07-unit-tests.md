---
work_package_id: "WP07"
subtasks:
  - "T024"
  - "T025"
  - "T026"
  - "T027"
title: "Unit Tests"
phase: "Phase 5 - Testing"
lane: "done"
assignee: ""
agent: "claude-opus"
shell_pid: "32657"
review_status: "approved"
reviewed_by: "Kent Gale"
dependencies: ["WP03"]
history:
  - timestamp: "2026-01-21T19:33:38Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP07 - Unit Tests

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.

---

## Review Feedback

> **Populated by `/spec-kitty.review`**

*[This section is empty initially.]*

---

## Implementation Command

```bash
spec-kitty implement WP07 --base WP06
```

Depends on WP03 (all service functions implemented). Can start after WP03 but best done after WP06.

---

## Objectives & Success Criteria

- ✅ Unit tests for all 6 service functions
- ✅ Tests cover happy path, edge cases, and error conditions
- ✅ Tests verify session handling (with and without session parameter)
- ✅ Tests achieve >70% coverage of service module
- ✅ All tests pass

## Context & Constraints

**Reference Documents**:
- `kitty-specs/061-finished-goods-inventory-service/plan.md` - Test plan section
- `src/tests/services/test_assembly_service.py` - Example test patterns
- `src/tests/conftest.py` - Available fixtures

**Key Constraints**:
- Use existing test fixtures for FinishedUnit and FinishedGood
- Test with AND without session parameter
- Test all filtering combinations for query functions
- Test error cases thoroughly

---

## Subtasks & Detailed Guidance

### Subtask T024 - Unit tests for get_inventory_status()

**Purpose**: Comprehensive tests for inventory status query function.

**Steps**:
1. Create `src/tests/services/test_finished_goods_inventory_service.py`
2. Add imports and fixtures:
   ```python
   import pytest
   from decimal import Decimal
   from src.services import finished_goods_inventory_service as fg_inv
   from src.database import session_scope
   from src.models import FinishedUnit, FinishedGood
   ```
3. Write tests for each scenario

**Test Cases**:

```python
class TestGetInventoryStatus:
    """Tests for get_inventory_status()"""

    def test_get_all_items(self, db_session, sample_finished_unit, sample_finished_good):
        """Returns both FU and FG when no filter"""
        result = fg_inv.get_inventory_status(session=db_session)
        assert len(result) >= 2
        types = {r["item_type"] for r in result}
        assert "finished_unit" in types
        assert "finished_good" in types

    def test_filter_by_finished_unit(self, db_session, sample_finished_unit):
        """Returns only FinishedUnits when filtered"""
        result = fg_inv.get_inventory_status(item_type="finished_unit", session=db_session)
        assert all(r["item_type"] == "finished_unit" for r in result)

    def test_filter_by_finished_good(self, db_session, sample_finished_good):
        """Returns only FinishedGoods when filtered"""
        result = fg_inv.get_inventory_status(item_type="finished_good", session=db_session)
        assert all(r["item_type"] == "finished_good" for r in result)

    def test_filter_by_item_id(self, db_session, sample_finished_unit):
        """Returns specific item when filtered by ID"""
        result = fg_inv.get_inventory_status(
            item_type="finished_unit",
            item_id=sample_finished_unit.id,
            session=db_session
        )
        assert len(result) == 1
        assert result[0]["id"] == sample_finished_unit.id

    def test_exclude_zero_inventory(self, db_session, sample_finished_unit):
        """Excludes items with zero inventory when flag set"""
        sample_finished_unit.inventory_count = 0
        db_session.flush()

        result = fg_inv.get_inventory_status(exclude_zero=True, session=db_session)
        assert all(r["inventory_count"] > 0 for r in result)

    def test_invalid_item_type_raises(self, db_session):
        """Raises ValueError for invalid item_type"""
        with pytest.raises(ValueError, match="Invalid item_type"):
            fg_inv.get_inventory_status(item_type="invalid", session=db_session)

    def test_item_id_without_type_raises(self, db_session):
        """Raises ValueError when item_id provided without item_type"""
        with pytest.raises(ValueError, match="item_id requires item_type"):
            fg_inv.get_inventory_status(item_id=1, session=db_session)

    def test_returns_dict_structure(self, db_session, sample_finished_unit):
        """Returns proper dict structure with all fields"""
        result = fg_inv.get_inventory_status(
            item_type="finished_unit",
            item_id=sample_finished_unit.id,
            session=db_session
        )
        item = result[0]
        assert "item_type" in item
        assert "id" in item
        assert "slug" in item
        assert "display_name" in item
        assert "inventory_count" in item
        assert "current_cost" in item
        assert "total_value" in item
        assert isinstance(item["current_cost"], Decimal)
        assert isinstance(item["total_value"], Decimal)

    def test_works_without_session(self, sample_finished_unit):
        """Works when session=None (creates own transaction)"""
        result = fg_inv.get_inventory_status(item_type="finished_unit")
        assert isinstance(result, list)
```

**Files**:
- `src/tests/services/test_finished_goods_inventory_service.py` (new file, ~100 lines for this subtask)

**Validation**:
- [ ] All filtering scenarios tested
- [ ] Error cases tested
- [ ] Dict structure verified
- [ ] Session handling tested

---

### Subtask T025 - Unit tests for check_availability() and validate_consumption()

**Purpose**: Tests for availability checking functions.

**Test Cases**:

```python
class TestCheckAvailability:
    """Tests for check_availability()"""

    def test_available_when_sufficient(self, db_session, sample_finished_unit):
        """Returns available=True when sufficient inventory"""
        sample_finished_unit.inventory_count = 10
        db_session.flush()

        result = fg_inv.check_availability("finished_unit", sample_finished_unit.id, 5, session=db_session)
        assert result["available"] is True
        assert result["current_count"] == 10
        assert result["requested"] == 5
        assert "shortage" not in result

    def test_unavailable_when_insufficient(self, db_session, sample_finished_unit):
        """Returns available=False with shortage when insufficient"""
        sample_finished_unit.inventory_count = 5
        db_session.flush()

        result = fg_inv.check_availability("finished_unit", sample_finished_unit.id, 10, session=db_session)
        assert result["available"] is False
        assert result["shortage"] == 5

    def test_item_not_found_raises(self, db_session):
        """Raises ValueError when item doesn't exist"""
        with pytest.raises(ValueError, match="not found"):
            fg_inv.check_availability("finished_unit", 99999, 5, session=db_session)

    def test_invalid_item_type_raises(self, db_session):
        """Raises ValueError for invalid item_type"""
        with pytest.raises(ValueError, match="Invalid item_type"):
            fg_inv.check_availability("invalid", 1, 5, session=db_session)

    def test_zero_quantity_raises(self, db_session, sample_finished_unit):
        """Raises ValueError for zero quantity"""
        with pytest.raises(ValueError, match="positive"):
            fg_inv.check_availability("finished_unit", sample_finished_unit.id, 0, session=db_session)


class TestValidateConsumption:
    """Tests for validate_consumption()"""

    def test_valid_when_sufficient(self, db_session, sample_finished_unit):
        """Returns valid=True with remaining_after when sufficient"""
        sample_finished_unit.inventory_count = 10
        db_session.flush()

        result = fg_inv.validate_consumption("finished_unit", sample_finished_unit.id, 3, session=db_session)
        assert result["valid"] is True
        assert result["remaining_after"] == 7

    def test_invalid_when_insufficient(self, db_session, sample_finished_unit):
        """Returns valid=False with error message when insufficient"""
        sample_finished_unit.inventory_count = 2
        db_session.flush()

        result = fg_inv.validate_consumption("finished_unit", sample_finished_unit.id, 5, session=db_session)
        assert result["valid"] is False
        assert "error" in result
        assert result["shortage"] == 3
```

**Files**:
- `src/tests/services/test_finished_goods_inventory_service.py` (add ~80 lines)

**Validation**:
- [ ] Sufficient inventory cases tested
- [ ] Insufficient inventory cases tested
- [ ] Error cases tested
- [ ] Return structure verified

---

### Subtask T026 - Unit tests for adjust_inventory()

**Purpose**: Comprehensive tests for the core mutation function.

**Test Cases**:

```python
class TestAdjustInventory:
    """Tests for adjust_inventory()"""

    def test_positive_adjustment(self, db_session, sample_finished_unit):
        """Positive quantity increases inventory"""
        initial = sample_finished_unit.inventory_count = 10
        db_session.flush()

        result = fg_inv.adjust_inventory(
            "finished_unit", sample_finished_unit.id, 5, "production",
            notes="Test", session=db_session
        )

        assert result["success"] is True
        assert result["previous_count"] == 10
        assert result["new_count"] == 15
        assert result["quantity_change"] == 5
        assert sample_finished_unit.inventory_count == 15

    def test_negative_adjustment(self, db_session, sample_finished_unit):
        """Negative quantity decreases inventory"""
        sample_finished_unit.inventory_count = 10
        db_session.flush()

        result = fg_inv.adjust_inventory(
            "finished_unit", sample_finished_unit.id, -3, "consumption",
            notes="Test", session=db_session
        )

        assert result["new_count"] == 7
        assert sample_finished_unit.inventory_count == 7

    def test_creates_audit_record(self, db_session, sample_finished_unit):
        """Creates FinishedGoodsAdjustment record"""
        from src.models import FinishedGoodsAdjustment

        sample_finished_unit.inventory_count = 10
        db_session.flush()

        result = fg_inv.adjust_inventory(
            "finished_unit", sample_finished_unit.id, 5, "production",
            notes="Test production", session=db_session
        )

        adjustment = db_session.query(FinishedGoodsAdjustment).get(result["adjustment_id"])
        assert adjustment is not None
        assert adjustment.finished_unit_id == sample_finished_unit.id
        assert adjustment.finished_good_id is None  # XOR
        assert adjustment.quantity_change == 5
        assert adjustment.previous_count == 10
        assert adjustment.new_count == 15
        assert adjustment.reason == "production"
        assert adjustment.notes == "Test production"

    def test_prevents_negative_inventory(self, db_session, sample_finished_unit):
        """Raises ValueError when adjustment would cause negative inventory"""
        sample_finished_unit.inventory_count = 5
        db_session.flush()

        with pytest.raises(ValueError, match="negative inventory"):
            fg_inv.adjust_inventory(
                "finished_unit", sample_finished_unit.id, -10, "consumption",
                notes="Test", session=db_session
            )

        # Verify inventory unchanged
        assert sample_finished_unit.inventory_count == 5

    def test_invalid_reason_raises(self, db_session, sample_finished_unit):
        """Raises ValueError for invalid reason"""
        with pytest.raises(ValueError, match="Invalid reason"):
            fg_inv.adjust_inventory(
                "finished_unit", sample_finished_unit.id, 5, "invalid_reason",
                session=db_session
            )

    def test_adjustment_reason_requires_notes(self, db_session, sample_finished_unit):
        """Raises ValueError when reason is 'adjustment' but notes not provided"""
        with pytest.raises(ValueError, match="Notes are required"):
            fg_inv.adjust_inventory(
                "finished_unit", sample_finished_unit.id, 5, "adjustment",
                session=db_session
            )

    def test_adjustment_reason_with_notes_succeeds(self, db_session, sample_finished_unit):
        """Succeeds when reason is 'adjustment' with notes"""
        sample_finished_unit.inventory_count = 10
        db_session.flush()

        result = fg_inv.adjust_inventory(
            "finished_unit", sample_finished_unit.id, 2, "adjustment",
            notes="Manual correction for count error", session=db_session
        )

        assert result["success"] is True

    def test_works_with_finished_good(self, db_session, sample_finished_good):
        """Works for finished_good item type"""
        sample_finished_good.inventory_count = 5
        db_session.flush()

        result = fg_inv.adjust_inventory(
            "finished_good", sample_finished_good.id, 3, "assembly",
            notes="Test", session=db_session
        )

        assert result["item_type"] == "finished_good"
        assert sample_finished_good.inventory_count == 8

    def test_works_without_session(self, sample_finished_unit):
        """Works when session=None (creates own transaction)"""
        # Need to use fresh query since different session
        result = fg_inv.adjust_inventory(
            "finished_unit", sample_finished_unit.id, 1, "production",
            notes="Test"
        )
        assert result["success"] is True
```

**Files**:
- `src/tests/services/test_finished_goods_inventory_service.py` (add ~120 lines)

**Validation**:
- [ ] Positive and negative adjustments tested
- [ ] Audit record creation verified
- [ ] Negative inventory prevention tested
- [ ] Invalid reason handling tested
- [ ] Notes requirement for "adjustment" reason tested
- [ ] Both item types tested
- [ ] Session handling tested

---

### Subtask T027 - Unit tests for get_low_stock_items() and get_total_inventory_value()

**Purpose**: Tests for aggregation and reporting functions.

**Test Cases**:

```python
class TestGetLowStockItems:
    """Tests for get_low_stock_items()"""

    def test_default_threshold(self, db_session, sample_finished_unit):
        """Uses DEFAULT_LOW_STOCK_THRESHOLD when none provided"""
        from src.utils.constants import DEFAULT_LOW_STOCK_THRESHOLD

        sample_finished_unit.inventory_count = DEFAULT_LOW_STOCK_THRESHOLD - 1
        db_session.flush()

        result = fg_inv.get_low_stock_items(session=db_session)
        assert any(r["id"] == sample_finished_unit.id for r in result)

    def test_custom_threshold(self, db_session, sample_finished_unit):
        """Uses custom threshold when provided"""
        sample_finished_unit.inventory_count = 15
        db_session.flush()

        result = fg_inv.get_low_stock_items(threshold=20, session=db_session)
        assert any(r["id"] == sample_finished_unit.id for r in result)

    def test_filter_by_item_type(self, db_session, sample_finished_unit, sample_finished_good):
        """Filters by item type"""
        sample_finished_unit.inventory_count = 2
        sample_finished_good.inventory_count = 2
        db_session.flush()

        result = fg_inv.get_low_stock_items(item_type="finished_unit", session=db_session)
        assert all(r["item_type"] == "finished_unit" for r in result)

    def test_ordered_by_count_ascending(self, db_session):
        """Results ordered by inventory_count ascending"""
        result = fg_inv.get_low_stock_items(threshold=100, session=db_session)
        counts = [r["inventory_count"] for r in result]
        assert counts == sorted(counts)


class TestGetTotalInventoryValue:
    """Tests for get_total_inventory_value()"""

    def test_returns_all_fields(self, db_session, sample_finished_unit, sample_finished_good):
        """Returns dict with all required fields"""
        result = fg_inv.get_total_inventory_value(session=db_session)

        assert "finished_units_value" in result
        assert "finished_goods_value" in result
        assert "total_value" in result
        assert "finished_units_count" in result
        assert "finished_goods_count" in result
        assert "total_items_count" in result

    def test_values_are_decimal(self, db_session, sample_finished_unit):
        """Value fields are Decimal type"""
        result = fg_inv.get_total_inventory_value(session=db_session)

        assert isinstance(result["finished_units_value"], Decimal)
        assert isinstance(result["finished_goods_value"], Decimal)
        assert isinstance(result["total_value"], Decimal)

    def test_counts_are_int(self, db_session, sample_finished_unit):
        """Count fields are int type"""
        result = fg_inv.get_total_inventory_value(session=db_session)

        assert isinstance(result["finished_units_count"], int)
        assert isinstance(result["finished_goods_count"], int)
        assert isinstance(result["total_items_count"], int)

    def test_total_is_sum(self, db_session, sample_finished_unit, sample_finished_good):
        """total_value equals sum of unit and good values"""
        result = fg_inv.get_total_inventory_value(session=db_session)

        expected_total = result["finished_units_value"] + result["finished_goods_value"]
        assert result["total_value"] == expected_total

    def test_empty_database(self, db_session):
        """Returns zeros for empty database"""
        # Clear any test data
        # ... (may need cleanup fixture)

        result = fg_inv.get_total_inventory_value(session=db_session)
        # Values may be zero or reflect only test fixtures
        assert result["total_value"] >= Decimal("0")
```

**Files**:
- `src/tests/services/test_finished_goods_inventory_service.py` (add ~80 lines)

**Validation**:
- [ ] Default threshold tested
- [ ] Custom threshold tested
- [ ] Ordering verified
- [ ] Return structure verified
- [ ] Type checking for Decimal/int

---

## Test Strategy

Run tests incrementally:

```bash
# Run just the new test file
./run-tests.sh src/tests/services/test_finished_goods_inventory_service.py -v

# Run with coverage
./run-tests.sh src/tests/services/test_finished_goods_inventory_service.py -v --cov=src/services/finished_goods_inventory_service --cov-report=term-missing

# Target: >70% coverage
```

**Fixture Requirements**:
- `db_session` - Database session (from conftest.py)
- `sample_finished_unit` - FinishedUnit instance with inventory
- `sample_finished_good` - FinishedGood instance with inventory

Check existing fixtures in `src/tests/conftest.py` and `src/tests/services/test_assembly_service.py` for patterns.

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Missing fixtures | Create new fixtures or reuse existing |
| Session isolation issues | Use db_session fixture properly |
| Coverage below target | Add edge case tests |

---

## Definition of Done Checklist

- [ ] T024: get_inventory_status tests complete
- [ ] T025: check_availability and validate_consumption tests complete
- [ ] T026: adjust_inventory tests complete
- [ ] T027: get_low_stock_items and get_total_inventory_value tests complete
- [ ] All tests pass
- [ ] Coverage >70% for service module
- [ ] Tests verify session handling (with and without)

---

## Review Guidance

**Key checkpoints**:
1. All service functions have test coverage
2. Happy path, edge cases, and error conditions tested
3. Session handling tested both ways
4. Decimal/int types verified where relevant
5. Test patterns consistent with existing test files

---

## Activity Log

- 2026-01-21T19:33:38Z - system - lane=planned - Prompt created.
- 2026-01-22T03:38:08Z - claude-opus - shell_pid=29038 - lane=doing - Started implementation via workflow command
- 2026-01-22T03:46:47Z - claude-opus - shell_pid=29038 - lane=for_review - Ready for review: Added 42 unit tests covering all 6 service functions. Tests verify happy path, edge cases, error handling, and session management. All 2581 tests pass.
- 2026-01-22T03:50:47Z - claude-opus - shell_pid=32657 - lane=doing - Started review via workflow command
- 2026-01-22T03:52:03Z - claude-opus - shell_pid=32657 - lane=done - Review passed: All 42 unit tests pass. Tests cover all 6 service functions with comprehensive happy path, edge cases, and error handling. Session handling tested both ways. Audit record creation verified. Type checking for Decimal/int verified.
