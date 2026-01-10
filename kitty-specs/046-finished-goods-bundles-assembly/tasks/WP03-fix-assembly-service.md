---
work_package_id: "WP03"
subtasks:
  - "T008"
  - "T009"
  - "T010"
title: "Fix Assembly Service Cost Capture"
phase: "Phase 2 - Service Layer Fixes"
lane: "done"
assignee: ""
agent: "claude"
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-10T07:30:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP03 - Fix Assembly Service Cost Capture

## IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

**Primary Goal**: Fix `assembly_service.record_assembly()` to capture actual component costs instead of hardcoded zeros. This enables User Story 2 (Record an Assembly) with accurate cost snapshots.

**Success Criteria**:
1. Recording an assembly captures actual `unit_cost_at_consumption` for each FinishedUnit
2. `AssemblyRun.total_component_cost` reflects sum of all component costs
3. `AssemblyRun.per_unit_cost` is calculated correctly
4. `AssemblyFinishedUnitConsumption` records have non-zero costs (when production history exists)
5. Nested FinishedGood component costs are calculated correctly

## Context & Constraints

**Why This Matters**: Currently, `record_assembly()` hardcodes all costs to `Decimal("0.0000")` with a comment saying "F045 removed costs." This was a placeholder - F046 must implement actual cost capture.

**Current Broken Code** (lines 341-356):
```python
# Feature 045: Costs now tracked on instances, not definitions
# FinishedUnit no longer has unit_cost field
unit_cost = Decimal("0.0000")  # WRONG - should calculate!
cost = Decimal("0.0000")
```

**Dependencies**: WP01 must be complete (provides `calculate_current_cost()`)

**Key Documents**:
- `kitty-specs/046-finished-goods-bundles-assembly/research/research.md` - Issue 3
- `kitty-specs/046-finished-goods-bundles-assembly/research/data-model.md` - Service Layer Fixes section

**Session Management Note**: Per CLAUDE.md, always use the provided session parameter when calling other service functions. The `record_assembly()` function already follows this pattern correctly.

## Subtasks & Detailed Guidance

### Subtask T008 - Fix FinishedUnit Cost Calculation

**Purpose**: Replace hardcoded zero cost with actual cost calculation for FinishedUnit components.

**File**: `src/services/assembly_service.py`

**Location**: Lines 341-356 (within `_record_assembly_impl` function)

**Current Broken Code**:
```python
if comp.finished_unit_id:
    # FinishedUnit component - decrement inventory_count
    fu = session.query(FinishedUnit).filter_by(id=comp.finished_unit_id).first()
    if fu:
        needed = int(comp.component_quantity * quantity)
        if fu.inventory_count < needed:
            raise InsufficientFinishedUnitError(
                fu.id, needed, fu.inventory_count
            )

        # Feature 045: Costs now tracked on instances, not definitions
        # FinishedUnit no longer has unit_cost field
        unit_cost = Decimal("0.0000")  # <-- FIX THIS
        cost = Decimal("0.0000")       # <-- FIX THIS

        fu.inventory_count -= needed
        total_component_cost += cost

        fu_consumptions.append(
            {
                "finished_unit_id": fu.id,
                "quantity_consumed": needed,
                "unit_cost_at_consumption": unit_cost,
                "total_cost": cost,
            }
        )
```

**Fixed Code**:
```python
if comp.finished_unit_id:
    # FinishedUnit component - decrement inventory_count
    fu = session.query(FinishedUnit).filter_by(id=comp.finished_unit_id).first()
    if fu:
        needed = int(comp.component_quantity * quantity)
        if fu.inventory_count < needed:
            raise InsufficientFinishedUnitError(
                fu.id, needed, fu.inventory_count
            )

        # F046: Calculate actual cost from FinishedUnit's production history
        unit_cost = fu.calculate_current_cost()
        cost = unit_cost * Decimal(str(needed))

        fu.inventory_count -= needed
        total_component_cost += cost

        fu_consumptions.append(
            {
                "finished_unit_id": fu.id,
                "quantity_consumed": needed,
                "unit_cost_at_consumption": unit_cost,
                "total_cost": cost,
            }
        )
```

**Key Changes**:
1. Replace `unit_cost = Decimal("0.0000")` with `unit_cost = fu.calculate_current_cost()`
2. Replace `cost = Decimal("0.0000")` with `cost = unit_cost * Decimal(str(needed))`
3. Update/remove the F045 comment

**Parallel?**: No - should be done with T009 (same function)

### Subtask T009 - Fix Nested FinishedGood Cost Calculation

**Purpose**: Replace hardcoded zero cost with actual cost calculation for nested FinishedGood components.

**File**: `src/services/assembly_service.py`

**Location**: Lines 358-376 (within `_record_assembly_impl` function)

**Current Broken Code**:
```python
elif comp.finished_good_id:
    # FinishedGood component (nested assembly) - decrement inventory_count
    # KNOWN LIMITATION: No consumption ledger entry is created for nested FGs.
    # See docs/known_limitations.md for details and future enhancement plan.
    nested_fg = session.query(FinishedGood).filter_by(id=comp.finished_good_id).first()
    if nested_fg:
        needed = int(comp.component_quantity * quantity)
        if nested_fg.inventory_count < needed:
            raise InsufficientFinishedGoodError(
                nested_fg.id, needed, nested_fg.inventory_count
            )

        # Feature 045: Costs now tracked on instances, not definitions
        # FinishedGood no longer has total_cost field
        unit_cost = Decimal("0.0000")  # <-- FIX THIS
        cost = Decimal("0.0000")       # <-- FIX THIS

        nested_fg.inventory_count -= needed
        total_component_cost += cost
```

