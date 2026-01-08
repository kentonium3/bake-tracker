---
work_package_id: WP05
title: Dropdown Builder Functions
lane: done
history:
- timestamp: '2025-12-24T23:15:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
agent: claude
assignee: claude
phase: Phase 1 - Widgets
review_status: ''
reviewed_by: ''
shell_pid: '33920'
subtasks:
- T027
- T028
- T029
- T030
- T031
- T032
- T033
---

# Work Package Prompt: WP05 – Dropdown Builder Functions

## Objectives & Success Criteria

**Goal**: Create recency-aware dropdown builders that integrate recency markers and sorting.

**Success Criteria**:
- [ ] `build_product_dropdown_values()` returns list with starred recent items first
- [ ] `build_ingredient_dropdown_values()` returns list with starred recent items first
- [ ] Separator line between recent and non-recent sections
- [ ] "[+ Create New Product]" option at bottom of product list
- [ ] Non-recent items sorted alphabetically
- [ ] All tests pass

## Context & Constraints

**References**:
- Plan: `kitty-specs/029-streamlined-inventory-entry/plan.md`
- Research: `kitty-specs/029-streamlined-inventory-entry/research.md`
- Design: `docs/design/F029_streamlined_inventory_entry.md` (Dropdown Builder section)

**Constraints**:
- Depends on WP03 recency query methods
- Uses Unicode star (⭐) and line separator (─)
- Separator must be handled specially in dialog (ignored on selection)

## Subtasks & Detailed Guidance

### Subtask T027 – Create dropdown_builders.py

**Purpose**: Establish module for dropdown building functions.

**Steps**:
1. Create `src/ui/widgets/dropdown_builders.py`
2. Add imports for models and services

**Files**: `src/ui/widgets/dropdown_builders.py` (NEW)

### Subtask T028 – Implement product dropdown builder

**Purpose**: Build product dropdown with recency sorting.

**Steps**:
1. Implement `build_product_dropdown_values(ingredient_id, session)` function
2. Query all products for ingredient
3. Get recent product IDs from recency service
4. Build sorted list

**Code**:
```python
from typing import List
from sqlalchemy.orm import Session
from src.models import Product
from src.services.inventory_item_service import get_recent_products

SEPARATOR = "─────────────────────────────"
CREATE_NEW_OPTION = "[+ Create New Product]"

def build_product_dropdown_values(
    ingredient_id: int,
    session: Session
) -> List[str]:
    """
    Build product dropdown values with recency markers and sorting.

    Args:
        ingredient_id: Ingredient to filter products for
        session: Database session

    Returns:
        List of dropdown values in display order:
        1. Recent products (starred)
        2. Separator
        3. Non-recent products (alphabetical)
        4. Separator
        5. Create new option
    """
    # Get all products for ingredient
    products = session.query(Product).filter_by(
        ingredient_id=ingredient_id,
        is_hidden=False
    ).order_by(Product.name).all()

    if not products:
        return [CREATE_NEW_OPTION]

    # Get recent product IDs
    recent_ids = set(get_recent_products(ingredient_id, session=session))

    # Separate recent vs non-recent
    recent_products = []
    other_products = []

    for product in products:
        if product.id in recent_ids:
            recent_products.append(f"⭐ {product.name}")
        else:
            other_products.append(product.name)

    # Build final list
    values = []

    if recent_products:
        values.extend(recent_products)
        if other_products:
            values.append(SEPARATOR)

    values.extend(other_products)

    if values:
        values.append(SEPARATOR)

    values.append(CREATE_NEW_OPTION)

    return values
```

### Subtask T029 – Implement ingredient dropdown builder

**Purpose**: Build ingredient dropdown with recency sorting.

**Steps**:
1. Implement `build_ingredient_dropdown_values(category, session)` function
2. Query all ingredients in category
3. Get recent ingredient IDs
4. Build sorted list (no create option for ingredients)

**Code**:
```python
from src.models import Ingredient
from src.services.inventory_item_service import get_recent_ingredients

def build_ingredient_dropdown_values(
    category: str,
    session: Session
) -> List[str]:
    """
    Build ingredient dropdown values with recency sorting.

    Args:
        category: Category to filter ingredients for
        session: Database session

    Returns:
        List of dropdown values in display order
    """
    # Get all ingredients in category
    ingredients = session.query(Ingredient).filter_by(
        category=category
    ).order_by(Ingredient.display_name).all()

    if not ingredients:
        return []

    # Get recent ingredient IDs
    recent_ids = set(get_recent_ingredients(category, session=session))

    # Separate recent vs non-recent
    recent_ingredients = []
    other_ingredients = []

    for ingredient in ingredients:
        if ingredient.id in recent_ids:
            recent_ingredients.append(f"⭐ {ingredient.display_name}")
        else:
            other_ingredients.append(ingredient.display_name)

    # Build final list
    values = []

    if recent_ingredients:
        values.extend(recent_ingredients)
        if other_ingredients:
            values.append(SEPARATOR)

    values.extend(other_ingredients)

    return values
```

