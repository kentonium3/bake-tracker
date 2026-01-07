---
work_package_id: "WP08"
subtasks:
  - "T034"
  - "T035"
  - "T036"
  - "T037"
title: "Inventory Update Tests"
phase: "Phase 2 - BT Mobile Workflows"
lane: "for_review"
assignee: ""
agent: "system"
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-06T12:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP08 - Inventory Update Tests

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

- Comprehensive unit tests for inventory update service from WP07
- Cover all edge cases: 0%, 100%, rounding, negative prevention
- Test FIFO selection with multiple inventory items
- Test error handling for missing data scenarios

**Success Criteria**:
- All tests pass
- >90% code coverage of WP07 implementation
- Edge cases documented in test names

## Context & Constraints

**Related Documents**:
- `kitty-specs/040-import-export-v4/tasks/planned/WP07-inventory-update-service.md` - Implementation to test
- `kitty-specs/040-import-export-v4/data-model.md` - JSON schema for test fixtures

**Key Constraints**:
- Use pytest fixtures for test data setup
- Use separate test database/session per test (pytest-isolated)
- Follow existing test patterns in `src/tests/services/`

**File to Modify**: `src/tests/services/test_import_export_service.py`

**Assignee**: Gemini

## Subtasks & Detailed Guidance

### Subtask T034 - Basic unit tests for import_inventory_updates_from_bt_mobile

**Purpose**: Test happy path scenarios.

**Steps**:
1. Create test class `TestInventoryUpdateFromBTMobile`
2. Test cases:
   ```python
   class TestInventoryUpdateFromBTMobile:

       def test_import_inventory_update_50_percent(self, db_session, tmp_path):
           """Test 50% remaining halves current quantity."""
           # Setup: Product with UPC, InventoryItem with quantity=10, Purchase
           product = Product(name="Test", upc_code="123456789012", ...)
           purchase = Purchase(product_id=product.id, quantity_purchased=Decimal("10"))
           inventory = InventoryItem(
               product_id=product.id,
               purchase_id=purchase.id,
               current_quantity=Decimal("10")
           )
           db_session.add_all([product, purchase, inventory])
           db_session.commit()

           # Create JSON file
           data = {
               "schema_version": "4.0",
               "import_type": "inventory_updates",
               "inventory_updates": [
                   {"upc": "123456789012", "percentage_remaining": 50}
               ]
           }
           file_path = tmp_path / "update.json"
           file_path.write_text(json.dumps(data))

           # Execute
           result = import_inventory_updates_from_bt_mobile(str(file_path))

           # Assert
           assert result.success_count == 1
           assert result.error_count == 0

           db_session.refresh(inventory)
           assert inventory.current_quantity == Decimal("5")

       def test_import_creates_depletion_record(self, db_session, tmp_path):
           """Test that InventoryDepletion record is created."""
           # Similar setup, then verify depletion record exists
           ...
   ```

**Files**: `src/tests/services/test_import_export_service.py`
**Parallel?**: Yes - independent of other test subtasks

### Subtask T035 - Test percentage calculation edge cases

**Purpose**: Verify boundary conditions and rounding.

**Steps**:
1. Test cases:
   ```python
   def test_import_inventory_update_0_percent(self, db_session, tmp_path):
       """Test 0% remaining fully depletes inventory."""
       # Setup with quantity=10
       # Assert final quantity = 0

   def test_import_inventory_update_100_percent(self, db_session, tmp_path):
       """Test 100% remaining leaves quantity unchanged."""
       # Setup with quantity=10
       # Assert final quantity = 10 (no depletion record created)

   def test_import_inventory_update_decimal_rounding(self, db_session, tmp_path):
       """Test that percentage calculations maintain precision."""
       # Setup with quantity=10
       # percentage=33 -> target = 3.3, verify Decimal precision

   def test_import_inventory_update_already_partial(self, db_session, tmp_path):
       """Test update when current_quantity < purchase quantity."""
       # Setup: purchase=10, current=7
       # percentage=50 -> target = 5 (based on original 10, not current 7)
       # adjustment = 5 - 7 = -2 (deplete 2)
   ```

**Files**: `src/tests/services/test_import_export_service.py`
**Parallel?**: Yes - independent of other test subtasks

### Subtask T036 - Test FIFO selection with multiple inventory items

**Purpose**: Verify oldest item is selected first.

