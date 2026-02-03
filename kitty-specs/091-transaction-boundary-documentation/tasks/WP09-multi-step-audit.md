---
work_package_id: WP09
title: Multi-Step Operation Audit
lane: "doing"
dependencies:
- WP02
base_branch: 091-transaction-boundary-documentation-WP02
base_commit: 045e749bde170f2c0207d5c1b90fae3ab0919311
created_at: '2026-02-03T06:27:46.394329+00:00'
subtasks:
- T035
- T036
- T037
- T038
- T039
- T040
phase: Phase 3 - Audit
assignee: ''
agent: "claude-review"
shell_pid: "59253"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-02-03T04:37:19Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP09 – Multi-Step Operation Audit

## Objectives & Success Criteria

**Goal**: Audit all MULTI functions for correct session passing and atomicity guarantees.

**Success Criteria**:
- [ ] All MULTI functions audited for session passing
- [ ] All nested service calls verified to receive `session=session`
- [ ] Any broken patterns identified and fixed
- [ ] Audit results documented

**Implementation Command**:
```bash
spec-kitty implement WP09 --base WP08
```

**Note**: This WP requires all documentation WPs (WP02-WP08) to be complete.

## Context & Constraints

**References**:
- Inventory: `kitty-specs/091-transaction-boundary-documentation/research/service_inventory.md`
- Constitution: `.kittify/memory/constitution.md` (Principle VI.C.2)
- CLAUDE.md: Session Management section

**Key Constraints**:
- Audit is verification, not documentation
- Fix only if broken atomicity found
- Document all audit findings

## Subtasks & Detailed Guidance

### Subtask T035 – Audit inventory_item_service.py multi-step functions

**Purpose**: Verify atomicity of 9 MULTI functions in inventory_item_service.py.

**Files**:
- Review: `src/services/inventory_item_service.py`

**Audit checklist for each MULTI function**:

| Function | Nested Calls | Session Passed? | Status |
|----------|--------------|-----------------|--------|
| `add_to_inventory` | ? | ? | |
| `get_total_quantity` | get_ingredient, get_inventory_items | ? | |
| `consume_fifo` | ? | ? | |
| `update_inventory_supplier` | ? | ? | |
| `update_inventory_quantity` | ? | ? | |
| `manual_adjustment` | ? | ? | |

**Audit steps for each function**:
1. Identify all calls to other service functions
2. Check if `session=session` is passed to each call
3. Check for multiple `with session_scope()` calls (anti-pattern)
4. Mark as PASS or FAIL

**Example audit**:
```python
# CORRECT - session passed
def manual_adjustment(item_id, adjustment, session=None):
    def _impl(sess):
        item = get_inventory_item(item_id, session=sess)  # session passed
        depletion = create_depletion(item, adjustment, session=sess)  # session passed
        return depletion

    if session: return _impl(session)
    with session_scope() as sess: return _impl(sess)

# WRONG - session not passed (broken atomicity)
def manual_adjustment(item_id, adjustment, session=None):
    item = get_inventory_item(item_id)  # MISSING session
    with session_scope() as sess:
        depletion = create_depletion(item, adjustment, session=sess)
    return depletion
```

**Validation**:
- [ ] All 9 MULTI functions audited
- [ ] Session passing verified for each nested call

---

### Subtask T036 – Audit purchase_service.py multi-step functions

**Purpose**: Verify atomicity of 12 MULTI functions in purchase_service.py.

**Files**:
- Review: `src/services/purchase_service.py`

**Functions to audit**:
- `record_purchase`
- `detect_price_change`
- `delete_purchase`
- `update_purchase`
- And 8 more from inventory

**Audit each using same checklist as T035**.

**Validation**:
- [ ] All 12 MULTI functions audited

---

### Subtask T037 – Audit product_service.py multi-step functions

**Purpose**: Verify atomicity of 7 MULTI functions in product_service.py.

**Files**:
- Review: `src/services/product_service.py`

