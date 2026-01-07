---
work_package_id: "WP07"
subtasks:
  - "T029"
  - "T030"
  - "T031"
  - "T032"
  - "T033"
title: "Inventory Update Service"
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

# Work Package Prompt: WP07 - Inventory Update Service

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

- Implement `import_inventory_updates_from_bt_mobile(file_path)` function
- UPC matching against Product.upc_code
- FIFO selection of InventoryItem (oldest purchase_date first)
- Percentage-based quantity calculation
- Create InventoryDepletion records for adjustments

**Success Criteria**:
- Import JSON with percentage=50, InventoryItem.current_quantity halved
- Import JSON with percentage=0, InventoryItem fully depleted
- FIFO order verified (oldest item adjusted first)
- ImportResult shows adjustment counts

## Context & Constraints

**Related Documents**:
- `kitty-specs/040-import-export-v4/spec.md` - User Story 4 acceptance criteria
- `kitty-specs/040-import-export-v4/data-model.md` - Inventory update JSON schema
- `kitty-specs/040-import-export-v4/research.md` - Key decisions D5, D6

**Key Constraints**:
- Schema validation: schema_version="4.0", import_type="inventory_updates"
- Use session management pattern from CLAUDE.md
- Product.upc_code is indexed (fast lookup)
- InventoryItem must have linked Purchase for original quantity
- Use Decimal for all quantity calculations

**File to Modify**: `src/services/import_export_service.py`

**Parallel Note**: This work package runs in parallel with WP05-WP06 (Claude). Add functions at END of file to avoid merge conflicts.

**Assignee**: Gemini

## Subtasks & Detailed Guidance

### Subtask T029 - Create function signature and schema validation

**Purpose**: Establish function structure with proper validation.

**Steps**:
1. Add new function at END of `import_export_service.py`:
   ```python
   def import_inventory_updates_from_bt_mobile(file_path: str) -> ImportResult:
       """
       Import inventory updates from BT Mobile JSON file.

       Adjusts InventoryItem quantities based on percentage remaining.
       Uses FIFO selection (oldest purchase_date first).

       Args:
           file_path: Path to JSON file with schema_version="4.0", import_type="inventory_updates"

       Returns:
           ImportResult with success_count, error_count, and details
       """
       result = ImportResult()

       # Read JSON
       try:
           with open(file_path, 'r') as f:
               data = json.load(f)
       except json.JSONDecodeError as e:
           result.add_error("file", file_path, f"Invalid JSON: {e}")
           return result

       # Validate schema
       if data.get("schema_version") != "4.0":
           result.add_error("file", file_path,
               f"Unsupported schema version: {data.get('schema_version')}")
           return result

       if data.get("import_type") != "inventory_updates":
           result.add_error("file", file_path,
               f"Wrong import type: {data.get('import_type')} (expected 'inventory_updates')")
           return result

       # Process updates...
       return result
   ```

**Files**: `src/services/import_export_service.py`
**Parallel?**: No - foundation for other subtasks

### Subtask T030 - Implement UPC to Product lookup

**Purpose**: Find product for each inventory update record.

**Steps**:
1. Inside the function, after validation:
   ```python
   with session_scope() as session:
       for update_data in data.get("inventory_updates", []):
           upc = update_data.get("upc")
           if not upc:
               result.add_error("inventory_update", "unknown", "Missing UPC")
               continue

           # UPC lookup
           product = session.query(Product).filter_by(upc_code=upc).first()

           if not product:
               result.add_error("inventory_update", upc,
                   f"No product found with UPC: {upc}")
               continue

           # Found product - continue with FIFO selection (T031)
           ...
   ```

**Files**: `src/services/import_export_service.py`
**Parallel?**: No - sequential logic

### Subtask T031 - Implement FIFO InventoryItem selection

**Purpose**: Select oldest inventory item with quantity for adjustment.

**Steps**:
1. After finding product, find FIFO inventory item:
   ```python
   from src.models.inventory_item import InventoryItem

   # FIFO: oldest purchase_date first, with remaining quantity
   inventory_item = (
       session.query(InventoryItem)
       .filter_by(product_id=product.id)
       .filter(InventoryItem.current_quantity > 0)
       .order_by(InventoryItem.purchase_date.asc())
       .first()
   )

   if not inventory_item:
       result.add_error("inventory_update", upc,
           f"No inventory with remaining quantity for product: {product.name}")
       continue
   ```

**Files**: `src/services/import_export_service.py`
**Parallel?**: No - depends on T030

**Notes**:
- FIFO means oldest purchase_date gets adjusted first
- Only consider items with current_quantity > 0

