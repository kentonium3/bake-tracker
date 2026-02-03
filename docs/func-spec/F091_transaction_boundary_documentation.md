# F091: Transaction Boundary Documentation

**Version**: 2.0 (Revised - Documentation Focus)
**Priority**: HIGH
**Type**: Documentation + Code Quality
**Estimated Effort**: 2-3 days

---

## Executive Summary

Current gaps:
- ❌ Service function docstrings lack transaction boundary documentation
- ❌ Multi-step operations lack atomicity guarantees documentation
- ❌ Transaction scope unclear for complex operations
- ❌ Developers must infer transaction behavior from code

This spec adds comprehensive transaction boundary documentation to all service functions, clarifying atomicity guarantees and transaction scope for debugging and maintenance.

**Note:** Savepoint support moved to web-prep/F002 (parked until needed).

---

## Problem Statement

**Current State (UNDOCUMENTED):**
```
Service Functions
├─ ✅ Session parameter pattern works correctly
├─ ✅ Multi-step operations ARE atomic (pass session)
├─ ❌ Transaction boundaries NOT documented in docstrings
├─ ❌ Atomicity guarantees implicit (must read code)
└─ ❌ Transaction scope unclear to developers

Documentation
├─ ❌ No "Transaction boundary:" sections in docstrings
└─ ❌ Developers infer behavior from code inspection
```

**Target State (WELL-DOCUMENTED):**
```
Service Functions
├─ ✅ All functions document transaction boundaries
├─ ✅ Atomicity guarantees explicitly stated
├─ ✅ Multi-step operation safety documented
├─ ✅ Session parameter usage explained
└─ ✅ Transaction patterns guide exists

Documentation
├─ ✅ "Transaction boundary:" in every service docstring
└─ ✅ Clear expectations without reading implementation
```

---

## CRITICAL: Study These Files FIRST

**Before implementation, planning phase MUST review:**

1. **Multi-Step Operations (Atomic Patterns)**
   - `src/services/batch_production_service.py` → `record_batch_production()`
   - `src/services/assembly_service.py` → `record_assembly()`
   - `src/services/planning/planning_service.py` → Multi-step planning operations
   - Note: How session is passed to nested service calls

2. **Single-Step Operations (Simple Transactions)**
   - `src/services/ingredient_service.py` → CRUD operations
   - `src/services/recipe_service.py` → Recipe management
   - Note: Session parameter pattern even for simple operations

3. **Read-Only Operations**
   - Various `get_*()` and `list_*()` functions
   - Note: When transaction isn't needed but session accepted

4. **Session Parameter Pattern Documentation**
   - `CLAUDE.md` → Current session management guidance
   - Note: Existing pattern to follow

---

## Requirements Reference

This specification implements:
- **Code Quality Principle VI.C.2**: Transaction Boundaries
  - "Service methods define transaction scope"
  - "No silent auto-commits; failures roll back cleanly"
- **Code Quality Principle VI.E.1**: Logging Strategy
  - "Include operation context (user intent, entity IDs, timing)"
- **Code Quality Principle VI.D.1**: Method Signatures
  - "Type hints for all public methods"
  - "Explicit over implicit"

From: `docs/design/code_quality_principles_revised.md` (v1.0)

---

## Functional Requirements

### FR-1: Add Transaction Boundary Docstrings

**What it must do:**
- Add "Transaction boundary:" section to ALL service function docstrings (~50-60 functions)
- Explicitly state atomicity guarantees (all-or-nothing vs read-only)
- Document multi-step operation scope and session passing
- Clarify session parameter usage

**Docstring patterns by operation type:**

**Pattern A: Read-Only Operation**
```python
"""
[Function description]

Transaction boundary: Read-only, no transaction needed.
Safe to call without session - uses temporary session for query.

Args:
    ...
    session: Optional session (for composition with other operations)

Returns:
    ...

Raises:
    ...
"""
```

