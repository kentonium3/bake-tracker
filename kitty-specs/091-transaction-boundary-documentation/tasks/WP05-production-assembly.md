---
work_package_id: WP05
title: Production & Assembly Services
lane: "for_review"
dependencies: [WP01]
base_branch: 091-transaction-boundary-documentation-WP01
base_commit: ea54478c184557f13c16ab46b637a8903d9343c6
created_at: '2026-02-03T05:22:34.429895+00:00'
subtasks:
- T015
- T016
- T017
- T018
phase: Phase 2 - Documentation
assignee: ''
agent: ''
shell_pid: "29745"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-02-03T04:37:19Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP05 – Production & Assembly Services

## Objectives & Success Criteria

**Goal**: Add transaction boundary documentation to production and assembly service files.

**Success Criteria**:
- [ ] All public functions in `batch_production_service.py` have "Transaction boundary:" section
- [ ] All public functions in `assembly_service.py` have "Transaction boundary:" section
- [ ] Existing docs verified and standardized

**Implementation Command**:
```bash
spec-kitty implement WP05 --base WP01
```

**Parallel-Safe**: Yes - assign to Gemini

## Context & Constraints

**References**:
- Templates: `kitty-specs/091-transaction-boundary-documentation/research/docstring_templates.md`
- Existing docs: These files have the BEST existing documentation

**Key Constraints**:
- These are critical multi-step atomic operations
- Existing documentation is excellent - preserve and verify
- These serve as examples for Pattern C in other services

## Subtasks & Detailed Guidance

### Subtask T015 – Document batch_production_service.py (~8 functions)

**Purpose**: Add transaction boundary documentation to all public functions.

**Files**:
- Edit: `src/services/batch_production_service.py`

**Functions to document**:

| Function | Type | Template | Notes |
|----------|------|----------|-------|
| `check_can_produce` | MULTI | Pattern C | **DOCUMENTED** (lines 219-244) |
| `record_batch_production` | MULTI | Pattern C | **DOCUMENTED** (lines 329-397) - EXCELLENT |
| `get_production_history` | READ | Pattern A | |
| `get_production_run` | READ | Pattern A | |
| `export_production_history` | READ | Pattern A | |
| `import_production_history` | MULTI | Pattern C | Version compatibility import |

**For check_can_produce**:
Existing documentation (lines 219-244) should include:
- Dry-run semantics
- Session passing to get_aggregated_ingredients and consume_fifo
- Atomicity within session

**For record_batch_production**:
This is the GOLD STANDARD for Pattern C documentation. Verify it includes:
1. "Transaction boundary:" phrase
2. 7-step atomic operation list
3. CRITICAL note about session passing
4. Clear rollback guarantees

**For undocumented functions (get_production_history, etc.)**:
Add Pattern A documentation:
```python
def get_production_history(filters: dict = None, session: Optional[Session] = None):
    """
    Retrieve production run history with optional filtering.

    Transaction boundary: Read-only, no transaction needed.
    Safe to call without session - uses temporary session for query.

    Args:
        filters: Optional dictionary of filter criteria
        session: Optional session (for composition with other operations)

    Returns:
        List of ProductionRun instances matching filters

    Raises:
        None (returns empty list if no matches)
    """
```

**Validation**:
- [ ] All 8 functions documented
- [ ] Existing docs preserved and verified

---

### Subtask T016 – Document assembly_service.py (~11 functions)

**Purpose**: Add transaction boundary documentation to all public functions.

**Files**:
- Edit: `src/services/assembly_service.py`

**Functions to document**:

| Function | Type | Template | Notes |
|----------|------|----------|-------|
| `check_can_assemble` | MULTI | Pattern C | **DOCUMENTED** (lines 200-205) |
| `record_assembly` | MULTI | Pattern C | **DOCUMENTED** (lines 344-392) - EXCELLENT |
| `get_assembly_history` | READ | Pattern A | |
| `get_assembly_run` | READ | Pattern A | |
| `export_assembly_history` | READ | Pattern A | |
| `import_assembly_history` | MULTI | Pattern C | UUID dedup import |
| `check_packaging_assigned` | READ | Pattern A | |

**For record_assembly**:
This is another GOLD STANDARD example. Verify it documents:
1. 9-step atomic operation
2. Component consumption (FU, FG, packaging)
3. Session passing to all nested calls
4. Rollback guarantees

**Validation**:
- [ ] All 11 functions documented
- [ ] Existing docs preserved and verified

---

### Subtask T017 – Verify record_batch_production docs

**Purpose**: Ensure documentation is the model for Pattern C.

**Steps**:
1. Read docstring at lines 329-397
2. Verify all Pattern C elements present
3. Note this as example for other services

**Checklist**:
- [ ] "Transaction boundary:" phrase present
- [ ] "Atomicity guarantee:" statement
- [ ] Steps numbered and specific (7 steps)
- [ ] "CRITICAL:" session passing note
- [ ] All service calls documented

---

### Subtask T018 – Verify record_assembly docs

**Purpose**: Ensure documentation is the model for Pattern C.

**Steps**:
1. Read docstring at lines 344-392
2. Verify all Pattern C elements present
3. Compare with record_batch_production for consistency

**Checklist**:
- [ ] "Transaction boundary:" phrase present
- [ ] "Atomicity guarantee:" statement
- [ ] Steps numbered and specific (9 steps)
- [ ] "CRITICAL:" session passing note
- [ ] Component consumption documented

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Overwriting good docs | Read existing first, enhance only |
| Inconsistent with other services | Use these as models for others |

## Definition of Done Checklist

- [ ] batch_production_service.py: All 8 functions documented
- [ ] assembly_service.py: All 11 functions documented
- [ ] record_batch_production: Verified as Pattern C model
- [ ] record_assembly: Verified as Pattern C model
- [ ] Tests still pass: `pytest src/tests -v -k "production or assembly"`

## Review Guidance

**Reviewers should verify**:
1. Existing excellent docs NOT degraded
2. New docs match existing style
3. These can serve as examples for team

## Activity Log

- 2026-02-03T04:37:19Z – system – lane=planned – Prompt created.
- 2026-02-03T05:29:15Z – unknown – shell_pid=29745 – lane=for_review – Ready for review: Added transaction boundary docs to batch_production_service.py (8 entries) and assembly_service.py (11 entries). GOLD STANDARD Pattern C verified for record_batch_production and record_assembly. All 340 tests pass.
