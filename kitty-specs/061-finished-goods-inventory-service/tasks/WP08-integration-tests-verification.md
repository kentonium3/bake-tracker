---
work_package_id: "WP08"
subtasks:
  - "T028"
  - "T029"
  - "T030"
  - "T031"
  - "T032"
title: "Integration Tests and Verification"
phase: "Phase 5 - Testing"
lane: "doing"
assignee: ""
agent: "claude-opus"
shell_pid: "40128"
review_status: ""
reviewed_by: ""
dependencies: ["WP04", "WP05", "WP06", "WP07"]
history:
  - timestamp: "2026-01-21T19:33:38Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP08 – Integration Tests and Verification

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
spec-kitty implement WP08 --base WP07
```

Depends on WP04, WP05, WP06, WP07 (all integration complete, cleanup done, unit tests established).

---

## Objectives & Success Criteria

- ✅ Integration test for complete assembly flow with audit trail
- ✅ Integration test for production flow with audit trail
- ✅ Session atomicity tests verify rollback behavior
- ✅ Export/import tests verify inventory preservation
- ✅ All tests pass

## Context & Constraints

**Reference Documents**:
- `kitty-specs/061-finished-goods-inventory-service/plan.md` - Integration test plan
- `src/tests/integration/` - Existing integration test patterns
- `src/tests/services/test_assembly_service.py` - Assembly test patterns

**Key Constraints**:
- Integration tests may need more complex fixtures
- Test full flow from start to finish
- Verify audit records created for all inventory changes
- Test atomicity (rollback on failure)

---

## Subtasks & Detailed Guidance

### Subtask T028 – Integration test for assembly service with inventory service

**Purpose**: Verify full assembly flow creates proper audit trail.

**Steps**:
1. Create `src/tests/integration/test_finished_goods_inventory_integration.py` (or add to existing)
2. Write test that:
   - Creates FinishedUnit with inventory
   - Creates FinishedGood that uses the FinishedUnit
   - Runs assembly
   - Verifies inventory counts changed
   - Verifies FinishedGoodsAdjustment records created

**Test Case**:

```python
class TestAssemblyIntegration:
    """Integration tests for assembly service with inventory tracking"""

    def test_assembly_creates_audit_trail(
        self, db_session, sample_finished_unit, sample_finished_good_with_unit_component
    ):
        """Assembly creates adjustment records for all inventory changes"""
        from src.models import FinishedGoodsAdjustment
        from src.services import assembly_service

        # Setup: Set inventory counts
        sample_finished_unit.inventory_count = 20
        sample_finished_good_with_unit_component.inventory_count = 0
        db_session.flush()

        initial_adjustment_count = db_session.query(FinishedGoodsAdjustment).count()

        # Act: Perform assembly
        result = assembly_service.record_assembly(
            finished_good_id=sample_finished_good_with_unit_component.id,
            quantity=2,
            session=db_session
        )

        # Assert: Audit records created
        final_adjustment_count = db_session.query(FinishedGoodsAdjustment).count()
        assert final_adjustment_count > initial_adjustment_count

        # Verify FU consumption recorded
        fu_adjustments = db_session.query(FinishedGoodsAdjustment).filter_by(
            finished_unit_id=sample_finished_unit.id,
            reason="assembly"
        ).all()
        assert len(fu_adjustments) >= 1
        assert any(adj.quantity_change < 0 for adj in fu_adjustments)  # Consumption

        # Verify FG creation recorded
        fg_adjustments = db_session.query(FinishedGoodsAdjustment).filter_by(
            finished_good_id=sample_finished_good_with_unit_component.id,
            reason="assembly"
        ).all()
        assert len(fg_adjustments) >= 1
        assert any(adj.quantity_change > 0 for adj in fg_adjustments)  # Creation

    def test_assembly_inventory_counts_correct(
        self, db_session, sample_finished_unit, sample_finished_good_with_unit_component
    ):
        """Assembly correctly updates inventory counts"""
        from src.services import assembly_service

        # Setup
        sample_finished_unit.inventory_count = 20
        sample_finished_good_with_unit_component.inventory_count = 5
        db_session.flush()

        fu_initial = sample_finished_unit.inventory_count
        fg_initial = sample_finished_good_with_unit_component.inventory_count

        # Get the component requirement
        component = sample_finished_good_with_unit_component.components[0]
        units_per_assembly = component.quantity

        # Act: Assemble 2
        assembly_service.record_assembly(
            finished_good_id=sample_finished_good_with_unit_component.id,
            quantity=2,
            session=db_session
        )

        # Assert
        db_session.refresh(sample_finished_unit)
        db_session.refresh(sample_finished_good_with_unit_component)

        assert sample_finished_unit.inventory_count == fu_initial - (units_per_assembly * 2)
        assert sample_finished_good_with_unit_component.inventory_count == fg_initial + 2
