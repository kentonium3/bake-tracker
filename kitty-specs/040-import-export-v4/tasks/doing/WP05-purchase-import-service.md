---
work_package_id: "WP05"
subtasks:
  - "T019"
  - "T020"
  - "T021"
  - "T022"
  - "T023"
  - "T024"
title: "Purchase Import Service"
phase: "Phase 2 - BT Mobile Workflows"
lane: "doing"
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

# Work Package Prompt: WP05 - Purchase Import Service

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

- Implement `import_purchases_from_bt_mobile(file_path)` function
- UPC matching against Product.upc_code
- Create Purchase + InventoryItem for matched UPCs
- Collect unmatched UPCs for resolution (handled by WP06)
- Return ImportResult with counts

**Success Criteria**:
- Import JSON with known UPCs creates Purchase + InventoryItem records
- Unknown UPCs are collected, not errored
- ImportResult shows matched/unmatched/error counts

## Context & Constraints

**Related Documents**:
- `kitty-specs/040-import-export-v4/spec.md` - User Story 3 acceptance criteria
- `kitty-specs/040-import-export-v4/data-model.md` - Purchase import JSON schema
- `kitty-specs/040-import-export-v4/research.md` - Key decisions D3, D4

**Key Constraints**:
- Schema validation: schema_version="4.0", import_type="purchases"
- Use session management pattern from CLAUDE.md
- Product.upc_code is indexed (fast lookup)
- Supplier resolved by name, created if not exists

**File to Modify**: `src/services/import_export_service.py`

**Parallel Note**: This work package runs in parallel with WP07-WP08 (Gemini). Add functions at END of file to avoid merge conflicts.

## Subtasks & Detailed Guidance

### Subtask T019 - Create function signature and schema validation

**Purpose**: Establish function structure with proper validation.

**Steps**:
1. Add new function at END of `import_export_service.py`:
   ```python
   def import_purchases_from_bt_mobile(file_path: str) -> ImportResult:
       """
       Import purchases from BT Mobile JSON file.

       Args:
           file_path: Path to JSON file with schema_version="4.0", import_type="purchases"

       Returns:
           ImportResult with matched_count, unmatched_upcs, error_count
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

       if data.get("import_type") != "purchases":
           result.add_error("file", file_path,
               f"Wrong import type: {data.get('import_type')} (expected 'purchases')")
           return result

       # Process purchases...
       return result
   ```

**Files**: `src/services/import_export_service.py`
**Parallel?**: No - foundation for other subtasks

### Subtask T020 - Implement UPC matching logic

**Purpose**: Match purchase UPCs against existing products.

**Steps**:
1. Inside the function, after validation:
   ```python
   default_supplier = data.get("supplier")
   unmatched_purchases = []

   with session_scope() as session:
       for purchase_data in data.get("purchases", []):
           upc = purchase_data.get("upc")
           if not upc:
               result.add_error("purchase", "unknown", "Missing UPC")
               continue

           # UPC lookup
           product = session.query(Product).filter_by(upc_code=upc).first()

           if not product:
               # Collect for resolution
               unmatched_purchases.append(purchase_data)
               continue

           # Product found - create purchase (T021)
           ...
   ```

**Files**: `src/services/import_export_service.py`
**Parallel?**: No - sequential logic

### Subtask T021 - Create Purchase + InventoryItem for matches

**Purpose**: Create database records for matched UPCs.

**Steps**:
1. When product is found:
   ```python
   from decimal import Decimal
   from src.models.purchase import Purchase
   from src.models.inventory_item import InventoryItem

   # Resolve supplier
   supplier_name = purchase_data.get("supplier", default_supplier)
   supplier = None
   if supplier_name:
       supplier = session.query(Supplier).filter_by(name=supplier_name).first()
       if not supplier:
           supplier = Supplier(name=supplier_name)
           session.add(supplier)
           session.flush()

   # Parse date
   scanned_at = purchase_data.get("scanned_at")
   purchase_date = datetime.fromisoformat(scanned_at.replace("Z", "+00:00")) if scanned_at else datetime.now()

   # Create Purchase
   purchase = Purchase(
       product_id=product.id,
       supplier_id=supplier.id if supplier else None,
       purchase_date=purchase_date,
       unit_price=Decimal(str(purchase_data.get("unit_price", 0))),
       quantity_purchased=Decimal(str(purchase_data.get("quantity_purchased", 1))),
       notes=purchase_data.get("notes")
   )
   session.add(purchase)
   session.flush()  # Get purchase.id

   # Create InventoryItem
   inventory_item = InventoryItem(
       product_id=product.id,
       purchase_id=purchase.id,
       current_quantity=purchase.quantity_purchased,
       purchase_date=purchase.purchase_date
   )
   session.add(inventory_item)

   result.add_success("purchase")
   ```

