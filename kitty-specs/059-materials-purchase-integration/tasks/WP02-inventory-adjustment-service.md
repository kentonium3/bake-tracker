---
work_package_id: "WP02"
subtasks:
  - "T006"
  - "T007"
  - "T008"
  - "T009"
  - "T010"
title: "Service Layer - Inventory Adjustment"
phase: "Phase 0 - Foundation"
lane: "for_review"
assignee: ""
agent: "Gemini"
shell_pid: "60227"
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

# Work Package Prompt: WP02 - Service Layer - Inventory Adjustment

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
# No dependencies - start from main branch (can run parallel with WP01)
spec-kitty implement WP02
```

---

## Objectives & Success Criteria

Add manual inventory adjustment method to MaterialInventoryService. This enables users to correct inventory discrepancies by:
- Adjusting "each" materials with Add/Subtract/Set operations
- Adjusting "variable" materials (linear_cm, square_cm) with percentage-based input
- Recording adjustment notes for audit trail

**Success Criteria**:
- [ ] Inventory items can be adjusted for "each" materials (direct quantity)
- [ ] Inventory items can be adjusted for "variable" materials (percentage)
- [ ] Adjustment notes are stored
- [ ] Validation prevents negative quantities
- [ ] All tests pass with >70% coverage for new code

---

## Context & Constraints

**Feature**: F059 - Materials Purchase Integration & Workflows
**Reference Documents**:
- Spec: `kitty-specs/059-materials-purchase-integration/spec.md`
- Plan: `kitty-specs/059-materials-purchase-integration/plan.md`
- Data Model: `kitty-specs/059-materials-purchase-integration/data-model.md`

**Key Clarification** (from spec):
> For "each" material adjustments, should adjustment create a new lot or update existing?
> **Answer**: Update the existing lot's quantity_remaining directly (consistent with variable materials)

**Validation Rules** (from data-model.md):
- Quantity non-negative: new_quantity >= 0
- Percentage valid: 0 <= percentage <= 100
- Cannot exceed original: new_quantity <= quantity_purchased (warning only, not blocked)

---

## Subtasks & Detailed Guidance

### Subtask T006 - Add adjust_inventory() Method Signature

**Purpose**: Define the public API for inventory adjustment.

**Steps**:
1. Open `src/services/material_inventory_service.py`
2. Add function signature with session pattern:

```python
def adjust_inventory(
    inventory_item_id: int,
    adjustment_type: str,  # "add", "subtract", "set", "percentage"
    value: Decimal,
    notes: Optional[str] = None,
    session: Optional[Session] = None
) -> Dict[str, Any]:
    """Adjust inventory quantity for a MaterialInventoryItem.

    Args:
        inventory_item_id: The MaterialInventoryItem ID to adjust
        adjustment_type: One of "add", "subtract", "set", "percentage"
            - "add": Add value to current quantity
            - "subtract": Subtract value from current quantity
            - "set": Set quantity to exact value
            - "percentage": Set to percentage of CURRENT quantity (0-100)
        value: The adjustment value (units for add/subtract/set, percent for percentage)
        notes: Optional adjustment reason for audit trail
        session: Optional database session

    Returns:
        Dict with updated inventory item data

    Raises:
        MaterialInventoryItemNotFoundError: If item doesn't exist
        ValidationError: If adjustment would result in negative quantity
    """
    if session is not None:
        return _adjust_inventory_impl(inventory_item_id, adjustment_type, value, notes, session)
    with session_scope() as sess:
        return _adjust_inventory_impl(inventory_item_id, adjustment_type, value, notes, sess)
