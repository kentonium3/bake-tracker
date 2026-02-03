---
work_package_id: WP03
title: Core CRUD Services - Product & Supplier
lane: "doing"
dependencies: [WP01]
base_branch: 091-transaction-boundary-documentation-WP01
base_commit: ea54478c184557f13c16ab46b637a8903d9343c6
created_at: '2026-02-03T05:13:56.229494+00:00'
subtasks:
- T008
- T009
- T010
phase: Phase 2 - Documentation
assignee: ''
agent: "codex-wp03"
shell_pid: "44227"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-02-03T04:37:19Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP03 – Core CRUD Services - Product & Supplier

## Objectives & Success Criteria

**Goal**: Add transaction boundary documentation to product and supplier service files.

**Success Criteria**:
- [ ] All public functions in `product_service.py` have "Transaction boundary:" section
- [ ] All public functions in `product_catalog_service.py` have "Transaction boundary:" section
- [ ] All public functions in `supplier_service.py` have "Transaction boundary:" section

**Implementation Command**:
```bash
spec-kitty implement WP03 --base WP01
```

**Parallel-Safe**: Yes - assign to Codex

## Context & Constraints

**References**:
- Templates: `kitty-specs/091-transaction-boundary-documentation/research/docstring_templates.md`
- Inventory: `kitty-specs/091-transaction-boundary-documentation/research/service_inventory.md`

**Key Constraints**:
- Do NOT change function logic - documentation only
- product_service.py has 7 MULTI functions - document steps carefully

## Subtasks & Detailed Guidance

### Subtask T008 – Document product_service.py (~16 functions)

**Purpose**: Add transaction boundary documentation to all public functions.

**Files**:
- Edit: `src/services/product_service.py`

**Functions to document**:

| Function | Type | Template | Notes |
|----------|------|----------|-------|
| `create_product` | MULTI | Pattern C | Validates ingredient via get_ingredient |
| `create_provisional_product` | MULTI | Pattern C | With session parameter, calls validation |
| `get_product` | READ | Pattern A | |
| `get_products_for_ingredient` | READ | Pattern A | |
| `set_preferred_product` | MULTI | Pattern C | Updates all products, then one specifically |
| `update_product` | SINGLE | Pattern B | |
| `delete_product` | MULTI | Pattern C | Checks dependencies first |
| `check_product_dependencies` | READ | Pattern A | |
| `search_products_by_upc` | READ | Pattern A | |
| `get_preferred_product` | READ | Pattern A | |
| `get_product_recommendation` | MULTI | Pattern C | Calls multiple services |

**Example for MULTI function (create_product)**:
```python
def create_product(product_data: dict, session: Optional[Session] = None) -> Product:
    """
    Create a new product linked to an ingredient.

    Transaction boundary: Multi-step operation (atomic).
    Steps executed atomically:
    1. Validate ingredient exists via get_ingredient()
    2. Verify ingredient is a leaf node (not a category)
    3. Generate unique product slug
    4. Create Product record

    CRITICAL: All nested service calls receive session parameter to ensure
    atomicity. Never create new session_scope() within this function.

    Args:
        product_data: Dictionary containing product details
        session: Optional session for transactional composition

    Returns:
        Created Product model instance

    Raises:
        IngredientNotFoundBySlug: If linked ingredient doesn't exist
        ValidationError: If ingredient is not a leaf node
    """
```

**Validation**:
- [ ] All functions documented
- [ ] MULTI functions list their steps

---

### Subtask T009 – Document product_catalog_service.py

**Purpose**: Add transaction boundary documentation to all public functions.

**Files**:
- Edit: `src/services/product_catalog_service.py`

**Common functions to document**:
- `get_catalog_*` functions - READ (Pattern A)
- `search_*` functions - READ (Pattern A)
- Any `create_*`, `update_*` - check if SINGLE or MULTI

**Validation**:
- [ ] All public functions documented

---

### Subtask T010 – Document supplier_service.py

**Purpose**: Add transaction boundary documentation to all public functions.

**Files**:
- Edit: `src/services/supplier_service.py`

**Typical functions**:
| Function | Type | Template |
|----------|------|----------|
| `create_supplier` | SINGLE | Pattern B |
| `get_supplier` | READ | Pattern A |
| `get_all_suppliers` | READ | Pattern A |
| `update_supplier` | SINGLE | Pattern B |
| `delete_supplier` | MULTI | Pattern C (checks dependencies) |
| `search_suppliers` | READ | Pattern A |

**Validation**:
- [ ] All public functions documented

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| MULTI classification errors | Verify by checking for service calls in body |

## Definition of Done Checklist

- [ ] product_service.py: All public functions documented
- [ ] product_catalog_service.py: All public functions documented
- [ ] supplier_service.py: All public functions documented
- [ ] MULTI functions have steps listed
- [ ] Tests still pass: `pytest src/tests -v -k "product or supplier"`

## Review Guidance

**Reviewers should verify**:
1. MULTI functions actually call other services
2. Steps in Pattern C match actual implementation
3. Template phrasing consistent

## Activity Log

- 2026-02-03T04:37:19Z – system – lane=planned – Prompt created.
- 2026-02-03T05:22:17Z – unknown – shell_pid=27597 – lane=for_review – Ready for review: Added transaction boundary docs to product_service.py (11), product_catalog_service.py (30), supplier_service.py (22). Tests pass.
- 2026-02-03T06:20:37Z – codex-wp03 – shell_pid=44227 – lane=doing – Started review via workflow command
