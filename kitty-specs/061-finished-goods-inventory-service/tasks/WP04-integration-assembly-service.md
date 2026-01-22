---
work_package_id: "WP04"
subtasks:
  - "T012"
  - "T013"
  - "T014"
  - "T015"
title: "Integration - Assembly Service"
phase: "Phase 3 - Integration"
lane: "for_review"
assignee: ""
agent: "claude-opus"
shell_pid: "13618"
review_status: ""
reviewed_by: ""
dependencies: ["WP03"]
history:
  - timestamp: "2026-01-21T19:33:38Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP04 – Integration - Assembly Service

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
spec-kitty implement WP04 --base WP03
```

Depends on WP03 (adjust_inventory function available).

---

## Objectives & Success Criteria

- ✅ Assembly service uses `adjust_inventory()` for all inventory changes
- ✅ Audit records created for FU consumption during assembly
- ✅ Audit records created for nested FG consumption during assembly
- ✅ Audit records created for FG creation during assembly
- ✅ Session passed correctly to maintain atomicity
- ✅ Existing assembly functionality unchanged (same inputs/outputs)

## Context & Constraints

**Reference Documents**:
- `kitty-specs/061-finished-goods-inventory-service/research.md` - Assembly service analysis
- `kitty-specs/061-finished-goods-inventory-service/plan.md` - Integration patterns
- `src/services/assembly_service.py` - Current implementation

**Key Constraints**:
- Pass session to all inventory service calls (F060 compliance)
- Preserve existing error handling
- Maintain atomicity (all changes in same transaction)
- Use "assembly" reason for all adjustments

---

## Subtasks & Detailed Guidance

### Subtask T012 – Update check_can_assemble for inventory service

**Purpose**: Optionally update availability checking to use inventory service.

**Steps**:
1. Open `src/services/assembly_service.py`
2. Add import at top:
   ```python
   from src.services import finished_goods_inventory_service as fg_inv
   ```
3. In `check_can_assemble` or `_check_can_assemble_impl`, consider using:
   ```python
   availability = fg_inv.check_availability(
       "finished_unit", fu.id, needed, session=session
   )
   if not availability["available"]:
       # Handle shortage
   ```
4. **NOTE**: This is optional - the existing `inventory_count >= needed` check works fine. The main benefit is consistency with the service pattern.

**Files**:
- `src/services/assembly_service.py` (modify, ~10 lines)

**Decision Point**:
- If the existing check is clear and working, you may skip this subtask
- The critical updates are T013-T015 which create audit records

**Validation**:
- [ ] Import added (if proceeding)
- [ ] Availability check works correctly
- [ ] Existing behavior unchanged

---

### Subtask T013 – Update FU consumption to use adjust_inventory

**Purpose**: Replace direct `inventory_count -= needed` with audit-tracked adjustment.

**Steps**:
1. Find the FU consumption code in `_record_assembly_impl`
2. Research.md indicates this is around line 156-158:
   ```python
   # BEFORE
   fu.inventory_count -= needed
   session.flush()
   ```
3. Replace with:
   ```python
   # AFTER
   fg_inv.adjust_inventory(
       item_type="finished_unit",
       item_id=fu.id,
       quantity=-needed,
       reason="assembly",
       notes=f"Assembly of {finished_good.display_name} (x{quantity})",
       session=session
   )
   ```
4. Remove the separate `session.flush()` call (adjust_inventory handles it)

**Files**:
- `src/services/assembly_service.py` (modify, ~10 lines)

**IMPORTANT**: Use grep to find the exact line numbers, as they may have shifted since research.md was written:
```bash
grep -n "inventory_count -= " src/services/assembly_service.py
```

**Validation**:
- [ ] Direct assignment replaced with adjust_inventory call
- [ ] Session passed to adjust_inventory
- [ ] Reason is "assembly"
- [ ] Notes include meaningful context

---

### Subtask T014 – Update nested FG consumption to use adjust_inventory

**Purpose**: Replace direct consumption of nested finished goods with audit-tracked adjustment.

**Steps**:
1. Find the nested FG consumption code in `_record_assembly_impl`
2. Research.md indicates this is around line 175-178:
   ```python
   # BEFORE
   nested_fg.inventory_count -= needed_nested
   session.flush()
   ```
3. Replace with:
   ```python
   # AFTER
   fg_inv.adjust_inventory(
       item_type="finished_good",
       item_id=nested_fg.id,
       quantity=-needed_nested,
       reason="assembly",
       notes=f"Component for {finished_good.display_name} (x{quantity})",
       session=session
   )
   ```

**Files**:
- `src/services/assembly_service.py` (modify, ~10 lines)

**IMPORTANT**: This may be in a loop or conditional. Use grep to find exact location:
```bash
grep -n "nested" src/services/assembly_service.py
```

**Validation**:
- [ ] Nested FG consumption uses adjust_inventory
- [ ] Session passed correctly
- [ ] Reason is "assembly"
- [ ] Notes distinguish from primary FU consumption

---

### Subtask T015 – Update FG creation to use adjust_inventory

**Purpose**: Replace direct `inventory_count += quantity` with audit-tracked adjustment.

**Steps**:
1. Find the FG creation code in `_record_assembly_impl`
2. Research.md indicates this is around line 191-193:
   ```python
   # BEFORE
   finished_good.inventory_count += quantity
   session.flush()
   ```
3. Replace with:
   ```python
   # AFTER
   fg_inv.adjust_inventory(
       item_type="finished_good",
       item_id=finished_good.id,
       quantity=+quantity,
       reason="assembly",
       notes=f"Assembled from components",
       session=session
   )
   ```

**Files**:
- `src/services/assembly_service.py` (modify, ~10 lines)

**Validation**:
- [ ] FG creation uses adjust_inventory with positive quantity
- [ ] Session passed correctly
- [ ] Reason is "assembly"
- [ ] Notes indicate this is a creation

---

## Test Strategy

No new tests in this WP - integration tests are in WP08.

Manual validation:
```python
from src.services import assembly_service
from src.database import session_scope

