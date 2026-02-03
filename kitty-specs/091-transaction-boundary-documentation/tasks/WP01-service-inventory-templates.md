---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
  - "T003"
  - "T004"
title: "Service Inventory & Templates"
phase: "Phase 1 - Foundation"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
dependencies: []
history:
  - timestamp: "2026-02-03T04:37:19Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 – Service Inventory & Templates

## Objectives & Success Criteria

**Goal**: Create comprehensive service function inventory and establish documentation templates.

**Success Criteria**:
- [ ] Inventory document exists with ALL service functions listed
- [ ] Each function classified as READ/SINGLE/MULTI
- [ ] Existing "Transaction boundary:" sections identified
- [ ] Template examples file created with Pattern A/B/C

**Implementation Command**:
```bash
spec-kitty implement WP01
```

## Context & Constraints

**References**:
- Spec: `kitty-specs/091-transaction-boundary-documentation/spec.md`
- Plan: `kitty-specs/091-transaction-boundary-documentation/plan.md`
- Func-spec: `docs/func-spec/F091_transaction_boundary_documentation.md`
- Constitution: `.kittify/memory/constitution.md` (Principle VI.C.2)

**Key Decisions**:
- This is foundation work - all other WPs depend on this
- Use exact templates from func-spec FR-1
- Output goes to `kitty-specs/091-transaction-boundary-documentation/research/`

## Subtasks & Detailed Guidance

### Subtask T001 – Create service function inventory

**Purpose**: Catalog all public functions in service files that need transaction boundary documentation.

**Steps**:
1. Create directory: `mkdir -p kitty-specs/091-transaction-boundary-documentation/research/`
2. Create file: `research/service_inventory.md`
3. For each file in `src/services/`:
   - List all public functions (no leading underscore)
   - Include function signature
   - Note if it has `session` parameter
4. Include these service files:
   - `ingredient_service.py`, `ingredient_crud_service.py`
   - `recipe_service.py`
   - `product_service.py`, `product_catalog_service.py`
   - `inventory_item_service.py`
   - `purchase_service.py`, `supplier_service.py`
   - `batch_production_service.py`, `assembly_service.py`
   - `planning/planning_service.py`, `plan_state_service.py`, `plan_snapshot_service.py`
   - `event_service.py`, `recipient_service.py`
   - `finished_good_service.py`
   - `material_consumption_service.py`, `material_purchase_service.py`
   - `material_inventory_service.py`, `finished_goods_inventory_service.py`
   - `import_export_service.py`, `enhanced_import_service.py`
   - `transaction_import_service.py`, `catalog_import_service.py`
   - `coordinated_export_service.py`, `denormalized_export_service.py`
   - `unit_service.py`, `unit_converter.py`
   - `preferences_service.py`, `health_service.py`

**Files**:
- Create: `kitty-specs/091-transaction-boundary-documentation/research/service_inventory.md`

**Validation**:
- [ ] All service files scanned
- [ ] Count matches grep output: `grep -r "^def " src/services/*.py | wc -l`

---

### Subtask T002 – Classify all functions as READ/SINGLE/MULTI

**Purpose**: Determine which docstring template each function needs.

**Classification Rules**:

**READ** (Pattern A):
- Function only queries data (no INSERT/UPDATE/DELETE)
- Names typically: `get_*`, `list_*`, `search_*`, `find_*`, `check_*`, `can_*`, `calculate_*`
- Returns data without side effects

**SINGLE** (Pattern B):
- Function performs ONE database write operation
- Names typically: `create_*`, `update_*`, `delete_*` (simple cases)
- Does NOT call other service functions

**MULTI** (Pattern C):
- Function calls 2+ other service functions
- OR performs multiple related writes
- OR has complex orchestration logic
- Names vary: `record_*`, `process_*`, or any `create_*`/`update_*`/`delete_*` that calls other services

**Steps**:
1. For each function in inventory, examine the implementation
2. Check for:
   - Calls to other service functions
   - Multiple `session.add()` / `session.delete()` calls
   - `with session_scope()` patterns
3. Add classification column to inventory table

**Example Classifications**:
```
| Function | File | Type | Has Session Param? |
|----------|------|------|-------------------|
| get_ingredient | ingredient_service.py | READ | Yes |
| create_ingredient | ingredient_service.py | SINGLE | Yes |
| delete_ingredient_safe | ingredient_service.py | MULTI | Yes |
| record_batch_production | batch_production_service.py | MULTI | Yes |
```

