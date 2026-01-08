---
work_package_id: WP01
title: PantryService dry_run Extension
lane: done
history:
- timestamp: '2025-12-02T00:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
agent: claude
assignee: claude
phase: Phase 0 - Foundational
review_status: approved
reviewed_by: claude
reviewer_shell_pid: '79852'
shell_pid: '75194'
subtasks:
- T001
- T002
- T003
- T004
- T005
---

# Work Package Prompt: WP01 – PantryService dry_run Extension

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you understand the feedback, update `review_status: acknowledged`.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

**Objective**: Add a `dry_run=True` parameter to `PantryService.consume_fifo()` that enables read-only FIFO cost simulation without modifying pantry inventory.

**Success Criteria**:
1. `consume_fifo(ingredient_slug, quantity, dry_run=True)` returns cost data without changing pantry quantities
2. `consume_fifo(ingredient_slug, quantity, dry_run=False)` behaves exactly as before (backward compatible)
3. Result includes `total_cost` (Decimal) representing FIFO cost of consumed portion
4. Each breakdown item includes `unit_cost` (Decimal) for that lot
5. Tests verify dry_run behavior and backward compatibility

## Context & Constraints

**Prerequisite Documents**:
- Constitution: `.kittify/memory/constitution.md` (FIFO Accuracy is NON-NEGOTIABLE)
- Plan: `kitty-specs/005-recipe-fifo-cost/plan.md`
- Contract: `kitty-specs/005-recipe-fifo-cost/contracts/pantry_service_dry_run.py`

**Architectural Constraints**:
- FIFO logic must remain centralized in `consume_fifo()` to prevent algorithm drift
- Session must NOT be flushed or committed when `dry_run=True`
- Existing tests must continue to pass

**Key File**: `src/services/pantry_service.py` (lines ~229-349)

## Subtasks & Detailed Guidance

### Subtask T001 – Add `dry_run` parameter to signature

**Purpose**: Extend the method signature with optional `dry_run` parameter.

**Steps**:
1. Locate `consume_fifo()` method in `src/services/pantry_service.py`
2. Add parameter: `dry_run: bool = False`
3. Update docstring to document the new parameter

**Files**: `src/services/pantry_service.py`

**Notes**: Default `False` ensures backward compatibility.

### Subtask T002 – Implement dry-run branch logic

**Purpose**: Skip database modifications when `dry_run=True`.

**Steps**:
1. Find where pantry item quantities are updated (likely `item.quantity -= consumed_amount`)
2. Wrap quantity updates in `if not dry_run:` block
3. Skip `session.flush()` and `session.commit()` when `dry_run=True`
4. Ensure the method still iterates through lots and calculates consumption

**Files**: `src/services/pantry_service.py`

**Notes**: The FIFO iteration logic should run regardless of dry_run - we just skip the writes.

### Subtask T003 – Add `total_cost` field to result dict

**Purpose**: Return the total FIFO cost of consumed inventory.

**Steps**:
1. Track cumulative cost as lots are processed
2. For each lot: `lot_cost = item.unit_cost * quantity_consumed`
3. Add to result dict: `"total_cost": total_cost`

**Files**: `src/services/pantry_service.py`

**Notes**: Use Decimal for all cost calculations to maintain precision.

### Subtask T004 – Add `unit_cost` to breakdown items

**Purpose**: Include per-lot unit cost in the breakdown for transparency.

**Steps**:
1. In the breakdown item dict, add: `"unit_cost": item.unit_cost`
2. Ensure this is a Decimal value

**Files**: `src/services/pantry_service.py`

**Notes**: This enables callers to see exactly what each lot cost.

### Subtask T005 – Write tests for dry_run behavior

**Purpose**: Verify dry_run works correctly and doesn't break existing behavior.

**Steps**:
1. Create test: `test_consume_fifo_dry_run_does_not_modify_inventory`
   - Setup: Create pantry items with known quantities
   - Act: Call `consume_fifo(dry_run=True)`
   - Assert: Pantry quantities unchanged after call
2. Create test: `test_consume_fifo_dry_run_returns_correct_cost`
   - Setup: Create pantry items with known unit costs
   - Act: Call `consume_fifo(dry_run=True)`
   - Assert: `total_cost` matches expected FIFO calculation
3. Create test: `test_consume_fifo_dry_run_includes_unit_cost_in_breakdown`
   - Assert: Each breakdown item has `unit_cost` field
4. Create test: `test_consume_fifo_default_still_modifies_inventory`
   - Verify backward compatibility: `dry_run=False` (default) updates quantities

**Files**: `src/tests/test_pantry_service.py`

**Notes**: Use existing test fixtures where possible. Follow existing test patterns in the file.

## Test Strategy

**Required Tests** (>70% coverage mandate):
- `test_consume_fifo_dry_run_does_not_modify_inventory`
- `test_consume_fifo_dry_run_returns_correct_cost`
- `test_consume_fifo_dry_run_includes_unit_cost_in_breakdown`
- `test_consume_fifo_default_still_modifies_inventory`
- `test_consume_fifo_dry_run_respects_fifo_order`

**Commands**:
```bash
pytest src/tests/test_pantry_service.py -v -k "consume_fifo"
pytest src/tests/test_pantry_service.py -v --cov=src/services/pantry_service
```

**Fixtures**: Use existing `db_session`, `sample_ingredient`, `sample_variant`, `sample_pantry_item` fixtures.

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Breaking existing consumption flow | Run existing tests before and after changes |
| Session state leakage in dry_run | Don't call flush/commit; rely on session rollback at scope exit |
| Cost calculation precision | Use Decimal throughout; test with known values |

## Definition of Done Checklist

- [x] T001: `dry_run` parameter added to `consume_fifo()` signature
- [x] T002: Dry-run branch logic skips database writes
- [x] T003: `total_cost` field added to result dict
- [x] T004: `unit_cost` field added to breakdown items
- [x] T005: All dry_run tests pass (8 tests in test_pantry_service.py)
- [x] Existing `consume_fifo` tests still pass (backward compatibility - 6 tests in test_fifo_scenarios.py)
- [x] `tasks.md` updated with completion status

## Review Guidance

**Key Acceptance Checkpoints**:
1. Call `consume_fifo(dry_run=True)` - pantry quantities must be unchanged
2. Call `consume_fifo(dry_run=False)` - must update quantities (existing behavior)
3. Verify `total_cost` matches manual FIFO calculation
4. Check Decimal precision in cost fields

**Constitution Compliance**:
- FIFO ordering must be correct in both modes
- No session leaks or uncommitted state issues

## Activity Log

- 2025-12-02T00:00:00Z – system – lane=planned – Prompt created via /spec-kitty.tasks
- 2025-12-03T03:37:10Z – claude – shell_pid=67856 – lane=doing – Started implementation
- 2025-12-03T04:15:00Z – claude – lane=doing – Completed T001-T005, all tests passing (14 total)
- 2025-12-03T15:19:47Z – claude – shell_pid=75194 – lane=for_review – Completed all subtasks T001-T005, all 14 tests passing
- 2025-12-03T20:25:00Z – claude – shell_pid=79852 – lane=done – APPROVED: All tests pass (14/14), contract compliance verified, FIFO accuracy confirmed, Definition of Done complete
- 2025-12-03T17:29:54Z – claude – shell_pid=75194 – lane=done – Approved: All 14 tests pass, contract compliance verified