### Subtask T032 - Implement percentage calculation

**Purpose**: Calculate target quantity and adjustment amount.

**Steps**:
1. After selecting inventory item:
   ```python
   from decimal import Decimal

   # Get percentage from update data
   percentage = update_data.get("remaining_percentage")
   if percentage is None:
       result.add_error("inventory_update", upc, "Missing remaining_percentage")
       continue

   # Validate percentage range
   if not (0 <= percentage <= 100):
       result.add_error("inventory_update", upc,
           f"Invalid percentage: {percentage} (must be 0-100)")
       continue

   # Get original quantity from linked purchase
   if not inventory_item.purchase_id:
       result.add_error("inventory_update", upc,
           "Cannot calculate percentage - inventory item has no linked purchase")
       continue

   purchase = session.query(Purchase).get(inventory_item.purchase_id)
   if not purchase:
       result.add_error("inventory_update", upc,
           "Cannot calculate percentage - linked purchase not found")
       continue

   original_quantity = purchase.quantity_purchased

   # Calculate target and adjustment
   pct_decimal = Decimal(str(percentage)) / Decimal(100)
   target_quantity = original_quantity * pct_decimal
   adjustment = target_quantity - inventory_item.current_quantity

   # adjustment < 0 means depletion, > 0 means addition (rare but possible)
   ```

**Files**: `src/services/import_export_service.py`
**Parallel?**: No - depends on T031

**Notes**:
- Use `Decimal(str(value))` not `Decimal(value)` for floats
- Handle both depletion (adjustment < 0) and addition (adjustment > 0)

### Subtask T033 - Create InventoryDepletion and update quantity

**Purpose**: Record the adjustment and update inventory.

**Steps**:
1. After calculating adjustment:
   ```python
   from src.models.inventory_depletion import InventoryDepletion
   from datetime import datetime

   # Update inventory item quantity
   new_quantity = inventory_item.current_quantity + adjustment

   # Validate no negative inventory
   if new_quantity < 0:
       result.add_error("inventory_update", upc,
           f"Adjustment would result in negative inventory: {new_quantity}")
       continue

   # Create depletion record (only for depletions, not additions)
   if adjustment < 0:
       depletion = InventoryDepletion(
           inventory_item_id=inventory_item.id,
           quantity_depleted=abs(adjustment),
           depletion_date=datetime.now(),
           reason="bt_mobile_inventory_update",
           notes=f"BT Mobile scan: {percentage}% remaining"
       )
       session.add(depletion)

   # Update current quantity
   inventory_item.current_quantity = new_quantity

   result.add_success("inventory_update")
   ```
2. After loop, commit:
   ```python
   session.commit()
   ```

**Files**: `src/services/import_export_service.py`
**Parallel?**: No - final step

**Notes**:
- Check InventoryDepletion model for required fields
- For additions (percentage > 100 edge case?), may skip depletion record

## Test Strategy

**Required Tests**:
```bash
pytest src/tests/services/test_import_export_service.py::TestInventoryUpdateFromBTMobile -v
```

**Test Fixture**:
```python
@pytest.fixture
def bt_mobile_inventory_json(tmp_path):
    data = {
        "schema_version": "4.0",
        "import_type": "inventory_updates",
        "created_at": "2026-01-06T14:30:00Z",
        "source": "bt_mobile",
        "inventory_updates": [
            {
                "upc": "051000127952",
                "scanned_at": "2026-01-06T14:15:23Z",
                "remaining_percentage": 50
            }
        ]
    }
    file_path = tmp_path / "inventory_updates.json"
    file_path.write_text(json.dumps(data))
    return str(file_path)
```

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| No linked purchase | Clear error message, skip item |
| Multiple FIFO items | Only adjust first (oldest), one at a time |
| Decimal precision | Use Decimal(str(value)) pattern |

## Definition of Done Checklist

- [ ] T029: Function signature and schema validation
- [ ] T030: UPC to Product lookup works
- [ ] T031: FIFO selection works (oldest first)
- [ ] T032: Percentage calculation correct
- [ ] T033: InventoryDepletion created, quantity updated
- [ ] Added at END of file (parallel safety)

## Review Guidance

- Verify FIFO order with multiple inventory items
- Check Decimal precision in calculations
- Test edge cases: 0%, 100%, no purchase
- Confirm InventoryDepletion records created correctly

## Activity Log

- 2026-01-06T12:00:00Z - system - lane=planned - Prompt created.
- 2026-01-07T03:38:02Z – system – shell_pid= – lane=doing – Moved to doing
- 2026-01-07T03:42:38Z – system – shell_pid= – lane=for_review – Moved to for_review
