---
work_package_id: "WP02"
subtasks:
  - "T005"
  - "T006"
title: "Service Layer - product_service Updates"
phase: "Phase 2 - Service Changes"
lane: "done"
assignee: "claude"
agent: "claude-reviewer"
shell_pid: "30652"
review_status: "approved without changes"
reviewed_by: "claude-reviewer"
history:
  - timestamp: "2025-12-19T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP02 - Service Layer - product_service Updates

## Review Feedback

> **Populated by `/spec-kitty.review`** - Reviewers add detailed feedback here when work needs changes.

*[This section is empty initially.]*

---

## Objectives & Success Criteria

**Objective**: Update product_service create and update methods to accept and persist product_name parameter.

**Success Criteria**:
- [ ] `create_product()` accepts optional `product_name` parameter
- [ ] `update_product()` accepts optional `product_name` parameter
- [ ] Empty strings are normalized to None before passing to model
- [ ] Existing callers continue to work without changes

## Context & Constraints

**Spec Reference**: `kitty-specs/023-product-name-differentiation/spec.md` - FR-001, FR-009
**Plan Reference**: `kitty-specs/023-product-name-differentiation/plan.md`
**CLAUDE.md**: See "Session Management (CRITICAL)" section for service function patterns

**Key Constraints**:
- Follow existing service patterns for optional parameters
- Maintain backward compatibility (parameter must have default value)
- Respect session management guidelines - pass session when calling from other services

**Dependencies**: WP01 must be complete (Product model must have product_name column)

## Subtasks & Detailed Guidance

### Subtask T005 - Update create_product()

**Purpose**: Allow new products to be created with a product_name.

**Steps**:
1. Open `src/services/product_service.py`
2. Locate `create_product()` function
3. Add `product_name` parameter to function signature:

```python
def create_product(
    ingredient_id: int,
    package_unit: str,
    package_unit_quantity: float,
    brand: Optional[str] = None,
    product_name: Optional[str] = None,  # NEW
    package_size: Optional[str] = None,
    package_type: Optional[str] = None,
    # ... other existing parameters
    session=None,
) -> Product:
```

4. Add normalization before creating Product:

```python
# Normalize empty strings to None
if product_name == '':
    product_name = None
```

5. Include `product_name` when creating the Product instance:

```python
product = Product(
    ingredient_id=ingredient_id,
    brand=brand,
    product_name=product_name,  # NEW
    package_size=package_size,
    # ... rest of fields
)
```

**Files**: `src/services/product_service.py`
**Parallel?**: Yes [P] - can be done alongside T006

**Notes**:
- Position parameter after `brand` to match model field order
- Keep default as None for backward compatibility
- Model also has validator, but service-level normalization is defense in depth

### Subtask T006 - Update update_product()

**Purpose**: Allow existing products to have their product_name modified.

**Steps**:
1. Locate `update_product()` function in `src/services/product_service.py`
2. Add `product_name` to function signature with appropriate default
3. Two patterns are possible depending on current implementation:

**Option A** - If using `**kwargs` pattern:
```python
def update_product(product_id: int, session=None, **kwargs) -> Product:
    # product_name comes through kwargs automatically
```
In this case, just ensure the update logic handles it.

**Option B** - If using explicit parameters:
```python
def update_product(
    product_id: int,
    brand: Optional[str] = None,
    product_name: Optional[str] = None,  # NEW - use sentinel for "not provided"
    package_size: Optional[str] = None,
    # ... other parameters
    session=None,
) -> Product:
```

4. Add normalization and update logic:

```python
# Normalize and update product_name if provided
if product_name is not None:
    product.product_name = product_name if product_name != '' else None
```

**Files**: `src/services/product_service.py`
**Parallel?**: Yes [P] - can be done alongside T005

**Notes**:
- Check existing update pattern in the file before implementing
- Handle the difference between "not provided" (don't change) vs "provided as None" (clear value)
- Empty string should normalize to None

## Risks & Mitigations

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Breaking existing callers | Low | Parameter has default value None |
| Session detachment issues | Medium | Follow CLAUDE.md session management patterns |
| Type hint issues | Low | Use Optional[str] consistently |

## Definition of Done Checklist

- [ ] T005: `create_product()` accepts `product_name` parameter
- [ ] T006: `update_product()` accepts `product_name` parameter
- [ ] Empty string normalization implemented in both functions
- [ ] Type hints added for new parameter
- [ ] Docstrings updated to document new parameter
- [ ] Existing callers unaffected (verified by existing tests passing)

## Review Guidance

**Reviewers should verify**:
1. Parameter position is consistent (after brand)
2. Default value is None for backward compatibility
3. Empty string normalization is present
4. Session parameter preserved per CLAUDE.md guidelines
5. No changes to function return types

## Activity Log

- 2025-12-19T00:00:00Z - system - lane=planned - Prompt created via /spec-kitty.tasks
- 2025-12-19T16:48:13Z – claude – shell_pid=28455 – lane=doing – Started implementation
- 2025-12-19T16:49:29Z – claude – shell_pid=28930 – lane=for_review – Service updates complete - ready for review
- 2025-12-19T17:01:05Z – claude-reviewer – shell_pid=30652 – lane=done – Code review complete: All criteria met - approved without changes