**Steps**:
1. Test cases:
   ```python
   def test_fifo_selects_oldest_inventory_item(self, db_session, tmp_path):
       """Test that oldest purchase_date is updated first."""
       product = Product(name="Test", upc_code="123456789012", ...)

       # Create two inventory items with different dates
       purchase1 = Purchase(product_id=product.id,
           quantity_purchased=Decimal("10"),
           purchase_date=datetime(2025, 1, 1))
       purchase2 = Purchase(product_id=product.id,
           quantity_purchased=Decimal("10"),
           purchase_date=datetime(2025, 6, 1))

       inv1 = InventoryItem(product_id=product.id, purchase_id=purchase1.id,
           current_quantity=Decimal("10"), purchase_date=datetime(2025, 1, 1))
       inv2 = InventoryItem(product_id=product.id, purchase_id=purchase2.id,
           current_quantity=Decimal("10"), purchase_date=datetime(2025, 6, 1))

       # Import 50% update
       ...

       # Assert: inv1 (oldest) is updated, inv2 unchanged
       db_session.refresh(inv1)
       db_session.refresh(inv2)
       assert inv1.current_quantity == Decimal("5")
       assert inv2.current_quantity == Decimal("10")

   def test_fifo_skips_empty_inventory_items(self, db_session, tmp_path):
       """Test that items with quantity=0 are skipped."""
       # Setup: older item with 0 quantity, newer with 10
       # Assert: newer item is updated (older is skipped)
   ```

**Files**: `src/tests/services/test_import_export_service.py`
**Parallel?**: Yes - independent of other test subtasks

### Subtask T037 - Test error handling

**Purpose**: Verify correct errors for invalid data.

**Steps**:
1. Test cases:
   ```python
   def test_import_inventory_update_no_product(self, db_session, tmp_path):
       """Test error when UPC doesn't match any product."""
       data = {
           "schema_version": "4.0",
           "import_type": "inventory_updates",
           "inventory_updates": [
               {"upc": "999999999999", "percentage_remaining": 50}
           ]
       }
       ...
       result = import_inventory_updates_from_bt_mobile(str(file_path))
       assert result.error_count == 1
       assert "No product found" in str(result.errors[0])

   def test_import_inventory_update_no_inventory(self, db_session, tmp_path):
       """Test error when product has no inventory items."""
       # Product exists but no InventoryItem records
       ...
       assert "No inventory with remaining quantity" in str(result.errors[0])

   def test_import_inventory_update_no_purchase(self, db_session, tmp_path):
       """Test error when inventory item has no linked purchase."""
       # InventoryItem exists but purchase_id is None
       ...
       assert "no linked purchase" in str(result.errors[0])

   def test_import_inventory_update_negative_result(self, db_session, tmp_path):
       """Test error when adjustment would go negative."""
       # Setup: purchase=10, current=3, percentage=50 -> target=5
       # This should succeed (3 + (5-3) = 5)
       # But if current=3 and target=10 (100%), that's +7 addition
       # Real negative: current=3, target calculated from wrong base?
       # Actually, test: manually corrupt data to trigger
       ...

   def test_import_inventory_update_invalid_percentage(self, db_session, tmp_path):
       """Test error for percentage outside 0-100 range."""
       data = {
           "schema_version": "4.0",
           "import_type": "inventory_updates",
           "inventory_updates": [
               {"upc": "123456789012", "percentage_remaining": 150}
           ]
       }
       ...
       assert "Invalid percentage" in str(result.errors[0])

   def test_import_inventory_update_wrong_schema_version(self, db_session, tmp_path):
       """Test error for wrong schema version."""
       data = {"schema_version": "3.5", "import_type": "inventory_updates", ...}
       ...
       assert "Unsupported schema version" in str(result.errors[0])

   def test_import_inventory_update_wrong_import_type(self, db_session, tmp_path):
       """Test error for wrong import type."""
       data = {"schema_version": "4.0", "import_type": "purchases", ...}
       ...
       assert "Wrong import type" in str(result.errors[0])
   ```

**Files**: `src/tests/services/test_import_export_service.py`
**Parallel?**: Yes - independent of other test subtasks

## Test Strategy

**Required Tests**:
```bash
pytest src/tests/services/test_import_export_service.py::TestInventoryUpdateFromBTMobile -v --cov=src/services/import_export_service
```

**Coverage Target**: >90% of `import_inventory_updates_from_bt_mobile` function

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Test isolation | Use pytest fixtures with db_session rollback |
| Flaky tests | Avoid time-dependent assertions |
| Missing edge cases | Review function branches for coverage |

## Definition of Done Checklist

- [ ] T034: Basic happy path tests pass
- [ ] T035: Edge case tests (0%, 100%, rounding) pass
- [ ] T036: FIFO selection tests pass
- [ ] T037: Error handling tests pass
- [ ] >90% coverage of WP07 code
- [ ] All tests run in isolation

## Review Guidance

- Check test names are descriptive
- Verify assertions match expected behavior from WP07
- Confirm test data setup is clear and minimal
- Look for missing edge cases

## Activity Log

- 2026-01-06T12:00:00Z - system - lane=planned - Prompt created.
- 2026-01-07T03:39:50Z – system – shell_pid= – lane=doing – Moved to doing
- 2026-01-07T03:42:42Z – system – shell_pid= – lane=for_review – Moved to for_review