# Perform an assembly (assuming test data exists)
with session_scope() as session:
    result = assembly_service.record_assembly(
        finished_good_id=1,
        quantity=2,
        session=session
    )
    print(f"Assembly result: {result}")

# Check for audit records
from src.models import FinishedGoodsAdjustment
with session_scope() as session:
    adjustments = session.query(FinishedGoodsAdjustment).filter_by(
        reason="assembly"
    ).order_by(FinishedGoodsAdjustment.adjusted_at.desc()).limit(10).all()
    for adj in adjustments:
        print(f"{adj.item_type}: {adj.quantity_change} ({adj.notes})")
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Line numbers shifted | Use grep to find exact locations |
| Breaking existing tests | Run test suite after each change |
| Session not passed correctly | Verify session parameter in each call |
| Missing audit records | Check database after manual test |

---

## Definition of Done Checklist

- [ ] T012: check_can_assemble optionally updated (or documented as skipped)
- [ ] T013: FU consumption uses adjust_inventory
- [ ] T014: Nested FG consumption uses adjust_inventory
- [ ] T015: FG creation uses adjust_inventory
- [ ] All adjust_inventory calls pass session parameter
- [ ] All adjust_inventory calls use "assembly" reason
- [ ] All adjust_inventory calls include meaningful notes
- [ ] Existing assembly tests still pass

---

## Review Guidance

**Key checkpoints**:
1. Session is passed to ALL adjust_inventory calls
2. Reason is "assembly" for all calls
3. Notes provide meaningful context for audit trail
4. No direct `inventory_count +=/-=` assignments remain in assembly flow
5. Existing functionality unchanged (same inputs produce same outputs, plus audit trail)

---

## Activity Log

- 2026-01-21T19:33:38Z – system – lane=planned – Prompt created.
- 2026-01-22T02:44:03Z – claude-opus – shell_pid=13618 – lane=doing – Started implementation via workflow command
- 2026-01-22T02:51:58Z – claude-opus – shell_pid=13618 – lane=for_review – Ready for review: Updated assembly_service.py to use adjust_inventory for all inventory changes. FU consumption (T013), nested FG consumption (T014), and FG creation (T015) now create audit records. T012 skipped as existing check works correctly. All 2581 tests pass.