```

**Files**:
- `src/services/material_inventory_service.py` (add function)

**Validation**:
- [ ] Function signature follows session pattern
- [ ] Docstring documents all parameters and behaviors
- [ ] Returns dict (not ORM object) for consistency

---

### Subtask T007 - Implement "each" Materials Adjustment

**Purpose**: Handle Add/Subtract/Set operations for discrete materials.

**Steps**:
1. In `_adjust_inventory_impl()`, handle adjustment_type cases:

```python
def _adjust_inventory_impl(
    inventory_item_id: int,
    adjustment_type: str,
    value: Decimal,
    notes: Optional[str],
    session: Session
) -> Dict[str, Any]:
    # Fetch the inventory item
    item = session.query(MaterialInventoryItem).filter_by(id=inventory_item_id).first()
    if not item:
        raise MaterialInventoryItemNotFoundError(f"Inventory item {inventory_item_id} not found")

    current_qty = item.quantity_remaining

    # Calculate new quantity based on adjustment type
    if adjustment_type == "add":
        new_qty = current_qty + value
    elif adjustment_type == "subtract":
        new_qty = current_qty - value
    elif adjustment_type == "set":
        new_qty = value
    elif adjustment_type == "percentage":
        # Handled in T008
        pass
    else:
        raise ValidationError(f"Invalid adjustment_type: {adjustment_type}")

    # Validate non-negative
    if new_qty < 0:
        raise ValidationError(
            f"Adjustment would result in negative quantity: {new_qty}. "
            f"Current: {current_qty}, Adjustment: {adjustment_type} {value}"
        )

    # Update the item
    item.quantity_remaining = new_qty
    if notes:
        # Append to existing notes or set
        if item.notes:
            item.notes = f"{item.notes}\n[Adjustment] {notes}"
        else:
            item.notes = f"[Adjustment] {notes}"

    session.commit()

    return _inventory_item_to_dict(item)
```

2. Ensure `_inventory_item_to_dict()` helper exists (or create it)

**Files**:
- `src/services/material_inventory_service.py` (implement)

**Parallel?**: Yes - can be developed alongside T008

**Validation**:
- [ ] "add" increases quantity correctly
- [ ] "subtract" decreases quantity correctly
- [ ] "set" replaces quantity correctly
- [ ] Negative result raises ValidationError

---

### Subtask T008 - Implement "variable" Materials Adjustment

**Purpose**: Handle percentage-based adjustment for linear_cm/square_cm materials.

**Steps**:
1. Add percentage handling to `_adjust_inventory_impl()`:

```python
elif adjustment_type == "percentage":
    # Percentage is 0-100, representing percentage of CURRENT remaining
    if value < 0 or value > 100:
        raise ValidationError(f"Percentage must be 0-100, got: {value}")
    new_qty = (current_qty * value) / Decimal("100")
    # Round to reasonable precision (2 decimal places for materials)
    new_qty = new_qty.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
```

2. The percentage represents "what percentage remains", not "what percentage to remove":
   - 100% = keep all (no change)
   - 50% = keep half
   - 0% = fully depleted

**Files**:
- `src/services/material_inventory_service.py` (extend)

**Parallel?**: Yes - can be developed alongside T007

**Validation**:
- [ ] 100% keeps quantity unchanged
- [ ] 50% halves the quantity
- [ ] 0% sets quantity to 0
- [ ] Out-of-range percentage (e.g., 150%) raises ValidationError

---

### Subtask T009 - Add Notes Field Support

**Purpose**: Record adjustment reason for audit trail.

**Steps**:
1. Notes handling is included in T007 implementation
2. Verify MaterialInventoryItem.notes field exists and is Text type
3. Append adjustment notes with timestamp prefix:

```python
from datetime import datetime

if notes:
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    adjustment_note = f"[{timestamp}] Adjustment ({adjustment_type}): {notes}"
    if item.notes:
        item.notes = f"{item.notes}\n{adjustment_note}"
    else:
        item.notes = adjustment_note