```

**Files**:
- `src/tests/integration/test_finished_goods_inventory_integration.py` (new or modify, ~80 lines)

**Validation**:
- [ ] Full assembly flow tested
- [ ] Audit records verified
- [ ] Inventory counts verified

---

### Subtask T029 – Integration test for production service with inventory service

**Purpose**: Verify production runs create proper audit trail.

**Test Case**:

```python
class TestProductionIntegration:
    """Integration tests for production service with inventory tracking"""

    def test_production_creates_audit_trail(self, db_session, sample_finished_unit):
        """Production run creates adjustment record"""
        from src.models import FinishedGoodsAdjustment
        from src.services import batch_production_service

        # Setup
        sample_finished_unit.inventory_count = 0
        db_session.flush()

        # Act: Record production
        result = batch_production_service.record_batch_production(
            finished_unit_id=sample_finished_unit.id,
            planned_yield=10,
            actual_yield=9,
            session=db_session
        )

        # Assert: Audit record created
        adjustments = db_session.query(FinishedGoodsAdjustment).filter_by(
            finished_unit_id=sample_finished_unit.id,
            reason="production"
        ).all()

        assert len(adjustments) >= 1
        latest = max(adjustments, key=lambda a: a.adjusted_at)
        assert latest.quantity_change == 9
        assert latest.new_count == 9

    def test_production_updates_inventory(self, db_session, sample_finished_unit):
        """Production run updates FinishedUnit inventory_count"""
        from src.services import batch_production_service

        # Setup
        sample_finished_unit.inventory_count = 5
        db_session.flush()

        # Act
        batch_production_service.record_batch_production(
            finished_unit_id=sample_finished_unit.id,
            planned_yield=10,
            actual_yield=8,
            session=db_session
        )

        # Assert
        db_session.refresh(sample_finished_unit)
        assert sample_finished_unit.inventory_count == 13  # 5 + 8
```

**Files**:
- `src/tests/integration/test_finished_goods_inventory_integration.py` (add ~50 lines)

**Validation**:
- [ ] Production flow tested
- [ ] Audit record verified
- [ ] Inventory count updated

---

### Subtask T030 – Session atomicity tests

**Purpose**: Verify multi-step operations roll back on failure.

**Test Case**:

```python
class TestSessionAtomicity:
    """Tests for transactional atomicity"""

    def test_assembly_rollback_on_insufficient_inventory(
        self, db_session, sample_finished_unit, sample_finished_good_with_unit_component
    ):
        """Assembly failure rolls back all changes"""
        from src.services import assembly_service

        # Setup: Not enough inventory
        sample_finished_unit.inventory_count = 1  # Less than needed
        sample_finished_good_with_unit_component.inventory_count = 10
        db_session.flush()

        fu_initial = sample_finished_unit.inventory_count
        fg_initial = sample_finished_good_with_unit_component.inventory_count

        # Act: Try to assemble (should fail)
        with pytest.raises(Exception):  # Adjust exception type as needed
            assembly_service.record_assembly(
                finished_good_id=sample_finished_good_with_unit_component.id,
                quantity=5,  # Needs more FU than available
                session=db_session
            )

        # Assert: No changes persisted
        db_session.refresh(sample_finished_unit)
        db_session.refresh(sample_finished_good_with_unit_component)

        assert sample_finished_unit.inventory_count == fu_initial
        assert sample_finished_good_with_unit_component.inventory_count == fg_initial

    def test_multi_adjustment_atomicity(self, db_session, sample_finished_unit):
        """Multiple adjustments in same session are atomic"""
        from src.services import finished_goods_inventory_service as fg_inv
        from src.models import FinishedGoodsAdjustment

        sample_finished_unit.inventory_count = 100
        db_session.flush()

        # Act: Multiple adjustments in same session
        fg_inv.adjust_inventory(
            "finished_unit", sample_finished_unit.id, -10, "consumption",
            notes="First", session=db_session
        )
        fg_inv.adjust_inventory(
            "finished_unit", sample_finished_unit.id, -5, "consumption",
            notes="Second", session=db_session
        )

        # Don't commit yet - verify session state
        assert sample_finished_unit.inventory_count == 85

        # Rollback
        db_session.rollback()

        # Assert: All changes rolled back
        db_session.refresh(sample_finished_unit)
        assert sample_finished_unit.inventory_count == 100