### Subtask T030 – Add star prefix for recent items

**Purpose**: Visual marker for recency.

**Steps**:
1. Use Unicode star: ⭐ (U+2B50)
2. Prefix format: "⭐ Product Name"
3. Dialog code will strip star when extracting actual name

**Notes**:
- Star is prepended with space for readability
- Dialog must handle: `value.replace("⭐ ", "")`

### Subtask T031 – Add separator line

**Purpose**: Visual separation between sections.

**Steps**:
1. Use Unicode box drawing: ─ (U+2500) repeated
2. Separator: "─────────────────────────────"
3. Dialog must ignore separator selection

**Notes**:
- Separator is non-selectable (dialog handles this)
- Provides visual grouping in dropdown

### Subtask T032 – Add create-new option

**Purpose**: Allow inline product creation from dropdown.

**Steps**:
1. Add "[+ Create New Product]" at bottom
2. Dialog detects this selection and triggers inline form
3. Always present in product dropdown (even if products exist)

### Subtask T033 – Create tests [P]

**Purpose**: Verify dropdown building logic.

**Steps**:
1. Create tests in appropriate test file
2. Test with mock recency data
3. Verify ordering and formatting

**Test Cases**:
```python
import pytest
from unittest.mock import patch
from src.ui.widgets.dropdown_builders import (
    build_product_dropdown_values,
    build_ingredient_dropdown_values,
    SEPARATOR,
    CREATE_NEW_OPTION
)

@patch('src.ui.widgets.dropdown_builders.get_recent_products')
def test_product_dropdown_recent_first(mock_recency, session, test_products):
    """Recent products should appear first with star."""
    mock_recency.return_value = [test_products['recent'].id]

    values = build_product_dropdown_values(
        test_products['ingredient'].id,
        session
    )

    # First item should be starred recent product
    assert values[0].startswith("⭐")
    assert test_products['recent'].name in values[0]

@patch('src.ui.widgets.dropdown_builders.get_recent_products')
def test_product_dropdown_separator_present(mock_recency, session, test_products):
    """Separator should appear between recent and non-recent."""
    mock_recency.return_value = [test_products['recent'].id]

    values = build_product_dropdown_values(
        test_products['ingredient'].id,
        session
    )

    assert SEPARATOR in values

@patch('src.ui.widgets.dropdown_builders.get_recent_products')
def test_product_dropdown_create_option_last(mock_recency, session, test_products):
    """Create option should be last."""
    mock_recency.return_value = []

    values = build_product_dropdown_values(
        test_products['ingredient'].id,
        session
    )

    assert values[-1] == CREATE_NEW_OPTION

def test_product_dropdown_empty_ingredient(session):
    """Empty ingredient should show only create option."""
    values = build_product_dropdown_values(999999, session)
    assert values == [CREATE_NEW_OPTION]
```

**Files**: Test file location TBD (widget tests or integration tests)

**Parallel?**: Yes, can be written alongside implementation

## Test Strategy

Run tests with:
```bash
pytest src/tests -v -k "dropdown_builder"
```

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Unicode rendering issues | Test on target platform |
| Separator selection | Handle in dialog code |
| Empty lists | Return appropriate defaults |

## Definition of Done Checklist

- [ ] `build_product_dropdown_values()` implemented
- [ ] `build_ingredient_dropdown_values()` implemented
- [ ] Star prefix works correctly
- [ ] Separator included between sections
- [ ] Create option at bottom of product dropdown
- [ ] All tests pass
- [ ] No linting errors

## Review Guidance

**Reviewers should verify**:
1. Recent items appear first with ⭐
2. Separator appears between sections (when both exist)
3. Alphabetical sort within non-recent section
4. Create option always present for products

## Activity Log

- 2025-12-24T23:15:00Z – system – lane=planned – Prompt created.
- 2025-12-25T05:09:43Z – claude – shell_pid=33920 – lane=doing – Starting implementation
- 2025-12-25T05:13:14Z – claude – shell_pid=33920 – lane=for_review – All 18 tests pass. Builders ready.
- 2025-12-25T06:40:05Z – claude – shell_pid=33920 – lane=done – Moved to done
