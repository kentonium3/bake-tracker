---
work_package_id: WP07
title: Material & Finished Good Services
lane: "doing"
dependencies: [WP01]
base_branch: 091-transaction-boundary-documentation-WP01
base_commit: ea54478c184557f13c16ab46b637a8903d9343c6
created_at: '2026-02-03T05:42:44.849404+00:00'
subtasks:
- T024
- T025
- T026
- T027
- T028
phase: Phase 2 - Documentation
assignee: ''
agent: "codex-wp07"
shell_pid: "44435"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-02-03T04:37:19Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP07 – Material & Finished Good Services

## Objectives & Success Criteria

**Goal**: Add transaction boundary documentation to material and finished good service files.

**Success Criteria**:
- [ ] All public functions/methods in material services have "Transaction boundary:" section
- [ ] All public functions/methods in finished good services have "Transaction boundary:" section

**Implementation Command**:
```bash
spec-kitty implement WP07 --base WP01
```

**Parallel-Safe**: Yes - assign to Gemini

## Context & Constraints

**References**:
- Templates: `kitty-specs/091-transaction-boundary-documentation/research/docstring_templates.md`

**Key Constraints**:
- `finished_good_service.py` uses CLASS-BASED pattern (static methods)
- Material services support the new material abstraction layer

## Subtasks & Detailed Guidance

### Subtask T024 – Document finished_good_service.py

**Purpose**: Add transaction boundary documentation to all public methods.

**Files**:
- Edit: `src/services/finished_good_service.py`

**Note**: This file uses a class-based service pattern with static methods.

**Methods to document**:

| Method | Type | Template |
|--------|------|----------|
| `get_finished_good_by_id` | READ | Pattern A |
| `get_finished_good_by_slug` | READ | Pattern A |
| `get_all_finished_goods` | READ | Pattern A |
| `create_finished_good` | MULTI | Pattern C |
| `update_finished_good` | MULTI | Pattern C |
| `delete_finished_good` | MULTI | Pattern C |
| `add_component` | MULTI | Pattern C |
| `remove_component` | MULTI | Pattern C |

**Example for class-based service**:
```python
class FinishedGoodService:
    @staticmethod
    def create_finished_good(data: dict, session: Optional[Session] = None) -> FinishedGood:
        """
        Create a new finished good with its components.

        Transaction boundary: ALL operations in single session (atomic).
        Atomicity guarantee: Either ALL steps succeed OR entire operation rolls back.
        Steps executed atomically:
        1. Validate finished good data
        2. Create FinishedGood record
        3. Create FinishedGoodComponent records for each ingredient
        4. Calculate aggregate properties (cost, weight)

        CRITICAL: All nested service calls receive session parameter to ensure
        atomicity. Never create new session_scope() within this method.

        Args:
            data: Dictionary containing finished good details and components
            session: Optional session for transactional composition

        Returns:
            Created FinishedGood instance with components loaded

        Raises:
            ValidationError: If data is invalid
            IngredientNotFoundBySlug: If component ingredient doesn't exist
        """
```

**Validation**:
- [ ] All public methods documented
- [ ] Class-based pattern handled correctly

---

### Subtask T025 – Document material_consumption_service.py

**Purpose**: Add transaction boundary documentation to material consumption operations.

**Files**:
- Edit: `src/services/material_consumption_service.py`

**Typical functions**:

| Function | Type | Template |
|----------|------|----------|
| `record_material_consumption` | MULTI | Pattern C |
| `get_consumption_history` | READ | Pattern A |
| `validate_material_availability` | READ | Pattern A |
| `calculate_consumption` | READ | Pattern A |

**For consumption operations (similar to FIFO)**:
```python
def record_material_consumption(
    material_slug: str,
    quantity: float,
    session: Optional[Session] = None
):
    """
    Record consumption of material using FIFO method.

    Transaction boundary: ALL operations in single session (atomic).
    Atomicity guarantee: Either ALL steps succeed OR entire operation rolls back.
    Steps executed atomically:
    1. Validate material exists and quantity available
    2. Get inventory items ordered by purchase date (FIFO)
    3. Consume from oldest items first
    4. Create MaterialConsumption records
    5. Update or delete inventory items as depleted

    CRITICAL: All nested service calls receive session parameter to ensure
    atomicity. Never create new session_scope() within this function.
    """
```

**Validation**:
- [ ] All public functions documented

---

### Subtask T026 – Document material_purchase_service.py

**Purpose**: Add transaction boundary documentation to material purchase operations.

**Files**:
- Edit: `src/services/material_purchase_service.py`

**Typical functions**:

| Function | Type | Template |
|----------|------|----------|
| `record_material_purchase` | MULTI | Pattern C |
| `get_purchase_history` | READ | Pattern A |
| `convert_to_base_units` | READ | Pattern A (utility) |
| `calculate_weighted_average` | READ | Pattern A |

**Validation**:
- [ ] All public functions documented

---

### Subtask T027 – Document material_inventory_service.py

**Purpose**: Add transaction boundary documentation to material inventory operations.

**Files**:
- Edit: `src/services/material_inventory_service.py`

**Typical functions**:

| Function | Type | Template |
|----------|------|----------|
| `get_material_inventory` | READ | Pattern A |
| `add_to_inventory` | MULTI | Pattern C |
| `adjust_inventory` | MULTI | Pattern C |
| `get_inventory_value` | READ | Pattern A |

**Validation**:
- [ ] All public functions documented

---

### Subtask T028 – Document finished_goods_inventory_service.py

**Purpose**: Add transaction boundary documentation to finished goods inventory operations.

**Files**:
- Edit: `src/services/finished_goods_inventory_service.py`

**Typical functions**:

| Function | Type | Template |
|----------|------|----------|
| `get_finished_goods_inventory` | READ | Pattern A |
| `add_finished_good_to_inventory` | MULTI | Pattern C |
| `consume_finished_good` | MULTI | Pattern C |
| `get_inventory_summary` | READ | Pattern A |

**Validation**:
- [ ] All public functions documented

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Class-based service pattern | Document methods same as functions |
| New material abstraction | Follow same patterns as ingredient services |

## Definition of Done Checklist

- [ ] finished_good_service.py: All public methods documented
- [ ] material_consumption_service.py: All public functions documented
- [ ] material_purchase_service.py: All public functions documented
- [ ] material_inventory_service.py: All public functions documented
- [ ] finished_goods_inventory_service.py: All public functions documented
- [ ] Tests still pass: `pytest src/tests -v -k "material or finished"`

## Review Guidance

**Reviewers should verify**:
1. Class-based methods documented correctly
2. FIFO consumption documented like consume_fifo
3. No functional changes

## Activity Log

- 2026-02-03T04:37:19Z – system – lane=planned – Prompt created.
- 2026-02-03T05:56:04Z – unknown – shell_pid=34904 – lane=for_review – Ready for review: Transaction boundary documentation added to finished_good_service.py, finished_unit_service.py, material_consumption_service.py, material_purchase_service.py, material_inventory_service.py, and finished_goods_inventory_service.py. All 780 related tests pass.
- 2026-02-03T06:20:42Z – codex-wp07 – shell_pid=44435 – lane=doing – Started review via workflow command