**Functions to audit**:
- `create_product`
- `create_provisional_product`
- `set_preferred_product`
- `delete_product`
- `get_product_recommendation`
- Others as identified

**Validation**:
- [ ] All 7 MULTI functions audited

---

### Subtask T038 – Audit assembly_service.py and batch_production_service.py

**Purpose**: Verify atomicity of critical production functions.

**Files**:
- Review: `src/services/assembly_service.py`
- Review: `src/services/batch_production_service.py`

**Functions to audit (known good - verify)**:
- `record_batch_production` - Should be correct (documented well)
- `record_assembly` - Should be correct (documented well)
- `check_can_produce`
- `check_can_assemble`

**These are expected to PASS - verify documentation matches implementation**.

**Validation**:
- [ ] All MULTI functions audited
- [ ] Existing good patterns confirmed

---

### Subtask T039 – Fix any broken atomicity patterns

**Purpose**: Fix session parameter passing where missing.

**If broken patterns found**:
1. Document the issue in audit results
2. Add `session=session` to the nested call
3. Verify the calling function accepts session parameter
4. Run tests to ensure fix works

**Example fix**:
```python
# Before (broken)
def some_function(...):
    with session_scope() as sess:
        result1 = other_service_call(...)  # Missing session
        result2 = sess.query(...).first()

# After (fixed)
def some_function(..., session=None):
    def _impl(sess):
        result1 = other_service_call(..., session=sess)  # Added session
        result2 = sess.query(...).first()
        return ...

    if session is not None:
        return _impl(session)
    with session_scope() as sess:
        return _impl(sess)
```

**Validation**:
- [ ] All identified issues fixed
- [ ] Tests pass after fixes

---

### Subtask T040 – Document audit results

**Purpose**: Create audit results document for reference.

**Files**:
- Create: `kitty-specs/091-transaction-boundary-documentation/research/atomicity_audit.md`

**Document structure**:
```markdown
# Transaction Atomicity Audit Results

**Date**: YYYY-MM-DD
**Auditor**: [agent name]

## Summary

- Total MULTI functions audited: XX
- Passed: XX
- Failed (fixed): XX
- Already correct: XX

## Audit by Service

### inventory_item_service.py

| Function | Nested Calls | Session Passed? | Status |
|----------|--------------|-----------------|--------|
| add_to_inventory | create_purchase, create_item | Yes | PASS |
| ... | ... | ... | ... |

### purchase_service.py
[Same format]

## Issues Found and Fixed

### Issue 1: [function_name]
- **Problem**: Session not passed to [nested_call]
- **Fix**: Added session=session parameter
- **Commit**: [commit hash if applicable]

## Conclusions

[Overall assessment of codebase atomicity]
```

**Validation**:
- [ ] Audit document created
- [ ] All services covered
- [ ] Issues and fixes documented

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| May find significant bugs | Document for separate fix if > minor |
| Session pattern not used | Report as tech debt if not using pattern |

## Definition of Done Checklist

- [ ] All MULTI functions in inventory_item_service audited
- [ ] All MULTI functions in purchase_service audited
- [ ] All MULTI functions in product_service audited
- [ ] Production/assembly services verified
- [ ] Any broken patterns fixed
- [ ] Audit results documented in research/atomicity_audit.md
- [ ] Tests pass: `pytest src/tests -v`

## Review Guidance

**Reviewers should verify**:
1. Audit thoroughness (spot check 5 functions)
2. Fixes are correct (session passed, not new session_scope)
3. Documentation complete

## Activity Log

- 2026-02-03T04:37:19Z – system – lane=planned – Prompt created.
- 2026-02-03T06:36:24Z – unknown – shell_pid=50996 – lane=for_review – Audit complete: 35 MULTI functions audited, 5 minor issues documented, no critical fixes needed
- 2026-02-03T06:44:02Z – claude-review – shell_pid=59253 – lane=doing – Started review via workflow command