**Pattern B: Single-Step Write**
```python
"""
[Function description]

Transaction boundary: Single operation, automatically atomic.
If session provided, caller controls transaction commit/rollback.
If session not provided, uses session_scope() (auto-commit on success).

Args:
    ...
    session: Optional session for transactional composition

Returns:
    ...

Raises:
    ...
"""
```

**Pattern C: Multi-Step Atomic Operation**
```python
"""
[Function description]

Transaction boundary: ALL operations in single session (atomic).
Atomicity guarantee: Either ALL steps succeed OR entire operation rolls back.
Steps executed atomically:
1. [Step 1 description]
2. [Step 2 description]
3. [Step 3 description]

CRITICAL: All nested service calls receive session parameter to ensure
atomicity. Never create new session_scope() within this function.

Args:
    ...
    session: Optional session for transactional composition

Returns:
    ...

Raises:
    ...
"""
```

**Implementation approach:**
1. Identify all service functions (~50-60 functions across all service files)
2. Classify each as: read-only, single-step write, or multi-step atomic
3. Add appropriate "Transaction boundary:" section to docstring
4. Document atomicity guarantees explicitly
5. Document session parameter usage

**Success criteria:**
- [ ] All service functions have "Transaction boundary:" documentation
- [ ] Atomicity guarantees explicitly stated (all-or-nothing or read-only)
- [ ] Multi-step operations list steps executed atomically
- [ ] Session parameter usage documented consistently
- [ ] Pattern consistency verified across all services

---

### FR-2: Audit Multi-Step Operations for Atomicity

**What it must do:**
- Identify all multi-step service operations (~20 functions)
- Verify atomicity by inspecting session passing
- Fix any operations with broken atomicity (missing session parameter)
- Document transaction scope in docstrings

**Audit checklist per multi-step operation:**
1. Does function accept `session` parameter? (Required)
2. Are all nested service calls passed the session? (Required for atomicity)
3. Are steps documented as atomic in docstring? (Required for clarity)
4. Is transaction boundary clear from docstring? (Required)

**Known multi-step operations to audit:**
- `batch_production_service.record_batch_production()` — production with consumption
- `assembly_service.record_assembly()` — assembly with component consumption
- `planning_service.record_assembly_confirmation()` — multi-step status updates
- Any service function calling 2+ other service functions

**Success criteria:**
- [ ] All multi-step operations identified (~20 functions)
- [ ] Each operation audited for correct session passing
- [ ] Any broken atomicity patterns fixed (add session parameter)
- [ ] Transaction boundaries documented in docstrings
- [ ] Audit results documented (list of operations verified)

---

### FR-3: Create Transaction Patterns Guide

**What it must do:**
- Document transaction patterns in CLAUDE.md or separate guide
- Provide clear examples of each pattern
- Document common pitfalls and how to avoid them
- Reference from service function docstrings

**Content structure:**

1. **Introduction**
   - Purpose of transaction documentation
   - How to read "Transaction boundary:" sections
   - When transactions matter vs don't matter

2. **Pattern Catalog**
   - **Read-Only Operations**: When and why no transaction needed
   - **Single-Step Write**: Simple create/update/delete
   - **Multi-Step Atomic**: Multiple operations that must succeed together
   - **Nested Service Calls**: How to maintain atomicity

3. **Session Parameter Pattern**
   - Why every service function accepts `session=None`
   - When to pass session (composing operations)
   - When to omit session (standalone calls)
   - Desktop vs web usage (same pattern, different callers)

4. **Common Pitfalls**
   - ❌ **Multiple session_scope() calls**: Breaks atomicity
   - ❌ **Not passing session to nested calls**: Breaks atomicity
   - ❌ **Assuming implicit transaction scope**: Causes bugs
   - ✅ **Pass session parameter**: Maintains atomicity
   - ✅ **Document transaction boundaries**: Prevents confusion

5. **Code Examples**
   - Example 1: Read-only operation (ingredient lookup)
   - Example 2: Single-step write (create ingredient)
   - Example 3: Multi-step atomic (batch production)
   - Example 4: Non-atomic pitfall (multiple session_scope() calls)
   - Example 5: Atomic fix (passing session parameter)