**Validation**:
- [ ] Every function has classification
- [ ] Classifications make sense (no SINGLE functions calling other services)

---

### Subtask T003 – Document existing "Transaction boundary:" sections

**Purpose**: Identify functions that already have documentation to avoid redundant work.

**Steps**:
1. Grep for existing documentation:
   ```bash
   grep -rn "Transaction boundary:" src/services/
   ```
2. For each match, add "HAS_DOC" flag to inventory
3. Create summary section showing documented functions:

**Known documented functions** (from prior analysis):
- `ingredient_service.get_ingredient` (lines 281-283)
- `inventory_item_service.consume_fifo` (lines 304-326) - EXCELLENT
- `purchase_service.record_purchase` (lines 74-126)
- `batch_production_service.check_can_produce` (lines 219-244)
- `batch_production_service.record_batch_production` (lines 329-397) - EXCELLENT
- `assembly_service.check_can_assemble` (lines 200-205)
- `assembly_service.record_assembly` (lines 344-392) - EXCELLENT

**Output**: Add "Existing Documentation" section to inventory with line numbers.

**Validation**:
- [ ] All existing docs found
- [ ] Line numbers recorded for reference

---

### Subtask T004 – Create docstring template examples file

**Purpose**: Provide copy-paste templates for consistent documentation.

**Steps**:
1. Create file: `research/docstring_templates.md`
2. Include three patterns from func-spec FR-1:

**Pattern A: Read-Only Operation**
```python
"""
[Function description - what it does and returns]

Transaction boundary: Read-only, no transaction needed.
Safe to call without session - uses temporary session for query.

Args:
    [parameter descriptions]
    session: Optional session (for composition with other operations)

Returns:
    [return value description]

Raises:
    [exceptions that can be raised]
"""
```

**Pattern B: Single-Step Write**
```python
"""
[Function description - what it creates/updates/deletes]

Transaction boundary: Single operation, automatically atomic.
If session provided, caller controls transaction commit/rollback.
If session not provided, uses session_scope() (auto-commit on success).

Args:
    [parameter descriptions]
    session: Optional session for transactional composition

Returns:
    [return value description]

Raises:
    [exceptions that can be raised]
"""
```

**Pattern C: Multi-Step Atomic Operation**
```python
"""
[Function description - overall operation]

Transaction boundary: ALL operations in single session (atomic).
Atomicity guarantee: Either ALL steps succeed OR entire operation rolls back.
Steps executed atomically:
1. [Step 1 description]
2. [Step 2 description]
3. [Step 3 description]

CRITICAL: All nested service calls receive session parameter to ensure
atomicity. Never create new session_scope() within this function.

Args:
    [parameter descriptions]
    session: Optional session for transactional composition

Returns:
    [return value description]

Raises:
    [exceptions that can be raised]
"""
```

3. Include real examples from existing well-documented functions:
   - Copy `consume_fifo` docstring as Pattern C example
   - Copy `record_batch_production` docstring as Pattern C example

**Files**:
- Create: `kitty-specs/091-transaction-boundary-documentation/research/docstring_templates.md`

**Validation**:
- [ ] All three patterns included
- [ ] Real code examples included
- [ ] Templates match func-spec FR-1 exactly

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Missing functions | Cross-check with `grep -r "^def " src/services/` |
| Misclassification | Review function body, not just name |
| Large files | Focus on public functions only (no `_` prefix) |

## Definition of Done Checklist

- [ ] `research/service_inventory.md` exists with complete inventory
- [ ] All functions classified as READ/SINGLE/MULTI
- [ ] Existing documentation identified with line numbers
- [ ] `research/docstring_templates.md` exists with all three patterns
- [ ] Templates match func-spec FR-1 exactly
- [ ] Inventory count: ~100+ functions documented

## Review Guidance

**Reviewers should verify**:
1. No service files missed
2. Classifications are accurate (spot-check 5-10 MULTI functions)
3. Templates match func-spec exactly
4. Existing docs identified correctly

## Activity Log

- 2026-02-03T04:37:19Z – system – lane=planned – Prompt created.