```

**Files**:
- `src/services/material_inventory_service.py` (already in T007)
- `src/models/material_inventory_item.py` (verify notes field)

**Validation**:
- [ ] Notes field accepts and stores adjustment reason
- [ ] Notes are appended, not replaced
- [ ] Timestamp is included for audit trail

---

### Subtask T010 - Write Unit Tests for Adjustment Scenarios

**Purpose**: Ensure adjustment functionality works correctly for all cases.

**Steps**:
1. Create or extend: `src/tests/services/test_material_inventory_service.py`
2. Add comprehensive tests:

```python
class TestInventoryAdjustment:
    """Tests for adjust_inventory() function."""

    @pytest.fixture
    def inventory_item(self, session, material_product):
        """Create a test inventory item with 100 units."""
        item = MaterialInventoryItem(
            product_id=material_product.id,
            purchased_at=date.today(),
            quantity_purchased=Decimal("100"),
            quantity_remaining=Decimal("100"),
            cost_per_unit=Decimal("0.50"),
        )
        session.add(item)
        session.commit()
        return item

    def test_adjust_add(self, session, inventory_item):
        """Test adding to inventory."""
        result = adjust_inventory(
            inventory_item.id, "add", Decimal("25"),
            notes="Found extra", session=session
        )
        assert result["quantity_remaining"] == Decimal("125")

    def test_adjust_subtract(self, session, inventory_item):
        """Test subtracting from inventory."""
        result = adjust_inventory(
            inventory_item.id, "subtract", Decimal("30"),
            notes="Used untracked", session=session
        )
        assert result["quantity_remaining"] == Decimal("70")

    def test_adjust_set(self, session, inventory_item):
        """Test setting exact quantity."""
        result = adjust_inventory(
            inventory_item.id, "set", Decimal("50"),
            notes="Physical count", session=session
        )
        assert result["quantity_remaining"] == Decimal("50")

    def test_adjust_percentage(self, session, inventory_item):
        """Test percentage adjustment (50% remaining)."""
        result = adjust_inventory(
            inventory_item.id, "percentage", Decimal("50"),
            notes="Half used", session=session
        )
        assert result["quantity_remaining"] == Decimal("50.00")

    def test_adjust_percentage_zero(self, session, inventory_item):
        """Test 0% (fully depleted)."""
        result = adjust_inventory(
            inventory_item.id, "percentage", Decimal("0"),
            session=session
        )
        assert result["quantity_remaining"] == Decimal("0")

    def test_adjust_negative_result_raises(self, session, inventory_item):
        """Test that negative result raises ValidationError."""
        with pytest.raises(ValidationError) as exc:
            adjust_inventory(
                inventory_item.id, "subtract", Decimal("200"),
                session=session
            )
        assert "negative quantity" in str(exc.value).lower()

    def test_adjust_invalid_percentage_raises(self, session, inventory_item):
        """Test that percentage > 100 raises ValidationError."""
        with pytest.raises(ValidationError):
            adjust_inventory(
                inventory_item.id, "percentage", Decimal("150"),
                session=session
            )

    def test_adjust_notes_stored(self, session, inventory_item):
        """Test that adjustment notes are stored."""
        adjust_inventory(
            inventory_item.id, "set", Decimal("75"),
            notes="Inventory recount", session=session
        )
        session.refresh(inventory_item)
        assert "Inventory recount" in inventory_item.notes

    def test_adjust_item_not_found(self, session):
        """Test adjusting non-existent item raises error."""
        with pytest.raises(MaterialInventoryItemNotFoundError):
            adjust_inventory(99999, "set", Decimal("50"), session=session)
```

**Files**:
- `src/tests/services/test_material_inventory_service.py` (add/extend)

**Parallel?**: Yes - can be written alongside implementation

**Validation**:
- [ ] All happy path tests pass
- [ ] Edge case tests pass (0%, 100%, negative)
- [ ] Error cases properly raise exceptions
- [ ] Coverage >70% for new code

---

## Test Strategy

Run tests with:
```bash
./run-tests.sh src/tests/services/test_material_inventory_service.py -v
./run-tests.sh src/tests/services/test_material_inventory_service.py -v --cov=src/services/material_inventory_service
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| FIFO ordering broken | Adjustment only updates quantity_remaining, not purchased_at - FIFO consumption unaffected |
| Precision issues | Use Decimal with explicit quantize() for percentage calculations |
| Notes field overflow | Text type has no practical limit; append with newlines |

---

## Definition of Done Checklist

- [ ] T006: adjust_inventory() function signature added
- [ ] T007: "each" materials adjustment (add/subtract/set) working
- [ ] T008: "variable" materials adjustment (percentage) working
- [ ] T009: Notes field stores adjustment reason with timestamp
- [ ] T010: All tests written and passing
- [ ] Validation prevents negative quantities
- [ ] Code follows session management pattern
- [ ] tasks.md updated with status change

---

## Review Guidance

- Verify adjustment logic matches clarification (update existing lot, not new lot)
- Check percentage calculation: 50% of 100 should be 50, not 150
- Ensure notes are appended with timestamp, not replaced
- Verify ValidationError raised for invalid inputs

---

## Activity Log

- 2026-01-18T00:00:00Z - system - lane=planned - Prompt created.
- 2026-01-19T00:02:57Z – Gemini – shell_pid=60227 – lane=doing – Started implementation via workflow command
- 2026-01-19T00:17:05Z – Gemini – shell_pid=60227 – lane=for_review – Ready for review: Implemented inventory adjustment service and tests.