**Success criteria:**
- [ ] Transaction patterns guide exists (CLAUDE.md or docs/design/)
- [ ] All three patterns documented with examples
- [ ] Common pitfalls documented with fixes
- [ ] Session parameter pattern explained clearly
- [ ] Guide referenced from code comments where appropriate

---

## Out of Scope

**Explicitly NOT included in this feature:**

- ❌ **Savepoint implementation** — Moved to web-prep/F002 (parked until needed)
  - No current use cases for partial rollback
  - Can implement in 30 minutes when needed
  - YAGNI: Don't build infrastructure for hypothetical scenarios

- ❌ **Changing transaction isolation levels** — Defer to web migration
  - SQLite defaults sufficient for desktop
  - PostgreSQL will need isolation level configuration

- ❌ **Distributed transactions** — Not needed (single database)

- ❌ **Two-phase commit** — YAGNI (single database, no microservices)

- ❌ **Transaction retry logic** — Defer to error handling feature
  - Current error handling is sufficient
  - Retry logic adds complexity without clear benefit

- ❌ **Refactoring service functions** — Focus on documentation
  - Existing patterns are correct (session parameter works)
  - No changes to implementation needed

---

## Success Criteria

**Complete when:**

### Documentation Added
- [ ] All service functions (~50-60) have "Transaction boundary:" docstrings
- [ ] Atomicity guarantees explicitly stated in each docstring
- [ ] Multi-step operations document steps executed atomically
- [ ] Session parameter usage documented consistently
- [ ] Transaction patterns guide exists (CLAUDE.md or docs/design/)

### Audit Completed
- [ ] All multi-step operations identified (~20 functions)
- [ ] Each operation verified for correct session passing
- [ ] Any broken atomicity patterns fixed (if found)
- [ ] Audit results documented (list of operations verified)

### Patterns Guide Created
- [ ] Three transaction patterns documented (read-only, single-step, multi-step)
- [ ] Common pitfalls documented with examples
- [ ] Session parameter pattern explained
- [ ] Code examples provided for each pattern

### Quality Checks
- [ ] Follows Code Quality Principle VI.C (Transaction Boundaries)
- [ ] Follows Code Quality Principle VI.E (Observability)
- [ ] Documentation consistent across all services
- [ ] No generic or placeholder documentation

---

## Architecture Principles

### Transaction Documentation Standard

**Every service function MUST document transaction boundaries:**

1. **Transaction Scope**
   - Read-only: No transaction needed (query only)
   - Single session: One operation, automatic commit
   - Multi-step atomic: All operations in single session

2. **Atomicity Guarantee**
   - All-or-nothing: All steps succeed OR all roll back
   - Read-only: No side effects, no transaction
   - Composable: Session parameter enables atomic composition

3. **Session Parameter Usage**
   - When provided: Caller controls transaction
   - When omitted: Function creates own session_scope()
   - Why accepted: Enables transactional composition

### Multi-Step Atomicity Pattern

**Critical for data integrity:**
- All nested service calls MUST receive session parameter
- Never create new session_scope() within multi-step operation
- Document steps executed atomically in docstring
- Verify session passing during code review

### Documentation as Safety Net

**Clear documentation prevents bugs:**
- Developer knows transaction scope without reading implementation
- Code reviewer can verify atomicity from docstring
- AI agent can check session parameter usage
- Future maintainer understands safety guarantees

---

## Constitutional Compliance

✅ **Principle VI.C.2: Transaction Boundaries**
- "Service methods define transaction scope" — Now documented explicitly
- "No silent auto-commits" — Documented in session parameter usage

✅ **Principle VI.E.1: Logging Strategy**
- "Include operation context" — Transaction boundaries are operation context
- Documentation aids debugging multi-step operations

✅ **Principle VI.D.1: Method Signatures**
- "Type hints for all public methods" — Session parameter has type hint
- "Explicit over implicit" — Transaction boundaries now explicit

