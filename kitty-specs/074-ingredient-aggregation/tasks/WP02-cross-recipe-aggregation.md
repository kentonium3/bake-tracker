---
work_package_id: WP02
title: Cross-Recipe Aggregation & Edge Cases
lane: "doing"
dependencies: [WP01]
base_branch: 074-ingredient-aggregation-WP01
base_commit: 79825eb63cd316e3fe05f288872cc53055b14f1d
created_at: '2026-01-27T20:54:30.779925+00:00'
subtasks:
- T006
- T007
- T008
- T009
- T010
phase: Phase 1 - Complete Feature
assignee: ''
agent: "gemini"
shell_pid: "33821"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-01-27T20:19:43Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP02 – Cross-Recipe Aggregation & Edge Cases

## Implementation Command

```bash
spec-kitty implement WP02 --base WP01
```

**Note**: This WP depends on WP01. The `--base WP01` flag ensures the worktree is created from WP01's branch.

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

Extend ingredient aggregation to handle:
1. Multiple recipes sharing common ingredients (combine totals)
2. Same ingredient in different units (keep separate)
3. Edge cases: empty events, recipes with no ingredients, zero batches
4. Precision: 3 decimal places with no cumulative rounding errors

**Success Criteria:**
- [ ] Two recipes with flour (2 cups + 1 cup) at 2 batches each = 6 cups total
- [ ] Same ingredient in cups vs tablespoons remains separate entries
- [ ] Empty event returns empty dict (not error)
- [ ] All edge case tests pass
- [ ] Precision maintained to 3 decimals

## Context & Constraints

**Reference Documents:**
- `kitty-specs/074-ingredient-aggregation/spec.md` - FR-002, FR-003, FR-004
- `kitty-specs/074-ingredient-aggregation/plan.md` - Design decision D2, D5

**Key Constraints:**
- Aggregation key is `(ingredient_id, unit)` - FR-003 requires different units stay separate
- Round to 3 decimals only at output - FR-004 precision requirement
- Service remains read-only - no database modifications

**From spec.md User Story 2:**
> When batch decisions span multiple recipes that share common ingredients, the system aggregates the same ingredient from different recipes into a single total.

**Edge Cases from spec.md:**
- Empty event → return empty dict
- Recipe with no ingredients → skip silently
- Floating point precision → round to 3 decimals at output only

## Subtasks & Detailed Guidance

### Subtask T006 – Implement Cross-Recipe Aggregation

**Purpose**: Combine same (ingredient_id, unit) pairs from different recipes.

**Steps**:
1. The implementation in WP01 already handles this via the `totals` dict accumulation
2. Verify the aggregation key `(ingredient_id, unit)` correctly combines entries
3. Add explicit test to confirm cross-recipe behavior

**Verification**:
The existing implementation in `_aggregate_ingredients_impl()` already does:
```python
key = (ing_id, unit)
totals[key] = totals.get(key, 0.0) + qty
```

This naturally handles cross-recipe aggregation. The main work is adding tests.

**Files**: `src/services/ingredient_aggregation_service.py` (verify existing)
**Parallel?**: No

### Subtask T007 – Handle Edge Cases

**Purpose**: Ensure graceful handling of empty/edge scenarios.

**Steps**:
1. **Empty event** (no batch decisions):
   - Already handled: returns `{}` when `batch_decisions` is empty
   - Add explicit test

2. **Recipe with no ingredients**:
   - Already handled: `_scale_recipe_ingredients()` returns empty list
   - Add explicit test

3. **FinishedUnit with no recipe**:
   - Already handled: `if fu is None or fu.recipe is None: continue`
   - Add explicit test