**Fixed Code**:
```python
elif comp.finished_good_id:
    # FinishedGood component (nested assembly) - decrement inventory_count
    # KNOWN LIMITATION: No consumption ledger entry is created for nested FGs.
    # See docs/known_limitations.md for details and future enhancement plan.
    nested_fg = session.query(FinishedGood).filter_by(id=comp.finished_good_id).first()
    if nested_fg:
        needed = int(comp.component_quantity * quantity)
        if nested_fg.inventory_count < needed:
            raise InsufficientFinishedGoodError(
                nested_fg.id, needed, nested_fg.inventory_count
            )

        # F046: Calculate actual cost from FinishedGood's component costs
        unit_cost = nested_fg.calculate_current_cost()
        cost = unit_cost * Decimal(str(needed))

        nested_fg.inventory_count -= needed
        total_component_cost += cost
```

**Key Changes**:
1. Replace `unit_cost = Decimal("0.0000")` with `unit_cost = nested_fg.calculate_current_cost()`
2. Replace `cost = Decimal("0.0000")` with `cost = unit_cost * Decimal(str(needed))`
3. Update/remove the F045 comment
4. Keep the KNOWN LIMITATION comment (consumption ledger for nested FGs is out of scope)

**Parallel?**: No - should be done with T008 (same function)

### Subtask T010 - Verify finished_good_service.py

**Purpose**: Verify that finished_good_service.py works correctly with the new cost methods.

**File**: `src/services/finished_good_service.py`

**Tasks**:
1. Search for `_recalculate_assembly_cost` method - verify it doesn't reference removed fields
2. Search for any references to `total_cost` or `unit_cost` attribute access
3. Run existing tests for this service

**Verification Commands**:
```bash
# Search for potentially broken references
grep -n "total_cost\|unit_cost" src/services/finished_good_service.py

# Run service tests
pytest src/tests/services/test_finished_good_service.py -v
```

**Note**: Based on codebase review, this service was updated in F045 to pass `Decimal("0.0000")` for cost validation. These should continue to work as the validation was relaxed.

**Parallel?**: Can start after T008/T009 complete

## Test Strategy

**Manual Verification**:
```python
from src.services import assembly_service
from src.services.database import session_scope

# Record an assembly and check costs
result = assembly_service.record_assembly(
    finished_good_id=1,  # Replace with valid ID
    quantity=1
)

print(f"Total cost: {result['total_component_cost']}")
print(f"Per unit cost: {result['per_unit_cost']}")
for fc in result['finished_unit_consumptions']:
    print(f"  FU {fc['finished_unit_id']}: {fc['unit_cost_at_consumption']} x {fc['quantity_consumed']} = {fc['total_cost']}")
```

**Integration Test**: After recording, query the AssemblyRun directly and verify costs are populated:
```python
from src.models import AssemblyRun
from src.services.database import session_scope

with session_scope() as session:
    run = session.query(AssemblyRun).order_by(AssemblyRun.id.desc()).first()
    print(f"AssemblyRun {run.id}:")
    print(f"  total_component_cost: {run.total_component_cost}")
    print(f"  per_unit_cost: {run.per_unit_cost}")
```

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| No production history -> zero costs | Expected | Document this behavior; costs will be zero until production is tracked |
| Breaking existing assemblies | None | Existing assembly records retain their (zero) costs |
| Session detachment | High | Use same session throughout function (already correct) |

## Definition of Done Checklist

- [ ] T008: FinishedUnit cost calculation fixed in `_record_assembly_impl`
- [ ] T009: Nested FinishedGood cost calculation fixed in `_record_assembly_impl`
- [ ] T010: finished_good_service.py verified (no broken references)
- [ ] Recording assembly captures non-zero costs (when production history exists)
- [ ] `total_component_cost` is sum of component costs
- [ ] `per_unit_cost` is `total_component_cost / quantity`
- [ ] Existing tests pass: `pytest src/tests -v`
- [ ] No new linting errors

## Review Guidance

**Key Checkpoints**:
1. Both cost calculation blocks updated (FinishedUnit and FinishedGood)
2. F045 placeholder comments updated or removed
3. `Decimal(str(needed))` used for multiplication (not int directly)
4. `total_component_cost += cost` accumulates correctly
5. Session usage is correct (no new session_scope() calls added)

**Grep Verification**:
```bash
# Should find NO hardcoded zero costs in the component processing blocks
grep -A5 "comp.finished_unit_id:" src/services/assembly_service.py | grep "Decimal.*0\.0000"
```

## Activity Log

- 2026-01-10T07:30:00Z - system - lane=planned - Prompt created via /spec-kitty.tasks
- 2026-01-10T13:02:04Z – unknown – lane=doing – Moved to doing
- 2026-01-10T13:06:40Z – unknown – lane=for_review – Moved to for_review
- 2026-01-10T13:30:19Z – claude – lane=done – Code review approved: Cost capture fixed, no hardcoded zeros, 29 assembly tests pass
