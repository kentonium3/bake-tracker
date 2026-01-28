---
work_package_id: WP03
title: Production-Aware Shopping List
lane: "done"
dependencies: [WP01]
base_branch: 079-production-aware-planning-calculations-WP01
base_commit: 2ef43f9ed9781cb38411cbfbb17660c86a9c15e8
created_at: '2026-01-28T06:17:43.364949+00:00'
subtasks:
- T009
- T010
- T011
- T012
phase: Phase 2 - Core Features
assignee: ''
agent: "claude-lead"
shell_pid: "27841"
review_status: "approved"
reviewed_by: "Kent Gale"
history:
- timestamp: '2026-01-28T06:03:15Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP03 – Production-Aware Shopping List

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you understand the feedback, update `review_status: acknowledged`.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if work is returned from review.]*

---

## Implementation Command

```bash
# Depends on WP01 - branch from WP01 worktree
spec-kitty implement WP03 --base WP01
```

---

## Objectives & Success Criteria

**Objective**: Modify the shopping list service to calculate ingredient needs for **remaining production** only when `production_aware=True` (the default).

**Success Criteria**:
- [ ] `get_shopping_list()` accepts `production_aware: bool = True` parameter
- [ ] When production_aware=True, calculates needs for remaining batches only
- [ ] When production_aware=False, calculates needs for total batches (backward compatibility)
- [ ] All production complete → empty shopping list (no ingredients needed)
- [ ] Tests verify: partial production, complete production, legacy mode
- [ ] All existing tests pass

---

## Context & Constraints

**Feature**: F079 Production-Aware Planning Calculations
**Spec**: `kitty-specs/079-production-aware-planning-calculations/spec.md` (User Story 4)
**Plan**: `kitty-specs/079-production-aware-planning-calculations/plan.md`

**Dependency**: This WP depends on WP01 for `get_remaining_production_needs()`.

**Key Constraints**:
- Must maintain backward compatibility
- Must follow session management pattern
- Shopping list currently wraps `event_service.get_shopping_list()` which may need bypassing

**Existing Code Context**:
- File to modify: `src/services/planning/shopping_list.py`
- Key function: `get_shopping_list()` (line 72)
- Current flow: wraps `event_service.get_shopping_list()` for ingredient aggregation
- May need: Direct calculation using recipe ingredients and remaining batch counts

---

## Subtasks & Detailed Guidance

### Subtask T009 – Add production_aware Parameter to Shopping List Functions

**Purpose**: Add the parameter to control total vs remaining needs calculation.

**Steps**:
1. Open `src/services/planning/shopping_list.py`
2. Add parameter to `get_shopping_list()`:
   ```python
   def get_shopping_list(
       event_id: int,
       *,
       include_sufficient: bool = True,
       production_aware: bool = True,  # NEW
       session: Optional[Session] = None,
   ) -> List[ShoppingListItem]:
       """Get shopping list with inventory comparison.

       Args:
           event_id: Event to get list for
           include_sufficient: If True, include items with sufficient stock
           production_aware: If True (default), calculate needs for remaining
                            production only. If False, calculate for total planned.
           session: Optional database session

       Returns:
           List of ShoppingListItem sorted by ingredient name
       """
   ```
3. Add same parameter to `get_items_to_buy()` and `get_shopping_summary()`:
   ```python
   def get_items_to_buy(
       event_id: int,
       *,
       production_aware: bool = True,  # NEW
       session: Optional[Session] = None,
   ) -> List[ShoppingListItem]:
   ```
4. Pass parameter through to implementation functions

**Files**: `src/services/planning/shopping_list.py`

---

### Subtask T010 – Create Remaining Ingredient Needs Helper

**Purpose**: Calculate ingredient needs based on remaining batches per recipe.

**Steps**:
1. Add import for remaining needs function:
   ```python
   from src.services.planning.progress import get_remaining_production_needs
   ```

2. Add import for recipe ingredient aggregation:
   ```python
   from src.services import recipe_service
   ```