**Files**: `src/services/import_export_service.py`
**Parallel?**: No - depends on T020

**Notes**:
- Use `Decimal(str(value))` not `Decimal(value)` for floats
- Check InventoryItem model for required fields

### Subtask T022 - Collect unmatched UPCs

**Purpose**: Gather unmatched UPCs for UI resolution.

**Steps**:
1. After processing loop:
   ```python
   # Store unmatched for resolution
   result.unmatched_purchases = unmatched_purchases

   # Commit successful imports
   session.commit()
   ```
2. Add `unmatched_purchases` attribute to ImportResult if not exists:
   ```python
   # In ImportResult class or at assignment:
   result.unmatched_purchases = []
   ```

**Files**: `src/services/import_export_service.py`
**Parallel?**: No - collects from T020

### Subtask T023 - Return ImportResult with counts

**Purpose**: Provide meaningful import summary.

**Steps**:
1. Ensure ImportResult tracks:
   - `success_count` - purchases created
   - `error_count` - errors encountered
   - `unmatched_purchases` - list for UI resolution
2. Return at end of function:
   ```python
   return result
   ```

**Files**: `src/services/import_export_service.py`
**Parallel?**: No - wraps up function

### Subtask T024 - Unit tests for purchase import

**Purpose**: Verify all scenarios work correctly.

**Steps**:
1. Create test class `TestPurchaseImportFromBTMobile`
2. Test cases:
   - `test_import_purchase_with_known_upc`: Product exists, Purchase+InventoryItem created
   - `test_import_purchase_with_unknown_upc`: No product, UPC collected in unmatched
   - `test_import_purchase_creates_supplier`: Supplier created if not exists
   - `test_import_purchase_invalid_schema_version`: Error for wrong version
   - `test_import_purchase_wrong_import_type`: Error for wrong type
   - `test_import_purchase_invalid_json`: Error for malformed JSON

**Files**: `src/tests/services/test_import_export_service.py`
**Parallel?**: No - tests after implementation

## Test Strategy

**Required Tests**:
```bash
pytest src/tests/services/test_import_export_service.py::TestPurchaseImportFromBTMobile -v
```

**Test Fixture**:
```python
@pytest.fixture
def bt_mobile_purchase_json(tmp_path):
    data = {
        "schema_version": "4.0",
        "import_type": "purchases",
        "created_at": "2026-01-06T14:30:00Z",
        "source": "bt_mobile",
        "supplier": "Test Store",
        "purchases": [
            {
                "upc": "051000127952",
                "scanned_at": "2026-01-06T14:15:23Z",
                "unit_price": 7.99,
                "quantity_purchased": 1.0
            }
        ]
    }
    file_path = tmp_path / "purchases.json"
    file_path.write_text(json.dumps(data))
    return str(file_path)
```

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Duplicate imports | Could add check for existing purchase with same UPC+date+price |
| Session detachment | Follow CLAUDE.md session patterns |
| Decimal precision | Use Decimal(str(value)) pattern |

## Definition of Done Checklist

- [ ] T019: Function signature and schema validation
- [ ] T020: UPC matching logic works
- [ ] T021: Purchase + InventoryItem created for matches
- [ ] T022: Unmatched UPCs collected
- [ ] T023: ImportResult has meaningful counts
- [ ] T024: All unit tests pass
- [ ] Added at END of file (parallel safety)

## Review Guidance

- Verify session management follows CLAUDE.md patterns
- Check Decimal handling for prices
- Confirm unmatched_purchases accessible for WP06
- Test with real sample JSON

## Activity Log

- 2026-01-06T12:00:00Z - system - lane=planned - Prompt created.
- 2026-01-07T03:27:59Z – system – shell_pid= – lane=doing – Moved to doing
