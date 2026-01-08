---
work_package_id: WP02
title: Category Defaults Utility
lane: done
history:
- timestamp: '2025-12-24T23:15:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
agent: claude
assignee: claude
phase: Phase 0 - Foundation
review_status: ''
reviewed_by: ''
shell_pid: '33920'
subtasks:
- T007
- T008
- T009
- T010
- T011
---

# Work Package Prompt: WP02 – Category Defaults Utility

## Objectives & Success Criteria

**Goal**: Implement category-to-unit default mapping for smart pre-filling in inline product creation.

**Success Criteria**:
- [ ] `get_default_unit_for_category('Baking')` returns `'lb'`
- [ ] `get_default_unit_for_category('Chocolate')` returns `'oz'`
- [ ] Unknown categories return `'lb'` as fallback
- [ ] Ingredient wrapper function works correctly
- [ ] All unit tests pass

## Context & Constraints

**References**:
- Plan: `kitty-specs/029-streamlined-inventory-entry/plan.md` (PD-004: Category-to-Unit Defaults)
- Research: `kitty-specs/029-streamlined-inventory-entry/research.md` (RQ-006)
- Design: `docs/design/F029_streamlined_inventory_entry.md` (Smart Defaults section)

**Constraints**:
- Mapping must match actual category names in database
- All defaults must be editable by user (this is just pre-fill)

## Subtasks & Detailed Guidance

### Subtask T007 – Create category_defaults.py

**Purpose**: Establish the module for category-to-unit mapping.

**Steps**:
1. Create `src/utils/category_defaults.py`
2. Add module docstring explaining purpose

**Files**: `src/utils/category_defaults.py` (NEW)

### Subtask T008 – Define mapping dictionary

**Purpose**: Centralize category-to-unit defaults.

**Steps**:
1. Define `CATEGORY_DEFAULT_UNITS` dictionary
2. Map all known categories to appropriate units

**Code**:
```python
CATEGORY_DEFAULT_UNITS: Dict[str, str] = {
    'Baking': 'lb',
    'Chocolate': 'oz',
    'Dairy': 'lb',
    'Spices': 'oz',
    'Liquids': 'fl oz',
    'Nuts': 'lb',
    'Fruits': 'lb',
    'Sweeteners': 'lb',
    'Leavening': 'oz',
    'Oils': 'fl oz',
    'Grains': 'lb',
}
```

### Subtask T009 – Implement get_default_unit_for_category()

**Purpose**: Provide category lookup with fallback.

**Steps**:
1. Implement function with category parameter
2. Use dict.get() with 'lb' fallback
3. Add type hints and docstring

**Code**:
```python
def get_default_unit_for_category(category: str) -> str:
    """
    Get default package unit for an ingredient category.

    Args:
        category: Ingredient category name

    Returns:
        Default unit string (e.g., 'lb', 'oz', 'fl oz')
        Returns 'lb' as fallback if category not found
    """
    return CATEGORY_DEFAULT_UNITS.get(category, 'lb')
```

### Subtask T010 – Implement ingredient wrapper

**Purpose**: Convenience function for use with Ingredient model.

**Steps**:
1. Import Ingredient model (or use duck typing)
2. Extract category from ingredient and delegate

**Code**:
```python
def get_default_unit_for_ingredient(ingredient) -> str:
    """
    Get default package unit for a specific ingredient.

    Args:
        ingredient: Ingredient model instance with .category attribute

    Returns:
        Default unit string
    """
    return get_default_unit_for_category(ingredient.category)
```

### Subtask T011 – Create unit tests [P]

**Purpose**: Verify mapping correctness.

**Steps**:
1. Create `src/tests/utils/test_category_defaults.py`
2. Test known categories return expected units
3. Test unknown category returns fallback
4. Test ingredient wrapper

**Test Cases**:
```python
import pytest
from src.utils.category_defaults import (
    get_default_unit_for_category,
    get_default_unit_for_ingredient,
    CATEGORY_DEFAULT_UNITS
)

def test_baking_defaults_to_lb():
    assert get_default_unit_for_category('Baking') == 'lb'

def test_chocolate_defaults_to_oz():
    assert get_default_unit_for_category('Chocolate') == 'oz'

def test_spices_defaults_to_oz():
    assert get_default_unit_for_category('Spices') == 'oz'

def test_liquids_defaults_to_fl_oz():
    assert get_default_unit_for_category('Liquids') == 'fl oz'

def test_unknown_category_falls_back_to_lb():
    assert get_default_unit_for_category('UnknownCategory') == 'lb'
    assert get_default_unit_for_category('') == 'lb'

def test_all_mapped_categories_have_values():
    """Verify all mapped categories return non-empty strings."""
    for category, unit in CATEGORY_DEFAULT_UNITS.items():
        assert unit, f"Category {category} has empty unit"
        assert isinstance(unit, str)

class MockIngredient:
    def __init__(self, category):
        self.category = category

def test_ingredient_wrapper_baking():
    ingredient = MockIngredient('Baking')
    assert get_default_unit_for_ingredient(ingredient) == 'lb'

def test_ingredient_wrapper_unknown():
    ingredient = MockIngredient('Unknown')
    assert get_default_unit_for_ingredient(ingredient) == 'lb'
```

**Files**: `src/tests/utils/test_category_defaults.py` (NEW)

**Parallel?**: Yes, can be written alongside implementation

## Test Strategy

Run tests with:
```bash
pytest src/tests/utils/test_category_defaults.py -v
```

All test cases must pass.

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Category names don't match DB | Verify against actual ingredient categories |
| Missing categories | Fallback to 'lb' handles gracefully |

## Definition of Done Checklist

- [ ] `src/utils/category_defaults.py` exists
- [ ] All 11 categories mapped
- [ ] Fallback to 'lb' works
- [ ] Ingredient wrapper works
- [ ] All unit tests pass
- [ ] No linting errors

## Review Guidance

**Reviewers should verify**:
1. Category names match database (query `SELECT DISTINCT category FROM ingredients`)
2. Unit values are reasonable for each category
3. Fallback works for edge cases

## Activity Log

- 2025-12-24T23:15:00Z – system – lane=planned – Prompt created.
- 2025-12-25T04:56:17Z – claude – shell_pid=33920 – lane=doing – Started implementation
- 2025-12-25T04:57:48Z – claude – shell_pid=33920 – lane=for_review – Ready for review - 21 tests passing
- 2025-12-25T06:39:49Z – claude – shell_pid=33920 – lane=done – Moved to done