3. Create helper function:
   ```python
   def _calculate_ingredient_needs_for_remaining(
       event_id: int,
       session: Session,
   ) -> Dict[str, Dict[str, Any]]:
       """Calculate ingredient needs for remaining production only.

       Args:
           event_id: Event to calculate for
           session: Database session

       Returns:
           Dict mapping ingredient_slug to {
               ingredient_id, ingredient_name, needed, unit
           }
       """
       from src.models import EventProductionTarget, Recipe

       # Get remaining batches per recipe
       remaining_by_recipe = get_remaining_production_needs(event_id, session=session)

       # Aggregate ingredients across all recipes with remaining batches
       ingredient_needs = {}  # slug -> {id, name, needed, unit}

       # Get production targets to know which recipes are in the plan
       targets = (
           session.query(EventProductionTarget)
           .filter(EventProductionTarget.event_id == event_id)
           .all()
       )

       for target in targets:
           remaining = remaining_by_recipe.get(target.recipe_id, 0)
           if remaining == 0:
               continue  # Skip complete recipes

           # Get aggregated ingredients for this recipe
           # This handles nested recipes
           ingredients = recipe_service.get_aggregated_ingredients(
               target.recipe_id,
               session=session,
           )

           for ing in ingredients:
               slug = ing["ingredient_slug"]
               # Scale by remaining batches
               needed_for_remaining = ing["quantity"] * remaining

               if slug in ingredient_needs:
                   ingredient_needs[slug]["needed"] += needed_for_remaining
               else:
                   ingredient_needs[slug] = {
                       "ingredient_id": ing["ingredient_id"],
                       "ingredient_slug": slug,
                       "ingredient_name": ing["ingredient_name"],
                       "needed": needed_for_remaining,
                       "unit": ing["unit"],
                   }

       return ingredient_needs
   ```

**Files**: `src/services/planning/shopping_list.py`

**Notes**:
- Uses `recipe_service.get_aggregated_ingredients()` which handles nested recipes
- Multiplies per-batch ingredient quantity by remaining batches
- Aggregates across all recipes in the event

---

### Subtask T011 – Integrate Remaining Needs into Shopping Flow

**Purpose**: Use the remaining needs calculation when production_aware=True.

**Steps**:
1. Update `_get_shopping_list_impl()` to use remaining needs:
   ```python
   def _get_shopping_list_impl(
       event_id: int,
       include_sufficient: bool,
       production_aware: bool,
       session: Session,
   ) -> List[ShoppingListItem]:
       """Implementation of get_shopping_list."""

       if production_aware:
           # Calculate needs from remaining production only
           ingredient_needs = _calculate_ingredient_needs_for_remaining(
               event_id, session
           )

           # If no remaining production, return empty list
           if not ingredient_needs:
               return []

           # Get current inventory for each ingredient
           from src.services import inventory_item_service

           items = []
           for slug, need_data in ingredient_needs.items():
               # Get current stock
               in_stock = inventory_item_service.get_available_quantity(
                   need_data["ingredient_id"],
                   session=session,
               )
               if in_stock is None:
                   in_stock = Decimal(0)

               needed = Decimal(str(need_data["needed"]))
               to_buy = calculate_purchase_gap(needed, in_stock)
               is_sufficient = in_stock >= needed

               if not include_sufficient and is_sufficient:
                   continue

               items.append(ShoppingListItem(
                   ingredient_id=need_data["ingredient_id"],
                   ingredient_slug=slug,
                   ingredient_name=need_data["ingredient_name"],
                   needed=needed,
                   in_stock=in_stock,
                   to_buy=to_buy,
                   unit=need_data["unit"],
                   is_sufficient=is_sufficient,
               ))

           return sorted(items, key=lambda x: x.ingredient_name)

       else:
           # Legacy behavior: use event_service for total needs
           result = event_service.get_shopping_list(
               event_id,
               session=session,
               include_packaging=False,
           )
           # ... existing transformation code ...
   ```

2. Update `get_items_to_buy()` to pass through parameter:
   ```python
   def get_items_to_buy(
       event_id: int,
       *,
       production_aware: bool = True,
       session: Optional[Session] = None,
   ) -> List[ShoppingListItem]:
       return get_shopping_list(
           event_id,
           include_sufficient=False,
           production_aware=production_aware,
           session=session,
       )
   ```

3. Update `get_shopping_summary()` similarly

**Files**: `src/services/planning/shopping_list.py`

**Notes**:
- May need to check if `inventory_item_service.get_available_quantity()` exists or use alternative
- Fall back to legacy behavior when production_aware=False
- Empty list when all production is complete

---

### Subtask T012 – Write Tests for Production-Aware Shopping List

**Purpose**: Verify shopping list correctly calculates needs for remaining production.

**Steps**:
1. Open or create `src/tests/planning/test_shopping_list.py`
2. Add tests for production-aware scenarios:

```python
class TestProductionAwareShoppingList:
    """Tests for production-aware shopping list calculation."""

    def test_partial_production_shows_remaining_needs(
        self, session, event_partial_production, inventory_200g_flour
    ):
        """
        Given: 10 batches target (100g flour each), 7 completed, 200g flour in stock
        When: get_shopping_list(production_aware=True)
        Then: Shows 100g flour to buy (3 batches * 100g = 300g needed, 200g in stock)
        """
        items = get_shopping_list(
            event_partial_production.id,
            production_aware=True,
            session=session,
        )

        flour_item = next((i for i in items if "flour" in i.ingredient_name.lower()), None)
        assert flour_item is not None
        assert flour_item.needed == Decimal("300")  # 3 remaining * 100g
        assert flour_item.in_stock == Decimal("200")
        assert flour_item.to_buy == Decimal("100")

    def test_all_production_complete_returns_empty_list(
        self, session, event_all_complete
    ):
        """
        Given: All production batches completed
        When: get_shopping_list(production_aware=True)
        Then: Returns empty list (nothing needed)
        """
        items = get_shopping_list(
            event_all_complete.id,
            production_aware=True,
            session=session,
        )

        assert items == []

    def test_sufficient_inventory_for_remaining_is_sufficient(
        self, session, event_partial_production, inventory_500g_flour
    ):
        """
        Given: Remaining needs 300g flour, 500g in stock
        When: get_shopping_list(production_aware=True)
        Then: Flour item shows is_sufficient=True, to_buy=0
        """
        items = get_shopping_list(
            event_partial_production.id,
            production_aware=True,
            session=session,
        )

        flour_item = next((i for i in items if "flour" in i.ingredient_name.lower()), None)
        assert flour_item.is_sufficient is True
        assert flour_item.to_buy == Decimal("0")

    def test_legacy_mode_shows_total_needs(
        self, session, event_partial_production
    ):
        """
        Given: 10 batches target (100g flour each), 7 completed
        When: get_shopping_list(production_aware=False)
        Then: Shows needs for all 10 batches (1000g flour)
        """
        items = get_shopping_list(
            event_partial_production.id,
            production_aware=False,
            session=session,
        )

        flour_item = next((i for i in items if "flour" in i.ingredient_name.lower()), None)
        assert flour_item.needed == Decimal("1000")  # All 10 batches

    def test_default_is_production_aware(self, session, event_partial_production):
        """Default behavior should be production_aware=True."""
        items_default = get_shopping_list(event_partial_production.id, session=session)
        items_explicit = get_shopping_list(
            event_partial_production.id,
            production_aware=True,
            session=session,
        )

        # Both should return same result
        assert len(items_default) == len(items_explicit)


class TestGetItemsToBuy:
    """Tests for get_items_to_buy with production_aware."""

    def test_respects_production_aware_flag(
        self, session, event_partial_production
    ):
        """get_items_to_buy should pass through production_aware parameter."""
        items = get_items_to_buy(
            event_partial_production.id,
            production_aware=True,
            session=session,
        )

        # Should only return items that need to be purchased
        assert all(item.to_buy > 0 for item in items)
```

3. Create fixtures as needed
4. Run tests: `./run-tests.sh src/tests/planning/test_shopping_list.py -v`

**Files**: `src/tests/planning/test_shopping_list.py`

**Parallel?**: Yes - tests can be written alongside implementation

---

## Test Strategy

**Required Tests**:
- Partial production shows needs for remaining batches only
- Complete production returns empty list
- Sufficient inventory shows is_sufficient=True
- Legacy mode (production_aware=False) shows total needs
- Default parameter is True
- get_items_to_buy respects production_aware flag

**Commands**:
```bash
# Run shopping list tests
./run-tests.sh src/tests/planning/test_shopping_list.py -v

# Run with coverage
./run-tests.sh src/tests/planning/test_shopping_list.py -v --cov=src/services/planning/shopping_list
```

---

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Complex integration with event_service | Medium | Medium | Bypass event_service and calculate directly |
| Inventory quantity lookup issues | Medium | Medium | Check inventory_item_service API; use fallback |
| Decimal precision issues | Low | Medium | Consistent use of Decimal() for all quantities |

---

## Definition of Done Checklist

- [ ] `get_shopping_list()` has `production_aware` parameter
- [ ] Remaining needs helper calculates correctly
- [ ] Complete production returns empty shopping list
- [ ] Legacy mode works for backward compatibility
- [ ] Tests cover all scenarios
- [ ] All existing tests pass
- [ ] Session management pattern followed

---

## Review Guidance

**Key Checkpoints**:
1. Verify session is passed through all function calls
2. Verify empty list returned when all production complete
3. Verify ingredient quantities are properly scaled by remaining batches
4. Verify Decimal types used consistently

---

## Activity Log

- 2026-01-28T06:03:15Z – system – lane=planned – Prompt generated via /spec-kitty.tasks
- 2026-01-28T06:51:09Z – unknown – shell_pid=96442 – lane=for_review – Implementation complete: Added production_aware parameter to shopping list functions. All 32 tests pass.
- 2026-01-28T12:40:36Z – claude-lead – shell_pid=27841 – lane=doing – Started review via workflow command
- 2026-01-28T12:41:19Z – claude-lead – shell_pid=27841 – lane=done – Review passed: production_aware parameter in get_shopping_list(), get_items_to_buy(), get_shopping_summary(). Uses get_remaining_production_needs and recipe_service.get_aggregated_ingredients for nested recipe support. Returns empty list when all complete. All 32 shopping list tests pass.