✅ **New Checklist Item: Code Review Checklist**
- "All public functions have docstrings" — Transaction boundary section included

---

## Risk Considerations

### Risk: Missing Undocumented Operations
**Mitigation:**
- Systematic audit of all service files (~10 files)
- Grep for `def .*session` to find functions with session parameter
- Manual review of each service module

### Risk: Inconsistent Documentation Format
**Mitigation:**
- Provide three standard templates (read-only, single-step, multi-step)
- Code review checks for "Transaction boundary:" section
- Use same phrasing across all services

### Risk: Documentation Becomes Stale
**Mitigation:**
- Add to code review checklist: "Transaction boundary matches implementation?"
- Update documentation when refactoring transaction scope
- Include in PR template: "Did you update transaction documentation?"

### Risk: Effort Underestimated
**Mitigation:**
- Estimate: ~50-60 functions × 5 minutes each = 4-5 hours for docstrings
- Estimate: ~20 multi-step operations × 15 minutes audit = 5 hours
- Estimate: Transaction guide = 4 hours
- Total: 13-14 hours (2 days) — reasonable for documentation task

---

## Implementation Plan

### Phase 1: Service Function Documentation (1-2 days)
1. **Audit service files** — List all functions with session parameter (~50-60)
2. **Classify functions** — Read-only, single-step, or multi-step
3. **Add docstrings** — Use appropriate template for each classification
4. **Verify consistency** — Review all docstrings for pattern consistency

### Phase 2: Multi-Step Operation Audit (1 day)
1. **Identify multi-step operations** — Functions calling 2+ service functions (~20)
2. **Verify session passing** — Check all nested calls receive session
3. **Fix broken patterns** — Add session parameter if missing (unlikely)
4. **Document audit results** — List of operations verified

### Phase 3: Transaction Patterns Guide (4 hours)
1. **Draft guide outline** — Structure content sections
2. **Write pattern descriptions** — Three patterns with examples
3. **Document common pitfalls** — Anti-patterns and fixes
4. **Add to CLAUDE.md or docs/design/** — Make discoverable

### Phase 4: Verification & Cleanup (2 hours)
1. **Review all documentation** — Consistency check
2. **Test docstring rendering** — Verify formatting
3. **Update code review checklist** — Add transaction boundary check
4. **Create PR** — Submit for review

**Total estimated effort:** 2-3 days

---

## Notes for Implementation

### Pattern Discovery (Planning Phase)

**Study these files for patterns:**
1. `src/services/batch_production_service.py`
   - `record_batch_production()` — Excellent multi-step atomic example
   - Note: How session passed to `consume_fifo()`, `get_aggregated_ingredients()`

2. `src/services/assembly_service.py`
   - `record_assembly()` — Another multi-step atomic example
   - Note: Multiple component types consumed atomically

3. `src/services/ingredient_service.py`
   - `create_ingredient()`, `update_ingredient()` — Single-step examples
   - `get_ingredient()` — Read-only example

### Key Patterns to Copy

**Existing good patterns:**
- Session parameter: `session: Optional[Session] = None`
- Session handling: `if session is not None: ... else: with session_scope():`
- Nested calls: Always pass `session=session` to maintain atomicity

**Docstring template usage:**
- Read-only: `get_*()`, `list_*()` functions
- Single-step: `create_*()`, `update_*()`, `delete_*()` with no nested calls
- Multi-step: Any function calling other service functions

### Focus Areas

1. **Documentation is primary deliverable** — Not code changes
2. **Verify atomicity, don't assume** — Audit session passing
3. **Consistency matters** — Use templates, same phrasing
4. **Examples help** — Transaction guide needs clear code examples

### Docstring Templates Reference

Available in FR-1 section above:
- Pattern A: Read-Only Operation
- Pattern B: Single-Step Write
- Pattern C: Multi-Step Atomic Operation

Copy exact phrasing for consistency.

---

**END OF SPECIFICATION**
