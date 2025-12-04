---
work_package_id: "WP02"
subtasks:
  - "T005"
  - "T006"
  - "T007"
title: "EventService Shopping List Integration"
phase: "Phase 2 - Service Integration"
lane: "done"
assignee: "claude"
agent: "claude"
shell_pid: "35768"
review_status: "approved"
reviewed_by: "claude"
history:
  - timestamp: "2025-12-04"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP02 - EventService Shopping List Integration

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

**Objective**: Extend `EventService.get_shopping_list()` to include variant recommendations for each ingredient with a shortfall, and calculate total estimated cost.

**Success Criteria**:
- Shopping list items include `variant_status`, `variant_recommendation`, `all_variants` fields
- Total estimated cost calculated correctly across all recommended purchases (SC-004)
- Existing shopping list functionality preserved - no regression (FR-009, SC-006)
- Integration tests pass

**MVP Note**: This work package + WP01 deliver the functional backend. Users can see recommendations once WP03 adds UI.

## Context & Constraints

**Prerequisites**: WP01 must be complete (VariantService recommendation methods exist).

**Key Files**:
- Modify: `src/services/event_service.py`
- Add tests: `src/tests/test_event_service.py`
- Reference: `src/services/variant_service.py` (WP01 output)

**Architecture Constraints**:
- Service layer must NOT import UI components
- Extend existing return structure, don't replace it
- Maintain backward compatibility with existing callers

**Related Documents**:
- [spec.md](../spec.md) - FR-007, FR-009, SC-004, SC-006
- [data-model.md](../data-model.md) - ShoppingListItem extension, ShoppingListSummary
- [research.md](../research.md) - Current get_shopping_list() return structure

## Subtasks & Detailed Guidance

### Subtask T005 - Modify `get_shopping_list()` to call VariantService

**Purpose**: For each shopping list item with a shortfall, enrich with variant recommendations.

**Steps**:
1. Import VariantService at top of `event_service.py`:
```python
from src.services.variant_service import get_variant_recommendation
```

2. Locate `get_shopping_list()` method (should exist from Feature 006).

3. After calculating shortfall for each ingredient, call VariantService:
```python
def get_shopping_list(event_id: int) -> Dict[str, Any]:
    # ... existing logic to calculate needs and shortfalls ...

    items = []
    for ingredient_data in aggregated_ingredients:
        item = {
            'ingredient_id': ingredient_data['ingredient_id'],
            'ingredient_name': ingredient_data['ingredient_name'],
            'ingredient_slug': ingredient_data['ingredient_slug'],  # Need this for variant lookup
            'unit': ingredient_data['unit'],
            'quantity_needed': ingredient_data['quantity_needed'],
            'quantity_on_hand': ingredient_data['quantity_on_hand'],
            'shortfall': ingredient_data['shortfall'],
        }

        # NEW: Add variant recommendations if shortfall > 0
        if item['shortfall'] > 0:
            variant_data = get_variant_recommendation(
                item['ingredient_slug'],
                item['shortfall'],
                item['unit']
            )
            item['variant_status'] = variant_data['variant_status']
            item['variant_recommendation'] = variant_data['variant_recommendation']
            item['all_variants'] = variant_data['all_variants']
        else:
            item['variant_status'] = 'sufficient'
            item['variant_recommendation'] = None
            item['all_variants'] = []

        items.append(item)

    # Calculate total (T006)
    total_estimated_cost = calculate_total_cost(items)

    return {
        'items': items,
        'total_estimated_cost': total_estimated_cost,
        'items_count': len(items),
        'items_with_shortfall': sum(1 for i in items if i['shortfall'] > 0)
    }
```

4. Ensure `ingredient_slug` is available in the aggregation. If not currently included, add it:
```python
# When building ingredient data, include slug
'ingredient_slug': ingredient.slug,
```

**Files**: `src/services/event_service.py`

**Notes**:
- The existing return was likely a list of dicts. Consider wrapping in a dict with `items` key for extensibility.
- If changing return structure breaks existing callers, maintain backward compatibility or update callers.

---

### Subtask T006 - Calculate total_estimated_cost

**Purpose**: Sum the estimated purchase costs for all recommended variants.

**Steps**:
1. Add helper function or inline calculation:
```python
def _calculate_total_estimated_cost(items: List[Dict]) -> Decimal:
    """
    Calculate total estimated cost for shopping list.

    Only includes items with:
    - variant_status = 'preferred' (user has a clear recommendation)
    - variant_recommendation is not None
    - variant_recommendation has valid total_cost

    Items with 'multiple' status are excluded (user hasn't chosen).
    Items with 'none' status are excluded (no variant to price).
    """
    total = Decimal('0.00')
    for item in items:
        if item.get('variant_status') == 'preferred':
            rec = item.get('variant_recommendation')
            if rec and rec.get('total_cost'):
                total += Decimal(str(rec['total_cost']))
    return total
```

2. Call this in `get_shopping_list()`:
```python
total_estimated_cost = _calculate_total_estimated_cost(items)
```

3. Return as part of response:
```python
return {
    'items': items,
    'total_estimated_cost': total_estimated_cost,
    # ... other summary fields
}
```

**Files**: `src/services/event_service.py`