4. **Zero batches** (shouldn't happen due to DB constraint, but handle defensively):
   ```python
   # In _aggregate_ingredients_impl, add check:
   if bd.batches <= 0:
       continue  # Skip invalid batch decisions
   ```

**Files**: `src/services/ingredient_aggregation_service.py`
**Parallel?**: No

### Subtask T008 – Implement 3-Decimal Precision Rounding

**Purpose**: Ensure precision requirement (FR-004) is met.

**Steps**:
1. Verify rounding happens only at final output:
   ```python
   # In result building (already in WP01 code):
   total_quantity=round(total_qty, 3),
   ```

2. The key is NOT rounding during accumulation:
   ```python
   # Good - accumulate full precision:
   totals[key] = totals.get(key, 0.0) + qty

   # Bad - don't do this (causes cumulative errors):
   totals[key] = round(totals.get(key, 0.0) + qty, 3)
   ```

3. Add test with values that would expose precision issues:
   - 0.333... quantities that could drift with premature rounding

**Files**: `src/services/ingredient_aggregation_service.py` (verify pattern)
**Parallel?**: No

### Subtask T009 – Write Unit Tests for Cross-Recipe Aggregation

**Purpose**: Verify multiple recipes correctly combine ingredients.

**Steps**:
Add tests to `src/tests/test_ingredient_aggregation_service.py`:

```python
class TestCrossRecipeAggregation:
    """Tests for cross-recipe ingredient aggregation."""

    @pytest.fixture
    def two_recipes_shared_ingredient(self, session):
        """Create two recipes sharing flour ingredient."""
        # Shared ingredient
        flour = Ingredient(name="Flour", category="Dry")
        # Recipe-specific ingredients
        sugar = Ingredient(name="Sugar", category="Dry")
        butter = Ingredient(name="Butter", category="Dairy")
        session.add_all([flour, sugar, butter])
        session.flush()

        # Recipe 1: Cookies (2 cups flour, 1 cup sugar)
        recipe1 = Recipe(name="Cookies", category="Cookies")
        session.add(recipe1)
        session.flush()
        session.add_all([
            RecipeIngredient(recipe_id=recipe1.id, ingredient_id=flour.id, quantity=2.0, unit="cups"),
            RecipeIngredient(recipe_id=recipe1.id, ingredient_id=sugar.id, quantity=1.0, unit="cups"),
        ])

        # Recipe 2: Bread (3 cups flour, 0.5 cups butter)
        recipe2 = Recipe(name="Bread", category="Bread")
        session.add(recipe2)
        session.flush()
        session.add_all([
            RecipeIngredient(recipe_id=recipe2.id, ingredient_id=flour.id, quantity=3.0, unit="cups"),
            RecipeIngredient(recipe_id=recipe2.id, ingredient_id=butter.id, quantity=0.5, unit="cups"),
        ])
        session.flush()

        return recipe1, recipe2, flour, sugar, butter

    def test_same_ingredient_same_unit_combined(
        self, session, sample_event, two_recipes_shared_ingredient
    ):
        """Same ingredient + unit from different recipes should combine."""
        recipe1, recipe2, flour, sugar, butter = two_recipes_shared_ingredient
        event = sample_event

        # Create FUs and batch decisions
        fu1 = FinishedUnit(
            slug="test-cookies", display_name="Test Cookies",
            recipe_id=recipe1.id, yield_mode=YieldMode.DISCRETE_COUNT,
            items_per_batch=24, item_unit="cookie",
        )
        fu2 = FinishedUnit(
            slug="test-bread", display_name="Test Bread",
            recipe_id=recipe2.id, yield_mode=YieldMode.BATCH_PORTION,
            batch_percentage=100,
        )
        session.add_all([fu1, fu2])
        session.flush()

        # 2 batches each
        session.add_all([
            BatchDecision(event_id=event.id, recipe_id=recipe1.id, finished_unit_id=fu1.id, batches=2),
            BatchDecision(event_id=event.id, recipe_id=recipe2.id, finished_unit_id=fu2.id, batches=2),
        ])
        session.flush()

        result = aggregate_ingredients_for_event(event.id, session=session)

        # Flour: (2 cups × 2) + (3 cups × 2) = 10 cups
        assert result[(flour.id, "cups")].total_quantity == 10.0
        # Sugar: 1 cup × 2 = 2 cups (only in recipe1)
        assert result[(sugar.id, "cups")].total_quantity == 2.0
        # Butter: 0.5 cups × 2 = 1 cup (only in recipe2)
        assert result[(butter.id, "cups")].total_quantity == 1.0

    def test_same_ingredient_different_units_separate(self, session, sample_event):
        """Same ingredient in different units should remain separate."""
        flour = Ingredient(name="Flour", category="Dry")
        session.add(flour)
        session.flush()

        # Recipe with flour in cups
        recipe1 = Recipe(name="Recipe Cups", category="Test")
        session.add(recipe1)
        session.flush()
        session.add(RecipeIngredient(
            recipe_id=recipe1.id, ingredient_id=flour.id, quantity=2.0, unit="cups"
        ))

        # Recipe with flour in tablespoons
        recipe2 = Recipe(name="Recipe Tbsp", category="Test")
        session.add(recipe2)
        session.flush()
        session.add(RecipeIngredient(
            recipe_id=recipe2.id, ingredient_id=flour.id, quantity=3.0, unit="tablespoons"
        ))
        session.flush()

        # Create FUs and decisions
        fu1 = FinishedUnit(
            slug="fu-cups", display_name="FU Cups",
            recipe_id=recipe1.id, yield_mode=YieldMode.DISCRETE_COUNT,
            items_per_batch=1, item_unit="item",
        )
        fu2 = FinishedUnit(
            slug="fu-tbsp", display_name="FU Tbsp",
            recipe_id=recipe2.id, yield_mode=YieldMode.DISCRETE_COUNT,
            items_per_batch=1, item_unit="item",
        )
        session.add_all([fu1, fu2])
        session.flush()

        event = sample_event
        session.add_all([
            BatchDecision(event_id=event.id, recipe_id=recipe1.id, finished_unit_id=fu1.id, batches=1),
            BatchDecision(event_id=event.id, recipe_id=recipe2.id, finished_unit_id=fu2.id, batches=1),
        ])
        session.flush()

        result = aggregate_ingredients_for_event(event.id, session=session)

        # Should have 2 separate entries for flour
        assert len(result) == 2
        assert result[(flour.id, "cups")].total_quantity == 2.0
        assert result[(flour.id, "tablespoons")].total_quantity == 3.0
```

**Files**: `src/tests/test_ingredient_aggregation_service.py`
**Parallel?**: Yes - can be written alongside T010

### Subtask T010 – Write Unit Tests for Edge Cases and Precision

**Purpose**: Verify edge case handling and precision requirements.

**Steps**:
Add tests to `src/tests/test_ingredient_aggregation_service.py`:

```python
class TestEdgeCases:
    """Tests for edge cases and precision."""

    def test_empty_event_returns_empty_dict(self, session, sample_event):
        """Event with no batch decisions should return empty dict."""
        result = aggregate_ingredients_for_event(sample_event.id, session=session)
        assert result == {}

    def test_recipe_with_no_ingredients(self, session, sample_event):
        """Recipe with no ingredients should be handled gracefully."""
        # Recipe with no ingredients
        recipe = Recipe(name="Empty Recipe", category="Test")
        session.add(recipe)
        session.flush()

        fu = FinishedUnit(
            slug="empty-fu", display_name="Empty FU",
            recipe_id=recipe.id, yield_mode=YieldMode.DISCRETE_COUNT,
            items_per_batch=1, item_unit="item",
        )
        session.add(fu)
        session.flush()

        event = sample_event
        session.add(BatchDecision(
            event_id=event.id, recipe_id=recipe.id, finished_unit_id=fu.id, batches=2
        ))
        session.flush()

        result = aggregate_ingredients_for_event(event.id, session=session)
        assert result == {}


class TestPrecision:
    """Tests for precision handling."""

    def test_precision_maintained_to_three_decimals(self, session, sample_event):
        """Quantities should be rounded to 3 decimal places."""
        ingredient = Ingredient(name="Test Ingredient", category="Test")
        session.add(ingredient)
        session.flush()

        recipe = Recipe(name="Precision Recipe", category="Test")
        session.add(recipe)
        session.flush()

        # Use a quantity that would show precision issues: 0.333...
        session.add(RecipeIngredient(
            recipe_id=recipe.id,
            ingredient_id=ingredient.id,
            quantity=0.3333333,  # More than 3 decimals
            unit="cups",
        ))
        session.flush()

        fu = FinishedUnit(
            slug="precision-fu", display_name="Precision FU",
            recipe_id=recipe.id, yield_mode=YieldMode.DISCRETE_COUNT,
            items_per_batch=1, item_unit="item",
        )
        session.add(fu)
        session.flush()

        event = sample_event
        session.add(BatchDecision(
            event_id=event.id, recipe_id=recipe.id, finished_unit_id=fu.id, batches=3
        ))
        session.flush()

        result = aggregate_ingredients_for_event(event.id, session=session)

        # 0.3333333 × 3 = 0.9999999 → should round to 1.0
        total = result[(ingredient.id, "cups")].total_quantity
        assert total == 1.0

    def test_multiple_small_quantities_no_drift(self, session, sample_event):
        """Many small additions should not cause precision drift."""
        ingredient = Ingredient(name="Drift Test", category="Test")
        session.add(ingredient)
        session.flush()

        # Create 10 recipes each with 0.1 cups
        fus = []
        for i in range(10):
            recipe = Recipe(name=f"Recipe {i}", category="Test")
            session.add(recipe)
            session.flush()
            session.add(RecipeIngredient(
                recipe_id=recipe.id,
                ingredient_id=ingredient.id,
                quantity=0.1,
                unit="cups",
            ))

            fu = FinishedUnit(
                slug=f"fu-{i}", display_name=f"FU {i}",
                recipe_id=recipe.id, yield_mode=YieldMode.DISCRETE_COUNT,
                items_per_batch=1, item_unit="item",
            )
            session.add(fu)
            fus.append(fu)

        session.flush()

        event = sample_event
        for fu in fus:
            session.add(BatchDecision(
                event_id=event.id, recipe_id=fu.recipe_id,
                finished_unit_id=fu.id, batches=1
            ))
        session.flush()

        result = aggregate_ingredients_for_event(event.id, session=session)

        # 10 × 0.1 = 1.0 exactly
        total = result[(ingredient.id, "cups")].total_quantity
        assert total == 1.0
```

**Files**: `src/tests/test_ingredient_aggregation_service.py`
**Parallel?**: Yes - can be written alongside T009

## Test Strategy

**Run all tests with:**
```bash
./run-tests.sh src/tests/test_ingredient_aggregation_service.py -v
```

**Expected results:**
- ~10 total tests pass (4 from WP01 + 6 from WP02)
- All edge cases handled gracefully
- Precision tests confirm no rounding drift

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Floating point precision | Round only at output, accumulate in full precision |
| Large number of batch decisions | Test with 10 recipes to verify no performance issues |
| Unit string inconsistency | Tests verify exact string matching for unit |

## Definition of Done Checklist

- [ ] Cross-recipe aggregation combines same (ingredient_id, unit)
- [ ] Different units for same ingredient remain separate
- [ ] Empty event returns empty dict
- [ ] Recipe with no ingredients handled gracefully
- [ ] Precision maintained to 3 decimals
- [ ] All ~10 unit tests pass

## Review Guidance

**Key checkpoints:**
1. FR-002: Same ingredient/unit from different recipes combined
2. FR-003: Different units stay separate (no conversion)
3. FR-004: 3 decimal precision, no cumulative drift
4. Edge cases handled without exceptions

## Activity Log

- 2026-01-27T20:19:43Z – system – lane=planned – Prompt created.
- 2026-01-27T20:56:47Z – claude – shell_pid=32596 – lane=for_review – WP02 complete: Cross-recipe aggregation tests and edge case tests (10 total)
- 2026-01-27T20:57:12Z – gemini – shell_pid=33821 – lane=doing – Started review via workflow command