```

**Files**:
- `src/tests/integration/test_finished_goods_inventory_integration.py` (add ~60 lines)

**Validation**:
- [ ] Failure causes rollback
- [ ] No partial changes persisted
- [ ] Audit records also rolled back

---

### Subtask T031 – Verify export includes inventory_count

**Purpose**: Confirm export functionality preserves inventory data.

**Test Case**:

```python
class TestExportImport:
    """Tests for export/import inventory preservation"""

    def test_export_includes_inventory_count(self, db_session, sample_finished_unit):
        """Exported data includes inventory_count field"""
        from src.services import import_export_service

        # Setup
        sample_finished_unit.inventory_count = 42
        db_session.flush()

        # Act: Export
        export_data = import_export_service.export_all(session=db_session)

        # Assert: Find the finished unit in export
        finished_units = export_data.get("finished_units", [])
        exported_unit = next(
            (u for u in finished_units if u["id"] == sample_finished_unit.id),
            None
        )

        assert exported_unit is not None
        assert exported_unit["inventory_count"] == 42
```

**Files**:
- `src/tests/integration/test_finished_goods_inventory_integration.py` (add ~30 lines)

**Note**: This test may already exist. Check `src/tests/services/test_import_export_service.py` first. If it exists, add an explicit assertion for inventory_count if not present.

**Validation**:
- [ ] inventory_count in export data
- [ ] Value matches database

---

### Subtask T032 – Verify import restores inventory_count

**Purpose**: Confirm import functionality restores inventory data.

**Test Case**:

```python
    def test_import_restores_inventory_count(self, db_session):
        """Imported data restores inventory_count correctly"""
        from src.services import import_export_service
        from src.models import FinishedUnit

        # Setup: Create import data with specific inventory
        import_data = {
            "finished_units": [
                {
                    "slug": "test-import-unit",
                    "display_name": "Test Import Unit",
                    "inventory_count": 99,
                    # ... other required fields
                }
            ]
        }

        # Act: Import
        import_export_service.import_all(import_data, session=db_session)

        # Assert: Find the imported unit
        imported = db_session.query(FinishedUnit).filter_by(
            slug="test-import-unit"
        ).first()

        assert imported is not None
        assert imported.inventory_count == 99
```

**Files**:
- `src/tests/integration/test_finished_goods_inventory_integration.py` (add ~30 lines)

**Note**: This test may need adjustment based on actual import_export_service API.

**Validation**:
- [ ] Import creates record with correct inventory_count
- [ ] Round-trip (export then import) preserves values

---

## Test Strategy

Run integration tests:

```bash
# Run just integration tests
./run-tests.sh src/tests/integration/test_finished_goods_inventory_integration.py -v

# Run all tests to ensure no regressions
./run-tests.sh -v

# Run with coverage for the whole project
./run-tests.sh --cov=src --cov-report=term-missing
```

**Fixture Requirements**:
- More complex fixtures may be needed for nested assemblies
- May need to extend existing fixtures or create new ones

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Complex fixture setup | Reuse existing integration test patterns |
| Import/export API differences | Verify actual service API before writing tests |
| Test isolation | Use database rollback/cleanup between tests |

---

## Definition of Done Checklist

- [ ] T028: Assembly integration test complete
- [ ] T029: Production integration test complete
- [ ] T030: Session atomicity tests complete
- [ ] T031: Export includes inventory_count verified
- [ ] T032: Import restores inventory_count verified
- [ ] All integration tests pass
- [ ] Full test suite passes (no regressions)

---

## Review Guidance

**Key checkpoints**:
1. Integration tests cover full workflows
2. Audit records verified in integration tests
3. Atomicity/rollback behavior tested
4. Export/import preservation verified
5. Tests are isolated and repeatable

---

## Activity Log

- 2026-01-21T19:33:38Z – system – lane=planned – Prompt created.
- 2026-01-22T03:53:00Z – claude-opus – shell_pid=33384 – lane=doing – Started implementation via workflow command
- 2026-01-22T04:08:56Z – claude-opus – shell_pid=33384 – lane=for_review – Ready for review: 14 integration tests covering assembly, production, atomicity, and export/import. All tests pass (13 passed + 1 xfail documenting export gap). Full suite: 2636 tests pass.
- 2026-01-22T04:15:11Z – claude-opus – shell_pid=40128 – lane=doing – Started review via workflow command