**Notes**:
- SC-004: Total must equal sum of individual recommended purchase costs
- Only sum 'preferred' items - 'multiple' means user hasn't decided
- Handle None/missing values gracefully

---

### Subtask T007 - Integration tests for shopping list

**Purpose**: Verify end-to-end shopping list generation with variant data.

**Steps**:
1. Create or extend `src/tests/test_event_service.py`:

```python
class TestShoppingListWithVariants:

    def test_shopping_list_includes_variant_recommendations(self, db_session):
        """SC-001: 100% of ingredients with variants show recommendations."""
        # Setup:
        # - Event with recipes requiring flour, sugar
        # - Flour has preferred variant
        # - Sugar has multiple variants (none preferred)
        # - Pantry has partial stock

        result = get_shopping_list(event.id)

        # Assert flour item has variant_status='preferred'
        flour_item = next(i for i in result['items'] if 'flour' in i['ingredient_name'].lower())
        assert flour_item['variant_status'] == 'preferred'
        assert flour_item['variant_recommendation'] is not None
        assert flour_item['variant_recommendation']['brand'] is not None

        # Assert sugar item has variant_status='multiple'
        sugar_item = next(i for i in result['items'] if 'sugar' in i['ingredient_name'].lower())
        assert sugar_item['variant_status'] == 'multiple'
        assert len(sugar_item['all_variants']) > 0

    def test_shopping_list_no_variants_configured(self, db_session):
        """FR-003: Handle ingredient without variants."""
        # Setup: ingredient with no variants

        result = get_shopping_list(event.id)

        # Assert item has variant_status='none'
        item = next(i for i in result['items'] if i['ingredient_slug'] == 'no-variant-ingredient')
        assert item['variant_status'] == 'none'
        assert item['variant_recommendation'] is None

    def test_total_estimated_cost_calculation(self, db_session):
        """SC-004: Total equals sum of recommended purchase costs."""
        # Setup:
        # - Event with 3 ingredients
        # - 2 have preferred variants (flour=$18, butter=$8)
        # - 1 has multiple variants (sugar - excluded from total)

        result = get_shopping_list(event.id)

        # Assert total = $18 + $8 = $26
        assert result['total_estimated_cost'] == Decimal('26.00')

    def test_existing_shopping_list_fields_preserved(self, db_session):
        """FR-009: Existing functionality preserved."""
        result = get_shopping_list(event.id)

        # Assert original fields still present
        for item in result['items']:
            assert 'ingredient_id' in item
            assert 'ingredient_name' in item
            assert 'unit' in item
            assert 'quantity_needed' in item
            assert 'quantity_on_hand' in item
            assert 'shortfall' in item

    def test_sufficient_stock_no_recommendation(self, db_session):
        """Edge case: No shortfall means no recommendation needed."""
        # Setup: ingredient where on_hand >= needed

        result = get_shopping_list(event.id)

        item = next(i for i in result['items'] if i['shortfall'] <= 0)
        assert item['variant_status'] == 'sufficient'
```

**Files**: `src/tests/test_event_service.py`

**Parallel**: Yes - can be developed alongside T005-T006.

---

## Test Strategy

**Required Tests**:
- `test_shopping_list_includes_variant_recommendations`
- `test_shopping_list_no_variants_configured`
- `test_total_estimated_cost_calculation`
- `test_existing_shopping_list_fields_preserved`
- `test_sufficient_stock_no_recommendation`

**Run Command**:
```bash
pytest src/tests/test_event_service.py -v -k "shopping"
```

**Fixtures Needed**:
- Event with packages containing FinishedGoods with recipes
- Ingredients with various variant configurations
- PantryItems with partial stock
- Purchases for cost data

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Breaking existing callers | Check for existing tests; update UI callers if return structure changes |
| Performance with many ingredients | N variant lookups acceptable for ~100 ingredients |
| Missing ingredient_slug | Ensure slug is populated in aggregation step |

---

## Definition of Done Checklist

- [ ] `get_shopping_list()` returns variant data for each item
- [ ] Total estimated cost calculated correctly
- [ ] Existing shopping list fields preserved (FR-009)
- [ ] All 5 integration tests pass
- [ ] Existing Feature 006 tests still pass (SC-006)
- [ ] Code passes black formatting
- [ ] Code passes flake8 linting

---

## Review Guidance

**Key Acceptance Checkpoints**:
1. Verify return structure matches data-model.md ShoppingListItem
2. Verify total only includes 'preferred' items, not 'multiple'
3. Verify existing callers (UI) still work or are updated
4. Run existing shopping list tests from Feature 006

---

## Activity Log

- 2025-12-04 - system - lane=planned - Prompt created via /spec-kitty.tasks.
- 2025-12-04T06:49:25Z – claude – shell_pid=35043 – lane=doing – Started implementation of EventService shopping list integration
- 2025-12-04T06:52:24Z – claude – shell_pid=35768 – lane=for_review – Implementation complete: T005-T007 done, 38 tests passing
- 2025-12-04T06:55:00Z – claude – shell_pid=36243 – lane=done – Approved: All tests pass (5 new + 18 Feature 006), no regressions. Total estimated cost and variant fields implemented.
- 2025-12-04T06:56:57Z – claude – shell_pid=35768 – lane=done – Approved: No regressions, total_estimated_cost implemented
