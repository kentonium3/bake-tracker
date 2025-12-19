---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
  - "T003"
  - "T004"
title: "Model Layer - Add product_name Column"
phase: "Phase 1 - Model Changes"
lane: "doing"
assignee: ""
agent: "claude"
shell_pid: "27965"
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-19T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 - Model Layer - Add product_name Column

## Review Feedback

> **Populated by `/spec-kitty.review`** - Reviewers add detailed feedback here when work needs changes.

*[This section is empty initially.]*

---

## Objectives & Success Criteria

**Objective**: Add `product_name` column to the Product model with proper constraints and display integration.

**Success Criteria**:
- [ ] Product model has `product_name` column (VARCHAR 200, nullable)
- [ ] UniqueConstraint includes all 5 fields: `(ingredient_id, brand, product_name, package_size, package_unit)`
- [ ] `display_name` property returns "Brand ProductName Size Type" format
- [ ] Empty strings are normalized to NULL on save
- [ ] Existing code continues to work (no breaking changes)

## Context & Constraints

**Spec Reference**: `kitty-specs/023-product-name-differentiation/spec.md`
**Plan Reference**: `kitty-specs/023-product-name-differentiation/plan.md`
**Data Model Reference**: `kitty-specs/023-product-name-differentiation/data-model.md`
**Constitution**: `.kittify/memory/constitution.md` - See Section VI (Schema Change Strategy)

**Key Constraints**:
- Column must be nullable to preserve existing products
- Follow existing field patterns (see `brand` column definition)
- SQLite NULL behavior is acceptable (NULLs are distinct in unique constraints)
- Display format confirmed by user: "Brand ProductName Size" (e.g., "Lindt 70% Cacao 3.5 oz")

## Subtasks & Detailed Guidance

### Subtask T001 - Add product_name Column

**Purpose**: Extend Product table with a new column to store variant names.

**Steps**:
1. Open `src/models/product.py`
2. Locate the `brand` column definition (line ~53)
3. Add new column definition immediately after `brand`:

```python
# Variant name (e.g., "70% Cacao", "Extra Virgin", "Original Recipe")
product_name = Column(String(200), nullable=True, index=False)
```

4. Update the docstring at the top of the class to include `product_name` in the attribute list

**Files**: `src/models/product.py`
**Parallel?**: No (must complete before T002-T004)

**Notes**:
- Position after `brand`, before `package_size` for logical grouping
- No index needed (searches will use full constraint)
- Match VARCHAR(200) from `brand` field

### Subtask T002 - Add UniqueConstraint

**Purpose**: Prevent duplicate products with identical identifying fields.

**Steps**:
1. Add import for `UniqueConstraint` if not present:
```python
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, Boolean, ForeignKey, Index, UniqueConstraint
```

2. Locate `__table_args__` (line ~103)
3. Add UniqueConstraint to the tuple:

```python
__table_args__ = (
    Index("idx_product_ingredient", "ingredient_id"),
    Index("idx_product_brand", "brand"),
    Index("idx_product_upc", "upc_code"),
    UniqueConstraint(
        "ingredient_id", "brand", "product_name", "package_size", "package_unit",
        name="uq_product_variant"
    ),
)
```

**Files**: `src/models/product.py`
**Parallel?**: No (depends on T001)

**Notes**:
- Reference pattern: `src/models/recipe.py:375`
- SQLite treats NULL as distinct, so multiple products with NULL product_name are allowed
- Constraint name follows convention: `uq_<table>_<purpose>`

### Subtask T003 - Update display_name Property

**Purpose**: Include product_name in the display string for UI and logs.

**Steps**:
1. Locate `display_name` property (line ~115)
2. Update to insert `product_name` after `brand`:

```python
@property
def display_name(self) -> str:
    """
    Get display name for this product.

    Returns:
        Formatted display name (e.g., "Lindt 70% Cacao 3.5 oz bar")
    """
    parts = []
    if self.brand:
        parts.append(self.brand)
    if self.product_name:
        parts.append(self.product_name)
    if self.package_size:
        parts.append(self.package_size)
    if self.package_type:
        parts.append(self.package_type)

    if not parts:
        return f"{self.ingredient.display_name} (generic)"

    return " ".join(parts)
```

**Files**: `src/models/product.py`
**Parallel?**: No (depends on T001)

**Notes**:
- Order matters: Brand, ProductName, Size, Type
- User clarification confirmed this format on 2025-12-19
- Update docstring to reflect new format

### Subtask T004 - Add Empty String Normalization

**Purpose**: Ensure empty strings are stored as NULL for constraint consistency.

**Steps**:
1. Add a SQLAlchemy event listener or validator to normalize empty strings
2. Option A - Use `@validates` decorator:

```python
from sqlalchemy.orm import validates

@validates('product_name')
def _normalize_product_name(self, key, value):
    """Normalize empty strings to None for consistency."""
    if value == '':
        return None
    return value
```

3. Add this method after the relationships section

**Files**: `src/models/product.py`
**Parallel?**: No (depends on T001)

**Notes**:
- This ensures "" and NULL are treated identically
- Important for unique constraint behavior
- Also helps with UI where empty text entry becomes ""

## Risks & Mitigations

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Constraint conflicts with existing data | Low | All existing products have NULL product_name; SQLite allows multiple NULLs |
| Breaking existing queries | Low | Column is nullable; no existing code references it |
| Import statement conflicts | Low | Check if UniqueConstraint already imported |

## Definition of Done Checklist

- [ ] T001: `product_name` column added to Product model
- [ ] T002: UniqueConstraint added with 5-field tuple
- [ ] T003: `display_name` property updated with correct format
- [ ] T004: Empty string normalization validator added
- [ ] All imports present and correct
- [ ] Docstrings updated to reflect changes
- [ ] No syntax errors (file parses correctly)

## Review Guidance

**Reviewers should verify**:
1. Column position is after `brand`, before `package_size`
2. UniqueConstraint includes exactly these fields in order: `ingredient_id`, `brand`, `product_name`, `package_size`, `package_unit`
3. `display_name` output format matches "Brand ProductName Size Type"
4. Validator correctly converts "" to None
5. No breaking changes to existing public API

## Activity Log

- 2025-12-19T00:00:00Z - system - lane=planned - Prompt created via /spec-kitty.tasks
- 2025-12-19T16:45:01Z – claude – shell_pid=27965 – lane=doing – Started implementation
